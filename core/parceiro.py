"""Programa Parceiros Turminha — o "Bônus Parceiro".

Parceiro = quem indica o app sem usá-lo no dia a dia (ex.: vendedor de vans). O Tony escolhe a dedo quem vira
parceiro (Promoções → Parceiros): a conta fica com um plano liberado sem cobrar (Pro por padrão) e a marcação
`parceiro`, que liga o painel "Parceiros Turminha" (e não o laboratório do Exclusivo).

Regras (contrato do programa, cláusula 3):
- mensal: R$ 10,00 na 1ª mensalidade paga pelo indicado e 20% de cada mensalidade a partir da 2ª;
- trimestral/semestral/anual: 1 mensalidade (valor pago ÷ meses) + 20% dos outros meses do período;
- renovação de período: 20% do valor pago; o teste grátis não gera bônus;
- apurado 7 dias depois do pagamento (arrependimento/estorno) e pago por Pix até o dia 10 do mês seguinte;
- vale para pagamentos feitos até 31/12/2027.

`registrar_bonus` é chamado pela regra única de pagamento (core/cobranca.py) e só usa SQL — roda também fora do
Streamlit (sincronização do Asaas no GitHub Actions). O resto usa core.db (importado dentro das funções).
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

from sqlalchemy import text

FIM = date(2027, 12, 31)
PRIMEIRA = 10.0
PCT = 0.20
DIAS_LIBERA = 7
TIPOS = {"primeira": "1ª mensalidade paga", "mensal": "20% da mensalidade",
         "periodo": "1 mensalidade + 20% do período", "renovacao": "20% da renovação"}


def calcular(base: float, meses: int, ja_teve_bonus: bool, ja_teve_periodo: bool) -> tuple[str, float]:
    """(tipo, valor) do bônus de um pagamento de `base` reais cobrindo `meses` meses."""
    base, meses = float(base or 0), max(1, int(meses or 1))
    if base <= 0:
        return "mensal", 0.0
    if meses < 3:                                   # mensal
        if not ja_teve_bonus:
            return "primeira", min(PRIMEIRA, base)
        return "mensal", round(base * PCT, 2)
    if not ja_teve_periodo:                         # 1ª compra de período: 1 mensalidade + 20% dos outros meses
        mes = base / meses
        return "periodo", round(mes + PCT * mes * (meses - 1), 2)
    return "renovacao", round(base * PCT, 2)


def dia_de_pagar(libera_em: date) -> date:
    """Até o dia 10 do mês seguinte ao da apuração."""
    prox = (libera_em.replace(day=1) + timedelta(days=32)).replace(day=1)
    return prox.replace(day=10)


def registrar_bonus(s, cliente: dict, hoje: date, valor_pago: float | None, meses: int, ref: str) -> float:
    """Gera o bônus deste pagamento para o parceiro que indicou o cliente (se for parceiro). Idempotente por `ref`."""
    pid = cliente.get("indicado_por")
    if not pid or hoje > FIM or not valor_pago or str(pid) == str(cliente["id"]):
        return 0.0
    par = s.execute(text("select parceiro from condutores where id = cast(:p as uuid)"), dict(p=str(pid))).first()
    if not par or not par[0]:
        return 0.0
    ant = s.execute(text("""select count(*), count(*) filter (where tipo in ('periodo', 'renovacao'))
                            from bonus_parceiro where cliente_id = cast(:c as uuid) and not estornado"""),
                    dict(c=str(cliente["id"]))).first()
    tipo, valor = calcular(valor_pago, meses, bool(ant[0]), bool(ant[1]))
    if valor <= 0:
        return 0.0
    s.execute(text("""insert into bonus_parceiro (parceiro_id, cliente_id, ref, pago_cliente, meses, base, tipo, valor,
                                                  libera_em)
                      values (cast(:p as uuid), cast(:c as uuid), :ref, :d, :m, :b, :t, :v, :lib)
                      on conflict (ref) do nothing"""),
              dict(p=str(pid), c=str(cliente["id"]), ref=str(ref)[:120], d=hoje, m=int(meses), b=round(valor_pago, 2),
                   t=tipo, v=valor, lib=hoje + timedelta(days=DIAS_LIBERA)))
    return valor


# ---------------------------------------------------------------- consultas (app)
def eh_parceiro(empresa: dict | None) -> bool:
    return bool((empresa or {}).get("parceiro"))


def nome_curto(nome: str | None) -> str:
    """Só o mínimo para conferir o bônus (contrato 6.2): as duas primeiras palavras."""
    return " ".join(str(nome or "").split()[:2]) or "—"


def indicados(pid):
    from core import db
    return db.ao_vivo("""select c.id, c.nome, c.plano, c.plano_tipo, c.plano_ate, c.periodo, c.ativo,
                                c.criado_em::date as desde,
                                coalesce((select sum(b.valor) from bonus_parceiro b
                                          where b.cliente_id = c.id and not b.estornado), 0) as bonus
                         from condutores c where c.indicado_por = cast(:p as uuid) order by c.criado_em desc""",
                      p=str(pid))


def extrato(pid):
    from core import db
    return db.ao_vivo("""select b.*, c.nome as cliente from bonus_parceiro b
                         left join condutores c on c.id = b.cliente_id
                         where b.parceiro_id = cast(:p as uuid) order by b.pago_cliente desc, b.criado_em desc""",
                      p=str(pid))


def resumo(pid, hoje: date) -> dict:
    """liberado (a receber), aguardando os 7 dias, já recebido, ativos."""
    from core import db
    r = db.um("""select coalesce(sum(valor) filter (where pago_em is null and libera_em <= :h), 0) as liberado,
                        coalesce(sum(valor) filter (where pago_em is null and libera_em > :h), 0) as aguardando,
                        coalesce(sum(valor) filter (where pago_em is not null), 0) as recebido,
                        min(libera_em) filter (where pago_em is null) as prox_lib
                 from bonus_parceiro where parceiro_id = cast(:p as uuid) and not estornado""", p=str(pid), h=hoje)
    r = dict(r or {})
    r["prazo"] = dia_de_pagar(r["prox_lib"]) if r.get("prox_lib") else None
    return r


def parceiros(hoje: date):
    """Todos os parceiros, com indicados, ativos e quanto pagar (para o admin)."""
    from core import db
    return db.ao_vivo("""select c.id, c.nome, u.email, c.chave_pix, c.codigo_indicacao, c.plano, c.parceiro_desde,
                                c.parceiro_contrato is not null as assinou,
                                (select count(*) from condutores x where x.indicado_por = c.id) as indicados,
                                (select count(*) from condutores x where x.indicado_por = c.id and x.ativo
                                   and x.plano_tipo = 'pago' and x.plano_ate >= :h) as ativos,
                                (select coalesce(sum(valor), 0) from bonus_parceiro b where b.parceiro_id = c.id
                                   and not b.estornado and b.pago_em is null and b.libera_em <= :h) as a_pagar,
                                (select coalesce(sum(valor), 0) from bonus_parceiro b where b.parceiro_id = c.id
                                   and not b.estornado and b.pago_em is null and b.libera_em > :h) as aguardando,
                                (select coalesce(sum(valor), 0) from bonus_parceiro b where b.parceiro_id = c.id
                                   and not b.estornado and b.pago_em is not null) as pago
                         from condutores c left join usuarios u on u.id = c.usuario_id
                         where c.parceiro order by c.nome""", h=hoje)


def marcar_pago(pid, hoje: date) -> float:
    """Marca como pago tudo que já está liberado e ainda não foi pago. Devolve o total."""
    from core import db
    r = db.gravar("""with x as (update bonus_parceiro set pago_em = :h
                                where parceiro_id = cast(:p as uuid) and pago_em is null and not estornado
                                  and libera_em <= :h returning valor)
                     select coalesce(sum(valor), 0) as total from x""", p=str(pid), h=hoje)
    return float((r or {}).get("total") or 0)


def estornar(bonus_id) -> None:
    from core import db
    db.gravar("update bonus_parceiro set estornado = true where id = cast(:i as uuid) and pago_em is null",
              i=str(bonus_id))


def codigo_livre(codigo: str, cid) -> bool:
    from core import db
    return db.um("select 1 as x from condutores where codigo_indicacao = :c and id <> cast(:i as uuid)",
                 c=codigo, i=str(cid)) is None


def tornar_parceiro(cid, plano: str, codigo: str | None, hoje: date):
    from core import db
    db.gravar("""update condutores set parceiro = true, parceiro_desde = coalesce(parceiro_desde, :h),
                   plano = :pl, plano_tipo = 'cortesia', plano_ate = null,
                   codigo_indicacao = coalesce(nullif(:cod, ''), codigo_indicacao)
                 where id = cast(:c as uuid)""", h=hoje, pl=plano, cod=(codigo or "").strip().upper(), c=str(cid))


def encerrar_parceiro(cid):
    """Encerra a parceria (contrato 7): não gera bônus novo; o acesso grátis acaba (vira sem plano)."""
    from core import db
    db.gravar("""update condutores set parceiro = false, plano_tipo = 'pago', plano_ate = current_date
                 where id = cast(:c as uuid)""", c=str(cid))


def sem_indicacao(dias: int = 30):
    """Contas novas (até `dias`) que entraram sem link — para vincular na mão."""
    from core import db
    return db.ao_vivo("""select id, nome, criado_em::date as desde from condutores
                         where indicado_por is null and not parceiro and criado_em >= now() - make_interval(days => :d)
                         order by criado_em desc""", d=int(dias))


def vincular(cliente_id, parceiro_id):
    from core import db
    db.gravar("""update condutores set indicado_por = cast(:p as uuid)
                 where id = cast(:c as uuid) and indicado_por is null and id <> cast(:p as uuid)""",
              p=str(parceiro_id), c=str(cliente_id))


# ---------------------------------------------------------------- contrato (aceite eletrônico)
VERSAO_CONTRATO = "2026-11-03"


def contrato_texto(titular: dict, parceiro: dict) -> str:
    """Texto do contrato. Os dados do titular (CPF/endereço) vêm dos Secrets — nada pessoal fica no repositório."""
    from core.contrato_parceiro import MODELO
    def v(d, k):
        return str(d.get(k) or "").strip() or "[não informado]"
    return MODELO.format(t_nome=v(titular, "nome"), t_doc=v(titular, "doc"), t_end=v(titular, "endereco"),
                         p_nome=v(parceiro, "nome"), p_doc=v(parceiro, "doc"), p_end=v(parceiro, "endereco"),
                         p_email=v(parceiro, "email"), p_whats=v(parceiro, "whatsapp"), p_pix=v(parceiro, "pix"))


def codigo_verificacao(texto: str, dados: dict) -> str:
    h = hashlib.sha256((texto + json.dumps(dados, sort_keys=True, default=str)).encode()).hexdigest().upper()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}"


def salvar_aceite(cid, dados: dict, texto: str) -> str:
    from core import db
    dados = dict(dados, versao=VERSAO_CONTRATO)
    dados["codigo"] = codigo_verificacao(texto, dados)
    db.gravar("""update condutores set parceiro_contrato = cast(:d as jsonb), chave_pix = :pix
                 where id = cast(:c as uuid)""", d=json.dumps(dados, ensure_ascii=False, default=str),
              pix=dados.get("pix"), c=str(cid))
    return dados["codigo"]


def contrato_pdf(texto: str, aceite: dict) -> bytes:
    import io
    import re
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title="Contrato de Parceria — Parceiros Turminha")
    corpo = ParagraphStyle("c", fontName="Helvetica", fontSize=9.5, leading=13, alignment=TA_JUSTIFY, spaceAfter=5)
    tit = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=12, leading=16, spaceAfter=8)
    sub = ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=10, leading=14, spaceBefore=6, spaceAfter=3)
    els = []
    for linha in texto.splitlines():
        ln = linha.strip()
        if not ln:
            continue
        ln = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ln = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", ln)
        if ln.startswith("# "):
            els.append(Paragraph(ln[2:], tit))
        elif ln.startswith("## "):
            els.append(Paragraph(ln[3:], sub))
        else:
            els.append(Paragraph(ln, corpo))
    els.append(Spacer(1, 10))
    els.append(Paragraph("<b>Assinatura eletrônica do PARCEIRO</b>", sub))
    for rot, k in (("Nome", "nome"), ("Login (Google)", "email"), ("Data e hora", "aceito_em"), ("IP", "ip"),
                   ("Versão do contrato", "versao"), ("Código de verificação", "codigo")):
        els.append(Paragraph(f"{rot}: {aceite.get(k) or '—'}", corpo))
    doc.build(els)
    return buf.getvalue()
