"""Alunos (passageiros) e responsáveis."""
from datetime import date

import pandas as pd
import streamlit as st

from core import repo
from core.fmt import TURNOS, brl, hoje, idade, link_whats
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
st.title("Alunos e responsáveis")

escolas = repo.escolas(cid)
todos = repo.passageiros(cid, so_ativos=False)
ativos = todos[todos["ativo"]] if not todos.empty else todos

if escolas.empty:
    st.info("Dica: cadastre as **escolas** antes, para escolher aqui.", icon=":material/school:")

aba_lista, aba_edit = st.tabs(["Lista", "Cadastrar / editar"])

# ------------------------------------------------------------------ lista
with aba_lista:
    if todos.empty:
        st.info("Nenhum aluno ainda. Use a aba **Cadastrar / editar**.")
    else:
        f1, f2, f3 = st.columns([2, 1, 1])
        busca = f1.text_input("Buscar", placeholder="nome, bairro, responsável…", label_visibility="collapsed")
        turno_f = f2.selectbox("Turno", ["Todos"] + list(TURNOS.values()), label_visibility="collapsed")
        ver_inat = f3.toggle("Mostrar inativos")
        df = todos if ver_inat else ativos
        if turno_f != "Todos":
            df = df[df["turno"].map(TURNOS) == turno_f]
        if busca:
            alvo = df[["nome", "bairro", "responsaveis", "escola"]].fillna("").astype(str).agg(" ".join, axis=1)
            df = df[alvo.str.contains(busca, case=False)]
        lot = len(ativos)
        st.caption(f"{lot} aluno(s) ativo(s) · {c['capacidade']} lugares na van · "
                   f"mensalidades somam {brl(ativos['mensalidade'].astype(float).sum())}/mês")
        vis = df.assign(turno=df["turno"].map(TURNOS), idade=df["data_nasc"].map(idade),
                        whats=df["telefone_resp"].map(lambda t: link_whats(t, "Olá!")))
        st.dataframe(vis[["nome", "idade", "escola", "turno", "bairro", "mensalidade", "dia_venc", "responsaveis",
                          "whats", "ativo"]],
                     hide_index=True, use_container_width=True,
                     column_config={"nome": "Aluno", "idade": "Idade", "escola": "Escola", "turno": "Turno",
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
        escola_id = st.selectbox("Escola", esc_ids, index=esc_ids.index(esc_atual), format_func=esc_nomes.get)
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
        dados = dict(escola_id=escola_id, nome=nome.strip(), data_nasc=nasc, serie=serie or None, turno=turno,
                     endereco=endereco or None, bairro=bairro or None, referencia=referencia or None,
                     observacoes=observacoes or None, mensalidade=mensalidade, dia_vencimento=dia_v or None,
                     inicio=inicio, fim=fim, faz_ida=faz_ida, faz_volta=faz_volta, ativo=ativo)
        if p is None and len(ativos) >= int(c["capacidade"]):
            st.warning(f"Atenção: a van tem {c['capacidade']} lugares e já há {len(ativos)} alunos ativos "
                       "(pode ser de turnos diferentes).")
        repo.salvar_passageiro(cid, dados, pid=g("id"))
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
        for r in resp.itertuples():
            with st.container(border=True):
                x1, x2 = st.columns([4, 1])
                x1.markdown(f"**{r.nome}** {('· ' + r.parentesco) if r.parentesco else ''}"
                            f"{' · 💰 financeiro' if r.financeiro else ''}  \n"
                            f"📞 {r.telefone or '—'} · ✉️ {r.email or 'sem e-mail (não acessa o app)'}")
                if x2.button("Remover", key=f"rm_{r.id}"):
                    repo.desvincular_responsavel(cid, p["id"], r.id)
                    st.rerun()

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
