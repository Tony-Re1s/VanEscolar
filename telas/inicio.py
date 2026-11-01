"""Página inicial pública (antes do login). Serve também de 'página inicial do app' para o Google."""
import streamlit as st

from core import auth
from telas import _ui

st.markdown(f"""<div class='ve-hero'><div class='logo'>{auth.VAN_SVG}</div>
<h1>Pequenos a Bordo</h1>
<p>O app do transporte escolar: rota e chamada, mensalidades, contrato digital e uma área para os pais
acompanharem tudo — no celular.</p></div>""", unsafe_allow_html=True)

_, meio, _ = st.columns([1, 2, 1])
with meio:
    auth.botao_entrar("entrar_topo")
    st.caption("Gestor, motorista ou responsável: entre com a sua conta Google.")

FEATS = [
    ("🚐", "Rota e chamada", "Inicie a rota, marque embarque e entrega e avise cada família no WhatsApp."),
    ("💰", "Mensalidades", "Geradas sozinhas todo mês, cobrança pronta com Pix e painel de inadimplência."),
    ("📄", "Contrato digital", "O responsável preenche e assina pelo app; você contra-assina e baixa o PDF."),
    ("👨‍👩‍👧", "Área dos pais", "Carteirinha, aviso de falta, “a van saiu” e as mensalidades em um lugar."),
    ("🧑‍✈️", "Vans e motoristas", "Várias vans, cada motorista vê só a dele."),
    ("📊", "Financeiro", "Despesas, lucro do mês e resultado por van."),
]
st.markdown("<div class='ve-grade'>" + "".join(
    f"<div class='ve-feat'><div class='i'>{i}</div><b>{_ui.esc(t)}</b><span>{_ui.esc(d)}</span></div>"
    for i, t, d in FEATS) + "</div>", unsafe_allow_html=True)

st.subheader("Planos")
_ui.cartoes_planos()
st.caption("Comece grátis. Os planos pagos liberam mais vans e alunos.")

st.markdown("<div class='ve-rodape'>Pequenos a Bordo · São Paulo/SP · "
            "<a href='/privacidade' target='_self'>Política de Privacidade</a> · "
            "<a href='/termos' target='_self'>Termos de Uso</a></div>", unsafe_allow_html=True)
