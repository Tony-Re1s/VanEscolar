"""Backup diário (roda no GitHub Actions — ver .github/workflows/backup.yml).

Variáveis de ambiente:
  NEON_URL       conexão do banco principal (obrigatória)
  BACKUP_SENHA   senha que criptografa o arquivo (obrigatória)
  RESERVA_URL    se existir, o banco reserva recebe uma cópia completa (opcional)
  SAIDA          pasta do arquivo (padrão: backups)

Rodar à mão:  NEON_URL=... BACKUP_SENHA=... python scripts/backup.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import backup  # noqa: E402


def main() -> None:
    url, senha = os.environ.get("NEON_URL"), os.environ.get("BACKUP_SENHA")
    if not url or not senha:
        sys.exit("Defina NEON_URL e BACKUP_SENHA.")
    dados = backup.exportar(backup.motor(url))
    total = backup.contagem(dados)
    pasta = Path(os.environ.get("SAIDA", "backups"))
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / backup.nome_arquivo()
    arq.write_bytes(backup.cifrar(dados, senha))
    print(f"Backup: {arq} ({arq.stat().st_size // 1024} KB) — " + ", ".join(f"{t}={n}" for t, n in total.items()))

    reserva = os.environ.get("RESERVA_URL")
    if reserva:
        backup.restaurar(backup.motor(reserva), dados)
        print("Banco reserva atualizado.")
    else:
        print("RESERVA_URL não definida: banco reserva não atualizado.")


if __name__ == "__main__":
    main()
