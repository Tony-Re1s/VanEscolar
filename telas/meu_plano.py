"""Meu plano: plano em vigor, uso (vans/alunos) e troca de plano."""
import streamlit as st

from core import auth, planos as pl, repo
from core.fmt import data_br, hoje, link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
emp = repo.empresa(c["id"])
atual = pl.plano_da_empresa(emp, hoje())
p = pl.PLANOS[atual]
uso = repo.uso_empresa(c["id"])

st.title("Meu plano")


def _uso(n, lim):
    return f"{n} · sem limite" if lim is None else f"{n} de {lim}"


venc = emp.get("plano_ate")
_ui.kpis([("Plano atual", p["nome"], ("até " + data_br(venc)) if venc and atual != "gratis" else pl.preco_txt(p) +
           ("/mês" if p["preco"] else "")),
          ("Vans", _uso(uso['vans'], p['vans'])),
          ("Alunos ativos", _uso(uso['alunos'], p['alunos'])),
          ("Situação", "Ativo" if atual == (emp.get("plano") or "gratis") else "Venceu → Grátis")])

if (emp.get("plano") or "gratis") != atual:
    st.warning("Sua assinatura venceu e a conta voltou ao plano Grátis. Nada foi apagado — renove para voltar a "
               "cadastrar acima do limite.", icon=":material/info:")
for rec, nome in (("vans", "vans"), ("alunos", "alunos")):
    lim = p[rec]
    if lim is not None and uso[rec] >= lim:
        st.info(f"Você atingiu o limite de {nome} do plano {p['nome']}.", icon=":material/upgrade:")

st.subheader("Planos")
_ui.cartoes_planos(atual)

st.markdown("")
contato = auth.cfg("contato_whatsapp")
opcoes = [k for k in pl.ORDEM if k != atual and k != "gratis"]
if opcoes:
    a, b = st.columns([2, 1])
    escolha = a.selectbox("Quero mudar para", opcoes, format_func=lambda k: f"{pl.PLANOS[k]['nome']} — "
                          f"{pl.preco_txt(pl.PLANOS[k])}/mês", label_visibility="collapsed")
    msg = (f"Olá! Quero assinar o plano {pl.PLANOS[escolha]['nome']} ({pl.preco_txt(pl.PLANOS[escolha])}/mês) do "
           f"Pequenos a Bordo para a empresa {c['nome']} ({st.session_state['usuario']['email']}).")
    lk = link_whats(contato, msg) if contato else None
    if lk:
        b.link_button("Assinar", lk, icon=":material/workspace_premium:", type="primary", width="stretch")
    else:
        b.button("Assinar", disabled=True, width="stretch",
                 help="Contato de vendas ainda não configurado ([app] contato_whatsapp nos Secrets).")
    st.caption("Pagamento por Pix, boleto ou cartão. Assim que confirmado, o plano é liberado na sua conta.")
