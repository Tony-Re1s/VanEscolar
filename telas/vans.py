"""Vans da empresa e quem dirige cada uma."""
import streamlit as st

from core import auth, repo
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
u = st.session_state["usuario"]
cid = c["id"]
st.title("Vans e motoristas")
st.caption("O motorista entra com o **e-mail do Google** cadastrado aqui e vê **só a van dele**: rota, chamada e os "
           "alunos (sem mensalidades nem financeiro).")

df = repo.vans(cid, so_ativas=False)

from core.fmt import link_whats

ac = repo.acessos(list(df["motorista_email"].dropna())) if not df.empty else {}
for v in df.itertuples():
    eu = (v.motorista_email or "") == u["email"]
    quem = "você" if eu else (v.motorista_nome or "sem motorista")
    with st.container(border=True, key=f"card_{v.id}"):
        st.markdown(f"**{_ui.esc(v.nome)}** {'' if v.ativo else '· 🔴 inativa'}  \n"
                    f"<span class='ve-sub'>{_ui.esc(v.veiculo or 'veículo não informado')} · "
                    f"{_ui.esc(v.placa or 'sem placa')} · {v.capacidade} lugares · {v.alunos} aluno(s) · "
                    f"motorista: {_ui.esc(quem)}"
                    f"{'' if eu or not v.motorista_email else ' (' + _ui.esc(v.motorista_email) + ')'}</span>"
                    + ("" if eu or not v.motorista_email else " " + _ui.selo_acesso(v.motorista_email, ac)),
                    unsafe_allow_html=True)
        if not eu and v.motorista_email:
            msg = (f"Olá, {(v.motorista_nome or '').split(' ')[0] or 'tudo bem'}! Você foi cadastrado(a) como motorista "
                   f"da {v.nome} no app Pequenos a Bordo ({c['nome']}). Acesse {_ui.APP_URL} e clique em "
                   f"\"Entrar com Google\" usando o e-mail {v.motorista_email}. Lá você vê a rota, faz a chamada, "
                   "inicia a rota e avisa os pais. 🚐")
            lk = link_whats(v.motorista_telefone, msg)
            if lk:
                st.link_button("Convidar no WhatsApp", lk, icon=":material/send:")
            else:
                st.caption("Cadastre o WhatsApp do motorista para enviar o convite.")
if not df.empty and any((e or "") != u["email"] for e in df["motorista_email"].dropna()):
    _ui.aviso_modo_teste()

NOVA = "➕ Nova van"
opcoes = [NOVA] + [r.nome for r in df.itertuples()]
st.divider()
escolha = st.selectbox("Cadastrar / editar", opcoes, index=0)
v = None if escolha == NOVA else df.iloc[opcoes.index(escolha) - 1].to_dict()
g = (v or {}).get
eu_dirijo_atual = (g("motorista_email") or "") == u["email"] if v else df.empty

eu_dirijo = st.toggle("Eu dirijo esta van", value=eu_dirijo_atual, key=f"eu_dirijo_{escolha}")

with st.form("van", clear_on_submit=v is None):
    nome = st.text_input("Apelido da van *", value=g("nome") or f"Van {len(df) + 1}",
                         help="Como você chama a van no dia a dia: Van 1, Sprinter branca, Van da manhã…")
    a, b, cc = st.columns(3)
    veiculo = a.text_input("Veículo", value=g("veiculo") or "", placeholder="Sprinter, Ducato…")
    placa = b.text_input("Placa", value=g("placa") or "")
    capacidade = cc.number_input("Lugares", 1, 60, int(g("capacidade") or 15))
    st.markdown("**Motorista**" + (" — você" if eu_dirijo else ""))
    m1, m2 = st.columns(2)
    mot_nome = m1.text_input("Nome do motorista", value="" if eu_dirijo_atual else (g("motorista_nome") or ""),
                             disabled=eu_dirijo)
    mot_email = m2.text_input("E-mail do Google do motorista", value="" if eu_dirijo_atual else
                              (g("motorista_email") or ""), disabled=eu_dirijo, placeholder="nome@gmail.com")
    m3, m4 = st.columns(2)
    mot_tel = m3.text_input("WhatsApp do motorista", value=g("motorista_telefone") or "",
                            help="Aparece para os pais como contato da van.")
    mot_cnh = m4.text_input("CNH (opcional)", value=g("motorista_cnh") or "")
    ativo = st.checkbox("Van ativa", value=bool(g("ativo") if v else True))
    ok = st.form_submit_button("Salvar van", type="primary")

if ok:
    if not nome.strip():
        st.error("Preencha o apelido da van.")
        st.stop()
    if not eu_dirijo and mot_email and "@" not in mot_email:
        st.error("E-mail do motorista inválido.")
        st.stop()
    dados = dict(nome=nome.strip(), veiculo=veiculo or None, placa=placa, capacidade=int(capacidade),
                 motorista_nome=(c["nome"] if eu_dirijo else (mot_nome or None)),
                 motorista_email=(u["email"] if eu_dirijo else (mot_email or None)),
                 motorista_telefone=(mot_tel or (c.get("telefone") if eu_dirijo else None)) or None,
                 motorista_cnh=mot_cnh or None, ativo=ativo)
    repo.salvar_van(cid, dados, vid=g("id"))
    auth.perfil(u)
    st.toast("Van salva." + ("" if eu_dirijo or not mot_email else
                             f" Peça para {mot_nome or 'o motorista'} entrar no app com {mot_email}."))
    st.rerun()
