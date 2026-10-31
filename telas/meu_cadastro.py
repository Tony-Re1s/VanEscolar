"""Dados do condutor e da van."""
import streamlit as st

from core import auth, repo
from telas._ui import exigir_condutor

c = exigir_condutor()
st.title("Meu cadastro e van")

with st.form("cadastro"):
    nome = st.text_input("Nome / nome do transporte *", value=c["nome"])
    c1, c2 = st.columns(2)
    telefone = c1.text_input("WhatsApp", value=c.get("telefone") or "")
    cnh = c2.text_input("CNH", value=c.get("cnh") or "")
    c3, c4, c5 = st.columns(3)
    veiculo = c3.text_input("Veículo", value=c.get("veiculo") or "")
    placa = c4.text_input("Placa", value=c.get("placa") or "")
    capacidade = c5.number_input("Lugares", 1, 60, int(c.get("capacidade") or 15))
    c6, c7 = st.columns(2)
    chave_pix = c6.text_input("Chave Pix", value=c.get("chave_pix") or "",
                              help="Aparece para os pais na área da família e na mensagem de cobrança.")
    dia = c7.number_input("Vencimento padrão (dia)", 1, 28, int(c.get("dia_vencimento") or 10),
                          help="Vale para alunos sem dia próprio. Mensalidades já geradas não mudam.")
    ok = st.form_submit_button("Salvar", type="primary")

if ok:
    if not nome.strip():
        st.error("Preencha o nome.")
        st.stop()
    repo.atualizar_condutor(c["id"], dict(nome=nome.strip(), telefone=telefone or None, cnh=cnh or None,
                                          veiculo=veiculo or None, placa=placa.upper() or None,
                                          capacidade=int(capacidade), chave_pix=chave_pix or None,
                                          dia_vencimento=int(dia)))
    auth.perfil(st.session_state["usuario"])
    st.success("Salvo.")
    st.rerun()
