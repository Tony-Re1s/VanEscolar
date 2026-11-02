"""Modo fácil — Alunos em 4 campos (nome, WhatsApp do responsável, valor, vencimento) e "colar uma lista".
Tudo fica no mesmo cadastro do modo completo (lá dá para completar escola, endereço, contrato…)."""
import pandas as pd
import streamlit as st

from core import repo
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
emp = repo.empresa(cid)
dia_padrao = int(emp.get("dia_vencimento") or 10)

vans = repo.vans(cid)
van_padrao = str(vans.iloc[0]["id"]) if not vans.empty else None

st.title("Alunos")
_ui.guia(c, "telas/facil_alunos.py")


with st.form("aluno_rapido", clear_on_submit=True):
    a, b = st.columns(2)
    nome = a.text_input("Nome do aluno *")
    whats = b.text_input("WhatsApp do responsável", placeholder="(11) 99999-9999")
    c1, c2 = st.columns(2)
    valor = c1.number_input("Mensalidade (R$)", min_value=0.0, step=10.0, format="%.2f")
    dia = c2.number_input("Dia do vencimento", min_value=1, max_value=28, value=dia_padrao)
    if st.form_submit_button("Adicionar aluno", type="primary", icon=":material/person_add:", width="stretch"):
        if not nome.strip():
            st.error("Digite o nome do aluno.")
        elif _ui.checar_limite(c, "alunos"):
            repo.cadastro_rapido(cid, van_padrao, nome, whats or None, valor, int(dia))
            st.toast(f"{nome.strip()} adicionado(a).")
            st.rerun()

_ui.importar_planilha(c, van_padrao, dia_padrao, chave="imp_f")  # também aceita colar uma lista

st.subheader("Seus alunos")
df = repo.alunos_facil(cid)
if df.empty:
    st.info("Nenhum aluno ainda.")
    st.stop()
tab = df[["nome", "whatsapp", "valor", "vencimento", "ativo"]].copy()
tab["whatsapp"] = tab["whatsapp"].fillna("")
tab["valor"] = pd.to_numeric(tab["valor"]).astype(float)
ed = st.data_editor(
    tab, hide_index=True, width="stretch", num_rows="fixed", key="ed_alunos_facil",
    column_config={"nome": st.column_config.TextColumn("Aluno", required=True),
                   "whatsapp": st.column_config.TextColumn("WhatsApp do responsável"),
                   "valor": st.column_config.NumberColumn("Mensalidade", min_value=0.0, format="R$ %.2f"),
                   "vencimento": st.column_config.NumberColumn("Vence dia", min_value=1, max_value=28, step=1),
                   "ativo": st.column_config.CheckboxColumn("Ativo")})
st.caption(f"{int(df['ativo'].sum())} aluno(s) ativo(s). Edite direto na tabela e salve. Desmarque **Ativo** "
           "para tirar um aluno da rota e das cobranças.")
if st.button("Salvar alterações", icon=":material/save:"):
    mudou = 0
    for i, r in ed.iterrows():
        o = df.loc[i]
        novo = (str(r["nome"]).strip(), (r["whatsapp"] or None), float(r["valor"] or 0),
                int(r["vencimento"]) if pd.notna(r["vencimento"]) else None, bool(r["ativo"]))
        velho = (o["nome"], o["whatsapp"] or None, float(o["valor"] or 0),
                 int(o["vencimento"]) if pd.notna(o["vencimento"]) else None, bool(o["ativo"]))
        if novo != velho and novo[0]:
            if novo[4] and not velho[4] and not _ui.checar_limite(c, "alunos"):
                st.stop()
            repo.atualizar_facil(cid, o["id"], *novo, responsavel_id=o["responsavel_id"])
            mudou += 1
    st.toast(f"{mudou} aluno(s) atualizado(s)." if mudou else "Nada mudou.")
    st.rerun()
