"""Termos de Uso (públicos)."""
import streamlit as st

RESPONSAVEL = "José Anthony Reis Lopes"
CONTATO = "joseareislopes@gmail.com"
ATUALIZADO = "01/11/2026"

st.title("Termos de Uso")
st.caption(f"Pequenos a Bordo · atualizados em {ATUALIZADO}")

st.markdown(f"""<div class='ve-doc'>

#### 1. O serviço
O **Pequenos a Bordo** é um aplicativo para gestão de transporte escolar (rotas, chamada, mensalidades, contrato
digital, financeiro e área da família), oferecido por **{RESPONSAVEL}** ({CONTATO}). Ao entrar no app, você
concorda com estes Termos e com a Política de Privacidade.

#### 2. Contas e perfis
O acesso é feito com uma conta Google. O **gestor** cria a empresa e cadastra vans, motoristas, alunos e
responsáveis. **Motoristas** e **responsáveis** veem apenas o que o gestor liberou para eles. Você é responsável
pelo uso da sua conta.

#### 3. Responsabilidades do gestor
O gestor declara que: as informações cadastradas são verdadeiras; tem autorização dos pais ou responsáveis para
cadastrar os dados dos alunos; usa o app de acordo com a LGPD; e cumpre as exigências legais do transporte escolar
(licenças, vistorias, habilitação, seguro etc.). O app é uma ferramenta de organização e **não substitui** essas
obrigações.

#### 4. Contrato entre gestor e família
O contrato de transporte assinado no app é celebrado **entre o gestor e o responsável**. O Pequenos a Bordo apenas
fornece o meio para preencher, assinar eletronicamente e guardar o documento, e não é parte dele. O gestor é
responsável pelo conteúdo das cláusulas.

#### 5. Planos e pagamento
Os planos são pagos, por número de vans, com valores informados na página de Planos. Toda conta nova ganha um
período de degustação gratuita. Os planos são mensais ou anuais e podem ser cancelados a qualquer momento; o acesso
segue até o fim do período já pago. Quando a degustação ou a assinatura vence sem pagamento, o acesso ao app fica
**suspenso** para o gestor, seus motoristas e os responsáveis, **sem perda de dados**, e volta assim que o pagamento
é confirmado. Valores podem mudar com aviso prévio de 30 dias; quem já assina pode manter o preço contratado
conforme a oferta vigente.

#### 6. Uso adequado
Não é permitido usar o app para fins ilegais, cadastrar dados de terceiros sem autorização, tentar acessar dados de
outras empresas ou prejudicar o funcionamento do serviço. Contas que violarem estes Termos podem ser suspensas.

#### 7. Disponibilidade
Trabalhamos para manter o app no ar e fazemos cópias de segurança diárias, mas não garantimos funcionamento
ininterrupto. O app pode ficar fora do ar por manutenção ou por falhas de fornecedores (hospedagem, banco de dados,
Google). Mensagens de WhatsApp dependem do aplicativo do próprio usuário.

#### 8. Responsabilidade
Na medida permitida pela lei, o Pequenos a Bordo não responde por decisões tomadas com base nas informações
cadastradas pelos usuários, por falhas de terceiros ou por danos indiretos. Nada nestes Termos limita direitos
garantidos pelo Código de Defesa do Consumidor.

#### 9. Encerramento
O gestor pode encerrar a conta quando quiser, pedindo pelo contato acima; os dados seguem o prazo da Política de
Privacidade.

#### 10. Foro
Estes Termos seguem a lei brasileira. Fica eleito o foro da comarca de São Paulo/SP, sem prejuízo do foro do
domicílio do consumidor.

</div>""", unsafe_allow_html=True)
