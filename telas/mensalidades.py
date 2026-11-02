"""Mensalidades: gerar o mês, receber, cobrar pelo WhatsApp, painel de inadimplência."""
import altair as alt
import streamlit as st

from core import cobranca_pais as cp, repo
from core.asaas import STATUS as ST_ASAAS, AsaasErro
from core.fmt import FORMAS, brl, data_br, hoje, inicio_mes, link_whats, mes_label, somar_meses
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
h = hoje()
st.title("Mensalidades")

# o mês atual é gerado sozinho; os outros, pelo botão
if st.session_state.get("_mens_gerado") != (cid, inicio_mes(h)):
    repo.gerar_mensalidades(cid, h)
    st.session_state["_mens_gerado"] = (cid, inicio_mes(h))

# cobrança mista: com a conta Asaas do gestor conectada, confere pagamentos e gera os Pix/boletos do mês
API = _ui.api_do_gestor(repo.empresa(cid))
if API:
    import time as _t
    if _t.time() - st.session_state.get("_sync_pais", 0) > 60:
        st.session_state["_sync_pais"] = _t.time()
        _r = cp.sincronizar(API, cid, h)
        if _r["pagas"] or _r["geradas"]:
            st.toast(f"Asaas: {_r['pagas']} pagamento(s) recebido(s) · {_r['geradas']} cobrança(s) gerada(s).")
        for _e in _r["erros"][:3]:
            st.warning(_e, icon=":material/warning:")
    with st.expander("Como cada aluno paga (Asaas ou manual)", icon=":material/tune:"):
        st.caption("Misture como quiser: **Manual** = você cobra e dá baixa; **Pix/boleto todo mês** = o app gera a "
                   "cobrança uns dias antes do vencimento e dá baixa sozinho; **Assinatura automática** = o Asaas "
                   "cobra todo mês (aceita cartão). O Asaas exige o CPF do responsável.")
        import pandas as _pd
        lst = cp.alunos_cobranca(cid)
        if lst:
            base_df = _pd.DataFrame(lst)
            ed = st.data_editor(
                base_df[["nome", "cobranca", "cpf"]], hide_index=True, width="stretch", num_rows="fixed",
                disabled=["nome"], key="ed_cobranca",
                column_config={"nome": "Aluno",
                               "cobranca": st.column_config.SelectboxColumn("Cobrança", options=list(cp.MODOS),
                                                                            required=True),
                               "cpf": st.column_config.TextColumn("CPF do responsável")})
            st.caption("Opções: manual · asaas (Pix/boleto todo mês) · recorrente (assinatura automática).")
            if st.button("Salvar formas de cobrança", icon=":material/save:"):
                erros = []
                for i, row in ed.iterrows():
                    o = base_df.loc[i]
                    if (row["cpf"] or "") != (o["cpf"] or ""):
                        cp.salvar_cpf(cid, o["id"], row["cpf"] or "")
                    if row["cobranca"] != o["cobranca"]:
                        try:
                            e = cp.definir_modo(API, cid, o["id"], row["cobranca"], h)
                        except AsaasErro as ex:
                            e = f"{o['nome']}: {ex}"
                        if e:
                            erros.append(e)
                for e in erros:
                    st.error(e)
                if not erros:
                    st.session_state["_sync_pais"] = 0
                    st.toast("Formas de cobrança salvas.")
                    st.rerun()

def _msg(r) -> str:
    primeiro = (r.responsavel or "").split(" ")[0] or "tudo bem"
    txt = (f"Olá, {primeiro}! Passando para lembrar da mensalidade da van de {r.aluno} "
           f"({mes_label(r.competencia)}), no valor de {brl(r.valor)}, com vencimento em {data_br(r.vencimento)}.")
    if r.situacao == "vencido":
        txt = (f"Olá, {primeiro}! A mensalidade da van de {r.aluno} ({mes_label(r.competencia)}), de {brl(r.valor)}, "
               f"venceu em {data_br(r.vencimento)}. Consegue verificar, por favor?")
    if getattr(r, "asaas_link", None):
        txt += f"\n\nPague por Pix ou boleto: {r.asaas_link}"
    elif c.get("chave_pix"):
        txt += f"\n\nChave Pix: {c['chave_pix']}"
    return txt + "\n\nObrigado! 🚐"



van = _ui.filtro_van(cid, "van_mens")
aba_mes, aba_cobrar, aba_painel = st.tabs(["Mês", "Cobrar vencidos", "Painel"])


def _tela_mes():
    meses = [somar_meses(inicio_mes(h), i) for i in range(-12, 3)]
    comp = st.select_slider("Mês", options=meses, value=inicio_mes(h), format_func=lambda d: mes_label(d, curto=True))

    df = repo.mensalidades_mes(cid, comp, h, van=van)
    g1, g2 = st.columns([3, 1])
    if g2.button("Gerar mês", icon=":material/autorenew:", width="stretch",
                 help="Cria a mensalidade de quem ainda não tem neste mês (alunos ativos com valor)."):
        n = repo.gerar_mensalidades(cid, comp)
        st.toast(f"{n} mensalidade(s) criada(s)." if n else "Todos os alunos já têm mensalidade neste mês.")
        st.rerun()

    if df.empty:
        g1.info("Nenhuma mensalidade neste mês. Cadastre alunos com valor de mensalidade e clique em **Gerar mês**.")
        return

    prev = df["valor"].astype(float).sum()
    rec = df["valor_pago"].fillna(0).astype(float).sum()
    aberto = df.loc[df["situacao"] != "pago", "valor"].astype(float).sum()
    venc = df.loc[df["situacao"] == "vencido", "valor"].astype(float).sum()
    base = df.loc[df["forma"].fillna("") != "Isento", "valor"].astype(float).sum()
    _ui.olho()
    _ui.kpis([("Recebido", brl(rec), f"{(df['situacao'] == 'pago').sum()} de {len(df)} pagos"),
              ("Previsto no mês", brl(prev)), ("Em aberto", brl(aberto)),
              ("Vencido", brl(venc), f"{(df['situacao'] == 'vencido').sum()} aluno(s) · "
                                     f"{(venc / base * 100 if base else 0):.0f}% do mês")])
    _ui.meta_mes(rec, prev, "Meta do mês" if comp == inicio_mes(h) else f"Meta de {mes_label(comp)}")

    filtro = st.segmented_control("Mostrar", ["Todos", "Em aberto", "Vencidos", "Pagos"], default="Em aberto",
                                  label_visibility="collapsed")
    if filtro == "Em aberto":
        df = df[df["situacao"] != "pago"]
    elif filtro == "Vencidos":
        df = df[df["situacao"] == "vencido"]
    elif filtro == "Pagos":
        df = df[df["situacao"] == "pago"]

    if st.session_state.get("_aviso_mens"):
        st.warning(st.session_state.pop("_aviso_mens"), icon=":material/info:")
    if df.empty:
        st.success("Nada por aqui. 🎉")



    for r in df.itertuples():
        with st.container(border=True, key=f"card_{'venc_' if r.situacao == 'vencido' else ''}{r.id}"):
            a, b = st.container(key=f"lp_{r.id}").columns([3, 2])
            asaas_tag = (" " + _ui.tag("embarcou", "Asaas · " + ST_ASAAS.get(r.asaas_status or "", "gerada"))
                         if getattr(r, "asaas_id", None) else "")
            a.markdown(f"**{_ui.esc(r.aluno)}** {_ui.tag(r.situacao, _ui.ROTULO_MENS[r.situacao])}{asaas_tag}  \n"
                       f"<span class='ve-sub'>vence {data_br(r.vencimento)} · {_ui.esc(r.responsavel or 'sem responsável')}"
                       f"</span>", unsafe_allow_html=True)
            if r.situacao == "pago":
                b.markdown(f"**{brl(r.valor_pago)}**  \n<span class='ve-sub'>pago {data_br(r.pago_em)} · "
                           f"{_ui.esc(r.forma or '')}</span>", unsafe_allow_html=True)
                if b.button("Estornar", key=f"est_{r.id}", type="tertiary"):
                    aviso = cp.estornar(API, cid, r._asdict())
                    if aviso:
                        st.session_state["_aviso_mens"] = aviso
                    st.rerun()
                continue
            b.markdown(f"**{brl(r.valor)}**")
            x1, x2, x3 = st.container(key=f"linha_{r.id}").columns(3)
            with x1.popover("Receber", icon=":material/check_circle:", width="stretch"):
                with st.form(f"pg_{r.id}"):
                    d = st.date_input("Data", value=h, format="DD/MM/YYYY")
                    v = st.number_input("Valor recebido", min_value=0.0, value=float(r.valor), step=5.0)
                    f = st.selectbox("Forma", FORMAS)
                    if st.form_submit_button("Confirmar", type="primary"):
                        aviso = cp.baixa_manual(API, cid, r._asdict(), d, v, f)
                        if aviso:
                            st.session_state["_aviso_mens"] = aviso
                        st.rerun()
            link = link_whats(r.telefone, _msg(r))
            if link:
                x2.link_button("Cobrar", link, icon=":material/chat:", width="stretch")
            else:
                x2.button("Sem WhatsApp", disabled=True, key=f"sw_{r.id}", width="stretch")
            with x3.popover("Ajustar", icon=":material/edit:", width="stretch"):
                with st.form(f"aj_{r.id}"):
                    nv = st.number_input("Valor", min_value=0.0, value=float(r.valor), step=5.0)
                    nd = st.date_input("Vencimento", value=r.vencimento, format="DD/MM/YYYY")
                    s1, s2 = st.columns(2)
                    if s1.form_submit_button("Salvar"):
                        repo.alterar_mensalidade(cid, r.id, nv, nd)
                        st.rerun()
                    if s2.form_submit_button("Isentar mês", help="Ex.: férias ou bolsa — fica como pago com R$ 0."):
                        if API and getattr(r, "asaas_id", None):
                            try:
                                API.cancelar_cobranca(r.asaas_id)
                            except AsaasErro:
                                pass
                        repo.pagar(cid, r.id, h, 0, "Isento")
                        st.rerun()
            if API:
                if getattr(r, "asaas_link", None):
                    st.link_button("Abrir cobrança (Pix/boleto)", r.asaas_link, icon=":material/receipt_long:",
                                   width="stretch")
                elif st.button("Gerar Pix/boleto no Asaas", key=f"ger_{r.id}", icon=":material/qr_code_2:",
                               width="stretch", help="Cobrança avulsa desta mensalidade, com baixa automática."):
                    try:
                        cp.gerar_cobranca(API, cid, r._asdict(), h)
                        st.rerun()
                    except AsaasErro as ex:
                        st.error(str(ex))


with aba_mes:
    _tela_mes()

# ------------------------------------------------------------------ cobrar todos os vencidos
with aba_cobrar:
    vv = repo.vencidas_todas(cid, h, van=van)
    if vv.empty:
        st.success("Nenhuma mensalidade vencida. 🎉")
    else:
        por_aluno = vv.groupby("aluno", sort=False)
        st.caption(f"{len(vv)} mensalidade(s) vencida(s) de {por_aluno.ngroups} aluno(s), somando "
                   f"{brl(vv['valor'].astype(float).sum())}. Toque em cada um: abre o WhatsApp do responsável com a "
                   "cobrança pronta (todos os meses em atraso juntos) — é só enviar.")
        for aluno, g in por_aluno:
            r0 = g.iloc[0]
            primeiro = (r0["responsavel"] or "").split(" ")[0] or "tudo bem"
            itens = "\n".join(f"• {mes_label(x.competencia)}: {brl(x.valor)} (venceu {data_br(x.vencimento)})"
                              for x in g.itertuples())
            total = g["valor"].astype(float).sum()
            txt = (f"Olá, {primeiro}! Consta em aberto a mensalidade da van de {aluno}:\n{itens}\n"
                   f"Total: {brl(total)}. Consegue verificar, por favor?")
            if c.get("chave_pix"):
                txt += f"\n\nChave Pix: {c['chave_pix']}"
            txt += "\n\nObrigado! 🚐"
            dias = (h - g["vencimento"].min()).days
            rot = f"{aluno} — {len(g)} mês(es) · {brl(total)} · {dias} dia(s) de atraso"
            lk = link_whats(r0["telefone"], txt)
            if lk:
                st.link_button(rot, lk, icon=":material/chat:", width="stretch")
            else:
                st.button(rot + " — sem WhatsApp", disabled=True, width="stretch", key=f"cv_{aluno}")

# ------------------------------------------------------------------ painel
with aba_painel:
    ini = somar_meses(inicio_mes(h), -11)
    se = repo.serie_mensalidades(cid, ini, somar_meses(inicio_mes(h), 1), h, van=van)
    if se.empty:
        st.info("Ainda não há mensalidades para mostrar.")
    else:
        for col in ("previsto", "recebido", "vencido"):
            se[col] = se[col].fillna(0).astype(float)
        tot_prev, tot_rec, tot_venc = se["previsto"].sum(), se["recebido"].sum(), se["vencido"].sum()
        _ui.kpis([("Recebido em 12 meses", brl(tot_rec), f"de {brl(tot_prev)} previstos"),
                  ("Taxa de recebimento", f"{(tot_rec / tot_prev * 100 if tot_prev else 0):.0f}%"),
                  ("Vencido em aberto", brl(tot_venc)),
                  ("Inadimplência", f"{(tot_venc / tot_prev * 100 if tot_prev else 0):.1f}%", "vencido ÷ previsto")])
        se["mes_txt"] = se["mes"].map(lambda d: mes_label(d, curto=True))
        ordem = list(se["mes_txt"])
        longo = se.melt(id_vars=["mes_txt"], value_vars=["previsto", "recebido"], var_name="tipo", value_name="v")
        barras = alt.Chart(longo).mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X("mes_txt:N", sort=ordem, title=None), xOffset="tipo:N",
            y=alt.Y("v:Q", title=None, axis=alt.Axis(labelExpr="replace(format(datum.value, ',.0f'), ',', '.')")),
            color=alt.Color("tipo:N", scale=alt.Scale(domain=["previsto", "recebido"], range=["#BFE4F7", "#0ABAB5"]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("tipo:N", title=""),
                     alt.Tooltip("v:Q", title="R$", format=",.2f")])
        st.markdown("**Previsto × recebido** (por mês de competência)")
        st.altair_chart(barras, width="stretch")
        se["inad"] = (se["vencido"] / se["previsto"].where(se["previsto"] > 0) * 100).fillna(0)
        linha = alt.Chart(se).mark_line(point=True, color="#FF8A80", strokeWidth=3).encode(
            x=alt.X("mes_txt:N", sort=ordem, title=None), y=alt.Y("inad:Q", title=None, axis=alt.Axis(format=".0f")),
            tooltip=[alt.Tooltip("mes_txt:N", title="Mês"), alt.Tooltip("inad:Q", title="% vencido", format=".1f")])
        st.markdown("**Inadimplência por mês** (% do previsto que está vencido e não pago)")
        st.altair_chart(linha.properties(height=180), width="stretch")

        st.markdown("**Pontualidade por aluno** (últimos 12 meses)")
        at = repo.atrasos_por_aluno(cid, ini, h, van=van)
        if at.empty:
            st.caption("Sem vencimentos no período.")
        else:
            at["em_aberto"] = at["em_aberto"].astype(float)
            st.dataframe(at, hide_index=True, width="stretch",
                         column_config={"aluno": "Aluno", "em_dia": "Pagou em dia", "com_atraso": "Pagou atrasado",
                                        "dias_medios": st.column_config.NumberColumn("Atraso médio (dias)"),
                                        "vencidas": "Vencidas hoje",
                                        "em_aberto": st.column_config.NumberColumn("Em aberto", format="R$ %.2f")})
