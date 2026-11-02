"""Modo fácil — Rota: iniciar a rota e avisar cada família no WhatsApp (só a mensagem, ou com o link da van no mapa)."""
import streamlit as st

from core import mensagens as M, repo
from core.fmt import TZ, agora, hoje, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
u = st.session_state["usuario"]
cid = c["id"]

if _ui.aviso_pausa(c):
    st.stop()
vans = repo.vans(cid)
if vans.empty:      # modo fácil: ninguém precisa cadastrar van antes — cria a "Van 1"
    repo.salvar_van(cid, dict(nome="Van 1", veiculo=None, placa=None, capacidade=15, motorista_nome=c["nome"],
                              motorista_email=u["email"], motorista_telefone=c.get("telefone"), motorista_cnh=None,
                              ativo=True))
    vans = repo.vans(cid)

st.title("Rota")
_ui.guia(c, "telas/facil_rota.py")
a, b = st.container(key="linha_frota_top").columns([1, 1], vertical_alignment="center")
if len(vans) > 1:
    van_id = a.selectbox("Van", list(vans["id"].astype(str)), label_visibility="collapsed",
                         format_func=lambda v: vans[vans["id"].astype(str) == v].iloc[0]["nome"])
else:
    van_id = str(vans.iloc[0]["id"])
trecho = (b if len(vans) > 1 else st).segmented_control(
    "Trecho", ["ida", "volta"], format_func={"ida": "🏠→🏫 Ida", "volta": "🏫→🏠 Volta"}.get,
    default="ida" if agora().hour < 11 else "volta", label_visibility="collapsed", width="stretch",
    key="frota_trecho") or ("ida" if agora().hour < 11 else "volta")

dia = hoje()
df = repo.chamada_dia(cid, van_id, dia, trecho)
if df.empty:
    st.info("Nenhum aluno nesta van ainda. Cadastre em **Alunos** — leva 10 segundos por aluno.",
            icon=":material/person_add:")
    st.page_link("telas/facil_alunos.py", label="Cadastrar alunos", icon=":material/groups:")
    st.stop()

# 1) iniciar rota (os pais veem no app que a van saiu)
rota = repo.rota_status(van_id, dia, trecho)
inicio = rota["iniciada_em"] if rota else None
finalizada = rota["finalizada_em"] if rota else None
_ui.manter_tela_ligada(inicio is not None and finalizada is None)
if inicio is None:
    if st.button(f"Iniciar rota — {'ida' if trecho == 'ida' else 'volta'}", key="ini_rota",
                 icon=":material/play_arrow:", width="stretch"):
        repo.iniciar_rota(cid, van_id, dia, trecho, u.get("nome") or u["email"])
        st.rerun()
elif finalizada is not None:
    st.success(f"✅ Rota finalizada às {finalizada.astimezone(TZ):%H:%M}.", icon=":material/flag:")
else:
    st.success(f"Rota iniciada às {inicio.astimezone(TZ):%H:%M}.", icon=":material/directions_bus:")

# 2) localização ao vivo (opcional) — só com a rota em andamento
link = None
if inicio is not None and finalizada is None:
    with st.container(border=True, key="card_loc_facil"):
        st.markdown("**📍 Localização ao vivo** <span class='ve-sub'>— os pais veem a van no mapa pelo link</span>",
                    unsafe_allow_html=True)
        link = _ui.localizacao_ao_vivo(cid, van_id)

# 3) avisar cada família
vao = df[~df["avisou"] & (df["status"] != "faltou")]
faltas = df[df["avisou"] | (df["status"] == "faltou")]
st.subheader(f"Avisar as famílias ({len(vao)})")
apelido = repo.apelido_motorista(van_id, u["email"])
if not apelido:
    st.caption("💡 Coloque como as famílias te chamam (ex.: Tio Jô) em **Minha empresa**.")
hora = agora().hour
for pos, r in enumerate(vao.itertuples(), start=1):
    nome1 = r.nome.split()[0]
    msg = M.saindo(trecho, nome1, apelido, hora)
    with st.container(border=True, key=f"card_fam_{r.id}"):
        st.markdown(f"**{pos}. {_ui.esc(r.nome)}**" + ("" if r.telefone else
                    " <span class='ve-sub'>· sem WhatsApp do responsável</span>"), unsafe_allow_html=True)
        x1, x2 = st.container(key=f"linha_fam_{r.id}").columns(2)
        so_msg = link_whats(r.telefone, msg)
        com_loc = link_whats(r.telefone, M.saindo(trecho, nome1, apelido, hora, link)) if link else None
        if so_msg:
            x1.link_button("Estou a caminho", so_msg, icon=":material/airport_shuttle:", width="stretch",
                           key=f"zap_sm_{r.id}")
        else:
            x1.button("Estou a caminho", key=f"zap_smsem_{r.id}", disabled=True, width="stretch",
                      icon=":material/airport_shuttle:")
        if com_loc:
            x2.link_button("Com localização", com_loc, icon=":material/share_location:", width="stretch",
                           key=f"zap_cl_{r.id}")
        else:
            x2.button("Com localização", key=f"zap_clsem_{r.id}", disabled=True, width="stretch",
                      icon=":material/share_location:",
                      help=("Inicie a rota e ligue a localização ao vivo." if r.telefone
                            else "Cadastre o WhatsApp do responsável."))
if not faltas.empty:
    st.caption("Não vão hoje: " + ", ".join(faltas["nome"]))

if inicio is not None and finalizada is None:
    st.divider()
    if st.button("Finalizar rota", key="fim_rota", icon=":material/flag:", width="stretch",
                 help="Fecha a rota e para a localização ao vivo (os pais deixam de ver a van)."):
        repo.finalizar_rota(cid, van_id, dia, trecho, u.get("nome") or u["email"], 0)
        st.toast("Rota finalizada.")
        st.rerun()
    if st.button("Desfazer início", type="tertiary"):
        repo.parar_localizacao(cid, van_id)
        repo.desfazer_inicio_rota(cid, van_id, dia, trecho)
        st.rerun()
elif finalizada is not None:
    if st.button("Reabrir rota", type="tertiary"):
        repo.reabrir_rota(cid, van_id, dia, trecho)
        st.rerun()
