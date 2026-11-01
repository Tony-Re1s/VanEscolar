"""Sincroniza os pagamentos do Asaas (roda no GitHub Actions a cada 30 min — ver .github/workflows/asaas.yml).

Variáveis: NEON_URL, ASAAS_API_KEY, ASAAS_AMBIENTE (sandbox | producao).
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import asaas, backup  # noqa: E402


def main():
    url, chave = os.environ.get("NEON_URL"), os.environ.get("ASAAS_API_KEY")
    if not url or not chave:
        print("NEON_URL/ASAAS_API_KEY não definidos — nada a fazer.")
        return
    api = asaas.Asaas(chave, os.environ.get("ASAAS_AMBIENTE") or "sandbox", os.environ.get("ASAAS_BASE_URL") or None)
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    r = asaas.sincronizar(api, backup.motor(url), hoje)
    print(f"{r['empresas']} assinatura(s) · {r['pagamentos_novos']} pagamento(s) novo(s) · "
          f"{r['valores_atualizados']} valor(es) atualizado(s)")
    # o registro do GitHub Actions pode ser público: sem nome de empresa, só o motivo
    for e in r["erros"]:
        print("ERRO:", e.split(": ", 1)[-1])


if __name__ == "__main__":
    main()
