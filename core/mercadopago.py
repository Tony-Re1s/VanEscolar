"""Integração com o Mercado Pago: assinatura do gestor como alternativa ao Asaas (o admin escolhe qual usar).

Dois jeitos de pagar (o gestor escolhe ao assinar):
  - "cartao": assinatura no cartão de crédito (preapproval) — o Mercado Pago cobra sozinho a cada período;
  - "avulso": um link de pagamento por período (Checkout Pro: Pix, boleto ou cartão). Perto do vencimento, Meu plano
    mostra "Pagar o próximo período" (o Mercado Pago não tem Pix recorrente nas assinaturas).

Como no Asaas, o Streamlit não recebe webhooks: o app CONSULTA o Mercado Pago (`sincronizar`) ao abrir Meu plano,
pelo botão do admin e a cada 30 min pelo GitHub Actions (scripts/asaas_sync.py). Os pagamentos ficam na mesma tabela
`asaas_pagamentos` (coluna gateway = 'mercadopago') e liberam o plano pela mesma regra (core/cobranca.py).

Configuração (Secrets do Streamlit ou variável MP_ACCESS_TOKEN no GitHub):
    [mercadopago]
    access_token = "TEST-..."   # credencial de teste; em produção "APP_USR-..."
"""
from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date

from sqlalchemy import text

BASE = "https://api.mercadopago.com"
APP_URL = "https://turminhaabordo.streamlit.app"
# status do Mercado Pago -> os mesmos códigos usados com o Asaas (a regra de liberar o plano é uma só)
_PAG = {"approved": "RECEIVED", "authorized": "PENDING", "pending": "PENDING", "in_process": "PENDING",
        "in_mediation": "PENDING", "rejected": "CANCELLED", "cancelled": "CANCELLED", "refunded": "REFUNDED",
        "charged_back": "REFUNDED"}
STATUS = {"CANCELLED": "cancelada / recusada"}


class MPErro(Exception):
    pass


class MercadoPago:
    def __init__(self, access_token: str, base_url: str | None = None):
        if not access_token:
            raise MPErro("Credencial do Mercado Pago não configurada.")
        self.token = access_token
        self.base = (base_url or BASE).rstrip("/")
        self.teste = access_token.startswith("TEST-")

    def _req(self, metodo: str, caminho: str, corpo: dict | None = None, params: dict | None = None):
        url = self.base + caminho + ("?" + urllib.parse.urlencode(params) if params else "")
        dados = json.dumps(corpo).encode() if corpo is not None else None
        cab = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
               "Accept": "application/json", "User-Agent": "TurminhaABordo/1.0"}
        if metodo == "POST":
            cab["X-Idempotency-Key"] = str(uuid.uuid4())
        req = urllib.request.Request(url, data=dados, method=metodo, headers=cab)
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                j = json.loads(e.read().decode())
                msg = j.get("message") or j.get("error") or str(e)
                causas = [c.get("description") for c in (j.get("cause") or []) if isinstance(c, dict)]
                if any(causas):
                    msg += " (" + "; ".join(c for c in causas if c) + ")"
            except Exception:  # noqa: BLE001
                msg = str(e)
            if e.code == 401:
                msg = "Credencial do Mercado Pago inválida."
            raise MPErro(msg) from e
        except urllib.error.URLError as e:
            raise MPErro(f"Não consegui falar com o Mercado Pago: {e.reason}") from e
        except (OSError, ValueError, http.client.HTTPException) as e:
            raise MPErro(f"Falha na comunicação com o Mercado Pago ({type(e).__name__}). Tente de novo.") from e

    # ------------------------------------------------------------ link avulso (Pix, boleto ou cartão)
    def criar_link(self, valor: float, descricao: str, ref: str, email: str | None) -> dict:
        corpo = {"items": [{"title": descricao[:250], "quantity": 1, "unit_price": round(float(valor), 2),
                            "currency_id": "BRL"}],
                 "external_reference": ref, "statement_descriptor": "TURMINHA",
                 "payment_methods": {"installments": 1},
                 "back_urls": {k: APP_URL for k in ("success", "pending", "failure")}, "auto_return": "approved"}
        if email:
            corpo["payer"] = {"email": email}
        r = self._req("POST", "/checkout/preferences", corpo)
        return {"id": r.get("id"), "link": (r.get("sandbox_init_point") if self.teste else None) or r.get("init_point")}

    def pagamentos_do_link(self, ref: str) -> list[dict]:
        r = self._req("GET", "/v1/payments/search", params={"external_reference": ref, "sort": "date_created",
                                                             "criteria": "desc", "limit": 30})
        return r.get("results") or []

    # ------------------------------------------------------------ assinatura no cartão (preapproval)
    def criar_assinatura(self, valor: float, meses: int, descricao: str, ref: str, email: str) -> dict:
        r = self._req("POST", "/preapproval", {
            "reason": descricao[:250], "external_reference": ref, "payer_email": email, "back_url": APP_URL,
            "status": "pending",
            "auto_recurring": {"frequency": int(meses), "frequency_type": "months",
                               "transaction_amount": round(float(valor), 2), "currency_id": "BRL"}})
        return {"id": r["id"], "link": (r.get("sandbox_init_point") if self.teste else None) or r.get("init_point"),
                "status": r.get("status")}

    def assinatura(self, assinatura: str) -> dict:
        return self._req("GET", f"/preapproval/{assinatura}")

    def cobrancas_assinatura(self, assinatura: str) -> list[dict]:
        r = self._req("GET", "/authorized_payments/search", params={"preapproval_id": assinatura, "limit": 100})
        return r.get("results") or []

    def atualizar_valor(self, assinatura: str, valor: float):
        self._req("PUT", f"/preapproval/{assinatura}",
                  {"auto_recurring": {"transaction_amount": round(float(valor), 2), "currency_id": "BRL"}})

    def cancelar(self, assinatura: str):
        self._req("PUT", f"/preapproval/{assinatura}", {"status": "cancelled"})

    def testar(self):
        self._req("GET", "/v1/payments/search", params={"limit": 1})


# ---------------------------------------------------------------- assinar
def _desc(pedido: dict) -> str:
    anual = pedido["periodo"] == "anual"
    return f"Turminha a Bordo — plano {pedido.get('plano_nome', pedido['plano'])} " + ("anual" if anual else "mensal")


def _guardar_link(s, cid: str, ref: str, valor: float, venc: date, link: str | None):
    s.execute(text("""insert into asaas_pagamentos (id, condutor_id, assinatura, valor, status, vencimento, link, gateway)
                      values (:id, cast(:cid as uuid), null, :v, 'PENDING', :venc, :link, 'mercadopago')
                      on conflict (id) do nothing"""),
              dict(id="mpref:" + ref, cid=cid, v=valor, venc=venc, link=link))


def assinar(api: MercadoPago, engine, emp: dict, email: str, pedido: dict, hoje: date, metodo: str) -> str | None:
    """Cria a assinatura no cartão (metodo="cartao") ou o link avulso (metodo="avulso") e guarda o pedido.
    Quem chama já encerrou a assinatura antiga (Asaas ou Mercado Pago). Devolve o link de pagamento."""
    cid = str(emp["id"])
    anual = pedido["periodo"] == "anual"
    valor = pedido["total"] if anual else pedido["preco"]
    if metodo == "cartao":
        sub = api.criar_assinatura(valor, 12 if anual else 1, _desc(pedido), cid, email)
        pedido = dict(pedido, mp_assinatura=sub["id"], mp_link=sub["link"], gateway="mercadopago")
        with engine.begin() as s:
            s.execute(text("""update condutores set mp_assinatura=:a, mp_valor=:v, gateway='mercadopago',
                                pedido=cast(:p as jsonb) where id = cast(:cid as uuid)"""),
                      dict(a=sub["id"], v=valor, p=json.dumps(pedido, ensure_ascii=False, default=str), cid=cid))
        return sub["link"]
    ref = f"{cid}.{uuid.uuid4().hex[:10]}"
    lk = api.criar_link(valor, _desc(pedido), ref, email)
    pedido = dict(pedido, mp_ref=ref, mp_link=lk["link"], gateway="mercadopago")
    with engine.begin() as s:
        _guardar_link(s, cid, ref, valor, hoje, lk["link"])
        s.execute(text("""update condutores set gateway='mercadopago', pedido=cast(:p as jsonb)
                          where id = cast(:cid as uuid)"""),
                  dict(p=json.dumps(pedido, ensure_ascii=False, default=str), cid=cid))
    return lk["link"]


def link_renovacao(api: MercadoPago, engine, emp: dict, email: str | None, valor: float, venc: date) -> str | None:
    """Link para pagar o próximo período (quem paga por Pix/boleto). Reaproveita o que ainda está em aberto."""
    cid = str(emp["id"])
    with engine.begin() as s:
        r = s.execute(text("""select link from asaas_pagamentos where condutor_id = cast(:cid as uuid)
                                and gateway = 'mercadopago' and id like 'mpref:%' and status = 'PENDING'
                                and abs(valor - :v) < 0.01 order by atualizado_em desc limit 1"""),
                      dict(cid=cid, v=valor)).first()
    if r and r[0]:
        return r[0]
    desc = (f"Turminha a Bordo — renovação {'anual' if (emp.get('periodo') or 'mensal') == 'anual' else 'mensal'}")
    ref = f"{cid}.{uuid.uuid4().hex[:10]}"
    lk = api.criar_link(valor, desc, ref, email)
    with engine.begin() as s:
        _guardar_link(s, cid, ref, valor, venc, lk["link"])
    return lk["link"]


def cancelar_assinatura(api: MercadoPago | None, engine, emp: dict):
    """Para a cobrança no cartão e descarta links em aberto. O plano segue até o fim do período já pago."""
    cid = str(emp["id"])
    if api and emp.get("mp_assinatura"):
        try:
            api.cancelar(emp["mp_assinatura"])
        except MPErro:
            pass
    with engine.begin() as s:
        s.execute(text("""update asaas_pagamentos set status = 'CANCELLED', atualizado_em = now()
                          where condutor_id = cast(:cid as uuid) and id like 'mpref:%' and status = 'PENDING'"""),
                  dict(cid=cid))
        s.execute(text("""update condutores set mp_assinatura = null, mp_valor = null,
                            pedido = case when pedido ->> 'gateway' = 'mercadopago' then null else pedido end
                          where id = cast(:cid as uuid)"""), dict(cid=cid))


# ---------------------------------------------------------------- sincronizar
def _status_cobranca(x: dict) -> str:
    pg = x.get("payment") or {}
    if pg.get("status"):
        return _PAG.get(pg["status"], "PENDING")
    return {"cancelled": "CANCELLED"}.get(x.get("status"), "PENDING")


def sincronizar(api: MercadoPago, engine, hoje: date, cid: str | None = None) -> dict:
    """Confere links avulsos em aberto e as cobranças das assinaturas no cartão; libera/renova quem pagou."""
    from core import cobranca
    from core.asaas import _catalogo_sql, _valor_esperado
    res = {"empresas": 0, "pagamentos_novos": 0, "valores_atualizados": 0, "erros": []}
    filtro = "and c.id = cast(:cid as uuid)" if cid else ""
    with engine.begin() as s:
        emps = [dict(r) for r in s.execute(text(f"""
            select c.* from condutores c
            where (c.mp_assinatura is not null or exists (
                     select 1 from asaas_pagamentos p where p.condutor_id = c.id and p.gateway = 'mercadopago'
                       and p.id like 'mpref:%' and p.status = 'PENDING')) {filtro}"""),
            dict(cid=cid) if cid else {}).mappings()]
        cat = _catalogo_sql(s)
    for emp in emps:
        res["empresas"] += 1
        ecid = str(emp["id"])
        try:
            with engine.begin() as s:
                refs = s.execute(text("""select id from asaas_pagamentos where condutor_id = cast(:cid as uuid)
                                           and id like 'mpref:%' and status = 'PENDING'"""),
                                 dict(cid=ecid)).scalars().all()
            for rid in refs:
                pags = api.pagamentos_do_link(rid.split(":", 1)[1])
                st_ = "RECEIVED" if any(p.get("status") == "approved" for p in pags) else "PENDING"
                if st_ != "PENDING":
                    with engine.begin() as s:
                        s.execute(text("update asaas_pagamentos set status = :st, atualizado_em = now() where id = :i"),
                                  dict(st=st_, i=rid))
            if emp.get("mp_assinatura"):
                for x in api.cobrancas_assinatura(emp["mp_assinatura"]):
                    with engine.begin() as s:
                        s.execute(text("""insert into asaas_pagamentos
                                            (id, condutor_id, assinatura, valor, status, vencimento, link, gateway)
                                          values (:id, cast(:cid as uuid), :a, :v, :st, :venc, null, 'mercadopago')
                                          on conflict (id) do update set status = excluded.status,
                                                 valor = excluded.valor, atualizado_em = now()"""),
                                  dict(id=f"mp:{x.get('id')}", cid=ecid, a=emp["mp_assinatura"],
                                       v=x.get("transaction_amount"), st=_status_cobranca(x),
                                       venc=(x.get("debit_date") or x.get("date_created") or hoje.isoformat())[:10]))
        except MPErro as e:
            res["erros"].append(f"{emp['nome']}: {e}")
            continue
        with engine.begin() as s:
            novos = s.execute(text("""select id, assinatura from asaas_pagamentos
                                      where condutor_id = cast(:cid as uuid) and gateway = 'mercadopago'
                                        and not processado and status = 'RECEIVED' order by vencimento"""),
                              dict(cid=ecid)).all()
            for pid, assin in novos:
                atual = dict(s.execute(text("select * from condutores where id = cast(:cid as uuid)"),
                                       dict(cid=ecid)).mappings().first())
                ped = atual.get("pedido")
                ok = isinstance(ped, dict) and ped.get("gateway") == "mercadopago" and (
                    (assin and ped.get("mp_assinatura") == assin) or ped.get("mp_ref") == pid.split(":", 1)[1])
                cobranca.aplicar_pagamento(s, atual, hoje, ped if ok else None)
                s.execute(text("update asaas_pagamentos set processado = true where id = :i"), dict(i=pid))
                res["pagamentos_novos"] += 1
            atual = dict(s.execute(text("select * from condutores where id = cast(:cid as uuid)"),
                                   dict(cid=ecid)).mappings().first())
        # fim de promoção / pausa / preço novo → próximas cobranças do cartão com o valor certo
        esperado = _valor_esperado(atual, hoje, cat) if not atual.get("pedido") else None
        if esperado and atual.get("mp_assinatura") and atual.get("mp_valor") is not None \
                and abs(float(atual["mp_valor"]) - esperado) > 0.004:
            try:
                api.atualizar_valor(atual["mp_assinatura"], esperado)
                with engine.begin() as s:
                    s.execute(text("update condutores set mp_valor = :v where id = cast(:cid as uuid)"),
                              dict(v=esperado, cid=ecid))
                res["valores_atualizados"] += 1
            except MPErro as e:
                res["erros"].append(f"{emp['nome']}: {e}")
    return res
