"""Cobrança MISTA das mensalidades dos pais (na conta Asaas do próprio gestor — o dinheiro cai direto para ele).

Por aluno: 'manual' (o gestor cobra como quiser e dá baixa), 'asaas' (o app gera Pix/boleto de cada mensalidade)
ou 'recorrente' (assinatura automática no Asaas). Em qualquer mensalidade dá para gerar um Pix/boleto avulso ou dar
baixa manual — se houver cobrança aberta no Asaas, ela é marcada como recebida lá também (não cobra de novo).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text

from core import db
from core.asaas import PAGO, Asaas, AsaasErro, so_digitos
from core.fmt import inicio_mes, mes_label, somar_meses, vencimento

MODOS = {"manual": "Manual (eu cobro e dou baixa)", "asaas": "Asaas — Pix/boleto todo mês",
         "recorrente": "Asaas — assinatura automática"}


# ---------------------------------------------------------------- responsável no Asaas
def _responsavel(cid, pid) -> dict | None:
    df = db.ao_vivo("""select r.* from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                       where pr.passageiro_id = cast(:p as uuid) and r.condutor_id = :cid
                       order by pr.financeiro desc, r.criado_em limit 1""", p=str(pid), cid=cid)
    return df.iloc[0].to_dict() if len(df) else None


def _cpf_do_contrato(pid) -> str | None:
    r = db.um("""select dados->>'cpf' as cpf from contratos where passageiro_id = cast(:p as uuid)
                 and responsavel_assinou_em is not null order by ano desc limit 1""", p=str(pid))
    return so_digitos(r["cpf"]) if r and r.get("cpf") else None


def cliente_do_aluno(api: Asaas, cid, pid) -> str:
    r = _responsavel(cid, pid)
    if not r:
        raise AsaasErro("Cadastre o responsável do aluno antes de cobrar pelo Asaas.")
    if r.get("asaas_cliente"):
        return r["asaas_cliente"]
    cpf = so_digitos(r.get("cpf")) or _cpf_do_contrato(pid)
    if not cpf:
        raise AsaasErro(f"Falta o CPF de {r['nome']} (responsável) — o Asaas exige para emitir Pix/boleto.")
    cli = api.criar_cliente(r["nome"], cpf, r.get("email"), so_digitos(r.get("telefone")) or None, str(r["id"]))
    db.gravar("update responsaveis set asaas_cliente = :c, cpf = :cpf where id = cast(:r as uuid)",
              c=cli, cpf=cpf, r=str(r["id"]))
    return cli


def salvar_cpf(cid, pid, cpf: str):
    r = _responsavel(cid, pid)
    if r:
        db.gravar("update responsaveis set cpf = :c where id = cast(:r as uuid) and condutor_id = :cid",
                  c=so_digitos(cpf) or None, r=str(r["id"]), cid=cid)


# ---------------------------------------------------------------- cobranças
def gerar_cobranca(api: Asaas, cid, m: dict, hoje: date) -> dict:
    """Pix/boleto de uma mensalidade (m = linha de mensalidades com aluno, passageiro_id, valor, vencimento…)."""
    cli = cliente_do_aluno(api, cid, m["passageiro_id"])
    venc = max(m["vencimento"], hoje)              # o Asaas não aceita vencimento no passado
    pag = api.criar_cobranca(cli, float(m["valor"]), venc,
                             f"Mensalidade da van — {m['aluno']} — {mes_label(m['competencia'])}", str(m["id"]))
    db.gravar("""update mensalidades set asaas_id=:i, asaas_link=:l, asaas_status=:s
                 where id = cast(:m as uuid) and condutor_id = :cid""",
              i=pag["id"], l=pag.get("invoiceUrl"), s=pag.get("status"), m=str(m["id"]), cid=cid)
    return pag


def baixa_manual(api: Asaas | None, cid, m: dict, data: date, valor: float, forma: str):
    """Baixa feita pelo gestor. Se há cobrança aberta no Asaas, marca como recebida lá (não cobra de novo)."""
    aviso = None
    if api and m.get("asaas_id") and (m.get("asaas_status") or "") not in PAGO:
        try:
            if forma == "Isento" or not valor:
                api.cancelar_cobranca(m["asaas_id"])
            else:
                api.receber_em_dinheiro(m["asaas_id"], data, valor)
        except AsaasErro as e:
            aviso = f"Baixa feita aqui, mas o Asaas respondeu: {e}"
    db.gravar("""update mensalidades set pago_em=:d, valor_pago=:v, forma=:f,
                   asaas_status = case when asaas_id is not null then 'RECEIVED_IN_CASH' else asaas_status end
                 where id = cast(:m as uuid) and condutor_id = :cid""",
              d=data, v=valor, f=forma, m=str(m["id"]), cid=cid)
    return aviso


def estornar(api: Asaas | None, cid, m: dict):
    aviso = None
    if api and m.get("asaas_id") and m.get("asaas_status") == "RECEIVED_IN_CASH":
        try:
            api.desfazer_dinheiro(m["asaas_id"])
        except AsaasErro as e:
            aviso = f"Estornado aqui, mas o Asaas respondeu: {e}"
    elif m.get("forma") == "Asaas":
        aviso = "Pagamento recebido pelo Asaas: a devolução do dinheiro, se houver, é feita no painel do Asaas."
    db.gravar("""update mensalidades set pago_em=null, valor_pago=null, forma=null,
                   asaas_status = case when asaas_status = 'RECEIVED_IN_CASH' then 'PENDING' else asaas_status end
                 where id = cast(:m as uuid) and condutor_id = :cid""", m=str(m["id"]), cid=cid)
    return aviso


# ---------------------------------------------------------------- forma de cobrança por aluno
def definir_modo(api: Asaas | None, cid, pid, modo: str, hoje: date) -> str | None:
    """Troca a forma de cobrança do aluno. 'recorrente' cria a assinatura no Asaas; sair dela cancela."""
    al = db.ao_vivo("""select p.*, coalesce(p.dia_vencimento, c.dia_vencimento) as dia
                       from passageiros p join condutores c on c.id = p.condutor_id
                       where p.id = cast(:p as uuid) and p.condutor_id = :cid""", p=str(pid), cid=cid)
    if not len(al):
        return "Aluno não encontrado."
    a = al.iloc[0].to_dict()
    if a.get("asaas_assinatura") and modo != "recorrente" and api:
        try:
            api.cancelar(a["asaas_assinatura"])
        except AsaasErro:
            pass
        db.gravar("update passageiros set asaas_assinatura = null where id = cast(:p as uuid)", p=str(pid))
    if modo == "recorrente" and not a.get("asaas_assinatura"):
        if not api:
            return "Conecte sua conta Asaas em Minha empresa."
        if not float(a["mensalidade"] or 0):
            return f"{a['nome']}: cadastre o valor da mensalidade antes."
        cli = cliente_do_aluno(api, cid, pid)
        prox = vencimento(inicio_mes(hoje), int(a["dia"] or 10))
        if prox < hoje:
            prox = vencimento(somar_meses(inicio_mes(hoje), 1), int(a["dia"] or 10))
        sub = api.criar_assinatura(cli, float(a["mensalidade"]), "MONTHLY", prox,
                                   f"Mensalidade da van — {a['nome']}", str(pid))
        db.gravar("update passageiros set asaas_assinatura = :s where id = cast(:p as uuid)", s=sub["id"], p=str(pid))
    db.gravar("update passageiros set cobranca = :m where id = cast(:p as uuid) and condutor_id = :cid",
              m=modo, p=str(pid), cid=cid)
    return None


def alunos_cobranca(cid) -> list[dict]:
    df = db.ao_vivo("""
        select p.id, p.nome, p.mensalidade, p.cobranca, p.asaas_assinatura,
               r.id as responsavel_id, r.nome as responsavel, coalesce(r.cpf, '') as cpf
        from passageiros p
        left join lateral (select r.* from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                           where pr.passageiro_id = p.id order by pr.financeiro desc, r.criado_em limit 1) r on true
        where p.condutor_id = :cid and p.ativo order by p.nome""", cid=cid)
    return df.to_dict("records")


# ---------------------------------------------------------------- sincronizar com o Asaas do gestor
def _marcar_pago(cid, mid, pag: dict):
    quando = pag.get("clientPaymentDate") or pag.get("paymentDate") or pag.get("confirmedDate") or date.today().isoformat()
    db.gravar("""update mensalidades set pago_em = cast(:d as date), valor_pago = :v, forma = 'Asaas', asaas_status = :s
                 where id = cast(:m as uuid) and condutor_id = :cid and pago_em is null""",
              d=quando, v=pag.get("value"), s=pag.get("status"), m=str(mid), cid=cid)


def sincronizar(api: Asaas, cid, hoje: date) -> dict:
    res = {"pagas": 0, "geradas": 0, "erros": []}
    # 1) cobranças avulsas em aberto
    abertas = db.ao_vivo("""select id, asaas_id from mensalidades
                            where condutor_id = :cid and asaas_id is not null and pago_em is null""", cid=cid)
    for m in abertas.to_dict("records"):
        try:
            pag = api.cobranca(m["asaas_id"])
        except AsaasErro as e:
            res["erros"].append(str(e))
            continue
        db.gravar("update mensalidades set asaas_status = :s, asaas_link = coalesce(:l, asaas_link) "
                  "where id = cast(:m as uuid)", s=pag.get("status"), l=pag.get("invoiceUrl"), m=str(m["id"]))
        if pag.get("status") in PAGO:
            _marcar_pago(cid, m["id"], pag)
            res["pagas"] += 1
    # 2) assinaturas recorrentes: cada cobrança gerada pelo Asaas vira (ou liga-se a) a mensalidade do mês
    for a in db.ao_vivo("""select id, nome, asaas_assinatura from passageiros where condutor_id = :cid
                           and cobranca = 'recorrente' and asaas_assinatura is not null""", cid=cid).to_dict("records"):
        try:
            pags = api.pagamentos(a["asaas_assinatura"])
        except AsaasErro as e:
            res["erros"].append(str(e))
            continue
        for pag in pags:
            due = date.fromisoformat(pag["dueDate"])
            comp = inicio_mes(due)
            db.gravar("""insert into mensalidades (condutor_id, passageiro_id, competencia, valor, vencimento)
                         values (:cid, cast(:p as uuid), :c, :v, :d) on conflict (passageiro_id, competencia) do nothing""",
                      cid=cid, p=str(a["id"]), c=comp, v=pag.get("value"), d=due)
            m = db.ao_vivo("""select id, pago_em, valor_pago, forma from mensalidades
                              where passageiro_id = cast(:p as uuid) and competencia = :c""",
                           p=str(a["id"]), c=comp).iloc[0].to_dict()
            st_pag = pag.get("status")
            # o mês já foi pago por fora (dinheiro, Pix direto, isento): avisa o Asaas para não cobrar a família de novo
            if m.get("pago_em") and m.get("forma") != "Asaas" and st_pag not in PAGO and st_pag != "DELETED":
                try:
                    if m.get("forma") == "Isento" or not float(m.get("valor_pago") or 0):
                        api.cancelar_cobranca(pag["id"])
                        st_pag = "DELETED"
                    else:
                        api.receber_em_dinheiro(pag["id"], m["pago_em"], float(m["valor_pago"]))
                        st_pag = "RECEIVED_IN_CASH"
                except AsaasErro as e:
                    res["erros"].append(str(e))
            db.gravar("""update mensalidades set asaas_id = :i, asaas_link = :l, asaas_status = :s
                         where id = cast(:m as uuid)""", i=pag["id"], l=pag.get("invoiceUrl"), s=st_pag,
                      m=str(m["id"]))
            if st_pag in ("RECEIVED", "CONFIRMED") and not m.get("pago_em"):
                _marcar_pago(cid, m["id"], pag)
                res["pagas"] += 1
    # 3) alunos "Asaas todo mês": gera o Pix/boleto das mensalidades que vencem nos próximos 10 dias
    pend = db.ao_vivo("""select m.*, p.nome as aluno from mensalidades m join passageiros p on p.id = m.passageiro_id
                         where m.condutor_id = :cid and p.cobranca = 'asaas' and p.ativo and m.pago_em is null
                           and m.asaas_id is null and coalesce(m.forma, '') <> 'Isento'
                           and m.vencimento <= :lim and m.valor > 0""", cid=cid, lim=hoje + timedelta(days=10))
    for m in pend.to_dict("records"):
        try:
            gerar_cobranca(api, cid, m, hoje)
            res["geradas"] += 1
        except AsaasErro as e:
            res["erros"].append(f"{m['aluno']}: {e}")
    if res["pagas"] or res["geradas"]:
        db._mudou()
    return res
