"""Aprenda a usar: vídeos curtos de cada tarefa, gravados do próprio app."""
import streamlit as st

from telas import _ui

st.title("Aprenda a usar")
st.caption("Vídeos de menos de 1 minuto, gravados no próprio app.")
for nome, (titulo, sub) in _ui.TUTORIAIS.items():
    arq = _ui._arquivo_tutorial(nome)
    if not arq:
        continue
    with st.expander(f"**{titulo}** · {sub}", icon=":material/play_circle:"):
        st.video(str(arq), muted=True)
st.page_link("telas/fale_conosco.py", label="Ainda com dúvida? Fale com a gente", icon=":material/forum:")
