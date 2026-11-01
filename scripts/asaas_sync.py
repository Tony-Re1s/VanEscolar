"""Sincroniza os pagamentos do Asaas e do Mercado Pago (GitHub Actions a cada 30 min — ver .github/workflows/asaas.yml).

Variáveis: NEON_URL, ASAAS_API_KEY, ASAAS_AMBIENTE (sandbox | producao), MP_ACCESS_TOKEN (Mercado Pago).
Cada gateway só roda se a credencial dele estiver definida.
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import asaas, backup, mercadopago  # noqa: E402


def _resumo(nome: str, r: dict):
    print(f"{nome}: {r['empresas']} assinatura(s) · {r['pagamentos_novos']} pagamento(s) novo(s) · "
          f"{r['valores_atualizados']} valor(es) atualizado(s)")
    # o registro do GitHub Actions pode ser público: sem nome de empresa, só o motivo
    for e in r["erros"]:
        print("ERRO:", e.split(": ", 1)[-1])


def main():
    url, chave, mp = os.environ.get("NEON_URL"), os.environ.get("ASAAS_API_KEY"), os.environ.get("MP_ACCESS_TOKEN")
    if not url or not (chave or mp):
        print("NEON_URL e ASAAS_API_KEY/MP_ACCESS_TOKEN não definidos — nada a fazer.")
        return
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    motor = backup.motor(url)
    if chave:
        api = asaas.Asaas(chave, os.environ.get("ASAAS_AMBIENTE") or "sandbox", os.environ.get("ASAAS_BASE_URL") or None)
        _resumo("Asaas", asaas.sincronizar(api, motor, hoje))
    if mp:
        try:
            _resumo("Mercado Pago", mercadopago.sincronizar(mercadopago.MercadoPago(mp), motor, hoje))
        except mercadopago.MPErro as e:
            print("ERRO Mercado Pago:", e)


if __name__ == "__main__":
    main()
