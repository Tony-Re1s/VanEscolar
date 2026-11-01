"""Avisos aos pais: o gestor escreve um recado que aparece na área da família — para todos, para uma van ou para
um aluno. (Opcional: abrir o WhatsApp de cada família com o mesmo texto.)"""
from datetime import timedelta

import streamlit as st

from core import repo
from core.fmt import TZ, data_br, hoje, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
u = st.session_state["usuario"]
cid = c["id"]
st.title("Avisos aos pais")
st.caption("O aviso aparece no topo da área da família (Meus filhos) de quem você escolher. Ex.: \"Amanhã não tem "
           "van por causa do feriado\", \"Hoje vou atrasar 15 minutos\".")

vans = repo.vans(cid)
alunos = repo.passageiros(cid)
ALVOS = {"todos": "Todas as famílias", "van": "Uma van", "aluno": "Um aluno"}

alvo = st.segmented_control("Para quem", list(ALVOS), format_func=ALVOS.get, default="todos", key="av_alvo") or "todos"
with st.form("aviso", clear_on_submit=True):
    van_id = aluno_id = None
    if alvo == "van":
        if vans.empty:
            st.info("Nenhuma van cadastrada.")
        else:
            van_id = st.selectbox("Van", list(vans["id"].astype(str)),
                                  format_func=lambda v: vans[vans["id"].astype(str) == v].iloc[0]["nome"])
    elif alvo == "aluno":
        if alunos.empty:
            st.info("Nenhum aluno cadastrado.")
        else:
            aluno_id = st.selectbox("Aluno", list(alunos["id"].astype(str)),
                                    format_func=lambda p: alunos[alunos["id"].astype(str) == p].iloc[0]["nome"])
    texto = st.text_area("Aviso *", max_chars=1000, placeholder="Ex.: Amanhã (sexta) não teremos van — feriado. "
                                                                "Bom descanso a todos!")
    a, b = st.columns(2)
    dias = a.selectbox("Mostrar por", [1, 3, 7, 15, 30], index=2, format_func=lambda d: f"{d} dia(s)")
    ok = st.form_submit_button("Publicar aviso", type="primary", icon=":material/campaign:")
if ok:
    if not texto.strip():
        st.error("Escreva o aviso.")
    elif (alvo == "van" and not van_id) or (alvo == "aluno" and not aluno_id):
        st.error("Escolha para quem é o aviso.")
    else:
        repo.salvar_aviso(cid, alvo, texto, u.get("nome") or u["email"], hoje() + timedelta(days=int(dias) - 1),
                          van_id, aluno_id)
        st.session_state["_ultimo_aviso"] = dict(alvo=alvo, van=van_id, aluno=aluno_id, texto=texto.strip())
        st.toast("Aviso publicado — já aparece para os pais.")
        st.rerun()

# depois de publicar: atalho para mandar também no WhatsApp de cada família
ult = st.session_state.get("_ultimo_aviso")
if ult and not alunos.empty:
    dest = alunos if ult["alvo"] == "todos" else \
        alunos[alunos["van_id"].astype(str) == ult["van"]] if ult["alvo"] == "van" else \
        alunos[alunos["id"].astype(str) == ult["aluno"]]
    dest = dest[dest["telefone_resp"].notna()]
    if not dest.empty:
        with st.expander(f"Mandar também no WhatsApp ({len(dest)} família(s))", icon=":material/chat:"):
            st.caption("Opcional: cada botão abre a conversa da família com o aviso pronto.")
            for r in dest.itertuples():
                lk = link_whats(r.telefone_resp, f"📣 {ult['texto']}")
                if lk:
                    st.link_button(r.nome, lk, icon=":material/send:", width="stretch")

st.subheader("Avisos publicados")
av = repo.avisos_empresa(cid)
if av.empty:
    st.caption("Nenhum aviso ainda.")
for r in av.itertuples():
    para = {"todos": "todas as famílias", "van": f"van {r.van}", "aluno": f"família de {r.aluno}"}[r.alvo]
    vence = r.ate is not None and r.ate < hoje()
    with st.container(border=True, key=f"card_aviso_{r.id}"):
        x1, x2 = st.columns([5, 1])
        x1.markdown(f"**Para {_ui.esc(para)}** <span class='ve-sub'>· {r.criado_em.astimezone(TZ):%d/%m %H:%M}"
                    + (f" · até {data_br(r.ate)}" if r.ate else "") + (" · encerrado" if vence else "")
                    + f"</span>  \n{_ui.sem_formula(_ui.esc(r.texto))}", unsafe_allow_html=True)
        if x2.button("Apagar", key=f"del_av_{r.id}", type="tertiary"):
            repo.excluir_aviso(cid, r.id)
            st.rerun()
