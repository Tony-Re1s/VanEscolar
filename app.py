"""Pequenos a Bordo — ponto de entrada.

Rodar local:  streamlit run app.py
"""
import streamlit as st

from core import auth, db
from telas import _ui

from pathlib import Path

_ST = Path(__file__).parent / "static"
st.set_page_config(page_title="Pequenos a Bordo", page_icon=str(_ST / "favicon.png"), layout="wide",
                   initial_sidebar_state="auto")
_ui.css()
st.logo(str(_ST / "logo.svg"), size="large", icon_image=str(_ST / "van.svg"))

db.migrar(db.banco_ativo(), db.versao_schema())
PRIVACIDADE = st.Page("telas/privacidade.py", title="Privacidade", icon=":material/shield_lock:")
TERMOS = st.Page("telas/termos.py", title="Termos de uso", icon=":material/gavel:")

if st.query_params.get("indicacao"):          # link "Indique e ganhe": guarda o código para o cadastro
    st.session_state["_indicacao"] = str(st.query_params["indicacao"]).strip().upper()[:20]

usuario = auth.usuario_logado()
if usuario is None:
    # visitante: página inicial (com o botão de entrar), privacidade e termos — sem login
    nav = st.navigation([st.Page("telas/inicio.py", title="Início", icon=":material/home:", default=True),
                         PRIVACIDADE, TERMOS], position="top")
    nav.run()
    st.stop()

if st.session_state.pop("_recarregar_perfil", False):
    auth.perfil(usuario)

cond = usuario.get("condutor")          # empresa da qual a pessoa é gestora
vans_mot = usuario.get("vans_motorista") or []   # vans que a pessoa dirige (de qualquer empresa)
if cond and not cond.get("ativo", True):
    st.error("O cadastro da sua empresa está desativado. Fale com o administrador do Pequenos a Bordo.")
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
        st.Page("telas/vans.py", title="Vans e motoristas", icon=":material/airport_shuttle:"),
        st.Page("telas/escolas.py", title="Escolas", icon=":material/school:"),
        st.Page("telas/meu_cadastro.py", title="Minha empresa", icon=":material/storefront:"),
        st.Page("telas/meu_plano.py", title="Meu plano", icon=":material/workspace_premium:"),
        st.Page("telas/indicacao.py", title="Indique e ganhe", icon=":material/redeem:"),
    ]
elif vans_mot:   # motorista contratado: só a(s) van(s) dele
    paginas["Minha van"] = [
        st.Page("telas/chamada.py", title="Rota e chamada", icon=":material/fact_check:", default=True),
        st.Page("telas/motorista_alunos.py", title="Meus alunos", icon=":material/groups:"),
    ]
if usuario.get("filhos"):
    paginas.setdefault("Família", []).append(
        st.Page("telas/pais.py", title="Meus filhos", icon=":material/family_restroom:",
                default=not cond and not vans_mot))
if usuario.get("admin"):
    paginas["Administração"] = [st.Page("telas/admin.py", title="Assinantes", icon=":material/admin_panel_settings:"),
                                st.Page("telas/promocoes.py", title="Promoções", icon=":material/sell:"),
                                st.Page("telas/banco.py", title="Banco e backup", icon=":material/database:")]
if not cond and not vans_mot and not usuario.get("filhos"):
    paginas.setdefault("Começar", []).append(
        st.Page("telas/boas_vindas.py", title="Criar minha empresa", icon=":material/rocket_launch:",
                default=not usuario.get("filhos") and not vans_mot))

paginas["Sobre"] = [PRIVACIDADE, TERMOS]

nav = st.navigation(paginas, expanded=True)
if st.session_state.get("_boas_vindas_msg"):
    st.toast(st.session_state.pop("_boas_vindas_msg"), icon="🎉")

with st.sidebar:
    st.markdown(f"**{_ui.esc(usuario.get('nome') or usuario['email'])}**  \n"
                f"<span class='ve-sub'>{_ui.esc(usuario['email'])}</span>", unsafe_allow_html=True)
    if cond:
        st.caption(f"🏢 {cond['nome']} · gestor")
    for v in vans_mot:
        st.caption(f"🚐 {v['nome']} · {v.get('placa') or 'sem placa'}" + ("" if cond else f" · {v['empresa']}"))
    st.button("Sair", icon=":material/logout:", on_click=auth.sair, width="stretch")

nav.run()
