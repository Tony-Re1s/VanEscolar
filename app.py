"""Turminha a Bordo — ponto de entrada.

Rodar local:  streamlit run app.py
"""
import importlib
import sys
from pathlib import Path

import streamlit as st


def _recarregar_codigo_novo():
    """O Streamlit Cloud atualiza os arquivos a cada publicação, mas guarda na memória os módulos já importados
    (core/*, telas/_ui). Recarrega os que mudaram desde a última execução — assim não precisa de Reboot."""
    for nome in ("core.fmt", "core.db", "core.planos", "core.contrato", "core.cobranca", "core.asaas", "core.repo",
                 "core.cobranca_pais", "core.comissao", "core.demo", "core.suporte", "core.mensagens",
                 "core.backup", "core.auth", "telas._ui"):
        m = sys.modules.get(nome)
        arq = getattr(m, "__file__", None)
        if not arq:
            continue
        mtime = Path(arq).stat().st_mtime
        if getattr(m, "_mtime", None) != mtime:
            importlib.reload(m)
            m._mtime = mtime


_recarregar_codigo_novo()

from core import auth, db  # noqa: E402
from telas import _ui  # noqa: E402

_ST = Path(__file__).parent / "static"
st.set_page_config(page_title="Turminha a Bordo", page_icon=str(_ST / "favicon.png"), layout="wide",
                   initial_sidebar_state="auto")
_ui.css()
st.logo(str(_ST / "logo.svg"), size="large", icon_image=str(_ST / "van.svg"))

db.migrar(db.banco_ativo(), db.versao_schema())
if st.query_params.get("contrato"):     # link do contrato assinado (WhatsApp/e-mail) — baixa sem login
    st.navigation([st.Page("telas/contrato_link.py", title="Contrato", icon=":material/description:")],
                  position="hidden").run()
    st.stop()

if st.query_params.get("van"):          # link "ver a van no mapa" que os pais recebem — abre sem login
    st.navigation([st.Page("telas/van_mapa.py", title="Onde está a van", icon=":material/location_on:")],
                  position="hidden").run()
    st.stop()

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

if not st.session_state.get("_comissao_ok"):     # 1x por sessão (e no máx. 1x por dia no banco)
    st.session_state["_comissao_ok"] = True
    try:
        from core import comissao as _com
        from core.fmt import hoje as _hoje
        _com.atualizar_todos(_hoje())
    except Exception:  # noqa: BLE001 — nunca atrapalha a entrada
        pass

cond = usuario.get("condutor")          # empresa da qual a pessoa é gestora
vans_mot = usuario.get("vans_motorista") or []   # vans que a pessoa dirige (de qualquer empresa)
if cond and not cond.get("ativo", True):
    st.error("O cadastro da sua empresa está desativado. Fale com o administrador do Turminha a Bordo.")
    st.button("Sair", on_click=auth.sair)
    st.stop()

paginas: dict[str, list] = {}
from core import planos as _plp  # noqa: E402
from core.fmt import hoje as _hjp  # noqa: E402
EM_PAUSA = bool(cond) and _plp.em_pausa(cond, _hjp())     # pausa de férias: rota e chamada ficam de fora
if cond and usuario.get("bloqueado"):
    # assinatura/degustação venceu: o gestor só vê a tela do plano para pagar (nada foi apagado)
    paginas["Assinatura"] = [st.Page("telas/meu_plano.py", title="Meu plano", icon=":material/workspace_premium:",
                                     default=True)]
elif cond and (cond.get("modo") or "completo") == "facil":
    # modo fácil: só o essencial — os dados são os mesmos do modo completo
    paginas["Modo fácil"] = ([] if EM_PAUSA else [
        st.Page("telas/facil_rota.py", title="Rota", icon=":material/airport_shuttle:", default=True)]) + [
        st.Page("telas/facil_alunos.py", title="Alunos", icon=":material/groups:", default=EM_PAUSA),
        st.Page("telas/mensalidades.py", title="Mensalidades", icon=":material/payments:"),
    ]
    paginas["Conta"] = [
        st.Page("telas/meu_cadastro.py", title="Minha empresa", icon=":material/storefront:"),
        st.Page("telas/meu_plano.py", title="Meu plano", icon=":material/workspace_premium:"),
        st.Page("telas/indicacao.py", title="Indique e ganhe", icon=":material/redeem:"),
    ]
elif cond:
    paginas["Dia a dia"] = [st.Page("telas/hoje.py", title="Hoje", icon=":material/today:", default=True)] + (
        [] if EM_PAUSA else [st.Page("telas/chamada.py", title="Rota e chamada", icon=":material/fact_check:")])
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
if cond and usuario.get("admin") and any(str(v["condutor_id"]) == str(cond["id"]) for v in vans_mot):
    # admin testando: é motorista de uma van da própria empresa (dados de demonstração) — vê a tela do motorista
    paginas["Ver como"] = [st.Page("telas/motorista_alunos.py", title="Motorista: meus alunos",
                                   icon=":material/badge:")]
if usuario.get("filhos"):
    paginas.setdefault("Família", []).append(
        st.Page("telas/pais.py", title="Meus filhos", icon=":material/family_restroom:",
                default=not cond and not vans_mot))
if usuario.get("admin"):
    paginas["Administração"] = [st.Page("telas/admin.py", title="Assinantes", icon=":material/admin_panel_settings:"),
                                st.Page("telas/promocoes.py", title="Promoções", icon=":material/sell:"),
                                st.Page("telas/banco.py", title="Banco e backup", icon=":material/database:")]
if not cond and not vans_mot and not usuario.get("filhos") and usuario.get("bloqueios"):
    paginas.setdefault("Aviso", []).append(
        st.Page("telas/bloqueado.py", title="Acesso suspenso", icon=":material/lock:", default=True))
elif not cond and not vans_mot and not usuario.get("filhos"):
    paginas.setdefault("Começar", []).append(
        st.Page("telas/boas_vindas.py", title="Criar minha empresa", icon=":material/rocket_launch:",
                default=not usuario.get("filhos") and not vans_mot))

# Fale conosco (assinante) — as respostas dadas no Telegram são buscadas de tempos em tempos
if cond and not usuario.get("bloqueado"):
    from telas import _ui as _uix  # noqa: E402
    _uix.sincronizar_suporte(intervalo=120)
    try:
        from core import suporte as _sup
        _novas = _sup.nao_lidas_cliente(_uix.motor(), cond["id"])
    except Exception:  # noqa: BLE001
        _novas = 0
    _grupo_fc = "Conta" if "Conta" in paginas else "Cadastros"
    paginas.setdefault(_grupo_fc, []).append(
        st.Page("telas/fale_conosco.py", title=f"Fale conosco ({_novas} nova{'s' if _novas > 1 else ''})"
                if _novas else "Fale conosco", icon=":material/support_agent:", url_path="fale_conosco"))
if usuario.get("admin"):
    paginas["Administração"].append(st.Page("telas/suporte_admin.py", title="Suporte", icon=":material/forum:"))

# parceiro Exclusivo (divulgador): canal com textos prontos, vagas VIP ao vivo e comissão
from core import planos as _pl  # noqa: E402
from core.fmt import hoje as _hj  # noqa: E402
DIVULGADOR = st.Page("telas/divulgador.py", title="Canal do divulgador", icon=":material/campaign:")
if cond and not usuario.get("bloqueado") and _pl.eh_exclusivo(cond, _hj()):
    grupo = "Conta" if "Conta" in paginas else "Cadastros"
    # no lugar do "Indique e ganhe": o prêmio do Exclusivo é a comissão (não ganha meses grátis)
    paginas[grupo] = [p for p in paginas.get(grupo, []) if p.title != "Indique e ganhe"] + [DIVULGADOR]
elif usuario.get("admin"):
    paginas["Administração"].append(DIVULGADOR)

paginas["Sobre"] = [PRIVACIDADE, TERMOS]

nav = st.navigation(paginas, expanded=True)

if cond and not usuario.get("bloqueado"):
    # botão no topo: modo fácil × completo (só muda o que aparece; os dados são os mesmos)
    _, topo = st.columns([3, 2])
    modo_atual = cond.get("modo") or "completo"
    escolhido = topo.segmented_control("Modo", ["facil", "completo"], default=modo_atual, key="modo_app",
                                       format_func={"facil": "Modo fácil", "completo": "Modo completo"}.get,
                                       label_visibility="collapsed", width="stretch")
    if escolhido and escolhido != modo_atual:
        from core import repo as _repo
        _repo.definir_modo(cond["id"], escolhido)
        cond["modo"] = escolhido
        st.rerun()
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
