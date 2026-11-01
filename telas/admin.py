"""Administração: painel de assinantes (empresas/gestores) — receita, vencimentos, cobrança e planos."""
from datetime import timedelta

import streamlit as st

from core import planos as pl
from core import repo
from core.fmt import brl, data_br, hoje, link_whats, somar_meses
from telas import _ui

if not st.session_state["usuario"].get("admin"):
    st.stop()

st.title("Assinantes")
_TEM = {"asaas": _ui.asaas_api() is not None, "mercadopago": _ui.mp_api() is not None}
if any(_TEM.values()):
    with st.container(border=True, key="card_gateway"):
        _esc = (pl.config("gateway") or {}).get("ativo") or "asaas"
        g1, g2 = st.columns([3, 2], vertical_alignment="center")
        novo_gw = g1.segmented_control(
            "Receber as novas assinaturas por", list(_ui.GATEWAYS), default=_esc, key="gw_ativo",
            format_func=lambda g: _ui.GATEWAYS[g] + ("" if _TEM[g] else " (sem credencial)"))
        if novo_gw and novo_gw != _esc:
            repo.salvar_config("gateway", {"ativo": novo_gw})
            st.toast(f"Novas assinaturas agora pelo {_ui.GATEWAYS[novo_gw]}.")
            st.rerun()
        ef = _ui.gateway_ativo()
        g1.caption(("⚠️ O " + _ui.GATEWAYS[_esc] + " está sem credencial nos Secrets — usando o "
                    + _ui.GATEWAYS[ef] + ". " if ef != _esc else "")
                   + "Vale para quem assinar a partir de agora; quem já assina continua onde está até trocar de "
                     "plano ou cancelar. O app confere os pagamentos sozinho a cada 30 min (e quando o gestor abre "
                     "Meu plano).")
        sincronizar_agora = g2.button("Sincronizar pagamentos agora", icon=":material/sync:", width="stretch")
    if sincronizar_agora:
        r = _ui.sincronizar_pagamentos(forcar=True) or {}
        st.toast(f"{r.get('empresas', 0)} assinatura(s) conferida(s) · {r.get('pagamentos_novos', 0)} pagamento(s) "
                 f"novo(s) · {r.get('valores_atualizados', 0)} valor(es) atualizado(s)")
        for e in r.get("erros") or []:
            st.error(e)
df = repo.empresas_todas()
if df.empty:
    st.info("Nenhuma empresa cadastrada ainda.")
    st.stop()

HOJE = hoje()
AVISO_DIAS = 7
cat = pl.catalogo()

# situação de cada empresa
SIT = {"pago": ("pago", "Em dia"), "vence": ("vence_logo", "Vence logo"), "vencido": ("vencido", "Vencido"),
       "teste": ("embarcou", "Degustação"), "acabou": ("vencido", "Degustação acabou"),
       "cortesia": ("desembarcou", "Exclusivo"),
       "sem_plano": ("vencido", "Sem plano"), "off": ("faltou", "Desativada"),
       "pausa": ("aviso", "Pausa de férias")}


def _situacao(r) -> str:
    if not r["ativo"]:
        return "off"
    contratado = r["plano"]
    ate = r["plano_ate"]
    tipo = pl.tipo_da_empresa(r)
    if contratado not in cat:
        return "sem_plano"
    if tipo in ("teste", "cortesia"):
        if ate and ate < HOJE:
            return "acabou"
        return tipo
    if ate and ate < HOJE:
        return "vencido"
    if pl.em_pausa(r, HOJE):
        return "pausa"
    if ate and ate <= HOJE + timedelta(days=AVISO_DIAS):
        return "vence"
    return "pago"


linhas = []
for r in df.to_dict("records"):
    r["sit"] = _situacao(r)
    r["vig"] = pl.plano_da_empresa(r, HOJE, cat)
    linhas.append(r)

pagos = [r for r in linhas if r["sit"] in ("pago", "vence", "pausa")]
testes = [r for r in linhas if r["sit"] == "teste"]
testes_7 = sum(1 for r in testes if r["plano_ate"] and r["plano_ate"] <= HOJE + timedelta(days=AVISO_DIAS))
receita = sum(pl.preco_vigente(r, HOJE, cat) for r in pagos)
pedidos = [r for r in linhas if r.get("pedido")]
cont = {k: sum(1 for r in linhas if r["sit"] == k) for k in SIT}

_ui.kpis([("Receita por mês", brl(receita), f"{len(pagos)} assinante(s) pagante(s)"),
          ("Vencem em 7 dias", str(cont["vence"]), f"{cont['vencido']} já vencido(s)"),
          ("Em degustação", str(len(testes)), f"{testes_7} acaba(m) em 7 dias"),
          ("Bloqueados", str(cont["vencido"] + cont["acabou"] + cont["sem_plano"]), "sem plano em vigor")])

por_plano = {k: sum(1 for r in linhas if r["vig"] == k and r["ativo"]) for k in cat}
st.markdown(" ".join(_ui.tag("pago", f"{cat[k]['nome']}: {n}")
                     for k, n in por_plano.items()) +
            f" <span class='ve-sub'>· {len(linhas)} empresa(s) · {int(df['vans'].sum())} van(s) · "
            f"{int(df['alunos'].sum())} alunos ativos</span>", unsafe_allow_html=True)

if pedidos:
    st.warning(f"**{len(pedidos)} pedido(s) de assinatura** aguardando confirmação de pagamento — estão no topo da "
               "lista (filtro *Pedidos*).", icon=":material/shopping_cart:")

# filtros
FILTROS = {"Todos": None, "Pedidos": "pedido", "Vencem logo": {"vence"}, "Vencidos": {"vencido"}, "Pagantes": {"pago", "vence"},
           "Degustação": {"teste", "acabou"}, "Exclusivo": {"cortesia"},
           "Bloqueados": {"vencido", "acabou", "sem_plano"}, "Desativadas": {"off"}}
a, b = st.columns([3, 2])
filtro = a.segmented_control("Mostrar", list(FILTROS), default="Todos", label_visibility="collapsed") or "Todos"
busca = b.text_input("Buscar", placeholder="Buscar nome ou e-mail", label_visibility="collapsed").strip().lower()

ORDEM_SIT = {"vencido": 0, "acabou": 1, "sem_plano": 2, "vence": 3, "teste": 4, "pago": 5, "cortesia": 6, "off": 7}
sel = [r for r in linhas
       if (FILTROS[filtro] is None or (FILTROS[filtro] == "pedido" and r.get("pedido"))
           or (FILTROS[filtro] != "pedido" and r["sit"] in FILTROS[filtro]))
       and (not busca or busca in (r["nome"] or "").lower() or busca in (r["email"] or "").lower())]
sel.sort(key=lambda r: (not r.get("pedido"), ORDEM_SIT[r["sit"]], r["plano_ate"] or HOJE, r["nome"] or ""))
if not sel:
    st.info("Nenhuma empresa neste filtro.")


def _mensagem(r) -> str | None:
    primeiro = (r["nome"] or "").split(" ")[0]
    p = cat.get(r["plano"])
    if p is None:
        return (f"Olá, {primeiro}! Sua conta no Turminha a Bordo está sem plano e o acesso está pausado (nada foi "
                "apagado). Quer que eu te ajude a escolher um plano para voltar a usar? 🚐")
    valor = pl.brl(pl.preco_vigente(dict(r, plano_ate=HOJE), HOJE, cat) or p["preco"])
    if r["sit"] == "vence":
        return (f"Olá, {primeiro}! Sua assinatura do plano {p['nome']} do Turminha a Bordo vence em "
                f"{data_br(r['plano_ate'])}. Quer que eu envie o Pix de {valor} para renovar? 🚐")
    if r["sit"] == "vencido":
        return (f"Olá, {primeiro}! Sua assinatura do plano {p['nome']} do Turminha a Bordo venceu em "
                f"{data_br(r['plano_ate'])} e a conta voltou o acesso foi pausado (nada foi apagado). Quer renovar por "
                f"{valor}/mês? 🚐")
    if r["sit"] == "teste" and r["plano_ate"]:
        return (f"Olá, {primeiro}! Sua degustação do plano {p['nome']} do Turminha a Bordo vai até "
                f"{data_br(r['plano_ate'])}. Está gostando? Para continuar com tudo liberado depois disso, é "
                f"{pl.preco_txt(p)}/mês. Posso te mandar o Pix? 🚐")
    if r["sit"] == "acabou":
        return (f"Olá, {primeiro}! Sua degustação do plano {p['nome']} do Turminha a Bordo terminou e "
                f"o acesso foi pausado (nada foi apagado). Quer continuar no {p['nome']} por {pl.preco_txt(p)}/mês? 🚐")
    return None


antigos = {str(x["id"]): x for x in repo.precos_antigos(HOJE).to_dict("records")}


for r in sel:
    chave, rotulo = SIT[r["sit"]]
    p = cat.get(r["plano"]) or {"nome": "Sem plano", "preco": 0.0}
    tem_plano = r["plano"] in cat
    with st.container(border=True, key=f"card_{r['id']}"):
        ate = f" até {data_br(r['plano_ate'])}" if r["plano_ate"] and tem_plano else ""
        if tem_plano and pl.tipo_da_empresa(r) != "pago":
            ate = f" · {pl.TIPOS[pl.tipo_da_empresa(r)]}" + (ate or " sem prazo")
        ultimo = f" · último acesso {data_br(r['ultimo_acesso'])}" if r.get("ultimo_acesso") else ""
        extras = ""
        if r.get("vip"):
            extras += " " + _ui.tag("vence_logo", "💎 VIP")
        if r.get("asaas_assinatura"):
            extras += " " + _ui.tag("embarcou", "💳 Asaas")
        elif r.get("mp_assinatura"):
            extras += " " + _ui.tag("embarcou", "💳 Mercado Pago · cartão")
        elif r.get("gateway") == "mercadopago":
            extras += " " + _ui.tag("embarcou", "💳 Mercado Pago · Pix/boleto")
        if int(r.get("meses_gratis") or 0):
            extras += " " + _ui.tag("embarcou", f"🎁 {int(r['meses_gratis'])} mês(es) grátis")
        vig = pl.preco_vigente(r, HOJE, cat)
        if vig:
            orig = pl.ORIGENS.get(r.get("desconto_origem") or "", "")
            extras += (f" <span class='ve-sub'>· {pl.brl(vig)}/mês" + (f" ({orig})" if orig and vig < p["preco"] else "")
                       + (" · anual" if r.get("periodo") == "anual" else "") + "</span>")
        st.markdown(_ui.sem_formula(f"**{_ui.esc(r['nome'])}** {_ui.tag(chave, rotulo)} {_ui.tag('pago', p['nome'] + ate)}{extras}  \n"
                    f"<span class='ve-sub'>{_ui.esc(r['email'])} · {_ui.esc(r['telefone'] or 'sem telefone')} · "
                    f"{r['vans']} van(s) · {r['alunos']} aluno(s) · desde {data_br(r['desde'])}{ultimo}</span>"),
                    unsafe_allow_html=True)
        ped = r.get("pedido")
        if ped:
            st.info(_ui.sem_formula(f"**Pedido:** {cat[ped['plano']]['nome']} {pl.PERIODOS[ped['periodo']].lower()} · "
                    f"**{pl.brl(ped['preco'])}/mês**" + (f" · {ped['rotulo']}" if ped.get("rotulo") else "")
                    + (f" · total {pl.brl(ped['total'])}" if ped["periodo"] == "anual" else "")
                    + (f" · por {ped['duracao_meses']} mês(es)" if ped.get("duracao_meses") else "")),
                    icon=":material/shopping_cart:")
            p1, p2 = st.container(key=f"linha_p_{r['id']}").columns(2)
            if ped.get("asaas_assinatura") or ped.get("gateway") == "mercadopago":
                st.caption(f"Cobrança gerada no {'Mercado Pago' if ped.get('gateway') == 'mercadopago' else 'Asaas'}"
                           " — o plano libera sozinho quando o pagamento cair. "
                           "Use “Confirmar pagamento” só se ele pagou por fora.")
            if p1.button("Confirmar pagamento", key=f"conf_{r['id']}", type="primary", icon=":material/check:",
                         width="stretch"):
                ate_ = repo.registrar_pagamento(r["id"], HOJE, ped)
                st.toast(f"{r['nome']}: {cat[ped['plano']]['nome']} liberado até {data_br(ate_)}.")
                st.rerun()
            if p2.button("Descartar pedido", key=f"desc_{r['id']}", icon=":material/close:", width="stretch"):
                repo.salvar_pedido(r["id"], None)
                st.rerun()
        c1, c2 = st.container(key=f"linha_a_{r['id']}").columns(2)
        c3, c4 = st.container(key=f"linha_b_{r['id']}").columns(2)
        msg = _mensagem(r)
        lk = link_whats(r["telefone"], msg) if msg else None
        if lk:
            c1.link_button("Cobrar" if r["sit"] in ("vence", "vencido") else
                           "Convidar a assinar" if r["sit"] in ("teste", "acabou") else "Oferecer plano", lk,
                           icon=":material/chat:", width="stretch")
        if tem_plano and r["ativo"] and r["sit"] != "cortesia":
            anual = r.get("periodo") == "anual"
            if c2.button("Pagou: +12 meses" if anual else "Pagou: +1 mês", key=f"mes_{r['id']}",
                         icon=":material/payments:", width="stretch",
                         help=f"Marca como pago e renova o {p['nome']}"):
                ate_ = repo.registrar_pagamento(r["id"], HOJE)
                st.toast(f"{r['nome']}: {p['nome']} renovado até {data_br(ate_)}.")
                st.rerun()
        mg = int(r.get("meses_gratis") or 0)
        if mg and tem_plano and r["ativo"]:
            if st.button(f"Usar mês grátis da indicação ({mg} disponível(is))", key=f"mg_{r['id']}",
                         icon=":material/redeem:", width="stretch"):
                ate_ = repo.usar_mes_gratis(r["id"], HOJE)
                st.toast(f"{r['nome']}: +1 mês grátis, até {data_br(ate_)}.")
                st.rerun()
        velho = antigos.get(str(r["id"]))
        if velho:
            if st.button(f"Atualizar para o preço novo ({pl.brl(float(velho['atual']))} → "
                         f"{pl.brl(float(velho['novo']))})", key=f"pn_{r['id']}", icon=":material/price_change:",
                         width="stretch", help="Hoje esta empresa paga o preço antigo do plano."):
                repo.atualizar_para_preco_novo([r["id"]])
                st.toast(f"{r['nome']}: agora paga {pl.brl(float(velho['novo']))}/mês.")
                st.rerun()
        with c3.popover("Plano", icon=":material/workspace_premium:", width="stretch"):
            with st.form(f"plano_{r['id']}"):
                planos = list(cat)
                novo = st.selectbox("Plano", planos, index=planos.index(r["plano"]) if tem_plano else 0,
                                    format_func=lambda k: f"{cat[k]['nome']} ({pl.preco_txt(cat[k])})")
                tipos = list(pl.TIPOS)
                tipo = st.radio("Como liberar", tipos, index=tipos.index(pl.tipo_da_empresa(r)), horizontal=True,
                                format_func=pl.TIPOS.get,
                                help="Pago: o cliente pagou. Degustação: grátis por alguns dias e depois o acesso "
                                     "bloqueia sozinho até assinar. Exclusivo: liberado sem cobrar.")
                dias = st.selectbox("Degustação por", pl.DIAS_TESTE, index=1, format_func=lambda d: f"{d} dias",
                                    help="Só para Degustação — conta a partir de hoje.")
                validade = st.date_input("Válido até (Pago e Exclusivo)", value=r["plano_ate"] or somar_meses(HOJE, 1),
                                         format="DD/MM/YYYY")
                sem_prazo = st.checkbox("Exclusivo sem prazo", value=r["sit"] == "cortesia" and not r["plano_ate"])
                combinado = st.number_input("Preço combinado (R$/mês)", min_value=0.0, step=1.0, format="%.2f",
                                            value=float(r.get("preco_combinado") or 0),
                                            help="Preço negociado só com esta empresa. 0 = usa o preço normal "
                                                 "(com as promoções).")
                if st.form_submit_button("Salvar plano", type="primary"):
                    if tipo == "teste":
                        ate_novo = HOJE + timedelta(days=dias)
                    elif tipo == "cortesia" and sem_prazo:
                        ate_novo = None
                    else:
                        ate_novo = validade
                    repo.definir_plano(r["id"], novo, ate_novo, tipo)
                    repo.definir_preco_combinado(r["id"], combinado or None)
                    st.toast(f"{r['nome']}: {cat[novo]['nome']}"
                             + f" · {pl.TIPOS[tipo]}"
                             + (f" até {data_br(ate_novo)}" if ate_novo else ""))
                    st.rerun()
        if c4.button("Desativar" if r["ativo"] else "Reativar", key=f"at_{r['id']}", width="stretch",
                     icon=":material/block:" if r["ativo"] else ":material/check_circle:"):
            repo.ativar_empresa(r["id"], not r["ativo"])
            st.rerun()


# ---------------------------------------------------------------- guarda dos dados (fidelização)
st.divider()
_dias = int(pl.config("fidelidade").get("dados_dias") or 60)
st.subheader("Dados para apagar")
venc_dados = repo.dados_vencidos(HOJE)
if venc_dados.empty:
    st.caption(f"Ninguém passou do prazo de guarda ({_dias} dias depois do vencimento sem pagar).")
else:
    st.caption(f"Empresas sem plano há mais de {_dias} dias. Os gestores foram avisados em **Meu plano**. Apagar "
               "remove alunos, responsáveis, vans, escolas, mensalidades, contratos, financeiro e conversas — a conta "
               "e o histórico de assinatura ficam. Não dá para desfazer.")
    for r in venc_dados.to_dict("records"):
        with st.container(border=True, key=f"card_apagar_{r['id']}"):
            st.markdown(f"**{_ui.esc(r['nome'])}** <span class='ve-sub'>· venceu em {data_br(r['plano_ate'])} · "
                        f"{int(r['alunos'])} aluno(s) · {int(r['vans'])} van(s)"
                        + (f" · cancelou em {data_br(r['cancelado_em'])}" if r.get("cancelado_em") else "")
                        + "</span>", unsafe_allow_html=True)
            if st.checkbox("Confirmo apagar os dados desta empresa", key=f"conf_ap_{r['id']}") and \
                    st.button("Apagar dados", key=f"ap_{r['id']}", icon=":material/delete_forever:"):
                repo.apagar_dados_empresa(r["id"], HOJE)
                st.toast(f"Dados de {r['nome']} apagados.")
                st.rerun()
