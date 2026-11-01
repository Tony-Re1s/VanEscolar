"""Fale conosco (assinante): chat com o suporte. As mensagens chegam no Telegram do administrador e as respostas
voltam para cá. Quem não assina fala por e-mail."""
import streamlit as st

from core import planos as pl, repo, suporte
from core.fmt import TZ, hoje
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
u = st.session_state["usuario"]
emp = repo.empresa(c["id"])
st.title("Fale conosco")

if not (u.get("admin") or pl.liberada(emp, hoje())):
    st.info("O chat com o suporte é para quem tem plano ativo. Fale com a gente por e-mail:",
            icon=":material/mail:")
    st.link_button(_ui.EMAIL_CONTATO, _ui.link_contato(), icon=":material/mail:")
    st.stop()

ENG = _ui.motor()
st.caption("Escreva sua dúvida, sugestão ou problema. A gente responde por aqui mesmo — normalmente no mesmo dia. "
           f"Se preferir, mande um e-mail para {_ui.EMAIL_CONTATO}.")


@st.fragment(run_every=15)
def _conversa():
    _ui.sincronizar_suporte(intervalo=10)
    msgs = suporte.mensagens(ENG, c["id"])
    if not msgs:
        st.markdown("<div class='ve-faixa'>👋 Olá! Como podemos ajudar?</div>", unsafe_allow_html=True)
    for m in msgs:
        quem = "user" if m["autor"] == "cliente" else "assistant"
        with st.chat_message(quem, avatar="🙂" if quem == "user" else "🚐"):
            st.markdown(_ui.sem_formula(_ui.esc(m["texto"])))
            st.caption(("Você" if quem == "user" else "Suporte Turminha a Bordo") + " · "
                       + m["criado_em"].astimezone(TZ).strftime("%d/%m %H:%M"))
    if any(m["autor"] == "suporte" and not m["lida"] for m in msgs):
        suporte.marcar_lidas_cliente(ENG, c["id"])


_conversa()

txt = st.chat_input("Escreva sua mensagem…", max_chars=2000)
if txt:
    p = pl.plano_da_empresa(emp, hoje())
    cab = (f"{emp['nome']} · {pl.catalogo().get(p, {}).get('nome', p or 'sem plano')} "
           f"({pl.TIPOS.get(pl.tipo_da_empresa(emp), '')}) · {u['email']}")
    if c.get("telefone"):
        cab += f" · {c['telefone']}"
    suporte.enviar_cliente(ENG, _ui.telegram(), c["id"], u["email"], txt, cab)
    st.rerun()
