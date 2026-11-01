"""Administração → Promoções: preços dos planos, cupons, campanhas, Passageiro VIP e indicação. Tudo ajustável."""
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
abas = st.tabs(["Planos e preços", "Cupons", "Campanhas", "Passageiro VIP", "Indicação"])


def _nome_plano(k):
    return cat[k]["nome"]


# ================================================================ planos e preços
with abas[0]:
    st.markdown("Edite direto na tabela e salve. Deixe **Vans/Alunos** vazio para ilimitado e **Preço VIP** vazio "
                "para o plano não ter VIP. Os itens do cartão vão separados por **|**.")
    df = pd.DataFrame([dict(plano=k, nome=cat[k]["nome"], preco=cat[k]["preco"], preco_vip=cat[k]["preco_vip"],
                            anual_desconto=cat[k]["anual_desconto"], vans=cat[k]["vans"], alunos=cat[k]["alunos"],
                            destaque=cat[k]["destaque"], itens=" | ".join(cat[k]["itens"])) for k in pl.ORDEM])
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
                               itens=[i.strip() for i in str(r["itens"] or "").split("|") if i.strip()]))
        repo.salvar_config_planos(linhas)
        st.toast("Planos salvos.")
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
        planos_sel = st.multiselect("Vale para", [k for k in pl.ORDEM if k != "gratis"], default=g("planos") or [],
                                    format_func=_nome_plano,
                                    help="Vazio = todos. No cupom de dias grátis, o 1º plano escolhido é o "
                                         "liberado (vazio = Pro).")
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
                st.error("Desconto em % precisa ser menor que 100. Para liberar de graça, use dias grátis ou cortesia.")
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
        pagos = [k for k in pl.ORDEM if k != "gratis"]
        plano = b.selectbox("Plano", pagos, index=pagos.index(g("plano") or "pro"), format_func=_nome_plano)
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

# ================================================================ indicação
with abas[4]:
    cfg = pl.config("indicacao")
    st.markdown(f"Cada gestor tem um código. Quem é indicado ganha **{cfg['dias_degustacao']} dias de "
                f"{_nome_plano(cfg['plano_degustacao'])}**; quem indica ganha **{cfg['premio_meses']} mês(es) grátis "
                f"a cada {cfg['meta']} indicados que pagarem o 1º mês** (acumula).")
    with st.form("ind_form"):
        a, b = st.columns(2)
        ativo = a.checkbox("Indicação ligada", value=bool(cfg.get("ativo")))
        meta = a.number_input("A cada quantos indicados pagantes", min_value=1, step=1, value=int(cfg["meta"]))
        premio = b.number_input("Meses grátis de prêmio", min_value=0, step=1, value=int(cfg["premio_meses"]))
        pagos = [k for k in pl.ORDEM if k != "gratis"]
        plano_d = a.selectbox("Degustação do indicado: plano", pagos,
                              index=pagos.index(cfg.get("plano_degustacao") or "pro"), format_func=_nome_plano)
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
