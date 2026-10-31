"""Rota do dia e chamada (embarque / desembarque / falta)."""
import streamlit as st

from core import repo
from core.fmt import TURNOS, agora, data_br, hoje, inicio_mes, link_maps_rota, link_whats, somar_meses
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
st.title("Rota e chamada")

a, b = st.columns([1, 1])
dia = a.date_input("Dia", value=hoje(), format="DD/MM/YYYY", label_visibility="collapsed")
padrao = "ida" if agora().hour < 11 or 13 <= agora().hour < 15 else "volta"
trecho = b.segmented_control("Trecho", ["ida", "volta"], default=padrao, label_visibility="collapsed",
                             format_func=lambda t: "🏠 → 🏫 Ida" if t == "ida" else "🏫 → 🏠 Volta") or padrao

df = repo.chamada_dia(cid, dia, trecho)
if df.empty:
    st.info("Nenhum aluno neste trecho. Cadastre alunos em **Alunos e responsáveis**.")
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
n_emb = df["status"].isin(["embarcou", "desembarcou"]).sum()
n_des = (df["status"] == "desembarcou").sum()
_ui.kpis([("Alunos no trecho", len(df)), ("Embarcaram", int(n_emb)), ("Desembarcaram", int(n_des)),
          ("Faltas / avisos", int(((df["status"] == "faltou") | df["avisou"]).sum()))], destaque=None)

# rota no Google Maps
casas = [", ".join(x for x in (r.endereco, r.bairro) if x) for r in vao.itertuples() if r.endereco]
escolas = list(dict.fromkeys(e for e in vao["escola_endereco"] if e))
if trecho == "ida":
    rota = link_maps_rota(casas + escolas[:-1], escolas[-1] if escolas else None)
else:
    rota = link_maps_rota(escolas + casas[::-1][:-1] if escolas else casas[::-1][:-1],
                          casas[::-1][-1] if casas else None)
if rota:
    st.link_button("Abrir rota no Google Maps", rota, icon=":material/map:", use_container_width=True,
                   help="Na ordem da rota, sem quem avisou falta. O Maps aceita até 9 paradas.")
    if len(casas) + len(escolas) > 10:
        st.caption("A rota tem mais de 10 paradas: o Maps mostra as 9 primeiras e o destino.")

st.divider()
BOT = {"ida": [("embarcou", "Embarcou"), ("desembarcou", "Na escola"), ("faltou", "Faltou")],
       "volta": [("embarcou", "Embarcou"), ("desembarcou", "Entregue"), ("faltou", "Faltou")]}
for r in df.itertuples():
    with st.container(border=True):
        st_atual = r.status if isinstance(r.status, str) else None
        etiqueta = (_ui.tag(st_atual, _ui.ROTULO_CHAM[st_atual]) if st_atual
                    else _ui.tag("aviso", "Avisou falta") if r.avisou else "")
        st.markdown(f"**{r.ordem_rota}. {_ui.esc(r.nome)}** {etiqueta}  \n"
                    f"<span class='ve-sub'>{_ui.esc(', '.join(x for x in (r.endereco, r.bairro) if x) or 'sem endereço')}"
                    f"{' · ' + _ui.esc(r.referencia) if r.referencia else ''} · {_ui.esc(r.escola or 'sem escola')}"
                    f"</span>", unsafe_allow_html=True)
        if r.observacoes:
            st.caption(f"⚠️ {r.observacoes}")
        cols = st.container(key=f"linha_{r.id}").columns(4)
        for col, (k, rot) in zip(cols, BOT[trecho]):
            if col.button(rot, key=f"{k}_{r.id}", use_container_width=True,
                          type="primary" if st_atual == k else "secondary"):
                repo.marcar(cid, r.id, dia, trecho, None if st_atual == k else k)
                st.rerun()
        msg = ("Bom dia! A van está chegando para buscar " if trecho == "ida" else "Olá! A van está chegando com ")
        link = link_whats(r.telefone, msg + f"{r.nome.split()[0]}. 🚐")
        if link:
            cols[3].link_button("Avisar", link, icon=":material/chat:", use_container_width=True)

st.divider()
with st.expander("Ordem da rota"):
    st.caption("Defina a ordem de busca (1 = primeiro). Vale para a ida; a volta usa a ordem inversa.")
    todos = repo.passageiros(cid)
    ed = st.data_editor(todos[["id", "ordem_rota", "nome", "turno", "bairro"]].assign(turno=todos["turno"].map(TURNOS)),
                        hide_index=True, use_container_width=True, disabled=["nome", "turno", "bairro"],
                        column_order=["ordem_rota", "nome", "turno", "bairro"],
                        column_config={"ordem_rota": st.column_config.NumberColumn("Ordem", min_value=0, step=1),
                                       "nome": "Aluno", "turno": "Turno", "bairro": "Bairro"}, key="ordem_ed")
    if st.button("Salvar ordem"):
        repo.salvar_ordem(cid, dict(zip(ed["id"].astype(str), ed["ordem_rota"].fillna(0))))
        st.toast("Ordem salva.")
        st.rerun()

with st.expander("Frequência do mês"):
    ini = inicio_mes(dia)
    fr = repo.frequencia(cid, ini, somar_meses(ini, 1))
    st.dataframe(fr, hide_index=True, use_container_width=True,
                 column_config={"nome": "Aluno", "presencas": "Presenças (trechos)", "faltas": "Faltas (trechos)"})
    st.caption(f"Contagem de {data_br(ini)} até hoje, por trecho (ida e volta contam separado).")
