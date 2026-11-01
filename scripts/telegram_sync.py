"""Busca as respostas do suporte no Telegram (GitHub Actions, junto com o Asaas). Variáveis: NEON_URL, TELEGRAM_TOKEN."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import backup, suporte  # noqa: E402


def main():
    url, tok = os.environ.get("NEON_URL"), os.environ.get("TELEGRAM_TOKEN")
    if not url or not tok:
        print("NEON_URL/TELEGRAM_TOKEN não definidos — nada a fazer.")
        return
    r = suporte.sincronizar(backup.motor(url), suporte.Telegram(tok))
    print(f"{r['respostas']} resposta(s) do suporte" + (f" · erro: {r['erro']}" if r["erro"] else ""))


if __name__ == "__main__":
    main()
