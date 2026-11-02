"""Meu plano: plano em vigor, uso (vans/alunos), promoções (cupom, anual, campanha, VIP) e pedido de assinatura."""
import streamlit as st

from core import asaas, auth, db, mercadopago, planos as pl, repo
from core.fmt import agora, data_br, hoje, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
API = _ui.asaas_api()          # cliente do Asaas (None = não configurado)
MP = _ui.mp_api()              # cliente do Mercado Pago (None = não configurado)
GW = _ui.gateway_ativo()       # quem recebe as NOVAS assinaturas; None = nenhum: pedido pelo WhatsApp e o admin libera
GW_NOME = _ui.GATEWAYS.get(GW or "", "")
STATUS_PAG = {**asaas.STATUS, **mercadopago.STATUS}
ANDROID = _ui.app_android()    # app da Play Store: não vende lá dentro (o gestor assina pelo site)
METODOS = {"cartao": "Cartão de crédito — renova sozinho", "avulso": "Pix ou boleto — paga a cada período"}
if API or MP:
    _sync = _ui.sincronizar_pagamentos(c["id"])
    if _sync and _sync.get("pagamentos_novos"):
        auth.perfil(st.session_state["usuario"])
        st.toast("Pagamento confirmado! Seu plano está liberado. 🎉")
emp = repo.empresa(c["id"])
HOJE = hoje()
cat = pl.catalogo()
atual = pl.plano_da_empresa(emp, HOJE, cat)       # None = sem plano em vigor (acesso bloqueado)
p = cat.get(atual)
uso = repo.uso_empresa(c["id"])
ENGINE = db.conexao(db.banco_ativo()).engine


def _criar_online(ped: dict, doc, metodo) -> bool:
    """Gera a cobrança no gateway ativo (encerrando a assinatura antiga, esteja onde estiver). False = erro mostrado."""
    if GW == "asaas" and not asaas.documento_valido(doc):
        st.error("Digite um CPF ou CNPJ válido.")
        return False
    try:
        if GW == "asaas":
            repo.salvar_documento(c["id"], asaas.so_digitos(doc))
            e_ = repo.empresa(c["id"])
            if e_.get("mp_assinatura") or e_.get("gateway") == "mercadopago":
                mercadopago.cancelar_assinatura(MP, ENGINE, e_)
            asaas.assinar(API, ENGINE, repo.empresa(c["id"]), st.session_state["usuario"]["email"], ped, HOJE)
            db.gravar("update condutores set gateway = 'asaas' where id = cast(:c as uuid)", c=str(c["id"]))
        else:
            e_ = repo.empresa(c["id"])
            if e_.get("asaas_assinatura") and API:
                asaas.cancelar_assinatura(API, ENGINE, e_)
            mercadopago.cancelar_assinatura(MP, ENGINE, repo.empresa(c["id"]))
            mercadopago.assinar(MP, ENGINE, repo.empresa(c["id"]), st.session_state["usuario"]["email"], ped, HOJE,
                                metodo or "cartao")
    except (asaas.AsaasErro, mercadopago.MPErro) as e:
        db._mudou()
        st.error(f"O {GW_NOME} recusou: {e}")
        return False
    db._mudou()
    return True


def _campos_pagamento(chave: str):
    """CPF/CNPJ (Asaas exige) ou a forma de pagar (Mercado Pago). Devolve (documento, método)."""
    if GW == "asaas":
        return st.text_input("CPF ou CNPJ de quem paga", value=emp.get("documento") or "", key=f"doc_{chave}",
                             help="O Asaas exige para emitir a cobrança (Pix, boleto ou cartão)."), None
    if GW == "mercadopago":
        return None, st.radio("Como pagar", list(METODOS), format_func=METODOS.get, key=f"met_{chave}")
    return None, None


st.title("Meu plano")


def _uso(n, lim):
    return f"{n} · sem limite" if lim is None else f"{n} de {lim}"


# ---------------------------------------------------------------- situação
venc = emp.get("plano_ate")
contratado = emp.get("plano")
tipo = pl.tipo_da_empresa(emp)
vigente = pl.preco_vigente(emp, HOJE, cat)
if p is None:
    sub = ("venceu em " + data_br(venc)) if venc else "sem plano"
elif tipo == "teste":
    sub = "degustação até " + data_br(venc)
elif tipo == "cortesia":
    sub = "exclusivo" + (" até " + data_br(venc) if venc else "")
else:
    sub = f"{pl.brl(vigente)}/mês" + (f" · até {data_br(venc)}" if venc else "")
GRATIS = pl.no_gratis(emp, HOJE, cat)        # sem plano em vigor, mas no Grátis (só financeiro)
LIM_G = pl.limite_gratis("alunos")
if p is None and GRATIS:
    sub, situacao = f"só financeiro · até {LIM_G} alunos", "Grátis"
elif p is None:
    situacao = "Bloqueado"
else:
    situacao = {"teste": "Degustação", "cortesia": "Exclusivo"}.get(tipo, "Ativo")
_ui.kpis([("Plano atual", p["nome"] if p else ("Grátis" if GRATIS else "Nenhum"), sub),
          ("Vans", _uso(uso['vans'], p['vans'] if p else (pl.limite_gratis("vans") if GRATIS else None))),
          ("Alunos ativos", _uso(uso['alunos'], p['alunos'] if p else (LIM_G if GRATIS else None))),
          ("Situação", situacao)])

if p is None:
    if st.session_state["usuario"].get("admin"):
        st.warning("Sua empresa está sem plano em vigor (como administrador, você continua com acesso).",
                   icon=":material/admin_panel_settings:")
    elif GRATIS:
        motivo = ("Sua degustação terminou" if tipo == "teste" else "Sua assinatura venceu") if venc else \
            "Você está sem assinatura"
        st.info(f"**{motivo}** e sua conta está no **plano Grátis**: mensalidades, cobrança pelo WhatsApp e "
                f"financeiro para até **{LIM_G} alunos**. Rota, avisos aos pais, mapa, contrato e fretamento voltam "
                "quando você assinar — **nada foi apagado**.", icon=":material/redeem:")
        if uso["alunos"] > (LIM_G or 0):
            st.warning(f"Você tem **{uso['alunos']} alunos ativos** — o Grátis vale para até {LIM_G}. Os alunos "
                       "continuam aí, mas para cadastrar mais é preciso assinar (ou desativar alguns).",
                       icon=":material/group:")
    else:
        motivo = ("Sua degustação terminou" if tipo == "teste" else "Sua assinatura venceu") if venc else \
            "Sua conta está sem plano"
        st.error(f"**{motivo}** e o acesso ao app está bloqueado — para você, seus motoristas e os pais. "
                 "**Nada foi apagado**: assine abaixo e tudo volta assim que o pagamento for confirmado.",
                 icon=":material/lock:")
elif tipo == "teste" and venc:
    faltam = (venc - HOJE).days
    st.info(f"Você está experimentando o plano **{p['nome']}** de graça até **{data_br(venc)}** "
            f"({'hoje é o último dia' if faltam <= 0 else 'falta 1 dia' if faltam == 1 else f'faltam {faltam} dias'})."
            + (f" Depois disso, se não assinar, sua conta passa para o **plano Grátis** (só financeiro, até "
               f"{LIM_G} alunos) — nada do que você cadastrou se perde." if pl.config("gratis").get("ativo") else
               " Depois disso o acesso é bloqueado até assinar — nada do que você cadastrou se perde."),
            icon=":material/celebration:")
FID = pl.config("fidelidade")
PAUSA_TXT = pl.brl(float(FID.get("pausa_preco") or 0))
if p and pl.em_pausa(emp, HOJE):
    with st.container(border=True, key="card_pausa"):
        st.markdown(f"⏸️ **Pausa de férias até {data_br(emp['pausa_ate'])}** · {PAUSA_TXT}/mês  \n"
                    "<span class='ve-sub'>Rota e chamada ficam pausadas; alunos, mensalidades, contratos e a área dos "
                    "pais continuam funcionando. Seus dados e seu preço continuam guardados. Quando a pausa acabar, o "
                    "plano volta ao normal sozinho.</span>", unsafe_allow_html=True)
        if st.button("Voltar ao normal agora", icon=":material/play_arrow:", type="primary"):
            repo.encerrar_pausa(c["id"], HOJE, API, MP)
            auth.perfil(st.session_state["usuario"])
            st.toast("Pausa encerrada — rota e chamada liberadas.")
            st.rerun()
if p and emp.get("cancelado_em") and venc:
    st.warning(f"Você cancelou a assinatura em {data_br(emp['cancelado_em'])}. O plano vale até **{data_br(venc)}**; "
               + (f"depois sua conta passa para o plano Grátis (só financeiro, até {LIM_G} alunos) e os dados ficam "
                  "guardados. " if pl.config("gratis").get("ativo") else
                  f"depois o acesso é bloqueado e os dados ficam guardados por {int(FID.get('dados_dias') or 60)} dias. ")
               + "Para continuar, é só assinar de novo abaixo.", icon=":material/event_busy:")
_prazo = pl.prazo_dados(emp, HOJE) if p is None and not st.session_state["usuario"].get("admin") else None
if _prazo:
    st.warning(f"🗂️ Seus dados ficam guardados até **{data_br(_prazo)}**. Depois dessa data, alunos, mensalidades, "
               "contratos e o resto do cadastro são **apagados** e não dá para recuperar.", icon=":material/delete_forever:")
if p is None and contratado in cat and pl.pode_pausar(emp, HOJE) and not ANDROID:
    with st.container(border=True, key="card_pausa_oferta"):
        st.markdown(f"**Está nas férias? Pause por {PAUSA_TXT}/mês** em vez de perder tudo  \n"
                    f"<span class='ve-sub'>Por até {int(FID.get('pausa_dias') or 60)} dias: seus dados e seu preço "
                    "ficam guardados, mensalidades e a área dos pais funcionam; só rota e chamada ficam pausadas. "
                    "Depois volta ao plano normal.</span>", unsafe_allow_html=True)
        doc_p, met_p = _campos_pagamento("pausa")
        if st.button(f"Pausar por {PAUSA_TXT}/mês", type="primary", icon=":material/pause_circle:"):
            ped = dict(plano=contratado, plano_nome=cat[contratado]["nome"], periodo="mensal",
                       preco=float(FID.get("pausa_preco") or 0), base=float(FID.get("pausa_preco") or 0),
                       total=float(FID.get("pausa_preco") or 0), origem="pausa", rotulo="Pausa de férias",
                       pausa=True, pausa_dias=int(FID.get("pausa_dias") or 60),
                       em=agora().isoformat(timespec="minutes"),
                       mensagem=f"Olá! Quero a pausa de férias ({PAUSA_TXT}/mês) do Turminha a Bordo. "
                                f"Empresa: {c['nome']} ({st.session_state['usuario']['email']}).")
            if GW:
                if not _criar_online(ped, doc_p, met_p):
                    st.stop()
            else:
                repo.salvar_pedido(c["id"], ped)
            st.rerun()
if p and tipo == "pago" and emp.get("desconto_origem") and emp.get("desconto_ate"):
    st.caption(f"Preço promocional ({pl.ORIGENS.get(emp['desconto_origem'], '')}) até {data_br(emp['desconto_ate'])}; "
               "depois volta ao preço normal do plano.")
if p:
    for rec, nome in (("vans", "vans"), ("alunos", "alunos")):
        lim = p[rec]
        if lim is not None and uso[rec] >= lim:
            st.info(f"Você atingiu o limite de {nome} do plano {p['nome']}.", icon=":material/upgrade:")
mg = int(emp.get("meses_gratis") or 0)
if mg:
    st.success(f"Você tem **{mg} mês(es) grátis** ganhos por indicação — eles entram nas próximas renovações.",
               icon=":material/redeem:")

_ui.faixa_vip(emp)

# ---------------------------------------------------------------- cupom e período (lidos antes dos cartões)
cupom = None
cod = st.session_state.get("mp_cupom")
if cod:
    cupom, erro_cupom = repo.validar_cupom(cod, c["id"], HOJE)
    if erro_cupom:
        st.session_state.pop("mp_cupom", None)
        st.session_state["mp_cupom_erro"] = erro_cupom
periodo = st.session_state.get("mp_periodo") or "mensal"
cupom_preco = cupom if cupom and cupom["tipo"] in ("pct", "valor") else None
precos = _ui.precos_planos(emp, cupom_preco, periodo)

st.subheader("Planos")
_ui.cartoes_planos(atual, precos)

# ---------------------------------------------------------------- pedido em andamento
contato = auth.cfg("contato_whatsapp")
pedido = emp.get("pedido")
if pedido:
    with st.container(border=True, key="card_pedido"):
        em = str(pedido.get("em") or "")
        st.markdown(_ui.sem_formula(f"**Pedido enviado** em {em[8:10]}/{em[5:7]} · "
                    f"plano **{cat[pedido['plano']]['nome']}** {pl.PERIODOS[pedido['periodo']].lower()} · "
                    f"**{pl.brl(pedido['preco'])}/mês**" + (f" · {pedido['rotulo']}" if pedido.get("rotulo") else "") +
                    "  \n<span class='ve-sub'>Assim que o pagamento for confirmado, o plano é liberado aqui.</span>"),
                    unsafe_allow_html=True)
        x1, x2 = st.container(key="linha_pedido").columns(2)
        if pedido.get("asaas_assinatura") and API:
            cob = repo.cobrancas_asaas(c["id"], pedido["asaas_assinatura"])
            pend = [x for x in cob if x["status"] not in asaas.PAGO and x.get("link")]
            if pend and not ANDROID:
                x1.link_button("Pagar agora (Pix, boleto ou cartão)", pend[0]["link"], icon=":material/payments:",
                               type="primary", width="stretch")
            if x2.button("Já paguei — verificar", icon=":material/refresh:", width="stretch"):
                r = _ui.sincronizar_asaas(c["id"], forcar=True)
                if r and r.get("erros"):
                    st.error("; ".join(r["erros"]))
                elif not (r and r.get("pagamentos_novos")):
                    st.info("Ainda não chegou a confirmação. Pix costuma cair em segundos; boleto em até 3 dias "
                            "úteis. O app confere sozinho a cada 30 minutos.")
                else:
                    auth.perfil(st.session_state["usuario"])
                    st.rerun()
            if st.button("Cancelar pedido", icon=":material/close:", type="tertiary"):
                asaas.cancelar_assinatura(API, db.conexao(db.banco_ativo()).engine, emp)
                db._mudou()
                st.rerun()
        elif pedido.get("gateway") == "mercadopago" and MP:
            cartao = bool(pedido.get("mp_assinatura"))
            if pedido.get("mp_link") and not ANDROID:
                x1.link_button("Cadastrar o cartão e pagar" if cartao else "Pagar agora (Pix, boleto ou cartão)",
                               pedido["mp_link"], icon=":material/payments:", type="primary", width="stretch")
            if x2.button("Já paguei — verificar", icon=":material/refresh:", width="stretch", key="mp_verificar"):
                r = _ui.sincronizar_mp(c["id"], forcar=True)
                if r and r.get("erros"):
                    st.error("; ".join(r["erros"]))
                elif not (r and r.get("pagamentos_novos")):
                    st.info("Ainda não chegou a confirmação do Mercado Pago. Pix e cartão costumam cair em segundos; "
                            "boleto em até 3 dias úteis. O app confere sozinho a cada 30 minutos.")
                else:
                    auth.perfil(st.session_state["usuario"])
                    st.rerun()
            st.caption("Pagamento pelo Mercado Pago" + (" — depois do 1º pagamento, o cartão é cobrado sozinho a "
                       "cada período." if cartao else "."))
            if st.button("Cancelar pedido", icon=":material/close:", type="tertiary", key="mp_cancelar_pedido"):
                mercadopago.cancelar_assinatura(MP, ENGINE, emp)
                db._mudou()
                st.rerun()
        else:
            lk = link_whats(contato, pedido.get("mensagem", "")) if contato else None
            if lk:
                x1.link_button("Enviar no WhatsApp", lk, icon=":material/send:", width="stretch")
            if x2.button("Cancelar pedido", icon=":material/close:", width="stretch"):
                repo.salvar_pedido(c["id"], None)
                st.rerun()
elif API and emp.get("asaas_assinatura"):
    # assinatura automática ativa: últimas cobranças e cancelar
    with st.container(border=True, key="card_asaas"):
        anual = (emp.get("periodo") or "mensal") == "anual"
        st.markdown(_ui.sem_formula(f"**Assinatura automática ativa** · {pl.brl(float(emp.get('asaas_valor') or 0))}"
                    f"{'/ano' if anual else '/mês'}  \n<span class='ve-sub'>O Asaas manda a cobrança por e-mail "
                    "antes de cada vencimento (Pix, boleto ou cartão).</span>"), unsafe_allow_html=True)
        for x in repo.cobrancas_asaas(c["id"], emp["asaas_assinatura"])[:4]:
            pago = x["status"] in asaas.PAGO
            linha = (f"{x['vencimento']:%d/%m/%Y} · {pl.brl(float(x['valor'] or 0))} · "
                     f"{asaas.STATUS.get(x['status'], x['status'].lower())}")
            if not pago and x.get("link"):
                st.markdown(_ui.sem_formula(f"{linha} · [pagar]({x['link']})"))
            else:
                st.caption(("✅ " if pago else "") + linha)
elif MP and emp.get("mp_assinatura"):
    # assinatura no cartão (Mercado Pago) ativa: últimas cobranças
    with st.container(border=True, key="card_mp"):
        anual = (emp.get("periodo") or "mensal") == "anual"
        st.markdown(_ui.sem_formula(f"**Assinatura no cartão ativa** · {pl.brl(float(emp.get('mp_valor') or 0))}"
                    f"{'/ano' if anual else '/mês'}  \n<span class='ve-sub'>O Mercado Pago cobra o cartão sozinho a "
                    "cada período.</span>"), unsafe_allow_html=True)
        for x in repo.cobrancas_asaas(c["id"], emp["mp_assinatura"])[:4]:
            pago = x["status"] in asaas.PAGO
            st.caption(("✅ " if pago else "") + f"{x['vencimento']:%d/%m/%Y} · {pl.brl(float(x['valor'] or 0))} · "
                       f"{STATUS_PAG.get(x['status'], x['status'].lower())}")
elif MP and emp.get("gateway") == "mercadopago" and tipo == "pago" and venc and not emp.get("cancelado_em"):
    # paga por Pix/boleto no Mercado Pago: um link por período, liberado perto do vencimento
    with st.container(border=True, key="card_mp_avulso"):
        faltam = (venc - HOJE).days
        st.markdown(_ui.sem_formula(f"**Você paga por Pix ou boleto (Mercado Pago)** · próximo vencimento "
                    f"**{data_br(venc)}**  \n<span class='ve-sub'>A partir de 7 dias antes do vencimento aparece "
                    "aqui o botão para pagar o próximo período.</span>"), unsafe_allow_html=True)
        valor_ren = asaas._valor_esperado(emp, HOJE, cat)
        if faltam <= 7 and valor_ren and ANDROID:
            _ui.aviso_assinar_pelo_site()
        elif faltam <= 7 and valor_ren:
            chave_lk = f"_mp_ren_{c['id']}"
            if st.button(f"Pagar o próximo período · {pl.brl(valor_ren)}", type="primary",
                         icon=":material/payments:", key="mp_renovar"):
                try:
                    st.session_state[chave_lk] = mercadopago.link_renovacao(
                        MP, ENGINE, emp, st.session_state["usuario"]["email"], valor_ren, venc)
                except mercadopago.MPErro as e:
                    st.error(f"O Mercado Pago recusou: {e}")
            if st.session_state.get(chave_lk):
                st.link_button("Abrir o pagamento (Pix, boleto ou cartão)", st.session_state[chave_lk],
                               icon=":material/open_in_new:", width="stretch")
                st.caption("Depois de pagar, o plano renova sozinho em poucos minutos.")

# ---------------------------------------------------------------- cancelar (com a oferta de pausa antes)
if p and tipo == "pago" and not emp.get("cancelado_em") and not pedido:
    with st.expander("Cancelar assinatura", icon=":material/cancel:"):
        if pl.pode_pausar(emp, HOJE):
            st.markdown(f"**Antes de cancelar: que tal uma pausa de férias?** Por **{PAUSA_TXT}/mês**, por até "
                        f"{int(FID.get('pausa_dias') or 60)} dias, você mantém **todos os dados** e o **seu preço** "
                        + ("de **Passageiro VIP** " if emp.get("vip") else "") +
                        "— só rota e chamada ficam pausadas. Depois volta ao normal sozinho.")
            if st.button(f"Pausar por {PAUSA_TXT}/mês", type="primary", icon=":material/pause_circle:",
                         key="pausar_ativo"):
                ate_p = repo.pausar(c["id"], HOJE, API, MP)
                auth.perfil(st.session_state["usuario"])
                st.toast(f"Pausa de férias ligada até {data_br(ate_p)}.")
                st.rerun()
            st.divider()
        perde = bool(FID.get("perde_vip", True))
        st.markdown("**Se cancelar:**  \n"
                    f"- o plano continua até **{data_br(venc) if venc else 'o fim do período pago'}** e depois "
                    + (f"sua conta passa para o **plano Grátis**: só mensalidades e financeiro, até {LIM_G} alunos — "
                       "rota, avisos aos pais, mapa, contrato e fretamento saem;  \n" if pl.config("gratis").get("ativo")
                       else "o acesso é bloqueado (para você, motoristas e pais);  \n")
                    + (f"- você **perde o preço de Passageiro VIP** ({pl.brl(vigente)}/mês) — se voltar, paga o preço "
                       "normal;  \n" if perde and emp.get("vip") else "")
                    + ("- seus dados continuam guardados." if pl.config("gratis").get("ativo") else
                       f"- seus dados ficam guardados por **{int(FID.get('dados_dias') or 60)} dias** depois do "
                       "vencimento e então são **apagados**."))
        if st.checkbox("Entendi e quero cancelar", key="conf_cancel") and \
                st.button("Cancelar assinatura", icon=":material/cancel:", key="btn_cancelar"):
            repo.cancelar_plano(c["id"], HOJE, API, MP)
            db._mudou()
            st.toast("Assinatura cancelada.")
            st.rerun()

# ---------------------------------------------------------------- assinar
st.subheader("Assinar")
if ANDROID:
    _ui.aviso_assinar_pelo_site()
else:
    pagos = list(cat)
    with st.container(border=True, key="card_assinar"):
        a, b = st.columns([3, 2])
        padrao = atual if atual in pagos else contratado if contratado in pagos else pagos[0]
        escolha = a.selectbox("Plano", pagos, index=pagos.index(padrao),
                              format_func=lambda k: f"{cat[k]['nome']} — {pl.preco_txt(cat[k])}/mês")
        anual_max = max(float(cat[k]["anual_desconto"] or 0) for k in pagos)
        rotulos = {"mensal": "Mensal", "anual": f"Anual (-{anual_max:.0f}%)" if anual_max else "Anual"}
        b.segmented_control("Período", list(rotulos), format_func=rotulos.get, key="mp_periodo", default="mensal")

        # cupom
        if cupom:
            cc1, cc2 = st.columns([3, 1])
            cc1.success(f"Cupom **{cupom['codigo']}** aplicado: " + (
                f"{cupom['valor']:g}% de desconto" if cupom["tipo"] == "pct" else
                f"{pl.brl(cupom['valor'])} de desconto" if cupom["tipo"] == "valor" else
                f"{int(cupom['valor'])} dias grátis") +
                (f" por {cupom['duracao_meses']} mês(es)" if cupom["tipo"] != "dias" and cupom.get("duracao_meses") else ""),
                icon=":material/sell:")
            if cc2.button("Remover", key="rm_cupom", width="stretch"):
                st.session_state.pop("mp_cupom", None)
                st.rerun()
        else:
            with st.form("cupom", border=False):
                cc1, cc2 = st.columns([3, 1], vertical_alignment="bottom")
                codigo = cc1.text_input("Cupom de desconto", placeholder="Tem um cupom? Digite aqui")
                if cc2.form_submit_button("Aplicar", width="stretch"):
                    ok, erro = repo.validar_cupom(codigo, c["id"], HOJE)
                    if ok:
                        st.session_state["mp_cupom"] = ok["codigo"]
                        st.session_state.pop("mp_cupom_erro", None)
                        st.rerun()
                    st.session_state["mp_cupom_erro"] = erro
            if st.session_state.get("mp_cupom_erro"):
                st.error(st.session_state["mp_cupom_erro"])

        # cupom de dias grátis: libera degustação na hora
        if cupom and cupom["tipo"] == "dias":
            plano_cupom = (cupom.get("planos") or [pl.config("degustacao").get("plano") or pagos[0]])[0]
            plano_cupom = plano_cupom if plano_cupom in cat else pagos[0]
            if tipo == "pago" and atual is not None:
                st.info("Esse cupom é de dias grátis e vale para quem ainda não é assinante.")
            elif st.button(f"Ativar {int(cupom['valor'])} dias grátis do {cat[plano_cupom]['nome']}", type="primary",
                           icon=":material/celebration:"):
                pl_, ate = repo.ativar_cupom_dias(c["id"], cupom, HOJE)
                st.session_state.pop("mp_cupom", None)
                st.toast(f"Pronto! {cat[pl_]['nome']} liberado até {data_br(ate)}.")
                st.rerun()
        else:
            if cupom and not pl.cupom_vale_para(cupom, escolha):
                st.warning(f"O cupom {cupom['codigo']} não vale para o plano {cat[escolha]['nome']}.")
            pr = precos[escolha]
            if pr.tem_desconto:
                linha = (f"<span style='text-decoration:line-through;color:#8A9BAA'>{pl.brl(pr.base)}</span> "
                         f"por <b style='font-size:1.25rem'>{pl.brl(pr.final)}/mês</b> · {_ui.esc(pr.rotulo)}")
                if pr.duracao_meses:
                    linha += f" — por {pr.duracao_meses} mês(es), depois {pl.brl(pr.base)}"
            else:
                linha = f"<b style='font-size:1.25rem'>{pl.brl(pr.final)}/mês</b>"
            if periodo == "anual":
                linha += f"<br><span class='ve-sub'>Pagamento anual: {pl.brl(pr.total)} por 12 meses</span>"
            st.markdown(_ui.sem_formula(linha), unsafe_allow_html=True)

            doc, metodo = _campos_pagamento("assinar")
            if st.button("Assinar", type="primary", icon=":material/workspace_premium:"):
                msg = (f"Olá! Quero assinar o Turminha a Bordo: plano {cat[escolha]['nome']} "
                       f"{pl.PERIODOS[periodo].lower()}, {pl.brl(pr.final)}/mês"
                       + (f" ({pr.rotulo})" if pr.tem_desconto else "")
                       + (f", total {pl.brl(pr.total)}" if periodo == "anual" else "")
                       + f". Empresa: {c['nome']} ({st.session_state['usuario']['email']}).")
                novo_pedido = dict(
                    plano=escolha, plano_nome=cat[escolha]["nome"], periodo=periodo, preco=pr.final, base=pr.base,
                    total=pr.total, origem=pr.origem, rotulo=pr.rotulo if pr.tem_desconto else "",
                    duracao_meses=pr.duracao_meses, cupom_id=str(pr.cupom["id"]) if pr.cupom else None,
                    vip_novo=pr.vip_novo, em=agora().isoformat(timespec="minutes"), mensagem=msg)
                if GW:
                    if not _criar_online(novo_pedido, doc, metodo):
                        st.stop()
                else:
                    repo.salvar_pedido(c["id"], novo_pedido)
                st.rerun()
        st.caption("Pagamento por Pix, boleto ou cartão. Assim que confirmado, o plano é liberado na sua conta."
                   + (" A cobrança se repete sozinha a cada período — dá para cancelar quando quiser." if GW == "asaas"
                      else " No cartão, a cobrança se repete sozinha; no Pix ou boleto, perto do vencimento aparece aqui "
                           "o botão para pagar o próximo período. Dá para cancelar quando quiser."
                      if GW == "mercadopago" else ""))


if st.session_state["usuario"].get("bloqueado"):
    st.caption(f"Dúvidas sobre a assinatura? Escreva para [{_ui.EMAIL_CONTATO}]({_ui.link_contato('Assinatura — Turminha a Bordo')}).")
