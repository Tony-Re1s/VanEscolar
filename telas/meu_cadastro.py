"""Minha empresa: dados do gestor, Pix e vencimento padrão das mensalidades."""
import streamlit as st

from core import auth, repo
from core import contrato as ct
from telas._ui import exigir_condutor

c = exigir_condutor()
st.title("Minha empresa")

with st.form("empresa"):
    nome = st.text_input("Nome / nome do transporte *", value=c["nome"])
    t1, t2 = st.columns(2)
    telefone = t1.text_input("WhatsApp", value=c.get("telefone") or "")
    apelido = t2.text_input("Como as famílias te chamam", value=c.get("apelido") or "", placeholder="Tio Jô, Tia Rose…",
                            help="Vai nas mensagens da rota: \"O tio Jô está a caminho para buscar a Helena\". "
                                 "Vale para as vans que você mesmo dirige.")
    c1, c2 = st.columns(2)
    chave_pix = c1.text_input("Chave Pix", value=c.get("chave_pix") or "",
                              help="Aparece para os pais na área da família e na mensagem de cobrança.")
    dia = c2.number_input("Vencimento padrão (dia)", 1, 28, int(c.get("dia_vencimento") or 10),
                          help="Vale para alunos sem dia próprio. Mensalidades já geradas não mudam.")
    ok = st.form_submit_button("Salvar", type="primary")

if ok:
    if not nome.strip():
        st.error("Preencha o nome.")
        st.stop()
    repo.atualizar_empresa(c["id"], dict(nome=nome.strip(), telefone=telefone or None, chave_pix=chave_pix or None,
                                         dia_vencimento=int(dia), apelido=apelido))
    auth.perfil(st.session_state["usuario"])
    st.success("Salvo.")
    st.rerun()

st.divider()
st.subheader("Receber as mensalidades pelo Asaas")
from core import planos as _pl  # noqa: E402
from core.asaas import Asaas, AsaasErro  # noqa: E402
from core.fmt import hoje as _hoje  # noqa: E402
from telas import _ui  # noqa: E402

_emp = repo.empresa(c["id"])
if not _ui.recurso_liberado("cobranca_pais", c["id"]):
    _ui.em_breve("cobranca_pais")
elif not _pl.tem_cobranca_auto(_emp, _hoje()):
    st.info("Gere **Pix e boleto** para os pais com **baixa automática** quando eles pagam. Disponível nos planos "
            "com cobrança automática (ex.: **Pro** e **Frota**).", icon=":material/workspace_premium:")
    st.page_link("telas/meu_plano.py", label="Ver planos", icon=":material/upgrade:")
elif _emp.get("asaas_gestor_chave"):
    amb = "produção" if (_emp.get("asaas_gestor_ambiente") or "producao") == "producao" else "testes (sandbox)"
    st.success(f"Conta Asaas conectada ({amb}). Escolha a forma de cobrança de cada aluno em **Mensalidades**. "
               "O dinheiro cai direto na sua conta Asaas.", icon=":material/check_circle:")
    if st.button("Desconectar o Asaas", type="tertiary", icon=":material/link_off:"):
        repo.desconectar_asaas_gestor(c["id"])
        st.rerun()
else:
    st.caption("Opcional. Você continua podendo cobrar do seu jeito e dar baixa à mão — e escolhe, aluno por aluno, "
               "quem paga pelo Asaas (Pix/boleto todo mês ou assinatura automática). O dinheiro cai na **sua** conta "
               "Asaas; a taxa do Asaas é cobrada por eles.")
    with st.form("asaas_gestor"):
        chave = st.text_input("Chave da API do seu Asaas", type="password",
                              help="No Asaas: Integrações → Chaves de API → Gerar chave. Começa com $aact_.")
        amb = st.radio("Conta", ["producao", "sandbox"], horizontal=True,
                       format_func={"producao": "Produção (de verdade)", "sandbox": "Testes (sandbox)"}.get)
        if st.form_submit_button("Conectar", type="primary", icon=":material/link:"):
            k = chave.strip()
            if not k.startswith("$aact_"):
                st.error("Essa chave não parece do Asaas (começa com $aact_).")
            else:
                try:
                    base = None
                    try:
                        base = st.secrets["asaas"].get("base_url_gestor")
                    except Exception:  # noqa: BLE001
                        pass
                    Asaas(k, amb, base).testar()
                    repo.conectar_asaas_gestor(c["id"], _ui.cifrar_chave(k), amb)
                    st.toast("Asaas conectado! ✅")
                    st.rerun()
                except AsaasErro as e:
                    st.error(f"Não consegui conectar: {e}")

if (c.get("modo") or "completo") != "facil":      # no modo fácil a tela de vans não aparece no menu
    st.page_link("telas/vans.py", label="Vans e motoristas", icon=":material/airport_shuttle:")

st.divider()
st.subheader("Contrato")
st.caption("Os responsáveis leem, preenchem os dados deles (aluno, escola, CPF, telefone, endereço, local) e assinam "
           "pelo app. Você contra-assina em **Alunos e responsáveis → Contratos**. Mudanças aqui valem para os "
           "próximos contratos — os já assinados não mudam.")
emp = repo.empresa(c["id"])
with st.form("contrato_modelo"):
    a, b, cc = st.columns([2, 1, 1])
    razao = a.text_input("Nome da contratada no contrato", value=emp.get("razao_social") or c["nome"],
                         help="Razão social ou nome fantasia, como deve sair no contrato.")
    cnpj = b.text_input("CNPJ", value=emp.get("cnpj") or "", placeholder="00.000.000/0001-00")
    cidade = cc.text_input("Cidade (local)", value=emp.get("cidade") or "", placeholder="São Paulo")
    clausulas = st.text_area("Cláusulas 1 a 7", value=ct.clausulas(emp), height=380,
                             help="A cláusula 8 (dados do aluno e do responsável) e as assinaturas o app monta sozinho.")
    x1, x2 = st.columns(2)
    salvar = x1.form_submit_button("Salvar contrato", type="primary")
    padrao = x2.form_submit_button("Voltar às cláusulas padrão")
if salvar or padrao:
    txt = None if padrao or clausulas.strip() == ct.CLAUSULAS_PADRAO.strip() else clausulas.strip()
    repo.atualizar_dados_contrato(c["id"], dict(razao_social=razao.strip() or None, cnpj=cnpj.strip() or None,
                                                cidade=cidade.strip() or None, contrato_clausulas=txt))
    st.toast("Contrato salvo.")
    st.rerun()
with st.expander("Ver como o responsável vai ver"):
    st.markdown(f"**{ct.TITULO}**")
    st.markdown(ct.preambulo(emp))
    st.text(ct.clausulas(emp))
