"""Fretamento: viagens por fora do transporte escolar (excursão, festa, aeroporto, empresa…).
Orçamento em 1 clique pelo WhatsApp → fechou → agenda → recebimentos e gastos (vão para o Financeiro, separados)."""
from datetime import timedelta

import streamlit as st

from core import planos as pl, repo
from core.fmt import CAT_DESPESA, DIAS_SEMANA, FORMAS, brl, data_br, hoje, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
h = hoje()
st.title("Fretamento")

emp = repo.empresa(cid)
if not pl.tem_fretamento(emp, h) and not st.session_state["usuario"].get("admin"):
    st.info("O **Fretamento** está disponível a partir do plano **Pro**: orçamento em 1 clique, agenda das viagens "
            "por fora e o lucro de cada frete separado do escolar.", icon=":material/workspace_premium:")
    st.page_link("telas/meu_plano.py", label="Ver planos", icon=":material/upgrade:")
    st.stop()

vans = repo.vans(cid)
V_IDS = [None] + [str(x) for x in vans["id"]] if not vans.empty else [None]
V_NOME = {None: "—"} | ({str(r.id): r.nome for r in vans.itertuples()} if not vans.empty else {})
V_MOT = {str(r.id): (r.motorista_nome or "") for r in vans.itertuples()} if not vans.empty else {}
TAG = {"orcamento": "aberto", "enviado": "aberto", "fechado": "pago", "realizado": "desembarcou",
       "recusado": "faltou", "cancelado": "faltou"}
CHAVE_PIX = c.get("chave_pix")


def _f(v):
    try:
        x = float(v)
        return 0.0 if x != x else x
    except (TypeError, ValueError):
        return 0.0


def _txt(v):
    return "" if v is None or (isinstance(v, float) and v != v) else str(v)


def _quando(f) -> str:
    d = f["data_ida"]
    t = f"{DIAS_SEMANA[d.weekday()]}, {data_br(d)}"
    if f.get("hora_ida") and _txt(f["hora_ida"]):
        t += f" às {f['hora_ida']:%H:%M}"
    dv = f.get("data_volta")
    if dv and _txt(dv) and dv != d:
        t += f" → volta {data_br(dv)}"
        if f.get("hora_volta") and _txt(f["hora_volta"]):
            t += f" às {f['hora_volta']:%H:%M}"
    elif f.get("hora_volta") and _txt(f["hora_volta"]):
        t += f" (volta às {f['hora_volta']:%H:%M})"
    return t


def msg_orcamento(f) -> str:
    nome = _txt(f.get("cliente")).split(" ")[0]
    linhas = [f"Olá{', ' + nome if nome else ''}! Segue o orçamento da viagem 🚐", "", f"📅 {_quando(f)}"]
    if _txt(f.get("origem")):
        linhas.append(f"📍 Saída: {f['origem']}")
    if _txt(f.get("destino")):
        linhas.append(f"🏁 Destino: {f['destino']}")
    if _f(f.get("passageiros")):
        linhas.append(f"👥 {int(_f(f['passageiros']))} passageiros")
    linhas += ["", f"💰 Valor: {brl(_f(f['valor']))}"]
    if _f(f.get("sinal")):
        linhas.append(f"✅ Para reservar a data: sinal de {brl(_f(f['sinal']))}")
    if f.get("validade") and _txt(f["validade"]):
        linhas.append(f"⏳ Orçamento válido até {data_br(f['validade'])}")
    if _txt(f.get("obs")):
        linhas += ["", _txt(f["obs"])]
    linhas += ["", "Para confirmar, é só responder aqui. Obrigado!", c["nome"]]
    return "\n".join(linhas)


def msg_confirmacao(f) -> str:
    nome = _txt(f.get("cliente")).split(" ")[0]
    falta = max(_f(f["valor"]) - _f(f["recebido"]), 0)
    linhas = [f"Olá{', ' + nome if nome else ''}! Viagem confirmada ✅", "", f"📅 {_quando(f)}"]
    if _txt(f.get("origem")):
        linhas.append(f"📍 Saída: {f['origem']}")
    if _txt(f.get("destino")):
        linhas.append(f"🏁 Destino: {f['destino']}")
    linhas += ["", f"💰 Total: {brl(_f(f['valor']))}" + (f" · já recebido {brl(_f(f['recebido']))}" if _f(f["recebido"]) else "")]
    if falta:
        linhas.append(f"Falta: {brl(falta)}" + (f" — Pix: {CHAVE_PIX}" if CHAVE_PIX else ""))
    linhas += ["", "Qualquer mudança, me avise. Até lá! 🚐", c["nome"]]
    return "\n".join(linhas)


def _link(f, msg) -> str:
    import urllib.parse
    return link_whats(_txt(f.get("cliente_telefone")), msg) or f"https://wa.me/?text={urllib.parse.quote(msg)}"


# ---------------------------------------------------------------- orçamento novo, em 3 etapas
def _rodape(chave, voltar=True, seguir="Continuar"):
    with st.container(key=f"wzpe_{chave}"):
        a, b = st.columns(2) if voltar else (None, st.container())
        v = a.form_submit_button("Voltar", icon=":material/arrow_back:", width="stretch") if voltar else False
        s_ = b.form_submit_button(seguir, type="primary", width="stretch",
                                  icon=":material/arrow_forward:" if seguir == "Continuar" else ":material/check:")
    return "voltar" if v else "seguir" if s_ else None


def novo_por_etapas():
    ss = st.session_state
    r = ss.setdefault("fr_rasc", {})
    et = ss.setdefault("fr_et", 0)
    g = r.get
    _ui.etapas(["Viagem", "Cliente e van", "Valores"], et)
    if et == 0:
        with st.form("fr0"):
            a, b = st.columns(2)
            di = a.date_input("Ida *", value=g("data_ida") or h + timedelta(days=7), format="DD/MM/YYYY")
            hi = b.time_input("Saída", value=g("hora_ida"), step=900)
            a, b = st.columns(2)
            dv = a.date_input("Volta", value=g("data_volta"), format="DD/MM/YYYY", help="Vazio = volta no mesmo dia")
            hv = b.time_input("Hora da volta", value=g("hora_volta"), step=900)
            ori = st.text_input("Saída de", value=g("origem") or "", placeholder="Endereço ou bairro")
            des = st.text_input("Destino", value=g("destino") or "", placeholder="Ex.: Aparecida, aeroporto")
            acao = _rodape("f0", voltar=False)
        if acao:
            if dv and dv < di:
                st.error("A volta não pode ser antes da ida.")
                st.stop()
            r.update(data_ida=di, hora_ida=hi, data_volta=dv, hora_volta=hv, origem=ori.strip() or None,
                     destino=des.strip() or None)
            ss["fr_et"] = 1
            st.rerun()
    elif et == 1:
        clientes = repo.clientes_frete(cid)
        ids = ["novo"] + ([str(x) for x in clientes["id"]] if not clientes.empty else [])
        nomes = {"novo": "➕ Cliente novo"} | ({str(x.id): x.nome + (f" · {x.telefone}" if x.telefone else "")
                                              for x in clientes.itertuples()} if not clientes.empty else {})
        cli = st.selectbox("Cliente", ids, index=ids.index(g("cliente")) if g("cliente") in ids else 0,
                           format_func=nomes.get, key="fr_cli")
        with st.form("fr1"):
            cn = ct = ""
            if cli == "novo":
                a, b = st.columns(2)
                cn = a.text_input("Nome do cliente *", value=g("cn") or "", placeholder="Pessoa ou empresa")
                ct = b.text_input("WhatsApp", value=g("ct") or "", placeholder="(11) 98888-7777")
            pas = st.number_input("Passageiros", min_value=0, step=1, value=int(g("passageiros") or 0))
            vat = g("van_id") or (V_IDS[1] if len(V_IDS) == 2 else None)
            a, b = st.columns(2)
            van = a.selectbox("Van", V_IDS, index=V_IDS.index(vat) if vat in V_IDS else 0, format_func=V_NOME.get)
            mot = b.text_input("Motorista", value=g("motorista") or "", placeholder=V_MOT.get(vat or "", "") or "Quem dirige")
            acao = _rodape("f1")
        if acao:
            r.update(cliente=cli, cn=cn.strip(), ct=ct.strip(), passageiros=int(pas) or None, van_id=van,
                     motorista=mot.strip() or None)
            if acao == "seguir" and cli == "novo" and not cn.strip() and not ss.get("fr_edit"):
                st.error("Coloque o nome do cliente.")
                st.stop()
            if acao == "seguir":
                for aviso in repo.conflitos_frete(cid, g("data_ida"), g("data_volta"), van, None):
                    st.toast("⚠️ " + aviso)
            ss["fr_et"] = 0 if acao == "voltar" else 2
            st.rerun()
    else:
        with st.form("fr2"):
            a, b = st.columns(2)
            val = a.number_input("Valor total (R$) *", min_value=0.0, step=50.0, value=float(g("valor") or 0))
            sin = b.number_input("Sinal (R$)", min_value=0.0, step=50.0, value=float(g("sinal") or 0),
                                 help="Quanto pedir para reservar a data.")
            vld = st.date_input("Orçamento válido até", value=g("validade") or h + timedelta(days=7), format="DD/MM/YYYY")
            obs = st.text_area("Observações (vão no orçamento)", value=g("obs") or "", height=80,
                               placeholder="Ex.: inclui pedágio; almoço por conta do grupo")
            acao = _rodape("f2", seguir="Salvar alterações" if ss.get("fr_edit") else "Salvar orçamento")
        if acao:
            r.update(valor=val, sinal=sin, validade=vld, obs=obs.strip() or None)
            if acao == "voltar":
                ss["fr_et"] = 1
                st.rerun()
            if val <= 0:
                st.error("Coloque o valor da viagem.")
                st.stop()
            cli_id = (repo.salvar_cliente_frete(cid, dict(nome=r["cn"], telefone=r["ct"] or None, documento=None,
                                                          email=None)) if r["cn"] else None) \
                if r["cliente"] == "novo" else r["cliente"]
            editando = ss.get("fr_edit")
            fid = repo.salvar_frete(cid, dict(cliente_id=cli_id, data_ida=r["data_ida"], hora_ida=r["hora_ida"],
                                              data_volta=r["data_volta"], hora_volta=r["hora_volta"],
                                              origem=r["origem"], destino=r["destino"], passageiros=r["passageiros"],
                                              van_id=r["van_id"], motorista=r["motorista"] or V_MOT.get(r["van_id"] or "", "") or None,
                                              valor=round(val, 2), sinal=round(sin, 2) or None, validade=vld,
                                              obs=r["obs"]), fid=editando)
            ss.pop("fr_rasc", None)
            ss["fr_et"] = 0
            if editando:
                ss.pop("fr_edit", None)
                st.toast("Alterações salvas. ✅")
            else:
                ss["_frete_novo"] = fid
            st.rerun()



def editar_por_etapas(f: dict):
    """Abre o orçamento nas mesmas 3 etapas do novo, já preenchido."""
    def _t(v):
        return v if _txt(v) else None
    st.session_state.update(fr_edit=str(f["id"]), fr_et=0, fr_rasc=dict(
        data_ida=f["data_ida"], hora_ida=_t(f.get("hora_ida")), data_volta=_t(f.get("data_volta")),
        hora_volta=_t(f.get("hora_volta")), origem=_txt(f.get("origem")) or None, destino=_txt(f.get("destino")) or None,
        cliente=str(f["cliente_id"]) if _txt(f.get("cliente_id")) else "novo", cn="", ct="",
        passageiros=int(_f(f.get("passageiros"))) or None, van_id=str(f["van_id"]) if _txt(f.get("van_id")) else None,
        motorista=_txt(f.get("motorista")) or None, valor=_f(f.get("valor")), sinal=_f(f.get("sinal")),
        validade=_t(f.get("validade")), obs=_txt(f.get("obs")) or None))
    st.rerun()

# ---------------------------------------------------------------- cartão de cada frete
def cartao(f: dict):
    fid = str(f["id"])
    st_ = f["status"]
    recebido, gastos, valor = _f(f["recebido"]), _f(f["gastos"]), _f(f["valor"])
    falta = max(valor - recebido, 0)
    with st.container(border=True, key=f"fr_{fid}"):
        rota = " → ".join(x for x in (_txt(f.get("origem")), _txt(f.get("destino"))) if x) or "Viagem"
        st.markdown(_ui.sem_formula(
            f"**{_ui.esc(rota)}** {_ui.tag(TAG[st_], repo.STATUS_FRETE[st_])}  \n"
            f"📅 {_ui.esc(_quando(f))}  \n<span class='ve-sub'>"
            + " · ".join(x for x in (
                f"👤 {_ui.esc(_txt(f.get('cliente')))}" if _txt(f.get("cliente")) else "",
                f"👥 {int(_f(f['passageiros']))} passageiros" if _f(f.get("passageiros")) else "",
                f"🚐 {_ui.esc(_txt(f.get('van')))}" if _txt(f.get("van")) else "",
                f"🧑‍✈️ {_ui.esc(_txt(f.get('motorista')))}" if _txt(f.get("motorista")) else "") if x)
            + "</span>"), unsafe_allow_html=True)
        fin = f"💰 **{brl(valor)}**"
        if st_ in ("fechado", "realizado"):
            fin += f" · recebido {brl(recebido)}" + (f" · **falta {brl(falta)}**" if falta else " ✅")
            if gastos:
                fin += f" · gastos {brl(gastos)} · **sobrou {brl(recebido - gastos)}**"
        elif _f(f.get("sinal")):
            fin += f" · sinal {brl(_f(f['sinal']))}"
        if st_ in ("orcamento", "enviado") and f.get("validade") and _txt(f["validade"]):
            venc = f["validade"]
            fin += f" · válido até {data_br(venc)}" + (" ⚠️ venceu" if venc < h else "")
        st.markdown(_ui.sem_formula(fin))
        if st_ in ("orcamento", "enviado", "fechado"):
            for aviso in repo.conflitos_frete(cid, f["data_ida"], f["data_volta"] if _txt(f.get("data_volta")) else None,
                                              f["van_id"] if _txt(f.get("van_id")) else None, fid):
                st.caption("⚠️ " + aviso)

        if st_ in ("orcamento", "enviado"):
            a, b, x = st.container(key=f"lb_{fid}").columns(3)
            a.link_button("Enviar orçamento", _link(f, msg_orcamento(f)), icon=":material/send:", type="primary",
                          width="stretch")
            if b.button("Fechou ✅", key=f"fe_{fid}", width="stretch"):
                repo.status_frete(cid, fid, "fechado")
                st.toast("Fechado! A viagem foi para a agenda.")
                st.rerun()
            if x.button("Não fechou", key=f"nf_{fid}", width="stretch"):
                repo.status_frete(cid, fid, "recusado")
                st.rerun()
            with st.expander("Ver o texto do orçamento"):
                st.code(msg_orcamento(f), language=None, wrap_lines=True)
        elif st_ in ("fechado", "realizado"):
            a, b = st.container(key=f"lb_{fid}").columns(2)
            a.link_button("Confirmação no WhatsApp", _link(f, msg_confirmacao(f)), icon=":material/chat:",
                          width="stretch")
            if st_ == "fechado" and b.button("Viagem realizada", key=f"re_{fid}", icon=":material/flag:",
                                            width="stretch"):
                repo.status_frete(cid, fid, "realizado")
                st.rerun()
            a, b = st.container(key=f"lc_{fid}").columns(2)
            with a.popover("Receber pagamento", icon=":material/payments:", width="stretch"):
                with st.form(f"rec_{fid}", border=False):
                    v = st.number_input("Valor (R$)", min_value=0.0, step=50.0,
                                        value=round(falta if recebido or not _f(f.get("sinal")) else min(_f(f["sinal"]), falta), 2))
                    dt = st.date_input("Data", value=h, format="DD/MM/YYYY")
                    fm = st.selectbox("Forma", FORMAS)
                    if st.form_submit_button("Registrar", type="primary"):
                        if v > 0:
                            rot = "Sinal" if not recebido and v < valor else ("Pagamento" if v >= falta else "Parcela")
                            repo.lancar_frete(cid, fid, "receita", round(v, 2), dt, "Fretamento",
                                              f"{rot} · {rota}" + (f" · {_txt(f.get('cliente'))}" if _txt(f.get('cliente')) else "")
                                              + f" ({fm})")
                            st.toast("Recebimento registrado — já está no Financeiro.")
                            st.rerun()
            with b.popover("Lançar gasto", icon=":material/receipt_long:", width="stretch"):
                with st.form(f"gas_{fid}", border=False):
                    cat = st.selectbox("Categoria", ["Combustível", "Pedágio / estacionamento", "Motorista extra",
                                                     "Alimentação", "Manutenção", "Outros"])
                    v = st.number_input("Valor (R$)", min_value=0.0, step=10.0, key=f"gv_{fid}")
                    dt = st.date_input("Data", value=f["data_ida"] if f["data_ida"] <= h else h, format="DD/MM/YYYY",
                                       key=f"gd_{fid}")
                    ds = st.text_input("Descrição (opcional)", key=f"gs_{fid}")
                    if st.form_submit_button("Lançar", type="primary"):
                        if v > 0:
                            repo.lancar_frete(cid, fid, "despesa", round(v, 2), dt, cat,
                                              (ds.strip() + " · " if ds.strip() else "") + f"Frete: {rota}")
                            st.toast("Gasto lançado no Financeiro.")
                            st.rerun()
            lan = repo.lancamentos_frete(cid, fid)
            if not lan.empty:
                with st.expander(f"Recebimentos e gastos ({len(lan)})"):
                    for r in lan.itertuples():
                        a, b = st.columns([5, 1])
                        a.caption(f"{'＋' if r.tipo == 'receita' else '−'} {brl(r.valor)} · {data_br(r.data)} · "
                                  f"{r.categoria}{' · ' + r.descricao if r.descricao else ''}")
                        if b.button("", icon=":material/delete:", key=f"dl_{r.id}", type="tertiary", help="Excluir"):
                            repo.excluir_lancamento(cid, r.id)
                            st.rerun()
        else:
            a, b = st.container(key=f"lb_{fid}").columns(2)
            if a.button("Reabrir orçamento", key=f"ra_{fid}", icon=":material/undo:", width="stretch"):
                repo.status_frete(cid, fid, "orcamento")
                st.rerun()
            if b.button("Excluir", key=f"ex_{fid}", icon=":material/delete:", width="stretch"):
                repo.excluir_frete(cid, fid)
                st.rerun()

        if st_ in ("orcamento", "enviado", "fechado"):
            a, b = st.container(key=f"linha_ed_{fid}").columns(2)
            if a.button("Editar", key=f"ed_{fid}", icon=":material/edit:", type="tertiary", width="stretch"):
                editar_por_etapas(f)
            if st_ == "fechado" and b.button("Cancelar viagem", key=f"cv_{fid}", icon=":material/cancel:",
                                             type="tertiary", width="stretch"):
                repo.status_frete(cid, fid, "cancelado")
                st.rerun()


# ---------------------------------------------------------------- tela
abertos = repo.fretes(cid, ["orcamento", "enviado"])
agenda = repo.fretes(cid, ["fechado"])
feitos = repo.fretes(cid, ["realizado", "recusado", "cancelado"])
mes = repo.resumo_meses(cid, h.replace(day=1), (h.replace(day=28) + timedelta(days=4)).replace(day=1), origem="frete").iloc[-1]
a_receber = sum(max(_f(r["valor"]) - _f(r["recebido"]), 0) for _, r in
                list(agenda.iterrows()) + list(feitos[feitos["status"] == "realizado"].iterrows()))

if st.session_state.get("fr_edit"):
    if st.button("Cancelar edição", icon=":material/close:", type="tertiary", key="fr_ed_cancelar"):
        for k in ("fr_edit", "fr_rasc"):
            st.session_state.pop(k, None)
        st.session_state["fr_et"] = 0
        st.rerun()
    st.subheader("Editar orçamento")
    novo_por_etapas()
    st.stop()

aba_novo, aba_orc, aba_ag, aba_hist = st.tabs(["Novo orçamento", f"Orçamentos ({len(abertos)})",
                                               f"Agenda ({len(agenda)})", "Histórico"])
with aba_novo:
    _fn = repo.frete(cid, st.session_state["_frete_novo"]) if st.session_state.get("_frete_novo") else None
    if _fn and _fn["status"] in ("orcamento", "enviado"):
        st.success(f"Orçamento salvo ({brl(_f(_fn['valor']))} · {_quando(_fn)}). Ele fica em **Orçamentos** "
                   "até o cliente responder.", icon=":material/check_circle:")
        a, b = st.container(key="linha_fr_ok").columns(2)
        a.link_button("Enviar pelo WhatsApp", _link(_fn, msg_orcamento(_fn)), icon=":material/send:",
                      type="primary", width="stretch")
        if b.button("Novo orçamento", icon=":material/add:", width="stretch", key="fr_outro"):
            st.session_state.pop("_frete_novo", None)
            st.rerun()
    else:
        novo_por_etapas()
with aba_orc:
    if abertos.empty:
        st.info("Nenhum orçamento aguardando resposta. Crie um em **Novo orçamento**.")
    for f in abertos.to_dict("records"):
        cartao(f)
with aba_ag:
    _ui.olho("fr")
    _ui.kpis([("Próximas viagens", len(agenda), "fechadas"),
              ("Orçamentos abertos", len(abertos), "aguardando resposta"),
              ("A receber", brl(a_receber), "de viagens fechadas"),
              ("Lucro no mês", brl(_f(mes["outras_receitas"]) - _f(mes["despesas"])), "fretamentos")])
    if agenda.empty:
        st.info("Nenhuma viagem fechada na agenda.")
    for f in agenda.to_dict("records"):
        cartao(f)
with aba_hist:
    if feitos.empty:
        st.info("As viagens realizadas, recusadas e canceladas aparecem aqui.")
    for f in sorted(feitos.to_dict("records"), key=lambda r: r["data_ida"], reverse=True)[:50]:
        cartao(f)
