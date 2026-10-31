"""Administração: condutores cadastrados no app."""
import streamlit as st

from core import repo
from core.fmt import data_br

if not st.session_state["usuario"].get("admin"):
    st.stop()

st.title("Condutores")
df = repo.condutores_todos()
if df.empty:
    st.info("Nenhum condutor cadastrado ainda.")
    st.stop()

st.caption(f"{len(df)} condutor(es) · {int(df['alunos'].sum())} alunos ativos no total")
for r in df.itertuples():
    with st.container(border=True):
        a, b = st.columns([4, 1])
        a.markdown(f"**{r.nome}** {'' if r.ativo else '· 🔴 desativado'}  \n"
                   f"<span class='ve-sub'>{r.email} · {r.telefone or 'sem telefone'} · {r.placa or 'sem placa'} · "
                   f"{r.alunos} aluno(s) · desde {data_br(r.desde)}</span>", unsafe_allow_html=True)
        if b.button("Desativar" if r.ativo else "Reativar", key=f"at_{r.id}", use_container_width=True):
            repo.ativar_condutor(r.id, not r.ativo)
            st.rerun()
