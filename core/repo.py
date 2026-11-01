"""Consultas e gravações. Tudo filtrado pela empresa (cid) — nunca confie em id vindo da tela sem ele.

Empresa = tabela `condutores` (o gestor). Cada empresa tem várias `vans`; cada van tem um motorista.
`van` nos filtros: None = todas as vans da empresa.
"""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from core import db
from core.fmt import inicio_mes, somar_meses, vencimento

_VAN = "(cast(:van as uuid) is null or {col} = cast(:van as uuid))"


def _filtro_van(col: str) -> str:
    return _VAN.format(col=col)


# ------------------------------------------------------------------ empresa (gestor)
def criar_empresa(usuario_id, email: str, nome: str, telefone: str | None, dirige: bool) -> dict:
    """Cadastro inicial: só nome e WhatsApp. Se o gestor também dirige, já cria a 'Van 1' com ele de motorista."""
    c = db.gravar("""
        insert into condutores (usuario_id, nome, telefone) values (:u, :nome, :tel)
        on conflict (usuario_id) do update set nome = excluded.nome, telefone = excluded.telefone
        returning *""", u=usuario_id, nome=nome, tel=telefone)
    if dirige and vans(c["id"], so_ativas=False).empty:
        salvar_van(c["id"], dict(nome="Van 1", veiculo=None, placa=None, capacidade=15, motorista_nome=nome,
                                 motorista_email=email, motorista_telefone=telefone, motorista_cnh=None, ativo=True))
    return c


def atualizar_empresa(cid, d: dict):
    db.gravar("""update condutores set nome=:nome, telefone=:telefone, chave_pix=:chave_pix,
                 dia_vencimento=:dia_vencimento where id=:cid""", cid=cid, **d)


def empresas_todas() -> pd.DataFrame:
    return db.ao_vivo("""
        select c.id, c.nome, u.email, c.telefone, c.ativo, c.criado_em::date as desde, c.plano, c.plano_ate,
               (select count(*) from vans v where v.condutor_id = c.id and v.ativo) as vans,
               (select count(*) from passageiros p where p.condutor_id = c.id and p.ativo) as alunos,
               u.ultimo_acesso
        from condutores c join usuarios u on u.id = c.usuario_id order by c.criado_em""")


def ativar_empresa(cid, ativo: bool):
    db.gravar("update condutores set ativo = :a where id = :cid", a=ativo, cid=cid)


# ------------------------------------------------------------------ vans e motoristas
def vans(cid, so_ativas=True) -> pd.DataFrame:
    return db.consultar(f"""
        select v.*, (select count(*) from passageiros p where p.van_id = v.id and p.ativo) as alunos
        from vans v where v.condutor_id = :cid {'and v.ativo' if so_ativas else ''}
        order by v.ativo desc, v.nome""", cid=cid)


_CAMPOS_V = ["nome", "veiculo", "placa", "capacidade", "motorista_nome", "motorista_email", "motorista_telefone",
             "motorista_cnh", "ativo"]


def salvar_van(cid, d: dict, vid=None):
    d = {k: d.get(k) for k in _CAMPOS_V}
    d["motorista_email"] = (d.get("motorista_email") or "").strip().lower() or None
    d["placa"] = (d.get("placa") or "").strip().upper() or None
    if vid:
        db.gravar(f"update vans set {', '.join(f'{k}=:{k}' for k in _CAMPOS_V)} where id=:vid and condutor_id=:cid",
                  cid=cid, vid=vid, **d)
    else:
        db.gravar(f"insert into vans (condutor_id, {', '.join(_CAMPOS_V)}) "
                  f"values (:cid, {', '.join(':' + k for k in _CAMPOS_V)})", cid=cid, **d)


def vans_do_motorista(email: str) -> pd.DataFrame:
    """Vans (de qualquer empresa ativa) em que este e-mail é o motorista."""
    return db.ao_vivo("""
        select v.id, v.nome, v.placa, v.veiculo, v.capacidade, v.condutor_id, c.nome as empresa,
               c.telefone as empresa_tel
        from vans v join condutores c on c.id = v.condutor_id
        where lower(v.motorista_email) = :e and v.ativo and c.ativo order by c.nome, v.nome""", e=email)


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
    select p.*, e.nome as escola, e.endereco as escola_endereco, v.nome as van,
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
    left join vans v on v.id = p.van_id
"""


def passageiros(cid, so_ativos=True, van=None) -> pd.DataFrame:
    return db.consultar(_SEL_PASS + f" where p.condutor_id = :cid {'and p.ativo' if so_ativos else ''}"
                        f" and {_filtro_van('p.van_id')} order by p.turno, p.ordem_rota, p.nome",
                        cid=cid, van=van)


_CAMPOS_P = ["escola_id", "van_id", "nome", "data_nasc", "serie", "turno", "endereco", "bairro", "referencia",
             "observacoes", "mensalidade", "dia_vencimento", "inicio", "fim", "faz_ida", "faz_volta", "ativo"]


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


def salvar_ordem(cid, van, ordens: dict):
    """{passageiro_id: ordem} — só alunos desta van."""
    with db.transacao() as s:
        for pid, o in ordens.items():
            s.execute(text("update passageiros set ordem_rota=:o where id=:pid and condutor_id=:cid and van_id=:van"),
                      {"o": int(o), "pid": pid, "cid": cid, "van": van})


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
        for a in alunos.itertuples():
            s.execute(text("""insert into mensalidades (condutor_id, passageiro_id, competencia, valor, vencimento)
                              values (:cid, :pid, :comp, :v, :venc) on conflict do nothing"""),
                      {"cid": cid, "pid": a.id, "comp": comp, "v": a.mensalidade,
                       "venc": vencimento(comp, a.dia)})
    return len(alunos)


_SEL_MENS = """
    select m.*, p.nome as aluno, p.turno, p.van_id, v.nome as van,
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
    left join vans v on v.id = p.van_id
"""


def mensalidades_mes(cid, competencia: date, hoje: date, van=None) -> pd.DataFrame:
    return db.consultar(_SEL_MENS + f" where m.condutor_id = :cid and m.competencia = :comp and {_filtro_van('p.van_id')}"
                        " order by m.vencimento, p.nome", cid=cid, comp=inicio_mes(competencia), hoje=hoje, van=van)


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


# ------------------------------------------------------------------ financeiro
def lancamentos(cid, ini: date, fim: date, van=None) -> pd.DataFrame:
    return db.consultar(f"""select l.*, v.nome as van from lancamentos l left join vans v on v.id = l.van_id
                            where l.condutor_id=:cid and l.data >= :i and l.data < :f and {_filtro_van('l.van_id')}
                            order by l.data desc, l.criado_em desc""", cid=cid, i=ini, f=fim, van=van)


def salvar_lancamento(cid, d: dict):
    db.gravar("""insert into lancamentos (condutor_id, van_id, tipo, categoria, descricao, valor, data, km)
                 select :cid, :van_id, :tipo, :categoria, :descricao, :valor, :data, :km
                 where cast(:van_id as uuid) is null
                    or exists (select 1 from vans where id = cast(:van_id as uuid) and condutor_id = :cid)""",
              cid=cid, **d)


def excluir_lancamento(cid, lid):
    db.gravar("delete from lancamentos where id=:lid and condutor_id=:cid", cid=cid, lid=lid)


def resumo_meses(cid, ini: date, fim: date, van=None) -> pd.DataFrame:
    """Por mês (regime de caixa): mensalidades recebidas, outras receitas, despesas. Com van: só o que é dela."""
    return db.consultar(f"""
        with meses as (select generate_series(cast(:i as date), cast(:f as date) - interval '1 month',
                                              interval '1 month')::date as mes),
        m as (select date_trunc('month', m.pago_em)::date mes, sum(m.valor_pago) v
              from mensalidades m join passageiros p on p.id = m.passageiro_id
              where m.condutor_id=:cid and m.pago_em >= :i and m.pago_em < :f and {_filtro_van('p.van_id')}
              group by 1),
        l as (select date_trunc('month', data)::date mes,
                     sum(valor) filter (where tipo='receita') rec, sum(valor) filter (where tipo='despesa') desp
              from lancamentos where condutor_id=:cid and data >= :i and data < :f and {_filtro_van('van_id')}
              group by 1)
        select meses.mes, coalesce(m.v,0) as mensalidades, coalesce(l.rec,0) as outras_receitas,
               coalesce(l.desp,0) as despesas
        from meses left join m using (mes) left join l using (mes) order by meses.mes""",
                        cid=cid, i=ini, f=fim, van=van)


def resultado_por_van(cid, ini: date, fim: date) -> pd.DataFrame:
    """Recebido, despesas e lucro de cada van no período; o que não tem van fica em 'Geral (sem van)'."""
    return db.consultar("""
        with m as (select p.van_id, sum(m.valor_pago) v from mensalidades m join passageiros p on p.id = m.passageiro_id
                   where m.condutor_id=:cid and m.pago_em >= :i and m.pago_em < :f group by 1),
        l as (select van_id, sum(valor) filter (where tipo='receita') rec, sum(valor) filter (where tipo='despesa') desp
              from lancamentos where condutor_id=:cid and data >= :i and data < :f group by 1),
        chaves as (select id as van_id, nome from vans where condutor_id=:cid
                   union all select null, 'Geral (sem van)')
        select k.nome as van, coalesce(m.v,0) + coalesce(l.rec,0) as recebido, coalesce(l.desp,0) as despesas
        from chaves k left join m on m.van_id is not distinct from k.van_id
                      left join l on l.van_id is not distinct from k.van_id
        order by (k.van_id is null), k.nome""", cid=cid, i=ini, f=fim)


def despesas_por_categoria(cid, ini: date, fim: date, van=None) -> pd.DataFrame:
    return db.consultar(f"""select categoria, sum(valor) as valor from lancamentos
                            where condutor_id=:cid and tipo='despesa' and data >= :i and data < :f
                              and {_filtro_van('van_id')}
                            group by 1 order by 2 desc""", cid=cid, i=ini, f=fim, van=van)


# ------------------------------------------------------------------ chamada / rota (por van)
def chamada_dia(cid, van, dia: date, trecho: str) -> pd.DataFrame:
    """Alunos da van no trecho do dia, com status marcado e aviso de falta dos pais. Sem cache (pais avisam ao vivo)."""
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
        where p.condutor_id = :cid and p.van_id = :van and p.ativo and p.{col}
          and p.inicio <= :d and (p.fim is null or p.fim >= :d)
        order by p.turno, p.ordem_rota, p.nome""", cid=cid, van=van, d=dia, t=trecho)


def marcar(cid, van, pid, dia: date, trecho: str, status: str | None):
    """Só marca aluno que é desta van desta empresa (o motorista não consegue marcar aluno de outra van)."""
    if status is None:
        db.gravar("""delete from chamadas ch using passageiros p
                     where ch.passageiro_id = p.id and p.id=:pid and p.condutor_id=:cid and p.van_id=:van
                       and ch.data=:d and ch.trecho=:t""", pid=pid, cid=cid, van=van, d=dia, t=trecho)
        return
    db.gravar("""insert into chamadas (passageiro_id, condutor_id, data, trecho, status)
                 select :pid, :cid, :d, :t, :s
                 where exists (select 1 from passageiros where id=:pid and condutor_id=:cid and van_id=:van)
                 on conflict (passageiro_id, data, trecho) do update set status = excluded.status, hora = now()""",
              pid=pid, cid=cid, van=van, d=dia, t=trecho, s=status)


def frequencia(cid, ini: date, fim: date, van=None) -> pd.DataFrame:
    return db.consultar(f"""
        select p.nome, count(ch.*) filter (where ch.status in ('embarcou','desembarcou')) as presencas,
               count(ch.*) filter (where ch.status = 'faltou') as faltas
        from passageiros p left join chamadas ch on ch.passageiro_id = p.id and ch.data >= :i and ch.data < :f
        where p.condutor_id = :cid and p.ativo and {_filtro_van('p.van_id')}
        group by p.nome order by p.nome""", cid=cid, i=ini, f=fim, van=van)


# ------------------------------------------------------------------ área dos pais
def filhos(pids: list[str]) -> pd.DataFrame:
    if not pids:
        return pd.DataFrame()
    return db.ao_vivo("""
        select p.id, p.nome, p.turno, p.serie, p.data_nasc, p.endereco, p.observacoes, p.faz_ida, p.faz_volta,
               e.nome as escola, c.nome as condutor, c.chave_pix, c.id as condutor_id,
               coalesce(v.motorista_nome, c.nome) as motorista,
               coalesce(v.motorista_telefone, c.telefone) as condutor_tel,
               v.placa, v.veiculo, v.nome as van
        from passageiros p join condutores c on c.id = p.condutor_id
        left join escolas e on e.id = p.escola_id left join vans v on v.id = p.van_id
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


def ausencias_empresa(cid, desde: date, van=None) -> pd.DataFrame:
    return db.ao_vivo(f"""select a.data, a.ida, a.volta, a.motivo, p.nome, v.nome as van, a.criado_em
                          from ausencias a join passageiros p on p.id = a.passageiro_id
                          left join vans v on v.id = p.van_id
                          where p.condutor_id = :cid and a.data >= :d and {_filtro_van('p.van_id')}
                          order by a.data, p.nome""", cid=cid, d=desde, van=van)


# ------------------------------------------------------------------ contratos
def contrato_do_aluno(pid, ano: int) -> dict | None:
    df = db.ao_vivo("select * from contratos where passageiro_id = :pid and ano = :a", pid=pid, a=ano)
    return df.iloc[0].to_dict() if len(df) else None


def empresa(cid) -> dict | None:
    df = db.ao_vivo("select * from condutores where id = :cid", cid=cid)
    return df.iloc[0].to_dict() if len(df) else None


def preparar_contrato(cid, pid, ano, servico: dict, por: str):
    """Gestor cria/atualiza as condições do serviço e libera para o responsável (só enquanto ele não assinou)."""
    import json as _json
    db.gravar("""
        insert into contratos (condutor_id, passageiro_id, ano, servico, preparado_por, preparado_em)
        select :cid, :pid, :ano, cast(:sv as jsonb), :por, now()
        where exists (select 1 from passageiros where id = :pid and condutor_id = :cid)
        on conflict (passageiro_id, ano) do update set servico = excluded.servico, preparado_por = excluded.preparado_por,
            preparado_em = now()
        where contratos.responsavel_assinou_em is null""",
              cid=cid, pid=pid, ano=ano, sv=_json.dumps(servico, ensure_ascii=False, default=str), por=por)


def assinar_contrato_responsavel(cid, pid, ano, texto, dados: dict, codigo, email, nome, ip):
    """Grava a assinatura do responsável no contrato já liberado. Só se o e-mail for responsável do aluno."""
    import json as _json
    return db.gravar("""
        update contratos set texto = :texto, dados = cast(:dados as jsonb), codigo = :codigo,
               responsavel_email = :email, responsavel_nome = :nome, responsavel_ip = :ip, responsavel_assinou_em = now()
        where passageiro_id = :pid and ano = :ano and condutor_id = :cid and servico is not null
          and responsavel_assinou_em is null
          and exists (select 1 from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                      where pr.passageiro_id = :pid and lower(r.email) = :email)
        returning id""", cid=cid, pid=pid, ano=ano, texto=texto, dados=_json.dumps(dados, ensure_ascii=False),
                     codigo=codigo, email=email, nome=nome, ip=ip)


def ultimo_contratante(email: str) -> dict:
    """Dados do contratante do último contrato que este e-mail assinou (para não digitar tudo de novo)."""
    df = db.ao_vivo("""select dados from contratos where lower(responsavel_email) = :e and dados is not null
                       order by responsavel_assinou_em desc limit 1""", e=email)
    return dict(df.iloc[0]["dados"]) if len(df) else {}


def assinar_contrato_contratada(cid, contrato_id, por: str):
    db.gravar("""update contratos set contratada_por = :por, contratada_assinou_em = now()
                 where id = :id and condutor_id = :cid and contratada_assinou_em is null""",
              id=contrato_id, cid=cid, por=por)


def cancelar_contrato(cid, contrato_id):
    """Gestor descarta o contrato (ex.: dados errados) — o responsável preenche e envia de novo."""
    db.gravar("delete from contratos where id = :id and condutor_id = :cid", id=contrato_id, cid=cid)


def contratos_empresa(cid, ano: int) -> pd.DataFrame:
    return db.ao_vivo("""
        select p.id as passageiro_id, p.nome as aluno, v.nome as van, c.id as contrato_id, c.responsavel_nome,
               c.responsavel_assinou_em, c.contratada_assinou_em, c.texto, c.codigo, c.responsavel_email,
               c.contratada_por, c.ano,
               c.servico,
               case when c.id is null then 'preparar'
                    when c.responsavel_assinou_em is null then 'pendente'
                    when c.contratada_assinou_em is null then 'assinar'
                    else 'ok' end as situacao,
               exists (select 1 from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                       where pr.passageiro_id = p.id and r.email is not null) as tem_email
        from passageiros p left join vans v on v.id = p.van_id
        left join contratos c on c.passageiro_id = p.id and c.ano = :a
        where p.condutor_id = :cid and p.ativo order by p.nome""", cid=cid, a=ano)


def atualizar_dados_contrato(cid, d: dict):
    db.gravar("""update condutores set razao_social=:razao_social, cnpj=:cnpj, cidade=:cidade,
                 contrato_clausulas=:contrato_clausulas where id=:cid""", cid=cid, **d)


# ------------------------------------------------------------------ início de rota
def iniciar_rota(cid, van, dia: date, trecho: str, por: str):
    db.gravar("""insert into rotas_iniciadas (van_id, data, trecho, iniciada_por)
                 select :van, :d, :t, :por where exists (select 1 from vans where id = :van and condutor_id = :cid)
                 on conflict (van_id, data, trecho) do nothing""", van=van, cid=cid, d=dia, t=trecho, por=por)


def desfazer_inicio_rota(cid, van, dia: date, trecho: str):
    db.gravar("""delete from rotas_iniciadas ri using vans v where ri.van_id = v.id and v.condutor_id = :cid
                 and ri.van_id = :van and ri.data = :d and ri.trecho = :t""", van=van, cid=cid, d=dia, t=trecho)


def rota_iniciada(van, dia: date, trecho: str):
    df = db.ao_vivo("select iniciada_em from rotas_iniciadas where van_id=:van and data=:d and trecho=:t",
                    van=van, d=dia, t=trecho)
    return df.iloc[0]["iniciada_em"] if len(df) else None


def rotas_dos_filhos(pids: list[str], dia: date) -> pd.DataFrame:
    """Para cada filho: se a van dele já saiu hoje (ida/volta) e a posição dele na ordem da ida."""
    return db.ao_vivo("""
        select p.id as passageiro_id, ri.trecho, ri.iniciada_em,
               (select count(*) + 1 from passageiros q
                 where q.van_id = p.van_id and q.ativo and q.faz_ida and q.turno = p.turno
                   and (q.ordem_rota, q.nome) < (p.ordem_rota, p.nome)
                   and not exists (select 1 from ausencias a where a.passageiro_id = q.id and a.data = :d and a.ida)
               ) as posicao
        from passageiros p join rotas_iniciadas ri on ri.van_id = p.van_id and ri.data = :d
        where p.id = any(cast(:ids as uuid[]))""", ids=pids, d=dia)


# ------------------------------------------------------------------ convites / acesso
def acessos(emails: list[str]) -> dict:
    """{email: último acesso} de quem já entrou no app (quem não está no dict nunca entrou)."""
    emails = [e.strip().lower() for e in emails if e]
    if not emails:
        return {}
    df = db.ao_vivo("select email, ultimo_acesso from usuarios where email = any(cast(:e as text[]))", e=emails)
    return dict(zip(df["email"], df["ultimo_acesso"])) if len(df) else {}


# ------------------------------------------------------------------ painel de mensalidades
def serie_mensalidades(cid, ini: date, fim: date, hoje: date, van=None) -> pd.DataFrame:
    """Por competência: previsto, recebido e vencido em aberto (isentos fora da conta)."""
    return db.consultar(f"""
        select m.competencia as mes,
               sum(m.valor) filter (where coalesce(m.forma,'') <> 'Isento') as previsto,
               sum(coalesce(m.valor_pago, 0)) as recebido,
               sum(m.valor) filter (where m.pago_em is null and m.vencimento < :hoje) as vencido
        from mensalidades m join passageiros p on p.id = m.passageiro_id
        where m.condutor_id = :cid and m.competencia >= :i and m.competencia < :f and {_filtro_van('p.van_id')}
        group by 1 order by 1""", cid=cid, i=ini, f=fim, hoje=hoje, van=van)


def vencidas_todas(cid, hoje: date, van=None) -> pd.DataFrame:
    """Todas as mensalidades vencidas e não pagas (qualquer mês), mais antigas primeiro."""
    return db.consultar(_SEL_MENS + f""" where m.condutor_id = :cid and m.pago_em is null and m.vencimento < :hoje
                                         and {_filtro_van('p.van_id')} order by p.nome, m.vencimento""",
                        cid=cid, hoje=hoje, van=van)


def atrasos_por_aluno(cid, desde: date, hoje: date, van=None) -> pd.DataFrame:
    """Histórico de pontualidade por aluno: pagas em dia, pagas com atraso, média de dias de atraso, em aberto."""
    return db.consultar(f"""
        select p.nome as aluno,
               count(*) filter (where m.pago_em is not null and m.pago_em <= m.vencimento) as em_dia,
               count(*) filter (where m.pago_em > m.vencimento) as com_atraso,
               round(avg(m.pago_em - m.vencimento) filter (where m.pago_em > m.vencimento)) as dias_medios,
               count(*) filter (where m.pago_em is null and m.vencimento < :hoje) as vencidas,
               coalesce(sum(m.valor) filter (where m.pago_em is null and m.vencimento < :hoje), 0) as em_aberto
        from mensalidades m join passageiros p on p.id = m.passageiro_id
        where m.condutor_id = :cid and m.competencia >= :d and m.vencimento < :hoje
          and coalesce(m.forma, '') <> 'Isento' and {_filtro_van('p.van_id')}
        group by p.nome
        order by vencidas desc, com_atraso desc, dias_medios desc nulls last, p.nome""",
                        cid=cid, d=desde, hoje=hoje, van=van)


# ------------------------------------------------------------------ planos
def uso_empresa(cid) -> dict:
    df = db.ao_vivo("""select (select count(*) from vans where condutor_id = :cid and ativo) as vans,
                              (select count(*) from passageiros where condutor_id = :cid and ativo) as alunos""", cid=cid)
    return {"vans": int(df.iloc[0]["vans"]), "alunos": int(df.iloc[0]["alunos"])}


def definir_plano(cid, plano: str, ate):
    db.gravar("update condutores set plano = :p, plano_ate = :a where id = :cid", p=plano, a=ate, cid=cid)
