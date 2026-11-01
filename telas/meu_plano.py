"""Meu plano: plano em vigor, uso (vans/alunos), promoções (cupom, anual, campanha, VIP) e pedido de assinatura."""
import streamlit as st

from core import asaas, auth, db, planos as pl, repo
from core.fmt import agora, data_br, hoje, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
API = _ui.asaas_api()          # None = Asaas não configurado: assinatura pelo WhatsApp e o admin libera
if API:
    _sync = _ui.sincronizar_asaas(c["id"])
    if _sync and _sync.get("pagamentos_novos"):
        auth.perfil(st.session_state["usuario"])
        st.toast("Pagamento confirmado! Seu plano está liberado. 🎉")
emp = repo.empresa(c["id"])
HOJE = hoje()
cat = pl.catalogo()
atual = pl.plano_da_empresa(emp, HOJE, cat)       # None = sem plano em vigor (acesso bloqueado)
p = cat.get(atual)
uso = repo.uso_empresa(c["id"])

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
if p is None:
    situacao = "Bloqueado"
else:
    situacao = {"teste": "Degustação", "cortesia": "Exclusivo"}.get(tipo, "Ativo")
_ui.kpis([("Plano atual", p["nome"] if p else "Nenhum", sub),
          ("Vans", _uso(uso['vans'], p['vans'] if p else None)),
          ("Alunos ativos", _uso(uso['alunos'], p['alunos'] if p else None)),
          ("Situação", situacao)])

if p is None:
    if st.session_state["usuario"].get("admin"):
        st.warning("Sua empresa está sem plano em vigor (como administrador, você continua com acesso).",
                   icon=":material/admin_panel_settings:")
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
            " Depois disso o acesso é bloqueado até assinar — nada do que você cadastrou se perde.",
            icon=":material/celebration:")
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
            if pend:
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
        with st.expander("Cancelar assinatura"):
            st.caption("O plano continua até o fim do período já pago; depois disso o acesso é bloqueado até assinar "
                       "de novo. Nada é apagado.")
            if st.checkbox("Quero cancelar a cobrança automática", key="conf_cancel_asaas") and \
                    st.button("Cancelar assinatura", icon=":material/cancel:"):
                asaas.cancelar_assinatura(API, db.conexao(db.banco_ativo()).engine, emp)
                db._mudou()
                st.toast("Assinatura cancelada.")
                st.rerun()

# ---------------------------------------------------------------- assinar
st.subheader("Assinar")
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

        if API:
            doc = st.text_input("CPF ou CNPJ de quem paga", value=emp.get("documento") or "",
                                help="O Asaas exige para emitir a cobrança (Pix, boleto ou cartão).")
        if st.button("Assinar", type="primary", icon=":material/workspace_premium:"):
            msg = (f"Olá! Quero assinar o Pequenos a Bordo: plano {cat[escolha]['nome']} "
                   f"{pl.PERIODOS[periodo].lower()}, {pl.brl(pr.final)}/mês"
                   + (f" ({pr.rotulo})" if pr.tem_desconto else "")
                   + (f", total {pl.brl(pr.total)}" if periodo == "anual" else "")
                   + f". Empresa: {c['nome']} ({st.session_state['usuario']['email']}).")
            novo_pedido = dict(
                plano=escolha, plano_nome=cat[escolha]["nome"], periodo=periodo, preco=pr.final, base=pr.base,
                total=pr.total, origem=pr.origem, rotulo=pr.rotulo if pr.tem_desconto else "",
                duracao_meses=pr.duracao_meses, cupom_id=str(pr.cupom["id"]) if pr.cupom else None,
                vip_novo=pr.vip_novo, em=agora().isoformat(timespec="minutes"), mensagem=msg)
            if API:
                if not asaas.documento_valido(doc):
                    st.error("Digite um CPF ou CNPJ válido.")
                    st.stop()
                repo.salvar_documento(c["id"], asaas.so_digitos(doc))
                try:
                    asaas.assinar(API, db.conexao(db.banco_ativo()).engine, repo.empresa(c["id"]),
                                  st.session_state["usuario"]["email"], novo_pedido, HOJE)
                except asaas.AsaasErro as e:
                    db._mudou()
                    st.error(f"O Asaas recusou: {e}")
                    st.stop()
                db._mudou()
            else:
                repo.salvar_pedido(c["id"], novo_pedido)
            st.rerun()
    st.caption("Pagamento por Pix, boleto ou cartão. Assim que confirmado, o plano é liberado na sua conta."
               + (" A cobrança se repete sozinha a cada período — dá para cancelar quando quiser." if API else ""))
