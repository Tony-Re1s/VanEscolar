# 🚐 Pequenos a Bordo

App de gestão para **motorista de van escolar**, com área para os **pais**.
Feito com **Streamlit + Neon (Postgres) + GitHub**, login com Google. Inspirado no SmartVan, do nosso jeito.

## O que tem (versão 1)

**Condutor**
| Tela | O que faz |
|---|---|
| **Hoje** | Lucro e recebido do mês, alunos ativos × lugares, faltas avisadas pelos pais, mensalidades vencidas/vencendo em 7 dias com cobrança no WhatsApp, aniversariantes |
| **Rota e chamada** | Ida/volta por turno, botões Embarcou / Na escola (Entregue) / Faltou, aviso "a van está chegando" no WhatsApp, rota no Google Maps na ordem de busca (sem quem avisou falta), ordem da rota, frequência do mês |
| **Mensalidades** | Geradas sozinhas todo mês (dia de vencimento por aluno ou padrão), receber (data, valor, forma), estornar, ajustar valor/vencimento, isentar mês, cobrança pronta no WhatsApp com a chave Pix |
| **Financeiro** | Despesas por categoria (combustível, manutenção, seguro, IPVA, monitora…), outras receitas (passeios), hodômetro, lucro do mês e gráfico de 12 meses (regime de caixa) |
| **Alunos e responsáveis** | Escola, turno, endereço, observações (alergias…), contrato (valor, vencimento, início/fim, ida/volta), responsáveis com WhatsApp e e-mail do Google; irmãos compartilham o responsável |
| **Escolas** | Endereço e horários |
| **Meu cadastro e van** | Veículo, placa, lugares, chave Pix, vencimento padrão |

**Responsável (pais)** — entra com o Google usando o e-mail cadastrado pelo condutor
- Carteirinha digital do aluno (escola, turno, condutor, placa, telefone)
- Status do dia: embarcou / chegou na escola / entregue em casa, com horário
- **Avisar falta** (ida, volta ou as duas, até 90 dias à frente) — aparece na hora para o condutor
- Mensalidades e chave Pix do condutor

**Admin** (e-mails em `[app] admins`) — lista de condutores, ativar/desativar.

Vários condutores usam o mesmo app: cada um cria a própria conta no 1º acesso e só vê os próprios dados.

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
