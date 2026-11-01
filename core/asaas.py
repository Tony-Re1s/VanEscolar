"""Integração com o Asaas: assinatura recorrente do gestor (Pix, boleto ou cartão — ele escolhe na página do Asaas).

O Streamlit não recebe webhooks, então o app CONSULTA o Asaas (`sincronizar`): ao abrir Meu plano, pelo botão no
painel de Assinantes e a cada 30 min pelo GitHub Actions (scripts/asaas_sync.py). Não depende do Streamlit.

Configuração (Secrets do Streamlit ou variáveis de ambiente no GitHub):
    [asaas]
    api_key = "$aact_hmlg_..."   # sandbox; em produção "$aact_prod_..."
    ambiente = "sandbox"          # ou "producao"
"""
from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from sqlalchemy import text

URLS = {"sandbox": "https://api-sandbox.asaas.com/v3", "producao": "https://api.asaas.com/v3"}
PAGO = {"RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"}
STATUS = {"PENDING": "aguardando pagamento", "OVERDUE": "vencida", "RECEIVED": "paga", "CONFIRMED": "paga",
          "RECEIVED_IN_CASH": "paga", "REFUNDED": "estornada", "REFUND_REQUESTED": "estorno pedido"}


class AsaasErro(Exception):
    pass


class Asaas:
    def __init__(self, api_key: str, ambiente: str = "sandbox", base_url: str | None = None):
        if not api_key:
            raise AsaasErro("Chave da API do Asaas não configurada.")
        self.key = api_key
        self.base = (base_url or URLS.get(ambiente) or URLS["sandbox"]).rstrip("/")
        self.ambiente = ambiente

    # ------------------------------------------------------------ HTTP
    def _req(self, metodo: str, caminho: str, corpo: dict | None = None, params: dict | None = None):
        url = self.base + caminho + ("?" + urllib.parse.urlencode(params) if params else "")
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(url, data=dados, method=metodo, headers={
            "access_token": self.key, "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "PequenosABordo/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                txt = r.read().decode() or "{}"
                return json.loads(txt)
        except urllib.error.HTTPError as e:
            try:
                erros = json.loads(e.read().decode()).get("errors") or []
                msg = "; ".join(x.get("description", "") for x in erros) or str(e)
            except Exception:  # noqa: BLE001
                msg = str(e)
            if e.code == 401:
                msg = "Chave da API do Asaas inválida (ou de outro ambiente: sandbox × produção)."
            raise AsaasErro(msg) from e
        except urllib.error.URLError as e:
            raise AsaasErro(f"Não consegui falar com o Asaas: {e.reason}") from e
        except (OSError, ValueError, http.client.HTTPException) as e:     # conexão caiu, resposta inválida…
            raise AsaasErro(f"Falha na comunicação com o Asaas ({type(e).__name__}). Tente de novo.") from e

    # ------------------------------------------------------------ recursos
    def criar_cliente(self, nome: str, documento: str, email: str | None, telefone: str | None, ref: str) -> str:
        r = self._req("POST", "/customers", {"name": nome, "cpfCnpj": documento, "email": email or None,
                                              "mobilePhone": telefone or None, "externalReference": ref,
                                              "notificationDisabled": False})
        return r["id"]

    def atualizar_cliente(self, cliente: str, nome: str, documento: str, email: str | None):
        self._req("PUT", f"/customers/{cliente}", {"name": nome, "cpfCnpj": documento, "email": email or None})

    def criar_assinatura(self, cliente: str, valor: float, ciclo: str, vencimento: date, descricao: str,
                         ref: str) -> dict:
        return self._req("POST", "/subscriptions", {
            "customer": cliente, "billingType": "UNDEFINED", "value": round(float(valor), 2),
            "nextDueDate": vencimento.isoformat(), "cycle": ciclo, "description": descricao[:500],
            "externalReference": ref})

    def pagamentos(self, assinatura: str) -> list[dict]:
        r = self._req("GET", f"/subscriptions/{assinatura}/payments", params={"limit": 100})
        return r.get("data") or []

    def atualizar_valor(self, assinatura: str, valor: float, pendentes: bool = False):
        self._req("PUT", f"/subscriptions/{assinatura}", {"value": round(float(valor), 2),
                                                          "updatePendingPayments": bool(pendentes)})

    def cancelar(self, assinatura: str):
        self._req("DELETE", f"/subscriptions/{assinatura}")


def so_digitos(t) -> str:
    return "".join(ch for ch in str(t or "") if ch.isdigit())


def documento_valido(doc: str) -> bool:
    d = so_digitos(doc)
    if len(d) == 11:
        if d == d[0] * 11:
            return False
        for n in (9, 10):
            s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
            if (s * 10 % 11) % 10 != int(d[n]):
                return False
        return True
    if len(d) == 14:
        if d == d[0] * 14:
            return False
        for n in (12, 13):
            pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
            s = sum(int(d[i]) * pesos[i] for i in range(n))
            dv = 0 if s % 11 < 2 else 11 - s % 11
            if dv != int(d[n]):
                return False
        return True
    return False


# ---------------------------------------------------------------- assinar (checkout)
def assinar(api: Asaas, engine, emp: dict, email: str, pedido: dict, hoje: date) -> dict:
    """Cria (ou reaproveita) o cliente no Asaas, troca a assinatura antiga pela nova e guarda o pedido.
    Cada passo já feito no Asaas é gravado na hora (se algo falhar no meio, a nova tentativa não duplica).
    Devolve a 1ª cobrança (com o link de pagamento)."""
    cid = str(emp["id"])
    doc = so_digitos(emp.get("documento"))
    cliente = emp.get("asaas_cliente")
    if cliente:
        api.atualizar_cliente(cliente, emp["nome"], doc, email)
    else:
        cliente = api.criar_cliente(emp["nome"], doc, email, so_digitos(emp.get("telefone")) or None, cid)
        with engine.begin() as s:
            s.execute(text("update condutores set asaas_cliente = :c where id = cast(:cid as uuid)"),
                      dict(c=cliente, cid=cid))
    if emp.get("asaas_assinatura"):
        try:
            api.cancelar(emp["asaas_assinatura"])
        except AsaasErro:
            pass
        with engine.begin() as s:
            s.execute(text("update condutores set asaas_assinatura = null, asaas_valor = null "
                           "where id = cast(:cid as uuid)"), dict(cid=cid))
    anual = pedido["periodo"] == "anual"
    valor = pedido["total"] if anual else pedido["preco"]
    desc = f"Pequenos a Bordo — plano {pedido.get('plano_nome', pedido['plano'])} " + ("anual" if anual else "mensal")
    sub = api.criar_assinatura(cliente, valor, "YEARLY" if anual else "MONTHLY", hoje, desc, cid)
    pedido = dict(pedido, asaas_assinatura=sub["id"])
    with engine.begin() as s:
        s.execute(text("""update condutores set asaas_cliente=:c, asaas_assinatura=:a, asaas_valor=:v,
                            pedido=cast(:p as jsonb) where id = cast(:cid as uuid)"""),
                  dict(c=cliente, a=sub["id"], v=valor, p=json.dumps(pedido, ensure_ascii=False, default=str),
                       cid=cid))
    try:
        pags = api.pagamentos(sub["id"])
    except AsaasErro:
        pags = []
    with engine.begin() as s:
        _guardar_pagamentos(s, cid, sub["id"], pags)
    return sorted(pags, key=lambda x: x.get("dueDate") or "")[0] if pags else {}


def cancelar_assinatura(api: Asaas, engine, emp: dict):
    """O plano segue até o fim do período já pago; só para de cobrar."""
    if emp.get("asaas_assinatura"):
        api.cancelar(emp["asaas_assinatura"])
    with engine.begin() as s:
        s.execute(text("update condutores set asaas_assinatura = null, asaas_valor = null, pedido = null "
                       "where id = cast(:cid as uuid)"), dict(cid=str(emp["id"])))


# ---------------------------------------------------------------- sincronizar
def _guardar_pagamentos(s, cid: str, assinatura: str, pags: list[dict]):
    for p in pags:
        s.execute(text("""insert into asaas_pagamentos (id, condutor_id, assinatura, valor, status, vencimento, link)
                          values (:id, cast(:cid as uuid), :a, :v, :st, :venc, :link)
                          on conflict (id) do update set status = excluded.status, valor = excluded.valor,
                                 vencimento = excluded.vencimento, link = excluded.link, atualizado_em = now()"""),
                  dict(id=p["id"], cid=cid, a=assinatura, v=p.get("value"), st=p.get("status"),
                       venc=p.get("dueDate"), link=p.get("invoiceUrl")))


def _valor_esperado(emp: dict, hoje: date, cat: dict) -> float | None:
    """Quanto a assinatura deveria cobrar agora (muda quando acaba a promoção ou o admin atualiza o preço)."""
    from core import planos as pl
    plano = emp.get("plano")
    if plano not in cat or (emp.get("plano_tipo") or "pago") != "pago":
        return None
    mensal = pl.preco_vigente(dict(emp, plano_ate=None), hoje, cat)
    return round(mensal * (12 if (emp.get("periodo") or "mensal") == "anual" else 1), 2) if mensal else None


def _catalogo_sql(s) -> dict:
    out = {}
    for r in s.execute(text("select * from config_planos")).mappings():
        out[r["plano"]] = dict(nome=r["nome"], preco=float(r["preco"] or 0),
                               preco_vip=float(r["preco_vip"]) if r["preco_vip"] is not None else None,
                               anual_desconto=float(r["anual_desconto"] or 0), vans=r["vans"], alunos=r["alunos"],
                               destaque=r["destaque"], itens=r["itens"])
    return out


def sincronizar(api: Asaas, engine, hoje: date, cid: str | None = None) -> dict:
    """Consulta as cobranças das assinaturas e libera/renova o plano de quem pagou. Idempotente."""
    from core import cobranca
    res = {"empresas": 0, "pagamentos_novos": 0, "valores_atualizados": 0, "erros": []}
    with engine.begin() as s:
        filtro = "and id = cast(:cid as uuid)" if cid else ""
        emps = [dict(r) for r in s.execute(text(f"select * from condutores where asaas_assinatura is not null {filtro}"),
                                           dict(cid=cid) if cid else {}).mappings()]
        cat = _catalogo_sql(s)
    for emp in emps:
        res["empresas"] += 1
        try:
            pags = api.pagamentos(emp["asaas_assinatura"])
        except AsaasErro as e:
            res["erros"].append(f"{emp['nome']}: {e}")
            continue
        with engine.begin() as s:
            _guardar_pagamentos(s, str(emp["id"]), emp["asaas_assinatura"], pags)
            novos = s.execute(text("""select id from asaas_pagamentos
                                      where condutor_id = cast(:cid as uuid) and not processado
                                        and status in ('RECEIVED', 'CONFIRMED', 'RECEIVED_IN_CASH')
                                      order by vencimento"""), dict(cid=str(emp["id"]))).scalars().all()
            for pid in novos:
                atual = dict(s.execute(text("select * from condutores where id = cast(:cid as uuid)"),
                                       dict(cid=str(emp["id"]))).mappings().first())
                ped = atual.get("pedido")
                usar_pedido = ped if isinstance(ped, dict) and ped.get("asaas_assinatura") == emp["asaas_assinatura"] \
                    else None
                cobranca.aplicar_pagamento(s, atual, hoje, usar_pedido)
                s.execute(text("update asaas_pagamentos set processado = true where id = :i"), dict(i=pid))
                res["pagamentos_novos"] += 1
            # fim de promoção / preço atualizado pelo admin → próximas cobranças com o valor novo
            atual = dict(s.execute(text("select * from condutores where id = cast(:cid as uuid)"),
                                   dict(cid=str(emp["id"]))).mappings().first())
        esperado = _valor_esperado(atual, hoje, cat) if not atual.get("pedido") else None
        if esperado and atual.get("asaas_valor") is not None and abs(float(atual["asaas_valor"]) - esperado) > 0.004:
            try:
                api.atualizar_valor(emp["asaas_assinatura"], esperado)
                with engine.begin() as s:
                    s.execute(text("update condutores set asaas_valor = :v where id = cast(:cid as uuid)"),
                              dict(v=esperado, cid=str(emp["id"])))
                res["valores_atualizados"] += 1
            except AsaasErro as e:
                res["erros"].append(f"{emp['nome']}: {e}")
    return res
