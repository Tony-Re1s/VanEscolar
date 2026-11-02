"""Vans da empresa e quem dirige cada uma — lista → ficha da van; van nova em 3 etapas (cada uma cabe na tela)."""
import streamlit as st

from core import auth, repo
from core.fmt import link_whats
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
u = st.session_state["usuario"]
cid = c["id"]
ss = st.session_state
st.title("Vans")

df = repo.vans(cid, so_ativas=False)
ac = repo.acessos(list(df["motorista_email"].dropna()) + list(df["monitor_email"].dropna())) if not df.empty else {}
ETAPAS = ["Van", "Motorista", "Monitor(a)"]


def _ir(modo=None, vid=None, sec=None):
    ss["vn_modo"], ss["vn_id"], ss["vn_sec"] = modo, vid, sec
    st.rerun()


def _convite(papel: str, nome, email, tel, van_nome, chave):
    """Botão de convite no WhatsApp para o motorista / monitor(a) entrar no app."""
    if not email or email == u["email"]:
        return
    msg = (f"Olá, {(nome or '').split(' ')[0] or 'tudo bem'}! Você foi cadastrado(a) como {papel} da {van_nome} no "
           f"app Turminha a Bordo ({c['nome']}). Acesse {_ui.APP_URL} e clique em \"Entrar com Google\" usando o "
           f"e-mail {email}. Lá você vê a rota, faz a chamada e avisa os pais. 🚐")
    lk = link_whats(tel, msg)
    if lk:
        st.link_button(f"Convidar {papel} no WhatsApp", lk, icon=":material/send:", key=f"conv_{chave}",
                       width="stretch")
    else:
        st.caption(f"Cadastre o WhatsApp do(a) {papel} para enviar o convite.")


def _campos_van(g, n_vans):
    nome = st.text_input("Apelido da van *", value=g("nome") or f"Van {n_vans + 1}",
                         help="Como você chama a van no dia a dia: Van 1, Sprinter branca, Van da manhã…")
    a, b = st.columns(2)
    veiculo = a.text_input("Veículo", value=g("veiculo") or "", placeholder="Sprinter, Ducato…")
    placa = b.text_input("Placa", value=g("placa") or "")
    cap = st.number_input("Lugares", 1, 60, int(g("capacidade") or 15))
    return dict(nome=nome.strip(), veiculo=veiculo or None, placa=placa, capacidade=int(cap))


def _campos_motorista(g, eu_dirijo):
    if eu_dirijo:
        st.info("Você dirige esta van — os seus dados de Minha empresa são usados.", icon=":material/person:")
        nome_m = email_m = None
    else:
        nome_m = st.text_input("Nome do motorista", value=g("motorista_nome") or "")
        email_m = st.text_input("E-mail do Google", value=g("motorista_email") or "", placeholder="nome@gmail.com",
                                help="Com esse e-mail o motorista entra no app e vê só esta van: rota e chamada.")
    a, b = st.columns(2)
    tel = a.text_input("WhatsApp", value=g("motorista_telefone") or "", help="Aparece para os pais como contato.")
    cnh = b.text_input("CNH (opcional)", value=g("motorista_cnh") or "")
    apelido = st.text_input("Como as famílias chamam", value=g("motorista_apelido") or "",
                            placeholder="Tio Jô, Tia Rose…",
                            help="Vai nas mensagens da rota: \"O tio Jô está a caminho\".")
    return dict(motorista_nome=(c["nome"] if eu_dirijo else (nome_m or None)),
                motorista_email=(u["email"] if eu_dirijo else ((email_m or "").strip() or None)),
                motorista_telefone=(tel or (c.get("telefone") if eu_dirijo else None)) or None,
                motorista_cnh=cnh or None, motorista_apelido=apelido or None)


def _campos_monitor(g):
    nome = st.text_input("Nome do(a) monitor(a)", value=g("monitor_nome") or "")
    email = st.text_input("E-mail do Google", value=g("monitor_email") or "", placeholder="nome@gmail.com")
    a, b = st.columns(2)
    tel = a.text_input("WhatsApp", value=g("monitor_telefone") or "")
    apelido = b.text_input("Como chamam", value=g("monitor_apelido") or "", placeholder="Tia Rose…")
    return dict(monitor_nome=nome or None, monitor_email=(email or "").strip() or None, monitor_telefone=tel or None,
                monitor_apelido=apelido or None)


def _validar(d: dict) -> bool:
    if not d.get("nome"):
        st.error("Preencha o apelido da van.")
        return False
    for k, quem in (("motorista_email", "do motorista"), ("monitor_email", "do(a) monitor(a)")):
        if d.get(k) and "@" not in d[k]:
            st.error(f"E-mail {quem} inválido.")
            return False
    return True


def _rodape(chave, voltar=True, seguir="Continuar", depois=False):
    with st.container(key=f"wzpe_{chave}"):
        a, b = st.columns(2) if voltar else (None, st.container())
        v = a.form_submit_button("Voltar", icon=":material/arrow_back:", width="stretch") if voltar else False
        s_ = b.form_submit_button(seguir, type="primary", width="stretch",
                                  icon=":material/arrow_forward:" if seguir == "Continuar" else ":material/check:")
    d = st.form_submit_button("Salvar agora (completo depois)", type="tertiary", width="stretch") if depois else False
    return "voltar" if v else "seguir" if s_ else "depois" if d else None


def _salvar_nova(r: dict):
    dados = dict(ativo=True) | r
    if not _validar(dados) or not _ui.checar_limite(c, "vans"):
        st.stop()
    repo.salvar_van(cid, dados)
    auth.perfil(u)
    ss.pop("vn_rasc", None)
    ss["vn_etapa"] = 0
    st.toast(f"{dados['nome']} cadastrada. ✅")
    novo = repo.db.ao_vivo("select id from vans where condutor_id = :cid order by criado_em desc limit 1", cid=cid)
    _ir("ficha", str(novo.iloc[0]["id"]) if len(novo) else None)


# ------------------------------------------------------------------ van nova, em etapas
def _nova():
    r = ss.setdefault("vn_rasc", {})
    et = ss.setdefault("vn_etapa", 0)
    g = r.get
    if st.button("Cancelar", icon=":material/close:", type="tertiary", key="vn_cancelar"):
        ss.pop("vn_rasc", None)
        ss["vn_etapa"] = 0
        _ir()
    _ui.etapas(ETAPAS, et)
    if et == 0:
        with st.form("vn0"):
            campos = _campos_van(g, len(df))
            acao = _rodape("v0", voltar=False, depois=True)
        if acao:
            r.update(campos)
            if not campos["nome"]:
                st.error("Preencha o apelido da van.")
                st.stop()
            if acao == "depois":
                _salvar_nova(r)
            ss["vn_etapa"] = 1
            st.rerun()
    elif et == 1:
        eu = st.toggle("Eu dirijo esta van", value=r.get("_eu", df.empty), key="vn_eu")
        with st.form("vn1"):
            campos = _campos_motorista(g, eu)
            acao = _rodape("v1", depois=True)
        if acao:
            r.update(campos, _eu=eu)
            if acao == "depois":
                _salvar_nova({k: v for k, v in r.items() if not k.startswith("_")})
            ss["vn_etapa"] = 0 if acao == "voltar" else 2
            st.rerun()
    else:
        st.caption("Opcional — quem acompanha as crianças também usa a rota e a chamada.")
        with st.form("vn2"):
            campos = _campos_monitor(g)
            acao = _rodape("v2", seguir="Cadastrar van")
        if acao:
            r.update(campos)
            if acao == "voltar":
                ss["vn_etapa"] = 1
                st.rerun()
            _salvar_nova({k: v for k, v in r.items() if not k.startswith("_")})


# ------------------------------------------------------------------ ficha da van
def _ficha(vid):
    linha = df[df["id"].astype(str) == str(vid)]
    if linha.empty:
        _ir()
    v = linha.iloc[0].to_dict()
    g = v.get
    sec = ss.get("vn_sec")
    eu = (g("motorista_email") or "") == u["email"]

    def _salvar(campos: dict):
        base = {k: g(k) for k in repo._CAMPOS_V} | campos
        if not _validar(base):
            st.stop()
        if base.get("ativo") and not bool(g("ativo")) and not _ui.checar_limite(c, "vans"):
            st.stop()
        repo.salvar_van(cid, base, vid=str(vid))
        auth.perfil(u)
        st.toast("Salvo. ✅")
        _ir("ficha", vid)

    if sec:
        if st.button(f"Ficha da {g('nome')}", icon=":material/arrow_back:", type="tertiary", key="vf_voltar"):
            _ir("ficha", vid)
    elif st.button("Todas as vans", icon=":material/arrow_back:", type="tertiary", key="vf_lista"):
        _ir()
    st.markdown(f"<div class='ve-ficha-topo'><div class='av'>🚐</div><div><h3>{_ui.esc(g('nome'))}</h3>"
                f"<span class='ve-sub'>{_ui.esc(' · '.join(x for x in [g('veiculo'), g('placa') or 'sem placa'] if x))} · "
                f"{g('alunos')} de {g('capacidade')} lugares{'' if g('ativo') else ' · 🔴 inativa'}</span></div></div>",
                unsafe_allow_html=True)

    if not sec:
        docs = repo.documentos_van(cid)
        docs = docs[docs["van_id"].astype(str) == str(vid)] if not docs.empty else docs
        from core.fmt import data_br
        prox = f"próximo: {docs.iloc[0]['tipo']} em {data_br(docs.iloc[0]['vencimento'])}" if len(docs) else "Nenhum ainda"
        mot = "Você" if eu else (g("motorista_nome") or "Sem motorista — toque para cadastrar")
        mon = g("monitor_nome") or g("monitor_email") or "Opcional — toque para cadastrar"
        for k, rot, sub, ic in [
            ("dados", "Dados da van", f"{g('veiculo') or 'Veículo'} · {g('placa') or 'sem placa'} · {g('capacidade')} lugares",
             ":material/airport_shuttle:"),
            ("mot", "Motorista", mot,
             ":material/badge:"),
            ("mon", "Monitor(a)", mon, ":material/escalator_warning:"),
            ("docs", f"Documentos ({len(docs)})", prox, ":material/description:"),
        ]:
            if _ui.linha_ficha(rot, sub, f"v{k}_{vid}", ic):
                _ir("ficha", vid, k)
        return

    if sec == "dados":
        with st.form("vf_dados"):
            campos = _campos_van(g, len(df))
            ativo = st.toggle("Van ativa", value=bool(g("ativo")))
            if st.form_submit_button("Salvar", type="primary", width="stretch"):
                _salvar(campos | dict(ativo=ativo))
    elif sec == "mot":
        eu_n = st.toggle("Eu dirijo esta van", value=eu, key=f"vf_eu_{vid}")
        with st.form("vf_mot"):
            campos = _campos_motorista({}.get if eu and not eu_n else g, eu_n)
            if st.form_submit_button("Salvar", type="primary", width="stretch"):
                _salvar(campos)
        if g("motorista_email") and not eu:
            st.markdown(_ui.selo_acesso(g("motorista_email"), ac), unsafe_allow_html=True)
        _convite("motorista", g("motorista_nome"), g("motorista_email"), g("motorista_telefone"), g("nome"), f"m{vid}")
    elif sec == "mon":
        with st.form("vf_mon"):
            campos = _campos_monitor(g)
            if st.form_submit_button("Salvar", type="primary", width="stretch"):
                _salvar(campos)
        if g("monitor_email"):
            st.markdown(_ui.selo_acesso(g("monitor_email"), ac), unsafe_allow_html=True)
        _convite("monitor(a)", g("monitor_nome"), g("monitor_email"), g("monitor_telefone"), g("nome"), f"n{vid}")
    elif sec == "docs":
        _ui.documentos_vans(cid, df[df["ativo"]], so_van=str(vid), titulo=False)


# ------------------------------------------------------------------ lista
def _lista():
    if st.button("Nova van", icon=":material/add:", type="primary", width="stretch", key="nova_van_btn"):
        ss["vn_rasc"], ss["vn_etapa"] = {}, 0
        _ir("nova")
    if df.empty:
        st.info("Cadastre a sua van: o apelido, a placa e quem dirige.", icon=":material/airport_shuttle:")
    for v in df.itertuples():
        eu = (v.motorista_email or "") == u["email"]
        quem = "você dirige" if eu else (v.motorista_nome or "sem motorista")
        sub = f"{v.placa or 'sem placa'} · {v.alunos}/{v.capacidade} alunos · {quem}" + ("" if v.ativo else " · inativa")
        if st.button(f"**{v.nome}**  \n{sub}", key=f"al_v{v.id}", width="stretch"):
            _ir("ficha", str(v.id))
    docs = repo.documentos_van(cid)
    if _ui.linha_ficha(f"Documentos e vencimentos ({len(docs)})",
                       "IPVA, licenciamento, seguro, vistoria…", "vdocs_todos", ":material/description:"):
        _ir("docs")


_modo = ss.get("vn_modo")
if _modo == "nova":
    _nova()
elif _modo == "ficha" and ss.get("vn_id"):
    _ficha(ss["vn_id"])
elif _modo == "docs":
    if st.button("Todas as vans", icon=":material/arrow_back:", type="tertiary", key="vd_voltar"):
        _ir()
    _ui.documentos_vans(cid, df[df["ativo"]] if not df.empty else df)
else:
    _lista()
