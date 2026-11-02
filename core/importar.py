"""Importar alunos de uma planilha (Excel, CSV ou colado do Google Planilhas).

Fluxo: o tio baixa o modelo, preenche, sobe o arquivo → `ler()` acha as colunas (pelo nome, sem ligar para
acento/maiúscula) → `validar()` marca erros e duplicados → `importar()` cria escolas que faltam, os alunos e os
responsáveis (financeiros) com o WhatsApp.
"""
from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd

from core import db, repo
from core.fmt import hoje, so_digitos

# coluna do modelo → (chave interna, apelidos aceitos)
COLUNAS = [
    ("Aluno", "nome", ["aluno", "nome", "nome do aluno", "crianca", "passageiro", "estudante"]),
    ("Responsável", "responsavel", ["responsavel", "nome do responsavel", "mae", "pai", "contato"]),
    ("WhatsApp", "whatsapp", ["whatsapp", "whats", "zap", "telefone", "celular", "fone", "telefone do responsavel"]),
    ("Mensalidade", "valor", ["mensalidade", "valor", "preco", "valor mensal"]),
    ("Dia do vencimento", "dia", ["dia do vencimento", "vencimento", "dia", "vence dia", "dia de pagamento"]),
    ("Escola", "escola", ["escola", "colegio", "nome da escola"]),
    ("Turno", "turno", ["turno", "periodo", "horario"]),
    ("Endereço", "endereco", ["endereco", "endereco do aluno", "rua", "endereco de busca"]),
]
TURNOS = {"manha": "manha", "matutino": "manha", "m": "manha", "tarde": "tarde", "vespertino": "tarde",
          "t": "tarde", "integral": "integral", "i": "integral", "noite": "noite", "noturno": "noite", "n": "noite"}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip().replace("  ", " ")


# ---------------------------------------------------------------- modelo
def modelo_xlsx() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()
    ws = wb.active
    ws.title = "Alunos"
    cab = [c[0] for c in COLUNAS]
    ws.append(cab)
    ws.append(["Maria Souza (exemplo — pode apagar)", "Ana Souza", "(11) 98888-7777", 350, 10,
               "Escola Estadual Centro", "Manhã", "Rua das Flores, 120"])
    larg = [34, 22, 18, 14, 18, 28, 12, 34]
    for i, w in enumerate(larg):
        col = chr(65 + i)
        ws.column_dimensions[col].width = w
        cel = ws[f"{col}1"]
        cel.font = Font(bold=True, color="FFFFFF")
        cel.fill = PatternFill("solid", fgColor="F59E0B" if i == 0 else "1E3A8A")
        cel.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 22
    for c in ws[2]:
        c.font = Font(italic=True, color="6B7280")
    ws.freeze_panes = "A2"
    dv = DataValidation(type="list", formula1='"Manhã,Tarde,Integral,Noite"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add("G2:G500")

    aj = wb.create_sheet("Como preencher")
    aj.column_dimensions["A"].width = 22
    aj.column_dimensions["B"].width = 80
    aj.append(["Coluna", "O que colocar"])
    for c in aj[1]:
        c.font = Font(bold=True)
    for linha in [
        ("Aluno", "OBRIGATÓRIO. Nome do aluno. Um aluno por linha."),
        ("Responsável", "Nome de quem paga (mãe, pai…). Se ficar vazio, vira \"Responsável de <aluno>\"."),
        ("WhatsApp", "Celular do responsável, com DDD. Ex.: (11) 98888-7777. É por ele que saem os avisos e cobranças."),
        ("Mensalidade", "Valor em reais. Ex.: 350 ou 350,00."),
        ("Dia do vencimento", "De 1 a 28. Se ficar vazio, usa o dia padrão da sua empresa."),
        ("Escola", "Nome da escola. Se ainda não existir no app, ela é criada."),
        ("Turno", "Manhã, Tarde, Integral ou Noite. Vazio = Manhã."),
        ("Endereço", "Onde buscar o aluno (rua, número, bairro)."),
        ("", ""),
        ("Dica", "Apague a linha de exemplo da Maria antes de importar. Pode usar Excel ou Google Planilhas."),
    ]:
        aj.append(list(linha))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- leitura
def ler(arquivo=None, texto: str | None = None) -> pd.DataFrame:
    """Lê xlsx/csv (arquivo enviado) ou texto colado (tabulações do Google Planilhas / Excel, ou ;)."""
    if arquivo is not None:
        nome = (getattr(arquivo, "name", "") or "").lower()
        dados = arquivo.getvalue() if hasattr(arquivo, "getvalue") else arquivo.read()
        if nome.endswith((".xlsx", ".xlsm")):
            bruto = pd.read_excel(io.BytesIO(dados), dtype=str, header=None)
        else:
            txt = None
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    txt = dados.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            bruto = _ler_texto(txt or "")
    else:
        bruto = _ler_texto(texto or "")
    return _mapear(bruto)


def _ler_texto(txt: str) -> pd.DataFrame:
    linhas = [ln for ln in txt.splitlines() if ln.strip()]
    if not linhas:
        return pd.DataFrame()
    sep = "\t" if "\t" in linhas[0] else (";" if ";" in linhas[0] else ",")
    return pd.DataFrame([[p.strip() for p in ln.split(sep)] for ln in linhas], dtype=str)


def _mapear(bruto: pd.DataFrame) -> pd.DataFrame:
    """Acha a linha de cabeçalho e as colunas pelo nome. Sem cabeçalho → ordem do modelo."""
    if bruto.empty:
        return pd.DataFrame(columns=[c[1] for c in COLUNAS])
    bruto = bruto.fillna("")
    apelidos = {a: chave for _, chave, lst in COLUNAS for a in lst}
    mapa, ini = {}, 0
    for i in range(min(5, len(bruto))):
        achou = {}
        for j, v in enumerate(bruto.iloc[i]):
            chave = apelidos.get(_norm(v))
            if chave and chave not in achou.values():
                achou[j] = chave
        if "nome" in achou.values():
            mapa, ini = achou, i + 1
            break
    if not mapa:      # sem cabeçalho: assume a ordem do modelo
        mapa = {j: COLUNAS[j][1] for j in range(min(len(COLUNAS), bruto.shape[1]))}
    df = pd.DataFrame({chave: bruto.iloc[ini:, j].astype(str).str.strip() for j, chave in mapa.items()})
    for _, chave, _ in COLUNAS:
        if chave not in df:
            df[chave] = ""
    df = df[[c[1] for c in COLUNAS]]
    df = df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)]
    df = df[~df["nome"].str.contains("pode apagar", case=False, na=False)]       # linha de exemplo do modelo
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- validação
def _valor(txt):
    t = str(txt or "").replace("R$", "").replace(" ", "").strip()
    if not t:
        return 0.0
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return round(float(t), 2)
    except ValueError:
        return None


def validar(cid, df: pd.DataFrame, dia_padrao: int) -> pd.DataFrame:
    """Devolve o df com valor/dia/turno/whatsapp normalizados + colunas `situacao` (ok|erro|duplicado) e `aviso`."""
    existentes = set(_norm(n) for n in db.ao_vivo("select nome from passageiros where condutor_id = :cid",
                                                   cid=cid)["nome"])
    vistos = set()
    out = []
    for _, r in df.iterrows():
        x = dict(r)
        avisos, sit = [], "ok"
        nome = str(x["nome"]).strip()
        if not nome:
            sit = "erro"
            avisos.append("sem nome do aluno")
        v = _valor(x["valor"])
        if v is None:
            sit = "erro"
            avisos.append(f"mensalidade inválida ({x['valor']})")
            v = 0.0
        x["valor"] = v
        d = so_digitos(str(x["dia"] or ""))
        if d and not (1 <= int(d) <= 31):
            sit = "erro"
            avisos.append(f"dia inválido ({x['dia']})")
        x["dia"] = min(28, int(d)) if d and 1 <= int(d) <= 31 else dia_padrao
        w = so_digitos(str(x["whatsapp"] or ""))
        if w.startswith("55") and len(w) > 11:
            w = w[2:]
        if w and len(w) not in (10, 11):
            sit = "erro" if sit == "erro" else "ok"
            avisos.append("WhatsApp incompleto (falta DDD?) — vai sem WhatsApp")
            w = ""
        x["whatsapp"] = w
        t = _norm(x["turno"])
        x["turno"] = TURNOS.get(t, "manha")
        if t and t not in TURNOS:
            avisos.append(f"turno \"{r['turno']}\" não reconhecido — ficou Manhã")
        chave = _norm(nome)
        if sit != "erro" and chave in existentes:
            sit = "duplicado"
            avisos.append("já existe um aluno com esse nome — não será importado")
        elif sit != "erro" and chave in vistos:
            sit = "duplicado"
            avisos.append("nome repetido na planilha — só a 1ª linha entra")
        vistos.add(chave)
        x["situacao"], x["aviso"] = sit, "; ".join(avisos)
        out.append(x)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- importação
def importar(cid, df: pd.DataFrame, van) -> int:
    """Importa só as linhas com situacao == 'ok'. Devolve quantos alunos criou."""
    ok = df[df["situacao"] == "ok"]
    esc = {_norm(n): str(i) for i, n in db.ao_vivo("select id, nome from escolas where condutor_id = :cid",
                                                     cid=cid)[["id", "nome"]].itertuples(index=False)}
    n = 0
    for _, x in ok.iterrows():
        eid = None
        nome_esc = str(x["escola"] or "").strip()
        if nome_esc:
            eid = esc.get(_norm(nome_esc))
            if not eid:
                repo.salvar_escola(cid, dict(nome=nome_esc, endereco=None, telefone=None, entrada_manha=None,
                                             saida_manha=None, entrada_tarde=None, saida_tarde=None, ativo=True))
                eid = str(db.ao_vivo("""select id from escolas where condutor_id = :cid and nome = :n
                                        order by criado_em desc nulls last limit 1""",
                                     cid=cid, n=nome_esc).iloc[0]["id"])
                esc[_norm(nome_esc)] = eid
        nome = str(x["nome"]).strip()
        pid = repo.salvar_passageiro(cid, dict(
            nome=nome, escola_id=eid, van_id=van, turno=x["turno"], endereco=(str(x["endereco"]).strip() or None),
            mensalidade=x["valor"] or 0, dia_vencimento=int(x["dia"]), faz_ida=True, faz_volta=True, ativo=True,
            inicio=hoje()))
        resp = str(x["responsavel"] or "").strip()
        if x["whatsapp"] or resp:
            repo.vincular_responsavel(cid, pid, dict(nome=resp or f"Responsável de {nome.split()[0]}",
                                                     telefone=x["whatsapp"] or None), financeiro=True)
        n += 1
    return n
