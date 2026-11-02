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
/* sem a cara do Streamlit: some o "Stop/Running", o Share/estrela/editar/GitHub e o menu ⋮ (o botão de abrir o menu
   lateral continua) — e o carregamento vira a van da Turminha */
[data-testid="stStatusWidget"], [data-testid="stToolbarActions"], [data-testid="stMainMenu"],
[data-testid="stAppDeployButton"], [data-testid="stDecoration"], .stDeployButton,
[data-testid="stToolbar"] [data-testid="stToolbarActionButton"] {display: none !important;}
[data-testid="stSkeleton"] {opacity: 0 !important;}
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
[class*="st-key-lp_"] [data-testid="stHorizontalBlock"], [class*="st-key-lpv_"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: .5rem !important;}
[class*="st-key-lp_"] [data-testid="stColumn"], [class*="st-key-lpv_"] [data-testid="stColumn"] {min-width: 0 !important;}
[class*="st-key-linha"] button, [class*="st-key-linha"] a {padding-left: .3rem !important; padding-right: .3rem !important;}
/* chamada: botões grandes (avisar / avisar + local) e cartão esmaecido de quem não vai */
[class*="st-key-linha_av"] button, [class*="st-key-linha_av"] a {min-height: 3.1rem !important; font-size: 1.02rem !important;
    font-weight: 700 !important; border-radius: 16px !important;}
[class*="st-key-linha_ok"] button, [class*="st-key-linha_ok"] a {min-height: 2.7rem !important; font-size: .98rem !important;}
[class*="st-key-card_falta"] {opacity: .55;}
[class*="st-key-card_falta"]:hover {opacity: .85;}
.st-key-tela_ligada {display: none !important;}
.st-key-marca_android {display: none !important;}
.st-key-marca_aba {display: none !important;}
/* rota do motorista: botões grandes e por cor — amarelo = mensagem, verde = embarcou/entregue,
   vermelho = faltou, azul = caminho. Lê de relance, toca sem errar. */
[class*="st-key-zap_"] button, [class*="st-key-zap_"] a, [class*="st-key-ok_"] button,
[class*="st-key-falta_"] button, [class*="st-key-nav_"] a, [class*="st-key-nav_"] button,
[class*="st-key-ini_rota"] button, [class*="st-key-fim_rota"] button, [class*="st-key-desf_"] button {
    min-height: 3.4rem !important; font-size: 1.08rem !important; font-weight: 800 !important;
    border-radius: 16px !important; border: none !important;}
[class*="st-key-zap_"] button, [class*="st-key-zap_"] a {background: #FFC83D !important; color: #16324F !important;}
[class*="st-key-ok_"] button, [class*="st-key-ini_rota"] button {background: #1E9E5A !important; color: #fff !important;}
[class*="st-key-falta_"] button {background: #E5484D !important; color: #fff !important;}
[class*="st-key-nav_"] a, [class*="st-key-nav_"] button {background: #2F7DE1 !important; color: #fff !important;}
[class*="st-key-fim_rota"] button {background: #16324F !important; color: #fff !important;}
[class*="st-key-desf_"] button {background: #EEF2F5 !important; color: #3E5468 !important; font-weight: 700 !important;}
[class*="st-key-zap_"] p, [class*="st-key-ok_"] p, [class*="st-key-falta_"] p, [class*="st-key-nav_"] p,
[class*="st-key-ini_rota"] p, [class*="st-key-fim_rota"] p, [class*="st-key-desf_"] p {font-size: 1.08rem !important;
    font-weight: 800 !important; line-height: 1.15 !important;}
/* 3 botões lado a lado no celular: sem ícone e com quebra de linha, para o texto caber inteiro */
@media (max-width: 520px) {
  [class*="st-key-linha_ok"] [data-testid="stIconMaterial"],
  [class*="st-key-linha_ok"] span:has(> [data-testid="stIconMaterial"]) {display: none !important;}
  [class*="st-key-linha_ok"] button > div, [class*="st-key-linha_ok"] a > div {gap: 0 !important; justify-content: center !important;}
  [class*="st-key-linha_ok"] p {font-size: .98rem !important;}
}
[class*="st-key-linha_ok"] *, [class*="st-key-linha_av"] * {overflow-wrap: normal !important; word-break: keep-all !important;}
[class*="st-key-linha_ok"] p, [class*="st-key-linha_av"] p {white-space: normal !important; overflow: visible !important;
    text-overflow: clip !important; word-break: normal !important;}
[class*="st-key-linha_ok"] button, [class*="st-key-linha_ok"] a {padding-left: .2rem !important; padding-right: .2rem !important;}
[class*="st-key-zap_"] button:disabled, [class*="st-key-ok_"] button:disabled, [class*="st-key-nav_"] button:disabled {
    opacity: .4 !important;}
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
/* barra de abas no celular (fixa embaixo) — ícones e letras grandes, para usar com o dedo */
.st-key-tabbar {display: none !important;}
@media (max-width: 640px) {
  .st-key-tabbar {display: flex !important; position: fixed; left: 0; right: 0; bottom: 0; z-index: 999990;
    background: rgba(255,255,255,.97); backdrop-filter: blur(8px); border-top: 1px solid #E1F0EF;
    box-shadow: 0 -6px 20px rgba(22,50,79,.08);
    padding: 6px max(22px, env(safe-area-inset-left)) calc(10px + env(safe-area-inset-bottom)) max(22px, env(safe-area-inset-right)) !important;}
  .st-key-tabbar [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: 6px !important; width: 100%;
    justify-content: space-between !important;}
  .st-key-tabbar [data-testid="stColumn"] {min-width: 0 !important; flex: 1 1 0 !important; width: 0 !important;
    max-width: none !important;}
  .st-key-tabbar [data-testid="stColumn"] > div, .st-key-tabbar [data-testid="stColumn"] [data-testid="stVerticalBlock"],
  .st-key-tabbar [data-testid="stElementContainer"], .st-key-tabbar [data-testid="stPageLink"],
  .st-key-tabbar [data-testid="stMarkdown"], .st-key-tabbar [data-testid="stMarkdownContainer"] {width: 100% !important;}
  .st-key-tabbar [data-testid="stPageLink"] a, .ve-mais {display: flex !important; flex-direction: column !important;
    align-items: center !important; justify-content: center !important; gap: 2px !important; padding: 6px 2px !important;
    width: 100% !important; box-sizing: border-box; text-align: center;
    border-radius: 16px !important; background: transparent !important; min-height: 64px; cursor: pointer;}
  .st-key-tabbar [data-testid="stElementContainer"], .st-key-tabbar [data-testid="stPageLink"],
  .st-key-tabbar [data-testid="stPageLink"] > div, .st-key-tabbar [data-testid="stMarkdown"],
  .st-key-tabbar [data-testid="stMarkdownContainer"] {margin: 0 !important; padding: 0 !important;}
  .st-key-tabbar [data-testid="stPageLink"] a, .ve-mais {height: 64px !important; min-height: 64px !important; margin: 0 !important;}
  .st-key-tabbar [data-testid="stPageLink"] a > span:first-child, .ve-mais .i {margin: 0 !important; height: 32px !important;
    width: auto !important; display: flex !important; align-items: center !important; justify-content: center !important;}
  .st-key-tabbar [data-testid="stPageLink"] a > span:last-child {margin: 0 !important; height: 22px; display: flex;
    align-items: center; justify-content: center; max-width: 100%;}
  .st-key-tabbar [data-testid="stPageLink"] a p, .ve-mais .r {line-height: 22px !important;}
  .st-key-tabbar [data-testid="stPageLink"] a span[data-testid="stIconMaterial"] {font-size: 1.9rem !important;
    color: #3E5468 !important;}
  .st-key-tabbar [data-testid="stPageLink"] a p, .ve-mais .r {font-size: .86rem !important; font-weight: 700 !important;
    color: #3E5468 !important; margin: 0 !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
  .st-key-tab_on [data-testid="stPageLink"] a {background: var(--tif-claro) !important;}
  .st-key-tabbar .st-key-tab_on [data-testid="stPageLink"] a p,
  .st-key-tabbar .st-key-tab_on [data-testid="stPageLink"] a span[data-testid="stIconMaterial"] {color: var(--tif-esc) !important;}
  .ve-mais .i {font-family: "Material Symbols Rounded"; font-size: 1.9rem; line-height: 1; color: #3E5468;}
  .block-container {padding-bottom: 7.5rem !important;}
}
/* botão 👁️ esconder valores: pequeno, à direita, colado nos números */
[class*="st-key-olhobtn_"] {display:flex; justify-content:flex-end; margin-bottom:-.6rem;}
[class*="st-key-olhobtn_"] button p {font-size:.85rem !important; color: var(--ve-cinza) !important;}
/* pendências do Hoje: linhas clicáveis */
.st-key-pendencias [data-testid="stPageLink"] a {background:#fff; border:1px solid #E1F0EF; border-radius:16px;
  padding: 10px 14px !important; box-shadow: var(--sombra); margin-bottom: 2px;}
.st-key-pendencias [data-testid="stPageLink"] a p {font-weight:700 !important; color: var(--ve-azul) !important;}
.st-key-pendencias [data-testid="stPageLink"] a::after {content:"›"; margin-left:auto; font-size:1.3rem; color:#8A9BAA;}
/* guia de primeiros passos em uma linha */
.st-key-guia_linha {background:#fff; border:1px solid #E1F0EF; border-radius:18px; padding:8px 12px;
  box-shadow: var(--sombra); margin-bottom:.6rem;}
.st-key-guia_linha [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap:.5rem !important;}
.st-key-guia_linha [data-testid="stColumn"] {min-width:0 !important;}
.ve-guia {font-size:.92rem; color: var(--ve-azul); line-height:1.25;}
.ve-guia .n {font-weight:800; color: var(--tif-esc);}
.ve-guia .bar {height:5px; background:#EEF2F5; border-radius:999px; margin-top:6px; overflow:hidden;}
.ve-guia .bar div {height:100%; background: var(--tif); border-radius:999px;}
.st-key-guia_linha .st-key-guia_ir button p {font-size:.85rem !important; white-space:nowrap;}
@media (max-width: 640px) {.st-key-guia_ir button [data-testid="stIconMaterial"] {display:none;}}
/* celular: nos formulários, 2 colunas continuam lado a lado (não empilham) — economiza tela */
@media (max-width: 640px) {
  [data-testid="stForm"] [data-testid="stHorizontalBlock"]:not(:has(> [data-testid="stColumn"]:nth-child(3))) {
    flex-wrap: nowrap !important; gap: .6rem !important;}
  [data-testid="stForm"] [data-testid="stHorizontalBlock"]:not(:has(> [data-testid="stColumn"]:nth-child(3))) > [data-testid="stColumn"] {
    min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;}
}
@media (max-width: 640px) {
  div[data-testid="stForm"] {padding: .8rem .85rem !important;}
  div[data-testid="stForm"] [data-testid="stVerticalBlock"] {gap: .55rem !important;}
}
/* barrinha de etapas */
.ve-etapas {display:flex; gap:6px; margin:.2rem 0 .8rem;}
.ve-etapas .e {flex:1; min-width:0; display:flex; flex-direction:column; align-items:center; gap:3px;
  position:relative;}
.ve-etapas .e span {width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:#EEF2F5; color:#8A9BAA; font-weight:800; font-size:.9rem; z-index:1;}
.ve-etapas .e b {font-size:.74rem; color:#8A9BAA; font-weight:700; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; max-width:100%;}
.ve-etapas .e.atual span {background: var(--tif-esc); color:#fff;}
.ve-etapas .e.atual b {color: var(--ve-azul);}
.ve-etapas .e.feito span {background: var(--tif-claro); color: var(--tif-esc);}
.ve-etapas .e:not(:first-child)::before {content:""; position:absolute; top:15px; right:50%; width:100%; height:3px;
  background:#EEF2F5;}
.ve-etapas .e.feito:not(:first-child)::before, .ve-etapas .e.atual:not(:first-child)::before {background: var(--tif);}
/* botões do rodapé do cadastro (Voltar / Continuar) */
[class*="st-key-wzpe_"] [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap:.6rem !important;}
[class*="st-key-wzpe_"] [data-testid="stColumn"] {min-width:0 !important;}
[class*="st-key-wzpe_"] button {min-height: 50px;}
/* linhas da ficha */
[class*="st-key-fl_"] button {justify-content: flex-start !important; text-align:left; background:#fff !important;
  border:1px solid #E1F0EF !important; border-radius:16px !important; padding: 10px 14px !important;
  box-shadow: var(--sombra); min-height: 58px;}
[class*="st-key-fl_"] button > div, [class*="st-key-al_"] button > div {justify-content: flex-start !important;
  width: 100%; text-align: left;}
[class*="st-key-fl_"] button [data-testid="stMarkdownContainer"], [class*="st-key-al_"] button [data-testid="stMarkdownContainer"] {
  text-align: left; flex: 1;}
[class*="st-key-fl_"] button p {text-align:left; color: var(--ve-cinza) !important; font-size:.85rem !important;
  line-height:1.3 !important;}
[class*="st-key-fl_"] button p strong {color: var(--ve-azul); font-size:1rem;}
[class*="st-key-fl_"] button::after {content:"›"; margin-left:auto; font-size:1.4rem; color:#8A9BAA; padding-left:8px;}
[class*="st-key-fl_"] button [data-testid="stIconMaterial"] {color: var(--tif-esc) !important; font-size:1.4rem !important;}
[class*="st-key-al_"] button {justify-content: flex-start !important; background:#fff !important;
  border:1px solid #E1F0EF !important; border-radius:16px !important; min-height:54px; box-shadow: var(--sombra);}
[class*="st-key-al_"] button p {text-align:left; color: var(--ve-cinza) !important; font-size:.84rem !important;}
[class*="st-key-al_"] button p strong {color: var(--ve-azul); font-size:1rem;}
[class*="st-key-al_"] button::after {content:"›"; margin-left:auto; font-size:1.4rem; color:#8A9BAA; padding-left:8px;}
.ve-ficha-topo {display:flex; align-items:center; gap:12px; margin:.2rem 0 .8rem;}
.ve-ficha-topo .av {width:54px; height:54px; border-radius:50%; background: var(--tif-claro); color: var(--tif-esc);
  display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.4rem; flex:none;}
.ve-ficha-topo h3 {margin:0 !important; font-size:1.3rem !important;}
[class*="st-key-vidbtn_"] {margin: -.6rem 0 -.4rem;}
[class*="st-key-vidbtn_"] button p {color: var(--tif-esc) !important; font-weight: 700 !important; font-size: .9rem !important;}
/* meta do mês */
.ve-meta {background:#fff; border:1px solid #E1F0EF; border-radius:18px; padding:12px 16px; margin:.3rem 0 .8rem;
  box-shadow: var(--sombra);}
.ve-meta .t {display:flex; justify-content:space-between; gap:8px; font-weight:700; color: var(--ve-azul);
  font-size:.95rem; flex-wrap: wrap;}
.ve-meta .t span {color: var(--ve-cinza); font-weight:600;}
.ve-meta .barra {height:12px; background:#EEF2F5; border-radius:999px; overflow:hidden; margin:.5rem 0 .3rem;}
.ve-meta .barra div {height:100%; border-radius:999px; background: linear-gradient(90deg, #14B8B0, #1E9E5A);}
.ve-meta .s {font-size:.85rem; color: var(--ve-cinza);}
/* atalhos grandes do Hoje */
[class*="st-key-atalho_"] a, [class*="st-key-atalho_"] button {min-height: 64px; border-radius: 18px !important;
  font-weight: 800 !important; justify-content: center !important; background: #fff !important;
  border: 1px solid #E1F0EF !important; box-shadow: var(--sombra); width: 100%;}
[class*="st-key-atalho_"] a p, [class*="st-key-atalho_"] button p {font-size: 1.02rem !important; font-weight: 800 !important;
  color: var(--ve-azul) !important;}
.st-key-atalhos [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important; gap: .5rem !important;}
.st-key-atalhos [data-testid="stColumn"] {min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;}
@media (max-width: 640px) {
  [class*="st-key-atalho_"] a, [class*="st-key-atalho_"] button {flex-direction: column !important; min-height: 70px;
    padding: 6px 4px !important; gap: 2px !important;}
  [class*="st-key-atalho_"] a p, [class*="st-key-atalho_"] button p {font-size: .9rem !important; white-space: nowrap;}
}
.st-key-atalho_rota a {background: #1E9E5A !important; border-color: #1E9E5A !important;}
.st-key-atalho_rota a * {color: #fff !important;}
.st-key-atalho_cobrar a {background: #FFC83D !important; border-color: #FFC83D !important;}
.st-key-atalho_cobrar a * {color: #16324F !important;}
/* mensalidade vencida em destaque */
[class*="st-key-card_venc_"] {border-left: 5px solid #E5484D !important; background: #FFF5F5 !important;}
[class*="st-key-lpv_"] {border-left: 4px solid #E5484D; background: #FFF5F5; border-radius: 12px; padding: 4px 8px;}
/* documentos da van */
.ve-doc-al {border-radius: 14px; padding: 8px 12px; margin: .25rem 0; font-size: .93rem;}
.ve-doc-al.venc {background:#FFF5F5; border-left: 4px solid #E5484D;}
.ve-doc-al.logo {background:#FFF8E6; border-left: 4px solid #F5A524;}
@media (max-width: 640px) {
  .ve-hero h1 {font-size: 1.9rem !important;}
  .block-container {padding-left: .8rem; padding-right: .8rem; padding-top: .4rem;}
  h1 {margin: 0 0 .2rem !important; padding: .2rem 0 !important;}
  .ve-etapas {margin: 0 0 .5rem;}
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


# Aba do navegador e atalho do celular: o Streamlit Cloud põe "· Streamlit" no título e o ícone dele na página de fora
# (o app roda num iframe do MESMO endereço, então dá para corrigir a página de fora daqui de dentro).
_MARCA_ABA = """<script>(function(){try{
if(!window.__tbMais){window.__tbMais=1;
  /* o Streamlit fecha o menu sozinho num toque fora dele (antes do nosso clique) — então o estado é lido no
     começo do toque, e o clique decide: aberto → fecha; fechado → abre */
  const aberto=()=>{const sb=document.querySelector('[data-testid="stSidebar"]');
    return !!sb && sb.getAttribute('data-collapsed')!=='true' && sb.getBoundingClientRect().right>40;};
  const marca=e=>{if(e.target.closest && e.target.closest('.ve-mais')) window.__tbMaisAberto=aberto();};
  document.addEventListener('pointerdown',marca,true); document.addEventListener('touchstart',marca,true);
  document.addEventListener('click',function(e){
    if(!(e.target.closest && e.target.closest('.ve-mais'))) return;
    const estava = window.__tbMaisAberto===undefined ? aberto() : window.__tbMaisAberto; window.__tbMaisAberto=undefined;
    setTimeout(()=>{const agora=aberto();
      if(estava && agora){const b=document.querySelector('[data-testid="stSidebarCollapseButton"] button'); if(b) b.click();}
      else if(!estava && !agora){const b=document.querySelector('[data-testid="stExpandSidebarButton"]'); if(b) b.click();}
    },60);},true);}
}catch(e){}})();
(function(){try{
const P=window.parent; if(!P||P===window) return; const d=P.document;
const T="Turminha a Bordo", I="https://turminhaabordo.com.br/icone-180.png";
function link(rel){let l=d.head.querySelector('link[rel="'+rel+'"]'); if(!l){l=d.createElement('link'); l.rel=rel; d.head.appendChild(l);} return l;}
function meta(n,v){let m=d.head.querySelector('meta[name="'+n+'"]'); if(!m){m=d.createElement('meta'); m.name=n; d.head.appendChild(m);} if(m.content!==v) m.content=v;}
function fix(){
  if(d.title!==T) d.title=T;
  d.head.querySelectorAll('link[rel~="icon"]').forEach(l=>{if(l.href!==I){l.href=I; l.type="image/png";}});
  if(!d.head.querySelector('link[rel~="icon"]')){const l=link("icon"); l.href=I; l.type="image/png";}
  const a=link("apple-touch-icon"); if(a.href!==I) a.href=I;
  meta("apple-mobile-web-app-title",T); meta("application-name",T); meta("theme-color","#14B8B0");
  if(!d.getElementById("tb-sem-selo")){const s=d.createElement("style"); s.id="tb-sem-selo";
    s.textContent='@media (max-width:640px){[data-testid="manage-app-button"],[class*="viewerBadge"],[class*="_profileContainer"]{display:none!important}}';
    d.head.appendChild(s);}
  if(P.innerWidth<=640){d.querySelectorAll("body *").forEach(e=>{try{const c=P.getComputedStyle(e);
    if(c.position==="fixed"&&!e.querySelector("iframe")&&e.tagName!=="IFRAME"&&e.getBoundingClientRect().top>P.innerHeight*0.6) e.style.setProperty("display","none","important");}catch(x){}});}
}
fix();
if(!P.__tbMarca){P.__tbMarca=new P.MutationObserver(()=>fix()); P.__tbMarca.observe(d.head,{subtree:true,childList:true,characterData:true,attributes:true});}
}catch(e){}})();</script>"""


def css():
    st.markdown(CSS, unsafe_allow_html=True)
    with st.container(key="marca_aba"):
        st.html(_MARCA_ABA, unsafe_allow_javascript=True)


_RE_DINHEIRO = __import__("re").compile(r"-?R\$\s?-?[\d.]+,\d{2}")


def ocultar_valores() -> bool:
    return bool(st.session_state.get("_ocultar_valores"))


def _mascara(t) -> str:
    """Com o 👁️ ligado, troca os valores em R$ por R$ •••••."""
    t = str(t)
    return _RE_DINHEIRO.sub("R$ •••••", t) if ocultar_valores() else t


def olho(chave: str = "olho"):
    """Botão 👁️ para esconder/mostrar os valores (para abrir o app na frente dos outros)."""
    oculto = ocultar_valores()
    with st.container(key=f"olhobtn_{chave}"):
        if st.button("Mostrar valores" if oculto else "Esconder valores", type="tertiary", key=f"_olho_{chave}",
                     icon=":material/visibility:" if oculto else ":material/visibility_off:"):
            st.session_state["_ocultar_valores"] = not oculto
            st.rerun()


def kpis(itens: list[tuple], destaque: int | None = 0):
    """itens: (rótulo, valor, subtítulo opcional)."""
    partes = []
    for i, it in enumerate(itens):
        rot, val, sub = (list(it) + [""])[:3]
        val, sub = _mascara(val), _mascara(sub)
        cls = "ve-kpi destaque" if i == destaque else "ve-kpi"
        partes.append(f"<div class='{cls}'><div class='l'>{esc(rot)}</div><div class='v'>{esc(val)}</div>"
                      f"<div class='s'>{esc(sub)}</div></div>")
    st.markdown(f"<div class='ve-kpis'>{''.join(partes)}</div>", unsafe_allow_html=True)


def tag(chave: str, texto: str | None = None) -> str:
    return f"<span class='ve-tag ve-{esc(chave)}'>{esc(texto or chave)}</span>"


APP_URL = "https://turminhaabordo.streamlit.app"
EMAIL_CONTATO = "contato@turminhaabordo.com.br"
INSTAGRAM = "turminha_abordo"
INSTAGRAM_URL = f"https://www.instagram.com/{INSTAGRAM}/"


# ---------------------------------------------------------------- Fale conosco (Telegram)
def telegram():
    """Cliente do bot de suporte (ou None se a chave não estiver nos Secrets)."""
    from core.suporte import Telegram
    try:
        cfg = st.secrets.get("telegram") or {}
        tok = cfg.get("token")
    except Exception:  # noqa: BLE001
        return None
    return Telegram(tok, cfg.get("base_url")) if tok else None


def motor():
    from core import db
    return db.conexao(db.banco_ativo()).engine


def sincronizar_suporte(intervalo: int = 60) -> dict | None:
    """Busca as respostas dadas no Telegram (no máx. 1x por `intervalo` segundos por sessão)."""
    import time
    from core import suporte
    tg = telegram()
    if not tg or time.time() - st.session_state.get("_sync_tg", 0) < intervalo:
        return None
    st.session_state["_sync_tg"] = time.time()
    try:
        return suporte.sincronizar(motor(), tg)
    except Exception:  # noqa: BLE001 — suporte nunca derruba o app
        return None


def aviso_pausa(cond: dict) -> bool:
    """Empresa em pausa de férias: avisa que rota/chamada estão pausadas (True = pare a tela)."""
    from core import planos as pl, repo
    from core.fmt import data_br, hoje
    emp = repo.empresa(cond["id"])
    if not pl.em_pausa(emp, hoje()):
        return False
    st.info(f"⏸️ **Pausa de férias até {data_br(emp['pausa_ate'])}** — rota e chamada estão pausadas. "
            "Para voltar antes, vá em **Meu plano → Voltar ao normal agora**.", icon=":material/pause_circle:")
    st.page_link("telas/meu_plano.py", label="Meu plano", icon=":material/workspace_premium:")
    return True


def link_contato(assunto: str = "Contato — Turminha a Bordo") -> str:
    import urllib.parse
    return f"mailto:{EMAIL_CONTATO}?subject={urllib.parse.quote(assunto)}"


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
    c = None if st.session_state.get("ver_como_motorista") else u.get("condutor")
    if c:
        for v in repo.vans(c["id"]).itertuples():
            out.append(dict(id=str(v.id), nome=v.nome, placa=v.placa, cid=c["id"], empresa=c["nome"], gestor=True,
                            minha=u["email"] in ((v.motorista_email or ""), (v.monitor_email or ""))))
            vistos.add(str(v.id))
    for v in u.get("vans_motorista") or []:
        if str(v["id"]) not in vistos:
            out.append(dict(id=str(v["id"]), nome=v["nome"], placa=v.get("placa"), cid=v["condutor_id"],
                            empresa=v["empresa"], gestor=False, minha=True, empresa_tel=v.get("empresa_tel")))
    out.sort(key=lambda x: (not x["minha"], x["empresa"], x["nome"]))   # a que a pessoa dirige vem primeiro
    return out


def rotulo_van(v: dict, varias_empresas=False) -> str:
    base = v["nome"] + (f" · {v['placa']}" if v.get("placa") else "")
    return base + (f" ({v['empresa']})" if varias_empresas else "")


def filtro_van(cid, chave: str, label="Van", rotulo_oculto: bool = False) -> str | None:
    """Selectbox 'Todas as vans' + vans da empresa (só aparece se houver mais de uma). Devolve van_id ou None."""
    from core import repo
    vs = repo.vans(cid)
    if len(vs) <= 1:
        return None
    ids = ["todas"] + [str(x) for x in vs["id"]]        # "todas" (e não None): None vira "Choose an option"
    nomes = {"todas": "Todas as vans"} | {str(r.id): r.nome for r in vs.itertuples()}
    if st.session_state.get(chave) not in ids:
        st.session_state[chave] = "todas"
    v = st.selectbox(label, ids, format_func=nomes.get, key=chave,
                     label_visibility="collapsed" if rotulo_oculto else "visible")
    return None if v == "todas" else v


def checar_limite(c: dict, recurso: str, novos: int = 1) -> bool:
    """True se cabe no plano; senão mostra o aviso com link para Meu plano e devolve False."""
    from core import planos as pl, repo
    from core.fmt import hoje
    emp = repo.empresa(c["id"])
    plano = pl.plano_da_empresa(emp, hoje())
    atual = repo.uso_empresa(c["id"])[recurso]
    if plano is None and pl.no_gratis(emp, hoje()):
        lim = pl.limite_gratis(recurso)
        if lim is None or atual + novos <= lim:
            return True
        st.error(f"O plano **Grátis** vale para até **{lim} {recurso}** ativos e você já tem {atual}. "
                 "Assine para cadastrar mais — e liberar rota, avisos aos pais e contrato.", icon=":material/upgrade:")
        st.page_link("telas/meu_plano.py", label="Ver planos", icon=":material/workspace_premium:")
        return False
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


def manter_tela_ligada(ligar: bool):
    """Durante a rota a tela do celular não apaga sozinha (Wake Lock do navegador; volta a pedir quando o motorista
    volta do WhatsApp/Maps). Fora da rota, libera."""
    js_on = """<script>(function(){const w=window;w.__tbWakeOn=true;if(w.__tbWake)return;w.__tbWake=true;
async function pedir(){try{if(w.__tbWakeOn&&'wakeLock' in navigator&&document.visibilityState==='visible'&&
(!w.__tbLock||w.__tbLock.released)){w.__tbLock=await navigator.wakeLock.request('screen');}}catch(e){}}
pedir();document.addEventListener('visibilitychange',pedir);document.addEventListener('click',pedir,{passive:true});
})();</script>"""
    js_off = """<script>(function(){const w=window;w.__tbWakeOn=false;
try{if(w.__tbLock&&!w.__tbLock.released)w.__tbLock.release();}catch(e){}})();</script>"""
    with st.container(key="tela_ligada"):
        st.html(js_on if ligar else js_off, unsafe_allow_javascript=True)


# ---------------------------------------------------------------- app da Play Store (não vende dentro do app)
def app_android() -> bool:
    """Aberto pelo app Android da Play Store? (ele abre com ?origem=android). Lá dentro o app não vende —
    regra do Google Play para assinatura digital; o gestor assina pelo site. Vale até o navegador fechar
    (cookie de sessão), assim continua valendo depois do login com o Google, que recarrega a página."""
    if st.session_state.get("_android"):
        return True
    try:
        cookie = st.context.cookies.get("turminha_android") == "1"
    except Exception:  # noqa: BLE001
        cookie = False
    if st.query_params.get("origem") == "android" or cookie:
        st.session_state["_android"] = True
        return True
    return False


def marcar_android():
    """Grava o cookie de sessão que lembra que é o app Android (chamado quando chega ?origem=android)."""
    with st.container(key="marca_android"):
        st.html("<script>document.cookie='turminha_android=1; path=/; SameSite=Lax; Secure';</script>",
                unsafe_allow_javascript=True)


def aviso_assinar_pelo_site():
    st.info("Para **assinar, renovar ou mudar de plano**, acesse **turminhaabordo.com.br** pelo navegador do "
            "celular ou do computador. Assim que o pagamento cair, o plano é liberado aqui no app.",
            icon=":material/open_in_browser:")


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


# ---------------------------------------------------------------- Mercado Pago (alternativa ao Asaas)
GATEWAYS = {"asaas": "Asaas", "mercadopago": "Mercado Pago"}


def mp_api():
    """Cliente do Mercado Pago a partir dos Secrets ([mercadopago] access_token), ou None se não configurado."""
    try:
        c = st.secrets["mercadopago"]
    except Exception:  # noqa: BLE001
        return None
    if not c.get("access_token"):
        return None
    from core.mercadopago import MercadoPago
    return MercadoPago(str(c["access_token"]), c.get("base_url"))


def gateway_ativo() -> str | None:
    """Quem recebe as NOVAS assinaturas (escolha do admin). Se o escolhido não tem credencial, usa o outro."""
    from core import planos as pl
    escolha = (pl.config("gateway") or {}).get("ativo") or "asaas"
    tem = {"asaas": asaas_api() is not None, "mercadopago": mp_api() is not None}
    if tem.get(escolha):
        return escolha
    return next((g for g, ok in tem.items() if ok), None)


def sincronizar_mp(cid=None, forcar: bool = False) -> dict | None:
    """Consulta o Mercado Pago (no máximo 1x por minuto por tela, a não ser que `forcar`)."""
    import time
    from core import db, mercadopago
    from core.fmt import hoje
    api = mp_api()
    if not api:
        return None
    chave = f"_mp_sync_{cid or 'todos'}"
    if not forcar and time.time() - st.session_state.get(chave, 0) < 60:
        return None
    st.session_state[chave] = time.time()
    try:
        res = mercadopago.sincronizar(api, db.conexao(db.banco_ativo()).engine, hoje(), str(cid) if cid else None)
    except mercadopago.MPErro as e:
        return {"erros": [str(e)], "pagamentos_novos": 0, "empresas": 0, "valores_atualizados": 0}
    if res["pagamentos_novos"] or res["valores_atualizados"]:
        db._mudou()
    return res


def sincronizar_pagamentos(cid=None, forcar: bool = False) -> dict | None:
    """Asaas + Mercado Pago juntos (cada um só se estiver configurado). Soma os resumos."""
    out = None
    for r in (sincronizar_asaas(cid, forcar), sincronizar_mp(cid, forcar)):
        if r is None:
            continue
        if out is None:
            out = {"empresas": 0, "pagamentos_novos": 0, "valores_atualizados": 0, "erros": []}
        for k in ("empresas", "pagamentos_novos", "valores_atualizados"):
            out[k] += r.get(k, 0)
        out["erros"] += r.get("erros") or []
    return out


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
           f"Turminha a Bordo. Para baixar o PDF: {link}")
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


def instagram(texto: str = "Siga no Instagram", chave: str = "insta"):
    """Link para o Instagram do app (abre o app do Instagram no celular)."""
    st.link_button(f"{texto} @{INSTAGRAM}", INSTAGRAM_URL, icon=":material/photo_camera:", width="stretch",
                   key=chave)


# ---------------------------------------------------------------- guia de primeiros passos (gestor novo)
def _passos_guia(facil: bool) -> list[dict]:
    return [
        dict(chave="aluno", titulo="Cadastre o primeiro aluno",
             sub="Só o nome e o WhatsApp de quem é responsável — ou importe sua planilha.",
             pagina="telas/facil_alunos.py" if facil else "telas/alunos.py", botao="Cadastrar aluno",
             dica="Digite o **nome do aluno** e o **WhatsApp do responsável** e toque em **Adicionar aluno**. "
                  "Valor e vencimento você pode pôr agora ou depois. Já tem a lista numa planilha? Use "
                  "**Importar planilha** logo abaixo e cadastre todos de uma vez."),
        dict(chave="rota", titulo="Faça a primeira rota",
             sub="Pode ser de teste: toque em Iniciar rota e veja como o pai é avisado.",
             pagina="telas/facil_rota.py" if facil else "telas/chamada.py", botao="Abrir a rota",
             dica="Toque em **Iniciar rota** e depois em **Estou a caminho**: o WhatsApp abre com a mensagem pronta "
                  "para o responsável. É só isso no dia a dia!"),
        dict(chave="pix", titulo="Coloque sua chave Pix",
             sub="Ela vai junto na cobrança das mensalidades pelo WhatsApp.",
             pagina="telas/meu_cadastro.py", botao="Colocar chave Pix",
             dica="Preencha a **Chave Pix** e, se quiser, o **dia de vencimento** padrão — e toque em **Salvar**."),
    ]


def guia(c: dict, pagina_atual: str | None = None):
    """Cartão 'Comece por aqui' com os próximos passos e um botão que leva direto para onde fazer.
    Some sozinho quando tudo estiver feito, ou quando o gestor esconder."""
    from core import repo
    u = st.session_state.get("usuario", {})
    if not c or u.get("bloqueado") or u.get("gratis"):
        return
    prog = repo.progresso_inicio(c["id"])
    if not prog or prog.get("fechado"):
        return
    emp = repo.empresa(c["id"]) or {}
    passos = _passos_guia((emp.get("modo") or "completo") == "facil")
    feitos = 1 + sum(1 for p in passos if prog.get(p["chave"]))
    total = 1 + len(passos)
    if feitos == total:
        return
    prox = next(p for p in passos if not prog.get(p["chave"]))
    # uma linha só: progresso + próximo passo (um toque leva até lá) + ✕ para quem não quer ver
    aqui = pagina_atual == prox["pagina"]
    with st.container(key="guia_linha"):
        a, b, x = st.columns([7, 2, 1], vertical_alignment="center")
        a.markdown(f"<div class='ve-guia'><span class='n'>🚐 {feitos}/{total}</span> "
                   f"{'Agora' if aqui else 'Próximo'}: <b>{esc(prox['titulo'])}</b>"
                   f"<div class='bar'><div style='width:{feitos / total * 100:.0f}%'></div></div></div>",
                   unsafe_allow_html=True)
        if not aqui and b.button("Ir", type="primary", key="guia_ir", width="stretch",
                                 icon=":material/arrow_forward:"):
            # já abre direto onde se faz o passo (cadastro novo do aluno / seção do Pix)
            if prox["chave"] == "aluno" and prox["pagina"] == "telas/alunos.py":
                st.session_state.update(al_modo="novo", al_rasc={}, al_etapa=0)
            elif prox["chave"] == "pix":
                st.session_state["me_sec"] = "pix"
            try:
                st.switch_page(prox["pagina"])
            except Exception:  # noqa: BLE001 — página fora do menu (ex.: pausa de férias)
                st.info("Abra essa tela pelo menu.")
        if x.button("", icon=":material/close:", type="tertiary", key="guia_fechar", help="Esconder o guia"):
            repo.fechar_guia(c["id"])
            st.rerun()


def faixa_gratis():
    """Aviso discreto no topo de quem está no plano Grátis."""
    from core import planos as pl
    lim = pl.limite_gratis("alunos")
    a, b = st.container(key="faixa_gratis").columns([3, 1], vertical_alignment="center")
    a.markdown(f"🆓 **Plano Grátis** <span class='ve-sub'>· mensalidades e financeiro para até {lim} alunos. "
               "Assine para liberar rota, avisos aos pais, mapa, contrato e fretamento.</span>", unsafe_allow_html=True)
    b.page_link("telas/meu_plano.py", label="Ver planos", icon=":material/workspace_premium:")


# ---------------------------------------------------------------- importar planilha de alunos
def importar_planilha(c: dict, van, dia_padrao: int, chave: str = "imp", caixa: bool = True):
    """Importar planilha: baixar modelo → subir xlsx/csv ou colar → conferir → importar.
    caixa=False: sem o expander (quando já está dentro de um popover)."""
    from contextlib import nullcontext
    from core import importar as imp
    with (st.expander("Importar planilha (Excel ou Google Planilhas)", icon=":material/upload_file:") if caixa
          else nullcontext()):
        st.caption("Baixe o modelo → preencha um aluno por linha → envie o arquivo aqui. "
                   "Já tem sua planilha? Pode mandar ela mesma — a gente acha as colunas pelo nome.")
        st.download_button("Baixar modelo (.xlsx)", imp.modelo_xlsx(), file_name="modelo-alunos.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           icon=":material/download:", key=f"{chave}_modelo")
        arq = st.file_uploader("Enviar planilha", type=["xlsx", "csv"], key=f"{chave}_arq")
        txt = st.text_area("…ou cole aqui (copie as linhas no Excel / Google Planilhas e cole)", height=90,
                           key=f"{chave}_txt")
        if not arq and not (txt or "").strip():
            return
        try:
            df = imp.ler(arquivo=arq) if arq else imp.ler(texto=txt)
        except Exception as e:  # noqa: BLE001
            st.error(f"Não consegui ler essa planilha ({e}). Tente salvar como .xlsx ou use o modelo.")
            return
        if df.empty:
            st.warning("Não achei nenhum aluno na planilha. Confira se a coluna **Aluno** está preenchida.")
            return
        v = imp.validar(c["id"], df, dia_padrao)
        ok = int((v["situacao"] == "ok").sum())
        dup = int((v["situacao"] == "duplicado").sum())
        err = int((v["situacao"] == "erro").sum())
        a, b, d = st.columns(3)
        a.metric("Prontos para importar", ok)
        b.metric("Vão ser pulados", dup, help="Já existe aluno com esse nome, ou o nome se repete na planilha.")
        d.metric("Com erro", err)
        rot = {"ok": "✅ OK", "duplicado": "⏭️ Pular", "erro": "❌ Erro"}
        mostra = v.assign(situacao=v["situacao"].map(rot),
                          turno=v["turno"].map({"manha": "Manhã", "tarde": "Tarde", "integral": "Integral",
                                                "noite": "Noite"}))
        st.dataframe(mostra[["situacao", "aviso", "nome", "responsavel", "whatsapp", "valor", "dia", "escola", "turno"]],
                     hide_index=True, width="stretch",
                     column_config={"situacao": "", "nome": "Aluno", "responsavel": "Responsável",
                                    "whatsapp": "WhatsApp",
                                    "valor": st.column_config.NumberColumn("Mensalidade", format="R$ %.2f"),
                                    "dia": "Vence dia", "escola": "Escola", "turno": "Turno", "aviso": "Observação"})
        if err:
            st.caption("Linhas com erro não entram — corrija na planilha e envie de novo, ou cadastre depois.")
        if ok and st.button(f"Importar {ok} aluno(s)", type="primary", icon=":material/group_add:",
                            key=f"{chave}_ir"):
            if checar_limite(c, "alunos", novos=ok):
                n = imp.importar(c["id"], v, van)
                for k in (f"{chave}_arq", f"{chave}_txt"):
                    st.session_state.pop(k, None)
                st.toast(f"{n} aluno(s) importado(s).", icon="✅")
                st.rerun()


# ---------------------------------------------------------------- barra de abas (só aparece no celular)
def barra_abas(itens: list[tuple[str, str, str]], atual: str = ""):
    """itens: (página, rótulo, ícone). O último botão, "Mais", abre o menu lateral com o resto.
    `atual`: url_path da página aberta — a aba dela fica destacada (vazio = página inicial = 1ª aba)."""
    from pathlib import Path
    with st.container(key="tabbar"):
        cols = st.columns(len(itens) + 1)
        for i, (col, (pag, rot, ic)) in enumerate(zip(cols, itens)):
            with col.container(key="tab_on" if Path(pag).stem == atual or (not atual and i == 0) else f"tab_{i}"):
                st.page_link(pag, label=rot, icon=ic)
        cols[-1].markdown("<div class='ve-mais'><span class='i'>menu</span><span class='r'>Mais</span></div>",
                          unsafe_allow_html=True)


# ---------------------------------------------------------------- meta do mês (recebido × previsto)
def meta_mes(recebido: float, previsto: float, rotulo: str = "Meta do mês"):
    from core.fmt import brl
    if not previsto:
        return
    pct = max(0.0, min(100.0, recebido / previsto * 100))
    falta = max(0.0, previsto - recebido)
    s = _mascara("Meta batida! 🎉 Todo mundo pagou." if falta <= 0.005 else f"Faltam {brl(falta)} para fechar o mês.")
    st.markdown(f"<div class='ve-meta'><div class='t'>{esc(rotulo)} <span>{_mascara(brl(recebido) + ' de ' + brl(previsto))} · "
                f"{pct:.0f}%</span></div><div class='barra'><div style='width:{pct:.1f}%'></div></div>"
                f"<div class='s'>{s}</div></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- documentos da van
def alertas_documentos(cid, dias: int = 30, link: bool = True):
    """Documentos vencidos ou vencendo nos próximos `dias` dias (IPVA, seguro, vistoria…)."""
    from datetime import timedelta
    from core import repo
    from core.fmt import brl, data_br, hoje
    h = hoje()
    df = repo.documentos_van(cid, ate=h + timedelta(days=dias))
    if df.empty:
        return
    st.subheader("📄 Documentos da van")
    for r in df.itertuples():
        d = (r.vencimento - h).days
        quando = (f"venceu há {-d} dia(s)" if d < 0 else "vence **hoje**" if d == 0 else
                  f"vence em {d} dia(s) ({data_br(r.vencimento)})")
        val = f" · {brl(r.valor)}" if r.valor is not None and str(r.valor) != "nan" and float(r.valor) > 0 else ""
        st.markdown(f"<div class='ve-doc-al {'venc' if d < 0 else 'logo'}'>{'🔴' if d < 0 else '🟡'} "
                    f"<b>{esc(r.tipo)}</b> · {esc(r.van)} — {quando}{val}</div>", unsafe_allow_html=True)
    if link:
        st.page_link("telas/vans.py", label="Ver documentos das vans", icon=":material/description:")


def documentos_vans(cid, vans, so_van: str | None = None, titulo: bool = True):
    """Cadastro dos documentos com vencimento + 'Paguei' (vira despesa no Financeiro e renova a data).
    so_van: mostra só os documentos dessa van (ficha da van)."""
    from datetime import timedelta
    from core import repo
    from core.fmt import brl, data_br, hoje, somar_meses
    h = hoje()
    if titulo:
        st.subheader("📄 Documentos e vencimentos")
    st.caption("O app avisa no **Hoje** 30 dias antes. Pagou? Toque em **Paguei**: vira despesa no Financeiro e a "
               "data vai para o ano seguinte.")
    opc_van = {None: "Empresa (todas)"} | {str(v.id): v.nome for v in vans.itertuples()}
    df = repo.documentos_van(cid)
    if so_van and not df.empty:
        df = df[df["van_id"].astype(str) == str(so_van)]
    for r in df.itertuples():
        d = (r.vencimento - h).days
        cor = "🔴" if d < 0 else "🟡" if d <= 30 else "🟢"
        with st.container(border=True, key=f"card_doc_{r.id}"):
            a, b = st.columns([3, 2], vertical_alignment="center")
            a.markdown(f"{cor} **{esc(r.tipo)}** · {esc(r.van)}  \n<span class='ve-sub'>vence {data_br(r.vencimento)}"
                       + (f" · {brl(r.valor)}" if r.valor is not None and str(r.valor) != "nan" else "")
                       + (f" · {esc(r.obs)}" if r.obs else "") + "</span>", unsafe_allow_html=True)
            x1, x2 = b.columns(2)
            with x1.popover("Paguei", icon=":material/check_circle:", width="stretch"):
                with st.form(f"pgdoc_{r.id}"):
                    v = st.number_input("Valor pago (R$)", min_value=0.0, step=10.0, format="%.2f",
                                        value=float(r.valor) if r.valor is not None and str(r.valor) != "nan" else 0.0)
                    dp = st.date_input("Pago em", value=h, format="DD/MM/YYYY")
                    prox = st.date_input("Próximo vencimento", value=somar_meses(r.vencimento, 12), format="DD/MM/YYYY")
                    if st.form_submit_button("Confirmar", type="primary"):
                        repo.pagar_documento_van(cid, r.id, v, dp, prox)
                        st.toast(f"{r.tipo}: pago" + (" e lançado no Financeiro." if v else "."))
                        st.rerun()
            if x2.button("Excluir", key=f"exdoc_{r.id}", icon=":material/delete:", type="tertiary"):
                repo.excluir_documento_van(cid, r.id)
                st.rerun()
    with st.expander("➕ Adicionar documento", expanded=df.empty):
        with st.form("novo_doc", clear_on_submit=True):
            a, b = st.columns(2)
            tipo = a.selectbox("Documento", list(repo.DOC_TIPOS))
            _ops = list(opc_van)
            van = b.selectbox("Van", _ops, format_func=opc_van.get,
                              index=_ops.index(str(so_van)) if so_van and str(so_van) in _ops else (1 if len(_ops) > 1 else 0))
            c1, c2 = st.columns(2)
            venc = c1.date_input("Vencimento", value=h + timedelta(days=30), format="DD/MM/YYYY")
            valor = c2.number_input("Valor (R$, opcional)", min_value=0.0, step=10.0, format="%.2f")
            obs = st.text_input("Observação (opcional)", placeholder="Ex.: seguradora, nº da apólice…")
            if st.form_submit_button("Salvar documento", type="primary"):
                repo.salvar_documento_van(cid, dict(van_id=van, tipo=tipo, vencimento=venc,
                                                    valor=valor or None, obs=obs or None))
                st.toast("Documento salvo.")
                st.rerun()


# ---------------------------------------------------------------- cadastro por etapas e ficha
def etapas(titulos: list[str], atual: int):
    """Barrinha de etapas no topo do cadastro: ● feito, ◉ atual, ○ falta."""
    partes = []
    for i, t in enumerate(titulos):
        cls = "feito" if i < atual else ("atual" if i == atual else "")
        partes.append(f"<div class='e {cls}'><span>{'✓' if i < atual else i + 1}</span><b>{esc(t)}</b></div>")
    st.markdown(f"<div class='ve-etapas'>{''.join(partes)}</div>", unsafe_allow_html=True)


def linha_ficha(rotulo: str, sub: str, chave: str, icone: str) -> bool:
    """Linha tocável da ficha (Responsáveis ›, Endereço ›…). Devolve True quando tocada."""
    with st.container(key=f"fl_{chave}"):
        return st.button(f"**{rotulo}**  \n{sub}" if sub else f"**{rotulo}**", key=f"flb_{chave}", icon=icone,
                         width="stretch")


# ---------------------------------------------------------------- vídeos "Aprenda a usar"
TUTORIAIS = {
    "aluno": ("Cadastrar um aluno", "Novo aluno em 4 etapas: aluno, responsável, escola e pagamento."),
    "rota": ("Fazer a rota do dia", "Iniciar a rota, avisar os pais e marcar quem embarcou."),
    "cobranca": ("Cobrar e receber mensalidades", "Cobrar no WhatsApp com o Pix e dar baixa quando receber."),
    "despesa": ("Lançar uma despesa", "Combustível, manutenção… e contas a pagar."),
}


def _arquivo_tutorial(nome: str):
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "static" / "tutoriais" / f"{nome}.mp4"
    return p if p.exists() else None


def video_ajuda(nome: str):
    """Botãozinho ▶ 'Ver como faz' que abre o vídeo daquela tela num quadro por cima."""
    arq = _arquivo_tutorial(nome)
    if not arq:
        return
    titulo = TUTORIAIS[nome][0]

    @st.dialog(titulo)
    def _ver():
        st.video(str(arq), autoplay=True, muted=True)

    with st.container(key=f"vidbtn_{nome}"):
        if st.button("Ver como faz", icon=":material/play_circle:", type="tertiary", key=f"vid_{nome}"):
            _ver()
