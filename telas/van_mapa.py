"""Página pública do link "ver a van no mapa" (sem login). Mostra só a van e a empresa — nenhum dado de criança.
O link expira quando o motorista para a localização (ou depois de algumas horas)."""
import pandas as pd
import streamlit as st

from core import repo
from core.fmt import TZ, agora
from telas import _ui

token = str(st.query_params.get("van", ""))[:40]

d = repo.posicao_publica(token)
if not d:
    st.title("Onde está a van")
    st.error("Link inválido. Peça um novo link ao motorista.", icon=":material/link_off:")
    st.stop()

st.title(f"🚐 {d['van']}")
st.caption(_ui.esc(d["empresa"]))


@st.fragment(run_every=20)
def _mapa():
    p = repo.posicao_publica(token) or {}
    if not p.get("ativa"):
        st.info("A localização desta rota foi encerrada. 🙂 Quando a van sair de novo, o motorista manda outro link.",
                icon=":material/check_circle:")
        return
    if p.get("loc_lat") is None:
        st.info("A rota começou — aguardando a primeira posição do celular do motorista…", icon=":material/hourglass_top:")
        return
    quando = p["loc_em"].astimezone(TZ)
    minutos = int((agora() - quando).total_seconds() // 60)
    st.map(pd.DataFrame({"lat": [p["loc_lat"]], "lon": [p["loc_lng"]]}), zoom=15, size=40, color="#0A9C97",
           height=420)
    atraso = "agora há pouco" if minutos < 1 else f"há {minutos} min"
    st.markdown(f"**Última posição: {quando:%H:%M}** ({atraso})" +
                (f" · precisão ~{int(p['loc_precisao'])} m" if p.get("loc_precisao") else ""))
    if minutos >= 3:
        st.caption("A posição pode estar parada porque o motorista está sem sinal ou com o app fechado.")
    st.link_button("Abrir no Google Maps", f"https://www.google.com/maps?q={p['loc_lat']},{p['loc_lng']}",
                   icon=":material/map:")
    st.caption("Atualiza sozinho a cada 20 segundos.")


_mapa()
