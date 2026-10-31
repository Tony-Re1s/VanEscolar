"""Motorista contratado: alunos da(s) van(s) que dirige — contato, endereço e cuidados. Sem valores."""
import streamlit as st

from core import repo
from core.fmt import TURNOS, idade, link_whats
from telas import _ui

u = st.session_state["usuario"]
st.title("Meus alunos")

vans = [v for v in _ui.vans_acessiveis(u) if v["minha"]]
if not vans:
    st.info("Você não está como motorista de nenhuma van.")
    st.stop()
varias = len({v["cid"] for v in vans}) > 1

for v in vans:
    st.subheader(f"🚐 {_ui.rotulo_van(v, varias)}")
    df = repo.passageiros(v["cid"], van=v["id"])
    if df.empty:
        st.caption("Nenhum aluno nesta van ainda.")
        continue
    for r in df.itertuples():
        with st.container(border=True):
            st.markdown(f"**{_ui.esc(r.nome)}** <span class='ve-sub'>· {idade(r.data_nasc) or '—'} anos · "
                        f"{TURNOS.get(r.turno, '')} · {_ui.esc(r.escola or 'sem escola')}</span>  \n"
                        f"<span class='ve-sub'>📍 {_ui.esc(', '.join(x for x in (r.endereco, r.bairro) if x) or 'sem endereço')}"
                        f"{' · ' + _ui.esc(r.referencia) if r.referencia else ''}</span>  \n"
                        f"<span class='ve-sub'>👪 {_ui.esc(r.responsaveis or 'sem responsável')}</span>",
                        unsafe_allow_html=True)
            if r.observacoes:
                st.caption(f"⚠️ {r.observacoes}")
            link = link_whats(r.telefone_resp, f"Olá! Aqui é o motorista da van de {r.nome.split()[0]}.")
            if link:
                st.link_button("WhatsApp do responsável", link, icon=":material/chat:")
