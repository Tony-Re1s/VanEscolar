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
contratado = emp.get("plano") or "gratis"
tipo = pl.tipo_da_empresa(emp) if contratado != "gratis" else "pago"
if atual == "gratis":
    sub = pl.preco_txt(p)
elif tipo == "teste":
    sub = "degustação até " + data_br(venc)
elif tipo == "cortesia":
    sub = "cortesia" + (" até " + data_br(venc) if venc else "")
else:
    sub = ("até " + data_br(venc)) if venc else pl.preco_txt(p) + "/mês"
if contratado != atual:
    situacao = "Degustação acabou" if tipo == "teste" else "Venceu → Grátis"
else:
    situacao = {"teste": "Degustação", "cortesia": "Cortesia"}.get(tipo, "Ativo")
_ui.kpis([("Plano atual", p["nome"], sub),
          ("Vans", _uso(uso['vans'], p['vans'])),
          ("Alunos ativos", _uso(uso['alunos'], p['alunos'])),
          ("Situação", situacao)])

if contratado != atual and tipo == "teste":
    st.warning(f"Sua degustação do plano {pl.PLANOS[contratado]['nome']} terminou e a conta voltou ao plano Grátis. "
               "Nada foi apagado — assine para continuar com tudo liberado.", icon=":material/info:")
elif contratado != atual:
    st.warning("Sua assinatura venceu e a conta voltou ao plano Grátis. Nada foi apagado — renove para voltar a "
               "cadastrar acima do limite.", icon=":material/info:")
elif tipo == "teste" and venc:
    faltam = (venc - hoje()).days
    st.info(f"Você está experimentando o plano **{p['nome']}** de graça até **{data_br(venc)}** "
            f"({'hoje é o último dia' if faltam <= 0 else 'falta 1 dia' if faltam == 1 else f'faltam {faltam} dias'}). Para continuar depois disso, "
            "assine abaixo — nada do que você cadastrou se perde.", icon=":material/celebration:")
for rec, nome in (("vans", "vans"), ("alunos", "alunos")):
    lim = p[rec]
    if lim is not None and uso[rec] >= lim:
        st.info(f"Você atingiu o limite de {nome} do plano {p['nome']}.", icon=":material/upgrade:")

st.subheader("Planos")
_ui.cartoes_planos(atual)

st.markdown("")
contato = auth.cfg("contato_whatsapp")
# em degustação, o próprio plano também aparece para assinar
opcoes = [k for k in pl.ORDEM if k != "gratis" and (k != atual or tipo == "teste")]
if opcoes:
    a, b = st.columns([2, 1])
    escolha = a.selectbox("Quero assinar", opcoes, index=opcoes.index(atual) if atual in opcoes else 0, format_func=lambda k: f"{pl.PLANOS[k]['nome']} — "
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
