"""Área da família: carteirinha, embarque do dia, avisar falta e mensalidades."""
from datetime import timedelta

import streamlit as st

from core import repo
from core.fmt import TZ, TURNOS, brl, data_br, hoje, idade, link_whats, mes_label
from telas import _ui

u = st.session_state["usuario"]
pids = u.get("filhos") or []
h = hoje()
st.title("Meus filhos")

filhos = repo.filhos(pids)
if filhos.empty:
    st.info("Nenhum aluno vinculado ao seu e-mail.")
    st.stop()

status = repo.status_hoje(pids, h)
abas = st.tabs([r.nome.split()[0] for r in filhos.itertuples()]) if len(filhos) > 1 else [st.container()]

for aba, f in zip(abas, filhos.itertuples()):
    pid = str(f.id)
    with aba:
        # carteirinha
        nasc = f"{idade(f.data_nasc)} anos · " if f.data_nasc else ""
        st.markdown(f"""<div class='ve-cart'>
            <div class='t'>Carteirinha do transporte escolar</div>
            <h3>{_ui.esc(f.nome)}</h3>
            <div>{nasc}{_ui.esc(f.serie or '')} {('· ' + TURNOS.get(f.turno, '')) if f.turno else ''}</div>
            <div class='r'>🏫 {_ui.esc(f.escola or '—')}</div>
            <div class='r'>🚐 {_ui.esc(f.van or f.condutor)} · {_ui.esc(f.veiculo or '')} {_ui.esc(f.placa or '')}</div>
            <div class='r'>👤 Motorista: {_ui.esc(f.motorista)} · 📞 {_ui.esc(f.condutor_tel or '—')}</div>
            <div class='r'>🏢 {_ui.esc(f.condutor)}</div></div>""", unsafe_allow_html=True)
        zap = link_whats(f.condutor_tel, f"Olá! Sou responsável por {f.nome}.")
        if zap:
            st.link_button("Falar com o motorista", zap, icon=":material/chat:")

        # hoje
        st.subheader("Hoje")
        s = status[status["passageiro_id"].astype(str) == pid] if not status.empty else status
        rot = {"ida": {"embarcou": "Embarcou na van", "desembarcou": "Chegou na escola", "faltou": "Não embarcou"},
               "volta": {"embarcou": "Saiu da escola na van", "desembarcou": "Entregue em casa",
                         "faltou": "Não voltou na van"}}
        linhas = []
        for t in ("ida", "volta"):
            x = s[s["trecho"] == t] if not s.empty else s
            if not x.empty:
                r = x.iloc[0]
                linhas.append(f"**{t.capitalize()}:** {rot[t][r['status']]} às {r['hora'].astimezone(TZ).strftime('%H:%M')}")
            else:
                linhas.append(f"**{t.capitalize()}:** aguardando")
        st.markdown("  \n".join(linhas))
        st.caption("Atualiza quando o motorista marca na chamada. Recarregue a página para ver o mais recente.")

        # avisar falta
        st.subheader("Avisar falta")
        aus = repo.ausencias([pid], h)
        with st.form(f"aus_{pid}", clear_on_submit=True):
            a, b = st.columns(2)
            d = a.date_input("Dia", value=h, min_value=h, max_value=h + timedelta(days=90), format="DD/MM/YYYY")
            q = b.selectbox("Trecho", ["Ida e volta", "Só ida", "Só volta"])
            m = st.text_input("Motivo (opcional)", placeholder="Ex.: consulta médica, vou buscar")
            if st.form_submit_button("Avisar a van", type="primary"):
                repo.avisar_ausencia(pid, d, q != "Só volta", q != "Só ida", m or None, u["id"])
                st.success(f"Aviso registrado para {data_br(d)}.")
                st.rerun()
        for r in aus.itertuples():
            trechos = " e ".join(t for t, v in (("ida", r.ida), ("volta", r.volta)) if v)
            a, b = st.columns([4, 1])
            a.markdown(f"📅 **{data_br(r.data)}** — não vai ({trechos}){' · ' + _ui.esc(r.motivo) if r.motivo else ''}")
            if b.button("Cancelar", key=f"canc_{r.id}", type="tertiary"):
                repo.cancelar_ausencia(pid, r.id)
                st.rerun()

        # mensalidades
        st.subheader("Mensalidades")
        mens = repo.mensalidades_filhos([pid], h)
        if f.chave_pix:
            st.markdown(f"Chave Pix para pagamento ({f.condutor}):")
            st.code(f.chave_pix, language=None)
        if mens.empty:
            st.caption("Nenhuma mensalidade lançada ainda.")
        for r in mens.itertuples():
            pago = f" · pago em {data_br(r.pago_em)}" if r.pago_em else ""
            st.markdown(f"{mes_label(r.competencia)} — **{brl(r.valor)}** · vence {data_br(r.vencimento)}{pago} "
                        f"{_ui.tag(r.situacao, _ui.ROTULO_MENS[r.situacao])}", unsafe_allow_html=True)
