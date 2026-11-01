"""Administração: painel de assinantes (empresas/gestores) — receita, vencimentos, cobrança e planos."""
from datetime import timedelta

import streamlit as st

from core import planos as pl
from core import repo
from core.fmt import brl, data_br, hoje, link_whats, somar_meses
from telas import _ui

if not st.session_state["usuario"].get("admin"):
    st.stop()

st.title("Assinantes")
df = repo.empresas_todas()
if df.empty:
    st.info("Nenhuma empresa cadastrada ainda.")
    st.stop()

HOJE = hoje()
AVISO_DIAS = 7

# situação de cada empresa
SIT = {"pago": ("pago", "Em dia"), "vence": ("vence_logo", "Vence logo"), "vencido": ("vencido", "Vencido"),
       "limite": ("aberto", "Grátis no limite"), "gratis": ("aberto", "Grátis"), "off": ("faltou", "Desativada")}


def _situacao(r) -> str:
    if not r["ativo"]:
        return "off"
    contratado = r["plano"] or "gratis"
    ate = r["plano_ate"]
    if contratado != "gratis":
        if ate and ate < HOJE:
            return "vencido"
        if ate and ate <= HOJE + timedelta(days=AVISO_DIAS):
            return "vence"
        return "pago"
    g = pl.PLANOS["gratis"]
    if r["vans"] >= g["vans"] or r["alunos"] >= g["alunos"] - 2:
        return "limite"
    return "gratis"


linhas = []
for r in df.to_dict("records"):
    r["sit"] = _situacao(r)
    r["vig"] = pl.plano_da_empresa(r, HOJE)
    linhas.append(r)

pagos = [r for r in linhas if r["sit"] in ("pago", "vence")]
receita = sum(pl.PLANOS[r["vig"]]["preco"] for r in pagos)
cont = {k: sum(1 for r in linhas if r["sit"] == k) for k in SIT}

_ui.kpis([("Receita por mês", brl(receita), f"{len(pagos)} assinante(s) pagante(s)"),
          ("Vencem em 7 dias", str(cont["vence"]), "renovar"),
          ("Vencidos", str(cont["vencido"]), "voltaram ao Grátis"),
          ("No Grátis", str(cont["gratis"] + cont["limite"]), f"{cont['limite']} perto do limite")])

por_plano = {k: sum(1 for r in linhas if r["vig"] == k and r["ativo"]) for k in pl.ORDEM}
st.markdown(" ".join(_ui.tag("pago" if k != "gratis" else "aberto", f"{pl.PLANOS[k]['nome']}: {n}")
                     for k, n in por_plano.items()) +
            f" <span class='ve-sub'>· {len(linhas)} empresa(s) · {int(df['vans'].sum())} van(s) · "
            f"{int(df['alunos'].sum())} alunos ativos</span>", unsafe_allow_html=True)

# filtros
FILTROS = {"Todos": None, "Vencem logo": {"vence"}, "Vencidos": {"vencido"}, "Pagantes": {"pago", "vence"},
           "Grátis no limite": {"limite"}, "Grátis": {"gratis", "limite"}, "Desativadas": {"off"}}
a, b = st.columns([3, 2])
filtro = a.segmented_control("Mostrar", list(FILTROS), default="Todos", label_visibility="collapsed") or "Todos"
busca = b.text_input("Buscar", placeholder="Buscar nome ou e-mail", label_visibility="collapsed").strip().lower()

ORDEM_SIT = {"vencido": 0, "vence": 1, "limite": 2, "pago": 3, "gratis": 4, "off": 5}
sel = [r for r in linhas
       if (FILTROS[filtro] is None or r["sit"] in FILTROS[filtro])
       and (not busca or busca in (r["nome"] or "").lower() or busca in (r["email"] or "").lower())]
sel.sort(key=lambda r: (ORDEM_SIT[r["sit"]], r["plano_ate"] or HOJE, r["nome"] or ""))
if not sel:
    st.info("Nenhuma empresa neste filtro.")


def _mensagem(r) -> str | None:
    primeiro = (r["nome"] or "").split(" ")[0]
    p = pl.PLANOS[r["plano"] or "gratis"]
    if r["sit"] == "vence":
        return (f"Olá, {primeiro}! Sua assinatura do plano {p['nome']} do Pequenos a Bordo vence em "
                f"{data_br(r['plano_ate'])}. Quer que eu envie o Pix de {pl.preco_txt(p)} para renovar? 🚐")
    if r["sit"] == "vencido":
        return (f"Olá, {primeiro}! Sua assinatura do plano {p['nome']} do Pequenos a Bordo venceu em "
                f"{data_br(r['plano_ate'])} e a conta voltou ao Grátis (nada foi apagado). Quer renovar por "
                f"{pl.preco_txt(p)}/mês? 🚐")
    if r["sit"] == "limite":
        return (f"Olá, {primeiro}! Vi que você já está usando bastante o Pequenos a Bordo 🚐 O plano Grátis vai até "
                f"1 van e 10 alunos. Com o Básico ({pl.preco_txt(pl.PLANOS['basico'])}/mês) os alunos ficam "
                f"ilimitados, e o Pro ({pl.preco_txt(pl.PLANOS['pro'])}/mês) vai até 3 vans. Posso te ajudar a assinar?")
    return None


for r in sel:
    chave, rotulo = SIT[r["sit"]]
    p = pl.PLANOS[r["plano"] or "gratis"]
    with st.container(border=True, key=f"card_{r['id']}"):
        ate = f" até {data_br(r['plano_ate'])}" if r["plano_ate"] and (r["plano"] or "gratis") != "gratis" else ""
        ultimo = f" · último acesso {data_br(r['ultimo_acesso'])}" if r.get("ultimo_acesso") else ""
        st.markdown(f"**{_ui.esc(r['nome'])}** {_ui.tag(chave, rotulo)} {_ui.tag('pago', p['nome'] + ate)}  \n"
                    f"<span class='ve-sub'>{_ui.esc(r['email'])} · {_ui.esc(r['telefone'] or 'sem telefone')} · "
                    f"{r['vans']} van(s) · {r['alunos']} aluno(s) · desde {data_br(r['desde'])}{ultimo}</span>",
                    unsafe_allow_html=True)
        c1, c2 = st.container(key=f"linha_a_{r['id']}").columns(2)
        c3, c4 = st.container(key=f"linha_b_{r['id']}").columns(2)
        msg = _mensagem(r)
        lk = link_whats(r["telefone"], msg) if msg else None
        if lk:
            c1.link_button("Cobrar" if r["sit"] in ("vence", "vencido") else "Oferecer plano", lk,
                           icon=":material/chat:", width="stretch")
        if (r["plano"] or "gratis") != "gratis" and r["ativo"]:
            base = max(r["plano_ate"] or HOJE, HOJE)
            if c2.button("+1 mês", key=f"mes_{r['id']}", icon=":material/payments:", width="stretch",
                         help=f"Renova o {p['nome']} até {data_br(somar_meses(base, 1))}"):
                repo.definir_plano(r["id"], r["plano"], somar_meses(base, 1))
                st.toast(f"{r['nome']}: {p['nome']} renovado até {data_br(somar_meses(base, 1))}.")
                st.rerun()
        with c3.popover("Plano", icon=":material/workspace_premium:", width="stretch"):
            with st.form(f"plano_{r['id']}"):
                novo = st.selectbox("Plano", pl.ORDEM, index=pl.ORDEM.index(r["plano"] or "gratis"),
                                    format_func=lambda k: f"{pl.PLANOS[k]['nome']} ({pl.preco_txt(pl.PLANOS[k])})")
                validade = st.date_input("Válido até", value=r["plano_ate"] or somar_meses(HOJE, 1),
                                         format="DD/MM/YYYY", help="Ignorado no plano Grátis.")
                if st.form_submit_button("Salvar plano", type="primary"):
                    repo.definir_plano(r["id"], novo, None if novo == "gratis" else validade)
                    st.rerun()
        if c4.button("Desativar" if r["ativo"] else "Reativar", key=f"at_{r['id']}", width="stretch",
                     icon=":material/block:" if r["ativo"] else ":material/check_circle:"):
            repo.ativar_empresa(r["id"], not r["ativo"])
            st.rerun()
