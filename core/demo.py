"""Dados de demonstração (só para o administrador testar): escolas, 3 vans com motoristas, alunos, responsáveis e
mensalidades do mês — tudo na empresa do próprio admin e com o telefone dele, para as mensagens de WhatsApp chegarem
nele mesmo. Os ids criados ficam guardados em config (chave demo_<empresa>) para apagar tudo depois com um clique."""
import json
from datetime import date

from sqlalchemy import text

from core import db
from core.fmt import inicio_mes, vencimento

ESCOLAS = [("Colégio Monteiro Lobato (demo)", "Rua Itapaiúna, 1200 — Vila Andrade"),
           ("EMEF Vila Sônia (demo)", "Av. Prof. Francisco Morato, 4000 — Vila Sônia")]

# (van, veículo, placa, motorista, e-mail do motorista: None = o próprio admin)
VANS = [("Van Amarela (demo)", "Sprinter", "DEM1A01", None, None),
        ("Van Azul (demo)", "Ducato", "DEM2B02", "Marcos Lima (demo)", "marcos.demo@exemplo.com"),
        ("Van Verde (demo)", "Master", "DEM3C03", "Rita Alves (demo)", "rita.demo@exemplo.com")]

# (aluno, nascimento, série, turno, escola 0/1, endereço, bairro, mensalidade, dia, responsável, parentesco)
ALUNOS = [
    [("Helena Martins", date(2018, 3, 12), "2º ano", "manha", 0, "Rua das Magnólias, 85", "Vila Sônia", 420, 10,
      "Paula Martins", "mãe"),
     ("Theo Ribeiro", date(2017, 8, 2), "3º ano", "manha", 0, "Rua Abílio Soares, 300", "Vila Indiana", 420, 10,
      "Rafael Ribeiro", "pai"),
     ("Laura Nogueira", date(2019, 11, 20), "1º ano", "manha", 1, "Rua Joaquim Nabuco, 51", "Jardim Bonfiglioli", 380,
      5, "Camila Nogueira", "mãe")],
    [("Miguel Santos", date(2016, 5, 9), "4º ano", "tarde", 0, "Rua Cláudio Soares, 72", "Butantã", 450, 15,
      "Juliana Santos", "mãe"),
     ("Sofia Almeida", date(2018, 1, 30), "2º ano", "tarde", 1, "Rua Pirajussara, 410", "Vila Sônia", 400, 10,
      "Bruno Almeida", "pai"),
     ("Davi Oliveira", date(2017, 9, 14), "3º ano", "tarde", 1, "Rua Corinto, 233", "Vila Indiana", 400, 5,
      "Fernanda Oliveira", "mãe")],
    [("Alice Ferreira", date(2015, 7, 3), "5º ano", "manha", 0, "Rua Heitor dos Prazeres, 99", "Morumbi", 480, 10,
      "Marina Ferreira", "mãe"),
     ("Gabriel Costa", date(2016, 12, 18), "4º ano", "manha", 0, "Rua Eng. Jorge Oliva, 140", "Vila Andrade", 480, 15,
      "Lucas Costa", "pai"),
     ("Manuela Rocha", date(2019, 4, 25), "1º ano", "manha", 1, "Rua Itaguaba, 61", "Jardim Peri Peri", 380, 5,
      "Patrícia Rocha", "avó")],
]


def _chave(cid) -> str:
    return f"demo_{cid}"


def existe(cid) -> dict | None:
    r = db.ao_vivo("select valor from config where chave = :k", k=_chave(cid))
    return r.iloc[0]["valor"] if len(r) else None


def criar(cid, telefone: str, email_admin: str, hoje: date) -> dict:
    """Cria tudo numa transação só. Devolve o resumo (quantos de cada)."""
    if existe(cid):
        raise ValueError("Os dados de demonstração já existem — apague antes de criar de novo.")
    ids = dict(escolas=[], vans=[], passageiros=[], responsaveis=[])
    comp = inicio_mes(hoje)
    with db.transacao() as s:
        def ins(sql, **p):
            return str(s.execute(text(sql + " returning id"), p).scalar_one())

        esc = [ins("""insert into escolas (condutor_id, nome, endereco, entrada_manha, saida_manha, entrada_tarde,
                      saida_tarde, ativo) values (:c, :n, :e, '07:00', '12:00', '13:00', '18:00', true)""",
                   c=cid, n=n, e=e) for n, e in ESCOLAS]
        ids["escolas"] = esc
        n_resp = 0
        for (vnome, veic, placa, mot, mot_email), alunos in zip(VANS, ALUNOS):
            vid = ins("""insert into vans (condutor_id, nome, veiculo, placa, capacidade, motorista_nome,
                         motorista_email, motorista_telefone, ativo)
                         values (:c, :n, :v, :p, 15, :mn, :me, :mt, true)""",
                      c=cid, n=vnome, v=veic, p=placa, mn=mot or "Você (teste)", me=mot_email or email_admin,
                      mt=telefone)
            ids["vans"].append(vid)
            for ordem, (nome, nasc, serie, turno, ie, end, bairro, valor, dia, resp, par) in enumerate(alunos, 1):
                pid = ins("""insert into passageiros (condutor_id, escola_id, van_id, nome, data_nasc, serie, turno,
                             endereco, bairro, mensalidade, dia_vencimento, inicio, faz_ida, faz_volta, ordem_rota,
                             ativo)
                             values (:c, :e, :v, :n, :d, :s, cast(:t as turno), :en, :b, :m, :dv, :i, true, true,
                                     :o, true)""",
                          c=cid, e=esc[ie], v=vid, n=nome, d=nasc, s=serie, t=turno, en=end, b=bairro, m=valor,
                          dv=dia, i=comp, o=ordem)
                ids["passageiros"].append(pid)
                # o 1º responsável usa o e-mail do admin (assim ele vê a área da família); os outros, e-mails de
                # exemplo (aparecem em "Ainda não entraram no app")
                email = email_admin if n_resp == 0 else f"{resp.split()[0].lower()}.demo@exemplo.com"
                rid = ins("""insert into responsaveis (condutor_id, nome, parentesco, telefone, email)
                             values (:c, :n, :p, :t, :e)""", c=cid, n=resp, p=par, t=telefone, e=email)
                ids["responsaveis"].append(rid)
                s.execute(text("""insert into passageiro_responsavel (passageiro_id, responsavel_id, financeiro)
                                  values (:p, :r, true)"""), dict(p=pid, r=rid))
                pago = n_resp % 3 == 0          # 1 em cada 3 já pagou o mês
                venc = vencimento(comp, dia)
                s.execute(text("""insert into mensalidades (condutor_id, passageiro_id, competencia, valor, vencimento,
                                  pago_em, valor_pago, forma)
                                  values (:c, :p, :m, :v, :vc, :pg, :vp, :f) on conflict do nothing"""),
                          dict(c=cid, p=pid, m=comp, v=valor, vc=venc, pg=min(venc, hoje) if pago else None,
                               vp=valor if pago else None, f="pix" if pago else None))
                n_resp += 1
        s.execute(text("""insert into config (chave, valor) values (:k, cast(:v as jsonb))"""),
                  dict(k=_chave(cid), v=json.dumps(ids)))
    return {k: len(v) for k, v in ids.items()}


def apagar(cid) -> bool:
    """Apaga só o que a demonstração criou (alunos levam junto mensalidades, chamadas e vínculos)."""
    ids = existe(cid)
    if not ids:
        return False
    with db.transacao() as s:
        for tab, chave in (("passageiros", "passageiros"), ("responsaveis", "responsaveis"), ("vans", "vans"),
                           ("escolas", "escolas")):
            if ids.get(chave):
                s.execute(text(f"delete from {tab} where condutor_id = :c and id = any(cast(:i as uuid[]))"),
                          dict(c=cid, i=ids[chave]))
        s.execute(text("delete from config where chave = :k"), dict(k=_chave(cid)))
    return True
