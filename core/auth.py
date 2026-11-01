"""Login com Google (st.login) e perfil de quem entrou.

Perfis (uma pessoa pode ter mais de um):
- admin       → e-mails em [app] admins nos Secrets; vê a tela de condutores.
- condutor    → tem cadastro em `condutores` (cria o próprio no 1º acesso).
- responsável → o e-mail dele foi cadastrado por algum condutor num aluno.
"""
import streamlit as st

from core import db

from pathlib import Path

import re as _re

# numa linha só e sem comentários: o st.markdown quebra HTML com linhas em branco
_VAN_SVG = " ".join(_re.sub(r"<!--.*?-->", "", (Path(__file__).resolve().parent.parent / "static" / "van.svg")
                            .read_text(encoding="utf-8"), flags=_re.S).split())

EXIGIDOS_AUTH = [("auth", "redirect_uri"), ("auth", "cookie_secret"), ("auth", "client_id"),
                 ("auth", "client_secret"), ("auth", "server_metadata_url")]


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
    exigidos = [("connections", db.banco_ativo(), "url")] + ([] if cfg("dev_email") else EXIGIDOS_AUTH)
    faltando = [".".join(c) for c in exigidos if not _segredo(*c)]
    if faltando:
        st.title("Turminha a Bordo — falta configurar")
        st.warning("O app está no ar, mas faltam itens nos **Secrets** (Manage app → ⋮ → Settings → Secrets):")
        st.markdown("\n".join(f"- `{f}`" for f in faltando))
        st.stop()


VAN_SVG = _VAN_SVG


def botao_entrar(chave="entrar"):
    st.button("Entrar com Google", type="primary", icon=":material/login:", on_click=st.login,
              width="stretch", key=chave)


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
    r = db.ao_vivo("""select distinct pr.passageiro_id, p.condutor_id from responsaveis r
                      join passageiro_responsavel pr on pr.responsavel_id = r.id
                      join passageiros p on p.id = pr.passageiro_id and p.ativo
                      join condutores c on c.id = p.condutor_id and c.ativo
                      where lower(r.email) = :e""", e=usuario["email"])
    from core import planos as pl, repo
    from core.fmt import hoje
    vm = repo.vans_do_motorista(usuario["email"])
    vans = vm.to_dict("records") if len(vm) else []
    filhos = [(str(x.passageiro_id), str(x.condutor_id)) for x in r.itertuples()] if len(r) else []
    # empresa sem plano em vigor (venceu e não pagou): motorista e pais ficam bloqueados até o gestor pagar
    emps = repo.empresas_por_id({c for _, c in filhos} | {str(v["condutor_id"]) for v in vans})
    cat = pl.catalogo()
    bloq = {i for i, e in emps.items() if not pl.liberada(e, hoje(), cat)}
    usuario["filhos"] = [p for p, c in filhos if c not in bloq]
    usuario["vans_motorista"] = [v for v in vans if str(v["condutor_id"]) not in bloq]
    usuario["bloqueios"] = sorted({emps[i]["nome"] for i in bloq})
    usuario["admin"] = usuario["email"] in admins()
    cond = usuario["condutor"]
    usuario["bloqueado"] = bool(cond) and not usuario["admin"] and not pl.liberada(cond, hoje(), cat)
    return usuario


def usuario_logado() -> dict | None:
    """Usuário logado (com perfil carregado) ou None se ninguém entrou — aí o app mostra as páginas públicas."""
    if "usuario" in st.session_state:
        return st.session_state["usuario"]
    _checar_configuracao()
    dev = cfg("dev_email")            # só para rodar local; nunca nos Secrets do Streamlit Cloud
    if dev:
        email, nome = dev, cfg("dev_nome", dev)
    else:
        if not st.user.get("is_logged_in", False):
            return None
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
