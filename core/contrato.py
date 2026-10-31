"""Contrato de transporte escolar: modelo, montagem com os dados, validação de CPF e PDF.

O texto das cláusulas vem de `condutores.contrato_clausulas` (o gestor pode editar);
vazio = CLAUSULAS_PADRAO (cláusulas 1 a 7 do contrato da JÔ Transporte).
A cláusula 8 (dados) e as assinaturas são montadas pelo app.
"""
from __future__ import annotations

import hashlib
import io
import json
import re

from core.fmt import TZ, data_br

CLAUSULAS_PADRAO = """CLÁUSULA 1ª – DO OBJETO
Prestação de serviço de transporte escolar, na modalidade ida e volta ou apenas ida ou apenas volta, durante o período letivo, conforme itinerário e horários previamente acordados.

CLÁUSULA 2ª – DO VALOR E DA FORMA DE PAGAMENTO
O presente contrato possui caráter anual, com pagamento parcelado em até 12 (doze) parcelas iguais, independentemente do início da prestação dos serviços ocorrer após o início do ano letivo. O valor acordado entre as partes será informado separadamente e aceito no ato da contratação, não sofrendo alterações em razão de início posterior.

CLÁUSULA 3ª – DAS FÉRIAS ESCOLARES
Os meses de janeiro, julho e dezembro são pagos normalmente, por se tratar de contrato anual com reserva de vaga e disponibilidade do serviço.

CLÁUSULA 4ª – DO CANCELAMENTO
O cancelamento poderá ser solicitado somente até o mês de outubro do ano vigente. Após esse período, as parcelas restantes deverão ser quitadas integralmente, independentemente da utilização do serviço.

CLÁUSULA 5ª – DA PONTUALIDADE E HORÁRIOS
O(a) aluno(a) deverá estar pronto(a) e no local combinado com, no mínimo, 10 (dez) minutos de antecedência ao horário estipulado. A CONTRATADA não se responsabiliza por atrasos decorrentes da ausência ou despreparo do(a) aluno(a). Não será realizada busca do(a) aluno(a) fora do horário regular da escola ou do horário previamente acordado.

CLÁUSULA 6ª – DA INADIMPLÊNCIA
O não pagamento de qualquer parcela na data de vencimento acarretará a suspensão imediata do serviço, independentemente de aviso prévio, até a completa regularização do débito. A permanência da inadimplência autoriza a CONTRATADA a adotar medidas de cobrança extrajudicial, conforme a legislação vigente, sem prejuízo da exigência do pagamento integral das parcelas contratadas.

CLÁUSULA 7ª – DA RESPONSABILIDADE POR DANOS
Eventuais danos causados ao veículo pelo(a) aluno(a), devidamente comprovados, serão de responsabilidade do(a) CONTRATANTE, que se compromete a arcar com os custos de reparo, respeitado o direito à informação e à ampla defesa, conforme o Código de Defesa do Consumidor."""

TITULO = "CONTRATO DE PRESTAÇÃO DE SERVIÇOS DE TRANSPORTE ESCOLAR"

# Condições do serviço — o gestor prepara por aluno
MODALIDADES = ["Ida e volta", "Somente ida", "Somente volta"]
# Dados do contratante — o responsável preenche e pode editar
CAMPOS_CONTRATANTE = [("responsavel", "Nome completo"), ("cpf", "CPF"), ("rg", "RG"),
                      ("nascimento", "Data de nascimento"), ("parentesco", "Parentesco com o(a) aluno(a)"),
                      ("telefone", "Telefone")]
CAMPOS_ENDERECO = [("cep", "CEP"), ("rua", "Rua / avenida"), ("numero", "Número"), ("complemento", "Complemento"),
                   ("bairro", "Bairro"), ("cidade", "Cidade"), ("uf", "UF")]


def preambulo(empresa: dict) -> str:
    nome = (empresa.get("razao_social") or empresa.get("nome") or "").strip()
    cnpj = (empresa.get("cnpj") or "").strip()
    doc = f", inscrita no CNPJ sob nº {cnpj}" if cnpj else ""
    return (f"Pelo presente instrumento particular, de um lado {nome.upper()}{doc}, doravante denominada "
            "CONTRATADA, e de outro lado o(a) responsável legal abaixo identificado(a), doravante denominado(a) "
            "CONTRATANTE, ajustam entre si o que segue, em conformidade com o Código de Defesa do Consumidor "
            "(Lei nº 8.078/90):")


def clausulas(empresa: dict) -> str:
    return (empresa.get("contrato_clausulas") or "").strip() or CLAUSULAS_PADRAO


def _brl(v) -> str:
    s = f"{float(v or 0):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _data(v) -> str:
    if not v:
        return ""
    if isinstance(v, str):
        return v if "/" in v else "/".join(reversed(v.split("-")))
    return v.strftime("%d/%m/%Y")


def servico_padrao(aluno: dict, ano: int) -> dict:
    """Condições sugeridas a partir do cadastro do aluno (o gestor ajusta antes de liberar)."""
    from datetime import date
    ida, volta = bool(aluno.get("faz_ida", True)), bool(aluno.get("faz_volta", True))
    modalidade = "Ida e volta" if ida and volta else "Somente ida" if ida else "Somente volta"
    ini = aluno.get("inicio")
    ini = ini if ini and getattr(ini, "year", 0) == ano else date(ano, 1, 1)
    fim = aluno.get("fim")
    fim = fim if fim and getattr(fim, "year", 0) == ano else date(ano, 12, 31)
    casa = ", ".join(x for x in (aluno.get("endereco"), aluno.get("bairro")) if x)
    escola = " – ".join(x for x in (aluno.get("escola"), aluno.get("escola_endereco")) if x)
    return dict(aluno=aluno.get("nome") or "", escola=aluno.get("escola") or "", turno=aluno.get("turno_txt") or "",
                modalidade=modalidade, horario_busca="", horario_entrega="", embarque=casa, desembarque=escola,
                inicio=ini.isoformat(), fim=fim.isoformat(), valor_parcela=float(aluno.get("mensalidade") or 0),
                parcelas=12, dia_vencimento=int(aluno.get("dia_venc") or 10))


def _numero(clausulas_txt: str) -> int:
    return len(re.findall(r"(?mi)^CL[ÁA]USULA", clausulas_txt))


def linhas_servico(sv: dict) -> list[str]:
    total = float(sv.get("valor_parcela") or 0) * int(sv.get("parcelas") or 0)
    horarios = " · ".join(x for x in (f"busca às {sv['horario_busca']}" if sv.get("horario_busca") else "",
                                      f"entrega às {sv['horario_entrega']}" if sv.get("horario_entrega") else "") if x)
    return [f"Aluno(a): {sv.get('aluno', '')}",
            f"Escola: {sv.get('escola', '')}",
            f"Turno: {sv.get('turno', '')}",
            f"Modalidade: {sv.get('modalidade', '')}",
            f"Horários: {horarios or 'conforme combinado'}",
            f"Endereço de embarque: {sv.get('embarque', '')}",
            f"Endereço de desembarque: {sv.get('desembarque', '')}",
            f"Vigência: de {_data(sv.get('inicio'))} a {_data(sv.get('fim'))}",
            f"Valor: {_brl(total)}, em {int(sv.get('parcelas') or 0)} parcelas de {_brl(sv.get('valor_parcela'))}, "
            f"com vencimento todo dia {int(sv.get('dia_vencimento') or 0)}"]


def endereco_txt(d: dict) -> str:
    rua = ", ".join(x for x in (d.get("rua"), d.get("numero"), d.get("complemento")) if x)
    cid = "/".join(x for x in (d.get("cidade"), d.get("uf")) if x)
    return " – ".join(x for x in (rua, d.get("bairro"), cid, f"CEP {d['cep']}" if d.get("cep") else "") if x)


def linhas_contratante(d: dict) -> list[str]:
    return [f"{rot}: {d.get(k) or ''}" for k, rot in CAMPOS_CONTRATANTE] + [f"Endereço: {endereco_txt(d)}"]


def montar_texto(empresa: dict, servico: dict, contratante: dict) -> str:
    """Contrato completo em texto (é o que fica congelado e gera o código de conferência)."""
    cl = clausulas(empresa)
    n = _numero(cl)
    linhas = [TITULO, "", preambulo(empresa), "", cl, "",
              f"CLÁUSULA {n + 1}ª – DAS CONDIÇÕES DO SERVIÇO", *linhas_servico(servico), "",
              f"CLÁUSULA {n + 2}ª – DOS DADOS DO CONTRATANTE", *linhas_contratante(contratante), "",
              f"Local e data: {contratante.get('local') or ''}, {contratante.get('data') or ''}"]
    return "\n".join(linhas)


def codigo(texto: str, dados: dict, email: str) -> str:
    base = texto + json.dumps(dados, sort_keys=True, ensure_ascii=False) + email
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16].upper()


def cpf_valido(cpf: str) -> bool:
    d = re.sub(r"\D", "", cpf or "")
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        s = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (s * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    d = re.sub(r"\D", "", cpf or "")
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else cpf


def _quando(ts) -> str:
    if ts is None:
        return ""
    return ts.astimezone(TZ).strftime("%d/%m/%Y às %H:%M")


def gerar_pdf(c: dict, empresa: dict) -> bytes:
    """PDF do contrato assinado (c = linha da tabela contratos)."""
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title=TITULO, author=empresa.get("razao_social") or empresa.get("nome"))
    tit = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=12.5, alignment=TA_CENTER, spaceAfter=14)
    corpo = ParagraphStyle("c", fontName="Helvetica", fontSize=9.6, leading=13, alignment=TA_JUSTIFY, spaceAfter=4)
    cab = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9.6, leading=13, spaceBefore=6, spaceAfter=1)
    peq = ParagraphStyle("p", fontName="Helvetica", fontSize=8.5, leading=11, textColor="#444444")

    texto = c["texto"]
    blocos = texto.split("\n")
    dado = ParagraphStyle("d", parent=corpo, spaceAfter=0, leading=13)
    out = [Paragraph(escape(TITULO), tit)]
    na_8 = False
    for linha in blocos[1:]:
        linha = linha.strip()
        if not linha:
            continue
        if linha.upper().startswith("CLÁUSULA") or linha.upper().startswith("CLAUSULA"):
            na_8 = any(k in linha.upper() for k in ("DAS CONDIÇÕES DO SERVIÇO", "DOS DADOS DO CONTRATANTE",
                                                      "DOS DADOS DO ALUNO"))
            out.append(Paragraph(escape(linha), cab))
        elif na_8 or linha.startswith("Local e data:"):
            rot, _, val = linha.partition(":")
            out.append(Paragraph(f"{escape(rot)}: <b>{escape(val.strip())}</b>", dado))
        else:
            out.append(Paragraph(escape(linha), corpo))

    out.append(Spacer(1, 14))
    ini_assin = len(out)
    out.append(Paragraph("<b>Assinatura eletrônica do(a) CONTRATANTE</b>", corpo))
    out.append(Paragraph(escape(f"{c['responsavel_nome']} — {c['responsavel_email']} — aceito em "
                                f"{_quando(c['responsavel_assinou_em'])}"), corpo))
    out.append(Spacer(1, 8))
    out.append(Paragraph("<b>Assinatura eletrônica da CONTRATADA</b>", corpo))
    if c.get("contratada_assinou_em"):
        out.append(Paragraph(escape(f"{empresa.get('razao_social') or empresa.get('nome')} — por "
                                    f"{c['contratada_por']} — em {_quando(c['contratada_assinou_em'])}"), corpo))
    else:
        out.append(Paragraph("Aguardando assinatura da contratada.", corpo))
    out.append(Spacer(1, 14))
    out.append(Paragraph(escape(
        f"Documento assinado eletronicamente no app Pequenos a Bordo, com identificação das partes por login "
        f"Google. Código de conferência: {c['codigo']}. Contrato {c['ano']}."), peq))
    from reportlab.platypus import KeepTogether
    out = out[:ini_assin - 1] + [KeepTogether(out[ini_assin - 1:])]   # assinaturas nunca ficam sozinhas na página
    doc.build(out)
    return buf.getvalue()
