"""Administração: empresas (gestores) cadastradas no app."""
import streamlit as st

from core import repo
from core.fmt import data_br

if not st.session_state["usuario"].get("admin"):
    st.stop()

st.title("Empresas")
df = repo.empresas_todas()
if df.empty:
    st.info("Nenhuma empresa cadastrada ainda.")
    st.stop()

st.caption(f"{len(df)} empresa(s) · {int(df['vans'].sum())} van(s) · {int(df['alunos'].sum())} alunos ativos no total")
for r in df.itertuples():
    with st.container(border=True):
        a, b = st.columns([4, 1])
        a.markdown(f"**{r.nome}** {'' if r.ativo else '· 🔴 desativada'}  \n"
                   f"<span class='ve-sub'>{r.email} · {r.telefone or 'sem telefone'} · {r.vans} van(s) · "
                   f"{r.alunos} aluno(s) · desde {data_br(r.desde)}</span>", unsafe_allow_html=True)
        if b.button("Desativar" if r.ativo else "Reativar", key=f"at_{r.id}", use_container_width=True):
            repo.ativar_empresa(r.id, not r.ativo)
            st.rerun()
