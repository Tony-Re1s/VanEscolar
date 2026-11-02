"""Grava os vídeos de "Aprenda a usar" direto do app (celular, conta de demonstração com dados fictícios).

Um navegador automático abre o app local, mostra uma legenda no topo e uma bolinha onde o dedo toca, e faz o
passo a passo de verdade. Quando a tela do app mudar, é só rodar de novo: os vídeos se refazem sozinhos.

Uso (com o app local rodando em :8501 e um banco de teste):
    python marketing/tutoriais/gravar.py            # todos
    python marketing/tutoriais/gravar.py aluno rota # só esses
Saída: static/tutoriais/<nome>.mp4 (720 px de largura, sem áudio).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "static" / "tutoriais"
TMP = Path("/tmp/tutoriais")
BASE = "http://localhost:8501"
W, H = 390, 844

# legenda no topo + bolinha do toque (injetado em toda página)
OVERLAY = """
(() => {
  const css = `#tut-cap{position:fixed;left:12px;right:12px;top:10px;z-index:2147483647;background:#16324F;color:#fff;
    font:700 17px/1.3 Nunito,system-ui,sans-serif;padding:12px 16px;border-radius:16px;box-shadow:0 8px 24px rgba(0,0,0,.25);
    opacity:0;transition:opacity .25s;text-align:center}
    #tut-cap.on{opacity:1}
    .tut-dot{position:fixed;z-index:2147483647;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;
    background:rgba(20,184,176,.35);border:3px solid #14B8B0;pointer-events:none;animation:tutp .6s ease-out forwards}
    @keyframes tutp{0%{transform:scale(.4);opacity:1}100%{transform:scale(1.25);opacity:0}}`;
  const add = () => {
    if (document.getElementById('tut-cap')) return;
    const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s);
    const c = document.createElement('div'); c.id = 'tut-cap'; document.body.appendChild(c);
  };
  window.__tutCap = (t) => { add(); const c = document.getElementById('tut-cap');
    if (!t) { c.classList.remove('on'); return; } c.textContent = t; c.classList.add('on'); };
  window.__tutTap = (x, y) => { add(); const d = document.createElement('div'); d.className = 'tut-dot';
    d.style.left = x + 'px'; d.style.top = y + 'px'; document.body.appendChild(d); setTimeout(() => d.remove(), 700); };
})();
"""


class Roteiro:
    def __init__(self, pg):
        self.pg = pg
        self.m = pg.locator("[data-testid=stMain]")

    def cap(self, texto: str | None, espera: float = 1.6):
        self.pg.evaluate("t => window.__tutCap(t)", texto)
        self.pg.wait_for_timeout(int(espera * 1000))

    def tocar(self, loc, clicar: bool = True, espera: float = 1.2):
        loc.scroll_into_view_if_needed()
        b = loc.bounding_box()
        if b:
            self.pg.evaluate("([x, y]) => window.__tutTap(x, y)", [b["x"] + b["width"] / 2, b["y"] + b["height"] / 2])
        self.pg.wait_for_timeout(350)
        if clicar:
            loc.click()
        self.pg.wait_for_timeout(int(espera * 1000))

    def digitar(self, loc, texto: str, espera: float = .5):
        self.tocar(loc, espera=.2)
        loc.press_sequentially(texto, delay=55)
        self.pg.wait_for_timeout(int(espera * 1000))

    def botao(self, nome: str):
        return self.m.get_by_role("button", name=nome).first

    def campo(self, nome: str):
        return self.m.get_by_role("textbox", name=nome).first


def _sql(q: str) -> str:
    return subprocess.run(["psql", "-h", "/var/lib/pgtest", "-U", "postgres", "van", "-Atc", q],
                          capture_output=True, text=True).stdout.strip()


EMP = "(select id from condutores where usuario_id=(select id from usuarios where email='condutor@teste.com'))"


# ---------------------------------------------------------------- roteiros
def aluno(r: Roteiro):
    r.pg.goto(f"{BASE}/alunos"); r.pg.wait_for_timeout(6000)
    r.cap("Cadastrar um aluno leva menos de 1 minuto", 2.2)
    r.cap("1. Toque em Novo aluno"); r.tocar(r.botao("Novo aluno"), espera=2)
    r.cap("2. Nome e endereço de embarque")
    r.digitar(r.campo("Nome do aluno *"), "Lucas Andrade")
    r.digitar(r.campo("Endereço de embarque"), "Rua das Palmeiras, 45")
    r.tocar(r.botao("Continuar"), espera=2)
    r.cap("3. Quem é o responsável e o WhatsApp")
    r.digitar(r.campo("Nome do responsável"), "Paula Andrade")
    r.digitar(r.campo("WhatsApp"), "11 98888-1234")
    r.tocar(r.botao("Continuar"), espera=2)
    r.cap("4. Escola, turno e van (dá para criar a escola aqui)", 2.4)
    r.tocar(r.botao("Continuar"), espera=2)
    r.cap("5. Valor da mensalidade e o dia do vencimento")
    v = r.m.get_by_role("spinbutton", name="Mensalidade (R$)").first
    r.tocar(v, espera=.2); v.fill(""); v.press_sequentially("380", delay=80)
    r.pg.wait_for_timeout(700)
    r.tocar(r.botao("Cadastrar aluno"), espera=2.5)
    r.cap("Pronto! A ficha do aluno abre sozinha ✅", 3)


def limpar_aluno():
    _sql(f"delete from passageiro_responsavel where passageiro_id in (select id from passageiros where condutor_id={EMP} and nome='Lucas Andrade')")
    _sql(f"delete from responsaveis where condutor_id={EMP} and nome='Paula Andrade'")
    _sql(f"delete from passageiros where condutor_id={EMP} and nome='Lucas Andrade'")


def rota(r: Roteiro):
    r.pg.goto(f"{BASE}/chamada"); r.pg.wait_for_timeout(6000)
    r.cap("A rota do dia, direto do celular", 2.2)
    r.cap("1. Toque em Iniciar rota"); r.tocar(r.m.get_by_role("button", name="Iniciar rota").first, espera=2.5)
    r.cap("2. Avise os pais que você está a caminho (abre o WhatsApp com a mensagem pronta)", 2.6)
    zap = r.m.locator("[class*='st-key-zap_ini_'] a").first
    if zap.count():
        r.tocar(zap, clicar=False, espera=1.8)
    r.cap("3. Em cada parada: Embarcou (ou Entregue) ou Faltou", 1.2)
    for _ in range(2):
        emb = r.m.get_by_role("button", name="Embarcou").or_(r.m.get_by_role("button", name="Entregue")).first
        if emb.count():
            r.tocar(emb, espera=2.4)
    r.cap("Os pais acompanham tudo pelo app 👨‍👩‍👧", 2.6)


def limpar_rota():
    _sql(f"delete from chamadas where condutor_id={EMP} and data = current_date")
    _sql(f"delete from rotas_iniciadas where data = current_date and van_id in (select id from vans where condutor_id={EMP})")


def cobranca(r: Roteiro):
    r.pg.goto(f"{BASE}/mensalidades"); r.pg.wait_for_timeout(6000)
    r.cap("Mensalidades: quem pagou e quem falta", 2.2)
    r.cap("1. Toque em Cobrar: o WhatsApp abre com a mensagem e o seu Pix", 2.6)
    cob = r.m.get_by_role("link", name="Cobrar").first
    if cob.count():
        r.tocar(cob, clicar=False, espera=1.2)
    r.cap("2. Recebeu? Toque em Receber e confirme")
    rec = r.m.get_by_role("button", name="Receber").first
    r.tocar(rec, espera=1.5)
    r.tocar(r.pg.locator("[data-testid=stPopoverBody]").get_by_role("button", name="Confirmar").first, espera=2.5)
    r.cap("Pronto! Já entra no Financeiro ✅", 2.6)


def limpar_cobranca():
    _sql(f"update mensalidades set pago_em=null, valor_pago=null, forma=null where condutor_id={EMP} and pago_em = current_date")


def despesa(r: Roteiro):
    r.pg.goto(f"{BASE}/financeiro"); r.pg.wait_for_timeout(6000)
    r.cap("Lançar uma despesa em 10 segundos", 2.2)
    r.cap("1. Toque em Lançar despesa ou receita")
    r.tocar(r.botao("Lançar despesa ou receita"), espera=2)
    d = r.pg.locator("[role=dialog]")
    r.cap("2. Escolha a categoria e o valor")
    v = d.get_by_role("spinbutton", name="Valor (R$)")
    r.tocar(v, espera=.2); v.fill(""); v.press_sequentially("180", delay=80)
    r.pg.wait_for_timeout(600)
    r.digitar(d.get_by_role("textbox", name="Descrição (opcional)"), "Abastecimento posto Shell")
    r.cap("Ainda não pagou? Desligue “Já foi paga” e vira conta a pagar", 2.6)
    r.tocar(d.get_by_role("button", name="Lançar"), espera=2.5)
    r.cap("Pronto! O lucro do mês já é atualizado ✅", 2.6)


def limpar_despesa():
    _sql(f"delete from lancamentos where condutor_id={EMP} and descricao='Abastecimento posto Shell'")


ROTEIROS = {"aluno": (aluno, limpar_aluno), "rota": (rota, limpar_rota), "cobranca": (cobranca, limpar_cobranca),
            "despesa": (despesa, limpar_despesa)}


def gravar(nome: str):
    fazer, limpar = ROTEIROS[nome]
    limpar()
    TMP.mkdir(parents=True, exist_ok=True)
    SAIDA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2, is_mobile=True, has_touch=True,
                            record_video_dir=str(TMP), record_video_size={"width": W, "height": H})
        ctx.add_init_script(OVERLAY)
        t0 = time.time()
        pg = ctx.new_page()
        r = Roteiro(pg)
        # aquecimento: abre o app e espera carregar (esse trecho é cortado do vídeo)
        pg.goto(BASE); pg.wait_for_timeout(7000)
        inicio = time.time() - t0
        try:
            fazer(r)
        finally:
            video = pg.video.path()
            ctx.close(); b.close()
            limpar()
    out = SAIDA / f"{nome}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{inicio + 6.5:.2f}", "-i", video,
                    "-vf", "scale=720:-2:flags=lanczos,fps=30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(out)], check=True)
    print("ok", out, f"{out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(ROTEIROS)):
        gravar(n)
