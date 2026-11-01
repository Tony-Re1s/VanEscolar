"""Estúdio do Instagram @turminha_abordo — gera as artes (PNG) e os Reels (MP4) a partir da pauta, no padrão visual único.

Uso:
    python marketing/instagram/estudio.py 003          # gera o post 003 da pauta em marketing/instagram/saida/003/
    python marketing/instagram/estudio.py proximo      # gera o próximo post "pendente" da pauta
    python marketing/instagram/estudio.py 003 --amostra  # Reels: só alguns quadros (para conferir rápido)

Padrão visual: fonte Nunito, gradiente Tiffany (#14B8B0 → #5BB8F0), azul-marinho #16324F, destaque amarelo #FFC928,
rodapé com o ícone + "Turminha a Bordo" + @turminha_abordo. Feed 1080x1350 (4:5); Reels e Story 1080x1920 (9:16).
No texto da pauta, *assim* vira o marca-texto amarelo e uma quebra de linha é "\\n".
Sem fotos de crianças reais e sem personagens de terceiros — só tipografia, ícones, emojis e telas do app.
"""
from __future__ import annotations

import base64
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
A = D / "assets"
PAUTA = D / "pauta.json"
SAIDA = D / "saida"
FPS = 30


def b64(p: Path, mime="image/png") -> str:
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


FONTES = "".join(
    f"@font-face{{font-family:Nunito;font-weight:{w};src:url({b64(A / 'fontes' / f'nunito-latin-{w}-normal.woff2', 'font/woff2')})}}"
    for w in (600, 700, 800, 900))
ICONE = (A / "perfil.svg").read_text().replace("<svg ", '<svg width="100%" height="100%" ')

CSS = FONTES + """
:root{--tif:#14B8B0;--tif2:#0A9C97;--navy:#16324F;--am:#FFC928;--creme:#F4FBFB;--verde:#1E9E5A;--verm:#E5484D;--azul:#2F7DE1}
*{box-sizing:border-box;margin:0;padding:0}
body{width:var(--w);height:var(--h);font-family:Nunito,sans-serif;color:var(--navy);overflow:hidden;position:relative}
.grad{background:linear-gradient(150deg,#14B8B0 0%,#3DB6D8 55%,#5BB8F0 100%);color:#fff}
.claro{background:var(--creme)}
.navy{background:var(--navy);color:#fff}
.amarelo{background:var(--am);color:var(--navy)}
.pad{position:absolute;inset:0;padding:120px 96px 150px}
.h1{font-weight:900;font-size:98px;line-height:1.02;letter-spacing:-1.5px}
.h2{font-weight:900;font-size:74px;line-height:1.05;letter-spacing:-1px}
.h3{font-weight:800;font-size:46px;line-height:1.18}
.txt{font-weight:700;font-size:38px;line-height:1.38}
.mark{background:linear-gradient(transparent 12%,var(--am) 12%,var(--am) 88%,transparent 88%);color:var(--navy);padding:0 12px;
      border-radius:10px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.amarelo .mark{background:linear-gradient(transparent 12%,#fff 12%,#fff 88%,transparent 88%)}
.pill{display:inline-block;align-self:flex-start;font-weight:800;font-size:30px;padding:12px 28px;border-radius:999px;background:rgba(255,255,255,.22);color:#fff}
.claro .pill{background:#DDF3F2;color:var(--tif2)}
.navy .pill{background:rgba(255,201,40,.18);color:var(--am)}
.amarelo .pill{background:rgba(22,50,79,.12);color:var(--navy)}
.rodape{position:absolute;left:96px;right:96px;bottom:56px;display:flex;align-items:center;justify-content:space-between;font-weight:800;font-size:28px}
.marca{display:flex;align-items:center;gap:16px}
.marca .ic{width:56px;height:56px;border-radius:16px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,.12)}
.pag{position:absolute;top:56px;right:96px;font-weight:900;font-size:28px;padding:8px 22px;border-radius:999px;background:rgba(22,50,79,.10)}
.grad .pag,.navy .pag{background:rgba(255,255,255,.22)}
.arrasta{position:absolute;right:96px;bottom:150px;font-weight:900;font-size:30px}
.item{display:flex;gap:26px;align-items:center;margin:30px 0}
.item .b{flex:0 0 72px;height:72px;border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:36px;font-weight:900}
.item .h3{font-size:48px}
.claro .item .b{background:#DDF3F2;color:var(--tif2)}
.grad .item .b,.navy .item .b{background:#fff;color:var(--verde)}
.amarelo .item .b{background:var(--navy);color:var(--am)}
.item .b.nao{background:#FFE4E5 !important;color:var(--verm) !important}
.cartao{background:#fff;color:var(--navy);border-radius:36px;box-shadow:0 18px 50px rgba(22,50,79,.14);padding:40px 44px}
.cta{display:inline-block;background:var(--am);color:var(--navy);font-weight:900;font-size:42px;padding:26px 54px;border-radius:999px;
     box-shadow:0 14px 30px rgba(255,201,40,.45)}
.amarelo .cta{background:var(--navy);color:#fff;box-shadow:none}
.numero{font-weight:900;font-size:300px;line-height:.9;letter-spacing:-8px}
.emoji{font-size:150px;line-height:1}
.bolha{position:absolute;border-radius:50%;opacity:.16;background:#fff}
.claro .bolha{background:var(--tif);opacity:.08}
.amarelo .bolha{background:#fff;opacity:.35}
.navy .bolha{opacity:.06}
.fone{position:absolute;border-radius:64px;background:var(--navy);padding:18px;box-shadow:0 40px 80px rgba(22,50,79,.35)}
.fone .tela{border-radius:48px;overflow:hidden;background:var(--creme);position:relative}
.fone .tela img{display:block;width:100%}
.fone .notch{position:absolute;top:14px;left:50%;transform:translateX(-50%);width:130px;height:30px;border-radius:20px;background:var(--navy);z-index:2}
.enquete{background:#fff;color:var(--navy);border-radius:40px;padding:44px;box-shadow:0 20px 50px rgba(0,0,0,.18);text-align:center}
.enquete .op{margin-top:24px;border:4px solid #E3ECEC;border-radius:24px;padding:22px;font-weight:900;font-size:44px}
"""


def fmt(t: str | None) -> str:
    """Texto da pauta -> HTML: escapa, *destaque* vira marca-texto, \\n vira quebra."""
    t = html.escape(t or "")
    t = re.sub(r"\*(.+?)\*", r"<span class='mark'>\1</span>", t)
    return t.replace("\n", "<br>")


def rodape(bottom=56) -> str:
    return (f"<div class='rodape' style='bottom:{bottom}px'><div class='marca'><div class='ic'>{ICONE}</div>Turminha a Bordo</div>"
            "<div>@turminha_abordo</div></div>")


def bolhas() -> str:
    return ("<div class='bolha' style='width:520px;height:520px;right:-180px;top:-160px'></div>"
            "<div class='bolha' style='width:300px;height:300px;left:-120px;bottom:200px'></div>")


def pagina(corpo: str, fundo: str, w=1080, h=1350) -> str:
    return f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body class='{fundo}' style='--w:{w}px;--h:{h}px'>{corpo}</body></html>"


def tela(nome: str, x: int, y: int, w: int = 420, h: int | None = None, topo: int = 0, rot: float = 0) -> str:
    alt = f"height:{h}px;" if h else ""
    return (f"<div class='fone' style='left:{x}px;top:{y}px;width:{w}px;transform:rotate({rot}deg)'><div class='notch'></div>"
            f"<div class='tela' style='{alt}'><img src='{b64(A / 'telas' / (nome + '.png'))}' style='margin-top:-{topo}px'></div></div>")


# ---------------------------------------------------------------- modelos de slide (feed 4:5)
def slide(s: dict, i: int, n: int) -> str:
    m = s.get("modelo", "texto")
    fundo = s.get("fundo") or ("grad" if m in ("capa", "cta") else "claro")
    pag = f"<div class='pag'>{i}/{n}</div>" if n > 1 else ""
    selo = f"<div class='pill'>{fmt(s['selo'])}</div>" if s.get("selo") else ""
    arrasta = "<div class='arrasta'>arrasta →</div>" if (m == "capa" and n > 1) else ""
    if m == "capa":
        emoji = f"<div class='emoji' style='margin-top:40px'>{s['emoji']}</div>" if s.get("emoji") else ""
        corpo = f"""<div class='pad'>{selo}{emoji}
          <div class='h1' style='margin-top:{40 if emoji else 60}px'>{fmt(s.get('titulo'))}</div>
          <div class='txt' style='margin-top:44px;max-width:820px;opacity:.95'>{fmt(s.get('texto'))}</div>{arrasta}</div>"""
    elif m == "lista":
        marca = s.get("icone", "✓")
        itens = "".join(
            f"<div class='item'><div class='b{' nao' if marca == '✕' else ''}'>{(k + 1) if marca == '1' else marca}</div>"
            f"<div class='h3'>{fmt(t)}</div></div>" for k, t in enumerate(s.get("itens") or []))
        corpo = f"""<div class='pad'>{selo}<div class='h2' style='margin-top:{30 if selo else 0}px'>{fmt(s.get('titulo'))}</div>
          <div style='margin-top:40px'>{itens}</div>
          <div class='txt' style='margin-top:20px;font-size:34px;opacity:.85'>{fmt(s.get('texto'))}</div></div>"""
    elif m == "numero":
        corpo = f"""<div class='pad'>{selo}<div class='numero' style='margin-top:60px'>{fmt(s.get('numero'))}</div>
          <div class='h2' style='margin-top:20px'>{fmt(s.get('titulo'))}</div>
          <div class='txt' style='margin-top:40px;max-width:860px'>{fmt(s.get('texto'))}</div></div>"""
    elif m == "tela":
        corpo = f"""<div class='pad'>{selo}<div class='h2' style='max-width:500px;margin-top:{30 if selo else 0}px;font-size:66px'>{fmt(s.get('titulo'))}</div>
          <div class='txt' style='margin-top:40px;max-width:460px;font-size:36px'>{fmt(s.get('texto'))}</div></div>
          {tela(s['tela'], 590, 230, w=410, h=s.get('altura'), topo=int(s.get('topo') or 0))}"""
    elif m == "citacao":
        corpo = f"""<div class='pad' style='display:flex;flex-direction:column;justify-content:center'>{selo}
          <div style='font-weight:900;font-size:220px;line-height:.6;opacity:.35;margin-top:60px'>“</div>
          <div class='h2' style='margin-top:10px'>{fmt(s.get('texto'))}</div>
          <div class='h3' style='margin-top:50px;opacity:.85'>{fmt(s.get('autor'))}</div></div>"""
    elif m == "cta":
        corpo = f"""<div class='pad' style='text-align:center;padding-top:190px'>
          <div style='width:210px;height:210px;margin:0 auto;border-radius:54px;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,.18)'>{ICONE}</div>
          <div class='h1' style='margin-top:60px;font-size:86px'>{fmt(s.get('titulo'))}</div>
          <div class='txt' style='margin-top:34px'>{fmt(s.get('texto'))}</div>
          <div style='margin-top:56px'><span class='cta'>{fmt(s.get('botao') or 'Salve e mande para outro pai 💛')}</span></div></div>"""
    else:  # texto
        emoji = f"<div class='emoji'>{s['emoji']}</div>" if s.get("emoji") else ""
        caixa = (f"<div class='cartao' style='margin-top:50px'><div class='txt'>{fmt(s.get('caixa'))}</div></div>"
                 if s.get("caixa") else "")
        corpo = f"""<div class='pad'>{selo}{emoji}<div class='h2' style='margin-top:{36 if (selo or emoji) else 0}px'>{fmt(s.get('titulo'))}</div>
          <div class='txt' style='margin-top:44px;max-width:880px'>{fmt(s.get('texto'))}</div>{caixa}</div>"""
    return pagina(bolhas() + pag + corpo + rodape(), fundo)


# ---------------------------------------------------------------- story (9:16)
def story(s: dict) -> str:
    fundo = s.get("fundo") or "grad"
    # sem botões de enquete desenhados (não seriam clicáveis): a pergunta convida a responder por DM
    enquete = (f"<div class='enquete' style='margin-top:80px'><div class='h3'>{fmt(s.get('pergunta'))}</div>"
               f"<div class='op' style='border:0;background:#F4FBFB'>Responde aqui por DM 💬</div></div>"
               if s.get("pergunta") else "")
    corpo = f"""{bolhas()}<div style='position:absolute;left:96px;right:96px;top:250px'>
      {f"<div class='pill'>{fmt(s['selo'])}</div>" if s.get('selo') else ''}
      {f"<div class='emoji' style='margin-top:40px'>{s['emoji']}</div>" if s.get('emoji') else ''}
      <div class='h1' style='margin-top:40px;font-size:96px'>{fmt(s.get('titulo'))}</div>
      <div class='txt' style='margin-top:36px;font-size:42px'>{fmt(s.get('texto'))}</div>{enquete}</div>{rodape(200)}"""
    return pagina(corpo, fundo, h=1920)


# ---------------------------------------------------------------- Reels (9:16): texto animado, cena a cena
REELS_HTML = """<html><head><meta charset='utf-8'><style>""" + CSS + """
body{width:1080px;height:1920px}
.cena{position:absolute;inset:0;display:none;overflow:hidden}
.bloco{position:absolute;left:90px;right:90px;top:520px}
.barra{position:absolute;left:90px;right:90px;top:120px;height:10px;border-radius:10px;background:rgba(255,255,255,.3);overflow:hidden}
.claro .barra,.amarelo .barra{background:rgba(22,50,79,.12)}
.barra i{display:block;height:100%;background:var(--am);border-radius:10px}
.amarelo .barra i,.claro .barra i{background:var(--navy)}
.lin{display:block;opacity:0}
</style></head><body>__CENAS__
<script>
const cl=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=cl(x);return 1-Math.pow(1-x,3)};
const back=x=>{x=cl(x);const c=1.7;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
function render(c,t,dur,total,ini){
  document.querySelectorAll('.cena').forEach(e=>e.style.display='none');
  const s=document.getElementById('c'+c); s.style.display='block';
  const bar=s.querySelector('.barra i'); if(bar) bar.style.width=(100*(ini+t)/total)+'%';
  const em=s.querySelector('.emoji'); if(em){const k=back(t/0.55); em.style.transform=`scale(${0.2+0.8*k}) rotate(${(1-cl(t/0.55))*-25}deg)`; em.style.opacity=cl(t/0.15);}
  s.querySelectorAll('.lin').forEach((l,i)=>{const k=ease((t-0.18-i*0.16)/0.45); l.style.opacity=k; l.style.transform=`translateY(${(1-k)*70}px)`;});
  const sub=s.querySelector('.sub'); if(sub){const k=ease((t-0.25-0.16*s.querySelectorAll('.lin').length)/0.5); sub.style.opacity=k; sub.style.transform=`translateY(${(1-k)*40}px)`;}
  const ic=s.querySelector('.icfinal'); if(ic){const k=back(t/0.7); ic.style.transform=`scale(${0.3+0.7*k})`;}
  const cta=s.querySelector('.cta'); if(cta){cta.style.transform=`scale(${1+0.05*Math.sin(t*5)*cl((t-0.9)/0.3)})`;}
}
</script></body></html>"""


def _cena_html(k: int, c: dict) -> str:
    fundo = c.get("fundo") or ("grad" if k % 2 else "navy")
    linhas = "".join(f"<span class='lin'>{fmt(x)}</span>" for x in (c.get("titulo") or "").split("\n"))
    emoji = f"<div class='emoji' style='margin-bottom:50px'>{c['emoji']}</div>" if c.get("emoji") else ""
    sub = f"<div class='txt sub' style='margin-top:50px;font-size:50px;opacity:0'>{fmt(c.get('sub'))}</div>" if c.get("sub") else ""
    return (f"<div class='cena {fundo}' id='c{k}'>{bolhas()}<div class='barra'><i></i></div>"
            f"<div class='bloco'>{emoji}<div class='h1' style='font-size:{c.get('tamanho') or 112}px'>{linhas}</div>{sub}</div>"
            f"{rodape(200)}</div>")


def _cena_final(k: int, fim: dict) -> str:
    return (f"<div class='cena grad' id='c{k}'>{bolhas()}<div style='position:absolute;left:90px;right:90px;top:430px;text-align:center'>"
            f"<div class='icfinal' style='width:280px;height:280px;margin:0 auto;border-radius:72px;overflow:hidden;"
            f"box-shadow:0 30px 60px rgba(0,0,0,.2)'>{ICONE}</div>"
            f"<div class='h1' style='margin-top:70px;font-size:104px'>{fmt(fim.get('titulo') or 'Turminha a Bordo')}</div>"
            f"<div class='txt' style='margin-top:36px;font-size:48px'>{fmt(fim.get('sub') or 'O app da van escolar')}</div>"
            f"<div style='margin-top:70px'><span class='cta' style='font-size:54px'>{fmt(fim.get('botao') or 'Siga @turminha_abordo')}</span></div>"
            f"</div>{rodape(200)}</div>")


def reels(post: dict, pasta: Path, amostra=False):
    from playwright.sync_api import sync_playwright
    cenas = post["cenas"]
    fim = post.get("fim") or {}
    roteiro = [(k + 1, float(c.get("dur") or 2.6)) for k, c in enumerate(cenas)] + [(len(cenas) + 1, float(fim.get("dur") or 3.0))]
    total = sum(d for _, d in roteiro)
    doc = REELS_HTML.replace("__CENAS__", "".join(_cena_html(k + 1, c) for k, c in enumerate(cenas))
                             + _cena_final(len(cenas) + 1, fim))
    arq = pasta / "_reels.html"
    arq.write_text(doc)
    quadros = pasta / "_quadros"
    shutil.rmtree(quadros, ignore_errors=True)
    quadros.mkdir()
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(arq.as_uri())
        pg.wait_for_timeout(800)
        n, ini = 0, 0.0
        for c, dur in roteiro:
            passos = [dur * 0.7] if amostra else [i / FPS for i in range(round(dur * FPS))]
            for t in passos:
                pg.evaluate(f"render({c},{t},{dur},{total},{ini})")
                pg.screenshot(path=str(quadros / f"{n:05d}.jpg"), type="jpeg", quality=92)
                n += 1
            ini += dur
        # capa: 1ª cena com o texto já na tela
        pg.evaluate(f"render(1,{min(roteiro[0][1] - 0.2, 1.6)},{roteiro[0][1]},{total},0)")
        pg.screenshot(path=str(pasta / "capa.jpg"), type="jpeg", quality=92)
        b.close()
    if amostra:
        return
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(quadros / "%05d.jpg"),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(pasta / "reels.mp4")], check=True)
    shutil.rmtree(quadros, ignore_errors=True)
    arq.unlink(missing_ok=True)


# ---------------------------------------------------------------- gerar um post
def legenda(post: dict) -> str:
    tags = " ".join("#" + h.lstrip("#") for h in (post.get("hashtags") or [])[:5])   # o Instagram aceita no máx. 5
    return (post.get("legenda") or "").strip() + ("\n\n" + tags if tags else "")


def gerar(post: dict, amostra=False) -> Path:
    from playwright.sync_api import sync_playwright
    pasta = SAIDA / post["id"]
    shutil.rmtree(pasta, ignore_errors=True)
    pasta.mkdir(parents=True)
    if post["formato"] == "reels":
        reels(post, pasta, amostra)
    else:
        slides = post.get("slides") or []
        with sync_playwright() as p:
            b = p.chromium.launch()
            for i, s in enumerate(slides, start=1):
                pg = b.new_page(viewport={"width": 1080, "height": 1350})
                pg.set_content(slide(s, i, len(slides)))
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(pasta / f"{i:02d}.png"))
                pg.close()
            b.close()
    if post.get("story"):
        from playwright.sync_api import sync_playwright as _s
        with _s() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1080, "height": 1920})
            pg.set_content(story(post["story"]))
            pg.wait_for_timeout(300)
            pg.screenshot(path=str(pasta / "story.png"))
            b.close()
    (pasta / "legenda.txt").write_text(legenda(post))
    return pasta


def carregar() -> list[dict]:
    return json.loads(PAUTA.read_text())


def proximo(pauta: list[dict]) -> dict | None:
    return next((p for p in pauta if p.get("status") == "pendente"), None)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pauta = carregar()
    alvo = proximo(pauta) if (not args or args[0] == "proximo") else next(p for p in pauta if p["id"] == args[0])
    if not alvo:
        print("Nenhum post pendente na pauta.")
        sys.exit(1)
    out = gerar(alvo, amostra="--amostra" in sys.argv)
    print(alvo["id"], alvo["formato"], "->", out)
    for f in sorted(out.iterdir()):
        print("  ", f.name)
