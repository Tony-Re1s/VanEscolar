"""Login com Google (st.login) e perfil de quem entrou.

Perfis (uma pessoa pode ter mais de um):
- admin       → e-mails em [app] admins nos Secrets; vê a tela de condutores.
- condutor    → tem cadastro em `condutores` (cria o próprio no 1º acesso).
- responsável → o e-mail dele foi cadastrado por algum condutor num aluno.
"""
import streamlit as st

from core import db

EXIGIDOS = [("connections", "neon", "url"), ("auth", "redirect_uri"), ("auth", "cookie_secret"),
            ("auth", "client_id"), ("auth", "client_secret"), ("auth", "server_metadata_url")]


def _segredo(*caminho):
    try:
        v = st.secrets
        for k in caminho:
            v = v[k]
        return v
    except Exception:  # noqa: BLE001 — secrets ausentes
        return None


def cfg(chave, padrao=None):
    v = _segredo("app", chave)
    return padrao if v is None else v


def _checar_configuracao():
    exigidos = [e for e in EXIGIDOS if e[0] != "auth"] if cfg("dev_email") else EXIGIDOS
    faltando = [".".join(c) for c in exigidos if not _segredo(*c)]
    if faltando:
        st.title("🚐 VanEscolar — falta configurar")
        st.warning("O app está no ar, mas faltam itens nos **Secrets** (Manage app → ⋮ → Settings → Secrets):")
        st.markdown("\n".join(f"- `{f}`" for f in faltando))
        st.stop()


def _tela_login():
    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
    _, meio, _ = st.columns([1, 2, 1])
    with meio:
        st.markdown("<div class='ve-logo'>🚐</div>", unsafe_allow_html=True)
        st.title("VanEscolar")
        st.caption("Gestão do transporte escolar: alunos, rotas, chamada, mensalidades e financeiro. "
                   "Pais acompanham o dia a dia e avisam faltas.")
        st.button("Entrar com Google", type="primary", icon=":material/login:", on_click=st.login,
                  use_container_width=True)
    st.stop()


def admins() -> list[str]:
    return [e.strip().lower() for e in (cfg("admins") or [])]


def _carregar(email: str, nome: str | None) -> dict:
    u = db.gravar("""
        insert into usuarios (email, nome, ultimo_acesso) values (:e, :n, now())
        on conflict (email) do update set ultimo_acesso = now(), nome = coalesce(usuarios.nome, excluded.nome)
        returning id, email, nome""", e=email, n=nome)
    return u


def perfil(usuario: dict) -> dict:
    """Atualiza condutor/responsável do usuário (lido sem cache: muda quando o condutor cadastra os pais)."""
    c = db.ao_vivo("select * from condutores where usuario_id = :u", u=usuario["id"])
    usuario["condutor"] = c.iloc[0].to_dict() if len(c) else None
    r = db.ao_vivo("""select distinct pr.passageiro_id from responsaveis r
                      join passageiro_responsavel pr on pr.responsavel_id = r.id
                      join passageiros p on p.id = pr.passageiro_id and p.ativo
                      join condutores c on c.id = p.condutor_id and c.ativo
                      where lower(r.email) = :e""", e=usuario["email"])
    usuario["filhos"] = [str(x) for x in r["passageiro_id"]] if len(r) else []
    usuario["admin"] = usuario["email"] in admins()
    return usuario


def exigir_login() -> dict:
    if "usuario" in st.session_state:
        return st.session_state["usuario"]
    _checar_configuracao()
    dev = cfg("dev_email")            # só para rodar local; nunca nos Secrets do Streamlit Cloud
    if dev:
        email, nome = dev, cfg("dev_nome", dev)
    else:
        if not st.user.get("is_logged_in", False):
            _tela_login()
        email, nome = st.user.get("email"), st.user.get("name")
    email = (email or "").strip().lower()
    if not email:
        st.error("Não consegui ler o e-mail da sua conta Google.")
        st.button("Sair", on_click=st.logout)
        st.stop()
    usuario = perfil(_carregar(email, nome))
    st.session_state["usuario"] = usuario
    return usuario


def sair():
    st.session_state.clear()
    if not cfg("dev_email"):
        st.logout()
