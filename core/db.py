"""Acesso ao banco (Neon Postgres) via st.connection.

A URL fica nos Secrets do Streamlit:

    [connections.neon]
    url = "postgresql+psycopg://usuario:senha@host/banco?sslmode=require"
"""
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import text

_SCHEMA = Path(__file__).resolve().parent.parent / "db" / "001_schema.sql"


def _conn():
    # pool_pre_ping: o Neon "dorme" após 5 min sem uso; isso refaz a conexão sozinho
    return st.connection("neon", type="sql", pool_pre_ping=True, pool_recycle=240)


# Leituras guardadas em memória por 2 min; qualquer gravação feita pelo app apaga o que estava guardado.
_VERSAO = {"n": 0}


def _mudou():
    _VERSAO["n"] += 1


@contextmanager
def transacao():
    """Bloco com commit no fim (ou rollback se der erro)."""
    with _conn().session as s:
        try:
            yield s
            s.commit()
            _mudou()
        except Exception:
            s.rollback()
            raise


def _ler(sql: str, params: dict):
    with _conn().session as s:
        res = s.execute(text(sql), params)
        return list(res.keys()), [tuple(r) for r in res.all()]


@st.cache_data(ttl=120, max_entries=3000, show_spinner=False)
def _ler_cache(sql: str, params: dict, versao: int):
    return _ler(sql, params)


def _buscar(sql: str, params: dict):
    try:
        return _ler_cache(sql, params, _VERSAO["n"])
    except Exception:  # noqa: BLE001 — parâmetro que não dá para guardar: lê direto
        return _ler(sql, params)


def _vazio(v) -> bool:
    try:
        return v is None or bool(pd.isna(v))
    except (TypeError, ValueError):   # listas/arrays
        return False


def _df(cols, linhas) -> pd.DataFrame:
    """DataFrame com None (não NaN) nos vazios de colunas de texto/data — as telas testam `if valor`."""
    # dtype=object: o pandas 3 transformaria texto vazio em NaN (StringDtype)
    df = pd.DataFrame(linhas, columns=cols, dtype=object)
    for c in df.columns:
        vals = [v for v in df[c] if v is not None]
        if vals and all(isinstance(v, bool) for v in vals) and len(vals) == len(df):
            df[c] = df[c].astype(bool)
        elif vals and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals) \
                and len(vals) == len(df):
            df[c] = pd.to_numeric(df[c])
        else:
            df[c] = pd.Series([None if _vazio(v) else v for v in df[c]], index=df.index, dtype=object)
    return df


def consultar(sql: str, **params) -> pd.DataFrame:
    return _df(*_buscar(sql, params))


def um(sql: str, **params) -> dict | None:
    cols, linhas = _buscar(sql, params)
    return dict(zip(cols, linhas[0])) if linhas else None


def ao_vivo(sql: str, **params) -> pd.DataFrame:
    """Leitura sem cache (o que muda por outro usuário, ex.: aviso de falta dos pais)."""
    return _df(*_ler(sql, params))


def gravar(sql: str, **params) -> dict | None:
    """INSERT/UPDATE/DELETE com commit; devolve a 1ª linha do RETURNING, se houver."""
    with transacao() as s:
        res = s.execute(text(sql), params)
        try:
            row = res.mappings().first()
        except Exception:  # noqa: BLE001 — comando sem RETURNING
            return None
        return dict(row) if row else None


@st.cache_resource(show_spinner="Preparando o banco…")
def migrar() -> bool:
    """Cria as tabelas na 1ª vez (idempotente). Roda uma vez por processo do servidor."""
    with _conn().session as s:
        s.execute(text(_SCHEMA.read_text(encoding="utf-8")))
        s.commit()
    return True
