"""Canal do divulgador (perfil Exclusivo): contador ao vivo das vagas VIP, textos prontos com o link de indicação,
comissão sobre os indicados ativos e as novidades que estão em teste (laboratório)."""
import urllib.parse

import pandas as pd
import streamlit as st

from core import comissao, planos as pl, repo
from core.fmt import data_br, hoje
from telas import _ui

u = st.session_state["usuario"]
c = u.get("condutor")
HOJE = hoje()
emp = repo.empresa(c["id"]) if c else None
if not (u.get("admin") or (emp and pl.eh_exclusivo(emp, HOJE))):
    st.warning("Esta área é dos parceiros **Exclusivos** do Pequenos a Bordo.")
    st.stop()

if emp:
    repo.garantir_codigo_indicacao(emp["id"])
    emp = repo.empresa(emp["id"])
codigo = (emp or {}).get("codigo_indicacao") or "SEUCODIGO"
link = f"{_ui.APP_URL}/?indicacao={codigo}"
cat = pl.catalogo()
cfg_vip = pl.config("vip")
cfg_ind = pl.config("indicacao")
cfg_deg = pl.config("degustacao")
dias = int(cfg_ind.get("dias_degustacao") or 0) if cfg_ind.get("ativo") else int(cfg_deg.get("dias") or 0)

st.title("Canal do divulgador")
st.markdown("<div class='ve-faixa'>⭐ Você é parceiro <b>Exclusivo</b>: tem o app completo, recebe as novidades "
            "primeiro e ganha comissão sobre os assinantes que indicar.</div>", unsafe_allow_html=True)
if not emp:
    st.caption("Você está vendo como administrador (sem empresa): os textos usam o código de exemplo.")


# ---------------------------------------------------------------- vagas VIP ao vivo
@st.fragment(run_every=30)
def _vagas():
    usadas = repo.vip_usadas()
    total = int(cfg_vip.get("vagas") or 0)
    livres = pl.vip_livres(cfg_vip, usadas, HOJE)
    with st.container(border=True, key="card_vagas_vip"):
        a, b = st.columns([1, 2])
        a.metric("Vagas VIP restantes", livres)
        if total:
            b.progress(min(1.0, usadas / total), text=f"{usadas} de {total} já garantiram o preço VIP")
        b.caption("Atualiza sozinho a cada 30 segundos." +
                  ("" if cfg_vip.get("ativo") else " · O Passageiro VIP está pausado."))
    return livres


livres = _vagas()

# ---------------------------------------------------------------- textos prontos
st.subheader("Textos prontos para divulgar")
st.caption("Copie (botão no canto do quadro) e cole onde quiser, ou abra o WhatsApp já com o texto — você escolhe "
           "para quem mandar. O número de vagas é o de agora.")
valores = dict(link=link, codigo=codigo, vagas=pl.vip_livres(cfg_vip, repo.vip_usadas(), HOJE),
               nome=(emp or {}).get("nome") or "", dias=dias,
               vip_basico=pl.brl(cat.get("basico", {}).get("preco_vip") or 0),
               vip_pro=pl.brl(cat.get("pro", {}).get("preco_vip") or 0))
textos = (pl.config("divulgacao") or {}).get("textos") or []
for i, t in enumerate(textos):
    txt = pl.texto_divulgacao(t.get("texto", ""), valores)
    with st.container(border=True, key=f"card_txt_{i}"):
        st.markdown(f"**{_ui.esc(t.get('titulo') or f'Texto {i + 1}')}**")
        st.code(txt, language=None, wrap_lines=True)
        st.link_button("Abrir no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(txt)}", icon=":material/send:",
                       key=f"wa_txt_{i}")
st.markdown("**Seu link**")
st.code(link, language=None)

# ---------------------------------------------------------------- comissão
st.subheader("Sua comissão")
if not emp:
    st.caption("A comissão aparece aqui para cada parceiro Exclusivo.")
else:
    s = comissao.situacao(emp["id"], HOJE)
    if not s["ativo"]:
        st.info("A comissão está pausada no momento.")
    else:
        pct = f"{s['pct']:g}%"
        st.markdown(f"Ao chegar a **{s['meta']} indicados pagando ao mesmo tempo**, você destrava **{pct} todo mês** "
                    f"sobre o que os seus indicados **ativos** pagam" +
                    (f", até **{data_br(pd.Timestamp(s['ate']).date())}**." if s["ate"] else ".") +
                    " Se algum sair, a comissão é sobre os que continuam.")
        if s["desde"]:
            _ui.kpis([("Indicados pagando agora", str(s["ativos"])),
                      ("Eles pagam por mês", pl.brl(s["base"])),
                      (f"Sua comissão ({s['competencia']:%m/%Y})", pl.brl(s["valor"]))], destaque=2)
            st.success(f"Comissão destravada em {data_br(s['desde'])}. ✅", icon=":material/lock_open:")
            if not s["vigente"]:
                st.caption("O período da comissão terminou.")
        else:
            _ui.kpis([("Indicados pagando agora", str(s["ativos"])), ("Meta", str(s["meta"])),
                      ("Faltam", str(s["faltam"]))])
            st.progress(min(1.0, s["ativos"] / max(1, s["meta"])),
                        text=f"{s['ativos']} de {s['meta']} — faltam {s['faltam']} para destravar a comissão")
        with st.form("pix_div"):
            pix = st.text_input("Chave Pix para receber a comissão", value=emp.get("chave_pix") or "")
            if st.form_submit_button("Salvar chave Pix"):
                repo.salvar_chave_pix(emp["id"], pix)
                st.toast("Chave Pix salva.")
                st.rerun()
        h = comissao.historico(emp["id"])
        if not h.empty:
            st.markdown("**Histórico**")
            st.dataframe(pd.DataFrame({
                "Mês": [f"{m:%m/%Y}" for m in h["competencia"]],
                "Indicados ativos": h["ativos"],
                "Base": [pl.brl(v) for v in h["base"]],
                "Comissão": [pl.brl(v) for v in h["valor"]],
                "Situação": ["pago em " + data_br(p) if p else "a receber" for p in h["pago_em"]],
            }), hide_index=True, width="stretch")

    ind = repo.indicados(emp["id"])
    st.markdown(f"**Seus indicados ({len(ind)})**")
    if ind.empty:
        st.caption("Ninguém ainda — use os textos acima!")
    else:
        st.dataframe(pd.DataFrame({
            "Empresa": ind["nome"],
            "Situação": [pl.TIPOS.get(t, t) if (p and a and a >= HOJE) or t == "cortesia" else "sem plano"
                         for t, p, a in zip(ind["plano_tipo"], ind["plano"], ind["plano_ate"])],
            "Desde": [data_br(d) for d in ind["desde"]],
        }), hide_index=True, width="stretch")

# ---------------------------------------------------------------- laboratório
lab = pl.config("laboratorio") or {}
em_teste = [k for k in pl.RECURSOS if lab.get(k) == "exclusivo"]
st.subheader("Novidades em teste 🧪")
if em_teste:
    st.caption("Só os Exclusivos veem estes recursos por enquanto. Use e conte para o Tony o que achou!")
    for k in em_teste:
        st.markdown(f"- {pl.RECURSOS[k]}")
else:
    st.caption("Nenhuma novidade em teste agora. Quando houver, aparece aqui primeiro para você.")
