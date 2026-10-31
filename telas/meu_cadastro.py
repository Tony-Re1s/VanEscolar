"""Minha empresa: dados do gestor, Pix e vencimento padrão das mensalidades."""
import streamlit as st

from core import auth, repo
from telas._ui import exigir_condutor

c = exigir_condutor()
st.title("Minha empresa")

with st.form("empresa"):
    nome = st.text_input("Nome / nome do transporte *", value=c["nome"])
    telefone = st.text_input("WhatsApp", value=c.get("telefone") or "")
    c1, c2 = st.columns(2)
    chave_pix = c1.text_input("Chave Pix", value=c.get("chave_pix") or "",
                              help="Aparece para os pais na área da família e na mensagem de cobrança.")
    dia = c2.number_input("Vencimento padrão (dia)", 1, 28, int(c.get("dia_vencimento") or 10),
                          help="Vale para alunos sem dia próprio. Mensalidades já geradas não mudam.")
    ok = st.form_submit_button("Salvar", type="primary")

if ok:
    if not nome.strip():
        st.error("Preencha o nome.")
        st.stop()
    repo.atualizar_empresa(c["id"], dict(nome=nome.strip(), telefone=telefone or None, chave_pix=chave_pix or None,
                                         dia_vencimento=int(dia)))
    auth.perfil(st.session_state["usuario"])
    st.success("Salvo.")
    st.rerun()

st.page_link("telas/vans.py", label="Vans e motoristas", icon=":material/airport_shuttle:")
