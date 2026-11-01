-- Pequenos a Bordo — schema completo (Postgres / Neon)
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
