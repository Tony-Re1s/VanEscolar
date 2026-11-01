"""Comissão do divulgador (perfil Exclusivo).

Regra (ajustável em Promoções → Divulgadores):
- destrava quando o divulgador chega a `meta` indicados PAGANTES ATIVOS ao mesmo tempo — destravou, fica;
- a partir daí, todo mês ele recebe `pct`% do que os indicados pagantes ATIVOS pagam naquele mês
  (caiu para 98 ativos → recebe sobre os 98);
- vale até a data `ate`; o pagamento é feito por Pix pelo administrador, que marca como pago (fica o histórico).
A linha do mês é recalculada enquanto não estiver paga; depois de paga, congela.
"""
from datetime import date

import pandas as pd

from core import db, planos as pl


def _cfg() -> dict:
    c = pl.config("comissao")
    return dict(ativo=bool(c.get("ativo")), meta=int(c.get("meta") or 100), pct=float(c.get("pct") or 0),
                ate=str(c.get("ate") or "") or None)


def pagantes_ativos(cid, hoje: date, cat: dict | None = None) -> tuple[int, float]:
    """(quantos indicados pagam hoje, quanto pagam por mês somados)."""
    cat = cat or pl.catalogo()
    df = db.ao_vivo("select * from condutores where indicado_por = cast(:c as uuid) and ativo", c=str(cid))
    n, base = 0, 0.0
    for emp in df.to_dict("records"):
        v = pl.preco_vigente(emp, hoje, cat)
        if v > 0:
            n += 1
            base += v
    return n, round(base, 2)


def situacao(cid, hoje: date, gravar: bool = True) -> dict:
    """Situação do divulgador hoje; com gravar=True destrava (se bateu a meta) e atualiza a linha do mês."""
    cfg = _cfg()
    emp = db.um("select comissao_desde from condutores where id = cast(:c as uuid)", c=str(cid)) or {}
    desde = emp.get("comissao_desde")
    n, base = pagantes_ativos(cid, hoje)
    vigente = cfg["ativo"] and (not cfg["ate"] or hoje.isoformat() <= cfg["ate"])
    if gravar and vigente and desde is None and n >= cfg["meta"]:
        db.gravar("update condutores set comissao_desde = :d where id = cast(:c as uuid) and comissao_desde is null",
                  d=hoje, c=str(cid))
        desde = hoje
    valor = round(base * cfg["pct"] / 100, 2) if (vigente and desde) else 0.0
    comp = hoje.replace(day=1)
    if gravar and vigente and desde:
        db.gravar("""insert into comissoes (condutor_id, competencia, ativos, base, valor)
                     values (cast(:c as uuid), :m, :n, :b, :v)
                     on conflict (condutor_id, competencia) do update
                       set ativos = excluded.ativos, base = excluded.base, valor = excluded.valor, atualizado_em = now()
                     where comissoes.pago_em is null""", c=str(cid), m=comp, n=n, b=base, v=valor)
    return dict(cfg, ativos=n, base=base, valor=valor, desde=desde, vigente=vigente, competencia=comp,
                faltam=max(0, cfg["meta"] - n))


def historico(cid) -> pd.DataFrame:
    return db.ao_vivo("""select competencia, ativos, base, valor, pago_em from comissoes
                         where condutor_id = cast(:c as uuid) order by competencia desc""", c=str(cid))


def divulgadores(hoje: date) -> pd.DataFrame:
    """Todos os Exclusivos (e quem já tem comissão), com a situação do mês e o total a pagar."""
    df = db.ao_vivo("""select c.id, c.nome, c.codigo_indicacao, c.chave_pix, c.comissao_desde,
                              (select count(*) from condutores x where x.indicado_por = c.id) as indicados,
                              (select coalesce(sum(valor), 0) from comissoes k
                                where k.condutor_id = c.id and k.pago_em is null) as a_pagar,
                              (select coalesce(sum(valor), 0) from comissoes k
                                where k.condutor_id = c.id and k.pago_em is not null) as ja_pago
                       from condutores c
                       where c.plano_tipo = 'cortesia' or exists (select 1 from comissoes k where k.condutor_id = c.id)
                       order by c.nome""")
    if df.empty:
        return df
    sit = [situacao(i, hoje) for i in df["id"]]
    df["ativos"] = [s["ativos"] for s in sit]
    df["mes"] = [s["valor"] for s in sit]
    # a_pagar já inclui o mês atual (recalculado acima) — relê para pegar o valor atualizado
    ap = db.ao_vivo("""select condutor_id as id, sum(valor) as a_pagar from comissoes where pago_em is null
                       group by condutor_id""")
    m = dict(zip(ap["id"].astype(str), ap["a_pagar"])) if len(ap) else {}
    df["a_pagar"] = [float(m.get(str(i), 0) or 0) for i in df["id"]]
    return df


def pendentes(cid) -> pd.DataFrame:
    return db.ao_vivo("""select competencia, ativos, valor from comissoes
                         where condutor_id = cast(:c as uuid) and pago_em is null and valor > 0
                         order by competencia""", c=str(cid))


def marcar_pago(cid, competencias: list, quando: date) -> int:
    n = 0
    for m in competencias:
        r = db.gravar("""update comissoes set pago_em = :q where condutor_id = cast(:c as uuid) and competencia = :m
                         and pago_em is null returning competencia""", q=quando, c=str(cid), m=m)
        n += 1 if r else 0
    return n


def desfazer_pago(cid, competencia) -> None:
    db.gravar("update comissoes set pago_em = null where condutor_id = cast(:c as uuid) and competencia = :m",
              c=str(cid), m=competencia)


def atualizar_todos(hoje: date) -> bool:
    """Uma vez por dia (no 1º acesso de qualquer pessoa): atualiza a comissão do mês de todos os divulgadores.
    Assim o mês fecha com os números do último dia, mesmo que ninguém abra a página do divulgador."""
    r = db.um("select valor from config where chave = 'comissao_dia'")
    if r and isinstance(r["valor"], dict) and r["valor"].get("dia") == hoje.isoformat():
        return False
    db.gravar("""insert into config (chave, valor) values ('comissao_dia', cast(:v as jsonb))
                 on conflict (chave) do update set valor = excluded.valor""", v=f'{{"dia": "{hoje.isoformat()}"}}')
    if not _cfg()["ativo"]:
        return True
    ids = db.ao_vivo("select id from condutores where plano_tipo = 'cortesia' and comissao_desde is not null "
                     "or plano_tipo = 'cortesia' and exists (select 1 from condutores x where x.indicado_por = "
                     "condutores.id)")
    for i in ids["id"] if len(ids) else []:
        situacao(i, hoje)
    return True
