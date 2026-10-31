"""Minha empresa: dados do gestor, Pix e vencimento padrão das mensalidades."""
import streamlit as st

from core import auth, repo
from core import contrato as ct
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

st.divider()
st.subheader("Contrato")
st.caption("Os responsáveis leem, preenchem os dados deles (aluno, escola, CPF, telefone, endereço, local) e assinam "
           "pelo app. Você contra-assina em **Alunos e responsáveis → Contratos**. Mudanças aqui valem para os "
           "próximos contratos — os já assinados não mudam.")
emp = repo.empresa(c["id"])
with st.form("contrato_modelo"):
    a, b, cc = st.columns([2, 1, 1])
    razao = a.text_input("Nome da contratada no contrato", value=emp.get("razao_social") or c["nome"],
                         help="Razão social ou nome fantasia, como deve sair no contrato.")
    cnpj = b.text_input("CNPJ", value=emp.get("cnpj") or "", placeholder="00.000.000/0001-00")
    cidade = cc.text_input("Cidade (local)", value=emp.get("cidade") or "", placeholder="São Paulo")
    clausulas = st.text_area("Cláusulas 1 a 7", value=ct.clausulas(emp), height=380,
                             help="A cláusula 8 (dados do aluno e do responsável) e as assinaturas o app monta sozinho.")
    x1, x2 = st.columns(2)
    salvar = x1.form_submit_button("Salvar contrato", type="primary")
    padrao = x2.form_submit_button("Voltar às cláusulas padrão")
if salvar or padrao:
    txt = None if padrao or clausulas.strip() == ct.CLAUSULAS_PADRAO.strip() else clausulas.strip()
    repo.atualizar_dados_contrato(c["id"], dict(razao_social=razao.strip() or None, cnpj=cnpj.strip() or None,
                                                cidade=cidade.strip() or None, contrato_clausulas=txt))
    st.toast("Contrato salvo.")
    st.rerun()
with st.expander("Ver como o responsável vai ver"):
    st.markdown(f"**{ct.TITULO}**")
    st.markdown(ct.preambulo(emp))
    st.text(ct.clausulas(emp))
