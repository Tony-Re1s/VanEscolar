"""Visual do app: CSS, cartões de indicador e helpers de tela (pensado primeiro para o celular)."""
from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
/* ===== paleta: verde Tiffany + azul bebê, texto azul-marinho, amarelo da van como acento ===== */
:root { --tif:#0ABAB5; --tif-esc:#0A9C97; --tif-claro:#E3F7F6; --bb:#89CFF0; --bb-claro:#EAF6FD;
        --ve-azul:#16324F; --ve-amarelo:#FFC928; --ve-verde:#0A9C97; --ve-vermelho:#E5484D; --ve-cinza:#5F7186;
        --sombra: 0 6px 22px rgba(22,50,79,.08); --sombra-forte: 0 10px 30px rgba(10,156,151,.22); }

/* fundo suave em degradê */
[data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(700px 300px at 95% -8%, rgba(10,186,181,.16), transparent 62%),
              radial-gradient(650px 280px at 0% -6%, rgba(137,207,240,.24), transparent 62%),
              linear-gradient(180deg, #FAFDFD 0%, #F3F9FB 100%) !important;
  background-attachment: fixed !important; }
[data-testid="stHeader"] {background: transparent !important;}
.block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1100px;}
h1 {font-weight: 800 !important; letter-spacing: -.02em; color: var(--ve-azul);}
h2, h3 {font-weight: 800 !important; color: var(--ve-azul);}

/* menu lateral */
[data-testid="stSidebar"] {border-right: 1px solid #E1F0EF; box-shadow: 4px 0 24px rgba(22,50,79,.04);}
[data-testid="stSidebarNavLink"] {border-radius: 999px !important; margin: 2px 6px; padding-left: 12px !important;}
[data-testid="stSidebarNavLink"][aria-current="page"], [data-testid="stSidebarNavLink"]:hover {
  background: var(--tif-claro) !important;}
[data-testid="stSidebarNavLink"][aria-current="page"] span {color: var(--tif-esc) !important; font-weight: 700;}

/* cartões (st.container(border=True), forms, expanders) */
[class*="st-key-card_"], div[data-testid="stForm"], [data-testid="stExpander"] details {
  background: #FFFFFF; border: 1px solid #E1F0EF !important; border-radius: 20px !important;
  box-shadow: var(--sombra); }
[data-testid="stExpander"] details summary {border-radius: 20px;}

/* botões em pílula */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button,
[data-testid="stPopover"] button {
  border-radius: 999px !important; font-weight: 700 !important; transition: transform .08s, box-shadow .15s;}
.stButton > button:hover, .stLinkButton > a:hover, .stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {transform: translateY(-1px);}
button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, #0ABAB5 0%, #0A9C97 55%, #3FA9D6 140%) !important; border: none !important;
  color: #fff !important; box-shadow: var(--sombra-forte) !important;}
button[data-testid="stBaseButton-secondary"], .stLinkButton > a, button[data-testid="stBaseButton-secondaryFormSubmit"] {
  background: #FFFFFF !important; border: 1.5px solid #CDEBEA !important; color: var(--ve-azul) !important;}
button[data-testid="stBaseButton-secondary"]:hover, .stLinkButton > a:hover {border-color: var(--tif) !important;
  color: var(--tif-esc) !important;}

/* abas e seletores em pílula */
[data-testid="stTabs"] [role="tablist"] {gap: 6px; background: rgba(255,255,255,.85); padding: 5px;
  border-radius: 999px; box-shadow: var(--sombra); width: fit-content; max-width: 100%; overflow-x: auto;
  border: 1px solid #E1F0EF;}
[data-testid="stTabs"] [role="tab"] {border-radius: 999px !important; padding: 6px 16px !important;
  height: auto !important; border: none !important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {background: var(--tif-esc) !important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] * {color: #fff !important; font-weight: 700;}
[data-testid="stTabs"] [role="tab"]::after, [data-testid="stTabs"] [role="tab"]::before {display: none !important;}
[data-testid="stTabs"] [role="tab"] {box-shadow: none !important; border-bottom: none !important;}
[data-testid="stButtonGroup"] button {border-radius: 999px !important; margin-right: 6px !important;
  border: 1.5px solid #CDEBEA !important; background: #fff !important;}
[data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[kind*="Active"] {
  background: var(--tif-esc) !important; border-color: var(--tif-esc) !important; color: #fff !important;}
[data-testid="stButtonGroup"] button[aria-checked="true"] p, [data-testid="stButtonGroup"] button[kind*="Active"] p {
  color: #fff !important;}

/* campos */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {background: #FFFFFF !important;
  border-radius: 14px !important;}
[data-testid="stAlert"] {border-radius: 16px; box-shadow: var(--sombra);}
[data-testid="stDataFrame"] {border-radius: 16px; overflow: hidden; box-shadow: var(--sombra); background: #fff;}

/* logo animado da tela de login */
.ve-logo {width: 112px; height: 112px; line-height: 1; filter: drop-shadow(0 10px 18px rgba(10,156,151,.25));}
.ve-logo svg {width: 100%; height: 100%; animation: ve-anda 1.6s ease-in-out infinite; transform-origin: 50% 85%;}
@keyframes ve-anda {0%,100% {transform: translateY(0) rotate(0deg);} 25% {transform: translateY(-3px) rotate(-1.5deg);}
                    50% {transform: translateY(0) rotate(0deg);} 75% {transform: translateY(-2px) rotate(1deg);}}
@media (prefers-reduced-motion: reduce) {.ve-logo svg {animation: none;}}

/* indicadores */
.ve-kpis {display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:12px; margin: .3rem 0 1.1rem;}
.ve-kpi {border-radius:20px; padding:14px 16px; background:#FFFFFF; border:1px solid #E1F0EF; box-shadow: var(--sombra);}
.ve-kpi .l {font-size:.74rem; color: var(--ve-cinza); text-transform: uppercase; letter-spacing:.05em; font-weight:700;}
.ve-kpi .v {font-size:1.4rem; font-weight:800; margin-top:3px; white-space:nowrap; color: var(--ve-azul);}
.ve-kpi .s {font-size:.78rem; color: var(--ve-cinza);}
.ve-kpi.destaque {background: linear-gradient(135deg, #0ABAB5 0%, #0A9C97 45%, #5DB8E6 120%); color:#fff; border:none;
  box-shadow: var(--sombra-forte);}
.ve-kpi.destaque .l, .ve-kpi.destaque .s {color: rgba(255,255,255,.88);}
.ve-kpi.destaque .v {color:#fff;}

/* etiquetas em pílula */
.ve-tag {display:inline-block; padding:3px 10px; border-radius:999px; font-size:.74rem; font-weight:700;
  vertical-align: middle;}
.ve-pago {background:#DDF6EE; color:#0B7A58;} .ve-vencido {background:#FFE4E5; color:#B4232A;}
.ve-vence_logo {background:#FFF3CC; color:#8A5A00;} .ve-aberto {background:#EAF1F7; color:#3E5468;}
.ve-embarcou {background:var(--bb-claro); color:#1F6FA3;} .ve-desembarcou {background:#DDF6EE; color:#0B7A58;}
.ve-faltou {background:#FFE4E5; color:#B4232A;} .ve-aviso {background:#FFF3CC; color:#8A5A00;}

/* carteirinha */
.ve-cart {border-radius:22px; padding:18px 20px; color:#16324F; max-width:420px;
          background: linear-gradient(135deg, #FFE27A 0%, #FFC928 60%, #FFB800 100%);
          box-shadow: 0 12px 28px rgba(255,184,0,.30);}
.ve-cart h3 {margin:0 0 4px; color:#16324F;} .ve-cart .r {font-size:.86rem; margin-top:6px;}
.ve-cart .t {font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; opacity:.75; font-weight:700;}
.ve-linha {display:flex; justify-content:space-between; gap:8px; align-items:center;}
.ve-sub {color: var(--ve-cinza); font-size:.85rem;}

/* linhas de ação (st.container(key="linha_…")): botões sempre lado a lado, inclusive no celular */
[class*="st-key-linha"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: .4rem !important;}
[class*="st-key-linha"] [data-testid="stColumn"] {min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;}
/* linhas proporcionais (key="lp_…"): também não quebram no celular, mas mantêm as larguras */
[class*="st-key-lp_"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: .5rem !important;}
[class*="st-key-lp_"] [data-testid="stColumn"] {min-width: 0 !important;}
[class*="st-key-linha"] button, [class*="st-key-linha"] a {padding-left: .3rem !important; padding-right: .3rem !important;}
/* página inicial e planos */
.ve-hero {text-align:center; padding: 1.2rem .5rem 1.4rem;}
.ve-hero .logo {width:120px; height:120px; margin: 0 auto .4rem; filter: drop-shadow(0 12px 20px rgba(10,156,151,.25));}
.ve-hero .logo svg {width:100%; height:100%; animation: ve-anda 1.6s ease-in-out infinite; transform-origin:50% 85%;}
.ve-hero h1 {font-size: 2.4rem !important; margin: .2rem 0 .3rem;}
.ve-hero p {font-size: 1.08rem; color: var(--ve-cinza); max-width: 620px; margin: 0 auto;}
.ve-grade {display:grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: .6rem 0 1.2rem;}
@media (max-width: 900px) {.ve-grade {grid-template-columns: repeat(2, 1fr);}}
@media (max-width: 560px) {.ve-grade {grid-template-columns: 1fr;}}
.ve-feat {background:#fff; border:1px solid #E1F0EF; border-radius:20px; padding:16px 18px; box-shadow: var(--sombra);}
.ve-feat .i {font-size: 1.6rem;} .ve-feat b {display:block; margin:.3rem 0 .15rem; color: var(--ve-azul);}
.ve-feat span {color: var(--ve-cinza); font-size: .92rem;}
.ve-plano {background:#fff; border:1px solid #E1F0EF; border-radius:22px; padding:18px; box-shadow: var(--sombra);
  height:100%; position:relative;}
.ve-plano.atual {border: 2px solid var(--tif-esc);}
.ve-plano.top {background: linear-gradient(160deg, #FFFFFF 0%, #E3F7F6 100%); border: 2px solid var(--tif);}
.ve-plano .d {font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color: var(--tif-esc);}
.ve-plano h3 {margin:.15rem 0 .2rem !important;}
.ve-plano .p {font-size:1.6rem; font-weight:800; color: var(--ve-azul);} .ve-plano .p small {font-size:.85rem;
  color: var(--ve-cinza); font-weight:600;}
.ve-plano ul {padding-left: 1.1rem; margin:.5rem 0 0; color: #33475B;} .ve-plano li {margin: .15rem 0;}
.ve-plano .de {color:#8A9BAA; text-decoration: line-through; font-weight:700; font-size:.95rem; margin-bottom:-4px;}
.ve-plano .promo {display:inline-block; margin-top:4px; background:#FFF3D6; color:#8A5A00; border-radius:999px; padding:2px 10px; font-size:.75rem; font-weight:800;}
.ve-faixa {background: linear-gradient(90deg, #FFF3D6, #FFE6A8); border:1px solid #F5D78A; color:#5C4300; border-radius:18px; padding:12px 16px; margin:.4rem 0 .8rem; font-weight:600;}
.ve-faixa b {color:#3D2C00;}
/* componente invisível do GPS (streamlit-js-eval): não ocupa espaço na tela */
[data-testid="stElementContainer"]:has(iframe[title*="streamlit_js_eval"]) {height: 0 !important; min-height: 0 !important; margin: 0 !important; overflow: hidden;}
[data-testid="stElementContainer"]:has(iframe[title*="streamlit_js_eval"]) + * {margin-top: 0;}
.ve-rodape {text-align:center; color: var(--ve-cinza); font-size:.85rem; margin-top: 2rem;}
.ve-doc {background:#fff; border:1px solid #E1F0EF; border-radius:20px; padding: 6px 24px 18px; box-shadow: var(--sombra);}
@media (max-width: 640px) {
  .ve-hero h1 {font-size: 1.9rem !important;}
  .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: 1rem;}
  .ve-kpis {grid-template-columns: repeat(2, minmax(0,1fr)); gap:10px;}
  .ve-kpi .v {font-size:1.12rem;}
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


APP_URL = "https://pequenosabordo.streamlit.app"


def selo_acesso(email: str | None, acessos: dict) -> str:
    """Etiqueta 'já acessou' / 'ainda não entrou' para um e-mail."""
    if not email:
        return tag("aberto", "sem e-mail")
    quando = acessos.get(email.strip().lower())
    if quando is None:
        return tag("vence_logo", "ainda não entrou")
    from core.fmt import TZ
    return tag("pago", "acessou " + quando.astimezone(TZ).strftime("%d/%m %H:%M"))


def cartoes_planos(atual: str | None = None, precos: dict | None = None):
    """Cartões dos planos lado a lado (no celular, empilhados). `precos`: plano → planos.Preco (mostra a promoção
    com o preço cheio riscado)."""
    from core import planos as pl
    cat = pl.catalogo()
    if not cat:
        st.info("Nenhum plano cadastrado.")
        return
    cols = st.columns(min(len(cat), 4))
    for i, k in enumerate(cat):
        col = cols[i % len(cols)]
        p = cat[k]
        pr = (precos or {}).get(k)
        top = "mais escolhido" in (p.get("destaque") or "").lower()
        cls = "ve-plano" + (" atual" if k == atual else "") + (" top" if top and k != atual else "")
        selo = "Seu plano" if k == atual else p["destaque"]
        itens = "".join(f"<li>{esc(i)}</li>" for i in p["itens"])
        if pr and pr.tem_desconto:
            valor = (f"<div class='de'>{pl.brl(pr.base)}</div><div class='p'>{pl.brl(pr.final)}<small>/mês</small></div>"
                     f"<div class='promo'>{esc(pr.rotulo)}</div>")
        else:
            valor = f"<div class='p'>{pl.preco_txt(p)}<small>{'/mês' if p['preco'] else ''}</small></div>"
        col.markdown(f"<div class='{cls}'><div class='d'>{esc(selo)}</div><h3>{esc(p['nome'])}</h3>{valor}"
                     f"<ul>{itens}</ul></div>", unsafe_allow_html=True)


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


def checar_limite(c: dict, recurso: str, novos: int = 1) -> bool:
    """True se cabe no plano; senão mostra o aviso com link para Meu plano e devolve False."""
    from core import planos as pl, repo
    from core.fmt import hoje
    plano = pl.plano_da_empresa(repo.empresa(c["id"]), hoje())
    atual = repo.uso_empresa(c["id"])[recurso]
    if pl.cabe(plano, recurso, atual, novos):
        return True
    lim = pl.limite(plano, recurso)
    st.error(f"O plano **{pl.catalogo()[plano]['nome']}** permite até **{lim} {recurso}** ativos e você já tem {atual}. "
             "Mude de plano para cadastrar mais.", icon=":material/upgrade:")
    st.page_link("telas/meu_plano.py", label="Ver planos", icon=":material/workspace_premium:")
    return False


def exigir_condutor() -> dict:
    u = st.session_state.get("usuario") or {}
    c = u.get("condutor")
    if not c:
        st.warning("Esta tela é do condutor.")
        st.stop()
    return c


def precos_planos(emp: dict | None, cupom: dict | None = None, periodo: str = "mensal") -> dict:
    """Preço de cada plano para esta empresa (ou para um visitante, se emp=None), com a melhor promoção."""
    from core import planos as pl, repo
    from core.fmt import hoje
    cat, camps, cfg_vip, usadas = pl.catalogo(), repo.campanhas(), pl.config("vip"), repo.vip_usadas()
    return {k: pl.calcular(emp, k, hoje(), periodo, cupom, cat, camps, cfg_vip, usadas) for k in cat}


def faixa_vip(emp: dict | None = None):
    """Faixa do Passageiro VIP: vagas restantes (ou 'você é VIP')."""
    from core import planos as pl, repo
    from core.fmt import hoje
    if emp and emp.get("vip"):
        st.markdown("<div class='ve-faixa'>💎 Você é <b>Passageiro VIP</b>: seu preço está travado para sempre.</div>",
                    unsafe_allow_html=True)
        return
    livres = pl.vip_livres(pl.config("vip"), repo.vip_usadas(), hoje())
    if livres > 0:
        st.markdown(f"<div class='ve-faixa'>💎 <b>Passageiro VIP</b>: assine agora e trave o preço VIP para sempre. "
                    f"Restam <b>{livres} vaga{'s' if livres != 1 else ''}</b>.</div>", unsafe_allow_html=True)


def sem_formula(t: str) -> str:
    """Escapa o '$' para o st.markdown não tratar 'R$ … R$' como fórmula matemática."""
    return t.replace("$", "\\$")


# ---------------------------------------------------------------- localização ao vivo da van
def link_mapa(token: str) -> str:
    return f"{APP_URL}/?van={token}"


def localizacao_ao_vivo(cid, van_id) -> str | None:
    """Liga/desliga a localização ao vivo da van. Ligada, o celular manda a posição a cada ~30 s enquanto este app
    estiver aberto e os pais veem a van num link público que expira. Devolve o link (ou None se desligada)."""
    from core import repo
    if not recurso_liberado("gps", cid):
        em_breve("gps")
        return None
    loc = repo.localizacao_van(cid, van_id)
    if not (loc and loc.get("ativa")):
        if st.button("Ligar localização ao vivo", key=f"loc_on_{van_id}", icon=":material/my_location:",
                     width="stretch", help="O celular pede permissão de localização na primeira vez."):
            repo.ligar_localizacao(cid, van_id)
            st.rerun()
        return None
    _enviar_posicao(cid, str(van_id))
    a, b = st.container(key=f"linha_loc_{van_id}").columns(2)
    a.link_button("Ver o mapa", link_mapa(loc["loc_token"]), icon=":material/map:", width="stretch")
    if b.button("Parar localização", key=f"loc_off_{van_id}", icon=":material/location_off:", width="stretch"):
        repo.parar_localizacao(cid, van_id)
        st.rerun()
    return link_mapa(loc["loc_token"])


@st.fragment(run_every=30)
def _enviar_posicao(cid, van_id: str):
    import time
    from streamlit_js_eval import get_geolocation
    from core import repo
    from core.fmt import agora
    pos = get_geolocation(component_key=f"geo_{van_id}_{int(time.time() // 30)}")
    if isinstance(pos, dict) and isinstance(pos.get("coords"), dict):
        c = pos["coords"]
        repo.salvar_posicao(cid, van_id, float(c["latitude"]), float(c["longitude"]), c.get("accuracy"))
        st.session_state[f"_gps_{van_id}"] = (agora(), c.get("accuracy"))
        st.session_state.pop(f"_gps_erro_{van_id}", None)
    elif isinstance(pos, dict) and pos.get("error"):
        st.session_state[f"_gps_erro_{van_id}"] = True
    if st.session_state.get(f"_gps_erro_{van_id}"):
        st.warning("Não consegui pegar a localização. Permita o acesso à localização para este site no navegador "
                   "do celular e deixe o GPS ligado.", icon=":material/location_disabled:")
    ult = st.session_state.get(f"_gps_{van_id}")
    if ult:
        prec = f" · precisão ~{int(ult[1])} m" if ult[1] else ""
        st.caption(f"📍 Localização ao vivo ligada — posição enviada às {ult[0]:%H:%M:%S}{prec}. "
                   "Atualiza a cada 30 s enquanto este app estiver aberto.")
    else:
        st.caption("📍 Localização ao vivo ligada — pegando a posição do celular…")


# ---------------------------------------------------------------- Asaas
def asaas_api():
    """Cliente do Asaas a partir dos Secrets ([asaas] api_key/ambiente), ou None se não configurado."""
    try:
        c = st.secrets["asaas"]
    except Exception:  # noqa: BLE001
        return None
    if not c.get("api_key"):
        return None
    from core.asaas import Asaas
    return Asaas(str(c["api_key"]), str(c.get("ambiente", "sandbox")), c.get("base_url"))


def sincronizar_asaas(cid=None, forcar: bool = False) -> dict | None:
    """Consulta o Asaas (no máximo 1x por minuto por tela, a não ser que `forcar`). Devolve o resumo ou None."""
    import time
    from core import asaas, db
    from core.fmt import hoje
    api = asaas_api()
    if not api:
        return None
    chave = f"_asaas_sync_{cid or 'todos'}"
    if not forcar and time.time() - st.session_state.get(chave, 0) < 60:
        return None
    st.session_state[chave] = time.time()
    try:
        res = asaas.sincronizar(api, db.conexao(db.banco_ativo()).engine, hoje(), str(cid) if cid else None)
    except asaas.AsaasErro as e:
        return {"erros": [str(e)], "pagamentos_novos": 0, "empresas": 0, "valores_atualizados": 0}
    if res["pagamentos_novos"] or res["valores_atualizados"]:
        db._mudou()
    return res


# ---------------------------------------------------------------- laboratório (novidades só para Exclusivo)
def recurso_liberado(chave: str, cid=None) -> bool:
    """Recurso em teste no laboratório? Então só Exclusivo e admin veem (os outros veem um aviso de 'em breve')."""
    from core import planos as pl, repo
    from core.fmt import hoje
    u = st.session_state.get("usuario") or {}
    if (pl.config("laboratorio") or {}).get(chave, "todos") != "exclusivo":
        return True
    cid = cid or (u.get("condutor") or {}).get("id")
    return pl.liberado(repo.empresa(cid) if cid else None, chave, hoje(), admin=bool(u.get("admin")))


def em_breve(chave: str):
    from core import planos as pl
    st.caption(f"🧪 **{pl.RECURSOS.get(chave, chave)}** está em teste com os parceiros Exclusivos e chega para "
               "todos em breve.")


# ---------------------------------------------------------------- enviar contrato assinado
def botoes_enviar_contrato(contrato: dict, aluno: str, telefone: str | None, email: str | None, para_quem: str,
                           chave: str):
    """WhatsApp e/ou e-mail com o link seguro para baixar o PDF do contrato assinado."""
    import urllib.parse
    from core import repo
    from core.fmt import link_whats
    if not recurso_liberado("envio_contrato"):
        return
    link = f"{APP_URL}/?contrato={repo.token_contrato(contrato['id'] if 'id' in contrato else contrato['contrato_id'])}"
    ano = contrato.get("ano")
    msg = (f"Olá! Segue o contrato de transporte escolar de {aluno} ({ano}), assinado eletronicamente pelo app "
           f"Pequenos a Bordo. Para baixar o PDF: {link}")
    assunto = f"Contrato de transporte escolar — {aluno} ({ano})"
    w = link_whats(telefone, msg) if telefone else f"https://wa.me/?text={urllib.parse.quote(msg)}"
    m = (f"mailto:{urllib.parse.quote(email or '')}?subject={urllib.parse.quote(assunto)}"
         f"&body={urllib.parse.quote(msg)}")
    a, b = st.container(key=f"linha_env_{chave}").columns(2)
    a.link_button(f"WhatsApp {para_quem}".strip(), w, icon=":material/chat:", width="stretch")
    b.link_button(f"E-mail {para_quem}".strip(), m, icon=":material/mail:", width="stretch")


# ---------------------------------------------------------------- Asaas do gestor (cobrança dos pais)
def _fernet():
    """Chave para guardar a chave da API do gestor criptografada no banco (derivada de um segredo do app)."""
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    seg = ""
    for sec, k in (("app", "chave_cripto"), ("auth", "cookie_secret")):
        try:
            seg = seg or str(st.secrets[sec].get(k) or "")
        except Exception:  # noqa: BLE001
            pass
    seg = seg or "pequenos-a-bordo-dev-local"
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("pab-asaas-gestor:" + seg).encode()).digest()))


def cifrar_chave(chave: str) -> str:
    return _fernet().encrypt(chave.strip().encode()).decode()


def api_do_gestor(emp: dict):
    """Cliente Asaas da conta do GESTOR (cobrança dos pais), ou None se não conectou / o plano não libera."""
    from core import planos as pl
    from core.asaas import Asaas
    from core.fmt import hoje
    if not emp or not emp.get("asaas_gestor_chave") or not pl.tem_cobranca_auto(emp, hoje()):
        return None
    if not recurso_liberado("cobranca_pais", emp.get("id")):
        return None
    try:
        chave = _fernet().decrypt(emp["asaas_gestor_chave"].encode()).decode()
    except Exception:  # noqa: BLE001
        return None
    base = None
    try:
        base = st.secrets["asaas"].get("base_url_gestor")
    except Exception:  # noqa: BLE001
        pass
    return Asaas(chave, emp.get("asaas_gestor_ambiente") or "producao", base)
