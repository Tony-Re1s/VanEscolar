"""Operação (gestor): panorama ao vivo de cada van — rota iniciada, localização, quem já foi entregue, faltas."""
import pandas as pd
import streamlit as st

from core import repo
from core.fmt import TZ, agora, hoje
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
st.title("Operação")
st.caption("Panorama do dia por van. Atualiza sozinho a cada 30 segundos.")

padrao = "ida" if agora().hour < 11 or 13 <= agora().hour < 15 else "volta"
trecho = st.segmented_control("Trecho", ["ida", "volta"], default=padrao, key="op_trecho",
                              format_func=lambda t: "🏠 → 🏫 Ida" if t == "ida" else "🏫 → 🏠 Volta") or padrao


@st.fragment(run_every=30)
def _painel():
    dia = hoje()
    vans = repo.vans(cid)
    if vans.empty:
        st.info("Nenhuma van cadastrada.")
        return
    emails = [e for e in list(vans["motorista_email"].dropna()) + list(vans["monitor_email"].dropna())]
    ac = repo.acessos(emails)
    tot = dict(alunos=0, feitos=0, faltas=0, rodando=0)
    pontos = []
    cards = []
    for v in vans.itertuples():
        df = repo.chamada_dia(cid, v.id, dia, trecho)
        n = len(df)
        feitos = int(df["status"].isin(["desembarcou", "embarcou"]).sum()) if n else 0
        faltas = int(((df["status"] == "faltou") | df["avisou"]).sum()) if n else 0
        ini = repo.rota_iniciada(v.id, dia, trecho)
        loc = repo.localizacao_van(cid, v.id) or {}
        tot["alunos"] += n
        tot["feitos"] += feitos
        tot["faltas"] += faltas
        tot["rodando"] += 1 if ini is not None else 0
        if loc.get("loc_lat") is not None:
            pontos.append(dict(lat=loc["loc_lat"], lon=loc["loc_lng"], van=v.nome))
        cards.append((v, df, n, feitos, faltas, ini, loc))

    _ui.kpis([("Vans em rota", f"{tot['rodando']} de {len(vans)}"), ("Alunos no trecho", str(tot["alunos"])),
              ("Ida concluída" if trecho == "ida" else "Entregues", str(tot["feitos"])),
              ("Faltas / avisos", str(tot["faltas"]))], destaque=None)
    if pontos:
        st.map(pd.DataFrame(pontos), zoom=11, size=60, color="#0A9C97", height=320)

    for v, df, n, feitos, faltas, ini, loc in cards:
        with st.container(border=True, key=f"card_op_{v.id}"):
            equipe = v.motorista_nome or "sem motorista"
            if v.monitor_nome:
                equipe += f" · monitor(a): {v.monitor_nome}"
            if ini is None:
                sit = _ui.tag("aberto", "rota não iniciada")
            elif n and feitos + faltas >= n:
                sit = _ui.tag("pago", "trecho concluído ✓")
            else:
                sit = _ui.tag("embarcou", f"em rota desde {ini.astimezone(TZ):%H:%M}")
            st.markdown(f"**🚐 {_ui.esc(v.nome)}** {sit}  \n<span class='ve-sub'>{_ui.esc(equipe)}</span>",
                        unsafe_allow_html=True)
            pend = max(0, n - feitos - faltas)
            st.progress(feitos / n if n else 0.0,
                        text=f"{feitos} de {n} {'na escola' if trecho == 'ida' else 'entregues'} · "
                             f"{pend} pendente(s) · {faltas} falta(s)")
            linhas = []
            if loc.get("ativa") and loc.get("loc_em") is not None:
                minutos = int((agora() - loc["loc_em"].astimezone(TZ)).total_seconds() // 60)
                linhas.append(f"📍 última posição às {loc['loc_em'].astimezone(TZ):%H:%M}"
                              + (" (agora há pouco)" if minutos < 2 else f" (há {minutos} min)"))
            elif loc.get("loc_em") is not None:
                linhas.append(f"📍 localização desligada · última às {loc['loc_em'].astimezone(TZ):%d/%m %H:%M}")
            else:
                linhas.append("📍 localização ainda não usada")
            ult = ac.get((v.motorista_email or "").lower()) if v.motorista_email else None
            if ult is not None:
                linhas.append(f"👤 motorista abriu o app às {ult.astimezone(TZ):%d/%m %H:%M}")
            elif v.motorista_email:
                linhas.append("👤 motorista ainda não entrou no app")
            st.caption("  ·  ".join(linhas))
            if n:
                faltando = df[~df["status"].isin(["desembarcou", "embarcou", "faltou"]) & ~df["avisou"]]
                if len(faltando):
                    st.caption("Pendentes: " + ", ".join(faltando["nome"]))
            if loc.get("ativa") and loc.get("loc_lat") is not None:
                st.link_button("Ver no Google Maps", f"https://www.google.com/maps?q={loc['loc_lat']},{loc['loc_lng']}",
                               icon=":material/map:")


_painel()
