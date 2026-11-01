"""Planos do Pequenos a Bordo (cobrança por nº de vans).

Preços e limites ficam aqui — mude à vontade. `None` = ilimitado.
O plano de cada empresa fica em `condutores.plano` (+ `plano_ate`, vencimento da assinatura paga).
Até o pagamento automático (Asaas) entrar, o admin libera o plano na tela Empresas.
"""
from __future__ import annotations

from datetime import date

PLANOS = {
    "gratis": dict(nome="Grátis", preco=0.0, vans=1, alunos=10,
                   destaque="Para conhecer",
                   itens=["1 van", "Até 10 alunos", "Rota, chamada e mensalidades", "Área dos pais"]),
    "basico": dict(nome="Básico", preco=29.90, vans=1, alunos=None,
                   destaque="Motorista autônomo",
                   itens=["1 van", "Alunos ilimitados", "Contrato digital com assinatura", "Financeiro e painel"]),
    "pro": dict(nome="Pro", preco=59.90, vans=3, alunos=None,
                destaque="Mais escolhido",
                itens=["Até 3 vans", "Motoristas contratados", "Financeiro por van", "Tudo do Básico"]),
    "frota": dict(nome="Frota", preco=99.90, vans=None, alunos=None,
                  destaque="Empresas maiores",
                  itens=["Vans ilimitadas", "Motoristas ilimitados", "Suporte prioritário", "Tudo do Pro"]),
}
ORDEM = ["gratis", "basico", "pro", "frota"]

# Como o plano foi liberado
TIPOS = {"pago": "Pago", "teste": "Degustação", "cortesia": "Cortesia"}
DIAS_TESTE = [7, 15, 30]


def plano_da_empresa(empresa: dict, hoje: date) -> str:
    """Plano em vigor: o contratado, ou Grátis se a assinatura venceu."""
    p = (empresa or {}).get("plano") or "gratis"
    ate = (empresa or {}).get("plano_ate")
    if p != "gratis" and ate and ate < hoje:
        return "gratis"
    return p if p in PLANOS else "gratis"


def tipo_da_empresa(empresa: dict) -> str:
    t = (empresa or {}).get("plano_tipo") or "pago"
    return t if t in TIPOS else "pago"


def limite(plano: str, recurso: str):
    return PLANOS[plano][recurso]


def cabe(plano: str, recurso: str, atual: int, novos: int = 1) -> bool:
    lim = limite(plano, recurso)
    return lim is None or atual + novos <= lim


def preco_txt(p: dict) -> str:
    if not p["preco"]:
        return "R$ 0"
    return "R$ " + f"{p['preco']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
