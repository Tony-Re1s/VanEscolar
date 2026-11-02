"""Tela inicial do condutor: o dia de hoje e o que precisa de atenção."""
from datetime import timedelta

import streamlit as st

from core import repo
from core.fmt import DIAS_SEMANA, brl, data_br, hoje, inicio_mes, mes_label, somar_meses
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
_ui.guia(c, "telas/hoje.py")
if alunos.empty:
    st.stop()

mens = repo.mensalidades_mes(cid, h, h)
rec = mens["valor_pago"].fillna(0).astype(float).sum() if not mens.empty else 0
prev = mens["valor"].astype(float).sum() if not mens.empty else 0
res = repo.resumo_meses(cid, inicio_mes(h), somar_meses(inicio_mes(h), 1)).iloc[0]
lucro = float(res["mensalidades"]) + float(res["outras_receitas"]) - float(res["despesas"])
_ui.olho()
_ui.kpis([("Lucro do mês", brl(lucro), mes_label(h)),
          ("Recebido", brl(rec), f"de {brl(prev)} previstos"),
          ("Alunos ativos", len(alunos), f"{len(vans)} van(s) · {int(vans['capacidade'].sum()) if len(vans) else 0} lugares"),
          ("Despesas do mês", brl(res["despesas"]))])
_ui.meta_mes(rec, prev)

# atalhos grandes
from core import planos as _pl  # noqa: E402
_em_pausa = _pl.em_pausa(repo.empresa(cid), h)
_at = st.container(key="atalhos").columns(3)
if not _em_pausa:
    with _at[0].container(key="atalho_rota"):
        st.page_link("telas/chamada.py", label="Iniciar rota", icon=":material/airport_shuttle:", width="stretch")
with _at[1].container(key="atalho_aluno"):
    if st.button("+ Aluno", icon=":material/person_add:", width="stretch", key="at_novo_aluno"):
        st.session_state.update(al_modo="novo", al_rasc={}, al_etapa=0, al_pid=None, al_sec=None)
        st.switch_page("telas/alunos.py")
with _at[2].container(key="atalho_cobrar"):
    st.page_link("telas/mensalidades.py", label="Cobrar", icon=":material/chat:", width="stretch")

# hoje: faltas avisadas (o que muda a rota de agora)
aus = repo.ausencias_empresa(cid, h)
varias_vans = len(vans) > 1
hoje_aus = aus[aus["data"] == h] if not aus.empty else aus
if _em_pausa:
    st.caption("⏸️ Pausa de férias: rota e chamada estão pausadas (veja em Meu plano).")
elif hoje_aus.empty:
    st.success("Nenhum aviso de falta para hoje.", icon=":material/check_circle:")
else:
    for r in hoje_aus.itertuples():
        trechos = " e ".join(t for t, v in (("ida", r.ida), ("volta", r.volta)) if v)
        st.warning(f"**{r.nome}**{f' ({r.van})' if varias_vans and r.van else ''} não vai hoje ({trechos})"
                   f"{' — ' + r.motivo if r.motivo else ''}", icon=":material/event_busy:")
prox = aus[aus["data"] > h] if not aus.empty else aus
if not prox.empty:
    st.caption("Próximas faltas: " + "; ".join(f"{r.nome} ({data_br(r.data)})" for r in prox.itertuples()))

# precisa de atenção: só contadores clicáveis — o detalhe fica na tela de cada assunto
_af = repo.alunos_facil(cid)
_af = _af[_af["ativo"]] if not _af.empty else _af
_sem_valor = int((_af["valor"].fillna(0).astype(float) <= 0).sum()) if not _af.empty else 0
_sem_zap = int(_af["whatsapp"].isna().sum() + (_af["whatsapp"].fillna("x") == "").sum()) if not _af.empty else 0
_atras = repo.vencidas_todas(cid, h)
_abertas = repo.mensalidades_em_aberto(cid, h)
_vencendo = int((_abertas["situacao"] != "vencido").sum()) if not _abertas.empty else 0
_cp = repo.contas_a_pagar(cid)
_cp = _cp[_cp["data"] <= h + timedelta(days=7)] if not _cp.empty else _cp
_docs = repo.documentos_van(cid, ate=h + timedelta(days=30))
_fr = (repo.fretes(cid, ["fechado"], h, h + timedelta(days=7))
       if _pl.tem_fretamento(repo.empresa(cid), h) else None)
_pend = [("telas/mensalidades.py", "Mensalidades atrasadas", len(_atras), ":material/warning:"),
         ("telas/mensalidades.py", "Mensalidades vencendo (7 dias)", _vencendo, ":material/schedule:"),
         ("telas/financeiro.py", "Contas a pagar (até 7 dias)", len(_cp), ":material/event_upcoming:"),
         ("telas/vans.py", "Documentos da van vencendo", len(_docs), ":material/description:"),
         ("telas/fretamento.py", "Fretamentos nos próximos 7 dias", 0 if _fr is None else len(_fr), ":material/tour:"),
         ("telas/alunos.py", "Aluno sem valor de mensalidade", _sem_valor, ":material/money_off:"),
         ("telas/alunos.py", "Aluno sem WhatsApp do responsável", _sem_zap, ":material/phone_disabled:")]
_pend = [x for x in _pend if x[2]]
st.subheader("Precisa de atenção")
if not _pend:
    st.success("Tudo em dia por aqui. 🎉", icon=":material/task_alt:")
with st.container(key="pendencias"):
    for _pg, _txt, _n, _ic in _pend:
        st.page_link(_pg, label=f"{_txt} · {_n}", icon=_ic, width="stretch")

# aniversariantes do mês — só aparece quando tem
niver = alunos[alunos["data_nasc"].notna()]
niver = niver[niver["data_nasc"].map(lambda d: d.month == h.month)]
if not niver.empty:
    st.subheader("🎂 Aniversariantes do mês")
    st.markdown(" · ".join(f"**{r.nome.split()[0]}** ({r.data_nasc.day:02d}/{r.data_nasc.month:02d})"
                           for r in niver.sort_values("data_nasc", key=lambda s: s.map(lambda d: d.day)).itertuples()))
