"""Acesso ao banco (Neon Postgres) via st.connection.

A URL fica nos Secrets do Streamlit:

    [connections.neon]
    url = "postgresql+psycopg://usuario:senha@host/banco?sslmode=require"
"""
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import exc, text

_SCHEMA = Path(__file__).resolve().parent.parent / "db" / "001_schema.sql"


def banco_ativo() -> str:
    """Qual conexão usar: [app] banco = "neon" (padrão) ou "reserva" nos Secrets — o switch do banco reserva."""
    try:
        return str(st.secrets["app"].get("banco", "neon"))
    except Exception:  # noqa: BLE001
        return "neon"


def bancos_configurados() -> list[str]:
    """Conexões com URL nos Secrets ([connections.neon], [connections.reserva]…)."""
    try:
        return [n for n, v in st.secrets["connections"].items() if v.get("url")]
    except Exception:  # noqa: BLE001
        return []


def conexao(nome: str):
    return st.connection(nome, type="sql", pool_pre_ping=False, pool_recycle=240,
                         connect_args={"prepare_threshold": None})


def _conn():
    # Sem pool_pre_ping (custava 1 ida ao banco a mais por consulta). Conexão que o Neon derrubou é
    # refeita pelo _tentar() abaixo; pool_recycle troca as conexões antigas antes do Neon fechá-las.
    return conexao(banco_ativo())   # sem prepared statements: compatível com o pooler do Neon


def _tentar(fn):
    """Roda fn(); se a conexão tinha caído (Neon dormiu/reiniciou), descarta o pool e tenta mais uma vez."""
    try:
        return fn()
    except exc.OperationalError:
        _conn().engine.dispose()
        return fn()
    except exc.DBAPIError as e:
        if not e.connection_invalidated:
            raise
        _conn().engine.dispose()
        return fn()


# Leituras guardadas em memória por 2 min; qualquer gravação feita pelo app apaga o que estava guardado.
_VERSAO = {"n": 0}


def _mudou():
    _VERSAO["n"] += 1


@contextmanager
def transacao():
    """Bloco com commit no fim (ou rollback se der erro)."""
    try:                                    # acorda/valida a conexão antes de gravar (1 ida a mais só nas gravações)
        _tentar(lambda: _ler("select 1", {}))
    except Exception:  # noqa: BLE001
        pass
    with _conn().session as s:
        try:
            yield s
            s.commit()
            _mudou()
        except Exception:
            s.rollback()
            raise


def _ler_uma_vez(sql: str, params: dict):
    # AUTOCOMMIT: leitura numa ida só (sem BEGIN/ROLLBACK em volta)
    import time
    t0 = time.time()
    with _conn().engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        t1 = time.time()
        res = c.execute(text(sql), params)
        out = list(res.keys()), [tuple(r) for r in res.all()]
    if time.time() - t0 > 1.5:      # diagnóstico de lentidão (aparece nos registros do Streamlit Cloud)
        print(f"[lento] consulta {time.time() - t0:.1f}s (conectar {t1 - t0:.1f}s): {' '.join(sql.split())[:80]}",
              flush=True)
    return out


def _ler(sql: str, params: dict):
    return _tentar(lambda: _ler_uma_vez(sql, params))


@st.cache_data(ttl=120, max_entries=3000, show_spinner=False)
def _ler_cache(sql: str, params: dict, versao: int, banco: str):
    return _ler(sql, params)


def _buscar(sql: str, params: dict):
    try:
        return _ler_cache(sql, params, _VERSAO["n"], banco_ativo())
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


def versao_schema() -> str:
    """Muda quando o db/001_schema.sql muda — assim o migrar() roda de novo sem precisar de Reboot."""
    import hashlib
    return hashlib.sha1(_SCHEMA.read_bytes()).hexdigest()[:12]


@st.cache_resource(show_spinner="Preparando o banco…")
def migrar(banco: str = "", versao: str = "") -> bool:
    """Cria as tabelas na 1ª vez (idempotente). Roda uma vez por processo do servidor e por banco
    (ao virar o switch para o reserva, ele também é preparado)."""
    with _conn().session as s:
        s.execute(text(_SCHEMA.read_text(encoding="utf-8")))
        s.commit()
    return True
