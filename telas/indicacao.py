"""Indique e ganhe: código do gestor, link para compartilhar, progresso e meses grátis."""
import urllib.parse

import streamlit as st

from core import planos as pl, repo
from core.fmt import data_br, hoje
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
repo.garantir_codigo_indicacao(c["id"])
emp = repo.empresa(c["id"])
cfg = pl.config("indicacao")
cat = pl.catalogo()

st.title("Indique e ganhe")
if not cfg.get("ativo"):
    st.info("O programa de indicação está pausado no momento.")
    st.stop()

meta, premio = int(cfg["meta"]), int(cfg["premio_meses"])
plano_d, dias_d = cat[cfg["plano_degustacao"]]["nome"], int(cfg["dias_degustacao"])
codigo = emp["codigo_indicacao"]
link = f"{_ui.APP_URL}/?indicacao={codigo}"
pagas = int(emp.get("indicacoes_pagas") or 0)
no_ciclo = pagas % meta
mg = int(emp.get("meses_gratis") or 0)

st.markdown(f"<div class='ve-faixa'>🎁 A cada <b>{meta} transportadores</b> que você indicar e que <b>assinarem</b>, "
            f"você ganha <b>{premio} mensalidade{'s' if premio != 1 else ''} grátis</b> — e acumula! "
            f"Quem você indicar ganha <b>{dias_d} dias do plano {plano_d}</b> de presente.</div>",
            unsafe_allow_html=True)

_ui.kpis([("Seu código", codigo), ("Indicados que assinaram", str(pagas)),
          ("Próximo prêmio", f"{no_ciclo} de {meta}"), ("Meses grátis guardados", str(mg))])
st.progress(no_ciclo / meta, text=f"Faltam {meta - no_ciclo} assinante(s) para ganhar mais {premio} mês(es) grátis")

st.subheader("Compartilhe")
msg = (f"Oi! Uso o Turminha a Bordo para organizar minha van escolar: rota, chamada, mensalidades e contrato, "
       f"tudo no celular 🚐 Entrando pelo meu link você ganha {dias_d} dias do plano {plano_d} grátis: {link} "
       f"(ou use o código {codigo} ao criar a conta).")
st.code(link, language=None)
st.link_button("Mandar no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}",
               icon=":material/send:", type="primary")
st.caption("Vale para quem ainda não tem conta: a pessoa entra pelo link (ou digita o seu código ao criar a empresa).")

st.subheader("Seus indicados")
ind = repo.indicados(c["id"])
if ind.empty:
    st.caption("Ninguém ainda — mande o link para os colegas de outras vans!")
for r in ind.to_dict("records"):
    if r["indicacao_contada"]:
        st_ = _ui.tag("pago", "assinou ✓ contou")
    elif r["plano"] and r["plano_tipo"] == "teste" and r["plano_ate"] and r["plano_ate"] >= hoje():
        st_ = _ui.tag("embarcou", f"em degustação até {data_br(r['plano_ate'])}")
    else:
        st_ = _ui.tag("aberto", "ainda não assinou")
    st.markdown(f"**{_ui.esc(r['nome'])}** {st_} <span class='ve-sub'>· desde {data_br(r['desde'])}</span>",
                unsafe_allow_html=True)
