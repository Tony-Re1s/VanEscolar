"""Vigia dos apps no Streamlit Cloud (GitHub Actions, de 30 em 30 min).

Abre cada app num navegador de verdade e espera o conteúdo aparecer. Se o app estava dormindo, acorda.
Se não abrir (tenta 2 vezes), avisa o Tony no Telegram e por e-mail — 1 vez quando cai, de novo a cada 3 h
enquanto continuar fora e 1 vez quando voltar. O estado fica no banco (config 'vigia_apps').

Variáveis: NEON_URL (estado + chat do Telegram), TELEGRAM_TOKEN (opcional),
EMAIL_USUARIO / EMAIL_SENHA_APP / EMAIL_AVISAR (opcionais, Gmail com senha de app).
Apps: VIGIA_APPS="Nome|url|reinicia;Nome|url" (padrão: Turminha e Finanças).

Reinício automático (só para app deste repositório, marcado "reinicia"): o Streamlit não tem API de reboot. O truque
conhecido é mudar o requirements.txt — o Streamlit reinstala as dependências e sobe o app de novo. O vigia troca uma
linha de comentário no fim do arquivo, faz o push, espera 4 min e testa de novo. No máximo 1 vez a cada 3 h.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, text

BRT = timezone(timedelta(hours=-3))
PADRAO = "Turminha a Bordo|https://turminhaabordo.streamlit.app/|reinicia;Finanças|https://financaspes.streamlit.app/"
LEMBRAR_A_CADA = timedelta(hours=3)


def apps() -> list[tuple[str, str, bool]]:
    out = []
    for item in (os.environ.get("VIGIA_APPS") or PADRAO).split(";"):
        partes = [x.strip() for x in item.split("|")]
        if len(partes) >= 2:
            out.append((partes[0], partes[1], len(partes) > 2 and partes[2] == "reinicia"))
    return out


def abre(pg, url: str) -> tuple[bool, str]:
    """True se o conteúdo do app apareceu."""
    try:
        pg.goto(url, timeout=90000)
    except Exception as e:  # noqa: BLE001
        return False, f"página não abriu ({type(e).__name__})"
    pg.wait_for_timeout(6000)
    botao = pg.get_by_role("button", name="Yes, get this app back up!")
    if botao.count():
        print("  estava dormindo — acordando…")
        botao.click()
    fim = datetime.now() + timedelta(seconds=120)
    while datetime.now() < fim:
        for fr in pg.frames:          # o app fica num iframe /~/+/ no Streamlit Cloud (ou na própria página)
            try:
                txt = fr.evaluate("() => (document.querySelector('[data-testid=\"stMain\"]') || "
                                  "document.querySelector('[data-testid=\"stAppViewBlockContainer\"]') || "
                                  "{innerText: ''}).innerText")
            except Exception:  # noqa: BLE001
                txt = ""
            if len((txt or "").strip()) > 10:
                return True, "ok"
        pg.wait_for_timeout(3000)
    return False, "o app ficou carregando por mais de 2 minutos"


def testar(so: str | None = None) -> dict[str, tuple[bool, str]]:
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for nome, url, _ in apps():
            if so and nome != so:
                continue
            pg = b.new_page()
            ok, motivo = abre(pg, url)
            if not ok:
                print(f"  {nome}: falhou ({motivo}) — tentando de novo em 1 min")
                pg.wait_for_timeout(60000)
                ok, motivo = abre(pg, url)
            print(f"{nome}: {'OK' if ok else 'FORA — ' + motivo}")
            res[nome] = (ok, motivo)
            pg.close()
        b.close()
    return res


def _cfg(engine, chave: str) -> dict:
    with engine.connect() as c:
        r = c.execute(text("select valor from config where chave = :k"), {"k": chave}).scalar()
    if isinstance(r, str):
        r = json.loads(r)
    return r or {}


def _salvar(engine, chave: str, valor: dict):
    with engine.begin() as c:
        c.execute(text("""insert into config (chave, valor) values (:k, cast(:v as jsonb))
                          on conflict (chave) do update set valor = excluded.valor"""),
                  {"k": chave, "v": json.dumps(valor)})


def telegram(engine, msg: str):
    tok = os.environ.get("TELEGRAM_TOKEN")
    chat = (_cfg(engine, "telegram_admin") or {}).get("chat_id") if engine else None
    if not (tok and chat):
        print("  (sem Telegram configurado)")
        return
    dados = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", dados, timeout=20)
    except Exception as e:  # noqa: BLE001
        print(f"  Telegram falhou: {e}")


def email(assunto: str, corpo: str):
    u, s = os.environ.get("EMAIL_USUARIO"), (os.environ.get("EMAIL_SENHA_APP") or "").replace(" ", "")
    if not (u and s):
        print("  (sem e-mail configurado)")
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = f"Turminha a Bordo <{u}>", os.environ.get("EMAIL_AVISAR") or u, assunto
    m.set_content(corpo)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=20) as srv:
            srv.login(u, s)
            srv.send_message(m)
    except Exception as e:  # noqa: BLE001
        print(f"  e-mail falhou: {e}")


def avisar(engine, assunto: str, corpo: str):
    print(f"AVISO: {assunto}")
    telegram(engine, f"{assunto}\n\n{corpo}")
    email(assunto, corpo)


def reiniciar() -> bool:
    """Força o Streamlit a reinstalar e subir o app de novo (mudança no requirements.txt + push)."""
    arq = "requirements.txt"
    linhas = [ln for ln in open(arq, encoding="utf-8").read().splitlines() if not ln.startswith("# vigia:")]
    linhas.append(f"# vigia: reinício automático em {datetime.now(BRT):%d/%m/%Y %H:%M:%S}")
    open(arq, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
    cmds = [["git", "config", "user.name", "vigia-turminha"],
            ["git", "config", "user.email", "vigia@turminhaabordo.com.br"],
            ["git", "add", arq], ["git", "commit", "-m", "vigia: reinício automático do app (travado)"],
            ["git", "pull", "--rebase", "origin", "main"], ["git", "push", "origin", "HEAD:main"]]
    for c in cmds:
        r = subprocess.run(c, capture_output=True, text=True)
        if r.returncode:
            print(f"  reinício falhou em {' '.join(c)}: {r.stderr.strip()[:200]}")
            return False
    print("  push feito — esperando o Streamlit subir o app de novo (4 min)…")
    time.sleep(240)
    return True


def main():
    url = os.environ.get("NEON_URL")
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1)
                           if url.startswith("postgresql://") else url, pool_pre_ping=True) if url else None
    res = testar()
    estado = _cfg(engine, "vigia_apps") if engine else {}
    agora = datetime.now(BRT)
    reinicia = {n for n, _, r in apps() if r}
    for nome, (ok, motivo) in res.items():
        e = estado.get(nome) or {}
        ult = e.get("ultimo_reinicio")
        if (not ok and nome in reinicia and os.environ.get("GITHUB_ACTIONS")
                and (not ult or agora - datetime.fromisoformat(ult) >= LEMBRAR_A_CADA)):
            e["ultimo_reinicio"] = agora.isoformat()
            if reiniciar():
                ok2, motivo2 = testar(so=nome)[nome]
                if ok2:
                    avisar(engine, f"🔄 {nome} travou e voltou sozinho",
                           f"Às {agora:%H:%M} o app não abria ({motivo}). Fiz o reinício automático e ele voltou. "
                           "Não precisa fazer nada.")
                    estado[nome] = {"falhando": False, "ultimo_reinicio": e["ultimo_reinicio"]}
                    continue
                motivo = f"{motivo2} — e o reinício automático não resolveu"
        if ok:
            if e.get("falhando"):
                desde = datetime.fromisoformat(e["desde"])
                avisar(engine, f"✅ {nome} voltou a abrir",
                       f"O app voltou às {agora:%H:%M} (ficou fora desde {desde:%d/%m %H:%M}).")
            estado[nome] = {"falhando": False, "ultimo_reinicio": e.get("ultimo_reinicio")}
        else:
            lembrar = (not e.get("falhando") or
                       agora - datetime.fromisoformat(e.get("ultimo_aviso", e.get("desde"))) >= LEMBRAR_A_CADA)
            if lembrar:
                avisar(engine, f"⚠️ {nome} não está abrindo",
                       f"Testei às {agora:%H:%M} e {motivo}.\n\nO que resolve quase sempre: share.streamlit.io → "
                       f"⋮ do app → Reboot. Vou testar de novo em 30 minutos e aviso quando voltar.")
                e["ultimo_aviso"] = agora.isoformat()
            estado[nome] = {"falhando": True, "desde": e.get("desde") or agora.isoformat(),
                            "ultimo_aviso": e.get("ultimo_aviso") or agora.isoformat(),
                            "ultimo_reinicio": e.get("ultimo_reinicio")}
    if engine:
        _salvar(engine, "vigia_apps", estado)


if __name__ == "__main__":
    main()
