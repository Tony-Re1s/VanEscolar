"""Cadastro de escolas."""
import streamlit as st

from core import repo
from telas._ui import exigir_condutor

c = exigir_condutor()
st.title("Escolas")

df = repo.escolas(c["id"], so_ativas=False)
NOVA = "➕ Nova escola"
opcoes = [NOVA] + [f"{r.nome}{'' if r.ativo else ' (inativa)'}" for r in df.itertuples()]
escolha = st.selectbox("Escola", opcoes, index=0 if df.empty else 1)
e = None if escolha == NOVA else df.iloc[opcoes.index(escolha) - 1].to_dict()


def _h(v):
    return None if v is None or str(v) in ("NaT", "None", "nan") else v


with st.form("escola", clear_on_submit=e is None):
    nome = st.text_input("Nome *", value=(e or {}).get("nome", ""))
    endereco = st.text_input("Endereço", value=(e or {}).get("endereco") or "",
                             help="Usado no link da rota do Google Maps.")
    a, b = st.columns(2)
    telefone = a.text_input("Telefone", value=(e or {}).get("telefone") or "")
    ativo = b.toggle("Ativa", value=bool((e or {}).get("ativo", True)))
    a, b = st.columns(2)
    em = a.time_input("Entrada manhã", value=_h((e or {}).get("entrada_manha")), step=300)
    sm = b.time_input("Saída manhã", value=_h((e or {}).get("saida_manha")), step=300)
    a, b = st.columns(2)
    et = a.time_input("Entrada tarde", value=_h((e or {}).get("entrada_tarde")), step=300)
    stt = b.time_input("Saída tarde", value=_h((e or {}).get("saida_tarde")), step=300)
    ok = st.form_submit_button("Salvar", type="primary", width="stretch")

if ok:
    if not nome.strip():
        st.error("Preencha o nome.")
        st.stop()
    repo.salvar_escola(c["id"], dict(nome=nome.strip(), endereco=endereco or None, telefone=telefone or None,
                                     entrada_manha=em, saida_manha=sm, entrada_tarde=et, saida_tarde=stt,
                                     ativo=ativo), eid=(e or {}).get("id"))
    st.success("Escola salva.")
    st.rerun()

if not df.empty:
    st.divider()
    st.dataframe(df[["nome", "endereco", "telefone", "entrada_manha", "saida_manha", "entrada_tarde", "saida_tarde",
                     "ativo"]],
                 hide_index=True, width="stretch",
                 column_config={"nome": "Escola", "endereco": "Endereço", "telefone": "Telefone",
                                "entrada_manha": st.column_config.TimeColumn("Entr. manhã", format="HH:mm"),
                                "saida_manha": st.column_config.TimeColumn("Saída manhã", format="HH:mm"),
                                "entrada_tarde": st.column_config.TimeColumn("Entr. tarde", format="HH:mm"),
                                "saida_tarde": st.column_config.TimeColumn("Saída tarde", format="HH:mm"),
                                "ativo": "Ativa"})
