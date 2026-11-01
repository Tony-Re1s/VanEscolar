"""Planos, preços e promoções do Pequenos a Bordo (cobrança por nº de vans).

Os planos e as configurações ficam no banco (tabelas config_planos e config) e se ajustam na tela
Administração → Promoções. Os valores abaixo são só o padrão (usados se o banco ainda não tiver nada).

Não existe plano grátis: conta nova ganha degustação; quando a assinatura/degustação vence, o acesso é bloqueado
até o pagamento (nada é apagado).

Regra de preço: entre cupom, campanha, Passageiro VIP e plano anual vale o MELHOR preço para o cliente
(os descontos não se somam). Preço combinado pelo admin passa por cima de tudo. Meses grátis da indicação
são crédito à parte.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

PADRAO = {
    "basico": dict(nome="Básico", preco=24.90, preco_vip=19.90, anual_desconto=17.0, vans=1, alunos=None,
                   destaque="Motorista autônomo", cobranca_auto=False,
                   itens=["1 van", "Alunos ilimitados", "Contrato digital com assinatura", "Financeiro e painel"]),
    "pro": dict(nome="Pro", preco=54.90, preco_vip=29.90, anual_desconto=17.0, vans=3, alunos=None,
                destaque="Mais escolhido", cobranca_auto=True,
                itens=["Até 3 vans", "Motoristas contratados", "Financeiro por van", "Tudo do Básico"]),
    "frota": dict(nome="Frota", preco=99.90, preco_vip=79.90, anual_desconto=17.0, vans=None, alunos=None,
                  destaque="Empresas maiores", cobranca_auto=True,
                  itens=["Vans ilimitadas", "Motoristas ilimitados", "Suporte prioritário", "Tudo do Pro"]),
}
ORDEM = ["basico", "pro", "frota"]      # só o padrão; os planos de verdade vêm do banco (catalogo())

CONFIG_PADRAO = {
    "vip": {"ativo": True, "vagas": 200, "ate": None},
    "indicacao": {"ativo": True, "meta": 10, "premio_meses": 2, "plano_degustacao": "pro", "dias_degustacao": 30},
    "degustacao": {"ativo": True, "plano": "pro", "dias": 30},
    "comissao": {"ativo": True, "meta": 100, "pct": 10, "ate": "2027-12-31"},
    "laboratorio": {},
    "divulgacao": {"textos": [
        {"titulo": "Convite curto (WhatsApp)",
         "texto": "Oi! 🚐 Conhece o Pequenos a Bordo? Rota, chamada, mensalidades e contrato da van escolar, tudo no "
                  "celular. Os primeiros assinantes viram *Passageiro VIP* e pagam menos para sempre — restam só "
                  "*{vagas} vagas*. Entre pelo meu link e ganhe {dias} dias grátis: {link}"},
        {"titulo": "Grupo de transportadores",
         "texto": "Pessoal da van escolar 👋 Estou usando o Pequenos a Bordo para organizar a rota, avisar os pais no "
                  "WhatsApp e controlar as mensalidades. Quem assinar agora entra como Passageiro VIP: Básico por "
                  "{vip_basico} e Pro por {vip_pro} por mês, preço travado para sempre. Faltam {vagas} vagas! "
                  "Teste {dias} dias grátis: {link} (código {codigo})"},
        {"titulo": "Status / story",
         "texto": "🚐 Van escolar organizada no celular: rota, chamada, mensalidades e contrato. Últimas {vagas} vagas "
                  "VIP com preço travado para sempre 👉 {link}"},
    ]},
}

# Como o plano foi liberado
TIPOS = {"pago": "Pago", "teste": "Degustação", "cortesia": "Exclusivo"}
DIAS_TESTE = [7, 15, 30]
PERIODOS = {"mensal": "Mensal", "anual": "Anual"}
ORIGENS = {"cupom": "Cupom", "campanha": "Campanha", "vip": "Passageiro VIP", "anual": "Anual",
           "combinado": "Preço combinado"}
TIPOS_CUPOM = {"pct": "% de desconto", "valor": "R$ de desconto", "dias": "Dias grátis"}


# ---------------------------------------------------------------- leitura do banco

def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _int(v):
    f = _num(v)
    return None if f is None else int(f)


def catalogo() -> dict:
    """Planos com preços e limites atuais (do banco; se não der, o padrão)."""
    try:
        from core import db
        df = db.consultar("select * from config_planos order by ordem, plano")
    except Exception:  # noqa: BLE001
        return {k: dict(v) for k, v in PADRAO.items()}
    if df.empty:
        return {k: dict(v) for k, v in PADRAO.items()}
    out = {}
    for r in df.to_dict("records"):
        out[r["plano"]] = dict(nome=r["nome"], preco=_num(r["preco"]) or 0.0, preco_vip=_num(r["preco_vip"]),
                               anual_desconto=_num(r["anual_desconto"]) or 0.0, vans=_int(r["vans"]),
                               alunos=_int(r["alunos"]), destaque=r["destaque"] or "",
                               itens=list(r["itens"] or []), cobranca_auto=bool(r.get("cobranca_auto")))
    return out


def config(chave: str) -> dict:
    base = dict(CONFIG_PADRAO.get(chave, {}))
    try:
        from core import db
        r = db.um("select valor from config where chave = :c", c=chave)
        if r and isinstance(r["valor"], dict):
            base.update(r["valor"])
    except Exception:  # noqa: BLE001
        pass
    return base


# ---------------------------------------------------------------- plano em vigor e limites

def plano_da_empresa(empresa: dict, hoje: date, cat: dict | None = None) -> str | None:
    """Plano em vigor, ou None se a empresa está sem plano (venceu, nunca assinou ou o plano foi excluído) —
    nesse caso o acesso fica bloqueado até pagar."""
    p = (empresa or {}).get("plano")
    ate = (empresa or {}).get("plano_ate")
    if not p or p not in (cat or catalogo()):
        return None
    if ate and ate < hoje:
        return None
    return p


def liberada(empresa: dict, hoje: date, cat: dict | None = None) -> bool:
    """Empresa ativa e com plano em vigor (pago, degustação ou cortesia)."""
    return bool(empresa) and bool(empresa.get("ativo", True)) and plano_da_empresa(empresa, hoje, cat) is not None


def tipo_da_empresa(empresa: dict) -> str:
    t = (empresa or {}).get("plano_tipo") or "pago"
    return t if t in TIPOS else "pago"


def limite(plano: str | None, recurso: str, cat: dict | None = None):
    cat = cat or catalogo()
    return cat[plano][recurso] if plano in cat else None


def cabe(plano: str, recurso: str, atual: int, novos: int = 1, cat: dict | None = None) -> bool:
    lim = limite(plano, recurso, cat)
    return lim is None or atual + novos <= lim


def brl(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def preco_txt(p: dict) -> str:
    return "R$ 0" if not p["preco"] else brl(p["preco"])


# ---------------------------------------------------------------- motor de preço

@dataclass
class Preco:
    plano: str
    periodo: str = "mensal"
    base: float = 0.0               # preço cheio por mês
    final: float = 0.0              # o que o cliente paga por mês
    origem: str | None = None       # cupom | campanha | vip | anual | combinado | None
    rotulo: str = ""
    duracao_meses: int | None = None   # por quantos meses vale o preço promocional (None = sempre)
    cupom: dict | None = None
    campanha: dict | None = None
    vip_novo: bool = False          # entra agora como Passageiro VIP
    opcoes: list = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(self.final * (12 if self.periodo == "anual" else 1), 2)

    @property
    def tem_desconto(self) -> bool:
        return self.final < self.base - 0.004


def vip_livres(cfg_vip: dict, usadas: int, hoje: date) -> int:
    if not cfg_vip.get("ativo"):
        return 0
    ate = cfg_vip.get("ate")
    if ate and str(ate) < hoje.isoformat():
        return 0
    return max(0, int(cfg_vip.get("vagas") or 0) - int(usadas))


def campanha_ativa(campanhas: list[dict], plano: str, hoje: date) -> dict | None:
    """A campanha em vigor para o plano (se houver mais de uma, a de menor preço)."""
    vigentes = [c for c in campanhas or [] if c.get("ativo") and c["plano"] == plano
                and c["inicio"] <= hoje <= c["fim"]]
    return min(vigentes, key=lambda c: float(c["preco"])) if vigentes else None


def cupom_vale_para(cupom: dict | None, plano: str) -> bool:
    if not cupom:
        return False
    planos = cupom.get("planos")
    return not planos or plano in planos


def calcular(empresa: dict | None, plano: str, hoje: date, periodo: str = "mensal", cupom: dict | None = None,
             cat: dict | None = None, campanhas: list[dict] | None = None, cfg_vip: dict | None = None,
             vip_usadas: int = 0) -> Preco:
    """Preço que esta empresa pagaria neste plano/período, com a melhor promoção disponível."""
    cat = cat or catalogo()
    p = cat[plano]
    base = float(p["preco"] or 0)
    res = Preco(plano=plano, periodo=periodo, base=base, final=base)
    if base <= 0:
        res.final = 0.0
        return res
    emp = empresa or {}

    combinado = _num(emp.get("preco_combinado"))
    if combinado is not None and combinado > 0:
        res.final, res.origem, res.rotulo = round(combinado, 2), "combinado", "Preço combinado"
        return res

    # candidatas: (valor por mês, prioridade no empate, origem, rótulo, duração, extra)
    cands = []
    pv = _num(p.get("preco_vip"))
    if pv is not None and pv < base:
        if emp.get("vip"):
            cands.append((pv, 0, "vip", "Passageiro VIP", None, {}))
        elif vip_livres(cfg_vip if cfg_vip is not None else config("vip"), vip_usadas, hoje) > 0:
            cands.append((pv, 0, "vip", "Passageiro VIP", None, {"vip_novo": True}))
    camp = campanha_ativa(campanhas or [], plano, hoje)
    if camp:
        cands.append((float(camp["preco"]), 1, "campanha", camp["nome"], _int(camp.get("duracao_meses")),
                      {"campanha": camp}))
    if cupom and cupom.get("tipo") in ("pct", "valor") and cupom_vale_para(cupom, plano):
        v = float(cupom["valor"])
        valor = base * (1 - v / 100) if cupom["tipo"] == "pct" else base - v
        rot = f"Cupom {cupom['codigo']} (" + (f"-{v:g}%" if cupom["tipo"] == "pct" else f"-{brl(v)}") + ")"
        cands.append((max(0.0, valor), 2, "cupom", rot, _int(cupom.get("duracao_meses")), {"cupom": cupom}))
    if periodo == "anual" and float(p.get("anual_desconto") or 0) > 0:
        d = float(p["anual_desconto"])
        cands.append((base * (1 - d / 100), 3, "anual", f"Anual (-{d:g}%)", None, {}))

    res.opcoes = [(round(c[0], 2), c[2], c[3]) for c in cands]
    if not cands:
        return res
    melhor = min(cands, key=lambda c: (round(c[0], 2), c[1]))
    if round(melhor[0], 2) >= base:
        return res
    res.final, res.origem, res.rotulo, res.duracao_meses = round(melhor[0], 2), melhor[2], melhor[3], melhor[4]
    extra = melhor[5]
    res.cupom = extra.get("cupom")
    res.campanha = extra.get("campanha")
    res.vip_novo = bool(extra.get("vip_novo"))
    return res


def preco_regular(empresa: dict, plano: str, cat: dict | None = None) -> float:
    """Preço "de tabela" do plano para esta empresa (sem cupom/campanha): VIP se for VIP; anual com desconto."""
    cat = cat or catalogo()
    if plano not in cat:
        return 0.0
    p = cat[plano]
    pv = _num(p.get("preco_vip"))
    if empresa.get("vip") and pv is not None:
        return pv
    if (empresa.get("periodo") or "mensal") == "anual" and p.get("anual_desconto"):
        return round(float(p["preco"]) * (1 - float(p["anual_desconto"]) / 100), 2)
    return float(p["preco"])


def preco_vigente(empresa: dict, hoje: date, cat: dict | None = None) -> float:
    """Quanto a empresa paga hoje por mês (0 se sem plano, degustação, cortesia ou vencido)."""
    cat = cat or catalogo()
    plano = plano_da_empresa(empresa, hoje, cat)
    if plano is None or tipo_da_empresa(empresa) != "pago":
        return 0.0
    combinado = _num(empresa.get("preco_combinado"))
    if combinado is not None and combinado > 0:
        return combinado
    pm = _num(empresa.get("preco_mensal"))
    ate = empresa.get("desconto_ate")
    if pm is not None and (not ate or ate >= hoje):
        return pm
    return preco_regular(empresa, plano, cat)


def tem_cobranca_auto(empresa: dict, hoje: date, cat: dict | None = None) -> bool:
    """O plano em vigor libera a cobrança automática dos pais pelo Asaas?"""
    cat = cat or catalogo()
    p = plano_da_empresa(empresa, hoje, cat)
    return bool(p and cat[p].get("cobranca_auto"))


# ---------------------------------------------------------------- laboratório (recursos só para Exclusivo)
RECURSOS = {"gps": "Localização ao vivo da van", "cobranca_pais": "Cobrança dos pais pelo Asaas",
            "envio_contrato": "Enviar o contrato assinado por WhatsApp/e-mail"}


def texto_divulgacao(modelo: str, valores: dict) -> str:
    """Troca {link}, {vagas}… pelos valores; marcador desconhecido fica como está (não quebra o texto)."""
    class _D(dict):
        def __missing__(self, k):
            return "{" + k + "}"
    try:
        return str(modelo).format_map(_D(valores))
    except (ValueError, IndexError):
        return str(modelo)


def eh_exclusivo(empresa: dict, hoje: date, cat: dict | None = None) -> bool:
    return bool(empresa) and tipo_da_empresa(empresa) == "cortesia" and liberada(empresa, hoje, cat)


def liberado(empresa: dict | None, chave: str, hoje: date, admin: bool = False) -> bool:
    """Recurso liberado para esta empresa? No laboratório ('exclusivo') só Exclusivo (e admin) usa."""
    modo = (config("laboratorio") or {}).get(chave, "todos")
    if modo != "exclusivo" or admin:
        return True
    return eh_exclusivo(empresa or {}, hoje)
