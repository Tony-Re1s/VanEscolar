"""Administração: banco em uso, switch para o reserva, backup e restauração."""
import time

import streamlit as st

from core import auth, backup, db
from core.fmt import agora
from telas import _ui

if not st.session_state["usuario"].get("admin"):
    st.stop()

ACTIONS = "https://github.com/Tony-Re1s/VanEscolar/actions/workflows/backup.yml"
NOMES = {"neon": "Neon (principal)", "reserva": "Reserva"}

st.title("Banco e backup")
ativo = db.banco_ativo()
bancos = db.bancos_configurados()


def _nome(b):
    return NOMES.get(b, b)


@st.cache_data(ttl=60, show_spinner=False)
def _testar(nome: str) -> tuple[bool, str]:
    t0 = time.perf_counter()
    try:
        with db.conexao(nome).engine.connect() as c:
            n = c.exec_driver_sql("select (select count(*) from condutores), (select count(*) from passageiros)").one()
        return True, f"{int((time.perf_counter() - t0) * 1000)} ms · {n[0]} empresa(s) · {n[1]} aluno(s)"
    except Exception as e:  # noqa: BLE001
        return False, str(e).split("\n")[0][:160]


# ---------------------------------------------------------------- situação
_ui.kpis([("Banco em uso", _nome(ativo)), ("Bancos configurados", str(len(bancos)))])
for b in bancos:
    ok, info = _testar(b)
    with st.container(border=True, key=f"card_banco_{b}"):
        st.markdown(f"**{_nome(b)}** {_ui.tag('pago', 'em uso') if b == ativo else ''}  \n"
                    f"<span class='ve-sub'>{'🟢' if ok else '🔴'} {_ui.esc(info)}</span>", unsafe_allow_html=True)
if st.button("Testar de novo", icon=":material/refresh:"):
    _testar.clear()
    st.rerun()

if "reserva" not in bancos:
    st.warning("Ainda não há banco reserva configurado. Crie um Postgres grátis em outro provedor e coloque a URL "
               "nos Secrets em `[connections.reserva]`.", icon=":material/warning:")

with st.expander("Como virar o switch para o banco reserva", icon=":material/swap_horiz:"):
    st.markdown(f"""
1. Confira acima que o **Reserva** está 🟢 e com os dados de ontem (o backup diário copia tudo para ele).
2. No Streamlit Cloud: **⋮ → Settings → Secrets**, na seção `[app]` coloque `banco = "reserva"` e salve.
3. O app passa a usar o reserva em segundos — os usuários não precisam fazer nada.
4. Quando o Neon voltar: copie o reserva → Neon aqui embaixo e troque para `banco = "neon"`.

Backups diários automáticos (criptografados, guardados por 30 dias): [GitHub → Actions → Backup diário]({ACTIONS}).
""")

# ---------------------------------------------------------------- backup agora
st.subheader("Backup agora")
senha_padrao = auth.cfg("backup_senha") or ""
with st.form("bk"):
    senha = st.text_input("Senha do arquivo", type="password",
                          placeholder="usa a senha dos Secrets" if senha_padrao else "",
                          help="Guarde essa senha: sem ela o arquivo não abre. Se ficar em branco, usa "
                               "[app] backup_senha dos Secrets.")
    if st.form_submit_button("Gerar backup", icon=":material/download:", type="primary"):
        s = senha or senha_padrao
        if not s:
            st.error("Informe uma senha.")
        else:
            with st.spinner("Exportando…"):
                dados = backup.exportar(db.conexao(ativo).engine)
                st.session_state["_bk"] = (backup.nome_arquivo(), backup.cifrar(dados, s), backup.contagem(dados))
if "_bk" in st.session_state:
    nome, arq, cont = st.session_state["_bk"]
    st.download_button(f"Baixar {nome}", arq, file_name=nome, mime="application/octet-stream",
                       icon=":material/file_download:")
    st.caption(" · ".join(f"{t} {n}" for t, n in cont.items() if n))

# ---------------------------------------------------------------- copiar entre bancos
outros = [b for b in bancos if b != ativo]
if outros:
    st.subheader("Copiar entre bancos")
    with st.form("copiar"):
        a, b = st.columns(2)
        origem = a.selectbox("De", bancos, index=bancos.index(ativo), format_func=_nome)
        destino = b.selectbox("Para", bancos, index=bancos.index(outros[0]), format_func=_nome)
        certeza = st.checkbox("Entendo que os dados do banco de destino serão substituídos.")
        if st.form_submit_button("Copiar", icon=":material/sync:"):
            if origem == destino:
                st.error("Escolha bancos diferentes.")
            elif not certeza:
                st.error("Marque a confirmação.")
            else:
                with st.spinner("Copiando…"):
                    feitos = backup.copiar(db.conexao(origem).engine, db.conexao(destino).engine)
                if destino == ativo:
                    st.cache_data.clear()
                    db._mudou()
                _testar.clear()
                st.success(f"Copiado {_nome(origem)} → {_nome(destino)} em {agora():%d/%m %H:%M}: "
                           f"{sum(feitos.values())} registros.", icon=":material/check_circle:")

# ---------------------------------------------------------------- restaurar
st.subheader("Restaurar um backup")
with st.form("rest"):
    arquivo = st.file_uploader("Arquivo .pab", type=["pab"])
    a, b = st.columns(2)
    senha_r = a.text_input("Senha", type="password", placeholder="usa a senha dos Secrets" if senha_padrao else "")
    destino_r = b.selectbox("Restaurar em", bancos, index=bancos.index(ativo), format_func=_nome)
    conf = st.text_input("Digite RESTAURAR para confirmar",
                         help="Os dados atuais do banco escolhido são apagados e trocados pelos do arquivo.")
    if st.form_submit_button("Restaurar", icon=":material/settings_backup_restore:"):
        if not arquivo:
            st.error("Escolha o arquivo.")
        elif conf.strip().upper() != "RESTAURAR":
            st.error("Digite RESTAURAR para confirmar.")
        else:
            try:
                dados = backup.decifrar(arquivo.getvalue(), senha_r or senha_padrao)
            except (backup.SenhaErrada, ValueError) as e:
                st.error(str(e))
                st.stop()
            with st.spinner("Restaurando…"):
                feitos = backup.restaurar(db.conexao(destino_r).engine, dados)
            if destino_r == ativo:
                st.cache_data.clear()
                db._mudou()
            _testar.clear()
            st.success(f"Backup de {dados.get('gerado_em', '?')[:16].replace('T', ' ')} UTC restaurado em "
                       f"{_nome(destino_r)}: {sum(feitos.values())} registros.", icon=":material/check_circle:")
