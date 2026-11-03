"""Comissão do divulgador (perfil Exclusivo).

Regra (ajustável em Promoções → Divulgadores, no geral ou só para um divulgador):
- faixas por nº de indicados PAGANTES ATIVOS ao mesmo tempo (ex.: 50 → 10%, 100 → 20%); a maior faixa alcançada
  fica (chegou a 100 e caiu para 80 → continua 20%);
- todo mês ele recebe a % da faixa sobre o que os indicados ATIVOS pagam naquele mês (caiu para 80 → sobre os 80);
- vale até a data `ate`; o pagamento é feito por Pix pelo administrador, que marca como pago (fica o histórico).
A linha do mês é recalculada enquanto não estiver paga; depois de paga, congela.
"""
from datetime import date

import pandas as pd

from core import db, planos as pl


def faixas_validas(faixas) -> list[dict]:
    """[{min, pct}] limpo e em ordem crescente de mínimo (linhas vazias/repetidas saem)."""
    out = {}
    for f in faixas or []:
        try:
            mn, pc = int(f.get("min")), float(f.get("pct"))
        except (TypeError, ValueError, AttributeError):
            continue
        if mn >= 1 and pc >= 0:
            out[mn] = pc
    return [dict(min=k, pct=out[k]) for k in sorted(out)]


def regra(emp: dict | None = None) -> dict:
    """Regra que vale para este divulgador: a própria (se tiver) por cima da geral."""
    c = pl.config("comissao")
    faixas = c.get("faixas")
    if not faixas and c.get("meta"):            # formato antigo (meta única + %)
        faixas = [dict(min=c["meta"], pct=c.get("pct") or 0)]
    r = dict(ativo=bool(c.get("ativo")), ate=str(c.get("ate") or "") or None, faixas=faixas_validas(faixas),
             propria=False)
    propria = (emp or {}).get("comissao_regra")
    if isinstance(propria, str):
        import json
        propria = json.loads(propria)
    if isinstance(propria, dict) and propria:
        if faixas_validas(propria.get("faixas")):
            r["faixas"] = faixas_validas(propria["faixas"])
        if propria.get("ate"):
            r["ate"] = str(propria["ate"])
        r["propria"] = True
    return r


def pct_da_faixa(n: int, faixas: list[dict]) -> float:
    pct = 0.0
    for f in faixas:
        if n >= f["min"]:
            pct = f["pct"]
    return pct


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
    """Situação do divulgador hoje. A % é a da MAIOR faixa já alcançada (alcançou, fica); a base é sempre o que os
    indicados ATIVOS pagam hoje. Com gravar=True guarda o pico e atualiza a linha do mês (se ainda não paga)."""
    emp = db.ao_vivo("select comissao_desde, comissao_pico, comissao_regra from condutores where id = cast(:c as uuid)",
                     c=str(cid))
    emp = emp.iloc[0].to_dict() if len(emp) else {}
    r = regra(emp)
    faixas = r["faixas"]
    desde, pico = emp.get("comissao_desde"), int(emp.get("comissao_pico") or 0)
    n, base = pagantes_ativos(cid, hoje)
    vigente = r["ativo"] and bool(faixas) and (not r["ate"] or hoje.isoformat() <= r["ate"])
    if vigente and n > pico:
        pico = n
        if gravar:
            db.gravar("update condutores set comissao_pico = :p where id = cast(:c as uuid) and comissao_pico < :p",
                      p=pico, c=str(cid))
    pct = pct_da_faixa(pico, faixas) if vigente else 0.0
    if gravar and vigente and desde is None and pct > 0:
        db.gravar("update condutores set comissao_desde = :d where id = cast(:c as uuid) and comissao_desde is null",
                  d=hoje, c=str(cid))
        desde = hoje
    valor = round(base * pct / 100, 2)
    comp = hoje.replace(day=1)
    if gravar and vigente and pct > 0:
        db.gravar("""insert into comissoes (condutor_id, competencia, ativos, base, valor, pct)
                     values (cast(:c as uuid), :m, :n, :b, :v, :p)
                     on conflict (condutor_id, competencia) do update
                       set ativos = excluded.ativos, base = excluded.base, valor = excluded.valor, pct = excluded.pct,
                           atualizado_em = now()
                     where comissoes.pago_em is null""", c=str(cid), m=comp, n=n, b=base, v=valor, p=pct)
    prox = next((f for f in faixas if f["min"] > pico), None)
    return dict(r, ativos=n, base=base, pct=pct, valor=valor, desde=desde, pico=pico, vigente=vigente,
                competencia=comp, proxima=prox, faltam=max(0, prox["min"] - n) if prox else 0)


def salvar_regra_propria(cid, faixas: list[dict] | None, ate: date | None):
    """Regra só deste divulgador; sem faixas e sem data = volta para a regra geral."""
    import json
    fx = faixas_validas(faixas)
    valor = {k: v for k, v in (("faixas", fx), ("ate", ate.isoformat() if ate else None)) if v}
    db.gravar("update condutores set comissao_regra = cast(:r as jsonb) where id = cast(:c as uuid)",
              r=json.dumps(valor) if valor else None, c=str(cid))


def historico(cid) -> pd.DataFrame:
    return db.ao_vivo("""select competencia, ativos, base, pct, valor, pago_em from comissoes
                         where condutor_id = cast(:c as uuid) order by competencia desc""", c=str(cid))


def divulgadores(hoje: date) -> pd.DataFrame:
    """Todos os Exclusivos (e quem já tem comissão), com a situação do mês e o total a pagar."""
    df = db.ao_vivo("""select c.id, c.nome, c.codigo_indicacao, c.chave_pix, c.comissao_desde, c.comissao_regra,
                              (select count(*) from condutores x where x.indicado_por = c.id) as indicados,
                              (select coalesce(sum(valor), 0) from comissoes k
                                where k.condutor_id = c.id and k.pago_em is null) as a_pagar,
                              (select coalesce(sum(valor), 0) from comissoes k
                                where k.condutor_id = c.id and k.pago_em is not null) as ja_pago
                       from condutores c
                       where c.plano_tipo = 'cortesia' and not c.parceiro
                          or exists (select 1 from comissoes k where k.condutor_id = c.id)
                       order by c.nome""")
    if df.empty:
        return df
    sit = [situacao(i, hoje) for i in df["id"]]
    df["ativos"] = [s["ativos"] for s in sit]
    df["mes"] = [s["valor"] for s in sit]
    df["pct"] = [s["pct"] for s in sit]
    df["pico"] = [s["pico"] for s in sit]
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
    if not regra()["ativo"]:
        return True
    ids = db.ao_vivo("select id from condutores where plano_tipo = 'cortesia' and not parceiro and ("
                     "comissao_desde is not null or exists (select 1 from condutores x where x.indicado_por = "
                     "condutores.id))")
    for i in ids["id"] if len(ids) else []:
        situacao(i, hoje)
    return True
