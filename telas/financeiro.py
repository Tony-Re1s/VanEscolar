"""Financeiro: despesas, outras receitas, lucro do mês e dos últimos 12 meses (regime de caixa)."""
import altair as alt
import pandas as pd
import streamlit as st

from core import planos as pl, repo
from core.fmt import CAT_DESPESA, CAT_RECEITA, brl, data_br, hoje, inicio_mes, mes_label, somar_meses
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
h = hoje()
st.title("Financeiro")

meses = [somar_meses(inicio_mes(h), i) for i in range(-24, 1)]
comp = st.select_slider("Mês", options=meses, value=inicio_mes(h), format_func=lambda d: mes_label(d, curto=True))
prox = somar_meses(comp, 1)
van = _ui.filtro_van(cid, "van_fin", "Ver")
vans = repo.vans(cid)
ORIGENS = {"tudo": "Tudo", "escolar": "Transporte escolar", "frete": "Fretamento"}
origem = None
if pl.tem_fretamento(repo.empresa(cid), h):
    origem = st.segmented_control("Mostrar", list(ORIGENS), format_func=ORIGENS.get, default="tudo", key="fin_origem")
    origem = None if origem in (None, "tudo") else origem

res = repo.resumo_meses(cid, somar_meses(comp, -11), prox, van=van, origem=origem)
mes = res.iloc[-1]
receita = float(mes["mensalidades"]) + float(mes["outras_receitas"])
desp = float(mes["despesas"])
if origem == "frete":
    fr = repo.fretes(cid, ["fechado", "realizado"])
    a_rec = sum(max(float(r.valor or 0) - float(r.recebido or 0), 0) for r in fr.itertuples()) if not fr.empty else 0
    _ui.kpis([("Lucro do mês", brl(receita - desp), "fretamentos: recebido − gastos"),
              ("Recebido", brl(receita), "dos fretamentos"),
              ("Gastos", brl(desp), "das viagens"),
              ("A receber", brl(a_rec), "de viagens fechadas")])
else:
    mens = repo.mensalidades_mes(cid, comp, h, van=van)
    inad = mens.loc[mens["situacao"] == "vencido", "valor"].astype(float).sum() if not mens.empty else 0
    _ui.kpis([("Lucro do mês", brl(receita - desp), "recebido − despesas"),
              ("Recebido", brl(receita), f"mensalidades {brl(mes['mensalidades'])}"),
              ("Despesas", brl(desp)),
              ("Inadimplência", brl(inad), "mensalidades vencidas do mês")])

abas = ["Lançar", "Lançamentos do mês", "12 meses"] + (["Por van"] if len(vans) > 1 else [])
aba_lancar, aba_mes, aba_ano, *aba_van = st.tabs(abas)

with aba_lancar:
    tipo = st.segmented_control("Tipo", ["despesa", "receita"], default="despesa",
                                format_func=lambda t: "Despesa" if t == "despesa" else "Outra receita",
                                label_visibility="collapsed") or "despesa"
    with st.form("lanc", clear_on_submit=True):
        a, b = st.columns(2)
        cat = a.selectbox("Categoria", CAT_DESPESA if tipo == "despesa" else CAT_RECEITA)
        valor = b.number_input("Valor (R$)", min_value=0.0, step=10.0)
        a2, b2 = st.columns(2)
        data = a2.date_input("Data", value=h if comp == inicio_mes(h) else comp, format="DD/MM/YYYY")
        km = b2.number_input("Hodômetro (km, opcional)", min_value=0, step=100, value=0)
        if not vans.empty:
            v_ids = [None] + [str(x) for x in vans["id"]]
            v_nomes = {None: "Geral (sem van)"} | {str(r.id): r.nome for r in vans.itertuples()}
            van_l = st.selectbox("Van", v_ids, index=v_ids.index(van) if van in v_ids else 0,
                                 format_func=v_nomes.get, help="Combustível, manutenção etc. de uma van específica. "
                                 "Contador, celular e MEI podem ficar como Geral.")
        else:
            van_l = None
        desc = st.text_input("Descrição", placeholder="Ex.: troca de óleo, posto X, passeio ao zoológico")
        st.caption("Mensalidades entram sozinhas quando você marca como recebidas — não precisa lançar aqui.")
        if st.form_submit_button("Lançar", type="primary"):
            if valor <= 0:
                st.error("Informe o valor.")
            else:
                repo.salvar_lancamento(cid, dict(van_id=van_l, tipo=tipo, categoria=cat, descricao=desc or None, valor=valor,
                                                 data=data, km=km or None))
                st.toast("Lançado.")
                st.rerun()

with aba_mes:
    lan = repo.lancamentos(cid, comp, prox, van=van, origem=origem)
    if lan.empty:
        st.info(f"Nenhum lançamento em {mes_label(comp)}.")
    else:
        cats = repo.despesas_por_categoria(cid, comp, prox, van=van, origem=origem)
        if not cats.empty:
            cats["valor"] = cats["valor"].astype(float)
            st.altair_chart(alt.Chart(cats).mark_bar(cornerRadiusEnd=6, color="#0ABAB5").encode(
                x=alt.X("valor:Q", title=None, axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")),
                y=alt.Y("categoria:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("categoria:N", title="Categoria"),
                         alt.Tooltip("valor:Q", title="R$", format=",.2f")]).properties(height=36 * len(cats) + 20),
                width="stretch")
        for r in lan.itertuples():
            a, b, x = st.container(key=f"lp_{r.id}").columns([4, 2, 1])
            sinal = "−" if r.tipo == "despesa" else "+"
            a.markdown(f"**{_ui.esc(r.categoria)}** <span class='ve-sub'>{data_br(r.data)}"
                       f"{' · ' + _ui.esc(r.descricao) if r.descricao else ''}{f' · {r.km} km' if r.km else ''}"
                       f"{' · 🚐 ' + _ui.esc(r.van) if r.van and len(vans) > 1 else ''}"
                       f"{' · 🧭 fretamento' if getattr(r, 'frete_id', None) and str(r.frete_id) not in ('None', 'nan') else ''}</span>",
                       unsafe_allow_html=True)
            b.markdown(f"{sinal} {brl(r.valor)}")
            if x.button("", icon=":material/delete:", key=f"del_{r.id}", type="tertiary", help="Excluir"):
                repo.excluir_lancamento(cid, r.id)
                st.rerun()

with aba_ano:
    res = res.assign(receitas=res["mensalidades"].astype(float) + res["outras_receitas"].astype(float),
                     despesas=res["despesas"].astype(float))
    res["lucro"] = res["receitas"] - res["despesas"]
    res["mes_txt"] = res["mes"].map(lambda d: mes_label(d, curto=True))
    longo = res.melt(id_vars=["mes_txt", "mes"], value_vars=["receitas", "despesas"], var_name="tipo", value_name="v")
    ordem = list(res["mes_txt"])
    barras = alt.Chart(longo).mark_bar().encode(
        x=alt.X("mes_txt:N", sort=ordem, title=None), xOffset="tipo:N",
        y=alt.Y("v:Q", title=None, axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")),
        color=alt.Color("tipo:N", scale=alt.Scale(domain=["receitas", "despesas"], range=["#0ABAB5", "#FF8A80"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("tipo:N", title=""),
                 alt.Tooltip("v:Q", title="R$", format=",.2f")])
    linha = alt.Chart(res).mark_line(point=True, color="#3FA9D6", strokeWidth=3).encode(
        x=alt.X("mes_txt:N", sort=ordem), y="lucro:Q",
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("lucro:Q", title="Lucro R$", format=",.2f")])
    st.altair_chart(barras + linha, width="stretch")
    tot = pd.DataFrame({"": ["Receitas", "Despesas", "Lucro"],
                        "12 meses": [brl(res["receitas"].sum()), brl(res["despesas"].sum()), brl(res["lucro"].sum())],
                        "Média/mês": [brl(res["receitas"].mean()), brl(res["despesas"].mean()),
                                      brl(res["lucro"].mean())]})
    st.dataframe(tot, hide_index=True, width="stretch")

if aba_van:
    with aba_van[0]:
        st.caption(f"Resultado de cada van em {mes_label(comp)} (regime de caixa). Despesas lançadas como "
                   "**Geral** aparecem separadas — divida de cabeça ou lance já na van.")
        pv = repo.resultado_por_van(cid, comp, prox)
        pv["recebido"] = pv["recebido"].astype(float)
        pv["despesas"] = pv["despesas"].astype(float)
        pv["lucro"] = pv["recebido"] - pv["despesas"]
        st.dataframe(pv, hide_index=True, width="stretch",
                     column_config={"van": "Van",
                                    "recebido": st.column_config.NumberColumn("Recebido", format="R$ %.2f"),
                                    "despesas": st.column_config.NumberColumn("Despesas", format="R$ %.2f"),
                                    "lucro": st.column_config.NumberColumn("Lucro", format="R$ %.2f")})
