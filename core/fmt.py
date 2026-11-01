"""Datas, dinheiro e rótulos."""
from __future__ import annotations

import calendar
import re
import urllib.parse
from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DIAS_SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

TURNOS = {"manha": "Manhã", "tarde": "Tarde", "integral": "Integral", "noite": "Noite"}
FORMAS = ["Pix", "Dinheiro", "Transferência", "Cartão", "Boleto"]
CAT_DESPESA = ["Combustível", "Manutenção", "Pneus", "Seguro", "IPVA / licenciamento", "Vistoria / alvará",
               "Monitora / ajudante", "Lavagem", "Pedágio / estacionamento", "Parcela do veículo",
               "Celular / internet", "Impostos (MEI)", "Outros"]
CAT_RECEITA = ["Passeio / excursão", "Viagem extra", "Taxa de matrícula", "Outros"]


def hoje() -> date:
    return datetime.now(TZ).date()


def agora() -> datetime:
    return datetime.now(TZ)


def brl(v) -> str:
    if v is None:
        return "—"
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(d) -> str:
    if d is None or (isinstance(d, float)):
        return "—"
    return d.strftime("%d/%m/%Y")


def mes_label(d: date, curto=False) -> str:
    return f"{(MESES_CURTOS if curto else MESES)[d.month - 1]}/{d.year}"


def inicio_mes(d: date) -> date:
    return d.replace(day=1)


def somar_meses(d: date, n: int) -> date:
    m = d.month - 1 + n
    a, m = d.year + m // 12, m % 12 + 1
    return date(a, m, min(d.day, calendar.monthrange(a, m)[1]))


def vencimento(competencia: date, dia: int) -> date:
    ult = calendar.monthrange(competencia.year, competencia.month)[1]
    return competencia.replace(day=min(int(dia), ult))


def idade(nasc) -> int | None:
    if not nasc:
        return None
    h = hoje()
    return h.year - nasc.year - ((h.month, h.day) < (nasc.month, nasc.day))


def so_digitos(t) -> str:
    return re.sub(r"\D", "", t if isinstance(t, str) else "")


def link_whats(telefone: str | None, msg: str) -> str | None:
    """wa.me com DDI 55 se vier só DDD+número."""
    d = so_digitos(telefone)
    if len(d) < 10:
        return None
    if not d.startswith("55") or len(d) <= 11:
        d = "55" + d
    return f"https://wa.me/{d}?text={urllib.parse.quote(msg)}"


def link_email(email: str | None, assunto: str, corpo: str) -> str | None:
    """mailto: — abre o e-mail do próprio gestor (Gmail/Outlook do celular) com a mensagem pronta."""
    email = (email or "").strip()
    if "@" not in email:
        return None
    return (f"mailto:{urllib.parse.quote(email)}?subject={urllib.parse.quote(assunto)}"
            f"&body={urllib.parse.quote(corpo)}")


def link_maps_rota(enderecos: list[str], destino: str | None = None) -> str | None:
    """Rota no Google Maps passando pelos endereços na ordem (até 9 paradas + destino)."""
    pontos = [e for e in enderecos if e]
    if destino:
        pontos.append(destino)
    if not pontos:
        return None
    q = urllib.parse.quote
    dest = pontos[-1]
    meio = pontos[:-1][:9]
    url = f"https://www.google.com/maps/dir/?api=1&destination={q(dest)}&travelmode=driving"
    if meio:
        url += "&waypoints=" + q("|".join(meio))
    return url
