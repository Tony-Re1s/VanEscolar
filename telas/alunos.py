"""Alunos (passageiros) e responsáveis."""
from datetime import date

import pandas as pd
import streamlit as st

from core import repo
from core.fmt import TURNOS, brl, hoje, idade, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
st.title("Alunos e responsáveis")

escolas = repo.escolas(cid)
vans = repo.vans(cid)
todos = repo.passageiros(cid, so_ativos=False)
ativos = todos[todos["ativo"]] if not todos.empty else todos

if vans.empty:
    st.info("Dica: cadastre as **vans** antes, para escolher em qual van cada aluno vai.",
            icon=":material/airport_shuttle:")
if escolas.empty:
    st.info("Dica: cadastre as **escolas** antes, para escolher aqui.", icon=":material/school:")

aba_lista, aba_edit, aba_ct = st.tabs(["Lista", "Cadastrar / editar", "Contratos"])

# ------------------------------------------------------------------ lista
with aba_lista:
    if todos.empty:
        st.info("Nenhum aluno ainda. Use a aba **Cadastrar / editar**.")
    else:
        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        busca = f1.text_input("Buscar", placeholder="nome, bairro, responsável…", label_visibility="collapsed")
        turno_f = f2.selectbox("Turno", ["Todos"] + list(TURNOS.values()), label_visibility="collapsed")
        van_nomes = ["Todas as vans"] + list(vans["nome"]) + ["Sem van"] if not vans.empty else ["Todas as vans"]
        van_f = f3.selectbox("Van", van_nomes, label_visibility="collapsed")
        ver_inat = f4.toggle("Mostrar inativos")
        df = todos if ver_inat else ativos
        if van_f == "Sem van":
            df = df[df["van"].isna()]
        elif van_f != "Todas as vans":
            df = df[df["van"] == van_f]
        if turno_f != "Todos":
            df = df[df["turno"].map(TURNOS) == turno_f]
        if busca:
            alvo = df[["nome", "bairro", "responsaveis", "escola"]].fillna("").astype(str).agg(" ".join, axis=1)
            df = df[alvo.str.contains(busca, case=False)]
        lugares = int(vans["capacidade"].sum()) if not vans.empty else 0
        st.caption(f"{len(ativos)} aluno(s) ativo(s) · {len(vans)} van(s) com {lugares} lugares · "
                   f"mensalidades somam {brl(ativos['mensalidade'].astype(float).sum())}/mês")
        sem_van = int(ativos["van"].isna().sum()) if not ativos.empty else 0
        if sem_van and not vans.empty:
            st.warning(f"{sem_van} aluno(s) ativo(s) sem van — não aparecem na rota. Escolha a van no cadastro.")
        vis = df.assign(turno=df["turno"].map(TURNOS), idade=df["data_nasc"].map(idade),
                        whats=df["telefone_resp"].map(lambda t: link_whats(t, "Olá!")))
        st.dataframe(vis[["nome", "van", "idade", "escola", "turno", "bairro", "mensalidade", "dia_venc",
                          "responsaveis", "whats", "ativo"]],
                     hide_index=True, use_container_width=True,
                     column_config={"nome": "Aluno", "van": "Van", "idade": "Idade", "escola": "Escola", "turno": "Turno",
                                    "bairro": "Bairro",
                                    "mensalidade": st.column_config.NumberColumn("Mensalidade", format="R$ %.2f"),
                                    "dia_venc": "Venc.", "responsaveis": "Responsáveis",
                                    "whats": st.column_config.LinkColumn("WhatsApp", display_text="abrir"),
                                    "ativo": "Ativo"})

# ------------------------------------------------------------------ cadastro
with aba_edit:
    NOVO = "➕ Novo aluno"
    nomes = [NOVO] + [f"{r.nome}{'' if r.ativo else ' (inativo)'}" for r in todos.itertuples()]
    pend = st.session_state.pop("aluno_sel", None)
    if pend in nomes:
        st.session_state["aluno_box"] = pend
    escolha = st.selectbox("Aluno", nomes, key="aluno_box")
    p = None if escolha == NOVO else todos.iloc[nomes.index(escolha) - 1].to_dict()
    g = (p or {}).get

    esc_ids = [None] + [str(x) for x in escolas["id"]] if not escolas.empty else [None]
    esc_nomes = {None: "—"} | ({str(r.id): r.nome for r in escolas.itertuples()} if not escolas.empty else {})
    esc_atual = str(g("escola_id")) if g("escola_id") is not None and str(g("escola_id")) in esc_ids else None
    van_ids = [None] + [str(x) for x in vans["id"]] if not vans.empty else [None]
    van_nomes_d = {None: "— sem van —"} | ({str(r.id): f"{r.nome} ({r.alunos}/{r.capacidade})"
                                           for r in vans.itertuples()} if not vans.empty else {})
    van_atual = str(g("van_id")) if g("van_id") is not None and str(g("van_id")) in van_ids else \
        (van_ids[1] if p is None and len(van_ids) == 2 else None)

    def _d(v):
        return None if v is None or pd.isna(v) else v

    with st.form("aluno", clear_on_submit=p is None):
        nome = st.text_input("Nome do aluno *", value=g("nome") or "")
        a1, a2, a3 = st.columns(3)
        nasc = a1.date_input("Nascimento", value=_d(g("data_nasc")), min_value=date(2000, 1, 1),
                             max_value=hoje(), format="DD/MM/YYYY")
        serie = a2.text_input("Série / turma", value=g("serie") or "")
        turnos = list(TURNOS)
        turno = a3.selectbox("Turno", turnos, index=turnos.index(g("turno")) if g("turno") in turnos else 0,
                             format_func=TURNOS.get)
        v1, v2 = st.columns(2)
        van_id = v1.selectbox("Van", van_ids, index=van_ids.index(van_atual), format_func=van_nomes_d.get)
        escola_id = v2.selectbox("Escola", esc_ids, index=esc_ids.index(esc_atual), format_func=esc_nomes.get)
        endereco = st.text_input("Endereço de embarque", value=g("endereco") or "",
                                 help="Rua, número e cidade — usado no link da rota do Google Maps.")
        b1, b2 = st.columns(2)
        bairro = b1.text_input("Bairro", value=g("bairro") or "")
        referencia = b2.text_input("Ponto de referência", value=g("referencia") or "")
        observacoes = st.text_area("Observações (alergias, cuidados, quem pode buscar…)", value=g("observacoes") or "",
                                   height=80)
        st.markdown("**Contrato**")
        m1, m2, m3, m4 = st.columns(4)
        mensalidade = m1.number_input("Mensalidade (R$)", min_value=0.0, step=10.0,
                                      value=float(g("mensalidade") or 0))
        dia_v = m2.number_input("Dia do vencimento", min_value=0, max_value=28, value=int(g("dia_vencimento") or 0),
                                help=f"0 = usar o padrão (dia {c['dia_vencimento']})")
        inicio = m3.date_input("Início", value=_d(g("inicio")) or hoje(), format="DD/MM/YYYY")
        fim = m4.date_input("Fim (opcional)", value=_d(g("fim")), format="DD/MM/YYYY")
        t1, t2, t3 = st.columns(3)
        faz_ida = t1.checkbox("Faz a ida", value=bool(g("faz_ida") if p else True))
        faz_volta = t2.checkbox("Faz a volta", value=bool(g("faz_volta") if p else True))
        ativo = t3.checkbox("Ativo", value=bool(g("ativo") if p else True))
        ok = st.form_submit_button("Salvar aluno", type="primary")

    if ok:
        if not nome.strip():
            st.error("Preencha o nome do aluno.")
            st.stop()
        if fim and fim < inicio:
            st.error("O fim do contrato é antes do início.")
            st.stop()
        dados = dict(escola_id=escola_id, van_id=van_id, nome=nome.strip(), data_nasc=nasc, serie=serie or None, turno=turno,
                     endereco=endereco or None, bairro=bairro or None, referencia=referencia or None,
                     observacoes=observacoes or None, mensalidade=mensalidade, dia_vencimento=dia_v or None,
                     inicio=inicio, fim=fim, faz_ida=faz_ida, faz_volta=faz_volta, ativo=ativo)
        repo.salvar_passageiro(cid, dados, pid=g("id"))
        if van_id and str(g("van_id")) != van_id:
            vv = vans.set_index(vans["id"].astype(str)).loc[van_id]
            if int(vv["alunos"]) + 1 > int(vv["capacidade"]):
                st.toast(f"Atenção: {vv['nome']} passou dos {vv['capacidade']} lugares "
                         "(pode estar ok se forem turnos diferentes).", icon="⚠️")
        st.session_state["aluno_sel"] = nome.strip() + ("" if ativo else " (inativo)")
        st.success("Aluno salvo. Agora cadastre os responsáveis logo abaixo.")
        st.rerun()

    # ---------------- responsáveis
    if p:
        st.divider()
        st.subheader(f"Responsáveis de {p['nome'].split()[0]}")
        st.caption("O **e-mail do Google** do responsável libera a área da família: ele vê a carteirinha, "
                   "o embarque do dia, as mensalidades e pode avisar faltas.")
        resp = repo.responsaveis_do(cid, p["id"])
        ac = repo.acessos(list(resp["email"].dropna())) if not resp.empty else {}
        for r in resp.itertuples():
            with st.container(border=True, key=f"card_resp_{r.id}"):
                x1, x2 = st.columns([4, 1])
                x1.markdown(f"**{_ui.esc(r.nome)}** {('· ' + _ui.esc(r.parentesco)) if r.parentesco else ''}"
                            f"{' · 💰 financeiro' if r.financeiro else ''} "
                            f"{_ui.selo_acesso(r.email, ac) if r.email else ''}  \n"
                            f"📞 {_ui.esc(r.telefone or '—')} · ✉️ {_ui.esc(r.email or 'sem e-mail (não acessa o app)')}",
                            unsafe_allow_html=True)
                if x2.button("Remover", key=f"rm_{r.id}"):
                    repo.desvincular_responsavel(cid, p["id"], r.id)
                    st.rerun()
                if r.email:
                    msg = (f"Olá, {r.nome.split(' ')[0]}! {c['nome']} cadastrou você como responsável de "
                           f"{p['nome']} no app Pequenos a Bordo. Acesse {_ui.APP_URL} e clique em \"Entrar com "
                           f"Google\" usando o e-mail {r.email}. Lá você vê a carteirinha, acompanha o embarque, avisa "
                           "faltas, vê as mensalidades e assina o contrato. 🚐")
                    lk = link_whats(r.telefone, msg)
                    if lk:
                        st.link_button("Convidar no WhatsApp", lk, icon=":material/send:", key=f"conv_{r.id}")
        if not resp.empty and resp["email"].notna().any():
            _ui.aviso_modo_teste()

        outros = repo.responsaveis(cid)
        outros = outros[~outros["id"].isin(resp["id"])] if not resp.empty and not outros.empty else outros
        with st.expander("➕ Adicionar responsável", expanded=resp.empty):
            if not outros.empty:
                ja = st.selectbox("Já cadastrado (irmãos)", [None] + [str(x) for x in outros["id"]],
                                  format_func=lambda i: "— novo responsável —" if i is None else
                                  outros.set_index(outros["id"].astype(str)).loc[i, "nome"])
                if ja and st.button("Vincular este responsável"):
                    r = outros.set_index(outros["id"].astype(str)).loc[ja]
                    repo.vincular_responsavel(cid, p["id"], dict(nome=r["nome"], parentesco=r["parentesco"],
                                                                 telefone=r["telefone"], email=r["email"]), rid=ja)
                    st.rerun()
            with st.form("resp", clear_on_submit=True):
                r1, r2 = st.columns(2)
                rn = r1.text_input("Nome *")
                rp = r2.selectbox("Parentesco", ["Mãe", "Pai", "Avó", "Avô", "Tia", "Tio", "Outro"])
                r3, r4 = st.columns(2)
                rt = r3.text_input("WhatsApp", placeholder="(11) 99999-9999")
                re_ = r4.text_input("E-mail do Google", placeholder="nome@gmail.com")
                rf = st.checkbox("Responsável financeiro (recebe a cobrança)", value=resp.empty)
                if st.form_submit_button("Adicionar"):
                    if not rn.strip():
                        st.error("Preencha o nome.")
                    else:
                        repo.vincular_responsavel(cid, p["id"], dict(nome=rn.strip(), parentesco=rp, telefone=rt or None,
                                                                     email=re_ or None), financeiro=rf)
                        st.rerun()

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
                            st.caption("⚠️ Sem e-mail do Google no responsável — cadastre na aba **Cadastrar / "
                                       "editar** para ele conseguir assinar.")
                        else:
                            tel = todos.loc[todos["id"] == r.passageiro_id, "telefone_resp"].squeeze() \
                                if not todos.empty else None
                            msg = (f"Olá! O contrato de transporte escolar de {r.aluno} ({ano}) já está no app "
                                   "Pequenos a Bordo: https://pequenosabordo.streamlit.app — entre com o seu Google, "
                                   "confira as condições, preencha seus dados e clique em Assinar e enviar. Obrigado!")
                            lk = _lw(tel if isinstance(tel, str) else None, msg)
                            if lk:
                                st.link_button("Lembrar no WhatsApp", lk, icon=":material/chat:")
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
                                 use_container_width=True):
                        repo.assinar_contrato_contratada(cid, r.contrato_id, eu_nome)
                        st.rerun()
                x2.download_button("PDF", ct.pdf_cache(c_full, emp), file_name=f"contrato_{ano}_{r.aluno}.pdf",
                                   mime="application/pdf", icon=":material/download:", key=f"pdfg_{r.contrato_id}",
                                   use_container_width=True)
                with x3.popover("Descartar", icon=":material/delete:", use_container_width=True):
                    st.caption("Apaga este contrato (inclusive as assinaturas). Depois é só preparar e liberar de novo.")
                    if st.button("Confirmar descarte", key=f"desc_{r.contrato_id}"):
                        repo.cancelar_contrato(cid, r.contrato_id)
                        st.rerun()
                with st.expander("Ver contrato"):
                    st.text(c_full["texto"] or "")
