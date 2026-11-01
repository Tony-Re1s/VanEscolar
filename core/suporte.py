"""Fale conosco: chat do assinante com o suporte, entregue no Telegram do administrador.

Como funciona (o Streamlit não recebe webhook, então o app CONSULTA o Telegram — getUpdates):
- o cliente escreve no app → a mensagem é gravada e enviada ao bot, no chat do administrador;
- o administrador usa "Responder" na mensagem no Telegram → na próxima consulta a resposta é gravada e aparece no app;
- conectar o administrador: ele manda ao bot o código que a tela de Suporte mostra (/start CODIGO).
Sem Streamlit aqui: recebe um engine do SQLAlchemy (serve para o app e para o GitHub Actions).
"""
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import text


class TelegramErro(Exception):
    pass


class Telegram:
    def __init__(self, token: str, base_url: str | None = None):
        if not token:
            raise TelegramErro("Chave do bot do Telegram não configurada.")
        self.base = (base_url or "https://api.telegram.org").rstrip("/") + f"/bot{token}"

    def _req(self, metodo: str, dados: dict | None = None):
        req = urllib.request.Request(self.base + "/" + metodo, data=json.dumps(dados or {}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                desc = json.loads(e.read().decode()).get("description") or str(e)
            except Exception:  # noqa: BLE001
                desc = str(e)
            if e.code == 401:
                desc = "Chave do bot do Telegram inválida."
            raise TelegramErro(desc) from e
        except (urllib.error.URLError, OSError) as e:
            raise TelegramErro(f"Não consegui falar com o Telegram ({e}).") from e
        if not res.get("ok"):
            raise TelegramErro(res.get("description") or "Erro no Telegram.")
        return res.get("result")

    def eu(self) -> dict:
        return self._req("getMe")

    def enviar(self, chat_id, texto: str, responder_a: int | None = None) -> int:
        d = {"chat_id": chat_id, "text": texto[:4000], "disable_web_page_preview": True}
        if responder_a:
            d["reply_parameters"] = {"message_id": responder_a, "allow_sending_without_reply": True}
        return int(self._req("sendMessage", d)["message_id"])

    def novidades(self, offset: int | None) -> list[dict]:
        d = {"timeout": 0, "allowed_updates": ["message"]}
        if offset:
            d["offset"] = offset
        return self._req("getUpdates", d) or []


# ---------------------------------------------------------------- configuração guardada no banco
def _cfg(c, chave: str) -> dict:
    r = c.execute(text("select valor from config where chave = :k"), {"k": chave}).first()
    return r[0] if r and isinstance(r[0], dict) else {}


def _set(c, chave: str, valor: dict):
    c.execute(text("""insert into config (chave, valor) values (:k, cast(:v as jsonb))
                      on conflict (chave) do update set valor = excluded.valor"""),
              {"k": chave, "v": json.dumps(valor)})


def admin_chat(engine) -> int | None:
    with engine.connect() as c:
        return _cfg(c, "telegram_admin").get("chat_id")


def codigo_conexao(engine, novo: bool = False) -> str:
    """Código que o administrador manda ao bot para ligar o chat dele (troca a cada pedido de 'novo')."""
    with engine.begin() as c:
        cod = _cfg(c, "telegram_codigo").get("codigo")
        if novo or not cod:
            cod = secrets.token_hex(3).upper()
            _set(c, "telegram_codigo", {"codigo": cod})
        return cod


def desconectar(engine):
    with engine.begin() as c:
        c.execute(text("delete from config where chave = 'telegram_admin'"))


# ---------------------------------------------------------------- cliente → suporte
def enviar_cliente(engine, tg: Telegram | None, cid, email: str, texto: str, cabecalho: str) -> bool:
    """Grava a mensagem e manda para o Telegram do administrador. Devolve True se chegou no Telegram."""
    texto = (texto or "").strip()[:2000]
    if not texto:
        return False
    with engine.begin() as c:
        mid = c.execute(text("""insert into suporte_mensagens (condutor_id, autor, autor_email, texto, lida)
                                values (cast(:c as uuid), 'cliente', :e, :t, false) returning id"""),
                        {"c": str(cid), "e": email, "t": texto}).scalar_one()
        chat = _cfg(c, "telegram_admin").get("chat_id")
    if not (tg and chat):
        return False
    try:
        tg_id = tg.enviar(chat, f"💬 {cabecalho}\n\n{texto}\n\n↩️ Use \"Responder\" nesta mensagem para responder.")
    except TelegramErro:
        return False
    with engine.begin() as c:
        c.execute(text("update suporte_mensagens set tg_msg_id = :g where id = :i"), {"g": tg_id, "i": mid})
    return True


def responder_pelo_app(engine, cid, texto: str, email: str):
    """O administrador também pode responder pela tela de Suporte do app."""
    with engine.begin() as c:
        c.execute(text("""insert into suporte_mensagens (condutor_id, autor, autor_email, texto, lida)
                          values (cast(:c as uuid), 'suporte', :e, :t, false)"""),
                  {"c": str(cid), "e": email, "t": texto.strip()[:4000]})
        c.execute(text("""update suporte_mensagens set lida = true
                          where condutor_id = cast(:c as uuid) and autor = 'cliente'"""), {"c": str(cid)})


def reenviar_pendentes(engine, tg: Telegram) -> int:
    """Mensagens de cliente que não chegaram no Telegram (enviadas antes de conectar o bot ou com o Telegram fora
    do ar) — manda agora. Só as dos últimos 7 dias."""
    with engine.connect() as c:
        chat = _cfg(c, "telegram_admin").get("chat_id")
        if not chat:
            return 0
        rs = [dict(r._mapping) for r in c.execute(text("""
            select m.id, m.texto, m.autor_email, m.criado_em, c.nome, c.plano, c.plano_tipo, c.telefone
            from suporte_mensagens m join condutores c on c.id = m.condutor_id
            where m.autor = 'cliente' and m.tg_msg_id is null and m.criado_em > now() - interval '7 days'
            order by m.criado_em limit 20"""))]
    n = 0
    for r in rs:
        cab = " · ".join(x for x in (r["nome"], (r["plano"] or "sem plano").capitalize(), r["autor_email"],
                                     r["telefone"]) if x)
        from zoneinfo import ZoneInfo
        quando = r["criado_em"].astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m %H:%M")
        try:
            tg_id = tg.enviar(chat, f"💬 {cab}\n(enviada em {quando})\n\n{r['texto']}\n\n"
                                    "↩️ Use \"Responder\" nesta mensagem para responder.")
        except TelegramErro:
            break
        with engine.begin() as c:
            c.execute(text("update suporte_mensagens set tg_msg_id = :g where id = :i"), {"g": tg_id, "i": r["id"]})
        n += 1
    return n


# ---------------------------------------------------------------- Telegram → app (respostas)
AJUDA = ("Para responder um cliente, toque e segure a mensagem dele e escolha \"Responder\". "
         "Mensagens soltas não vão para ninguém.")


def sincronizar(engine, tg: Telegram) -> dict:
    """Lê as novidades do bot: conecta o administrador (código) e grava as respostas dele. Idempotente."""
    out = dict(respostas=0, conectado=False, erro=None, reenviadas=0)
    try:
        with engine.connect() as c:
            offset = _cfg(c, "telegram_offset").get("offset")
        ups = tg.novidades(offset)
    except TelegramErro as e:
        out["erro"] = str(e)
        return out
    if not ups:
        out["reenviadas"] = reenviar_pendentes(engine, tg)
        return out
    with engine.begin() as c:
        chat_admin = _cfg(c, "telegram_admin").get("chat_id")
        codigo = _cfg(c, "telegram_codigo").get("codigo")
        avisos = []
        for u in ups:
            m = u.get("message") or {}
            chat = (m.get("chat") or {})
            txt = (m.get("text") or "").strip()
            if chat.get("type") != "private" or not txt:
                continue
            # 1) conexão do administrador: "/start CODIGO" ou só "CODIGO"
            palavras = txt.replace("/start", " ").split()
            if codigo and codigo in [p.upper() for p in palavras]:
                _set(c, "telegram_admin", {"chat_id": chat["id"], "nome": (m.get("from") or {}).get("first_name")})
                _set(c, "telegram_codigo", {"codigo": secrets.token_hex(3).upper()})   # código vale 1 vez
                chat_admin, codigo = chat["id"], None
                out["conectado"] = True
                avisos.append((chat["id"], "✅ Pronto! As mensagens do \"Fale conosco\" vão chegar aqui. "
                                            "Para responder, use \"Responder\" na mensagem do cliente.", None))
                continue
            if chat.get("id") != chat_admin:
                avisos.append((chat["id"], "Olá! 👋 Este é o canal interno de suporte do Turminha a Bordo. "
                                           "Se você é assinante, fale com a gente pelo app, em \"Fale conosco\".",
                               None))
                continue
            orig = (m.get("reply_to_message") or {}).get("message_id")
            if not orig:
                avisos.append((chat["id"], AJUDA, m.get("message_id")))
                continue
            r = c.execute(text("select condutor_id from suporte_mensagens where tg_msg_id = :g limit 1"),
                          {"g": orig}).first()
            if not r:
                avisos.append((chat["id"], "Não achei de qual cliente é essa mensagem. Responda direto na mensagem "
                                           "que chegou do cliente.", m.get("message_id")))
                continue
            novo = c.execute(text("""insert into suporte_mensagens (condutor_id, autor, texto, tg_msg_id, tg_update_id)
                                     values (:c, 'suporte', :t, :g, :u) on conflict (tg_update_id) do nothing
                                     returning id"""),
                             {"c": r[0], "t": txt[:4000], "g": m.get("message_id"), "u": u["update_id"]}).first()
            if novo:
                c.execute(text("""update suporte_mensagens set lida = true
                                  where condutor_id = :c and autor = 'cliente'"""), {"c": r[0]})
                out["respostas"] += 1
        _set(c, "telegram_offset", {"offset": max(u["update_id"] for u in ups) + 1})
    for chat_id, msg, resp in avisos:
        try:
            tg.enviar(chat_id, msg, resp)
        except TelegramErro:
            pass
    out["reenviadas"] = reenviar_pendentes(engine, tg)
    return out


# ---------------------------------------------------------------- leituras
def mensagens(engine, cid) -> list[dict]:
    with engine.connect() as c:
        rs = c.execute(text("""select id, autor, texto, criado_em, lida from suporte_mensagens
                               where condutor_id = cast(:c as uuid) order by criado_em, id"""), {"c": str(cid)})
        return [dict(r._mapping) for r in rs]


def nao_lidas_cliente(engine, cid) -> int:
    """Respostas do suporte que o cliente ainda não viu."""
    with engine.connect() as c:
        return int(c.execute(text("""select count(*) from suporte_mensagens where condutor_id = cast(:c as uuid)
                                     and autor = 'suporte' and not lida"""), {"c": str(cid)}).scalar_one())


def marcar_lidas_cliente(engine, cid):
    with engine.begin() as c:
        c.execute(text("""update suporte_mensagens set lida = true where condutor_id = cast(:c as uuid)
                          and autor = 'suporte' and not lida"""), {"c": str(cid)})


def conversas(engine) -> list[dict]:
    with engine.connect() as c:
        rs = c.execute(text("""
            select c.id, c.nome, c.plano, c.plano_tipo, max(m.criado_em) as ultima,
                   count(*) filter (where m.autor = 'cliente' and not m.lida) as pendentes
            from suporte_mensagens m join condutores c on c.id = m.condutor_id
            group by c.id, c.nome, c.plano, c.plano_tipo order by pendentes desc, ultima desc"""))
        return [dict(r._mapping) for r in rs]
