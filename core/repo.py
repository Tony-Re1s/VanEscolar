"""Consultas e gravações. Tudo filtrado pelo condutor (cid) — nunca confie em id vindo da tela sem ele."""
from __future__ import annotations

from datetime import date

import pandas as pd

from core import db
from core.fmt import inicio_mes, somar_meses, vencimento


# ------------------------------------------------------------------ condutor
def criar_condutor(usuario_id, d: dict) -> dict:
    return db.gravar("""
        insert into condutores (usuario_id, nome, telefone, cnh, veiculo, placa, capacidade, chave_pix, dia_vencimento)
        values (:u, :nome, :telefone, :cnh, :veiculo, :placa, :capacidade, :chave_pix, :dia_vencimento)
        on conflict (usuario_id) do update set nome = excluded.nome
        returning *""", u=usuario_id, **d)


def atualizar_condutor(cid, d: dict):
    db.gravar("""update condutores set nome=:nome, telefone=:telefone, cnh=:cnh, veiculo=:veiculo, placa=:placa,
                 capacidade=:capacidade, chave_pix=:chave_pix, dia_vencimento=:dia_vencimento where id=:cid""",
              cid=cid, **d)


def condutores_todos() -> pd.DataFrame:
    return db.ao_vivo("""
        select c.id, c.nome, u.email, c.telefone, c.placa, c.ativo, c.criado_em::date as desde,
               (select count(*) from passageiros p where p.condutor_id = c.id and p.ativo) as alunos,
               u.ultimo_acesso
        from condutores c join usuarios u on u.id = c.usuario_id order by c.criado_em""")


def ativar_condutor(cid, ativo: bool):
    db.gravar("update condutores set ativo = :a where id = :cid", a=ativo, cid=cid)


# ------------------------------------------------------------------ escolas
def escolas(cid, so_ativas=True) -> pd.DataFrame:
    return db.consultar(f"""select * from escolas where condutor_id = :cid {'and ativo' if so_ativas else ''}
                            order by nome""", cid=cid)


def salvar_escola(cid, d: dict, eid=None):
    if eid:
        db.gravar("""update escolas set nome=:nome, endereco=:endereco, telefone=:telefone,
                     entrada_manha=:entrada_manha, saida_manha=:saida_manha, entrada_tarde=:entrada_tarde,
                     saida_tarde=:saida_tarde, ativo=:ativo where id=:eid and condutor_id=:cid""",
                  cid=cid, eid=eid, **d)
    else:
        db.gravar("""insert into escolas (condutor_id, nome, endereco, telefone, entrada_manha, saida_manha,
                     entrada_tarde, saida_tarde, ativo)
                     values (:cid, :nome, :endereco, :telefone, :entrada_manha, :saida_manha, :entrada_tarde,
                     :saida_tarde, :ativo)""", cid=cid, **d)


# ------------------------------------------------------------------ passageiros
_SEL_PASS = """
    select p.*, e.nome as escola, e.endereco as escola_endereco,
           coalesce(p.dia_vencimento, c.dia_vencimento) as dia_venc,
           (select string_agg(r.nome || coalesce(' (' || r.parentesco || ')', ''), ', ' order by r.nome)
              from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
             where pr.passageiro_id = p.id) as responsaveis,
           (select r.telefone from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
             where pr.passageiro_id = p.id and r.telefone is not null
             order by pr.financeiro desc, r.nome limit 1) as telefone_resp
    from passageiros p
    join condutores c on c.id = p.condutor_id
    left join escolas e on e.id = p.escola_id
"""


def passageiros(cid, so_ativos=True) -> pd.DataFrame:
    return db.consultar(_SEL_PASS + f" where p.condutor_id = :cid {'and p.ativo' if so_ativos else ''}"
                        " order by p.turno, p.ordem_rota, p.nome", cid=cid)


def passageiro(cid, pid) -> dict | None:
    df = db.consultar(_SEL_PASS + " where p.condutor_id = :cid and p.id = :pid", cid=cid, pid=pid)
    return df.iloc[0].to_dict() if len(df) else None


_CAMPOS_P = ["escola_id", "nome", "data_nasc", "serie", "turno", "endereco", "bairro", "referencia", "observacoes",
             "mensalidade", "dia_vencimento", "inicio", "fim", "faz_ida", "faz_volta", "ativo"]


def salvar_passageiro(cid, d: dict, pid=None) -> str:
    d = {k: d.get(k) for k in _CAMPOS_P}
    if pid:
        db.gravar(f"update passageiros set {', '.join(f'{k}=:{k}' for k in _CAMPOS_P)} "
                  "where id=:pid and condutor_id=:cid", cid=cid, pid=pid, **d)
        return str(pid)
    r = db.gravar(f"""insert into passageiros (condutor_id, {', '.join(_CAMPOS_P)}, ordem_rota)
                      values (:cid, {', '.join(':' + k for k in _CAMPOS_P)},
                              (select coalesce(max(ordem_rota), 0) + 1 from passageiros where condutor_id = :cid))
                      returning id""", cid=cid, **d)
    return str(r["id"])


def salvar_ordem(cid, ordens: dict):
    """{passageiro_id: ordem}"""
    with db.transacao() as s:
        from sqlalchemy import text
        for pid, o in ordens.items():
            s.execute(text("update passageiros set ordem_rota=:o where id=:pid and condutor_id=:cid"),
                      {"o": int(o), "pid": pid, "cid": cid})


# ------------------------------------------------------------------ responsáveis
def responsaveis_do(cid, pid) -> pd.DataFrame:
    return db.consultar("""select r.*, pr.financeiro from responsaveis r
                           join passageiro_responsavel pr on pr.responsavel_id = r.id
                           where r.condutor_id = :cid and pr.passageiro_id = :pid order by pr.financeiro desc, r.nome""",
                        cid=cid, pid=pid)


def responsaveis(cid) -> pd.DataFrame:
    return db.consultar("select * from responsaveis where condutor_id = :cid order by nome", cid=cid)


def vincular_responsavel(cid, pid, d: dict, rid=None, financeiro=True):
    email = (d.get("email") or "").strip().lower() or None
    if not rid:
        r = db.gravar("""insert into responsaveis (condutor_id, nome, parentesco, telefone, email)
                         values (:cid, :nome, :parentesco, :telefone, :email) returning id""",
                      cid=cid, nome=d["nome"], parentesco=d.get("parentesco"), telefone=d.get("telefone"), email=email)
        rid = r["id"]
    else:
        db.gravar("""update responsaveis set nome=:nome, parentesco=:parentesco, telefone=:telefone, email=:email
                     where id=:rid and condutor_id=:cid""", cid=cid, rid=rid, nome=d["nome"],
                  parentesco=d.get("parentesco"), telefone=d.get("telefone"), email=email)
    db.gravar("""insert into passageiro_responsavel (passageiro_id, responsavel_id, financeiro)
                 select :pid, :rid, :f where exists (select 1 from passageiros where id=:pid and condutor_id=:cid)
                 on conflict (passageiro_id, responsavel_id) do update set financeiro = excluded.financeiro""",
              pid=pid, rid=rid, f=financeiro, cid=cid)


def desvincular_responsavel(cid, pid, rid):
    db.gravar("""delete from passageiro_responsavel pr using passageiros p
                 where pr.passageiro_id = p.id and p.condutor_id = :cid and pr.passageiro_id = :pid
                 and pr.responsavel_id = :rid""", cid=cid, pid=pid, rid=rid)


# ------------------------------------------------------------------ mensalidades
def gerar_mensalidades(cid, competencia: date) -> int:
    """Cria a mensalidade do mês para cada aluno ativo que ainda não tem. Devolve quantas criou."""
    comp = inicio_mes(competencia)
    fim_mes = somar_meses(comp, 1)
    alunos = db.ao_vivo("""
        select p.id, p.mensalidade, coalesce(p.dia_vencimento, c.dia_vencimento) as dia
        from passageiros p join condutores c on c.id = p.condutor_id
        where p.condutor_id = :cid and p.ativo and p.mensalidade > 0
          and p.inicio < :fim and (p.fim is null or p.fim >= :comp)
          and not exists (select 1 from mensalidades m where m.passageiro_id = p.id and m.competencia = :comp)""",
                        cid=cid, comp=comp, fim=fim_mes)
    if alunos.empty:
        return 0
    with db.transacao() as s:
        from sqlalchemy import text
        for a in alunos.itertuples():
            s.execute(text("""insert into mensalidades (condutor_id, passageiro_id, competencia, valor, vencimento)
                              values (:cid, :pid, :comp, :v, :venc) on conflict do nothing"""),
                      {"cid": cid, "pid": a.id, "comp": comp, "v": a.mensalidade,
                       "venc": vencimento(comp, a.dia)})
    return len(alunos)


_SEL_MENS = """
    select m.*, p.nome as aluno, p.turno,
           (select r.nome from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
             where pr.passageiro_id = p.id order by pr.financeiro desc, r.nome limit 1) as responsavel,
           (select r.telefone from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
             where pr.passageiro_id = p.id and r.telefone is not null order by pr.financeiro desc, r.nome limit 1)
             as telefone,
           case when m.pago_em is not null then 'pago'
                when m.vencimento < :hoje then 'vencido'
                when m.vencimento <= :hoje + 5 then 'vence_logo'
                else 'aberto' end as situacao
    from mensalidades m join passageiros p on p.id = m.passageiro_id
"""


def mensalidades_mes(cid, competencia: date, hoje: date) -> pd.DataFrame:
    return db.consultar(_SEL_MENS + " where m.condutor_id = :cid and m.competencia = :comp order by m.vencimento, p.nome",
                        cid=cid, comp=inicio_mes(competencia), hoje=hoje)


def mensalidades_em_aberto(cid, hoje: date) -> pd.DataFrame:
    return db.consultar(_SEL_MENS + """ where m.condutor_id = :cid and m.pago_em is null and m.vencimento <= :hoje + 7
                                        order by m.vencimento, p.nome""", cid=cid, hoje=hoje)


def pagar(cid, mid, data_pg: date, valor, forma, obs=None):
    db.gravar("""update mensalidades set pago_em=:d, valor_pago=:v, forma=:f, obs=coalesce(:o, obs)
                 where id=:mid and condutor_id=:cid""", cid=cid, mid=mid, d=data_pg, v=valor, f=forma, o=obs)


def estornar(cid, mid):
    db.gravar("update mensalidades set pago_em=null, valor_pago=null, forma=null where id=:mid and condutor_id=:cid",
              cid=cid, mid=mid)


def alterar_mensalidade(cid, mid, valor, venc: date):
    db.gravar("update mensalidades set valor=:v, vencimento=:d where id=:mid and condutor_id=:cid and pago_em is null",
              cid=cid, mid=mid, v=valor, d=venc)


def excluir_mensalidade(cid, mid):
    db.gravar("delete from mensalidades where id=:mid and condutor_id=:cid", cid=cid, mid=mid)


# ------------------------------------------------------------------ financeiro
def lancamentos(cid, ini: date, fim: date) -> pd.DataFrame:
    return db.consultar("""select * from lancamentos where condutor_id=:cid and data >= :i and data < :f
                           order by data desc, criado_em desc""", cid=cid, i=ini, f=fim)


def salvar_lancamento(cid, d: dict):
    db.gravar("""insert into lancamentos (condutor_id, tipo, categoria, descricao, valor, data, km)
                 values (:cid, :tipo, :categoria, :descricao, :valor, :data, :km)""", cid=cid, **d)


def excluir_lancamento(cid, lid):
    db.gravar("delete from lancamentos where id=:lid and condutor_id=:cid", cid=cid, lid=lid)


def resumo_meses(cid, ini: date, fim: date) -> pd.DataFrame:
    """Por mês (regime de caixa): mensalidades recebidas, outras receitas, despesas."""
    return db.consultar("""
        with meses as (select generate_series(cast(:i as date), cast(:f as date) - interval '1 month', interval '1 month')::date as mes),
        m as (select date_trunc('month', pago_em)::date mes, sum(valor_pago) v from mensalidades
              where condutor_id=:cid and pago_em >= :i and pago_em < :f group by 1),
        l as (select date_trunc('month', data)::date mes,
                     sum(valor) filter (where tipo='receita') rec, sum(valor) filter (where tipo='despesa') desp
              from lancamentos where condutor_id=:cid and data >= :i and data < :f group by 1)
        select meses.mes, coalesce(m.v,0) as mensalidades, coalesce(l.rec,0) as outras_receitas,
               coalesce(l.desp,0) as despesas
        from meses left join m using (mes) left join l using (mes) order by meses.mes""", cid=cid, i=ini, f=fim)


def despesas_por_categoria(cid, ini: date, fim: date) -> pd.DataFrame:
    return db.consultar("""select categoria, sum(valor) as valor from lancamentos
                           where condutor_id=:cid and tipo='despesa' and data >= :i and data < :f
                           group by 1 order by 2 desc""", cid=cid, i=ini, f=fim)


# ------------------------------------------------------------------ chamada / rota
def chamada_dia(cid, dia: date, trecho: str) -> pd.DataFrame:
    """Alunos do trecho no dia, com status já marcado e aviso de falta dos pais. Sem cache (pais avisam ao vivo)."""
    col = "faz_ida" if trecho == "ida" else "faz_volta"
    return db.ao_vivo(f"""
        select p.id, p.nome, p.turno, p.endereco, p.bairro, p.referencia, p.observacoes, p.ordem_rota,
               e.nome as escola, e.endereco as escola_endereco, ch.status, ch.hora,
               a.motivo as aviso_motivo, (a.id is not null) as avisou,
               (select r.telefone from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                 where pr.passageiro_id = p.id and r.telefone is not null order by pr.financeiro desc limit 1) as telefone
        from passageiros p
        left join escolas e on e.id = p.escola_id
        left join chamadas ch on ch.passageiro_id = p.id and ch.data = :d and ch.trecho = :t
        left join ausencias a on a.passageiro_id = p.id and a.data = :d and a.{trecho}
        where p.condutor_id = :cid and p.ativo and p.{col}
          and p.inicio <= :d and (p.fim is null or p.fim >= :d)
        order by p.turno, p.ordem_rota, p.nome""", cid=cid, d=dia, t=trecho)


def marcar(cid, pid, dia: date, trecho: str, status: str | None):
    if status is None:
        db.gravar("delete from chamadas where passageiro_id=:pid and condutor_id=:cid and data=:d and trecho=:t",
                  pid=pid, cid=cid, d=dia, t=trecho)
        return
    db.gravar("""insert into chamadas (passageiro_id, condutor_id, data, trecho, status)
                 select :pid, :cid, :d, :t, :s where exists (select 1 from passageiros where id=:pid and condutor_id=:cid)
                 on conflict (passageiro_id, data, trecho) do update set status = excluded.status, hora = now()""",
              pid=pid, cid=cid, d=dia, t=trecho, s=status)


def frequencia(cid, ini: date, fim: date) -> pd.DataFrame:
    return db.consultar("""
        select p.nome, count(*) filter (where ch.status in ('embarcou','desembarcou')) as presencas,
               count(*) filter (where ch.status = 'faltou') as faltas
        from passageiros p left join chamadas ch on ch.passageiro_id = p.id and ch.data >= :i and ch.data < :f
        where p.condutor_id = :cid and p.ativo group by p.nome order by p.nome""", cid=cid, i=ini, f=fim)


# ------------------------------------------------------------------ área dos pais
def filhos(pids: list[str]) -> pd.DataFrame:
    if not pids:
        return pd.DataFrame()
    return db.ao_vivo("""
        select p.id, p.nome, p.turno, p.serie, p.data_nasc, p.endereco, p.observacoes, p.faz_ida, p.faz_volta,
               e.nome as escola, c.nome as condutor, c.telefone as condutor_tel, c.placa, c.veiculo, c.chave_pix,
               c.id as condutor_id
        from passageiros p join condutores c on c.id = p.condutor_id left join escolas e on e.id = p.escola_id
        where p.id = any(cast(:ids as uuid[])) order by p.nome""", ids=pids)


def status_hoje(pids: list[str], dia: date) -> pd.DataFrame:
    return db.ao_vivo("""select passageiro_id, trecho, status, hora from chamadas
                         where passageiro_id = any(cast(:ids as uuid[])) and data = :d""", ids=pids, d=dia)


def mensalidades_filhos(pids: list[str], hoje: date) -> pd.DataFrame:
    return db.ao_vivo(_SEL_MENS + " where m.passageiro_id = any(cast(:ids as uuid[])) and m.competencia >= :h - 365"
                      " order by m.competencia desc, p.nome", ids=pids, hoje=hoje, h=hoje)


def ausencias(pids: list[str], desde: date) -> pd.DataFrame:
    return db.ao_vivo("""select a.*, p.nome from ausencias a join passageiros p on p.id = a.passageiro_id
                         where a.passageiro_id = any(cast(:ids as uuid[])) and a.data >= :d order by a.data""",
                      ids=pids, d=desde)


def avisar_ausencia(pid, dia: date, ida: bool, volta: bool, motivo, usuario_id):
    db.gravar("""insert into ausencias (passageiro_id, data, ida, volta, motivo, criado_por)
                 values (:pid, :d, :ida, :volta, :m, :u)
                 on conflict (passageiro_id, data) do update set ida=excluded.ida, volta=excluded.volta,
                     motivo=excluded.motivo, criado_por=excluded.criado_por, criado_em=now()""",
              pid=pid, d=dia, ida=ida, volta=volta, m=motivo, u=usuario_id)


def cancelar_ausencia(pid, aid):
    db.gravar("delete from ausencias where id=:aid and passageiro_id=:pid", aid=aid, pid=pid)


def ausencias_condutor(cid, desde: date) -> pd.DataFrame:
    return db.ao_vivo("""select a.data, a.ida, a.volta, a.motivo, p.nome, a.criado_em
                         from ausencias a join passageiros p on p.id = a.passageiro_id
                         where p.condutor_id = :cid and a.data >= :d order by a.data, p.nome""", cid=cid, d=desde)
