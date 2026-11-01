"""Administração → Promoções: preços dos planos, cupons, campanhas, Passageiro VIP, indicação, divulgadores
(comissão e textos) e laboratório. Tudo ajustável."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from core import planos as pl, repo
from core.fmt import data_br, hoje
from telas import _ui

if not st.session_state["usuario"].get("admin"):
    st.stop()

HOJE = hoje()
st.title("Promoções")
st.caption("Regra: entre cupom, campanha, Passageiro VIP e anual, o cliente paga o **melhor preço** (não somam). "
           "Preço combinado passa por cima de tudo. Meses grátis da indicação são crédito à parte.")

cat = pl.catalogo()
abas = st.tabs(["Planos e preços", "Cupons", "Campanhas", "Passageiro VIP", "Degustação", "Indicação",
               "Divulgadores", "Laboratório"])
PLANOS = list(cat)


def _nome_plano(k):
    return cat[k]["nome"] if k in cat else f"{k} (excluído)"


# ================================================================ planos e preços
with abas[0]:
    st.markdown("Edite direto na tabela e salve. Deixe **Vans/Alunos** vazio para ilimitado e **Preço VIP** vazio "
                "para o plano não ter VIP. Os itens do cartão vão separados por **|**.")
    df = pd.DataFrame([dict(plano=k, nome=cat[k]["nome"], preco=cat[k]["preco"], preco_vip=cat[k]["preco_vip"],
                            anual_desconto=cat[k]["anual_desconto"], vans=cat[k]["vans"], alunos=cat[k]["alunos"],
                            destaque=cat[k]["destaque"], cobranca_auto=bool(cat[k].get("cobranca_auto")),
                            itens=" | ".join(cat[k]["itens"])) for k in PLANOS])
    ed = st.data_editor(
        df, hide_index=True, width="stretch", num_rows="fixed", disabled=["plano"],
        column_config={
            "plano": st.column_config.TextColumn("Código"),
            "nome": st.column_config.TextColumn("Nome", required=True),
            "preco": st.column_config.NumberColumn("Preço/mês", min_value=0.0, format="R$ %.2f", required=True),
            "preco_vip": st.column_config.NumberColumn("Preço VIP", min_value=0.0, format="R$ %.2f"),
            "anual_desconto": st.column_config.NumberColumn("Anual: % off", min_value=0.0, max_value=90.0,
                                                            format="%.2f%%"),
            "vans": st.column_config.NumberColumn("Vans", min_value=1, step=1),
            "alunos": st.column_config.NumberColumn("Alunos", min_value=1, step=1),
            "destaque": st.column_config.TextColumn("Selo"),
            "cobranca_auto": st.column_config.CheckboxColumn("Cobra pais pelo Asaas",
                                                             help="Libera a cobrança automática dos pais (Pix/boleto)"),
            "itens": st.column_config.TextColumn("Itens do cartão", width="large"),
        }, key="ed_planos")
    if st.button("Salvar planos", type="primary", icon=":material/save:"):
        linhas = []
        for r in ed.to_dict("records"):
            def n(v, inteiro=False):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return None
                return int(v) if inteiro else round(float(v), 2)
            linhas.append(dict(plano=r["plano"], nome=str(r["nome"]).strip(), preco=n(r["preco"]) or 0.0,
                               preco_vip=n(r["preco_vip"]), anual_desconto=n(r["anual_desconto"]) or 0.0,
                               vans=n(r["vans"], True), alunos=n(r["alunos"], True), destaque=r["destaque"] or "",
                               cobranca_auto=bool(r.get("cobranca_auto")),
                               itens=[i.strip() for i in str(r["itens"] or "").split("|") if i.strip()]))
        repo.salvar_config_planos(linhas)
        st.toast("Planos salvos. Quem já assina continua no preço antigo até você atualizar.")
        st.rerun()

    # ---- quem paga preço antigo
    antigos = repo.precos_antigos(HOJE)
    if not antigos.empty:
        st.markdown(f"**Assinantes no preço antigo ({len(antigos)})** — escolha quem passa para o preço novo:")
        tab = antigos.assign(atualizar=False)[["atualizar", "nome", "plano_nome", "periodo", "vip", "atual", "novo"]]
        ed_a = st.data_editor(
            tab, hide_index=True, width="stretch", disabled=["nome", "plano_nome", "periodo", "vip", "atual", "novo"],
            column_config={"atualizar": st.column_config.CheckboxColumn("Atualizar"),
                           "nome": "Empresa", "plano_nome": "Plano", "periodo": "Período",
                           "vip": st.column_config.CheckboxColumn("VIP"),
                           "atual": st.column_config.NumberColumn("Paga hoje", format="R$ %.2f"),
                           "novo": st.column_config.NumberColumn("Preço novo", format="R$ %.2f")},
            key="ed_antigos")
        a1, a2 = st.columns(2)
        marcados = [antigos.iloc[i]["id"] for i, v in enumerate(ed_a["atualizar"]) if v]
        if a1.button(f"Atualizar selecionados ({len(marcados)})", disabled=not marcados, width="stretch",
                     icon=":material/check_box:"):
            repo.atualizar_para_preco_novo(marcados)
            st.toast(f"{len(marcados)} assinante(s) no preço novo.")
            st.rerun()
        if a2.button(f"Atualizar todos ({len(antigos)})", width="stretch", icon=":material/done_all:"):
            repo.atualizar_para_preco_novo(list(antigos["id"]))
            st.toast("Todos no preço novo.")
            st.rerun()

    # ---- criar plano
    with st.expander("➕ Criar plano novo", icon=":material/add_card:"):
        with st.form("novo_plano", clear_on_submit=True):
            a, b = st.columns(2)
            nome_n = a.text_input("Nome do plano *", placeholder="Ex.: Escolar Plus")
            selo_n = b.text_input("Selo do cartão", placeholder="Ex.: Para 2 vans")
            c1, c2, c3 = st.columns(3)
            preco_n = c1.number_input("Preço/mês *", min_value=0.0, step=1.0, format="%.2f")
            vip_n = c2.number_input("Preço VIP (0 = sem VIP)", min_value=0.0, step=1.0, format="%.2f")
            anual_n = c3.number_input("Anual: % de desconto", min_value=0.0, max_value=90.0, step=1.0, value=16.67)
            d1, d2 = st.columns(2)
            vans_n = d1.number_input("Vans (0 = ilimitado)", min_value=0, step=1, value=1)
            alunos_n = d2.number_input("Alunos (0 = ilimitado)", min_value=0, step=1, value=0)
            itens_n = st.text_area("Itens do cartão (um por linha)", placeholder="2 vans\nAlunos ilimitados")
            auto_n = st.checkbox("Libera a cobrança automática dos pais pelo Asaas")
            if st.form_submit_button("Criar plano", type="primary"):
                import re
                import unicodedata
                cod = unicodedata.normalize("NFKD", nome_n).encode("ascii", "ignore").decode().lower()
                cod = re.sub(r"[^a-z0-9]+", "_", cod).strip("_")[:30]
                if not nome_n.strip() or preco_n <= 0:
                    st.error("Preencha o nome e um preço maior que zero.")
                elif cod in cat:
                    st.error("Já existe um plano com esse nome.")
                else:
                    repo.criar_plano(dict(plano=cod, nome=nome_n.strip(), preco=round(preco_n, 2),
                                          preco_vip=round(vip_n, 2) or None, anual_desconto=round(anual_n, 2),
                                          vans=int(vans_n) or None, alunos=int(alunos_n) or None,
                                          destaque=selo_n.strip(), cobranca_auto=auto_n,
                                          itens=[i.strip() for i in itens_n.splitlines() if i.strip()]))
                    st.toast(f"Plano {nome_n} criado.")
                    st.rerun()

    # ---- excluir plano
    with st.expander("🗑️ Excluir plano", icon=":material/delete:"):
        st.caption("Só dá para excluir um plano sem nenhum gestor ativo nele. As campanhas dele são apagadas e ele "
                   "sai dos cupons.")
        x1, x2 = st.columns([3, 1], vertical_alignment="bottom")
        alvo = x1.selectbox("Plano", PLANOS, format_func=_nome_plano, key="excluir_plano")
        n = len(repo.gestores_no_plano(alvo, HOJE))
        x1.caption(f"{n} gestor(es) ativo(s) no {_nome_plano(alvo)}.")
        if x2.button("Excluir", key="btn_excluir_plano", disabled=n > 0, width="stretch"):
            erro = repo.excluir_plano(alvo, HOJE)
            if erro:
                st.error(erro)
            else:
                st.toast(f"Plano {_nome_plano(alvo)} excluído.")
                st.rerun()

    st.markdown("**Prévia (como o visitante vê, com as promoções de hoje):**")
    _ui.cartoes_planos(precos=_ui.precos_planos(None))

# ================================================================ cupons
with abas[1]:
    cdf = repo.cupons()
    if cdf.empty:
        st.info("Nenhum cupom ainda. Crie o primeiro abaixo.")
    for r in cdf.to_dict("records"):
        v = float(r["valor"])
        desc = (f"{v:g}% off" if r["tipo"] == "pct" else f"{pl.brl(v)} off" if r["tipo"] == "valor"
                else f"{int(v)} dias grátis")
        dur = "" if r["tipo"] == "dias" else (f" por {r['duracao_meses']} mês(es)" if r["duracao_meses"] else " para sempre")
        planos_txt = ", ".join(_nome_plano(k) for k in (r["planos"] or [])) or "todos os planos"
        venc = r["valido_ate"] and r["valido_ate"] < HOJE
        esgot = r["limite_usos"] is not None and r["usos"] >= r["limite_usos"]
        status = ("faltou", "desligado") if not r["ativo"] else ("vencido", "vencido") if venc else \
            ("vence_logo", "esgotado") if esgot else ("pago", "ativo")
        with st.container(border=True, key=f"card_cp_{r['id']}"):
            st.markdown(_ui.sem_formula(f"**{_ui.esc(r['codigo'])}** {_ui.tag(*status)} {_ui.tag('embarcou', desc + dur)}  \n"
                        f"<span class='ve-sub'>{planos_txt} · usado {r['usos']}"
                        f"{'/' + str(r['limite_usos']) if r['limite_usos'] is not None else ''} vez(es)"
                        f"{' · válido até ' + data_br(r['valido_ate']) if r['valido_ate'] else ''}</span>"),
                        unsafe_allow_html=True)
            if r["usos"]:
                with st.expander("Quem usou"):
                    u = repo.cupom_usos(r["id"])
                    st.dataframe(u.rename(columns={"nome": "Empresa", "usado_em": "Quando"}), hide_index=True,
                                 width="stretch")

    st.divider()
    NOVO = "➕ Novo cupom"
    ops = [NOVO] + list(cdf["codigo"]) if not cdf.empty else [NOVO]
    esc_cp = st.selectbox("Criar / editar cupom", ops)
    atual_cp = None if esc_cp == NOVO else cdf[cdf["codigo"] == esc_cp].iloc[0].to_dict()
    g = (atual_cp or {}).get
    with st.form("cupom_form", clear_on_submit=atual_cp is None):
        a, b, cc = st.columns([2, 2, 1])
        codigo = a.text_input("Código *", value=g("codigo") or "", placeholder="VOLTAAULAS")
        tipos = list(pl.TIPOS_CUPOM)
        tipo = b.selectbox("Tipo", tipos, index=tipos.index(g("tipo") or "pct"), format_func=pl.TIPOS_CUPOM.get)
        valor = cc.number_input("Valor *", min_value=0.0, step=1.0, value=float(g("valor") or 10),
                                help="% (ex.: 20), R$ (ex.: 10) ou nº de dias (ex.: 30), conforme o tipo.")
        planos_sel = st.multiselect("Vale para", PLANOS, default=[k for k in (g("planos") or []) if k in cat],
                                    format_func=_nome_plano,
                                    help="Vazio = todos. No cupom de dias grátis, o 1º plano escolhido é o "
                                         "liberado (vazio = o plano da degustação).")
        d1, d2, d3 = st.columns(3)
        duracao = d1.number_input("Desconto por quantos meses", min_value=0, step=1,
                                  value=int(g("duracao_meses") or 0) if atual_cp else 1,
                                  help="0 = para sempre. 1 = só o primeiro mês. (Não se aplica a dias grátis.)")
        tem_validade = d2.checkbox("Tem data limite", value=bool(g("valido_ate")))
        validade = d2.date_input("Usar até", value=g("valido_ate") or HOJE + timedelta(days=30), format="DD/MM/YYYY",
                                 label_visibility="collapsed")
        limite = d3.number_input("Limite de usos", min_value=0, step=1, value=int(g("limite_usos") or 0),
                                 help="0 = sem limite.")
        ativo = st.checkbox("Ativo", value=bool(g("ativo")) if atual_cp else True)
        if st.form_submit_button("Salvar cupom", type="primary"):
            cod = codigo.strip().upper().replace(" ", "")
            if not cod or valor <= 0:
                st.error("Preencha o código e o valor.")
            elif tipo == "pct" and valor >= 100:
                st.error("Desconto em % precisa ser menor que 100. Para liberar de graça, use dias grátis ou o plano Exclusivo.")
            elif atual_cp is None and cod in set(cdf["codigo"] if not cdf.empty else []):
                st.error("Já existe um cupom com esse código.")
            else:
                repo.salvar_cupom(dict(codigo=cod, tipo=tipo, valor=valor, planos=planos_sel or None,
                                       duracao_meses=int(duracao) or None,
                                       valido_ate=validade if tem_validade else None,
                                       limite_usos=int(limite) or None, ativo=ativo),
                                  cupom_id=g("id"))
                st.toast(f"Cupom {cod} salvo.")
                st.rerun()
    if atual_cp is not None:
        k1, k2 = st.columns([3, 1], vertical_alignment="center")
        conf_cp = k1.checkbox(f"Quero excluir o cupom {atual_cp['codigo']} (o histórico de uso some junto)",
                              key=f"conf_cp_{atual_cp['id']}")
        if k2.button("Excluir cupom", disabled=not conf_cp, icon=":material/delete:", width="stretch"):
            repo.excluir_cupom(atual_cp["id"])
            st.toast(f"Cupom {atual_cp['codigo']} excluído.")
            st.rerun()

# ================================================================ campanhas
with abas[2]:
    camps = repo.campanhas()
    if not camps:
        st.info("Nenhuma campanha ainda. Ex.: “Volta às aulas: Pro por R$ 39,90 de 01/01 a 28/02”.")
    for cp in camps:
        no_ar = cp["ativo"] and cp["inicio"] <= HOJE <= cp["fim"]
        status = ("pago", "no ar") if no_ar else ("faltou", "desligada") if not cp["ativo"] else \
            ("aberto", "agendada") if cp["inicio"] > HOJE else ("vencido", "encerrada")
        dur = f" por {cp['duracao_meses']} mês(es)" if cp["duracao_meses"] else " para sempre"
        with st.container(border=True, key=f"card_cm_{cp['id']}"):
            st.markdown(_ui.sem_formula(f"**{_ui.esc(cp['nome'])}** {_ui.tag(*status)}  \n<span class='ve-sub'>"
                        f"{_nome_plano(cp['plano'])} de {pl.brl(cat[cp['plano']]['preco'])} por "
                        f"<b>{pl.brl(cp['preco'])}</b>/mês{dur} · {data_br(cp['inicio'])} a {data_br(cp['fim'])}</span>"),
                        unsafe_allow_html=True)
    st.divider()
    NOVA = "➕ Nova campanha"
    nomes = [f"{c['nome']} ({data_br(c['inicio'])})" for c in camps]
    esc_cm = st.selectbox("Criar / editar campanha", [NOVA] + nomes)
    cm = None if esc_cm == NOVA else camps[nomes.index(esc_cm)]
    g = (cm or {}).get
    with st.form("camp_form", clear_on_submit=cm is None):
        a, b, cc = st.columns([3, 2, 2])
        nome = a.text_input("Nome *", value=g("nome") or "", placeholder="Volta às aulas")
        plano = b.selectbox("Plano", PLANOS, index=PLANOS.index(g("plano")) if g("plano") in cat else 0,
                            format_func=_nome_plano)
        preco = cc.number_input("Preço promocional/mês *", min_value=0.0, step=1.0, format="%.2f",
                                value=float(g("preco") or 39.90))
        d1, d2, d3 = st.columns(3)
        inicio = d1.date_input("Começa", value=g("inicio") or HOJE, format="DD/MM/YYYY")
        fim = d2.date_input("Termina", value=g("fim") or HOJE + timedelta(days=30), format="DD/MM/YYYY")
        duracao = d3.number_input("Preço vale por quantos meses", min_value=0, step=1,
                                  value=int(g("duracao_meses") or 0) if cm else 3,
                                  help="Para quem assinar durante a campanha. 0 = para sempre.")
        ativo = st.checkbox("Ativa", value=bool(g("ativo")) if cm else True)
        if st.form_submit_button("Salvar campanha", type="primary"):
            if not nome.strip():
                st.error("Dê um nome para a campanha.")
            elif fim < inicio:
                st.error("A data de término é antes do começo.")
            elif preco >= cat[plano]["preco"]:
                st.error(f"O preço promocional precisa ser menor que o normal ({pl.brl(cat[plano]['preco'])}).")
            else:
                repo.salvar_campanha(dict(nome=nome.strip(), plano=plano, preco=preco, inicio=inicio, fim=fim,
                                          duracao_meses=int(duracao) or None, ativo=ativo), camp_id=g("id"))
                st.toast("Campanha salva.")
                st.rerun()
    if cm is not None:
        k1, k2 = st.columns([3, 1], vertical_alignment="center")
        conf_cm = k1.checkbox(f"Quero excluir a campanha {cm['nome']}", key=f"conf_cm_{cm['id']}")
        if k2.button("Excluir campanha", disabled=not conf_cm, icon=":material/delete:", width="stretch"):
            repo.excluir_campanha(cm["id"])
            st.toast("Campanha excluída.")
            st.rerun()

# ================================================================ Passageiro VIP
with abas[3]:
    cfg = pl.config("vip")
    usadas = repo.vip_usadas()
    livres = pl.vip_livres(cfg, usadas, HOJE)
    _ui.kpis([("Vagas VIP", str(int(cfg.get("vagas") or 0))), ("Já são VIP", str(usadas)),
              ("Restam", str(livres), "aberto" if livres else "fechado")])
    st.markdown("Quem assina enquanto há vagas **trava o preço VIP para sempre** (o preço VIP de cada plano fica na "
                "aba *Planos e preços*).")
    with st.form("vip_form"):
        a, b = st.columns(2)
        ativo = a.checkbox("VIP aberto", value=bool(cfg.get("ativo")))
        vagas = b.number_input("Número de vagas", min_value=0, step=1, value=int(cfg.get("vagas") or 0))
        tem_ate = a.checkbox("Fechar numa data", value=bool(cfg.get("ate")))
        ate_txt = cfg.get("ate")
        ate = b.date_input("Fecha em", value=pd.to_datetime(ate_txt).date() if ate_txt else HOJE + timedelta(days=60),
                           format="DD/MM/YYYY")
        if st.form_submit_button("Salvar VIP", type="primary"):
            repo.salvar_config("vip", dict(ativo=ativo, vagas=int(vagas), ate=ate.isoformat() if tem_ate else None))
            st.toast("Passageiro VIP salvo.")
            st.rerun()
    v = repo.vips()
    if not v.empty:
        st.markdown("**Passageiros VIP**")
        st.dataframe(v.rename(columns={"nome": "Empresa", "plano": "Plano", "preco_mensal": "Preço/mês"}),
                     hide_index=True, width="stretch")

# ================================================================ degustação de conta nova
with abas[4]:
    cfg = pl.config("degustacao")
    st.markdown("Não existe plano grátis: **toda conta nova ganha uma degustação** e, quando ela acaba, o acesso "
                "fica bloqueado até assinar (nada é apagado). Quem chega por indicação ganha a degustação da aba "
                "*Indicação*.")
    with st.form("deg_form"):
        a, b, cc = st.columns(3)
        ativo_d = a.checkbox("Degustação ligada", value=bool(cfg.get("ativo")),
                             help="Desligada: a conta nova já nasce bloqueada até assinar.")
        plano_dd = b.selectbox("Plano", PLANOS, index=PLANOS.index(cfg["plano"]) if cfg.get("plano") in cat else 0,
                               format_func=_nome_plano)
        dias_dd = cc.number_input("Dias", min_value=1, step=1, value=int(cfg.get("dias") or 15))
        if st.form_submit_button("Salvar degustação", type="primary"):
            repo.salvar_config("degustacao", dict(ativo=ativo_d, plano=plano_dd, dias=int(dias_dd)))
            st.toast("Degustação salva.")
            st.rerun()

# ================================================================ indicação
with abas[5]:
    cfg = pl.config("indicacao")
    st.markdown(f"Cada gestor tem um código. Quem é indicado ganha **{cfg['dias_degustacao']} dias de "
                f"{_nome_plano(cfg['plano_degustacao'])}**; quem indica ganha **{cfg['premio_meses']} mês(es) grátis "
                f"a cada {cfg['meta']} indicados que pagarem o 1º mês** (acumula).")
    with st.form("ind_form"):
        a, b = st.columns(2)
        ativo = a.checkbox("Indicação ligada", value=bool(cfg.get("ativo")))
        meta = a.number_input("A cada quantos indicados pagantes", min_value=1, step=1, value=int(cfg["meta"]))
        premio = b.number_input("Meses grátis de prêmio", min_value=0, step=1, value=int(cfg["premio_meses"]))
        plano_d = a.selectbox("Degustação do indicado: plano", PLANOS,
                              index=PLANOS.index(cfg["plano_degustacao"]) if cfg.get("plano_degustacao") in cat else 0,
                              format_func=_nome_plano)
        dias = b.number_input("Degustação do indicado: dias", min_value=0, step=1, value=int(cfg["dias_degustacao"]))
        if st.form_submit_button("Salvar indicação", type="primary"):
            repo.salvar_config("indicacao", dict(ativo=ativo, meta=int(meta), premio_meses=int(premio),
                                                 plano_degustacao=plano_d, dias_degustacao=int(dias)))
            st.toast("Indicação salva.")
            st.rerun()
    rk = repo.ranking_indicacoes()
    st.markdown("**Ranking de indicações**")
    if rk.empty:
        st.caption("Ninguém indicou ainda.")
    else:
        st.dataframe(rk.rename(columns={"nome": "Empresa", "codigo_indicacao": "Código", "indicados": "Indicados",
                                        "indicacoes_pagas": "Pagantes", "meses_gratis": "Meses grátis guardados"})
                     [["Empresa", "Código", "Indicados", "Pagantes", "Meses grátis guardados"]],
                     hide_index=True, width="stretch")

# ================================================================ divulgadores (Exclusivo): comissão e textos
with abas[6]:
    from core import comissao
    cfg = pl.config("comissao")
    st.markdown("Os parceiros **Exclusivos** divulgam o app. Ao chegar à meta de indicados **pagando ao mesmo tempo**, "
                "destravam a comissão (fica destravada) e passam a receber a % sobre o que os indicados **ativos** "
                "pagam no mês, até a data final. Exclusivo **não** ganha os meses grátis da indicação. "
                "Você paga por Pix e marca como pago aqui.")
    with st.form("com_form"):
        a, b, cc, d = st.columns(4)
        ativo_c = a.checkbox("Comissão ligada", value=bool(cfg.get("ativo")))
        meta_c = b.number_input("Meta (indicados pagando)", min_value=1, step=1, value=int(cfg.get("meta") or 100))
        pct_c = cc.number_input("Comissão (%)", min_value=0.0, max_value=100.0, step=1.0,
                                value=float(cfg.get("pct") or 10))
        ate_c = d.date_input("Vale até", value=pd.Timestamp(cfg.get("ate") or HOJE.replace(year=HOJE.year + 1)).date(),
                             format="DD/MM/YYYY")
        if st.form_submit_button("Salvar comissão", type="primary"):
            repo.salvar_config("comissao", dict(ativo=ativo_c, meta=int(meta_c), pct=float(pct_c),
                                                ate=ate_c.isoformat()))
            st.toast("Comissão salva.")
            st.rerun()

    st.markdown("**Divulgadores**")
    dv = comissao.divulgadores(HOJE)
    if dv.empty:
        st.caption("Nenhum Exclusivo ainda. Para tornar alguém divulgador, dê o plano **Exclusivo** em *Assinantes*.")
    else:
        st.dataframe(pd.DataFrame({
            "Divulgador": dv["nome"], "Código": dv["codigo_indicacao"], "Indicados": dv["indicados"],
            "Pagando agora": dv["ativos"],
            "Destravou": [data_br(x) if x else "—" for x in dv["comissao_desde"]],
            "Comissão do mês": [pl.brl(v) for v in dv["mes"]],
            "A pagar": [pl.brl(v) for v in dv["a_pagar"]], "Já pago": [pl.brl(float(v)) for v in dv["ja_pago"]],
            "Chave Pix": dv["chave_pix"].fillna("—")}), hide_index=True, width="stretch")
        for r in dv[dv["a_pagar"] > 0].itertuples():
            pend = comissao.pendentes(r.id)
            with st.container(border=True, key=f"card_pagar_{r.id}"):
                st.markdown(f"**{_ui.esc(r.nome)}** — a pagar **{pl.brl(r.a_pagar)}** · Pix: "
                            f"`{r.chave_pix or 'sem chave cadastrada'}`")
                meses = st.multiselect("Meses", list(pend["competencia"]), default=list(pend["competencia"]),
                                       format_func=lambda m, p=pend: f"{m:%m/%Y} — " + pl.brl(
                                           float(p.loc[p["competencia"] == m, "valor"].iloc[0])),
                                       key=f"meses_{r.id}")
                st.caption("O mês atual ainda pode mudar até o fim do mês (se entrar ou sair indicado). "
                           "Marcando como pago, ele congela.")
                if st.button("Marcar como pago (Pix feito)", key=f"pago_{r.id}", type="primary",
                             icon=":material/paid:", disabled=not meses):
                    n = comissao.marcar_pago(r.id, meses, HOJE)
                    st.toast(f"{n} mês(es) marcado(s) como pago(s).")
                    st.rerun()

    st.divider()
    st.markdown("**Textos prontos do Canal do divulgador**")
    st.caption("Marcadores que viram o valor de cada divulgador: **{link}** (link de indicação), **{codigo}**, "
               "**{vagas}** (vagas VIP restantes, ao vivo), **{vip_basico}**, **{vip_pro}** (preços VIP), "
               "**{dias}** (dias grátis de quem é indicado), **{nome}** (empresa do divulgador).")
    tx = pd.DataFrame((pl.config("divulgacao") or {}).get("textos") or [], columns=["titulo", "texto"])
    ed_tx = st.data_editor(tx, hide_index=True, width="stretch", num_rows="dynamic", key="ed_textos_div",
                           column_config={"titulo": st.column_config.TextColumn("Título", required=True),
                                          "texto": st.column_config.TextColumn("Texto", required=True,
                                                                               width="large")})
    if st.button("Salvar textos", icon=":material/save:"):
        lin = [dict(titulo=str(r["titulo"]).strip(), texto=str(r["texto"]).strip()) for _, r in ed_tx.iterrows()
               if pd.notna(r["titulo"]) and pd.notna(r["texto"]) and str(r["texto"]).strip()]
        repo.salvar_config("divulgacao", dict(textos=lin))
        st.toast(f"{len(lin)} texto(s) salvo(s).")
        st.rerun()

# ================================================================ laboratório
with abas[7]:
    st.markdown("Recurso **em teste** aparece só para os **Exclusivos** (e para você). Quando estiver bom, libere "
                "para **todos** os planos. Os outros assinantes veem um aviso de \"chega em breve\".")
    lab = dict(pl.config("laboratorio") or {})
    with st.form("lab_form"):
        novo = {}
        for k, nome in pl.RECURSOS.items():
            novo[k] = st.radio(nome, ["todos", "exclusivo"], horizontal=True, key=f"lab_{k}",
                               index=1 if lab.get(k) == "exclusivo" else 0,
                               format_func={"todos": "Liberado para todos", "exclusivo": "Só Exclusivo (teste)"}.get)
        if st.form_submit_button("Salvar laboratório", type="primary"):
            repo.salvar_config("laboratorio", novo)
            st.toast("Laboratório salvo.")
            st.rerun()
