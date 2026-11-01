"""Motorista ou responsável de uma empresa cuja assinatura venceu: acesso suspenso até o gestor regularizar."""
import streamlit as st

from telas import _ui

u = st.session_state["usuario"]
st.title("Acesso suspenso")
empresas = ", ".join(u.get("bloqueios") or [])
st.markdown(f"<div class='ve-faixa'>🔒 O Turminha a Bordo de <b>{_ui.esc(empresas)}</b> está pausado ou com a "
            "assinatura vencida, por isso a rota e a chamada estão indisponíveis no momento.</div>",
            unsafe_allow_html=True)
st.markdown("Fale com o gestor do transporte: assim que ele regularizar, tudo volta a aparecer aqui — "
            "nenhum dado foi apagado.")
st.caption(f"Dúvidas sobre o app? Escreva para [{_ui.EMAIL_CONTATO}]({_ui.link_contato()}).")
