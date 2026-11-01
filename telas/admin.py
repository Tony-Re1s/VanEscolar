"""Administração: empresas (gestores) cadastradas no app."""
import streamlit as st

from core import planos as pl
from core import repo
from core.fmt import data_br, hoje, somar_meses

if not st.session_state["usuario"].get("admin"):
    st.stop()

st.title("Empresas")
df = repo.empresas_todas()
if df.empty:
    st.info("Nenhuma empresa cadastrada ainda.")
    st.stop()

st.caption(f"{len(df)} empresa(s) · {int(df['vans'].sum())} van(s) · {int(df['alunos'].sum())} alunos ativos no total")
for r in df.itertuples():
    with st.container(border=True, key=f"card_{r.id}"):
        a, b = st.columns([4, 1])
        a.markdown(f"**{r.nome}** {'' if r.ativo else '· 🔴 desativada'}  \n"
                   f"<span class='ve-sub'>{r.email} · {r.telefone or 'sem telefone'} · {r.vans} van(s) · "
                   f"{r.alunos} aluno(s) · desde {data_br(r.desde)}</span>", unsafe_allow_html=True)
        if b.button("Desativar" if r.ativo else "Reativar", key=f"at_{r.id}", width="stretch"):
            repo.ativar_empresa(r.id, not r.ativo)
            st.rerun()
        emp = repo.empresa(r.id)
        vig = pl.plano_da_empresa(emp, hoje())
        with st.popover(f"Plano: {pl.PLANOS[vig]['nome']}" + (f" até {data_br(emp['plano_ate'])}"
                        if emp.get("plano_ate") and vig != "gratis" else ""), icon=":material/workspace_premium:"):
            with st.form(f"plano_{r.id}"):
                novo = st.selectbox("Plano", pl.ORDEM, index=pl.ORDEM.index(emp.get("plano") or "gratis"),
                                    format_func=lambda k: f"{pl.PLANOS[k]['nome']} ({pl.preco_txt(pl.PLANOS[k])})")
                ate = st.date_input("Válido até", value=emp.get("plano_ate") or somar_meses(hoje(), 1),
                                    format="DD/MM/YYYY", help="Ignorado no plano Grátis.")
                if st.form_submit_button("Salvar plano", type="primary"):
                    repo.definir_plano(r.id, novo, None if novo == "gratis" else ate)
                    st.rerun()
