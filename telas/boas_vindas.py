"""1º acesso: criar a empresa (gestor). Só o essencial — vans, Pix e vencimento ficam para depois."""
import streamlit as st

from core import auth, repo

u = st.session_state["usuario"]

st.title("Bem-vindo ao Pequenos a Bordo")

if not u.get("filhos"):
    st.info("**É pai, mãe ou responsável?** Peça a quem cuida da van para cadastrar o seu e-mail "
            f"(**{u['email']}**) no aluno. **É motorista de uma van?** Peça ao gestor para cadastrar esse e-mail "
            "na sua van. Depois é só entrar de novo.", icon=":material/info:")

aberto = auth.cfg("cadastro_aberto", True)
permitidos = [e.strip().lower() for e in (auth.cfg("condutores_permitidos") or [])]
if not (aberto or u.get("admin") or u["email"] in permitidos):
    st.warning("O cadastro de novas empresas está fechado no momento. Fale com o administrador.")
    st.stop()

st.subheader("Criar minha empresa de transporte")
st.caption("Você vira o **gestor**: cadastra as vans, os motoristas, os alunos e cuida das mensalidades. "
           "Leva 30 segundos — o resto você completa depois.")
with st.form("nova_empresa"):
    nome = st.text_input("Seu nome ou nome do transporte *", value=u.get("nome") or "")
    telefone = st.text_input("WhatsApp", placeholder="(11) 99999-9999")
    dirige = st.checkbox("Eu também dirijo uma van", value=True,
                         help="Já cria a 'Van 1' com você de motorista. Dá para mudar em Vans e motoristas.")
    ok = st.form_submit_button("Criar", type="primary", use_container_width=True)

if ok:
    if not nome.strip():
        st.error("Preencha o nome.")
        st.stop()
    repo.criar_empresa(u["id"], u["email"], nome.strip(), telefone or None, dirige)
    auth.perfil(u)
    st.rerun()
