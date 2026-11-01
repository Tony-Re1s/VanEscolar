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
        insert into condutores (usuario_id, nome, telefone, modo) values (:u, :nome, :tel, 'facil')
        on conflict (usuario_id) do update set nome = excluded.nome, telefone = excluded.telefone
        returning *""", u=usuario_id, nome=nome, tel=telefone)
    garantir_codigo_indicacao(c["id"])
    if dirige and vans(c["id"], so_ativas=False).empty:
        salvar_van(c["id"], dict(nome="Van 1", veiculo=None, placa=None, capacidade=15, motorista_nome=nome,
                                 motorista_email=email, motorista_telefone=telefone, motorista_cnh=None, ativo=True))
    return c


def atualizar_empresa(cid, d: dict):
    d = dict(d, apelido=" ".join((d.get("apelido") or "").split()) or None)
    db.gravar("""update condutores set nome=:nome, telefone=:telefone, chave_pix=:chave_pix,
                 dia_vencimento=:dia_vencimento, apelido=:apelido where id=:cid""", cid=cid, **d)


def apelido_motorista(van_id, email: str | None = None) -> str | None:
    """Como as famílias chamam quem está mandando a mensagem: se for o(a) monitor(a) da van, o apelido dele(a);
    senão o de quem dirige (o da van; se o próprio gestor dirige, o apelido dele)."""
    r = db.um("""select case when :e <> '' and lower(v.monitor_email) = :e
                             then coalesce(v.monitor_apelido, split_part(v.monitor_nome, ' ', 1)) end as monitor,
                        coalesce(v.motorista_apelido,
                                 case when lower(v.motorista_email) = lower(u.email) then c.apelido end) as apelido
                 from vans v join condutores c on c.id = v.condutor_id left join usuarios u on u.id = c.usuario_id
                 where v.id = cast(:v as uuid)""", v=str(van_id), e=(email or "").strip().lower())
    return (r or {}).get("monitor") or (r or {}).get("apelido")


def empresas_todas() -> pd.DataFrame:
    return db.ao_vivo("""
        select c.id, c.nome, u.email, c.telefone, c.ativo, c.criado_em::date as desde, c.plano, c.plano_ate, c.plano_tipo, c.periodo, c.preco_mensal, c.desconto_origem,
               c.desconto_ate, c.preco_combinado, c.vip, c.pedido, c.meses_gratis, c.indicacoes_pagas,
               c.asaas_assinatura, c.pausa_ate, c.cancelado_em, c.perdeu_vip, c.dados_apagados_em,
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
             "motorista_cnh", "motorista_apelido", "monitor_nome", "monitor_email", "monitor_telefone",
             "monitor_apelido", "ativo"]


def salvar_van(cid, d: dict, vid=None):
    d = {k: d.get(k) for k in _CAMPOS_V}
    d["motorista_email"] = (d.get("motorista_email") or "").strip().lower() or None
    d["placa"] = (d.get("placa") or "").strip().upper() or None
    d["motorista_apelido"] = " ".join((d.get("motorista_apelido") or "").split()) or None
    d["monitor_email"] = (d.get("monitor_email") or "").strip().lower() or None
    d["monitor_apelido"] = " ".join((d.get("monitor_apelido") or "").split()) or None
    if vid:
        db.gravar(f"update vans set {', '.join(f'{k}=:{k}' for k in _CAMPOS_V)} where id=:vid and condutor_id=:cid",
                  cid=cid, vid=vid, **d)
    else:
        db.gravar(f"insert into vans (condutor_id, {', '.join(_CAMPOS_V)}) "
                  f"values (:cid, {', '.join(':' + k for k in _CAMPOS_V)})", cid=cid, **d)


def vans_do_motorista(email: str) -> pd.DataFrame:
    """Vans (de qualquer empresa ativa) em que este e-mail é o motorista ou o(a) monitor(a)."""
    return db.ao_vivo("""
        select v.id, v.nome, v.placa, v.veiculo, v.capacidade, v.condutor_id, c.nome as empresa,
               c.telefone as empresa_tel,
               case when lower(v.motorista_email) = :e then 'motorista' else 'monitor' end as papel
        from vans v join condutores c on c.id = v.condutor_id
        where (lower(v.motorista_email) = :e or lower(v.monitor_email) = :e) and v.ativo and c.ativo
        order by c.nome, v.nome""", e=email)


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
               v.placa, v.veiculo, v.nome as van, v.monitor_nome, v.monitor_telefone,
               coalesce(v.motorista_apelido, case when lower(v.motorista_email) = lower(u.email) then c.apelido end)
                 as apelido,
               case when v.loc_ate > now() then v.loc_token end as loc_token
        from passageiros p join condutores c on c.id = p.condutor_id
        left join usuarios u on u.id = c.usuario_id
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


def desfazer_falta_trecho(cid, pid, dia: date, trecho: str):
    """Motorista: "vai sim" — tira o aviso de falta dos pais só deste trecho (se sobrar nada, apaga o aviso)."""
    col = "ida" if trecho == "ida" else "volta"
    db.gravar(f"""update ausencias a set {col} = false from passageiros p
                  where a.passageiro_id = p.id and p.id = :pid and p.condutor_id = :cid and a.data = :d""",
              pid=pid, cid=cid, d=dia)
    db.gravar("delete from ausencias where passageiro_id = :pid and data = :d and not ida and not volta",
              pid=pid, d=dia)


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
                       where pr.passageiro_id = p.id and r.email is not null) as tem_email,
               (select r.email from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                 where pr.passageiro_id = p.id and r.email is not null
                 order by pr.financeiro desc, r.nome limit 1) as email_resp
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


def responsaveis_sem_acesso(cid) -> pd.DataFrame:
    """Responsáveis (com e-mail) de alunos ativos que ainda nunca entraram no app."""
    return db.ao_vivo("""
        select r.id, r.nome, r.telefone, r.email,
               string_agg(distinct p.nome, ', ' order by p.nome) as alunos
        from responsaveis r
        join passageiro_responsavel pr on pr.responsavel_id = r.id
        join passageiros p on p.id = pr.passageiro_id and p.ativo
        where r.condutor_id = :cid and r.email is not null
          and not exists (select 1 from usuarios u where u.email = lower(r.email))
        group by r.id, r.nome, r.telefone, r.email order by r.nome""", cid=cid)


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


def definir_plano(cid, plano: str, ate, tipo: str = "pago"):
    """tipo: pago | teste (degustação; em `ate` o acesso bloqueia) | cortesia (sem cobrar; `ate` opcional)."""
    db.gravar("update condutores set plano = :p, plano_ate = :a, plano_tipo = :t where id = :cid",
              p=plano, a=ate, t=tipo, cid=cid)


# ------------------------------------------------------------------ promoções (cupons, campanhas, VIP, indicação)
import json as _json  # noqa: E402

_CODIGO_SQL = ("upper(left(regexp_replace(split_part(nome, ' ', 1), '[^A-Za-z]', '', 'g'), 6)) "
               "|| upper(substr(md5(id::text), 1, 3))")


def garantir_codigo_indicacao(cid):
    db.gravar(f"update condutores set codigo_indicacao = {_CODIGO_SQL} where id = :cid and codigo_indicacao is null",
              cid=cid)


# preço "de tabela" que cada assinante paga hoje, calculado com os valores atuais de config_planos
_SQL_PRECO_REGULAR = """case when c.vip and cp.preco_vip is not null then cp.preco_vip
                             when c.periodo = 'anual' and cp.anual_desconto > 0
                                  then round(cp.preco * (1 - cp.anual_desconto / 100), 2)
                             else cp.preco end"""


def salvar_config_planos(linhas: list[dict]):
    """Salva preços/limites. Quem já assina e ainda não tinha preço gravado fica com o preço ANTIGO
    (para mudar, use "Atualizar para o preço novo")."""
    with db.transacao() as s:
        s.execute(text(f"""update condutores c set preco_mensal = {_SQL_PRECO_REGULAR}
                           from config_planos cp
                           where cp.plano = c.plano and c.plano_tipo = 'pago' and c.preco_mensal is null
                             and c.preco_combinado is null"""))
        for r in linhas:
            s.execute(text("""update config_planos set nome=:nome, preco=:preco, preco_vip=:preco_vip,
                                anual_desconto=:anual_desconto, vans=:vans, alunos=:alunos, destaque=:destaque,
                                itens=cast(:itens as jsonb), cobranca_auto=:cobranca_auto where plano=:plano"""),
                      dict(r, itens=_json.dumps(r["itens"], ensure_ascii=False),
                           cobranca_auto=bool(r.get("cobranca_auto"))))


def salvar_config(chave: str, valor: dict):
    db.gravar("""insert into config (chave, valor) values (:c, cast(:v as jsonb))
                 on conflict (chave) do update set valor = excluded.valor""",
              c=chave, v=_json.dumps(valor, ensure_ascii=False, default=str))


def _cupom_dict(r: dict | None) -> dict | None:
    if not r:
        return None
    r = dict(r)
    r["valor"] = float(r["valor"])
    return r


def cupons() -> pd.DataFrame:
    return db.ao_vivo("""select c.*, (select count(*) from cupons_usos u where u.cupom_id = c.id) as usos
                         from cupons c order by c.ativo desc, c.criado_em desc""")


def cupom_por_id(cupom_id) -> dict | None:
    if not cupom_id:
        return None
    return _cupom_dict(db.um("select * from cupons where id = cast(:i as uuid)", i=str(cupom_id)))


def salvar_cupom(d: dict, cupom_id=None) -> dict:
    d = dict(d, codigo=d["codigo"].strip().upper(),
             planos=_json.dumps(d["planos"]) if d.get("planos") else None)
    if cupom_id:
        return db.gravar("""update cupons set codigo=:codigo, tipo=:tipo, valor=:valor, planos=cast(:planos as jsonb),
                              duracao_meses=:duracao_meses, valido_ate=:valido_ate, limite_usos=:limite_usos,
                              ativo=:ativo where id = cast(:id as uuid) returning *""", id=str(cupom_id), **d)
    return db.gravar("""insert into cupons (codigo, tipo, valor, planos, duracao_meses, valido_ate, limite_usos, ativo)
                        values (:codigo, :tipo, :valor, cast(:planos as jsonb), :duracao_meses, :valido_ate,
                                :limite_usos, :ativo) returning *""", **d)


def cupom_usos(cupom_id) -> pd.DataFrame:
    return db.ao_vivo("""select c.nome, u.usado_em from cupons_usos u join condutores c on c.id = u.condutor_id
                         where u.cupom_id = cast(:i as uuid) order by u.usado_em desc""", i=str(cupom_id))


def validar_cupom(codigo: str, cid, hoje: date, plano: str | None = None) -> tuple[dict | None, str | None]:
    """Devolve (cupom, None) se pode usar, ou (None, motivo)."""
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None, "Digite o código do cupom."
    c = _cupom_dict(db.um("""select c.*, (select count(*) from cupons_usos u where u.cupom_id = c.id) as usos,
                                    exists(select 1 from cupons_usos u where u.cupom_id = c.id
                                           and u.condutor_id = cast(:cid as uuid)) as ja_usou
                             from cupons c where c.codigo = :cod""", cod=codigo, cid=str(cid)))
    if not c or not c["ativo"]:
        return None, "Cupom não encontrado."
    if c["valido_ate"] and c["valido_ate"] < hoje:
        return None, f"Esse cupom venceu em {c['valido_ate']:%d/%m/%Y}."
    if c["ja_usou"]:
        return None, "Você já usou esse cupom."
    if c["limite_usos"] is not None and c["usos"] >= c["limite_usos"]:
        return None, "Esse cupom já atingiu o limite de usos."
    if plano and c.get("planos") and plano not in c["planos"]:
        return None, "Esse cupom não vale para o plano escolhido."
    return c, None


def ativar_cupom_dias(cid, cupom: dict, hoje: date) -> tuple[str, date]:
    """Cupom de dias grátis: libera degustação do plano do cupom (ou Pro) e registra o uso."""
    from datetime import timedelta
    from core import planos as pl
    plano = (cupom.get("planos") or [pl.config("degustacao").get("plano") or next(iter(pl.catalogo()))])[0]
    ate = hoje + timedelta(days=int(cupom["valor"]))
    with db.transacao() as s:
        s.execute(text("""update condutores set plano=:p, plano_ate=:a, plano_tipo='teste' where id=cast(:cid as uuid)"""),
                  dict(p=plano, a=ate, cid=str(cid)))
        s.execute(text("""insert into cupons_usos (cupom_id, condutor_id) values (cast(:c as uuid), cast(:cid as uuid))
                          on conflict do nothing"""), dict(c=str(cupom["id"]), cid=str(cid)))
    return plano, ate


def campanhas() -> list[dict]:
    df = db.consultar("select * from campanhas order by ativo desc, inicio desc")
    out = df.to_dict("records")
    for c in out:
        c["preco"] = float(c["preco"])
    return out


def salvar_campanha(d: dict, camp_id=None):
    if camp_id:
        db.gravar("""update campanhas set nome=:nome, plano=:plano, preco=:preco, inicio=:inicio, fim=:fim,
                       duracao_meses=:duracao_meses, ativo=:ativo where id = cast(:id as uuid)""", id=str(camp_id), **d)
    else:
        db.gravar("""insert into campanhas (nome, plano, preco, inicio, fim, duracao_meses, ativo)
                     values (:nome, :plano, :preco, :inicio, :fim, :duracao_meses, :ativo)""", **d)


def vip_usadas() -> int:
    """Vagas VIP já usadas — leitura sem cache (o contador do divulgador atualiza ao vivo)."""
    df = db.ao_vivo("select count(*) as n from condutores where vip")
    return int(df.iloc[0]["n"]) if len(df) else 0


def vips() -> pd.DataFrame:
    return db.ao_vivo("select nome, plano, preco_mensal from condutores where vip order by nome")


def salvar_pedido(cid, pedido: dict | None):
    db.gravar("update condutores set pedido = cast(:p as jsonb) where id = cast(:cid as uuid)",
              p=_json.dumps(pedido, ensure_ascii=False, default=str) if pedido else None, cid=str(cid))


def definir_preco_combinado(cid, valor: float | None):
    db.gravar("update condutores set preco_combinado = :v where id = cast(:cid as uuid)",
              v=valor if valor else None, cid=str(cid))


def registrar_pagamento(cid, hoje: date, pedido: dict | None = None) -> date:
    """Confirma um pagamento (regra em core/cobranca.py, a mesma usada pela sincronização com o Asaas)."""
    from core import cobranca
    emp = empresa(cid)
    with db.transacao() as s:
        return cobranca.aplicar_pagamento(s, emp, hoje, pedido)


def usar_mes_gratis(cid, hoje: date) -> date | None:
    emp = empresa(cid)
    if not emp or int(emp.get("meses_gratis") or 0) <= 0 or not emp.get("plano"):
        return None
    ate = somar_meses(max(emp.get("plano_ate") or hoje, hoje), 1)
    db.gravar("""update condutores set plano_ate = :a, meses_gratis = meses_gratis - 1, plano_tipo = 'pago'
                 where id = cast(:cid as uuid) and meses_gratis > 0""", a=ate, cid=str(cid))
    return ate


def empresa_por_codigo(codigo: str) -> dict | None:
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None
    return db.um("select id, nome from condutores where codigo_indicacao = :c and ativo", c=codigo)


def aplicar_indicacao(cid, indicador_id, hoje: date) -> tuple[str, date] | None:
    """Liga o novo gestor a quem indicou e dá a degustação maior (se a indicação estiver ligada)."""
    from datetime import timedelta
    from core import planos as pl
    if not indicador_id or str(indicador_id) == str(cid):
        return None
    cfg = pl.config("indicacao")
    db.gravar("update condutores set indicado_por = cast(:i as uuid) where id = cast(:cid as uuid) "
              "and indicado_por is null", i=str(indicador_id), cid=str(cid))
    if not cfg.get("ativo"):
        return None
    plano = cfg.get("plano_degustacao")
    if plano not in pl.catalogo():
        return None
    ate = hoje + timedelta(days=int(cfg.get("dias_degustacao") or 30))
    definir_plano(cid, plano, ate, "teste")
    return plano, ate


def salvar_chave_pix(cid, chave: str | None):
    db.gravar("update condutores set chave_pix = :p where id = cast(:c as uuid)", p=(chave or "").strip() or None,
              c=str(cid))


def indicados(cid) -> pd.DataFrame:
    return db.ao_vivo("""select nome, plano, plano_tipo, plano_ate, indicacao_contada, criado_em::date as desde
                         from condutores where indicado_por = cast(:cid as uuid) order by criado_em desc""",
                      cid=str(cid))


def ranking_indicacoes() -> pd.DataFrame:
    return db.ao_vivo("""select c.nome, c.codigo_indicacao, c.indicacoes_pagas, c.meses_gratis,
                                (select count(*) from condutores x where x.indicado_por = c.id) as indicados
                         from condutores c
                         where c.indicacoes_pagas > 0 or exists(select 1 from condutores x where x.indicado_por = c.id)
                         order by c.indicacoes_pagas desc, indicados desc, c.nome""")



# ------------------------------------------------------------------ planos: criar, excluir, preço antigo × novo
def criar_plano(d: dict):
    db.gravar("""insert into config_planos (plano, nome, preco, preco_vip, anual_desconto, vans, alunos, destaque, itens,
                                            cobranca_auto, ordem)
                 values (:plano, :nome, :preco, :preco_vip, :anual_desconto, :vans, :alunos, :destaque,
                         cast(:itens as jsonb), :cobranca_auto, coalesce((select max(ordem) from config_planos), 0) + 1)""",
              **dict(d, itens=_json.dumps(d["itens"], ensure_ascii=False), cobranca_auto=bool(d.get("cobranca_auto"))))


def gestores_no_plano(plano: str, hoje: date) -> pd.DataFrame:
    """Empresas ativas com esse plano em vigor (pago, degustação ou cortesia)."""
    return db.ao_vivo("""select nome, plano_tipo, plano_ate from condutores
                         where ativo and plano = :p and (plano_ate is null or plano_ate >= :h) order by nome""",
                      p=plano, h=hoje)


def excluir_plano(plano: str, hoje: date) -> str | None:
    """Exclui o plano se nenhum gestor ativo estiver nele. Devolve o motivo se não puder."""
    from core import planos as pl
    g = gestores_no_plano(plano, hoje)
    if len(g):
        return f"{len(g)} gestor(es) ativo(s) neste plano: " + ", ".join(g["nome"].head(5))
    for chave, campo, nome in (("degustacao", "plano", "a degustação de conta nova"),
                               ("indicacao", "plano_degustacao", "o presente da indicação")):
        atual = db.ao_vivo("select valor from config where chave = :c", c=chave)     # sem cache: decisão de exclusão
        if len(atual) and (atual.iloc[0]["valor"] or {}).get(campo, pl.CONFIG_PADRAO[chave].get(campo)) == plano:
            return f"Esse plano é usado n{nome} (aba Degustação/Indicação) — troque lá antes."
    if db.um("select 1 as x from condutores where pedido->>'plano' = :p", p=plano):
        return "Há pedido de assinatura aguardando neste plano — confirme ou descarte antes."
    if len(db.consultar("select plano from config_planos")) <= 1:
        return "Precisa existir pelo menos um plano."
    with db.transacao() as s:
        s.execute(text("delete from campanhas where plano = :p"), dict(p=plano))
        s.execute(text("""update cupons set planos = nullif((select coalesce(jsonb_agg(x), '[]'::jsonb)
                                                              from jsonb_array_elements_text(planos) x where x <> :p),
                                                             '[]'::jsonb)
                          where planos ? :p"""), dict(p=plano))
        s.execute(text("delete from config_planos where plano = :p"), dict(p=plano))
    return None


def excluir_cupom(cupom_id):
    db.gravar("delete from cupons where id = cast(:i as uuid)", i=str(cupom_id))


def excluir_campanha(camp_id):
    db.gravar("delete from campanhas where id = cast(:i as uuid)", i=str(camp_id))


def precos_antigos(hoje: date) -> pd.DataFrame:
    """Assinantes pagando um preço travado diferente do preço de tabela atual do plano deles
    (fica de fora quem tem cupom/campanha em andamento ou preço combinado)."""
    return db.ao_vivo(f"""
        select c.id, c.nome, c.plano, cp.nome as plano_nome, c.periodo, c.vip, c.preco_mensal as atual,
               {_SQL_PRECO_REGULAR} as novo
        from condutores c join config_planos cp on cp.plano = c.plano
        where c.ativo and c.plano_tipo = 'pago' and (c.plano_ate is null or c.plano_ate >= :h)
          and c.preco_combinado is null and c.preco_mensal is not null
          and (c.desconto_ate is null or c.desconto_ate < :h)
          and coalesce(c.desconto_origem, '') not in ('cupom', 'campanha', 'combinado')
          and c.preco_mensal <> {_SQL_PRECO_REGULAR}
        order by cp.ordem, c.nome""", h=hoje)


def atualizar_para_preco_novo(ids: list):
    """Passa os assinantes escolhidos para o preço de tabela atual do plano deles."""
    if not ids:
        return
    db.gravar(f"""update condutores c set preco_mensal = {_SQL_PRECO_REGULAR}, desconto_origem = null, desconto_ate = null
                  from config_planos cp
                  where cp.plano = c.plano and c.id = any(cast(:ids as uuid[]))""", ids=[str(i) for i in ids])


def aplicar_degustacao_inicial(cid, hoje: date) -> tuple[str, date] | None:
    """Conta nova (sem indicação): degustação automática configurada em Promoções."""
    from datetime import timedelta
    from core import planos as pl
    cfg = pl.config("degustacao")
    plano = cfg.get("plano")
    if not cfg.get("ativo") or plano not in pl.catalogo():
        return None
    ate = hoje + timedelta(days=int(cfg.get("dias") or 15))
    definir_plano(cid, plano, ate, "teste")
    return plano, ate


def empresas_por_id(ids: list) -> dict:
    if not ids:
        return {}
    df = db.ao_vivo("select * from condutores where id = any(cast(:ids as uuid[]))", ids=[str(i) for i in ids])
    return {str(r["id"]): r for r in df.to_dict("records")}


# ------------------------------------------------------------------ modo fácil
def definir_modo(cid, modo: str):
    db.gravar("update condutores set modo = :m where id = cast(:cid as uuid)", m=modo, cid=str(cid))


def alunos_facil(cid, van=None) -> pd.DataFrame:
    """Lista enxuta: aluno, WhatsApp e nome do responsável principal, valor e vencimento."""
    return db.ao_vivo(f"""
        select p.id, p.nome, p.mensalidade as valor, coalesce(p.dia_vencimento, c.dia_vencimento) as vencimento,
               p.ativo, r.id as responsavel_id, r.nome as responsavel, r.telefone as whatsapp
        from passageiros p join condutores c on c.id = p.condutor_id
        left join lateral (select r.* from passageiro_responsavel pr join responsaveis r on r.id = pr.responsavel_id
                           where pr.passageiro_id = p.id order by pr.financeiro desc, r.criado_em limit 1) r on true
        where p.condutor_id = :cid and {_filtro_van('p.van_id')}
        order by p.ativo desc, p.ordem_rota, p.nome""", cid=cid, van=van)


def cadastro_rapido(cid, van, nome: str, whatsapp: str | None, valor: float, dia: int | None,
                    responsavel: str | None = None) -> str:
    """Aluno em 4 campos: cria o aluno na van e o responsável (financeiro) com o WhatsApp."""
    from core.fmt import hoje
    pid = salvar_passageiro(cid, dict(nome=nome.strip(), turno="manha", mensalidade=valor or 0, van_id=van,
                                      dia_vencimento=dia, faz_ida=True, faz_volta=True, ativo=True,
                                      inicio=hoje()))
    if whatsapp or responsavel:
        vincular_responsavel(cid, pid, dict(nome=(responsavel or "").strip() or f"Responsável de {nome.split()[0]}",
                                            telefone=whatsapp or None), financeiro=True)
    return pid


def atualizar_facil(cid, pid, nome: str, whatsapp: str | None, valor: float, dia: int | None, ativo: bool,
                    responsavel_id=None):
    db.gravar("""update passageiros set nome=:n, mensalidade=:v, dia_vencimento=:d, ativo=:a
                 where id = cast(:p as uuid) and condutor_id = :cid""",
              n=nome.strip(), v=valor or 0, d=dia, a=ativo, p=str(pid), cid=cid)
    if responsavel_id:
        db.gravar("update responsaveis set telefone=:t where id = cast(:r as uuid) and condutor_id = :cid",
                  t=whatsapp or None, r=str(responsavel_id), cid=cid)
    elif whatsapp:
        vincular_responsavel(cid, str(pid), dict(nome=f"Responsável de {nome.split()[0]}", telefone=whatsapp),
                             financeiro=True)


# ------------------------------------------------------------------ localização da van (link "ver a van no mapa")
def ligar_localizacao(cid, van, horas: int = 4) -> str:
    """Liga o compartilhamento: mantém o link se ainda estiver valendo, senão cria outro. Devolve o token."""
    import secrets
    r = db.ao_vivo("""select loc_token, loc_ate from vans where id = cast(:v as uuid) and condutor_id = :cid""",
                   v=str(van), cid=cid)
    if not len(r):
        raise ValueError("Van não encontrada.")
    tok = r.iloc[0]["loc_token"]
    ate = r.iloc[0]["loc_ate"]
    ainda = ate is not None and db.um("select now() < cast(:a as timestamptz) as ok", a=ate)["ok"]
    if not tok or not ainda:
        tok = secrets.token_urlsafe(9)
    db.gravar(f"""update vans set loc_token = :t, loc_ate = now() + interval '{int(horas)} hours'
                  where id = cast(:v as uuid) and condutor_id = :cid""", t=tok, v=str(van), cid=cid)
    return tok


def salvar_posicao(cid, van, lat: float, lng: float, precisao: float | None):
    db.gravar("""update vans set loc_lat=:la, loc_lng=:lo, loc_precisao=:p, loc_em=now()
                 where id = cast(:v as uuid) and condutor_id = :cid and loc_ate > now()""",
              la=lat, lo=lng, p=precisao, v=str(van), cid=cid)


def parar_localizacao(cid, van):
    db.gravar("""update vans set loc_ate = now(), loc_lat = null, loc_lng = null, loc_em = null
                 where id = cast(:v as uuid) and condutor_id = :cid""", v=str(van), cid=cid)


def localizacao_van(cid, van) -> dict | None:
    df = db.ao_vivo("""select loc_token, loc_lat, loc_lng, loc_precisao, loc_em, loc_ate, (loc_ate > now()) as ativa
                       from vans where id = cast(:v as uuid) and condutor_id = :cid""", v=str(van), cid=cid)
    return df.iloc[0].to_dict() if len(df) else None


def posicao_publica(token: str) -> dict | None:
    """Para a página pública do link: só a van e a empresa — nenhum dado de criança."""
    if not token or len(token) > 40:
        return None
    df = db.ao_vivo("""select v.nome as van, c.nome as empresa, v.loc_lat, v.loc_lng, v.loc_precisao, v.loc_em,
                              v.loc_ate, (v.loc_ate > now()) as ativa
                       from vans v join condutores c on c.id = v.condutor_id
                       where v.loc_token = :t""", t=token)
    return df.iloc[0].to_dict() if len(df) else None



# ------------------------------------------------------------------ Asaas (dados locais)
def salvar_documento(cid, doc: str):
    db.gravar("update condutores set documento = :d where id = cast(:cid as uuid)", d=doc, cid=str(cid))


def cobrancas_asaas(cid, assinatura: str | None = None) -> list[dict]:
    df = db.ao_vivo("""select id, assinatura, valor, status, vencimento, link from asaas_pagamentos
                       where condutor_id = cast(:cid as uuid) and (cast(:a as text) is null or assinatura = :a)
                       order by vencimento desc""", cid=str(cid), a=assinatura)
    return df.to_dict("records")


# ------------------------------------------------------------------ contrato: link seguro para baixar
def token_contrato(contrato_id) -> str:
    import secrets
    r = db.um("select link_token from contratos where id = cast(:i as uuid)", i=str(contrato_id))
    if r and r.get("link_token"):
        return r["link_token"]
    tok = secrets.token_urlsafe(18)
    db.gravar("update contratos set link_token = :t where id = cast(:i as uuid) and link_token is null",
              t=tok, i=str(contrato_id))
    return (db.ao_vivo("select link_token from contratos where id = cast(:i as uuid)", i=str(contrato_id))
            .iloc[0]["link_token"])


def contrato_por_token(tok: str) -> dict | None:
    if not tok or len(tok) > 40:
        return None
    df = db.ao_vivo("""select c.*, p.nome as aluno from contratos c join passageiros p on p.id = c.passageiro_id
                       where c.link_token = :t and c.responsavel_assinou_em is not null""", t=tok)
    return df.iloc[0].to_dict() if len(df) else None


# ------------------------------------------------------------------ Asaas do gestor (cobrança dos pais)
def conectar_asaas_gestor(cid, chave_cifrada: str, ambiente: str):
    db.gravar("update condutores set asaas_gestor_chave = :k, asaas_gestor_ambiente = :a where id = cast(:cid as uuid)",
              k=chave_cifrada, a=ambiente, cid=str(cid))


def desconectar_asaas_gestor(cid):
    db.gravar("update condutores set asaas_gestor_chave = null where id = cast(:cid as uuid)", cid=str(cid))


# ------------------------------------------------------------------ fidelização: pausa de férias, cancelamento, dados
def pausar(cid, hoje: date, api=None) -> date:
    """Liga a pausa de férias (preço reduzido por N dias). Com assinatura no Asaas, as próximas cobranças já vêm
    com o valor da pausa; quando a pausa acaba, a sincronização volta o valor normal sozinha."""
    from datetime import timedelta
    from core import planos as pl
    cfg = pl.config("fidelidade")
    ate = hoje + timedelta(days=int(cfg.get("pausa_dias") or 60))
    db.gravar("""update condutores set pausa_ate = :a, pausa_ultima = :h, cancelado_em = null
                 where id = cast(:c as uuid)""", a=ate, h=hoje, c=str(cid))
    _ajustar_valor_asaas(cid, hoje, api)
    return ate


def encerrar_pausa(cid, hoje: date, api=None):
    from datetime import timedelta
    db.gravar("update condutores set pausa_ate = :a where id = cast(:c as uuid) and pausa_ate >= :h",
              a=hoje - timedelta(days=1), h=hoje, c=str(cid))
    _ajustar_valor_asaas(cid, hoje, api)


def _ajustar_valor_asaas(cid, hoje: date, api):
    from core import planos as pl
    emp = empresa(cid)
    if not (api and emp and emp.get("asaas_assinatura")):
        return
    mensal = pl.preco_vigente(dict(emp, plano_ate=None), hoje)
    valor = round(mensal * (12 if (emp.get("periodo") or "mensal") == "anual" else 1), 2)
    if valor and abs(valor - float(emp.get("asaas_valor") or 0)) > 0.009:
        api.atualizar_valor(emp["asaas_assinatura"], valor)
        db.gravar("update condutores set asaas_valor = :v where id = cast(:c as uuid)", v=valor, c=str(cid))


def cancelar_plano(cid, hoje: date, api=None):
    """Cancela de vez: para a cobrança automática, marca o cancelamento e (pela regra) perde o Passageiro VIP.
    O plano segue até o fim do período já pago."""
    from core import planos as pl
    emp = empresa(cid)
    if api and emp and emp.get("asaas_assinatura"):
        from core import asaas
        asaas.cancelar_assinatura(api, db.conexao(db.banco_ativo()).engine, emp)
    perde = bool(pl.config("fidelidade").get("perde_vip", True))
    db.gravar(f"""update condutores set cancelado_em = :h, pausa_ate = null, pedido = null
                  {", vip = false, perdeu_vip = true" if perde else ""}
                  where id = cast(:c as uuid)""", h=hoje, c=str(cid))


def dados_vencidos(hoje: date) -> pd.DataFrame:
    """Empresas sem plano há mais que o prazo de guarda (e com dados ainda não apagados)."""
    from core import planos as pl
    dias = int(pl.config("fidelidade").get("dados_dias") or 60)
    return db.ao_vivo("""
        select c.id, c.nome, c.plano, c.plano_tipo, c.plano_ate, c.cancelado_em,
               (select count(*) from passageiros p where p.condutor_id = c.id) as alunos,
               (select count(*) from vans v where v.condutor_id = c.id) as vans
        from condutores c
        where c.dados_apagados_em is null and coalesce(c.plano_tipo, 'pago') <> 'cortesia'
          and c.plano_ate is not null and c.plano_ate + cast(:d as int) < :h
        order by c.plano_ate""", d=dias, h=hoje)


def apagar_dados_empresa(cid, hoje: date):
    """Apaga os dados de operação (alunos, responsáveis, vans, escolas, mensalidades, contratos, financeiro, chamadas,
    suporte). A conta e o histórico de assinatura ficam — a pessoa pode assinar de novo e começar do zero."""
    with db.transacao() as s:
        for t in ("chamadas", "mensalidades", "contratos", "lancamentos", "passageiros", "responsaveis", "vans",
                  "escolas", "suporte_mensagens"):
            s.execute(text(f"delete from {t} where condutor_id = cast(:c as uuid)"), {"c": str(cid)})
        s.execute(text("update condutores set dados_apagados_em = :h where id = cast(:c as uuid)"),
                  {"h": hoje, "c": str(cid)})


# ------------------------------------------------------------------ avisos do gestor para os pais
def salvar_aviso(cid, alvo: str, texto: str, por: str, ate: date | None, van_id=None, passageiro_id=None):
    db.gravar("""insert into avisos (condutor_id, alvo, van_id, passageiro_id, texto, criado_por, ate)
                 values (:c, :a, cast(:v as uuid), cast(:p as uuid), :t, :por, :ate)""",
              c=cid, a=alvo, v=str(van_id) if van_id else None, p=str(passageiro_id) if passageiro_id else None,
              t=texto.strip()[:1000], por=por, ate=ate)


def avisos_empresa(cid) -> pd.DataFrame:
    return db.ao_vivo("""select a.id, a.alvo, a.texto, a.criado_em, a.ate, a.criado_por, v.nome as van, p.nome as aluno
                         from avisos a left join vans v on v.id = a.van_id left join passageiros p on p.id = a.passageiro_id
                         where a.condutor_id = :c order by a.criado_em desc limit 50""", c=cid)


def excluir_aviso(cid, aid):
    db.gravar("delete from avisos where id = cast(:a as uuid) and condutor_id = :c", a=str(aid), c=cid)


def avisos_dos_filhos(pids: list[str], hoje: date) -> pd.DataFrame:
    """Avisos em vigor para cada filho: os gerais da empresa, os da van dele e os só dele (últimos 30 dias)."""
    if not pids:
        return pd.DataFrame()
    return db.ao_vivo("""
        select p.id as passageiro_id, a.id, a.alvo, a.texto, a.criado_em, a.ate
        from passageiros p join avisos a on a.condutor_id = p.condutor_id
         and (a.alvo = 'todos' or (a.alvo = 'van' and a.van_id = p.van_id) or (a.alvo = 'aluno' and a.passageiro_id = p.id))
        where p.id = any(cast(:ids as uuid[])) and (a.ate is null or a.ate >= :h)
          and a.criado_em > now() - interval '30 days'
        order by a.criado_em desc""", ids=pids, h=hoje)
