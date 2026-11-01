"""Regra única de "pagamento confirmado" — usada pelo app (botão do admin) e pela sincronização com o Asaas
(que também roda fora do Streamlit, no GitHub Actions). Só SQL: recebe a conexão/sessão já aberta."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from core.fmt import somar_meses


def _config(s, chave: str, padrao: dict) -> dict:
    r = s.execute(text("select valor from config where chave = :c"), dict(c=chave)).first()
    out = dict(padrao)
    if r and isinstance(r[0], dict):
        out.update(r[0])
    return out


def contar_indicacao(s, emp: dict):
    """1º pagamento de quem foi indicado: soma 1 para quem indicou e, a cada meta, dá os meses grátis."""
    if not emp.get("indicado_por") or emp.get("indicacao_contada"):
        return
    cfg = _config(s, "indicacao", {"meta": 10, "premio_meses": 2})
    meta, premio = max(1, int(cfg.get("meta") or 10)), int(cfg.get("premio_meses") or 0)
    s.execute(text("update condutores set indicacao_contada = true where id = cast(:i as uuid)"), dict(i=str(emp["id"])))
    # Exclusivo (divulgador) não ganha meses grátis — o prêmio dele é a comissão
    s.execute(text(f"""update condutores set indicacoes_pagas = indicacoes_pagas + 1,
                         meses_gratis = meses_gratis + case when (indicacoes_pagas + 1) % {meta} = 0
                                                             and coalesce(plano_tipo, 'pago') <> 'cortesia'
                                                            then {premio} else 0 end
                       where id = cast(:i as uuid)"""), dict(i=str(emp["indicado_por"])))


def aplicar_pagamento(s, emp: dict, hoje: date, pedido: dict | None = None) -> date:
    """Com `pedido`: aplica o plano/preço pedido. Sem: renova o plano atual (1 mês, ou 12 no anual).
    Conta a indicação no 1º pagamento. Devolve a nova data de validade."""
    plano = (pedido or {}).get("plano") or emp["plano"]
    periodo = (pedido or {}).get("periodo") or emp.get("periodo") or "mensal"
    meses = 12 if periodo == "anual" else 1
    tipo = emp.get("plano_tipo") or "pago"
    renovando = emp.get("plano") == plano and tipo == "pago" and emp.get("plano_ate")
    base = max(emp["plano_ate"], hoje) if renovando else hoje
    ate = somar_meses(base, meses)
    cid = str(emp["id"])
    if pedido and pedido.get("pausa"):
        dias = int(pedido.get("pausa_dias") or 60)
        s.execute(text("""update condutores set plano=:plano, plano_tipo='pago', plano_ate=:ate, periodo='mensal',
                            pausa_ate=:pa, pausa_ultima=:hoje, cancelado_em=null, pedido=null
                          where id = cast(:cid as uuid)"""),
                  dict(plano=plano, ate=ate, pa=hoje + timedelta(days=dias), hoje=hoje, cid=cid))
    elif pedido:
        dur = pedido.get("duracao_meses")
        s.execute(text("""update condutores set plano=:plano, plano_tipo='pago', plano_ate=:ate, periodo=:periodo,
                            preco_mensal=:preco, desconto_origem=:origem, desconto_ate=:dat,
                            vip = vip or :vip, cupom_id = coalesce(cast(:cupom as uuid), cupom_id), pedido = null,
                            cancelado_em = null
                          where id = cast(:cid as uuid)"""),
                  dict(plano=plano, ate=ate, periodo=periodo, preco=pedido.get("preco"),
                       origem=pedido.get("origem"), dat=somar_meses(hoje, int(dur)) if dur else None,
                       vip=bool(pedido.get("vip_novo") or pedido.get("origem") == "vip"),
                       cupom=pedido.get("cupom_id"), cid=cid))
        if pedido.get("cupom_id"):
            s.execute(text("""insert into cupons_usos (cupom_id, condutor_id)
                              values (cast(:c as uuid), cast(:cid as uuid)) on conflict do nothing"""),
                      dict(c=str(pedido["cupom_id"]), cid=cid))
    else:
        s.execute(text("""update condutores set plano_tipo='pago', plano_ate=:ate, periodo=:periodo, cancelado_em=null
                          where id = cast(:cid as uuid)"""), dict(ate=ate, periodo=periodo, cid=cid))
    contar_indicacao(s, emp)
    return ate
