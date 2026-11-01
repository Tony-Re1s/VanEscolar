"""Mensagens de WhatsApp da rota, com o apelido de quem dirige ("o tio Jô está a caminho para buscar a Helena").

Ida  = a van vai buscar a criança em casa e levar para a escola.
Volta = a van sai da escola e leva a criança para casa.
"""


def quem(apelido: str | None) -> str:
    """'Tio Jô' → 'o tio Jô'; 'Tia Rose' → 'a tia Rose'; 'Marcos' → 'Marcos'; vazio → 'a van'."""
    a = " ".join((apelido or "").split())
    if not a:
        return "a van"
    p = a.split(" ", 1)
    primeiro = p[0].lower()
    resto = p[1] if len(p) > 1 else ""
    if primeiro in ("tio", "tia"):
        return ("o " if primeiro == "tio" else "a ") + primeiro + (" " + resto if resto else "")
    return a


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def saudacao(hora: int) -> str:
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"


def _mapa(link: str | None) -> str:
    return f" Acompanhe a van ao vivo: {link}" if link else ""


def saindo(trecho: str, crianca: str, apelido: str | None, hora: int, link: str | None = None,
           parada: int | None = None, avisar_falta: bool = False) -> str:
    """Rota começou: ida → indo buscar; volta → saiu da escola levando para casa."""
    q = quem(apelido)
    if trecho == "ida":
        msg = f"{saudacao(hora)}! 🚐 {_cap(q)} está a caminho para buscar {crianca}."
        if parada:
            msg += f" {crianca} é a parada nº {parada} da rota."
        msg += " Pode deixar tudo pronto, por favor."
        if avisar_falta:
            msg += " Se não for hoje, avise pelo app Turminha a Bordo."
    else:
        msg = f"{saudacao(hora)}! 🚐 {_cap(q)} saiu da escola e está levando {crianca} para casa."
    return msg + _mapa(link)


def chegando(trecho: str, crianca: str, apelido: str | None, hora: int, link: str | None = None) -> str:
    """Perto da casa: ida → chegando para buscar; volta → chegando em casa."""
    q = quem(apelido)
    if trecho == "ida":
        msg = f"{saudacao(hora)}! 🚐 {_cap(q)} está chegando para buscar {crianca}. Já pode descer, por favor!"
    else:
        msg = f"{saudacao(hora)}! 🚐 {crianca} está chegando em casa com {q}!"
    return msg + _mapa(link)
