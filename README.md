# 🚐 Pequenos a Bordo

App de gestão para **motorista de van escolar**, com área para os **pais**.
Feito com **Streamlit + Neon (Postgres) + GitHub**, login com Google. Inspirado no SmartVan, do nosso jeito.

## Quem usa

| Perfil | Como entra | O que vê |
|---|---|---|
| **Gestor** (dono da empresa) | Cria a empresa no 1º acesso (só nome e WhatsApp) | Tudo: várias vans, motoristas, alunos, mensalidades, financeiro (geral ou por van) |
| **Motorista** | O gestor cadastra o e-mail do Google dele na van | Só a(s) van(s) que dirige: rota, chamada e os alunos — sem valores |
| **Responsável** (pais) | O gestor cadastra o e-mail do Google dele no aluno | Carteirinha, embarque do dia, avisar falta, mensalidades e Pix |
| **Admin** | E-mail em `[app] admins` nos Secrets | Lista de empresas, ativar/desativar |

O gestor pode ser também o motorista de uma das vans ("Eu dirijo esta van").

## Telas do gestor

| Tela | O que faz |
|---|---|
| **Hoje** | Lucro e recebido do mês, alunos × lugares das vans, faltas avisadas, mensalidades para cobrar, aniversariantes |
| **Rota e chamada** | Por van: ida/volta, Embarcou / Na escola (Entregue) / Faltou, aviso no WhatsApp, rota no Google Maps, ordem da rota, frequência |
| **Mensalidades** | Geradas sozinhas todo mês; receber, estornar, ajustar, isentar, cobrar no WhatsApp com Pix; filtro por van |
| **Financeiro** | Despesas e receitas (de uma van ou gerais), lucro do mês, 12 meses e resultado por van |
| **Alunos e responsáveis** | Van, escola, turno, endereço, cuidados, contrato, responsáveis |
| **Vans e motoristas** | Apelido, veículo, placa, lugares e quem dirige (e-mail do Google) |
| **Escolas** · **Minha empresa** | Endereço/horários · Pix e vencimento padrão |

## Estrutura
```
app.py              login + menu por perfil (condutor / responsável / admin)
core/db.py          conexão com o Neon, cache de leitura, cria as tabelas sozinho
core/auth.py        login Google + perfil
core/repo.py        todas as consultas (sempre filtradas pelo condutor)
core/fmt.py         R$, datas, links de WhatsApp e Google Maps
telas/              uma tela por arquivo
db/001_schema.sql   tabelas (aplicado automaticamente no 1º acesso)
```

---

## Como colocar no ar

### 1. Banco — Neon
1. **neon.com** → *New project*: nome `vanescolar`, Postgres 17, região **AWS US East** (perto do Streamlit Cloud).
2. **Connect** → copie a *connection string* e troque `postgresql://` por **`postgresql+psycopg://`**.
   As tabelas são criadas pelo próprio app no 1º acesso.

### 2. Login — Google
Dá para **reaproveitar o cliente OAuth do app de finanças**: em *Credenciais* → o ID do cliente →
**URIs de redirecionamento autorizados** → adicione `https://<endereço-do-app>.streamlit.app/oauth2callback`.
(Ou crie um cliente novo do tipo *Aplicativo da Web* com essa URI.)

> **Pais e outros condutores precisam conseguir entrar.** Na *Tela de consentimento OAuth*, com o app em
> modo *Teste* só entram os e-mails da lista de *Usuários de teste*. Para abrir para todos, clique em
> **Publicar app** — com os escopos básicos (e-mail e perfil) o Google não exige verificação.

### 3. Streamlit Cloud
1. **share.streamlit.io** → *Create app* → repositório `VanEscolar` (nome do repo mantido), branch `main`, arquivo `app.py`.
2. *Advanced settings* → **Secrets**: cole o conteúdo de `.streamlit/secrets.toml.example` preenchido.
   `cookie_secret`: qualquer frase longa e aleatória.

### Rodar no computador
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # preencha; para testar sem Google use dev_email
streamlit run app.py
```

## Próximas ideias
- Contrato em PDF para assinatura dos pais
- Recibo de pagamento (PDF) e lembrete automático de vencimento
- Lista de espera e reajuste anual de mensalidades em lote
- Manutenção preventiva por km (óleo, pneus) e vencimento de vistoria/CNH
- Localização da van em tempo real para os pais
