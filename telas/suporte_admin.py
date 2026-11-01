"""Administração → Suporte: liga o Telegram do administrador ao bot e mostra/responde as conversas do Fale conosco."""
import streamlit as st

from core import repo, suporte
from core.fmt import TZ
from telas import _ui

u = st.session_state["usuario"]
if not u.get("admin"):
    st.stop()

st.title("Suporte")
ENG = _ui.motor()
tg = _ui.telegram()

if not tg:
    st.warning("Falta a chave do bot nos **Secrets** do Streamlit: uma seção `[telegram]` com `token = \"…\"`.",
               icon=":material/key:")
else:
    res = _ui.sincronizar_suporte(intervalo=0)
    if res and res.get("erro"):
        st.error(f"Telegram: {res['erro']}", icon=":material/error:")
    chat = suporte.admin_chat(ENG)
    with st.container(border=True, key="card_tg"):
        if chat:
            st.success("Seu Telegram está conectado: as mensagens do Fale conosco chegam no bot. Para responder, "
                       "use **Responder** na mensagem do cliente.", icon=":material/check_circle:")
            if st.button("Desconectar / conectar outro Telegram", type="tertiary"):
                suporte.desconectar(ENG)
                st.rerun()
        else:
            try:
                bot = tg.eu().get("username")
            except Exception as e:  # noqa: BLE001
                bot = None
                st.error(f"Não consegui falar com o bot: {e}")
            cod = suporte.codigo_conexao(ENG)
            st.markdown("**Conectar o seu Telegram** — toque no botão (abre o bot e envia o código) e depois clique "
                        f"em *Já mandei*. Ou mande para o bot a mensagem: `{cod}`")
            a, b = st.columns(2)
            if bot:
                a.link_button("Abrir o bot no Telegram", f"https://t.me/{bot}?start={cod}", icon=":material/send:",
                              type="primary", width="stretch")
            if b.button("Já mandei", icon=":material/refresh:", width="stretch"):
                st.rerun()

st.subheader("Conversas")
conv = suporte.conversas(ENG)
if not conv:
    st.caption("Nenhuma mensagem ainda.")
    st.stop()
ids = [str(x["id"]) for x in conv]
rot = {str(x["id"]): f"{x['nome']}" + (f"  · {x['pendentes']} sem resposta" if x["pendentes"] else "") for x in conv}
esc = st.selectbox("Cliente", ids, format_func=rot.get, key="sup_cli")
for m in suporte.mensagens(ENG, esc):
    quem = "user" if m["autor"] == "cliente" else "assistant"
    with st.chat_message(quem, avatar="🙂" if quem == "user" else "🚐"):
        st.markdown(_ui.sem_formula(_ui.esc(m["texto"])))
        st.caption(m["criado_em"].astimezone(TZ).strftime("%d/%m %H:%M"))
resp = st.chat_input("Responder pelo app…")
if resp:
    suporte.responder_pelo_app(ENG, esc, resp, u["email"])
    st.rerun()
