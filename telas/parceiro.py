"""Parceiros Turminha — o painel do parceiro: link de indicação, indicados, Bônus Parceiro e contrato."""
import urllib.parse
from datetime import datetime

import streamlit as st

from core import auth, parceiro as pc, repo
from core.fmt import TZ, brl, data_br, hoje
from telas import _ui

u = st.session_state["usuario"]
c = u.get("condutor")
HOJE = hoje()
emp = repo.empresa(c["id"]) if c else None
if not (u.get("admin") or pc.eh_parceiro(emp)):
    st.warning("Esta área é dos **Parceiros Turminha**.")
    st.stop()
if not emp:
    st.info("Você está como administrador, sem empresa. Os parceiros e os pagamentos ficam em **Promoções → Parceiros**.")
    st.stop()

repo.garantir_codigo_indicacao(emp["id"])
emp = repo.empresa(emp["id"])
codigo = emp.get("codigo_indicacao")
link_curto = f"turminhaabordo.com.br/?indicacao={codigo}"
link = f"https://{link_curto}"
aceite = emp.get("parceiro_contrato")
if isinstance(aceite, str):
    import json
    aceite = json.loads(aceite)


def _titular() -> dict:
    return dict(nome=auth.cfg("titular_nome") or "José Anthony Reis Lopes", doc=auth.cfg("titular_doc"),
                endereco=auth.cfg("titular_endereco"))


# ---------------------------------------------------------------- 1º acesso: aceite do contrato
if not aceite:
    st.title("Bem-vindo, parceiro!")
    st.markdown("<div class='ve-faixa'>Antes de começar, leia e aceite o contrato do programa "
                "<b>Parceiros Turminha</b>.</div>", unsafe_allow_html=True)
    with st.form("aceite"):
        nome = st.text_input("Nome completo ou razão social *", value=emp.get("nome") or "")
        a, b = st.container(key="linha_parc1").columns(2)
        doc = a.text_input("CPF ou CNPJ *")
        whats = b.text_input("WhatsApp *", value=emp.get("telefone") or "")
        endereco = st.text_input("Endereço *")
        pix = st.text_input("Chave Pix para receber o bônus *", value=emp.get("chave_pix") or "",
                            placeholder="CPF, e-mail, celular ou chave aleatória")
        dados = dict(nome=nome, doc=doc, endereco=endereco, email=u["email"], whatsapp=whats, pix=pix)
        with st.container(border=True, height=260):
            st.markdown(pc.contrato_texto(_titular(), dados))
        ok_check = st.checkbox("Li e aceito o contrato. Entendo que este aceite eletrônico tem validade de assinatura.")
        assinar = st.form_submit_button("Aceitar e assinar", type="primary", width="stretch", icon=":material/draw:")
    st.caption("Registramos o seu login Google, data, hora e IP do aparelho. Você baixa uma cópia em PDF depois.")
    if assinar:
        faltando = [r for r, v in (("nome", nome), ("CPF/CNPJ", doc), ("WhatsApp", whats), ("endereço", endereco),
                                   ("chave Pix", pix)) if not str(v).strip()]
        if faltando:
            st.error("Preencha: " + ", ".join(faltando) + ".")
        elif not ok_check:
            st.error("Marque que leu e aceita o contrato.")
        else:
            ip = (st.context.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or None
            dados.update(aceito_em=datetime.now(TZ).strftime("%d/%m/%Y %H:%M:%S"), ip=ip)
            pc.salvar_aceite(emp["id"], dados, pc.contrato_texto(_titular(), dados))
            st.toast("Contrato assinado. Bem-vindo! 🤝")
            st.rerun()
    st.stop()

# ---------------------------------------------------------------- painel
st.title("Parceiros Turminha")
st.markdown("<div class='ve-faixa'>🤝 Você ganha um <b>bônus</b> por cada assinante que entrar pelo seu link — "
            f"pago por Pix até o dia 10 de cada mês, até <b>{data_br(pc.FIM)}</b>.</div>", unsafe_allow_html=True)
r = pc.resumo(emp["id"], HOJE)
ind = pc.indicados(emp["id"])
ativos = int(((ind["plano_tipo"] == "pago") & (ind["plano_ate"] >= HOJE) & ind["ativo"]).sum()) if len(ind) else 0
_ui.kpis([("A receber", brl(float(r.get("liberado") or 0)),
           f"até {data_br(r['prazo'])}" if r.get("prazo") else "liberado até agora"),
          ("Assinantes ativos", str(ativos), f"de {len(ind)} indicado{'s' if len(ind) != 1 else ''}"),
          ("Já recebido", brl(float(r.get("recebido") or 0)),
           f"+ {brl(float(r['aguardando']))} aguardando 7 dias" if float(r.get("aguardando") or 0) else "")])

st.subheader("Seu link")
st.code(link_curto, language=None)
msg = ("Oi! Conhece o Turminha a Bordo? É um app pro tio e a tia da van escolar: alunos, rota com aviso pros pais no "
       f"WhatsApp e cobrança das mensalidades, tudo no celular 🚐 Entrando por este link você ganha dias grátis "
       f"pra testar: {link}")
a, b = st.container(key="linha_parc2").columns(2)
a.link_button("Mandar no WhatsApp", f"https://wa.me/?text={urllib.parse.quote(msg)}", icon=":material/send:",
              type="primary", width="stretch")
with b.popover("Texto pronto", icon=":material/content_copy:", width="stretch"):
    st.code(msg, language=None, wrap_lines=True)
st.caption("Quem abre o link já entra com a sua indicação — não precisa digitar código.")

st.subheader("Seus indicados")
if ind.empty:
    st.caption("Ninguém ainda — mande o link para os tios e tias da van!")
for x in ind.to_dict("records"):
    em_dia = x["plano_tipo"] == "pago" and x["plano_ate"] and x["plano_ate"] >= HOJE and x["ativo"]
    if em_dia:
        k, sit = "pago", f"{'Mensal' if (x['periodo'] or 'mensal') == 'mensal' else str(x['periodo']).capitalize()} · ativo"
    elif x["plano_tipo"] == "teste" and x["plano_ate"] and x["plano_ate"] >= HOJE:
        k, sit = "embarcou", f"Em teste até {data_br(x['plano_ate'])}"
    elif float(x["bonus"] or 0) > 0:
        k, sit = "faltou", "Saiu"
    else:
        k, sit = "aberto", "Não assinou"
    bonus = brl(float(x["bonus"])) if float(x["bonus"] or 0) else "—"
    st.markdown(_ui.sem_formula(f"**{_ui.esc(pc.nome_curto(x['nome']))}** {_ui.tag(k, sit)} "
                f"<span class='ve-sub' style='float:right'>{_ui.esc(bonus)}</span>"), unsafe_allow_html=True)

ext = pc.extrato(emp["id"])
with st.expander(f"Extrato do bônus ({len(ext)})"):
    if ext.empty:
        st.caption("O bônus aparece aqui quando um indicado paga a mensalidade.")
    for x in ext.to_dict("records"):
        if x["estornado"]:
            k, sit = "faltou", "estornado"
        elif x["pago_em"]:
            k, sit = "pago", f"pago {data_br(x['pago_em'])}"
        elif x["libera_em"] > HOJE:
            k, sit = "embarcou", f"libera {data_br(x['libera_em'])}"
        else:
            k, sit = "aberto", f"a pagar até {data_br(pc.dia_de_pagar(x['libera_em']))}"
        st.markdown(_ui.sem_formula(f"**{_ui.esc(brl(float(x['valor'])))}** · {_ui.esc(pc.nome_curto(x['cliente']))} "
                    f"{_ui.tag(k, sit)}<br><span class='ve-sub'>{data_br(x['pago_cliente'])} · "
                    f"{_ui.esc(pc.TIPOS.get(x['tipo'], x['tipo']))}</span>"), unsafe_allow_html=True)

with st.expander("Regras e contrato"):
    st.markdown("- **Mensal:** R$ 10 na 1ª mensalidade paga + 20% de cada mensalidade a partir da 2ª\n"
                "- **Trimestral, semestral ou anual:** 1 mensalidade cheia + 20% dos outros meses\n"
                "- **Renovação:** 20% · o teste grátis não gera bônus\n"
                "- Liberado 7 dias depois do pagamento · Pix até o dia 10 do mês seguinte\n"
                f"- Vale para pagamentos até {data_br(pc.FIM)}")
    st.caption(f"Contrato assinado em {aceite.get('aceito_em')} · código de verificação {aceite.get('codigo')}")
    texto = pc.contrato_texto(_titular(), aceite)
    st.download_button("Baixar o contrato (PDF)", pc.contrato_pdf(texto, aceite), "contrato-parceiro-turminha.pdf",
                       "application/pdf", icon=":material/download:")

with st.expander("Minha chave Pix"):
    with st.form("pix"):
        nova = st.text_input("Chave Pix para receber o bônus", value=emp.get("chave_pix") or "")
        if st.form_submit_button("Salvar"):
            repo.salvar_chave_pix(emp["id"], nova)
            st.toast("Chave Pix salva.")
            st.rerun()
