"""Modo fácil — Alunos em 4 campos (nome, WhatsApp do responsável, valor, vencimento) e "colar uma lista".
Tudo fica no mesmo cadastro do modo completo (lá dá para completar escola, endereço, contrato…)."""
import re

import pandas as pd
import streamlit as st

from core import repo
from core.fmt import so_digitos
from telas import _ui
from telas._ui import exigir_condutor

c = exigir_condutor()
cid = c["id"]
emp = repo.empresa(cid)
dia_padrao = int(emp.get("dia_vencimento") or 10)

vans = repo.vans(cid)
van_padrao = str(vans.iloc[0]["id"]) if not vans.empty else None

st.title("Alunos")
st.caption("Só o essencial. Quer endereço, escola ou contrato? Troque para o **modo completo** no topo — o que você "
           "cadastrar aqui aparece lá.")


def _valor(txt) -> float:
    t = str(txt or "").replace("R$", "").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return round(float(t), 2)
    except ValueError:
        return 0.0


def _dia(txt):
    d = so_digitos(str(txt or ""))
    return min(28, max(1, int(d))) if d else None


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

with st.expander("Colar uma lista (vários de uma vez)", icon=":material/content_paste:"):
    st.caption("Um aluno por linha: **nome; WhatsApp; valor; dia**. Só o nome é obrigatório. "
               "Ex.: `Maria Souza; 11 98888-7777; 350; 10`")
    txt = st.text_area("Lista", height=140, label_visibility="collapsed",
                       placeholder="Maria Souza; 11 98888-7777; 350; 10\nJoão Lima; 11 97777-6666; 380")
    linhas = []
    for ln in (txt or "").splitlines():
        partes = [p.strip() for p in re.split(r"[;\t]", ln)]
        if partes and partes[0]:
            linhas.append(dict(nome=partes[0], whats=partes[1] if len(partes) > 1 else "",
                               valor=_valor(partes[2]) if len(partes) > 2 else 0.0,
                               dia=_dia(partes[3]) if len(partes) > 3 else dia_padrao))
    if linhas:
        st.dataframe(pd.DataFrame(linhas).rename(columns={"nome": "Aluno", "whats": "WhatsApp", "valor": "Valor",
                                                          "dia": "Vence dia"}), hide_index=True, width="stretch")
        if st.button(f"Cadastrar {len(linhas)} aluno(s)", type="primary", icon=":material/group_add:"):
            if _ui.checar_limite(c, "alunos", novos=len(linhas)):
                for x in linhas:
                    repo.cadastro_rapido(cid, van_padrao, x["nome"], x["whats"] or None, x["valor"],
                                         x["dia"] or dia_padrao)
                st.toast(f"{len(linhas)} aluno(s) cadastrado(s).")
                st.rerun()

st.subheader("Seus alunos")
df = repo.alunos_facil(cid)
if df.empty:
    st.info("Nenhum aluno ainda.")
    st.stop()
tab = df[["nome", "whatsapp", "valor", "vencimento", "ativo"]].copy()
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
