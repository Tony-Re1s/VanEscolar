"""Avisos para o administrador (Tony): conta nova e 1ª mensagem de suporte de cada cliente.

E-mail pelo Gmail do próprio Tony (SMTP com "senha de app"), configurado nos Secrets:
    [email]
    usuario = "...@gmail.com"
    senha_app = "xxxx xxxx xxxx xxxx"
    avisar = "...@gmail.com"     # opcional (padrão: o próprio usuario)
Também manda no Telegram do admin, se o bot de suporte estiver conectado.
Tudo roda numa thread com timeout curto: se falhar, o app segue normal (só fica no log).
"""
from __future__ import annotations

import smtplib
import ssl
import threading
from email.message import EmailMessage


def _cfg_email() -> dict:
    import streamlit as st
    try:
        cfg = dict(st.secrets.get("email") or {})
    except Exception:  # noqa: BLE001
        return {}
    if not (cfg.get("usuario") and cfg.get("senha_app")):
        return {}
    cfg["avisar"] = cfg.get("avisar") or cfg["usuario"]
    cfg["senha_app"] = str(cfg["senha_app"]).replace(" ", "")
    return cfg


def _enviar_email(cfg: dict, assunto: str, corpo: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"Turminha a Bordo <{cfg['usuario']}>"
    msg["To"] = cfg["avisar"]
    msg["Subject"] = assunto
    msg.set_content(corpo)
    try:
        with smtplib.SMTP_SSL(cfg.get("servidor", "smtp.gmail.com"), int(cfg.get("porta", 465)),
                              context=ssl.create_default_context(), timeout=15) as s:
            s.login(cfg["usuario"], cfg["senha_app"])
            s.send_message(msg)
    except Exception as e:  # noqa: BLE001
        print(f"[avisos] e-mail não saiu: {type(e).__name__}: {e}", flush=True)


def _enviar_telegram(texto: str) -> None:
    try:
        from core import db, suporte
        from telas import _ui
        tg = _ui.telegram()
        chat = suporte.admin_chat(db._conn().engine) if tg else None
    except Exception as e:  # noqa: BLE001
        print(f"[avisos] Telegram não saiu: {type(e).__name__}: {e}", flush=True)
        return
    if tg and chat:
        def _vai():
            try:
                tg.enviar(chat, texto)
            except Exception as e:  # noqa: BLE001
                print(f"[avisos] Telegram não saiu: {type(e).__name__}: {e}", flush=True)
        threading.Thread(target=_vai, daemon=True).start()


def avisar(assunto: str, corpo: str, telegram: bool = True) -> None:
    """Dispara e-mail (e Telegram) sem travar a tela."""
    cfg = _cfg_email()
    if cfg:
        threading.Thread(target=_enviar_email, args=(cfg, assunto, corpo), daemon=True).start()
    if telegram:
        _enviar_telegram(f"{assunto}\n\n{corpo}")


def conta_nova(nome: str, email: str, telefone: str | None, indicador: str | None, presente: str | None) -> None:
    corpo = "\n".join([
        f"Empresa: {nome}",
        f"E-mail: {email}",
        f"WhatsApp: {telefone or 'não informado'}",
        f"Indicado por: {indicador}" if indicador else "Sem indicação",
        f"Plano grátis: {presente}" if presente else "",
        "",
        "Veja em Administração → Assinantes: https://turminhaabordo.com.br",
    ])
    avisar(f"🚐 Nova conta no Turminha: {nome}", corpo)


def primeira_mensagem(empresa: str, cabecalho: str, texto: str) -> None:
    corpo = f"{cabecalho}\n\nMensagem:\n{texto}\n\nResponda pelo Telegram ou em Administração → Suporte no app."
    # no Telegram a mensagem já chega pelo bot de suporte — aqui vai só o e-mail
    avisar(f"💬 Primeira mensagem de suporte: {empresa}", corpo, telegram=False)
