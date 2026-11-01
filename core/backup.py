"""Cópia de segurança do banco: exporta todas as tabelas para um arquivo criptografado e restaura em qualquer
Postgres (o Neon ou o banco reserva).

Não depende do Streamlit — é usado pela tela "Banco e backup" e pelo backup diário do GitHub (scripts/backup.py).

Formato do arquivo (.pab): b"PAB1" + sal (16 bytes) + token Fernet de JSON compactado (gzip).
A chave sai da senha via PBKDF2-SHA256. Sem a senha, o arquivo não abre.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import create_engine, text

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "001_schema.sql"
MAGICO = b"PAB1"
ITERACOES = 390_000

# Ordem de dependência (quem é referenciado vem antes)
TABELAS = ["config", "config_planos", "cupons", "campanhas", "usuarios", "condutores", "cupons_usos", "asaas_pagamentos", "escolas", "vans", "passageiros", "responsaveis", "passageiro_responsavel",
           "mensalidades", "lancamentos", "chamadas", "ausencias", "contratos", "rotas_iniciadas"]


class SenhaErrada(Exception):
    pass


# ---------------------------------------------------------------- conexão

def url_sqlalchemy(url: str) -> str:
    """Aceita postgres://, postgresql:// ou postgresql+psycopg:// e devolve no formato do psycopg 3."""
    url = url.strip()
    for velho in ("postgres://", "postgresql://"):
        if url.startswith(velho):
            return "postgresql+psycopg://" + url[len(velho):]
    return url


def motor(url: str):
    return create_engine(url_sqlalchemy(url), connect_args={"prepare_threshold": None}, pool_pre_ping=True)


# ---------------------------------------------------------------- exportar / restaurar

def _colunas(c, tabela: str) -> list[str]:
    res = c.execute(text("select column_name from information_schema.columns "
                         "where table_schema = 'public' and table_name = :t order by ordinal_position"), {"t": tabela})
    return [r[0] for r in res]


def exportar(engine) -> dict:
    """Lê todas as tabelas numa transação só leitura (foto consistente)."""
    dados = {"app": "Pequenos a Bordo", "versao": 1,
             "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tabelas": {}}
    with engine.connect() as c:
        c.execute(text("set transaction isolation level repeatable read read only"))
        for t in TABELAS:
            cols = _colunas(c, t)
            if not cols:
                continue
            # to_jsonb faz a conversão de tipos (datas, uuid, numeric, jsonb) do jeito que o Postgres entende de volta
            res = c.execute(text(f"select coalesce(jsonb_agg(to_jsonb(x)), '[]'::jsonb) from {t} x"))
            dados["tabelas"][t] = {"colunas": cols, "linhas": res.scalar()}
        c.rollback()
    return dados


def contagem(dados: dict) -> dict[str, int]:
    return {t: len(v["linhas"]) for t, v in dados["tabelas"].items()}


def criar_tabelas(engine) -> None:
    with engine.begin() as c:
        c.execute(text(SCHEMA.read_text(encoding="utf-8")))


def restaurar(engine, dados: dict) -> dict[str, int]:
    """APAGA os dados do banco de destino e grava os do backup. Tudo numa transação: ou vai tudo, ou nada."""
    criar_tabelas(engine)
    feitos = {}
    with engine.begin() as c:
        c.execute(text("truncate " + ", ".join(TABELAS) + " cascade"))
        for t in TABELAS:
            bloco = dados["tabelas"].get(t)
            if not bloco or not bloco["linhas"]:
                feitos[t] = 0
                continue
            # só as colunas que existem nos dois lados; as novas ficam com o valor padrão
            cols = [x for x in _colunas(c, t) if x in set(bloco["colunas"])]
            lista = ", ".join(f'"{x}"' for x in cols)
            c.execute(text(f"insert into {t} ({lista}) select {lista} from "
                           f"jsonb_populate_recordset(null::{t}, cast(:d as jsonb))"),
                      {"d": json.dumps(bloco["linhas"], ensure_ascii=False)})
            feitos[t] = len(bloco["linhas"])
    return feitos


def copiar(origem, destino) -> dict[str, int]:
    """Copia tudo de um banco para outro (ex.: Neon → reserva)."""
    return restaurar(destino, exportar(origem))


# ---------------------------------------------------------------- arquivo criptografado

def _chave(senha: str, sal: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=ITERACOES)
    return base64.urlsafe_b64encode(kdf.derive(senha.encode("utf-8")))


def cifrar(dados: dict, senha: str) -> bytes:
    if not senha:
        raise ValueError("Informe a senha do backup.")
    sal = os.urandom(16)
    bruto = gzip.compress(json.dumps(dados, ensure_ascii=False).encode("utf-8"))
    return MAGICO + sal + Fernet(_chave(senha, sal)).encrypt(bruto)


def decifrar(arquivo: bytes, senha: str) -> dict:
    if not arquivo.startswith(MAGICO):
        raise ValueError("Este arquivo não é um backup do Pequenos a Bordo.")
    sal, token = arquivo[4:20], arquivo[20:]
    try:
        bruto = Fernet(_chave(senha, sal)).decrypt(token)
    except InvalidToken as e:
        raise SenhaErrada("Senha errada (ou arquivo corrompido).") from e
    return json.loads(gzip.decompress(bruto))


def nome_arquivo(quando: datetime | None = None) -> str:
    quando = quando or datetime.now(timezone.utc)
    return f"pequenos-a-bordo-{quando:%Y-%m-%d-%H%M}.pab"
