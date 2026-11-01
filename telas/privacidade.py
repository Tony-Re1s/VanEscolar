"""Política de Privacidade (pública)."""
import streamlit as st

RESPONSAVEL = "José Anthony Reis Lopes"
CONTATO = "joseareislopes@gmail.com"
ATUALIZADA = "01/11/2026"

st.title("Política de Privacidade")
st.caption(f"Pequenos a Bordo · atualizada em {ATUALIZADA}")

st.markdown(f"""<div class='ve-doc'>

#### 1. Quem somos
O **Pequenos a Bordo** (pequenosabordo.streamlit.app) é um aplicativo de gestão de transporte escolar. O
responsável pelo aplicativo é **{RESPONSAVEL}**, contato: **{CONTATO}**.

Cada empresa ou motorista de transporte escolar que usa o app (o **gestor**) decide quais alunos, responsáveis e
motoristas cadastra. Em relação a esses dados, **o gestor é o controlador** e o Pequenos a Bordo atua como
**operador**, tratando os dados em nome dele e conforme esta política. Em relação aos dados de conta dos próprios
gestores, o Pequenos a Bordo é o controlador.

#### 2. Quais dados tratamos
- **Login com Google:** nome, e-mail e foto da conta Google. Não temos acesso à sua senha nem a outros dados do Google.
- **Gestor:** nome ou nome do transporte, WhatsApp, chave Pix, razão social, CNPJ e cidade, informados por ele.
- **Vans e motoristas:** apelido, veículo, placa, lugares e nome, e-mail, WhatsApp e CNH (opcional) do motorista.
- **Alunos:** nome, data de nascimento, série, turno, escola, endereço de embarque, ponto de referência e
  observações informadas pelo gestor (por exemplo, alergias ou quem pode buscar).
- **Responsáveis:** nome, parentesco, telefone e e-mail; e, ao assinar o contrato, CPF, RG, data de nascimento e
  endereço completo.
- **Uso do serviço:** chamada (embarque, entrega, faltas e horários), avisos de falta, início de rota,
  mensalidades e pagamentos registrados, lançamentos financeiros e o registro da assinatura eletrônica do contrato
  (data, hora, e-mail e endereço IP).

#### 3. Dados de crianças e adolescentes
O app trata dados de alunos menores de idade **somente para a prestação do transporte escolar contratado pela
família** e no melhor interesse da criança, conforme o art. 14 da LGPD. Os dados do aluno são cadastrados pelo
gestor com o conhecimento dos pais ou responsáveis, que podem consultá-los na área da família e pedir correção ou
exclusão. Não usamos dados de crianças para publicidade nem os compartilhamos para outros fins.

#### 4. Para que usamos
Para identificar quem entra no app e mostrar a cada pessoa só o que é dela; organizar rotas, chamada e avisos às
famílias; gerar e controlar mensalidades e o financeiro do gestor; registrar e emitir o contrato digital; e manter
a segurança, o funcionamento e o suporte do serviço.

**Bases legais (LGPD, art. 7º e 11):** execução de contrato e procedimentos preliminares; cumprimento de obrigação
legal; legítimo interesse (segurança e melhoria do serviço); e, quando necessário, consentimento — inclusive o
consentimento específico dos pais ou responsáveis para dados de crianças.

#### 5. Com quem compartilhamos
Não vendemos dados. Usamos fornecedores para operar o app, que só tratam os dados para isso:
**Google** (login), **Streamlit / Snowflake** (hospedagem do app), **Neon** (banco de dados) e **GitHub** (código e
cópias de segurança criptografadas). Mensagens de WhatsApp só são enviadas quando o próprio usuário toca no botão e
envia pelo aplicativo dele. Quando houver planos pagos, o processador de pagamentos (ex.: Asaas) receberá os dados
necessários à cobrança do gestor. Também podemos compartilhar dados por ordem judicial ou exigência legal.
Alguns fornecedores ficam fora do Brasil; nesses casos a transferência segue o art. 33 da LGPD.

#### 6. Por quanto tempo guardamos
Enquanto a conta do gestor estiver ativa e pelo tempo necessário para cumprir obrigações legais (por exemplo,
contratos e registros de pagamento). Quando o gestor encerra a conta, os dados são excluídos ou anonimizados em
até 90 dias, salvo o que a lei exigir guardar. As cópias de segurança são substituídas em até 30 dias.

#### 7. Seus direitos
Você pode pedir, a qualquer momento: confirmação e acesso aos seus dados, correção, anonimização, bloqueio ou
exclusão, portabilidade, informação sobre compartilhamento e revogação do consentimento (art. 18 da LGPD).
Se os dados foram cadastrados por um gestor, você pode falar com ele diretamente ou com a gente, e nós
encaminhamos. Contato: **{CONTATO}**. Você também pode reclamar à ANPD.

#### 8. Segurança
Acesso só por login Google e com permissões por perfil (gestor, motorista, responsável); conexão criptografada
(HTTPS); senhas e chaves fora do código; e cópias de segurança criptografadas. Nenhum sistema é 100% seguro: se
houver um incidente relevante, avisaremos os afetados e a ANPD.

#### 9. Cookies
Usamos apenas um cookie necessário para manter você logado. Não usamos cookies de publicidade.

#### 10. Mudanças
Podemos atualizar esta política; a data no topo indica a versão. Mudanças importantes serão avisadas no app.

</div>""", unsafe_allow_html=True)
