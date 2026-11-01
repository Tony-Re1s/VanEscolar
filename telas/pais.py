"""Área da família: carteirinha, embarque do dia, avisar falta e mensalidades."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from core import contrato as ct
from core import repo, rota as R
from core.fmt import TZ, TURNOS, brl, data_br, hoje, idade, link_whats, mes_label
from telas import _ui

u = st.session_state["usuario"]
pids = u.get("filhos") or []
h = hoje()
st.title("Meus filhos")

filhos = repo.filhos(pids)
if filhos.empty:
    st.info("Nenhum aluno vinculado ao seu e-mail.")
    st.stop()

status = repo.status_hoje(pids, h)
rotas = repo.rotas_dos_filhos(pids, h)
avisos = repo.avisos_dos_filhos(pids, h)


@st.fragment(run_every=30)
def _ao_vivo(pid: str, nome: str):
    """Van no mapa só enquanto a rota do filho está em andamento: na ida até chegar na escola, na volta até ser
    entregue. Atualiza sozinho a cada 30 segundos."""
    f1 = repo.filhos([pid])
    tok = f1.iloc[0]["loc_token"] if len(f1) else None
    s1 = repo.status_hoje([pid], h)
    r1 = repo.rotas_dos_filhos([pid], h)
    a1 = repo.ausencias([pid], h)
    a1 = a1[a1["data"] == h] if not a1.empty else a1
    for t in ("ida", "volta"):
        x = r1[r1["trecho"] == t] if not r1.empty else r1
        if x.empty:
            continue
        st_t = s1[s1["trecho"] == t]["status"] if not s1.empty else []
        st_t = st_t.iloc[0] if len(st_t) else None
        ausente = bool(len(a1) and a1[t].any())
        if R.em_andamento_para(x.iloc[0].to_dict(), st_t, ausente):
            onde = {"embarcou": f"{nome} está na van", None: "A van está a caminho" if t == "ida"
                    else f"{nome} está na van, voltando para casa"}.get(st_t, "A van está em rota")
            st.info(f"🚐 {onde}.", icon=":material/directions_bus:")
            if isinstance(tok, str) and tok:
                st.link_button("📍 Ver a van no mapa agora", _ui.link_mapa(tok), type="primary", width="stretch",
                               key=f"mapa_{pid}_{t}")
            return


def _contrato(f, pid):
    """Contrato do ano. O gestor libera com as condições do serviço; o responsável completa os dados dele e assina."""
    ano = h.year
    emp = repo.empresa(f.condutor_id)
    c = repo.contrato_do_aluno(pid, ano)
    if not c or not c.get("servico"):
        return                                   # ainda não liberado pelo gestor: nada a fazer
    if c.get("responsavel_assinou_em") is not None:
        ok = c["contratada_assinou_em"] is not None
        with st.expander(f"📄 Contrato {ano} — " + ("assinado pelas duas partes ✅" if ok
                                                    else "enviado, aguardando a contratada"), expanded=False):
            st.caption(f"Enviado por {c['responsavel_nome']} em {data_br(c['responsavel_assinou_em'].astimezone(TZ))}"
                       f" · código {c['codigo']}")
            st.download_button("Baixar contrato (PDF)", ct.pdf_cache(c, emp), file_name=f"contrato_{ano}_{pid[:8]}.pdf",
                               mime="application/pdf", icon=":material/download:", key=f"pdf_{pid}")
            st.caption("Guardar uma cópia:")
            _ui.botoes_enviar_contrato(c, f.nome, (c.get("dados") or {}).get("telefone"), u["email"], "", f"p_{pid}")
        return

    sv = dict(c["servico"])
    st.warning(f"**Contrato {ano} para assinar** — confira as condições, preencha seus dados e envie para "
               f"{emp.get('razao_social') or emp['nome']}.", icon=":material/contract_edit:")
    with st.expander("📄 Ler, preencher e assinar o contrato", expanded=True):
        n = ct._numero(ct.clausulas(emp))
        st.markdown(f"**{ct.TITULO}**")
        st.markdown(ct.preambulo(emp))
        st.text_area("Cláusulas", ct.clausulas(emp), height=240, disabled=True, key=f"cl_{pid}",
                     label_visibility="collapsed")
        st.markdown(f"**CLÁUSULA {n + 1}ª – DAS CONDIÇÕES DO SERVIÇO**")
        st.markdown("  \n".join(_ui.esc(x) for x in ct.linhas_servico(sv)))
        st.caption("Alguma condição errada? Fale com a van antes de assinar — ela corrige e libera de novo.")

        # pré-preenche: o que já assinou antes (irmãos / ano anterior) > cadastro do responsável
        resp = repo.responsaveis_do(f.condutor_id, pid)
        eu = resp[resp["email"].fillna("").str.lower() == u["email"]] if not resp.empty else resp
        r0 = eu.iloc[0].to_dict() if len(eu) else {}
        ant = repo.ultimo_contratante(u["email"])
        v = lambda k, alt="": ant.get(k) or alt  # noqa: E731

        st.markdown(f"**CLÁUSULA {n + 2}ª – DOS DADOS DO CONTRATANTE** — preencha ou corrija")
        with st.form(f"contrato_{pid}"):
            nome = st.text_input("Nome completo *", value=v("responsavel", r0.get("nome") or u.get("nome") or ""))
            a, b = st.columns(2)
            cpf = a.text_input("CPF *", value=v("cpf"), placeholder="000.000.000-00")
            rg = b.text_input("RG", value=v("rg"))
            a, b = st.columns(2)
            nasc = a.text_input("Data de nascimento", value=v("nascimento"), placeholder="dd/mm/aaaa")
            par_ops = ["Mãe", "Pai", "Avó", "Avô", "Tia", "Tio", "Responsável legal", "Outro"]
            par_atual = v("parentesco", r0.get("parentesco") or "Mãe")
            parentesco = b.selectbox("Parentesco *", par_ops,
                                     index=par_ops.index(par_atual) if par_atual in par_ops else len(par_ops) - 1)
            tel = st.text_input("Telefone *", value=v("telefone", r0.get("telefone") or ""))
            st.markdown("**Endereço**")
            a, b = st.columns([1, 2])
            cep = a.text_input("CEP *", value=v("cep"), placeholder="00000-000")
            rua = b.text_input("Rua / avenida *", value=v("rua"))
            a, b, cc = st.columns([1, 2, 2])
            numero = a.text_input("Número *", value=v("numero"))
            compl = b.text_input("Complemento", value=v("complemento"), placeholder="apto, bloco…")
            bairro = cc.text_input("Bairro *", value=v("bairro"))
            a, b = st.columns([3, 1])
            cidade = a.text_input("Cidade *", value=v("cidade", emp.get("cidade") or ""))
            uf = b.text_input("UF *", value=v("uf", "SP"), max_chars=2)
            local = st.text_input("Local da assinatura *", value=v("local", emp.get("cidade") or ""))
            aceite = st.checkbox("Li e concordo com todas as cláusulas e condições deste contrato. Entendo que este "
                                 "aceite, feito com o meu login Google, vale como minha assinatura eletrônica.")
            st.caption("Assinatura eletrônica com validade jurídica (Lei nº 14.063/2020 e art. 10, § 2º, da MP nº "
                       "2.200-2/2001). Ficam registrados seu e-mail, data, hora e IP, e o contrato recebe um código "
                       "de conferência.")
            enviar = st.form_submit_button("Assinar e enviar", type="primary", width="stretch")
        if enviar:
            obrig = (("nome", nome), ("CPF", cpf), ("telefone", tel), ("CEP", cep), ("rua", rua), ("número", numero),
                     ("bairro", bairro), ("cidade", cidade), ("UF", uf), ("local", local))
            faltando = [rot for rot, val in obrig if not val.strip()]
            if faltando:
                st.error("Preencha: " + ", ".join(faltando) + ".")
                return
            if not ct.cpf_valido(cpf):
                st.error("CPF inválido. Confira os números.")
                return
            if not aceite:
                st.error("Marque que leu e concorda com o contrato.")
                return
            dados = dict(responsavel=nome.strip(), cpf=ct.formatar_cpf(cpf), rg=rg.strip(), nascimento=nasc.strip(),
                         parentesco=parentesco, telefone=tel.strip(), cep=cep.strip(), rua=rua.strip(),
                         numero=numero.strip(), complemento=compl.strip(), bairro=bairro.strip(),
                         cidade=cidade.strip(), uf=uf.strip().upper(), local=local.strip(), data=data_br(h))
            texto = ct.montar_texto(emp, sv, dados)
            cod = ct.codigo(texto, dados, u["email"])
            ip = (st.context.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or None
            r = repo.assinar_contrato_responsavel(f.condutor_id, pid, ano, texto, dados, cod, u["email"],
                                                  nome.strip(), ip)
            if not r:
                st.error("Não foi possível registrar. Seu e-mail precisa estar cadastrado como responsável deste "
                         "aluno — fale com a van.")
                return
            st.toast("Contrato assinado e enviado! ✅")
            st.rerun()


abas = st.tabs([r.nome.split()[0] for r in filhos.itertuples()]) if len(filhos) > 1 else [st.container()]

for aba, f in zip(abas, filhos.itertuples()):
    pid = str(f.id)
    with aba:
        # avisos do transporte (gerais, da van ou só deste filho)
        av = avisos[avisos["passageiro_id"].astype(str) == pid] if not avisos.empty else avisos
        quem_av = f.apelido or f.condutor
        for x in av.itertuples():
            st.markdown(f"<div class='ve-faixa'>📣 <b>Aviso de {_ui.esc(quem_av)}</b> "
                        f"<span class='ve-sub'>· {x.criado_em.astimezone(TZ):%d/%m %H:%M}</span><br>"
                        f"{_ui.sem_formula(_ui.esc(x.texto))}</div>", unsafe_allow_html=True)
        # localização ao vivo da van — só enquanto a rota deste filho está em andamento
        _ao_vivo(pid, f.nome.split()[0])
        _contrato(f, pid)

        # carteirinha
        nasc = f"{idade(f.data_nasc)} anos · " if f.data_nasc else ""
        st.markdown(f"""<div class='ve-cart'>
            <div class='t'>Carteirinha do transporte escolar</div>
            <h3>{_ui.esc(f.nome)}</h3>
            <div>{nasc}{_ui.esc(f.serie or '')} {('· ' + TURNOS.get(f.turno, '')) if f.turno else ''}</div>
            <div class='r'>🏫 {_ui.esc(f.escola or '—')}</div>
            <div class='r'>🚐 {_ui.esc(f.van or f.condutor)} · {_ui.esc(f.veiculo or '')} {_ui.esc(f.placa or '')}</div>
            <div class='r'>👤 Motorista: {_ui.esc(f.motorista)} · 📞 {_ui.esc(f.condutor_tel or '—')}</div>
            {"<div class='r'>🧡 Monitor(a): " + _ui.esc(f.monitor_nome) + (" · 📞 " + _ui.esc(f.monitor_telefone) if f.monitor_telefone else "") + "</div>" if f.monitor_nome else ""}
            <div class='r'>🏢 {_ui.esc(f.condutor)}</div></div>""", unsafe_allow_html=True)
        zap = link_whats(f.condutor_tel, f"Olá! Sou responsável por {f.nome}.")
        if zap:
            st.link_button("Falar com o motorista", zap, icon=":material/chat:")

        # hoje
        st.subheader("Hoje")
        s = status[status["passageiro_id"].astype(str) == pid] if not status.empty else status
        rot = {"ida": {"embarcou": "Embarcou na van", "desembarcou": "Chegou na escola", "faltou": "Não embarcou"},
               "volta": {"embarcou": "Saiu da escola na van", "desembarcou": "Entregue em casa",
                         "faltou": "Não voltou na van"}}
        linhas = []
        for t in ("ida", "volta"):
            x = s[s["trecho"] == t] if not s.empty else s
            if not x.empty:
                r = x.iloc[0]
                linhas.append(f"**{t.capitalize()}:** {rot[t][r['status']]} às {r['hora'].astimezone(TZ).strftime('%H:%M')}")
            else:
                linhas.append(f"**{t.capitalize()}:** aguardando")
        rt = rotas[rotas["passageiro_id"].astype(str) == pid] if not rotas.empty else rotas
        for t in ("ida", "volta"):
            x = rt[rt["trecho"] == t] if not rt.empty else rt
            if x.empty:
                continue
            q = x.iloc[0]
            fim = q.get("finalizada_em")
            if fim is not None and not pd.isna(fim):
                linhas.append(f"✅ Rota da {t} finalizada às {fim.astimezone(TZ):%H:%M}")
            elif not (not s.empty and (s["trecho"] == t).any()):
                pos = f" · {f.nome.split()[0]} é o {int(q['posicao'])}º da rota" if t == "ida" else ""
                st.info(f"🚐 A van saiu para a {'ida' if t == 'ida' else 'volta'} às "
                        f"{q['iniciada_em'].astimezone(TZ).strftime('%H:%M')}{pos}.", icon=":material/directions_bus:")
        st.markdown("  \n".join(linhas))
        st.caption("Atualiza quando o motorista marca na chamada. Recarregue a página para ver o mais recente.")

        # avisar falta
        st.subheader("Avisar falta")
        aus = repo.ausencias([pid], h)
        with st.form(f"aus_{pid}", clear_on_submit=True):
            a, b = st.columns(2)
            d = a.date_input("Dia", value=h, min_value=h, max_value=h + timedelta(days=90), format="DD/MM/YYYY")
            q = b.selectbox("Trecho", ["Ida e volta", "Só ida", "Só volta"])
            m = st.text_input("Motivo (opcional)", placeholder="Ex.: consulta médica, vou buscar")
            if st.form_submit_button("Avisar a van", type="primary"):
                repo.avisar_ausencia(pid, d, q != "Só volta", q != "Só ida", m or None, u["id"])
                st.success(f"Aviso registrado para {data_br(d)}.")
                st.rerun()
        for r in aus.itertuples():
            trechos = " e ".join(t for t, v in (("ida", r.ida), ("volta", r.volta)) if v)
            a, b = st.columns([4, 1])
            a.markdown(f"📅 **{data_br(r.data)}** — não vai ({trechos}){' · ' + _ui.esc(r.motivo) if r.motivo else ''}")
            if b.button("Cancelar", key=f"canc_{r.id}", type="tertiary"):
                repo.cancelar_ausencia(pid, r.id)
                st.rerun()

        # mensalidades
        st.subheader("Mensalidades")
        mens = repo.mensalidades_filhos([pid], h)
        if f.chave_pix:
            st.markdown(f"Chave Pix para pagamento ({f.condutor}):")
            st.code(f.chave_pix, language=None)
        if mens.empty:
            st.caption("Nenhuma mensalidade lançada ainda.")
        for r in mens.itertuples():
            pago = f" · pago em {data_br(r.pago_em)}" if r.pago_em else ""
            st.markdown(f"{mes_label(r.competencia)} — **{brl(r.valor)}** · vence {data_br(r.vencimento)}{pago} "
                        f"{_ui.tag(r.situacao, _ui.ROTULO_MENS[r.situacao])}", unsafe_allow_html=True)

# Instagram do app (engajamento das famílias)
st.divider()
with st.container(border=True, key="card_insta_pais"):
    st.markdown("**📸 O Turminha a Bordo está no Instagram!**  \n"
                "<span class='ve-sub'>Dicas de segurança no transporte escolar e as novidades do app.</span>",
                unsafe_allow_html=True)
    _ui.instagram("Seguir", chave="insta_pais")
