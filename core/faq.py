"""Respostas prontas do "Fale conosco" (camada 1 do suporte: resolve as dúvidas comuns sem esperar ninguém).
Cada item: título do botão, resposta em passos e a tela do app que resolve (aberta por um atalho)."""

FAQ = [
    dict(titulo="Cadastrar aluno", pagina="telas/alunos.py", pagina_facil="telas/facil_alunos.py", texto="""
**Modo completo:** vá em **Alunos e responsáveis → Cadastrar / editar**, preencha o nome (o resto é opcional) e
salve. Depois, no próprio cadastro, adicione o **responsável** com o WhatsApp e o e-mail do Google dele.

**Modo fácil:** em **Alunos**, digite nome, WhatsApp do responsável, mensalidade e dia de vencimento e toque em
**Adicionar aluno**. Dá também para **colar uma lista** com vários de uma vez."""),
    dict(titulo="Convidar os pais", pagina="telas/alunos.py", texto="""
No cadastro do aluno, cada responsável tem os botões **Convidar no WhatsApp** e **Convidar por e-mail** — a
mensagem já vai pronta com o link do app. O responsável entra com o **e-mail do Google** que você cadastrou.

Em **Alunos e responsáveis → Lista → "Ainda não entraram no app"** você vê quem ainda não acessou e reenvia o
convite."""),
    dict(titulo="Enviar contrato", pagina="telas/alunos.py", texto="""
1. Preencha o **CNPJ e o nome da contratada** em **Minha empresa → Contrato**.
2. Em **Alunos e responsáveis → Contratos**, toque em **Liberar** (um a um ou todos de uma vez).
3. O responsável abre o app, confere, preenche os dados dele e **assina**. Depois você assina também.
4. Com o contrato assinado, mande o **PDF** pelos botões de WhatsApp ou e-mail. A assinatura eletrônica tem
   validade jurídica (Lei 14.063/2020)."""),
    dict(titulo="Iniciar rota e avisar os pais", pagina="telas/chamada.py", pagina_facil="telas/facil_rota.py", texto="""
Em **Rota e chamada** (ou **Rota**, no modo fácil), escolha **Ida** ou **Volta** e toque em **Iniciar rota**: os
pais já veem no app que a van saiu e aparece um botão de WhatsApp para cada família.

Em cada aluno: **Avisar** (manda "está chegando"), **Avisar + local** (com o link da van no mapa), **Na escola /
Entregue**, **Faltou** e **Como chegar** (abre o Google Maps até a casa)."""),
    dict(titulo="Localização ao vivo", pagina="telas/chamada.py", pagina_facil="telas/facil_rota.py", texto="""
Na tela da rota, toque em **Ligar localização ao vivo** e permita a localização no celular. A posição é enviada a
cada ~30 segundos **enquanto o app estiver aberto na tela** — se você abrir outro app (como o Maps), o envio pausa.

Os pais veem a van pelo botão **"Ver a van no mapa agora"** na área deles, ou pelo link que vai no **Avisar +
local**. Toque em **Parar localização** no fim da rota."""),
    dict(titulo="Mensalidades e baixa", pagina="telas/mensalidades.py", texto="""
As mensalidades são **geradas sozinhas** todo mês, com o valor e o vencimento de cada aluno. Em **Mensalidades**,
toque no aluno para **dar baixa** quando ele pagar (Pix, dinheiro…), ou mande a **cobrança no WhatsApp** com a sua
chave Pix (cadastre-a em **Minha empresa**)."""),
    dict(titulo="Cobrar pelo Asaas (Pix/boleto)", pagina="telas/meu_cadastro.py", texto="""
Nos planos com cobrança automática, conecte a sua conta **Asaas** em **Minha empresa → Receber as mensalidades
pelo Asaas** (cole a chave da API do seu Asaas). Depois, em **Mensalidades → Como cada aluno paga**, escolha por
aluno: **Manual**, **Pix/boleto todo mês** ou **Assinatura automática**. Quando o pai paga, a baixa é automática e
o dinheiro cai na **sua** conta Asaas."""),
    dict(titulo="Motorista e monitor(a)", pagina="telas/vans.py", texto="""
Em **Vans e motoristas**, abra a van e preencha o **e-mail do Google** do motorista (e, se tiver, do(a)
**monitor(a)**). Eles entram no app com esse e-mail e veem **só a rota e a chamada** da van — sem cadastros nem
financeiro. Use o botão **Convidar no WhatsApp** para mandar o acesso."""),
    dict(titulo="Avisos para os pais", pagina="telas/avisos.py", texto="""
Em **Avisos**, escreva o recado e escolha para quem: **todas as famílias**, **uma van** ou **um aluno** (ou para a
**equipe**). O aviso aparece no topo da área da família pelo tempo que você escolher."""),
    dict(titulo="Plano, pagamento e pausa", pagina="telas/meu_plano.py", texto="""
Em **Meu plano** você vê o plano atual, muda de plano, aplica cupom e paga (Pix, boleto ou cartão). Ao cancelar,
o plano vale até o fim do período pago. Se for só pelas férias, a **pausa de férias** mantém seus dados e seu
preço pagando bem menos."""),
]
