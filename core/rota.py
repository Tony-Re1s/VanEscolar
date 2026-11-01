"""Situação das crianças na rota do trecho (sem Streamlit): quem está na van, quem falta, quem já foi concluído.

Ida (casa → escola): Embarcou = pegou em casa (está na van) → Na escola = desembarcou na escola.
Volta (escola → casa): ao iniciar, todas estão na van → Entregue = desembarcou em casa.
"""
import pandas as pd


def _st(v):
    return v if isinstance(v, str) else None


def nao_vai(r) -> bool:
    s = _st(r.status)
    return s == "faltou" or (bool(r.avisou) and s is None)


def situacao(df: pd.DataFrame, trecho: str) -> dict:
    """Listas de nomes: na_van (embarcou e não desembarcou), a_buscar (ida, ainda não embarcou),
    concluidos, ausentes; e `pendentes` = quem impede de finalizar a rota."""
    out = dict(na_van=[], a_buscar=[], concluidos=[], ausentes=[])
    for r in df.itertuples():
        s = _st(r.status)
        if nao_vai(r):
            out["ausentes"].append(r.nome)
        elif s == "desembarcou":
            out["concluidos"].append(r.nome)
        elif s == "embarcou" or trecho == "volta":
            out["na_van"].append(r.nome)
        else:
            out["a_buscar"].append(r.nome)
    out["pendentes"] = len(out["na_van"]) + len(out["a_buscar"])
    return out


def em_andamento_para(rota: dict | None, status: str | None, ausente: bool) -> bool:
    """O responsável acompanha a van? Só com a rota em andamento e a criança ainda não concluída nem ausente."""
    if not rota or pd.isna(rota.get("iniciada_em")):
        return False
    fim = rota.get("finalizada_em")
    if fim is not None and not pd.isna(fim):
        return False
    return not ausente and status not in ("desembarcou", "faltou")
