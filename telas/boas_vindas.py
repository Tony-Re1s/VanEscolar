"""1º acesso: criar o cadastro de condutor (ou orientar o responsável)."""
import streamlit as st

from core import auth, repo

u = st.session_state["usuario"]

st.title("🚐 Bem-vindo ao VanEscolar")

if not u.get("filhos"):
    st.info("**É pai, mãe ou responsável?** Peça ao condutor da van para cadastrar o seu e-mail "
            f"(**{u['email']}**) no aluno. Depois é só entrar de novo para ver a área da família.")

aberto = auth.cfg("cadastro_aberto", True)
permitidos = [e.strip().lower() for e in (auth.cfg("condutores_permitidos") or [])]
if not (aberto or u.get("admin") or u["email"] in permitidos):
    st.warning("O cadastro de novos condutores está fechado no momento. Fale com o administrador.")
    st.stop()

st.subheader("Sou condutor — criar minha conta")
st.caption("Leva 1 minuto. Dá para mudar tudo depois em **Meu cadastro e van**.")
with st.form("novo_condutor"):
    nome = st.text_input("Seu nome (ou nome do transporte) *", value=u.get("nome") or "")
    c1, c2 = st.columns(2)
    telefone = c1.text_input("WhatsApp", placeholder="(11) 99999-9999")
    cnh = c2.text_input("CNH (opcional)")
    c3, c4, c5 = st.columns(3)
    veiculo = c3.text_input("Veículo", placeholder="Sprinter, Ducato…")
    placa = c4.text_input("Placa")
    capacidade = c5.number_input("Lugares", min_value=1, max_value=60, value=15)
    c6, c7 = st.columns(2)
    chave_pix = c6.text_input("Chave Pix (para os pais pagarem)")
    dia = c7.number_input("Vencimento padrão (dia)", min_value=1, max_value=28, value=10)
    ok = st.form_submit_button("Criar minha conta", type="primary", use_container_width=True)

if ok:
    if not nome.strip():
        st.error("Preencha o nome.")
        st.stop()
    repo.criar_condutor(u["id"], dict(nome=nome.strip(), telefone=telefone or None, cnh=cnh or None,
                                      veiculo=veiculo or None, placa=(placa or "").upper() or None,
                                      capacidade=int(capacidade), chave_pix=chave_pix or None,
                                      dia_vencimento=int(dia)))
    auth.perfil(u)
    st.success("Conta criada! Próximo passo: cadastrar as escolas e os alunos.")
    st.rerun()
