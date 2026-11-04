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

# respostas prontas: resolvem as dúvidas comuns na hora
from core.faq import FAQ  # noqa: E402
st.markdown("**Dúvidas rápidas** <span class='ve-sub'>— toque para ver a resposta na hora</span>",
            unsafe_allow_html=True)
tit = st.pills("Dúvidas rápidas", [f["titulo"] for f in FAQ], key="faq_sel", label_visibility="collapsed")
if tit:
    f = next(x for x in FAQ if x["titulo"] == tit)
    facil = (emp.get("modo") or "completo") == "facil"
    with st.container(border=True, key="card_faq"):
        st.markdown(f"**{tit}**")
        st.markdown(_ui.sem_formula(f["texto"].strip()))
        destino = f.get("pagina_facil") if facil and f.get("pagina_facil") else f.get("pagina")
        if destino:
            try:
                st.page_link(destino, label="Abrir essa tela", icon=":material/arrow_forward:")
            except Exception:  # noqa: BLE001 — tela que não existe neste modo/plano
                pass
        st.caption("Não resolveu? Escreva abaixo que a gente responde.")

st.divider()
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
    primeira = not any(m["autor"] == "cliente" for m in suporte.mensagens(ENG, c["id"]))
    suporte.enviar_cliente(ENG, _ui.telegram(), c["id"], u["email"], txt, cab)
    if primeira:
        from core import avisos_admin
        avisos_admin.primeira_mensagem(emp["nome"], cab, txt)
    st.rerun()
