"""Alunos (passageiros) e responsáveis."""
from datetime import date

import pandas as pd
import streamlit as st

from core import repo
from core.fmt import TURNOS, brl, data_br, hoje, idade, link_email, link_whats, mes_label
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
st.title("Alunos")
if not st.session_state.get("al_modo"):
    _ui.guia(c, "telas/alunos.py")

escolas = repo.escolas(cid)
vans = repo.vans(cid)
todos = repo.passageiros(cid, so_ativos=False)
ativos = todos[todos["ativo"]] if not todos.empty else todos
ss = st.session_state
PARENTESCOS = ["Mãe", "Pai", "Avó", "Avô", "Tia", "Tio", "Outro"]
ETAPAS = ["Aluno", "Responsável", "Escola e van", "Pagamento"]


def _d(v):
    return None if v is None or (not isinstance(v, (str, date)) and pd.isna(v)) else v


def _ir(modo=None, pid=None, sec=None):
    ss["al_modo"], ss["al_pid"], ss["al_sec"] = modo, pid, sec
    st.rerun()


# opções de escola e van (usadas no cadastro e na ficha)
esc_ids = [None] + [str(x) for x in escolas["id"]] if not escolas.empty else [None]
esc_nomes = {None: "— escolher —"} | ({str(r.id): r.nome for r in escolas.itertuples()} if not escolas.empty else {})
van_ids = [None] + [str(x) for x in vans["id"]] if not vans.empty else [None]
van_nomes_d = {None: "— sem van —"} | ({str(r.id): f"{r.nome} ({r.alunos}/{r.capacidade})"
                                       for r in vans.itertuples()} if not vans.empty else {})


def _nova_escola(chave: str):
    """'+ Nova escola' sem sair do cadastro: um campinho aparece no lugar, cria e já deixa escolhida."""
    k = f"nesc_on_{chave}"
    if not ss.get(k):
        if st.button("Nova escola", icon=":material/add:", type="tertiary", key=f"nesc_b_{chave}"):
            ss[k] = True
            st.rerun()
        return None
    with st.form(f"nesc_{chave}"):
        n = st.text_input("Nome da nova escola *")
        a, b = st.columns(2)
        criar = a.form_submit_button("Criar escola", type="primary", width="stretch")
        cancelar = b.form_submit_button("Cancelar", width="stretch")
    if cancelar:
        ss[k] = False
        st.rerun()
    if criar:
        if not n.strip():
            st.error("Digite o nome da escola.")
            return None
        repo.salvar_escola(cid, dict(nome=n.strip(), endereco=None, telefone=None, entrada_manha=None,
                                     saida_manha=None, entrada_tarde=None, saida_tarde=None, ativo=True))
        r = repo.db.ao_vivo("select id from escolas where condutor_id = :cid and nome = :n "
                            "order by criado_em desc limit 1", cid=cid, n=n.strip())
        ss[k] = False
        st.toast(f"Escola {n.strip()} criada. ✅")
        return str(r.iloc[0]["id"]) if len(r) else None
    return None


def _campos_escola(g, chave):
    """Escola, série, turno, van, ida/volta — a mesma tela no cadastro novo e na ficha."""
    e_at = str(g("escola_id")) if g("escola_id") and str(g("escola_id")) in esc_ids else None
    v_at = str(g("van_id")) if g("van_id") and str(g("van_id")) in van_ids else (
        van_ids[1] if len(van_ids) == 2 and g("van_id") is None else None)
    escola_id = st.selectbox("Escola", esc_ids, index=esc_ids.index(e_at), format_func=esc_nomes.get)
    a1, a2 = st.columns(2)
    serie = a1.text_input("Série / turma", value=g("serie") or "")
    turnos = list(TURNOS)
    turno = a2.selectbox("Turno", turnos, index=turnos.index(g("turno")) if g("turno") in turnos else 0,
                         format_func=TURNOS.get)
    van_id = st.selectbox("Van", van_ids, index=van_ids.index(v_at), format_func=van_nomes_d.get)
    t1, t2 = st.columns(2)
    ida = t1.checkbox("Faz a ida", value=bool(g("faz_ida")) if g("faz_ida") is not None else True)
    volta = t2.checkbox("Faz a volta", value=bool(g("faz_volta")) if g("faz_volta") is not None else True)
    return dict(escola_id=escola_id, serie=serie or None, turno=turno, van_id=van_id, faz_ida=ida, faz_volta=volta)


def _rodape(chave, voltar=True, seguir="Continuar", depois=False):
    """Voltar | Continuar (dentro do form) + 'Salvar e completar depois'. Devolve qual foi tocado."""
    with st.container(key=f"wzpe_{chave}"):
        a, b = st.columns(2) if voltar else (None, st.container())
        v = a.form_submit_button("Voltar", icon=":material/arrow_back:", width="stretch") if voltar else False
        s_ = b.form_submit_button(seguir, type="primary", width="stretch",
                                  icon=":material/arrow_forward:" if seguir == "Continuar" else ":material/check:")
    d = st.form_submit_button("Salvar e completar depois", type="tertiary", width="stretch") if depois else False
    return "voltar" if v else "seguir" if s_ else "depois" if d else None


def _salvar_rasc(r: dict):
    nome = (r.get("nome") or "").strip()
    if not _ui.checar_limite(c, "alunos"):
        st.stop()
    dados = dict(nome=nome, data_nasc=r.get("data_nasc"), endereco=r.get("endereco"), bairro=r.get("bairro"),
                 referencia=r.get("referencia"), observacoes=r.get("observacoes"), escola_id=r.get("escola_id"),
                 serie=r.get("serie"), turno=r.get("turno") or "manha",
                 van_id=r.get("van_id", van_ids[1] if len(van_ids) == 2 else None),
                 faz_ida=r.get("faz_ida", True), faz_volta=r.get("faz_volta", True),
                 mensalidade=r.get("mensalidade") or 0, dia_vencimento=r.get("dia_vencimento") or None,
                 inicio=r.get("inicio") or hoje(), fim=r.get("fim"), ativo=True)
    pid = repo.salvar_passageiro(cid, dados)
    if r.get("resp_id"):
        rr = repo.responsaveis(cid)
        rr = rr[rr["id"].astype(str) == r["resp_id"]]
        if len(rr):
            x = rr.iloc[0]
            repo.vincular_responsavel(cid, pid, dict(nome=x["nome"], parentesco=x["parentesco"],
                                                     telefone=x["telefone"], email=x["email"]), rid=r["resp_id"])
    elif (r.get("resp_nome") or "").strip() or r.get("resp_tel") or r.get("resp_email"):
        repo.vincular_responsavel(cid, pid, dict(
            nome=(r.get("resp_nome") or "").strip() or f"Responsável de {nome.split()[0]}",
            parentesco=r.get("resp_par"), telefone=r.get("resp_tel") or None, email=r.get("resp_email") or None),
            financeiro=True)
    ss.pop("al_rasc", None)
    ss["al_etapa"] = 0
    st.toast(f"{nome} cadastrado(a). ✅")
    _ir("ficha", pid)


# ------------------------------------------------------------------ cadastro novo, por etapas
def _cadastro_novo():
    r = ss.setdefault("al_rasc", {})
    et = ss.setdefault("al_etapa", 0)
    g = r.get
    if st.button("Cancelar", icon=":material/close:", type="tertiary", key="wz_cancelar"):
        ss.pop("al_rasc", None)
        ss["al_etapa"] = 0
        _ir()
    _ui.etapas(ETAPAS, et)

    if et == 0:
        with st.form("wz0"):
            nome = st.text_input("Nome do aluno *", value=g("nome") or "")
            end = st.text_input("Endereço de embarque", value=g("endereco") or "", placeholder="Rua, número, cidade")
            b1, b2 = st.columns(2)
            bairro = b1.text_input("Bairro", value=g("bairro") or "")
            nasc = b2.date_input("Nascimento", value=g("data_nasc"), min_value=date(2000, 1, 1), max_value=hoje(),
                                 format="DD/MM/YYYY")
            ref = g("referencia")
            acao = _rodape("e0", voltar=False, depois=True)
        if acao:
            if not nome.strip():
                st.error("Digite o nome do aluno.")
                st.stop()
            r.update(nome=nome.strip(), data_nasc=nasc, endereco=end or None, bairro=bairro or None,
                     referencia=ref or None)
            if acao == "depois":
                _salvar_rasc(r)
            ss["al_etapa"] = 1
            st.rerun()

    elif et == 1:
        outros = repo.responsaveis(cid)
        ops = [None] + ([str(x) for x in outros["id"]] if not outros.empty else [])
        nomes_o = {None: "Não — é um responsável novo"} | (
            {str(x.id): f"{x.nome} ({x.telefone or 'sem WhatsApp'})" for x in outros.itertuples()} if not outros.empty else {})
        with st.form("wz1"):
            ja = None
            if len(ops) > 1:
                ja = st.selectbox("Irmão de alguém que já está na van?", ops,
                                  index=ops.index(g("resp_id")) if g("resp_id") in ops else 0, format_func=nomes_o.get)
            rn = st.text_input("Nome do responsável", value=g("resp_nome") or "",
                               placeholder=f"Responsável de {(g('nome') or 'aluno').split()[0]}")
            p1, p2 = st.columns(2)
            rp = p1.selectbox("Parentesco", PARENTESCOS,
                              index=PARENTESCOS.index(g("resp_par")) if g("resp_par") in PARENTESCOS else 0)
            rt = p2.text_input("WhatsApp", value=g("resp_tel") or "", placeholder="(11) 99999-9999")
            re_ = st.text_input("E-mail do Google", value=g("resp_email") or "", placeholder="nome@gmail.com",
                                help="Com o e-mail, o responsável entra no app: vê o embarque, avisa faltas e assina "
                                     "o contrato.")
            acao = _rodape("e1", depois=True)
        if acao:
            r.update(resp_id=ja, resp_nome=rn.strip() or None, resp_par=rp, resp_tel=rt or None,
                     resp_email=(re_ or "").strip() or None)
            if acao == "depois":
                _salvar_rasc(r)
            ss["al_etapa"] = 0 if acao == "voltar" else 2
            st.rerun()

    elif et == 2:
        nova = _nova_escola("wz")
        if nova:
            r["escola_id"] = nova
            st.rerun()
        with st.form("wz2"):
            campos = _campos_escola(g, "wz")
            acao = _rodape("e2", depois=True)
        if acao:
            r.update(campos)
            if acao == "depois":
                _salvar_rasc(r)
            ss["al_etapa"] = 1 if acao == "voltar" else 3
            st.rerun()

    else:
        with st.form("wz3"):
            m1, m2 = st.columns(2)
            mens = m1.number_input("Mensalidade (R$)", min_value=0.0, step=10.0, value=float(g("mensalidade") or 0))
            dia = m2.number_input("Vence dia", min_value=1, max_value=28,
                                  value=int(g("dia_vencimento") or c.get("dia_vencimento") or 10))
            d1, d2 = st.columns(2)
            ini = d1.date_input("Início", value=g("inicio") or hoje(), format="DD/MM/YYYY")
            fim = d2.date_input("Fim (opcional)", value=g("fim"), format="DD/MM/YYYY")
            obs = st.text_area("Observações", value=g("observacoes") or "", height=80,
                               placeholder="Alergias, cuidados, quem pode buscar…")
            acao = _rodape("e3", seguir="Cadastrar aluno")
        if acao:
            r.update(mensalidade=mens, dia_vencimento=int(dia), inicio=ini, fim=fim, observacoes=obs or None)
            if acao == "voltar":
                ss["al_etapa"] = 2
                st.rerun()
            if fim and fim < ini:
                st.error("O fim é antes do início.")
                st.stop()
            _salvar_rasc(r)


# ------------------------------------------------------------------ ficha do aluno
def _ficha(pid):
    linha = todos[todos["id"].astype(str) == str(pid)]
    if linha.empty:
        _ir()
    p = linha.iloc[0].to_dict()
    g = p.get
    sec = ss.get("al_sec")
    primeiro = p["nome"].split()[0]

    def _salvar(campos: dict, msg="Salvo. ✅"):
        base = {k: _d(g(k)) for k in repo._CAMPOS_P}
        base.update(campos)
        if base.get("ativo") and not bool(g("ativo")) and not _ui.checar_limite(c, "alunos"):
            st.stop()
        repo.salvar_passageiro(cid, base, pid=str(pid))
        st.toast(msg)
        _ir("ficha", pid)

    if sec:
        if st.button(f"Ficha de {primeiro}", icon=":material/arrow_back:", type="tertiary", key="fi_voltar"):
            _ir("ficha", pid)
    else:
        if st.button("Todos os alunos", icon=":material/arrow_back:", type="tertiary", key="fi_lista"):
            _ir()
    iniciais = "".join(x[0] for x in p["nome"].split()[:2]).upper()
    st.markdown(f"<div class='ve-ficha-topo'><div class='av'>{_ui.esc(iniciais)}</div><div><h3>{_ui.esc(p['nome'])}</h3>"
                f"<span class='ve-sub'>{_ui.esc(p.get('van') or 'sem van')} · {TURNOS.get(g('turno'), '')}"
                f"{'' if g('ativo') else ' · 🔴 inativo'}</span></div></div>", unsafe_allow_html=True)
    resp = repo.responsaveis_do(cid, str(pid))
    h = hoje()

    if not sec:
        idd = idade(g("data_nasc")) if _d(g("data_nasc")) else None
        nresp = len(resp)
        mens = repo.mensalidades_filhos([str(pid)], h)
        abertas = mens[mens["situacao"] != "pago"] if not mens.empty else mens
        venc = int((abertas["situacao"] == "vencido").sum()) if not abertas.empty else 0
        cts = repo.contratos_empresa(cid, h.year)
        ctr = cts[cts["passageiro_id"].astype(str) == str(pid)] if not cts.empty else cts
        st_ct = {"ok": "Assinado ✅", "assinar": "Falta você assinar", "pendente": "Com o responsável",
                 "preparar": "Ainda não preparado"}.get(ctr.iloc[0]["situacao"] if len(ctr) else "", "—")
        itens = [
            ("dados", "Dados do aluno", " · ".join(x for x in [f"{idd} anos" if idd is not None else None,
                                                               g("endereco")] if x) or "Nascimento, endereço",
             ":material/person:"),
            ("resp", f"Responsáveis ({nresp})", ", ".join(resp["nome"]) if nresp else "Nenhum — toque para adicionar",
             ":material/family_restroom:"),
            ("escola", "Escola e van", " · ".join(x for x in [p.get("escola"), p.get("van")] if x) or "Escolher",
             ":material/school:"),
            ("pag", "Pagamento", f"{brl(g('mensalidade'))} · vence dia {g('dia_vencimento') or c.get('dia_vencimento')}",
             ":material/payments:"),
            ("mens", "Mensalidades", ((f"{venc} vencida(s) · " if venc else "") + f"{len(abertas)} em aberto")
             if len(abertas) else "Tudo pago ✅",
             ":material/receipt_long:"),
            ("ct", "Contrato", st_ct, ":material/description:"),
        ]
        for k, rot, sub, ic in itens:
            if _ui.linha_ficha(rot, sub, f"{k}_{pid}", ic):
                _ir("ficha", pid, k)
        return

    if sec == "dados":
        with st.form("fi_dados"):
            nome = st.text_input("Nome do aluno *", value=g("nome") or "")
            nasc = st.date_input("Nascimento", value=_d(g("data_nasc")), min_value=date(2000, 1, 1), max_value=h,
                                 format="DD/MM/YYYY")
            end = st.text_input("Endereço de embarque", value=g("endereco") or "")
            b1, b2 = st.columns(2)
            bairro = b1.text_input("Bairro", value=g("bairro") or "")
            ref = b2.text_input("Referência", value=g("referencia") or "")
            obs = st.text_area("Observações", value=g("observacoes") or "", height=80)
            if st.form_submit_button("Salvar", type="primary", width="stretch"):
                if not nome.strip():
                    st.error("Digite o nome.")
                    st.stop()
                _salvar(dict(nome=nome.strip(), data_nasc=nasc, endereco=end or None, bairro=bairro or None,
                             referencia=ref or None, observacoes=obs or None))

    elif sec == "escola":
        nova = _nova_escola(f"fi{pid}")
        if nova:
            _salvar(dict(escola_id=nova), "Escola criada e escolhida. ✅")
        with st.form("fi_escola"):
            campos = _campos_escola(g, "fi")
            if st.form_submit_button("Salvar", type="primary", width="stretch"):
                van_id = campos["van_id"]
                if van_id and str(g("van_id")) != van_id:
                    vv = vans.set_index(vans["id"].astype(str)).loc[van_id]
                    if int(vv["alunos"]) + 1 > int(vv["capacidade"]):
                        st.toast(f"Atenção: {vv['nome']} passou dos {vv['capacidade']} lugares.", icon="⚠️")
                _salvar(campos)

    elif sec == "pag":
        with st.form("fi_pag"):
            m1, m2 = st.columns(2)
            mens = m1.number_input("Mensalidade (R$)", min_value=0.0, step=10.0, value=float(g("mensalidade") or 0))
            dia = m2.number_input("Vence dia", min_value=0, max_value=28, value=int(g("dia_vencimento") or 0),
                                  help=f"0 = o padrão da empresa (dia {c['dia_vencimento']})")
            d1, d2 = st.columns(2)
            ini = d1.date_input("Início", value=_d(g("inicio")) or h, format="DD/MM/YYYY")
            fim = d2.date_input("Fim (opcional)", value=_d(g("fim")), format="DD/MM/YYYY")
            ativo = st.toggle("Aluno ativo", value=bool(g("ativo")),
                              help="Desligado: sai da rota e das cobranças (o histórico fica).")
            if st.form_submit_button("Salvar", type="primary", width="stretch"):
                if fim and fim < ini:
                    st.error("O fim é antes do início.")
                    st.stop()
                _salvar(dict(mensalidade=mens, dia_vencimento=int(dia) or None, inicio=ini, fim=fim, ativo=ativo))

    elif sec == "resp":
        ac = repo.acessos(list(resp["email"].dropna())) if not resp.empty else {}
        for r in resp.itertuples():
            with st.container(border=True, key=f"card_resp_{r.id}"):
                x1, x2 = st.columns([4, 1], vertical_alignment="center")
                x1.markdown(f"**{_ui.esc(r.nome)}** {('· ' + _ui.esc(r.parentesco)) if r.parentesco else ''}"
                            f"{' · 💰' if r.financeiro else ''} {_ui.selo_acesso(r.email, ac) if r.email else ''}  \n"
                            f"<span class='ve-sub'>📞 {_ui.esc(r.telefone or '—')} · ✉️ "
                            f"{_ui.esc(r.email or 'sem e-mail')}</span>", unsafe_allow_html=True)
                if x2.button("", key=f"rm_{r.id}", icon=":material/delete:", type="tertiary", help="Remover"):
                    repo.desvincular_responsavel(cid, str(pid), r.id)
                    _ir("ficha", pid, "resp")
                if r.email:
                    msg = (f"Olá, {r.nome.split(' ')[0]}! {c['nome']} cadastrou você como responsável de "
                           f"{p['nome']} no app Turminha a Bordo. Acesse {_ui.APP_URL} e clique em \"Entrar com "
                           f"Google\" usando o e-mail {r.email}. Lá você vê a carteirinha, acompanha o embarque, avisa "
                           "faltas, vê as mensalidades e assina o contrato. 🚐")
                    k1, k2 = st.container(key=f"linha_conv_{r.id}").columns(2)
                    lk = link_whats(r.telefone, msg)
                    if lk:
                        k1.link_button("Convidar no WhatsApp", lk, icon=":material/send:", key=f"conv_{r.id}",
                                       width="stretch")
                    k2.link_button("Convidar por e-mail", link_email(r.email, "Convite — Turminha a Bordo", msg),
                                   icon=":material/mail:", key=f"convm_{r.id}", width="stretch")
        outros = repo.responsaveis(cid)
        outros = outros[~outros["id"].isin(resp["id"])] if not resp.empty and not outros.empty else outros
        with st.expander("Adicionar responsável", icon=":material/person_add:", expanded=resp.empty):
            if not outros.empty:
                ja = st.selectbox("Irmão de alguém que já está na van?", [None] + [str(x) for x in outros["id"]],
                                  format_func=lambda i: "Não — é um responsável novo" if i is None else
                                  outros.set_index(outros["id"].astype(str)).loc[i, "nome"])
                if ja and st.button("Vincular este responsável", type="primary"):
                    x = outros.set_index(outros["id"].astype(str)).loc[ja]
                    repo.vincular_responsavel(cid, str(pid), dict(nome=x["nome"], parentesco=x["parentesco"],
                                                                  telefone=x["telefone"], email=x["email"]), rid=ja)
                    _ir("ficha", pid, "resp")
            with st.form("resp", clear_on_submit=True):
                rn = st.text_input("Nome *")
                rp = st.selectbox("Parentesco", PARENTESCOS)
                rt = st.text_input("WhatsApp", placeholder="(11) 99999-9999")
                re_ = st.text_input("E-mail do Google", placeholder="nome@gmail.com")
                rf = st.checkbox("Recebe a cobrança", value=resp.empty)
                if st.form_submit_button("Adicionar", type="primary", width="stretch"):
                    if not rn.strip():
                        st.error("Digite o nome.")
                    else:
                        repo.vincular_responsavel(cid, str(pid), dict(nome=rn.strip(), parentesco=rp,
                                                                      telefone=rt or None, email=re_ or None),
                                                  financeiro=rf)
                        _ir("ficha", pid, "resp")

    elif sec == "mens":
        mens = repo.mensalidades_filhos([str(pid)], h)
        if mens.empty:
            st.info("Nenhuma mensalidade ainda.")
        for r in mens.head(12).itertuples():
            a, b = st.container(key=f"{'lpv' if r.situacao == 'vencido' else 'lp'}_fm{r.id}").columns([3, 2])
            a.markdown(f"**{mes_label(r.competencia, curto=True)}** {_ui.tag(r.situacao, _ui.ROTULO_MENS[r.situacao])}"
                       f"  \n<span class='ve-sub'>vence {data_br(r.vencimento)}</span>", unsafe_allow_html=True)
            b.markdown(f"**{brl(r.valor_pago if r.situacao == 'pago' else r.valor)}**")
        st.page_link("telas/mensalidades.py", label="Receber ou cobrar em Mensalidades", icon=":material/payments:")

    elif sec == "ct":
        st.info("O contrato de cada aluno fica na aba **Contratos**, aqui em cima: lá você prepara, envia para o "
                "responsável assinar e assina também.", icon=":material/description:")


# ------------------------------------------------------------------ lista
def _lista():
    a, b = st.container(key="linha_al_topo").columns([1, 1])
    if a.button("Novo aluno", icon=":material/person_add:", type="primary", width="stretch", key="novo_aluno_btn"):
        ss["al_rasc"], ss["al_etapa"] = {}, 0
        _ir("novo")
    with b.popover("Importar planilha", icon=":material/upload_file:", width="stretch"):
        _ui.importar_planilha(c, str(vans.iloc[0]["id"]) if not vans.empty else None,
                              int(c.get("dia_vencimento") or 10), chave="imp_c", caixa=False)
    if todos.empty:
        st.info("Nenhum aluno ainda. Toque em **Novo aluno** ou importe a sua planilha.", icon=":material/groups:")
        return
    nao_entraram = repo.responsaveis_sem_acesso(cid)
    if not nao_entraram.empty:
        with st.expander(f"Ainda não entraram no app ({len(nao_entraram)})", icon=":material/person_alert:"):
            for r in nao_entraram.itertuples():
                msg = (f"Olá, {r.nome.split(' ')[0]}! Lembrete do app Turminha a Bordo, da van de {r.alunos}. "
                       f"Acesse {_ui.APP_URL} e clique em \"Entrar com Google\" usando o e-mail {r.email}. Lá você "
                       "vê a carteirinha, acompanha o embarque, avisa faltas, vê as mensalidades e assina o "
                       "contrato. 🚐")
                with st.container(border=True, key=f"card_naoentrou_{r.id}"):
                    st.markdown(f"**{_ui.esc(r.nome)}** <span class='ve-sub'>· {_ui.esc(r.alunos)}</span>",
                                unsafe_allow_html=True)
                    k1, k2 = st.container(key=f"linha_reenv_{r.id}").columns(2)
                    lk = link_whats(r.telefone, msg)
                    if lk:
                        k1.link_button("WhatsApp", lk, icon=":material/send:", width="stretch")
                    k2.link_button("E-mail", link_email(r.email, "Convite — Turminha a Bordo", msg),
                                   icon=":material/mail:", width="stretch")
    f1, f2 = st.container(key="linha_al_busca").columns([5, 2], vertical_alignment="center")
    busca = f1.text_input("Buscar", placeholder="🔍 Buscar aluno ou bairro", label_visibility="collapsed")
    with f2.popover("Filtros", icon=":material/tune:", width="stretch"):
        turno_f = st.selectbox("Turno", ["Todos"] + list(TURNOS.values()))
        van_nomes = ["Todas as vans"] + list(vans["nome"]) + ["Sem van"] if not vans.empty else ["Todas as vans"]
        van_f = st.selectbox("Van", van_nomes)
        ver_inat = st.toggle("Mostrar inativos")
    df = todos if ver_inat else ativos
    if van_f == "Sem van":
        df = df[df["van"].isna()]
    elif van_f != "Todas as vans":
        df = df[df["van"] == van_f]
    if turno_f != "Todos":
        df = df[df["turno"].map(TURNOS) == turno_f]
    if busca:
        alvo = df[["nome", "bairro", "responsaveis", "escola"]].fillna("").astype(str).agg(" ".join, axis=1)
        df = df[alvo.str.contains(busca, case=False, regex=False)]
    sem_van = int(ativos["van"].isna().sum()) if not ativos.empty else 0
    if sem_van and not vans.empty:
        st.warning(f"{sem_van} aluno(s) sem van — não aparecem na rota.", icon=":material/airport_shuttle:")
    st.caption(f"{len(df)} aluno(s) · toque para abrir a ficha")
    for r in df.itertuples():
        sub = " · ".join(x for x in [r.van or "sem van", TURNOS.get(r.turno, ""), brl(r.mensalidade)] if x)
        if st.button(f"**{r.nome}**{'' if r.ativo else ' (inativo)'}  \n{sub}", key=f"al_{r.id}", width="stretch"):
            _ir("ficha", str(r.id))


_modo = ss.get("al_modo")
if _modo == "novo":
    _cadastro_novo()
    st.stop()
if _modo == "ficha" and ss.get("al_pid"):
    _ficha(ss["al_pid"])
    st.stop()
aba_al, aba_ct = st.tabs(["Alunos", "Contratos"])
with aba_al:
    _lista()

# ------------------------------------------------------------------ contratos
def _form_servico(r, sv: dict, chave: str):
    """Formulário das condições do serviço (gestor). Devolve o dict ou None se não salvou."""
    from datetime import date as _date
    from core import contrato as ct
    with st.form(chave):
        a, b = st.columns(2)
        aluno_n = a.text_input("Aluno(a)", value=sv.get("aluno", ""))
        escola_n = b.text_input("Escola", value=sv.get("escola", ""))
        a, b, cc, dd = st.columns(4)
        turno = a.selectbox("Turno", list(TURNOS.values()),
                            index=list(TURNOS.values()).index(sv["turno"]) if sv.get("turno") in TURNOS.values() else 0)
        modal = b.selectbox("Modalidade", ct.MODALIDADES,
                            index=ct.MODALIDADES.index(sv["modalidade"]) if sv.get("modalidade") in ct.MODALIDADES else 0)
        hb = cc.text_input("Horário de busca", value=sv.get("horario_busca", ""), placeholder="06:40")
        he = dd.text_input("Horário de entrega", value=sv.get("horario_entrega", ""), placeholder="12:30")
        embarque = st.text_input("Endereço de embarque", value=sv.get("embarque", ""))
        desembarque = st.text_input("Endereço de desembarque", value=sv.get("desembarque", ""))
        a, b = st.columns(2)
        ini = a.date_input("Início", value=_date.fromisoformat(sv["inicio"]), format="DD/MM/YYYY")
        fim = b.date_input("Fim", value=_date.fromisoformat(sv["fim"]), format="DD/MM/YYYY")
        a, b, cc = st.columns(3)
        parcela = a.number_input("Valor da parcela (R$)", min_value=0.0, step=10.0, value=float(sv.get("valor_parcela", 0)))
        parcelas = b.number_input("Nº de parcelas", min_value=1, max_value=12, value=int(sv.get("parcelas", 12)))
        dia = cc.number_input("Dia do vencimento", min_value=1, max_value=28, value=int(sv.get("dia_vencimento", 10)))
        st.caption(f"Valor total: {brl(parcela * parcelas)}")
        ok = st.form_submit_button("Salvar e liberar para o responsável", type="primary")
    if not ok:
        return None
    if fim < ini:
        st.error("O fim é antes do início.")
        return None
    return dict(aluno=aluno_n.strip(), escola=escola_n.strip(), turno=turno, modalidade=modal,
                horario_busca=hb.strip(), horario_entrega=he.strip(), embarque=embarque.strip(),
                desembarque=desembarque.strip(), inicio=ini.isoformat(), fim=fim.isoformat(),
                valor_parcela=float(parcela), parcelas=int(parcelas), dia_vencimento=int(dia))


with aba_ct:
    from core import contrato as ct
    from core.fmt import TZ, link_whats as _lw
    ano = hoje().year
    emp = repo.empresa(cid)
    eu_nome = st.session_state["usuario"].get("nome") or st.session_state["usuario"]["email"]
    cts = repo.contratos_empresa(cid, ano)
    por_id = {r.id: r._asdict() for r in todos.itertuples()} if not todos.empty else {}

    def _padrao(pid):
        a = dict(por_id.get(pid, {}))
        a["turno_txt"] = TURNOS.get(a.get("turno"), "")
        return ct.servico_padrao(a, ano)

    if cts.empty:
        st.info("Nenhum aluno ativo.")
    else:
        n = cts["situacao"].value_counts()
        st.caption(f"Contratos {ano}: {n.get('ok', 0)} assinados · {n.get('assinar', 0)} para você assinar · "
                   f"{n.get('pendente', 0)} com o responsável · {n.get('preparar', 0)} para preparar")
        if not emp.get("cnpj"):
            st.warning("Preencha o **CNPJ** e o nome da contratada em **Minha empresa → Contrato** antes de liberar "
                       "os contratos.", icon=":material/contract_edit:")
        sem = cts[cts["situacao"] == "preparar"]
        if len(sem):
            with st.popover(f"Liberar {len(sem)} contrato(s) com as condições do cadastro",
                            icon=":material/bolt:"):
                st.caption("Usa a mensalidade, o vencimento, o turno, ida/volta e os endereços do cadastro de cada "
                           "aluno, 12 parcelas e o ano todo. Você pode ajustar um a um depois, enquanto o responsável "
                           "não assinar.")
                if st.button("Liberar todos", type="primary"):
                    for pid in sem["passageiro_id"]:
                        repo.preparar_contrato(cid, pid, ano, _padrao(pid), eu_nome)
                    st.rerun()

        filtro = st.segmented_control("Mostrar", ["Todos", "Preparar", "Com o responsável", "Para eu assinar",
                                                  "Assinados"], default="Todos", key="f_ct",
                                      label_visibility="collapsed")
        mapa = {"Preparar": "preparar", "Com o responsável": "pendente", "Para eu assinar": "assinar",
                "Assinados": "ok"}
        if filtro in mapa:
            cts = cts[cts["situacao"] == mapa[filtro]]
        rot = {"ok": ("pago", "Assinado ✅"), "assinar": ("vence_logo", "Assine você"),
               "pendente": ("aberto", "Com o responsável"), "preparar": ("vencido", "Preparar")}
        for r in cts.itertuples():
            with st.container(border=True, key=f"card_ct_{r.passageiro_id}"):
                cls, txt = rot[r.situacao]
                st.markdown(f"**{_ui.esc(r.aluno)}** {_ui.tag(cls, txt)}"
                            f"{' <span class=ve-sub>· ' + _ui.esc(r.van) + '</span>' if r.van else ''}",
                            unsafe_allow_html=True)

                if r.situacao in ("preparar", "pendente"):
                    sv = dict(r.servico) if r.servico else _padrao(r.passageiro_id)
                    if r.situacao == "pendente":
                        st.caption("  ·  ".join(ct.linhas_servico(sv)[3:]))
                        if not r.tem_email:
                            st.caption("⚠️ Sem e-mail do Google no responsável — cadastre na ficha "
                                       "do aluno para ele conseguir assinar.")
                        else:
                            tel = todos.loc[todos["id"] == r.passageiro_id, "telefone_resp"].squeeze() \
                                if not todos.empty else None
                            msg = (f"Olá! O contrato de transporte escolar de {r.aluno} ({ano}) já está no app "
                                   "Turminha a Bordo: " + _ui.APP_URL + " — entre com o seu Google, "
                                   "confira as condições, preencha seus dados e clique em Assinar e enviar. Obrigado!")
                            lk = _lw(tel if isinstance(tel, str) else None, msg)
                            lm = link_email(r.email_resp, f"Contrato da van escolar — {r.aluno} ({ano})", msg)
                            k1, k2 = st.container(key=f"linha_lembra_{r.passageiro_id}").columns(2)
                            if lk:
                                k1.link_button("Lembrar no WhatsApp", lk, icon=":material/chat:", width="stretch")
                            if lm:
                                k2.link_button("Lembrar por e-mail", lm, icon=":material/mail:", width="stretch")
                    titulo = "Preparar contrato" if r.situacao == "preparar" else "Ajustar condições"
                    with st.expander(titulo, expanded=False):
                        novo = _form_servico(r, sv, f"sv_{r.passageiro_id}")
                        if novo:
                            repo.preparar_contrato(cid, r.passageiro_id, ano, novo, eu_nome)
                            st.toast("Contrato liberado para o responsável.")
                            st.rerun()
                    continue

                st.caption(f"Assinado por {r.responsavel_nome} em "
                           f"{r.responsavel_assinou_em.astimezone(TZ).strftime('%d/%m/%Y %H:%M')}"
                           + (f" · contratada em {r.contratada_assinou_em.astimezone(TZ).strftime('%d/%m/%Y %H:%M')}"
                              if r.contratada_assinou_em else ""))
                c_full = r._asdict()
                x1, x2, x3 = st.container(key=f"linha_ct_{r.contrato_id}").columns(3)
                if r.situacao == "assinar":
                    if x1.button("Assinar", key=f"ass_{r.contrato_id}", type="primary", icon=":material/draw:",
                                 width="stretch"):
                        repo.assinar_contrato_contratada(cid, r.contrato_id, eu_nome)
                        st.rerun()
                x2.download_button("PDF", ct.pdf_cache(c_full, emp), file_name=f"contrato_{ano}_{r.aluno}.pdf",
                                   mime="application/pdf", icon=":material/download:", key=f"pdfg_{r.contrato_id}",
                                   width="stretch")
                with x3.popover("Descartar", icon=":material/delete:", width="stretch"):
                    st.caption("Apaga este contrato (inclusive as assinaturas). Depois é só preparar e liberar de novo.")
                    if st.button("Confirmar descarte", key=f"desc_{r.contrato_id}"):
                        repo.cancelar_contrato(cid, r.contrato_id)
                        st.rerun()
                tel_r = todos.loc[todos["id"] == r.passageiro_id, "telefone_resp"].squeeze() if not todos.empty else None
                _ui.botoes_enviar_contrato(c_full, r.aluno, tel_r if isinstance(tel_r, str) else None,
                                           r.responsavel_email, "ao responsável", f"g_{r.contrato_id}")
                with st.expander("Ver contrato"):
                    st.text(c_full["texto"] or "")
