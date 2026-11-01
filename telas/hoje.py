"""Tela inicial do condutor: o dia de hoje e o que precisa de atenção."""
import streamlit as st

from core import repo
from core.fmt import DIAS_SEMANA, brl, data_br, hoje, inicio_mes, link_whats, mes_label, somar_meses
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
h = hoje()
primeiro = c["nome"].split()[0]
st.title(f"Olá, {primeiro}! 👋")
st.caption(f"{DIAS_SEMANA[h.weekday()].capitalize()}, {data_br(h)}")

if st.session_state.get("_mens_gerado") != (cid, inicio_mes(h)):
    repo.gerar_mensalidades(cid, h)
    st.session_state["_mens_gerado"] = (cid, inicio_mes(h))

alunos = repo.passageiros(cid)
vans = repo.vans(cid)
if alunos.empty:
    st.info("**Primeiros passos**\n\n1. Cadastre as **Vans** e quem dirige cada uma\n2. Cadastre as **Escolas**\n"
            "3. Cadastre os **Alunos** (com a van) e os responsáveis — com o e-mail do Google, para os pais acessarem\n"
            "4. Use **Rota e chamada** todo dia\n5. Em **Minha empresa**, coloque a chave Pix e o vencimento padrão; "
            "as **Mensalidades** do mês são geradas sozinhas", icon=":material/rocket_launch:")
    c1, c2, c3 = st.columns(3)
    c1.page_link("telas/vans.py", label="Vans e motoristas", icon=":material/airport_shuttle:")
    c2.page_link("telas/escolas.py", label="Escolas", icon=":material/school:")
    c3.page_link("telas/alunos.py", label="Alunos", icon=":material/groups:")
    st.stop()

mens = repo.mensalidades_mes(cid, h, h)
rec = mens["valor_pago"].fillna(0).astype(float).sum() if not mens.empty else 0
prev = mens["valor"].astype(float).sum() if not mens.empty else 0
res = repo.resumo_meses(cid, inicio_mes(h), somar_meses(inicio_mes(h), 1)).iloc[0]
lucro = float(res["mensalidades"]) + float(res["outras_receitas"]) - float(res["despesas"])
_ui.kpis([("Lucro do mês", brl(lucro), mes_label(h)),
          ("Recebido", brl(rec), f"de {brl(prev)} previstos"),
          ("Alunos ativos", len(alunos), f"{len(vans)} van(s) · {int(vans['capacidade'].sum()) if len(vans) else 0} lugares"),
          ("Despesas do mês", brl(res["despesas"]))])

# faltas avisadas
aus = repo.ausencias_empresa(cid, h)
varias_vans = len(vans) > 1
hoje_aus = aus[aus["data"] == h] if not aus.empty else aus
st.subheader("Hoje")
if hoje_aus.empty:
    st.success("Nenhum aviso de falta para hoje.", icon=":material/check_circle:")
else:
    for r in hoje_aus.itertuples():
        trechos = " e ".join(t for t, v in (("ida", r.ida), ("volta", r.volta)) if v)
        st.warning(f"**{r.nome}**{f' ({r.van})' if varias_vans and r.van else ''} não vai ({trechos})"
                   f"{' — ' + r.motivo if r.motivo else ''}",
                   icon=":material/event_busy:")
prox = aus[aus["data"] > h] if not aus.empty else aus
if not prox.empty:
    st.caption("Próximas faltas avisadas: " + "; ".join(f"{r.nome} ({data_br(r.data)})" for r in prox.itertuples()))
from core import planos as _pl  # noqa: E402
if _pl.em_pausa(repo.empresa(c["id"]), h):
    st.caption("⏸️ Pausa de férias: rota e chamada estão pausadas (veja em Meu plano).")
else:
    st.page_link("telas/chamada.py", label="Abrir rota e chamada", icon=":material/fact_check:")

# a receber
st.subheader("Mensalidades para cobrar")
abertas = repo.mensalidades_em_aberto(cid, h)
if abertas.empty:
    st.success("Nada vencido nem vencendo nos próximos 7 dias.", icon=":material/payments:")
else:
    for r in abertas.itertuples():
        a, b, x = st.container(key=f"lp_{r.id}").columns([3, 2, 1])
        a.markdown(f"**{_ui.esc(r.aluno)}** {_ui.tag(r.situacao, _ui.ROTULO_MENS[r.situacao])}  \n"
                   f"<span class='ve-sub'>{mes_label(r.competencia, curto=True)} · vence {data_br(r.vencimento)}</span>",
                   unsafe_allow_html=True)
        b.markdown(f"**{brl(r.valor)}**")
        txt = (f"Olá! Lembrete da mensalidade da van de {r.aluno} ({mes_label(r.competencia)}): {brl(r.valor)}, "
               f"vencimento {data_br(r.vencimento)}." + (f"\nChave Pix: {c['chave_pix']}" if c.get("chave_pix") else ""))
        link = link_whats(r.telefone, txt)
        if link:
            x.link_button("", link, icon=":material/chat:", help="Cobrar no WhatsApp")
    st.page_link("telas/mensalidades.py", label="Ver todas as mensalidades", icon=":material/payments:")

# aniversários do mês
niver = alunos[alunos["data_nasc"].notna()]
niver = niver[niver["data_nasc"].map(lambda d: d.month == h.month)]
if not niver.empty:
    st.subheader("🎂 Aniversariantes do mês")
    st.markdown(" · ".join(f"**{r.nome.split()[0]}** ({r.data_nasc.day:02d}/{r.data_nasc.month:02d})"
                           for r in niver.sort_values("data_nasc", key=lambda s: s.map(lambda d: d.day)).itertuples()))
