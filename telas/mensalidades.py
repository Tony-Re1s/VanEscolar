"""Mensalidades: gerar o mês, receber, cobrar pelo WhatsApp."""
import streamlit as st

from core import repo
from core.fmt import FORMAS, brl, data_br, hoje, inicio_mes, link_whats, mes_label, somar_meses
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
h = hoje()
st.title("Mensalidades")

# o mês atual é gerado sozinho; os outros, pelo botão
if st.session_state.get("_mens_gerado") != (cid, inicio_mes(h)):
    repo.gerar_mensalidades(cid, h)
    st.session_state["_mens_gerado"] = (cid, inicio_mes(h))

meses = [somar_meses(inicio_mes(h), i) for i in range(-12, 3)]
comp = st.select_slider("Mês", options=meses, value=inicio_mes(h), format_func=lambda d: mes_label(d, curto=True))

df = repo.mensalidades_mes(cid, comp, h)
g1, g2 = st.columns([3, 1])
if g2.button("Gerar mês", icon=":material/autorenew:", use_container_width=True,
             help="Cria a mensalidade de quem ainda não tem neste mês (alunos ativos com valor)."):
    n = repo.gerar_mensalidades(cid, comp)
    st.toast(f"{n} mensalidade(s) criada(s)." if n else "Todos os alunos já têm mensalidade neste mês.")
    st.rerun()

if df.empty:
    g1.info("Nenhuma mensalidade neste mês. Cadastre alunos com valor de mensalidade e clique em **Gerar mês**.")
    st.stop()

prev = df["valor"].astype(float).sum()
rec = df["valor_pago"].fillna(0).astype(float).sum()
aberto = df.loc[df["situacao"] != "pago", "valor"].astype(float).sum()
venc = df.loc[df["situacao"] == "vencido", "valor"].astype(float).sum()
_ui.kpis([("Recebido", brl(rec), f"{(df['situacao'] == 'pago').sum()} de {len(df)} pagos"),
          ("Previsto no mês", brl(prev)), ("Em aberto", brl(aberto)),
          ("Vencido", brl(venc), f"{(df['situacao'] == 'vencido').sum()} aluno(s)")])

filtro = st.segmented_control("Mostrar", ["Todos", "Em aberto", "Vencidos", "Pagos"], default="Em aberto",
                              label_visibility="collapsed")
if filtro == "Em aberto":
    df = df[df["situacao"] != "pago"]
elif filtro == "Vencidos":
    df = df[df["situacao"] == "vencido"]
elif filtro == "Pagos":
    df = df[df["situacao"] == "pago"]

if df.empty:
    st.success("Nada por aqui. 🎉")


def _msg(r) -> str:
    primeiro = (r.responsavel or "").split(" ")[0] or "tudo bem"
    txt = (f"Olá, {primeiro}! Passando para lembrar da mensalidade da van de {r.aluno} "
           f"({mes_label(r.competencia)}), no valor de {brl(r.valor)}, com vencimento em {data_br(r.vencimento)}.")
    if r.situacao == "vencido":
        txt = (f"Olá, {primeiro}! A mensalidade da van de {r.aluno} ({mes_label(r.competencia)}), de {brl(r.valor)}, "
               f"venceu em {data_br(r.vencimento)}. Consegue verificar, por favor?")
    if c.get("chave_pix"):
        txt += f"\n\nChave Pix: {c['chave_pix']}"
    return txt + "\n\nObrigado! 🚐"


for r in df.itertuples():
    with st.container(border=True):
        a, b = st.container(key=f"lp_{r.id}").columns([3, 2])
        a.markdown(f"**{_ui.esc(r.aluno)}** {_ui.tag(r.situacao, _ui.ROTULO_MENS[r.situacao])}  \n"
                   f"<span class='ve-sub'>vence {data_br(r.vencimento)} · {_ui.esc(r.responsavel or 'sem responsável')}"
                   f"</span>", unsafe_allow_html=True)
        if r.situacao == "pago":
            b.markdown(f"**{brl(r.valor_pago)}**  \n<span class='ve-sub'>pago {data_br(r.pago_em)} · "
                       f"{_ui.esc(r.forma or '')}</span>", unsafe_allow_html=True)
            if b.button("Estornar", key=f"est_{r.id}", type="tertiary"):
                repo.estornar(cid, r.id)
                st.rerun()
            continue
        b.markdown(f"**{brl(r.valor)}**")
        x1, x2, x3 = st.container(key=f"linha_{r.id}").columns(3)
        with x1.popover("Receber", icon=":material/check_circle:", use_container_width=True):
            with st.form(f"pg_{r.id}"):
                d = st.date_input("Data", value=h, format="DD/MM/YYYY")
                v = st.number_input("Valor recebido", min_value=0.0, value=float(r.valor), step=5.0)
                f = st.selectbox("Forma", FORMAS)
                if st.form_submit_button("Confirmar", type="primary"):
                    repo.pagar(cid, r.id, d, v, f)
                    st.rerun()
        link = link_whats(r.telefone, _msg(r))
        if link:
            x2.link_button("Cobrar", link, icon=":material/chat:", use_container_width=True)
        else:
            x2.button("Sem WhatsApp", disabled=True, key=f"sw_{r.id}", use_container_width=True)
        with x3.popover("Ajustar", icon=":material/edit:", use_container_width=True):
            with st.form(f"aj_{r.id}"):
                nv = st.number_input("Valor", min_value=0.0, value=float(r.valor), step=5.0)
                nd = st.date_input("Vencimento", value=r.vencimento, format="DD/MM/YYYY")
                s1, s2 = st.columns(2)
                if s1.form_submit_button("Salvar"):
                    repo.alterar_mensalidade(cid, r.id, nv, nd)
                    st.rerun()
                if s2.form_submit_button("Isentar mês", help="Ex.: férias ou bolsa — fica como pago com R$ 0."):
                    repo.pagar(cid, r.id, h, 0, "Isento")
                    st.rerun()
