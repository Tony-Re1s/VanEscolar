"""Financeiro: despesas, outras receitas, lucro do mês e dos últimos 12 meses (regime de caixa)."""
import altair as alt
import pandas as pd
import streamlit as st

from core import repo
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

res = repo.resumo_meses(cid, somar_meses(comp, -11), prox)
mes = res.iloc[-1]
receita = float(mes["mensalidades"]) + float(mes["outras_receitas"])
desp = float(mes["despesas"])
mens = repo.mensalidades_mes(cid, comp, h)
inad = mens.loc[mens["situacao"] == "vencido", "valor"].astype(float).sum() if not mens.empty else 0
_ui.kpis([("Lucro do mês", brl(receita - desp), "recebido − despesas"),
          ("Recebido", brl(receita), f"mensalidades {brl(mes['mensalidades'])}"),
          ("Despesas", brl(desp)),
          ("Inadimplência", brl(inad), "mensalidades vencidas do mês")])

aba_lancar, aba_mes, aba_ano = st.tabs(["Lançar", "Lançamentos do mês", "12 meses"])

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
        desc = st.text_input("Descrição", placeholder="Ex.: troca de óleo, posto X, passeio ao zoológico")
        st.caption("Mensalidades entram sozinhas quando você marca como recebidas — não precisa lançar aqui.")
        if st.form_submit_button("Lançar", type="primary"):
            if valor <= 0:
                st.error("Informe o valor.")
            else:
                repo.salvar_lancamento(cid, dict(tipo=tipo, categoria=cat, descricao=desc or None, valor=valor,
                                                 data=data, km=km or None))
                st.toast("Lançado.")
                st.rerun()

with aba_mes:
    lan = repo.lancamentos(cid, comp, prox)
    if lan.empty:
        st.info(f"Nenhum lançamento em {mes_label(comp)}.")
    else:
        cats = repo.despesas_por_categoria(cid, comp, prox)
        if not cats.empty:
            cats["valor"] = cats["valor"].astype(float)
            st.altair_chart(alt.Chart(cats).mark_bar(cornerRadiusEnd=4, color="#1D3557").encode(
                x=alt.X("valor:Q", title=None, axis=alt.Axis(format=",.0f")),
                y=alt.Y("categoria:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("categoria:N", title="Categoria"),
                         alt.Tooltip("valor:Q", title="R$", format=",.2f")]).properties(height=36 * len(cats) + 20),
                use_container_width=True)
        for r in lan.itertuples():
            a, b, x = st.container(key=f"lp_{r.id}").columns([4, 2, 1])
            sinal = "−" if r.tipo == "despesa" else "+"
            a.markdown(f"**{_ui.esc(r.categoria)}** <span class='ve-sub'>{data_br(r.data)}"
                       f"{' · ' + _ui.esc(r.descricao) if r.descricao else ''}{f' · {r.km} km' if r.km else ''}</span>",
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
        y=alt.Y("v:Q", title=None, axis=alt.Axis(format=",.0f")),
        color=alt.Color("tipo:N", scale=alt.Scale(domain=["receitas", "despesas"], range=["#2A9D8F", "#D62839"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("tipo:N", title=""),
                 alt.Tooltip("v:Q", title="R$", format=",.2f")])
    linha = alt.Chart(res).mark_line(point=True, color="#1D3557").encode(
        x=alt.X("mes_txt:N", sort=ordem), y="lucro:Q",
        tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("lucro:Q", title="Lucro R$", format=",.2f")])
    st.altair_chart(barras + linha, use_container_width=True)
    tot = pd.DataFrame({"": ["Receitas", "Despesas", "Lucro"],
                        "12 meses": [brl(res["receitas"].sum()), brl(res["despesas"].sum()), brl(res["lucro"].sum())],
                        "Média/mês": [brl(res["receitas"].mean()), brl(res["despesas"].mean()),
                                      brl(res["lucro"].mean())]})
    st.dataframe(tot, hide_index=True, use_container_width=True)
