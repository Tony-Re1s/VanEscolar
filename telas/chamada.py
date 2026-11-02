"""Rota do dia e chamada (embarque / desembarque / falta) — por van.
Gestor: escolhe qualquer van da empresa. Motorista contratado: só a(s) van(s) que dirige."""
import urllib.parse

import streamlit as st

from core import mensagens as M, repo, rota as R
from core.fmt import TZ, TURNOS, agora, data_br, hoje, inicio_mes, link_maps_rota, link_whats, somar_meses
from telas import _ui

u = st.session_state["usuario"]
st.title("Rota e chamada")
if u.get("condutor"):
    _ui.guia(u["condutor"], "telas/chamada.py")

if u.get("condutor") and _ui.aviso_pausa(u["condutor"]):
    st.stop()
vans = _ui.vans_acessiveis(u)
if not vans:
    st.info("Nenhuma van cadastrada. Cadastre em **Vans e motoristas**." if u.get("condutor")
            else "Você não está como motorista de nenhuma van.")
    st.stop()
varias = len({v["cid"] for v in vans}) > 1
if len(vans) > 1:
    idx = st.selectbox("Van", range(len(vans)), format_func=lambda i: _ui.rotulo_van(vans[i], varias),
                       key="van_chamada")
    van = vans[idx]
else:
    van = vans[0]
    st.caption(f"🚐 {_ui.rotulo_van(van, varias)}")
cid, van_id = van["cid"], van["id"]

# motorista/monitor: recados do gestor e contato rápido com ele
if not van["gestor"]:
    for x in repo.avisos_equipe(cid, van_id, hoje()).itertuples():
        st.markdown(f"<div class='ve-faixa'>📌 <b>Recado do gestor</b> <span class='ve-sub'>· "
                    f"{x.criado_em.astimezone(TZ):%d/%m %H:%M}</span><br>{_ui.sem_formula(_ui.esc(x.texto))}</div>",
                    unsafe_allow_html=True)
    tel_g = van.get("empresa_tel")
    if tel_g:
        from core.fmt import so_digitos
        g1, g2 = st.container(key="linha_gestor").columns(2)
        g1.link_button("Ligar para o gestor", f"tel:+55{so_digitos(tel_g)[-11:]}", icon=":material/call:",
                       width="stretch")
        lk_g = link_whats(tel_g, f"Olá! Aqui é da {van['nome']}.")
        if lk_g:
            g2.link_button("WhatsApp do gestor", lk_g, icon=":material/chat:", width="stretch")

a, b = st.columns([1, 1])
dia = a.date_input("Dia", value=hoje(), format="DD/MM/YYYY", label_visibility="collapsed")
padrao = "ida" if agora().hour < 11 or 13 <= agora().hour < 15 else "volta"
trecho = b.segmented_control("Trecho", ["ida", "volta"], default=padrao, label_visibility="collapsed",
                             format_func=lambda t: "🏠 → 🏫 Ida" if t == "ida" else "🏫 → 🏠 Volta") or padrao

df = repo.chamada_dia(cid, van_id, dia, trecho)
if df.empty:
    st.info("Nenhum aluno desta van neste trecho." + (" Coloque os alunos na van em **Alunos e responsáveis**."
                                                      if van["gestor"] else ""))
    st.stop()

turnos_presentes = [t for t in TURNOS if t in set(df["turno"])]
if len(turnos_presentes) > 1:
    sel = st.pills("Turno", turnos_presentes, default=turnos_presentes, selection_mode="multi",
                   format_func=TURNOS.get, label_visibility="collapsed") or turnos_presentes
    df = df[df["turno"].isin(sel)]

# avisos dos pais
avisos = df[df["avisou"]]
if not avisos.empty:
    st.warning("**Avisos de falta:** " + "; ".join(
        f"{r.nome}{' — ' + r.aviso_motivo if r.aviso_motivo else ''}" for r in avisos.itertuples()),
        icon=":material/notifications_active:")

vao = df[~df["avisou"] & (df["status"] != "faltou")]
sit = R.situacao(df, trecho)
if trecho == "ida":
    _ui.kpis([("Alunos no trecho", len(df)), ("Na van", len(sit["na_van"])), ("Na escola", len(sit["concluidos"])),
              ("Faltas / avisos", len(sit["ausentes"]))], destaque=None)
else:
    _ui.kpis([("Alunos no trecho", len(df)), ("Entregues", len(sit["concluidos"])),
              ("Faltam entregar", sit["pendentes"]), ("Faltas / avisos", len(sit["ausentes"]))], destaque=None)

# iniciar rota: registra a saída (os pais acompanham no app) e lista uma mensagem pronta no WhatsApp para o
# responsável de cada criança que vai hoje, na ordem da rota (o WhatsApp comum não permite envio automático em massa)
rota = repo.rota_status(van_id, dia, trecho)
inicio = rota["iniciada_em"] if rota else None
finalizada = rota["finalizada_em"] if rota else None
quem = u.get("nome") or u["email"]
apelido = repo.apelido_motorista(van_id, u["email"])
link_mapa = None
eh_hoje = dia == hoje()


def _marcar(pid, status):
    """Marca e, se a rota ainda não começou, já começa (o motorista não perde tempo com mais um toque)."""
    if eh_hoje and inicio is None and status in ("embarcou", "desembarcou"):
        repo.iniciar_rota(cid, van_id, dia, trecho, quem)
    repo.marcar(cid, van_id, pid, dia, trecho, status)
    st.session_state["_checar_fim"] = True


@st.dialog("Conferir antes de finalizar", width="small")
def _confirmar_fim(s: dict):
    st.error("**⚠️ Ainda tem criança pendente nesta rota.** Confira a van antes de finalizar.",
             icon=":material/warning:")
    if s["na_van"]:
        st.markdown(("**Ainda na van (não marcadas na escola):** " if trecho == "ida"
                     else "**Ainda não entregues:** ") + ", ".join(_ui.esc(n) for n in s["na_van"]))
    if s["a_buscar"]:
        st.markdown("**Não embarcaram e sem falta marcada:** " + ", ".join(_ui.esc(n) for n in s["a_buscar"]))
    ok = st.checkbox("Conferi a van — não ficou nenhuma criança", key="conf_fim_rota")
    a, b = st.columns(2)
    if a.button("Voltar", width="stretch", key="fim_voltar"):
        st.rerun()
    if b.button("Finalizar mesmo assim", type="primary", width="stretch", disabled=not ok, key="fim_confirma"):
        repo.finalizar_rota(cid, van_id, dia, trecho, quem, s["pendentes"])
        st.rerun()


# finaliza sozinha quando a última criança é concluída (só logo depois de uma marcação, para não fechar sem querer)
if st.session_state.pop("_checar_fim", False) and inicio is not None and finalizada is None and eh_hoje \
        and sit["pendentes"] == 0:
    repo.finalizar_rota(cid, van_id, dia, trecho, quem, 0)
    st.toast("Todas as crianças " + ("na escola" if trecho == "ida" else "entregues") + " — rota finalizada ✓")
    st.rerun()

_ui.manter_tela_ligada(eh_hoje and inicio is not None and finalizada is None)

if inicio is None:
    if eh_hoje and st.button(f"Iniciar rota — {'ida' if trecho == 'ida' else 'volta'}", key="ini_rota",
                             icon=":material/play_arrow:", width="stretch",
                             help="Registra a saída da van (os pais acompanham no app) e prepara as mensagens."):
        repo.iniciar_rota(cid, van_id, dia, trecho, quem)
        st.rerun()
elif finalizada is not None:
    pend_fim = rota.get("pendentes_ao_finalizar") or 0
    st.success(f"✅ Rota finalizada às {finalizada.astimezone(TZ):%H:%M}"
               + (f" por {rota['finalizada_por']}" if rota.get("finalizada_por") else "") + ".",
               icon=":material/flag:")
    if pend_fim:
        st.warning(f"Finalizada com {pend_fim} criança(s) pendente(s) — conferido pelo motorista/monitor.",
                   icon=":material/warning:")
    if st.button("Reabrir rota", type="tertiary", key="reabrir_rota"):
        repo.reabrir_rota(cid, van_id, dia, trecho)
        st.rerun()
else:
    st.success(f"Rota em andamento desde {inicio.astimezone(TZ):%H:%M} — os pais acompanham no app.",
               icon=":material/directions_bus:")
    with st.container(border=True, key="card_loc_chamada"):
        st.markdown("**📍 Localização ao vivo** <span class='ve-sub'>— cada família vê a van até o filho "
                    + ("chegar na escola" if trecho == "ida" else "ser entregue") + "</span>",
                    unsafe_allow_html=True)
        link_mapa = _ui.localizacao_ao_vivo(cid, van_id)
    vao_hoje = df[~df["avisou"] & (df["status"] != "faltou")]
    with st.expander(f"Avisar os responsáveis no WhatsApp ({len(vao_hoje)})"):
        st.caption("Toque em cada um: abre a conversa do responsável cadastrado com a mensagem pronta — é só enviar.")
        for pos, r in enumerate(vao_hoje.itertuples(), start=1):
            nome1 = r.nome.split()[0]
            msg = M.saindo(trecho, nome1, apelido, agora().hour, link_mapa,
                           parada=pos if trecho == "ida" else None, avisar_falta=trecho == "ida")
            lk = link_whats(r.telefone, msg)
            if lk:
                st.link_button(f"{pos}. {r.nome}", lk, icon=":material/chat:", width="stretch", key=f"zap_ini_{r.id}")
            else:
                st.button(f"{pos}. {r.nome} — sem WhatsApp cadastrado", disabled=True, width="stretch",
                          key=f"semzap_{r.id}")
    # ida: na porta da escola, um toque desembarca todos que estão na van (um botão por escola)
    if trecho == "ida":
        na_van = df[df["status"] == "embarcou"]
        for esc, g in na_van.groupby(na_van["escola"].fillna("escola"), sort=False):
            if st.button(f"Cheguei na {esc} — {len(g)} na escola", key=f"ok_escola_{abs(hash(esc))}",
                         icon=":material/school:", width="stretch"):
                repo.marcar_varios(cid, van_id, list(g["id"]), dia, trecho, "desembarcou")
                st.session_state["_checar_fim"] = True
                st.rerun()
    if st.button("Finalizar rota", key="fim_rota", icon=":material/flag:", width="stretch"):
        if sit["pendentes"]:
            _confirmar_fim(sit)
        else:
            repo.finalizar_rota(cid, van_id, dia, trecho, quem, 0)
            st.rerun()
    if st.button("Desfazer início da rota", type="tertiary", key="desfaz_inicio"):
        repo.parar_localizacao(cid, van_id)
        repo.desfazer_inicio_rota(cid, van_id, dia, trecho)
        st.rerun()

# recado rápido para todas as famílias desta van (aparece na área dos pais hoje)
with st.expander("Avisar todos os pais desta van", icon=":material/campaign:"):
    PRONTOS = ["Hoje a van vai atrasar uns 15 minutos.", "Hoje a van vai atrasar uns 30 minutos.",
               "Trânsito pesado — chegaremos um pouco mais tarde.", "Outro aviso…"]
    escolha_av = st.radio("Aviso", PRONTOS, key=f"av_pronto_{van_id}", label_visibility="collapsed")
    txt_av = st.text_input("Escreva o aviso", key=f"av_txt_{van_id}") if escolha_av == PRONTOS[-1] else escolha_av
    if st.button("Publicar para os pais", icon=":material/send:", key=f"av_pub_{van_id}", type="primary",
                 disabled=not (txt_av or "").strip()):
        repo.salvar_aviso(cid, "van", txt_av, u.get("nome") or u["email"], hoje(), van_id=van_id)
        st.toast("Aviso publicado — os pais da van já veem no app.")
    st.caption("Aparece hoje no topo da área da família de todos os alunos desta van.")

# rota no Google Maps
casas = [", ".join(x for x in (r.endereco, r.bairro) if x) for r in vao.itertuples() if r.endereco]
escolas = list(dict.fromkeys(e for e in vao["escola_endereco"] if e))
if trecho == "ida":
    rota_maps = link_maps_rota(casas + escolas[:-1], escolas[-1] if escolas else None)
else:
    rota_maps = link_maps_rota(escolas + casas[::-1][:-1] if escolas else casas[::-1][:-1],
                               casas[::-1][-1] if casas else None)
if rota_maps:
    st.link_button("Abrir rota no Google Maps", rota_maps, icon=":material/map:", width="stretch",
                   help="Na ordem da rota, sem quem avisou falta. O Maps aceita até 9 paradas.")
    if len(casas) + len(escolas) > 10:
        st.caption("A rota tem mais de 10 paradas: o Maps mostra as 9 primeiras e o destino.")

st.divider()
st.caption("🟡 mensagem para os pais · 🟢 " + ("embarcou / na escola" if trecho == "ida" else "entregue")
           + " · 🔴 faltou · 🔵 caminho até a casa")
FEITO = {"ida": "Na escola", "volta": "Entregue"}


def _ordem(r):
    """Quem ainda precisa de ação primeiro; concluídos e ausentes vão para o fim da lista."""
    s = r.status if isinstance(r.status, str) else None
    if R.nao_vai(r):
        return 3
    return {None: 0, "embarcou": 1, "desembarcou": 2}.get(s, 0)


for r in sorted(df.itertuples(), key=_ordem):
    st_atual = r.status if isinstance(r.status, str) else None
    nao_vai = R.nao_vai(r)
    with st.container(border=True, key=f"card_{'falta_' if nao_vai else ''}{r.id}"):
        rot = {"embarcou": "Na van", "desembarcou": FEITO[trecho] + " ✓", "faltou": "Faltou"}
        etiqueta = (_ui.tag(st_atual, rot[st_atual]) if st_atual
                    else _ui.tag("aviso", "Pais avisaram falta") if r.avisou else "")
        end = ", ".join(x for x in (r.endereco, r.bairro) if x)
        st.markdown(f"**{r.ordem_rota}. {_ui.esc(r.nome)}** {etiqueta}  \n"
                    f"<span class='ve-sub'>{_ui.esc(end or 'sem endereço')}"
                    f"{' · ' + _ui.esc(r.referencia) if r.referencia else ''} · {_ui.esc(r.escola or 'sem escola')}"
                    f"</span>", unsafe_allow_html=True)
        if r.observacoes:
            st.caption(f"⚠️ {r.observacoes}")
        if r.avisou:
            st.caption("📣 Os pais avisaram que não vai" + (f": {r.aviso_motivo}" if r.aviso_motivo else "") + ".")

        # já concluído / não vai: só o botão de desfazer
        if nao_vai:
            if r.avisou and st_atual is None:
                if st.button("Vai sim", key=f"desf_vai_{r.id}", width="stretch", icon=":material/undo:",
                             help="Os pais avisaram falta, mas a criança vai: tira o aviso deste trajeto."):
                    repo.desfazer_falta_trecho(cid, r.id, dia, trecho)
                    st.rerun()
            elif st.button("Desfazer falta", key=f"desf_falta_{r.id}", width="stretch", icon=":material/undo:"):
                _marcar(r.id, None)
                st.rerun()
            continue
        if st_atual == "desembarcou":
            if st.button("Desfazer", key=f"desf_ok_{r.id}", width="stretch", icon=":material/undo:",
                         help="Volta para " + ("\"na van\"" if trecho == "ida" else "\"não entregue\"") + "."):
                _marcar(r.id, "embarcou" if trecho == "ida" else None)
                st.rerun()
            continue
        nome1 = r.nome.split()[0]
        if st_atual == "embarcou":   # ida: está na van, a caminho da escola
            b1, b2 = st.container(key=f"linha_ok_{r.id}").columns(2)
            if b1.button("Na escola", key=f"ok_esc_{r.id}", width="stretch", icon=":material/school:",
                         help="Deixou na escola."):
                _marcar(r.id, "desembarcou")
                st.rerun()
            if b2.button("Não embarcou", key=f"desf_emb_{r.id}", width="stretch", icon=":material/undo:",
                         help="Desfaz o embarque."):
                _marcar(r.id, None)
                st.rerun()
            continue

        # 1) avisar (amarelo): só mensagem / com o link da van no mapa
        a1, a2 = st.container(key=f"linha_av_{r.id}").columns(2)
        link = link_whats(r.telefone, M.chegando(trecho, nome1, apelido, agora().hour))
        if link:
            a1.link_button("Avisar", link, icon=":material/chat:", width="stretch", key=f"zap_av_{r.id}",
                           help="\"Está chegando\" no WhatsApp do responsável.")
        else:
            a1.button("Avisar", key=f"zap_sem_{r.id}", disabled=True, width="stretch", icon=":material/chat:",
                      help="Cadastre o WhatsApp do responsável.")
        if link and link_mapa:
            a2.link_button("Avisar + local", link_whats(r.telefone, M.chegando(trecho, nome1, apelido,
                                                                                 agora().hour, link_mapa)),
                           icon=":material/share_location:", width="stretch", key=f"zap_loc_{r.id}",
                           help="Avisa que está chegando e manda o link da van no mapa.")
        else:
            a2.button("Avisar + local", key=f"zap_locsem_{r.id}", disabled=True, width="stretch",
                      icon=":material/share_location:",
                      help="Inicie a rota e ligue a localização ao vivo (no topo) para mandar o mapa."
                      if link else "Cadastre o WhatsApp do responsável.")

        # 2) embarcou (ida) / entregue (volta) · faltou · como chegar
        b1, b2, b3 = st.container(key=f"linha_ok_{r.id}").columns(3)
        if trecho == "ida":
            if b1.button("Embarcou", key=f"ok_emb_{r.id}", width="stretch", icon=":material/check_circle:",
                         help="Pegou a criança em casa — os pais acompanham a van até a escola."):
                _marcar(r.id, "embarcou")
                st.rerun()
        elif b1.button("Entregue", key=f"ok_ent_{r.id}", width="stretch", icon=":material/check_circle:",
                       help="Entregou em casa."):
            _marcar(r.id, "desembarcou")
            st.rerun()
        if b2.button("Faltou", key=f"falta_{r.id}", width="stretch", icon=":material/person_off:",
                     help="Marca a falta (dá para desfazer)."):
            _marcar(r.id, "faltou")
            st.rerun()
        if end:
            b3.link_button("Como chegar", "https://www.google.com/maps/dir/?api=1&travelmode=driving&destination="
                           + urllib.parse.quote(end), icon=":material/navigation:", width="stretch", key=f"nav_{r.id}",
                           help="Abre o Google Maps com o caminho até a casa.")
        else:
            b3.button("Como chegar", key=f"nav_sem_{r.id}", disabled=True, width="stretch",
                      icon=":material/navigation:", help="Cadastre o endereço do aluno.")

st.divider()
if van["gestor"]:   # motorista/monitor só opera a rota; a ordem é cadastro do gestor
    with st.expander("Ordem da rota"):
        st.caption("Defina a ordem de busca (1 = primeiro). Vale para a ida; a volta usa a ordem inversa.")
        todos = repo.passageiros(cid, van=van_id)
        ed = st.data_editor(todos[["id", "ordem_rota", "nome", "turno", "bairro"]].assign(turno=todos["turno"].map(TURNOS)),
                            hide_index=True, width="stretch", disabled=["nome", "turno", "bairro"],
                            column_order=["ordem_rota", "nome", "turno", "bairro"],
                            column_config={"ordem_rota": st.column_config.NumberColumn("Ordem", min_value=0, step=1),
                                           "nome": "Aluno", "turno": "Turno", "bairro": "Bairro"}, key=f"ordem_{van_id}")
        if st.button("Salvar ordem"):
            repo.salvar_ordem(cid, van_id, dict(zip(ed["id"].astype(str), ed["ordem_rota"].fillna(0))))
            st.toast("Ordem salva.")
            st.rerun()

with st.expander("Frequência do mês"):
    ini = inicio_mes(dia)
    fr = repo.frequencia(cid, ini, somar_meses(ini, 1), van=van_id)
    st.dataframe(fr, hide_index=True, width="stretch",
                 column_config={"nome": "Aluno", "presencas": "Presenças (trechos)", "faltas": "Faltas (trechos)"})
    st.caption(f"Contagem de {data_br(ini)} até hoje, por trecho (ida e volta contam separado).")
