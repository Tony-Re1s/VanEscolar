"""VanEscolar — ponto de entrada.

Rodar local:  streamlit run app.py
"""
import streamlit as st

from core import auth, db
from telas import _ui

st.set_page_config(page_title="VanEscolar", page_icon="🚐", layout="wide", initial_sidebar_state="auto")
_ui.css()

db.migrar()
usuario = auth.exigir_login()
if st.session_state.pop("_recarregar_perfil", False):
    auth.perfil(usuario)

cond = usuario.get("condutor")
if cond and not cond.get("ativo", True):
    st.error("O seu cadastro de condutor está desativado. Fale com o administrador do VanEscolar.")
    st.button("Sair", on_click=auth.sair)
    st.stop()

paginas: dict[str, list] = {}
if cond:
    paginas["Dia a dia"] = [
        st.Page("telas/hoje.py", title="Hoje", icon=":material/today:", default=True),
        st.Page("telas/chamada.py", title="Rota e chamada", icon=":material/fact_check:"),
    ]
    paginas["Dinheiro"] = [
        st.Page("telas/mensalidades.py", title="Mensalidades", icon=":material/payments:"),
        st.Page("telas/financeiro.py", title="Financeiro", icon=":material/monitoring:"),
    ]
    paginas["Cadastros"] = [
        st.Page("telas/alunos.py", title="Alunos e responsáveis", icon=":material/groups:"),
        st.Page("telas/escolas.py", title="Escolas", icon=":material/school:"),
        st.Page("telas/meu_cadastro.py", title="Meu cadastro e van", icon=":material/airport_shuttle:"),
    ]
if usuario.get("filhos"):
    paginas.setdefault("Família", []).append(
        st.Page("telas/pais.py", title="Meus filhos", icon=":material/family_restroom:", default=not cond))
if usuario.get("admin"):
    paginas["Administração"] = [st.Page("telas/admin.py", title="Condutores", icon=":material/admin_panel_settings:")]
if not cond:
    paginas.setdefault("Começar", []).append(
        st.Page("telas/boas_vindas.py", title="Sou condutor", icon=":material/rocket_launch:",
                default=not usuario.get("filhos")))

nav = st.navigation(paginas, expanded=True)

with st.sidebar:
    st.markdown(f"**{_ui.esc(usuario.get('nome') or usuario['email'])}**  \n"
                f"<span class='ve-sub'>{_ui.esc(usuario['email'])}</span>", unsafe_allow_html=True)
    if cond:
        st.caption(f"🚐 {cond.get('veiculo') or 'Van'} · {cond.get('placa') or 'sem placa'}")
    st.button("Sair", icon=":material/logout:", on_click=auth.sair, use_container_width=True)

nav.run()
