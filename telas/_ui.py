"""Visual do app: CSS, cartões de indicador e helpers de tela (pensado primeiro para o celular)."""
from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
:root { --ve-amarelo:#F5B700; --ve-azul:#1D3557; --ve-verde:#2A9D8F; --ve-vermelho:#D62839; --ve-cinza:#6B7280; }
.block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1100px;}
.ve-logo {width: 112px; height: 112px; line-height: 1;}
.ve-logo svg {width: 100%; height: 100%; animation: ve-anda 1.6s ease-in-out infinite; transform-origin: 50% 85%;}
@keyframes ve-anda {0%,100% {transform: translateY(0) rotate(0deg);} 25% {transform: translateY(-3px) rotate(-1.5deg);}
                    50% {transform: translateY(0) rotate(0deg);} 75% {transform: translateY(-2px) rotate(1deg);}}
@media (prefers-reduced-motion: reduce) {.ve-logo svg {animation: none;}}
.ve-kpis {display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:10px; margin: .2rem 0 1rem;}
.ve-kpi {border-radius:14px; padding:12px 14px; background: var(--secondary-background-color);
         border:1px solid rgba(128,128,128,.18);}
.ve-kpi .l {font-size:.78rem; color: var(--ve-cinza); text-transform: uppercase; letter-spacing:.03em;}
.ve-kpi .v {font-size:1.35rem; font-weight:700; margin-top:2px; white-space:nowrap;}
.ve-kpi .s {font-size:.78rem; color: var(--ve-cinza);}
.ve-kpi.destaque {background: linear-gradient(135deg, #1D3557 0%, #2E5C8A 100%); color:#fff; border:none;}
.ve-kpi.destaque .l, .ve-kpi.destaque .s {color: rgba(255,255,255,.8);}
.ve-tag {display:inline-block; padding:2px 9px; border-radius:99px; font-size:.75rem; font-weight:600;}
.ve-pago {background:#DCFCE7; color:#166534;} .ve-vencido {background:#FEE2E2; color:#991B1B;}
.ve-vence_logo {background:#FEF3C7; color:#92400E;} .ve-aberto {background:#E5E7EB; color:#374151;}
.ve-embarcou {background:#DBEAFE; color:#1E40AF;} .ve-desembarcou {background:#DCFCE7; color:#166534;}
.ve-faltou {background:#FEE2E2; color:#991B1B;} .ve-aviso {background:#FEF3C7; color:#92400E;}
.ve-cart {border-radius:18px; padding:18px 20px; color:#1D3557; max-width:420px;
          background: linear-gradient(135deg, #FFD23F 0%, #F5B700 100%); box-shadow: 0 6px 18px rgba(0,0,0,.12);}
.ve-cart h3 {margin:0 0 4px; color:#1D3557;} .ve-cart .r {font-size:.85rem; margin-top:6px;}
.ve-cart .t {font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; opacity:.75;}
.ve-linha {display:flex; justify-content:space-between; gap:8px; align-items:center;}
.ve-sub {color: var(--ve-cinza); font-size:.85rem;}
/* linhas de ação (st.container(key="linha_…")): botões sempre lado a lado, inclusive no celular */
[class*="st-key-linha"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: .4rem !important;}
[class*="st-key-linha"] [data-testid="stColumn"] {min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;}
/* linhas proporcionais (key="lp_…"): também não quebram no celular, mas mantêm as larguras */
[class*="st-key-lp_"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: .5rem !important;}
[class*="st-key-lp_"] [data-testid="stColumn"] {min-width: 0 !important;}
[class*="st-key-linha"] button, [class*="st-key-linha"] a {padding-left: .3rem !important; padding-right: .3rem !important;}
@media (max-width: 640px) {
  .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: 1rem;}
  .ve-kpis {grid-template-columns: repeat(2, minmax(0,1fr));}
  .ve-kpi .v {font-size:1.1rem;}
  h1 {font-size: 1.6rem !important;}
}
</style>
"""

ROTULO_MENS = {"pago": "Pago", "vencido": "Vencido", "vence_logo": "Vence em breve", "aberto": "Em aberto"}
ROTULO_CHAM = {"embarcou": "Embarcou", "desembarcou": "Desembarcou", "faltou": "Faltou"}


def esc(t) -> str:
    return html.escape("" if t is None else str(t))


def css():
    st.markdown(CSS, unsafe_allow_html=True)


def kpis(itens: list[tuple], destaque: int | None = 0):
    """itens: (rótulo, valor, subtítulo opcional)."""
    partes = []
    for i, it in enumerate(itens):
        rot, val, sub = (list(it) + [""])[:3]
        cls = "ve-kpi destaque" if i == destaque else "ve-kpi"
        partes.append(f"<div class='{cls}'><div class='l'>{esc(rot)}</div><div class='v'>{esc(val)}</div>"
                      f"<div class='s'>{esc(sub)}</div></div>")
    st.markdown(f"<div class='ve-kpis'>{''.join(partes)}</div>", unsafe_allow_html=True)


def tag(chave: str, texto: str | None = None) -> str:
    return f"<span class='ve-tag ve-{esc(chave)}'>{esc(texto or chave)}</span>"


def vans_acessiveis(u: dict) -> list[dict]:
    """Vans que a pessoa pode operar na rota/chamada: todas da empresa dela (gestor) + as que ela dirige.
    Cada item: id, nome, placa, cid (empresa dona), empresa, gestor (True se ela é a gestora dessa empresa)."""
    from core import repo
    out, vistos = [], set()
    c = u.get("condutor")
    if c:
        for v in repo.vans(c["id"]).itertuples():
            out.append(dict(id=str(v.id), nome=v.nome, placa=v.placa, cid=c["id"], empresa=c["nome"], gestor=True,
                            minha=(v.motorista_email or "") == u["email"]))
            vistos.add(str(v.id))
    for v in u.get("vans_motorista") or []:
        if str(v["id"]) not in vistos:
            out.append(dict(id=str(v["id"]), nome=v["nome"], placa=v.get("placa"), cid=v["condutor_id"],
                            empresa=v["empresa"], gestor=False, minha=True))
    out.sort(key=lambda x: (not x["minha"], x["empresa"], x["nome"]))   # a que a pessoa dirige vem primeiro
    return out


def rotulo_van(v: dict, varias_empresas=False) -> str:
    base = v["nome"] + (f" · {v['placa']}" if v.get("placa") else "")
    return base + (f" ({v['empresa']})" if varias_empresas else "")


def filtro_van(cid, chave: str, label="Van") -> str | None:
    """Selectbox 'Todas as vans' + vans da empresa (só aparece se houver mais de uma). Devolve van_id ou None."""
    from core import repo
    vs = repo.vans(cid)
    if len(vs) <= 1:
        return None
    ids = [None] + [str(x) for x in vs["id"]]
    nomes = {None: "Todas as vans"} | {str(r.id): r.nome for r in vs.itertuples()}
    return st.selectbox(label, ids, format_func=nomes.get, key=chave)


def exigir_condutor() -> dict:
    u = st.session_state.get("usuario") or {}
    c = u.get("condutor")
    if not c:
        st.warning("Esta tela é do condutor.")
        st.stop()
    return c
