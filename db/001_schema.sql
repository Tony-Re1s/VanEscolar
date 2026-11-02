-- Turminha a Bordo — schema completo (Postgres / Neon)
-- O app aplica este arquivo sozinho no 1º acesso (tudo é "if not exists").
-- Isolamento: toda tabela de dados tem condutor_id; o app sempre filtra por ele.

create extension if not exists pgcrypto;

do $$ begin
  create type turno as enum ('manha', 'tarde', 'integral', 'noite');
exception when duplicate_object then null; end $$;

do $$ begin
  create type trecho as enum ('ida', 'volta');
exception when duplicate_object then null; end $$;

do $$ begin
  create type status_chamada as enum ('embarcou', 'desembarcou', 'faltou');
exception when duplicate_object then null; end $$;

do $$ begin
  create type tipo_lanc as enum ('receita', 'despesa');
exception when duplicate_object then null; end $$;

-- Quem já entrou no app (login Google)
create table if not exists usuarios (
  id             uuid primary key default gen_random_uuid(),
  email          text not null unique,
  nome           text,
  criado_em      timestamptz not null default now(),
  ultimo_acesso  timestamptz
);

-- Condutor = o "dono" dos dados. Um usuário pode ter um cadastro de condutor.
create table if not exists condutores (
  id               uuid primary key default gen_random_uuid(),
  usuario_id       uuid not null unique references usuarios(id) on delete cascade,
  nome             text not null,
  telefone         text,
  cnh              text,
  veiculo          text,
  placa            text,
  capacidade       int not null default 15,
  chave_pix        text,
  dia_vencimento   int not null default 10 check (dia_vencimento between 1 and 28),
  ativo            boolean not null default true,
  criado_em        timestamptz not null default now()
);

create table if not exists escolas (
  id            uuid primary key default gen_random_uuid(),
  condutor_id   uuid not null references condutores(id) on delete cascade,
  nome          text not null,
  endereco      text,
  telefone      text,
  entrada_manha time, saida_manha time,
  entrada_tarde time, saida_tarde time,
  ativo         boolean not null default true,
  criado_em     timestamptz not null default now()
);
create index if not exists ix_escolas_condutor on escolas(condutor_id);

create table if not exists passageiros (
  id              uuid primary key default gen_random_uuid(),
  condutor_id     uuid not null references condutores(id) on delete cascade,
  escola_id       uuid references escolas(id) on delete set null,
  nome            text not null,
  data_nasc       date,
  serie           text,
  turno           turno not null default 'manha',
  endereco        text,
  bairro          text,
  referencia      text,
  observacoes     text,           -- alergias, cuidados, quem pode buscar...
  mensalidade     numeric(10,2) not null default 0,
  dia_vencimento  int check (dia_vencimento between 1 and 28),   -- vazio = padrão do condutor
  inicio          date not null default current_date,
  fim             date,
  faz_ida         boolean not null default true,
  faz_volta       boolean not null default true,
  ordem_rota      int not null default 0,
  ativo           boolean not null default true,
  criado_em       timestamptz not null default now()
);
create index if not exists ix_pass_condutor on passageiros(condutor_id);

-- Responsáveis (pais). E-mail = o do Google, para entrar na área dos pais.
create table if not exists responsaveis (
  id           uuid primary key default gen_random_uuid(),
  condutor_id  uuid not null references condutores(id) on delete cascade,
  nome         text not null,
  parentesco   text,
  telefone     text,
  email        text,
  criado_em    timestamptz not null default now()
);
create index if not exists ix_resp_condutor on responsaveis(condutor_id);
create index if not exists ix_resp_email on responsaveis(lower(email));

create table if not exists passageiro_responsavel (
  passageiro_id   uuid not null references passageiros(id) on delete cascade,
  responsavel_id  uuid not null references responsaveis(id) on delete cascade,
  financeiro      boolean not null default true,   -- quem recebe a cobrança
  primary key (passageiro_id, responsavel_id)
);

-- Uma mensalidade por passageiro por mês
create table if not exists mensalidades (
  id             uuid primary key default gen_random_uuid(),
  condutor_id    uuid not null references condutores(id) on delete cascade,
  passageiro_id  uuid not null references passageiros(id) on delete cascade,
  competencia    date not null,          -- sempre dia 1 do mês
  valor          numeric(10,2) not null,
  vencimento     date not null,
  pago_em        date,
  valor_pago     numeric(10,2),
  forma          text,                   -- pix, dinheiro, transferência, cartão
  obs            text,
  criado_em      timestamptz not null default now(),
  unique (passageiro_id, competencia)
);
create index if not exists ix_mens_condutor on mensalidades(condutor_id, competencia);

-- Outras receitas (passeio, viagem) e todas as despesas
create table if not exists lancamentos (
  id           uuid primary key default gen_random_uuid(),
  condutor_id  uuid not null references condutores(id) on delete cascade,
  tipo         tipo_lanc not null,
  categoria    text not null,
  descricao    text,
  valor        numeric(10,2) not null check (valor > 0),
  data         date not null default current_date,
  km           int,                      -- hodômetro (opcional, combustível/manutenção)
  criado_em    timestamptz not null default now()
);
create index if not exists ix_lanc_condutor on lancamentos(condutor_id, data);

-- Chamada do dia: embarque/desembarque/falta, por trecho
create table if not exists chamadas (
  passageiro_id  uuid not null references passageiros(id) on delete cascade,
  condutor_id    uuid not null references condutores(id) on delete cascade,
  data           date not null,
  trecho         trecho not null,
  status         status_chamada not null,
  hora           timestamptz not null default now(),
  primary key (passageiro_id, data, trecho)
);
create index if not exists ix_cham_condutor on chamadas(condutor_id, data);

-- Aviso de ausência feito pelos pais (ou pelo condutor)
create table if not exists ausencias (
  id             uuid primary key default gen_random_uuid(),
  passageiro_id  uuid not null references passageiros(id) on delete cascade,
  data           date not null,
  ida            boolean not null default true,
  volta          boolean not null default true,
  motivo         text,
  criado_por     uuid references usuarios(id) on delete set null,
  criado_em      timestamptz not null default now(),
  unique (passageiro_id, data)
);

-- ============================================================================================
-- v2 — empresa (gestor) com várias vans; cada van tem um motorista (o próprio gestor ou outra
-- pessoa, que entra com o Google pelo e-mail cadastrado aqui e só vê a van dela).
-- ============================================================================================
create table if not exists vans (
  id                  uuid primary key default gen_random_uuid(),
  condutor_id         uuid not null references condutores(id) on delete cascade,   -- a empresa/gestor
  nome                text not null,                -- apelido: "Van 1", "Van da manhã", "Sprinter branca"
  veiculo             text,
  placa               text,
  capacidade          int not null default 15,
  motorista_nome      text,
  motorista_email     text,                         -- e-mail do Google do motorista
  motorista_telefone  text,
  motorista_cnh       text,
  ativo               boolean not null default true,
  criado_em           timestamptz not null default now()
);
create index if not exists ix_vans_condutor on vans(condutor_id);
create index if not exists ix_vans_motorista on vans(lower(motorista_email));

alter table passageiros add column if not exists van_id uuid references vans(id) on delete set null;
alter table lancamentos add column if not exists van_id uuid references vans(id) on delete set null;
create index if not exists ix_pass_van on passageiros(van_id);

-- dados da v1: quem tinha veículo/placa no cadastro ganha a "Van 1" (dirigida por ele) e os alunos vão para ela
with novas as (
  insert into vans (condutor_id, nome, veiculo, placa, capacidade, motorista_nome, motorista_email,
                    motorista_telefone, motorista_cnh)
  select c.id, 'Van 1', c.veiculo, c.placa, c.capacidade, c.nome, u.email, c.telefone, c.cnh
  from condutores c join usuarios u on u.id = c.usuario_id
  where (c.placa is not null or c.veiculo is not null)
    and not exists (select 1 from vans v where v.condutor_id = c.id)
  returning id, condutor_id
)
update passageiros p set van_id = novas.id from novas where p.condutor_id = novas.condutor_id and p.van_id is null;

-- ============================================================================================
-- v3 — contrato digital: o gestor define os dados da contratada e as cláusulas; o responsável
-- preenche os dados dele, aceita e envia; o gestor contra-assina. O texto assinado fica congelado.
-- ============================================================================================
alter table condutores add column if not exists razao_social text;
alter table condutores add column if not exists cnpj text;
alter table condutores add column if not exists cidade text;
alter table condutores add column if not exists contrato_clausulas text;     -- vazio = modelo padrão

create table if not exists contratos (
  id                     uuid primary key default gen_random_uuid(),
  condutor_id            uuid not null references condutores(id) on delete cascade,
  passageiro_id          uuid not null references passageiros(id) on delete cascade,
  ano                    int not null,
  texto                  text not null,             -- contrato completo como foi assinado
  dados                  jsonb not null,            -- campos preenchidos pelo responsável
  codigo                 text not null,             -- hash curto do texto+dados (confere a integridade)
  responsavel_email      text not null,
  responsavel_nome       text not null,
  responsavel_assinou_em timestamptz not null default now(),
  responsavel_ip         text,
  contratada_por         text,
  contratada_assinou_em  timestamptz,
  criado_em              timestamptz not null default now(),
  unique (passageiro_id, ano)
);
create index if not exists ix_contratos_condutor on contratos(condutor_id, ano);

-- v4 — contrato em duas etapas: o gestor prepara as condições do serviço (servico) e libera;
-- o responsável completa os dados dele (dados) e assina. Até lá os campos de assinatura ficam vazios.
alter table contratos add column if not exists servico jsonb;
alter table contratos add column if not exists preparado_por text;
alter table contratos add column if not exists preparado_em timestamptz;
alter table contratos alter column texto drop not null, alter column dados drop not null,
  alter column codigo drop not null, alter column responsavel_email drop not null,
  alter column responsavel_nome drop not null, alter column responsavel_assinou_em drop not null,
  alter column responsavel_assinou_em drop default;

-- v5 — início de rota (os pais veem que a van saiu)
create table if not exists rotas_iniciadas (
  van_id      uuid not null references vans(id) on delete cascade,
  data        date not null,
  trecho      trecho not null,
  iniciada_em timestamptz not null default now(),
  iniciada_por text,
  primary key (van_id, data, trecho)
);

-- v6 — planos (cobrança por nº de vans). Até o pagamento automático, o admin libera o plano.
alter table condutores add column if not exists plano text not null default 'gratis';
alter table condutores add column if not exists plano_ate date;

-- v7 — tipo do plano: pago, teste (degustação com prazo) ou cortesia (liberado sem cobrar)
alter table condutores add column if not exists plano_tipo text not null default 'pago';

-- v8 — promoções: preços editáveis, cupons, campanhas, plano anual, Passageiro VIP e indicação
create table if not exists config_planos (
  plano           text primary key,             -- gratis | basico | pro | frota
  nome            text not null,
  preco           numeric(10,2) not null default 0,
  preco_vip       numeric(10,2),                -- preço travado do Passageiro VIP (null = sem VIP neste plano)
  anual_desconto  numeric(5,2) not null default 0,   -- % de desconto pagando 12 meses
  vans            int,                          -- null = ilimitado
  alunos          int,
  destaque        text,
  itens           jsonb not null default '[]'::jsonb,
  ordem           int not null default 0
);

create table if not exists config (
  chave  text primary key,
  valor  jsonb not null
);

create table if not exists cupons (
  id             uuid primary key default gen_random_uuid(),
  codigo         text not null unique,          -- sempre maiúsculo
  tipo           text not null check (tipo in ('pct', 'valor', 'dias')),
  valor          numeric(10,2) not null check (valor > 0),   -- % | R$ | dias
  planos         jsonb,                         -- ["pro","frota"]; null = todos
  duracao_meses  int,                           -- desconto por N meses; null = para sempre
  valido_ate     date,
  limite_usos    int,
  ativo          boolean not null default true,
  criado_em      timestamptz not null default now()
);

create table if not exists campanhas (
  id             uuid primary key default gen_random_uuid(),
  nome           text not null,
  plano          text not null,
  preco          numeric(10,2) not null check (preco >= 0),
  inicio         date not null,
  fim            date not null,
  duracao_meses  int,                           -- preço promocional por N meses; null = para sempre
  ativo          boolean not null default true,
  criado_em      timestamptz not null default now()
);

alter table condutores add column if not exists periodo text not null default 'mensal';        -- mensal | anual
alter table condutores add column if not exists preco_mensal numeric(10,2);     -- valor por mês combinado na assinatura
alter table condutores add column if not exists desconto_origem text;           -- cupom|campanha|vip|anual|combinado
alter table condutores add column if not exists desconto_ate date;              -- fim do preço promocional (null = sempre)
alter table condutores add column if not exists preco_combinado numeric(10,2);  -- preço negociado pelo admin
alter table condutores add column if not exists vip boolean not null default false;
alter table condutores add column if not exists cupom_id uuid references cupons(id) on delete set null;
alter table condutores add column if not exists pedido jsonb;                   -- pedido de assinatura aguardando pagamento
alter table condutores add column if not exists codigo_indicacao text unique;
alter table condutores add column if not exists indicado_por uuid references condutores(id) on delete set null;
alter table condutores add column if not exists indicacao_contada boolean not null default false;
alter table condutores add column if not exists indicacoes_pagas int not null default 0;
alter table condutores add column if not exists meses_gratis int not null default 0;

create table if not exists cupons_usos (
  cupom_id     uuid not null references cupons(id) on delete cascade,
  condutor_id  uuid not null references condutores(id) on delete cascade,
  usado_em     timestamptz not null default now(),
  primary key (cupom_id, condutor_id)
);

-- valores iniciais (só entram se ainda não existem — depois tudo se ajusta na tela Promoções)
insert into config_planos (plano, nome, preco, preco_vip, anual_desconto, vans, alunos, destaque, itens, ordem)
select v.plano, v.nome, v.preco, v.preco_vip, v.anual_desconto, v.vans, v.alunos, v.destaque, v.itens::jsonb, v.ordem
from (values
  ('gratis', 'Grátis', 0, null, 0, 1, 10, 'Para conhecer',
   '["1 van", "Até 10 alunos", "Rota, chamada e mensalidades", "Área dos pais"]', 1),
  ('basico', 'Básico', 29.90, 24.90, 16.67, 1, null, 'Motorista autônomo',
   '["1 van", "Alunos ilimitados", "Contrato digital com assinatura", "Financeiro e painel"]', 2),
  ('pro', 'Pro', 59.90, 49.90, 16.67, 3, null, 'Mais escolhido',
   '["Até 3 vans", "Motoristas contratados", "Financeiro por van", "Tudo do Básico"]', 3),
  ('frota', 'Frota', 99.90, 84.90, 16.67, null, null, 'Empresas maiores',
   '["Vans ilimitadas", "Motoristas ilimitados", "Suporte prioritário", "Tudo do Pro"]', 4)
) as v(plano, nome, preco, preco_vip, anual_desconto, vans, alunos, destaque, itens, ordem)
where not exists (select 1 from config_planos);   -- só na 1ª vez: depois os planos são do admin

insert into config (chave, valor) values
  ('vip', '{"ativo": true, "vagas": 50, "ate": null}'),
  ('indicacao', '{"ativo": true, "meta": 10, "premio_meses": 2, "plano_degustacao": "pro", "dias_degustacao": 30}'),
  ('degustacao', '{"dias_padrao": 15}')
on conflict (chave) do nothing;

update condutores set codigo_indicacao =
  upper(left(regexp_replace(split_part(nome, ' ', 1), '[^A-Za-z]', '', 'g'), 6)) || upper(substr(md5(id::text), 1, 3))
where codigo_indicacao is null;


-- v9 — sem plano Grátis: planos criados/excluídos pelo admin, degustação automática e bloqueio ao vencer
update config set valor = valor || '{"ativo": true, "plano": "pro", "dias": 15}'::jsonb
where chave = 'degustacao' and not (valor ? 'plano');
do $$
begin
  if not exists (select 1 from config where chave = 'mig_v9_sem_gratis') then
    delete from config_planos where plano = 'gratis';
    -- quem estava no Grátis ganha a degustação padrão (15 dias de Pro) para não ficar bloqueado de surpresa
    update condutores set plano = 'pro', plano_tipo = 'teste', plano_ate = current_date + 15
     where coalesce(plano, 'gratis') = 'gratis';
    insert into config (chave, valor) values ('mig_v9_sem_gratis', 'true');
  end if;
end $$;

-- v10 — preços definidos com o Tony (mercado: SmartVan, Vanzinha, VanGo, Via Van). Roda uma vez só;
-- depois tudo se ajusta em Promoções. Quem já assinava fica no preço que tinha.
do $$
begin
  if not exists (select 1 from config where chave = 'mig_v10_precos') then
    update condutores c set preco_mensal = case when c.vip and cp.preco_vip is not null then cp.preco_vip
                                                else cp.preco end
      from config_planos cp
     where cp.plano = c.plano and c.plano_tipo = 'pago' and c.preco_mensal is null and c.preco_combinado is null;
    update config_planos set preco = 24.90, preco_vip = 19.90, anual_desconto = 17 where plano = 'basico';
    update config_planos set preco = 54.90, preco_vip = 29.90, anual_desconto = 17 where plano = 'pro';
    update config_planos set preco = 99.90, preco_vip = 79.90, anual_desconto = 17 where plano = 'frota';
    update config set valor = valor || '{"ativo": true, "vagas": 200}'::jsonb where chave = 'vip';
    update config set valor = valor || '{"dias": 30}'::jsonb where chave = 'degustacao';
    insert into config (chave, valor) values ('mig_v10_precos', 'true');
  end if;
end $$;

-- v11 — modo fácil e localização da van ao vivo (link público que expira)
alter table condutores add column if not exists modo text not null default 'completo';   -- facil | completo
alter table vans add column if not exists loc_token text unique;      -- link "ver a van no mapa"
alter table vans add column if not exists loc_lat double precision;
alter table vans add column if not exists loc_lng double precision;
alter table vans add column if not exists loc_precisao double precision;
alter table vans add column if not exists loc_em timestamptz;         -- hora da última posição
alter table vans add column if not exists loc_ate timestamptz;        -- o link vale até aqui

-- v12 — Asaas: assinatura recorrente do gestor (Pix, boleto ou cartão). O app consulta o Asaas (Streamlit não
-- recebe webhook): ao abrir Meu plano, pelo botão no painel e a cada 30 min pelo GitHub Actions.
alter table condutores add column if not exists documento text;            -- CPF ou CNPJ de quem paga
alter table condutores add column if not exists asaas_cliente text;
alter table condutores add column if not exists asaas_assinatura text;
alter table condutores add column if not exists asaas_valor numeric(10,2);  -- valor por cobrança hoje no Asaas
create table if not exists asaas_pagamentos (
  id            text primary key,              -- id da cobrança no Asaas (pay_...)
  condutor_id   uuid not null references condutores(id) on delete cascade,
  assinatura    text,
  valor         numeric(10,2),
  status        text,
  vencimento    date,
  link          text,                           -- invoiceUrl (página de pagamento)
  processado    boolean not null default false, -- já liberou o plano
  atualizado_em timestamptz not null default now()
);

-- v13 — link seguro para baixar o contrato assinado (enviado por WhatsApp/e-mail)
alter table contratos add column if not exists link_token text unique;

-- v14 — cobrança mista dos pais: cada gestor pode conectar a própria conta Asaas (opcional) e escolher, por aluno,
-- manual / Asaas por mês / Asaas recorrente. Baixa manual sempre possível. Recurso liberado por plano.
alter table config_planos add column if not exists cobranca_auto boolean not null default false;
do $$
begin
  if not exists (select 1 from config where chave = 'mig_v14_cobranca') then
    update config_planos set cobranca_auto = true where plano in ('pro', 'frota');
    insert into config (chave, valor) values ('mig_v14_cobranca', 'true');
  end if;
end $$;
alter table condutores add column if not exists asaas_gestor_chave text;       -- chave da API do gestor (criptografada)
alter table condutores add column if not exists asaas_gestor_ambiente text;
alter table responsaveis add column if not exists cpf text;
alter table responsaveis add column if not exists asaas_cliente text;
alter table passageiros add column if not exists cobranca text not null default 'manual';   -- manual | asaas | recorrente
alter table passageiros add column if not exists asaas_assinatura text;
alter table mensalidades add column if not exists asaas_id text;
alter table mensalidades add column if not exists asaas_link text;
alter table mensalidades add column if not exists asaas_status text;

-- v15 — divulgadores (Exclusivo): comissão sobre os indicados ativos, textos de divulgação e laboratório
alter table condutores add column if not exists comissao_desde date;     -- quando destravou a comissão (meta batida)
create table if not exists comissoes (
  condutor_id   uuid not null references condutores(id) on delete cascade,
  competencia   date not null,                 -- dia 1 do mês
  ativos        int not null default 0,        -- indicados pagantes ativos no fechamento
  base          numeric(10,2) not null default 0,
  valor         numeric(10,2) not null default 0,
  pago_em       date,
  atualizado_em timestamptz not null default now(),
  primary key (condutor_id, competencia)
);
insert into config (chave, valor) values
  ('comissao', '{"ativo": true, "meta": 100, "pct": 10, "ate": "2027-12-31"}'),
  ('laboratorio', '{}')
on conflict (chave) do nothing;

-- v16 — comissão por faixas (ex.: 50 pagantes → 10%, 100 → 20%), a maior faixa alcançada fica;
--       regra própria por divulgador (faixas/data) — vazia = usa a regra geral
alter table condutores add column if not exists comissao_pico int not null default 0;   -- maior nº de ativos já alcançado
alter table condutores add column if not exists comissao_regra jsonb;                   -- regra própria (opcional)
alter table comissoes add column if not exists pct numeric(5,2);
do $$
begin
  if not exists (select 1 from config where chave = 'mig_v16_faixas') then
    update config set valor = (valor - 'meta' - 'pct')
                              || '{"faixas": [{"min": 50, "pct": 10}, {"min": 100, "pct": 20}]}'::jsonb
     where chave = 'comissao';
    insert into config (chave, valor) values ('mig_v16_faixas', 'true');
  end if;
end $$;

-- v17 — "Fale conosco": chat do assinante com o suporte; as mensagens vão para o Telegram do administrador e as
--       respostas dadas lá (Responder na mensagem) voltam para o app
create table if not exists suporte_mensagens (
  id            bigserial primary key,
  condutor_id   uuid not null references condutores(id) on delete cascade,
  autor         text not null check (autor in ('cliente', 'suporte')),
  autor_email   text,
  texto         text not null,
  criado_em     timestamptz not null default now(),
  tg_msg_id     bigint,            -- id da mensagem no chat do Telegram do administrador
  tg_update_id  bigint unique,     -- resposta que veio do Telegram (evita gravar 2x)
  lida          boolean not null default false
);
create index if not exists ix_suporte_condutor on suporte_mensagens(condutor_id, criado_em);
create index if not exists ix_suporte_tg on suporte_mensagens(tg_msg_id);

-- v18 — como as famílias chamam quem dirige ("Tio Jô", "Tia Rose"): vai nas mensagens de WhatsApp da rota
alter table vans add column if not exists motorista_apelido text;
alter table condutores add column if not exists apelido text;

-- v19 — fidelização: "pausa de férias" (oferecida só ao cancelar ou ao vencer sem pagar), perda do VIP ao cancelar
--       e prazo de guarda dos dados de quem ficou sem plano
alter table condutores add column if not exists pausa_ate date;          -- em pausa até esta data (preço reduzido)
alter table condutores add column if not exists pausa_ultima date;       -- início da última pausa (1 por ano)
alter table condutores add column if not exists cancelado_em date;       -- pediu o cancelamento
alter table condutores add column if not exists dados_apagados_em date;  -- dados apagados depois do prazo
insert into config (chave, valor) values
  ('fidelidade', '{"pausa_preco": 9.9, "pausa_dias": 60, "dados_dias": 60, "perde_vip": true}')
on conflict (chave) do nothing;
alter table condutores add column if not exists perdeu_vip boolean not null default false;   -- cancelou: não volta a ser VIP

-- v20 — avisos do gestor para os pais: para todos, para uma van ou para um aluno (aparecem na área da família)
create table if not exists avisos (
  id             uuid primary key default gen_random_uuid(),
  condutor_id    uuid not null references condutores(id) on delete cascade,
  alvo           text not null check (alvo in ('todos', 'van', 'aluno')),
  van_id         uuid references vans(id) on delete cascade,
  passageiro_id  uuid references passageiros(id) on delete cascade,
  texto          text not null,
  criado_por     text,
  criado_em      timestamptz not null default now(),
  ate            date
);
create index if not exists ix_avisos_condutor on avisos(condutor_id, criado_em);

-- v21 — monitor(a) da van (opcional): entra com o Google e tem a mesma visão do motorista (rota, chamada, avisar pais)
alter table vans add column if not exists monitor_nome text;
alter table vans add column if not exists monitor_email text;
alter table vans add column if not exists monitor_telefone text;
alter table vans add column if not exists monitor_apelido text;

-- v22 — avisos também para a equipe (motoristas e monitores), além dos pais
alter table avisos add column if not exists publico text not null default 'pais';

-- v23 — fim da rota: finalizada sozinha quando não sobra criança pendente, ou pelo motorista/monitor (com conferência
--       das pendentes). Os pais acompanham a van só enquanto a rota do filho está em andamento.
alter table rotas_iniciadas add column if not exists finalizada_em timestamptz;
alter table rotas_iniciadas add column if not exists finalizada_por text;
alter table rotas_iniciadas add column if not exists pendentes_ao_finalizar int;

-- v24 — Mercado Pago como alternativa ao Asaas (o admin escolhe qual recebe as NOVAS assinaturas; quem já assina
--       continua onde está). Cartão = assinatura (preapproval); Pix/boleto = um link por período.
alter table condutores add column if not exists gateway text;            -- onde está a assinatura: asaas | mercadopago
alter table condutores add column if not exists mp_assinatura text;      -- id da assinatura no cartão (preapproval)
alter table condutores add column if not exists mp_valor numeric(10,2);
alter table asaas_pagamentos add column if not exists gateway text not null default 'asaas';

-- v25 — Fretamento: viagens por fora (excursão, festa, aeroporto, empresa…) com orçamento, agenda e financeiro
--       separado do transporte escolar. Liberado por plano (Pro e Frota).
alter table config_planos add column if not exists fretamento boolean not null default false;
do $$
begin
  if not exists (select 1 from config where chave = 'mig_v25_fretamento') then
    update config_planos set fretamento = true where plano in ('pro', 'frota');
    insert into config (chave, valor) values ('mig_v25_fretamento', 'true');
  end if;
end $$;
create table if not exists fretes_clientes (
  id           uuid primary key default gen_random_uuid(),
  condutor_id  uuid not null references condutores(id) on delete cascade,
  nome         text not null,
  telefone     text,
  documento    text,                          -- CPF ou CNPJ (opcional)
  email        text,
  criado_em    timestamptz not null default now()
);
create index if not exists ix_fretes_clientes on fretes_clientes(condutor_id, nome);
create table if not exists fretes (
  id           uuid primary key default gen_random_uuid(),
  condutor_id  uuid not null references condutores(id) on delete cascade,
  cliente_id   uuid references fretes_clientes(id) on delete set null,
  status       text not null default 'orcamento',   -- orcamento | enviado | fechado | realizado | recusado | cancelado
  data_ida     date not null,
  hora_ida     time,
  data_volta   date,
  hora_volta   time,
  origem       text,
  destino      text,
  passageiros  int,
  van_id       uuid references vans(id) on delete set null,
  motorista    text,
  valor        numeric(10,2) not null default 0,
  sinal        numeric(10,2),                 -- quanto pede para reservar a data
  validade     date,                          -- orçamento válido até
  obs          text,
  enviado_em   timestamptz,
  fechado_em   timestamptz,
  criado_em    timestamptz not null default now()
);
create index if not exists ix_fretes on fretes(condutor_id, data_ida);
alter table lancamentos add column if not exists frete_id uuid references fretes(id) on delete set null;

-- v26 — guia de primeiros passos (aparece até o gestor concluir ou esconder)
alter table condutores add column if not exists guia_fechado boolean not null default false;
