"""Gera worker.js: turminhaabordo.com.br — /app (página do atalho com nome e ícone) e o resto redireciona para o app."""
import base64
from pathlib import Path

D = Path(__file__).parent   # cloudflare/: icones e worker.js gerado
i180 = base64.b64encode((D / "icone-180.png").read_bytes()).decode()
i512 = base64.b64encode((D / "icone-512.png").read_bytes()).decode()

HTML = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Turminha a Bordo</title>
<meta name="apple-mobile-web-app-title" content="Turminha a Bordo">
<meta name="application-name" content="Turminha a Bordo">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#14B8B0">
<link rel="apple-touch-icon" href="/icone-180.png">
<link rel="icon" type="image/png" href="/icone-180.png">
<link rel="manifest" href="/manifest.json">
<script>
  var APP = "https://turminhaabordo.streamlit.app/";
  var atalho = window.navigator.standalone === true || window.matchMedia("(display-mode: standalone)").matches;
  if (atalho) { window.location.replace(APP); }
</script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#16324F;min-height:100vh;
       background:linear-gradient(160deg,#14B8B0 0%,#3DB6D8 55%,#5BB8F0 100%);display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#fff;border-radius:28px;max-width:420px;width:100%;padding:32px 26px;text-align:center;box-shadow:0 20px 50px rgba(10,40,60,.25)}
  .card img{width:96px;height:96px;border-radius:24px;box-shadow:0 8px 20px rgba(0,0,0,.15)}
  h1{font-size:26px;margin:18px 0 6px;font-weight:900}
  p.sub{color:#3E5468;font-size:16px;margin-bottom:22px}
  .passos{text-align:left;background:#F4FBFB;border-radius:18px;padding:16px 18px;font-size:15px;line-height:1.5;margin-bottom:22px}
  .passos b{color:#0A9C97}
  .passos .t{font-weight:800;margin-bottom:6px}
  .so{display:none}
  .btn{display:block;background:#FFC928;color:#16324F;font-weight:900;font-size:18px;text-decoration:none;padding:16px;border-radius:999px;
       box-shadow:0 10px 24px rgba(255,201,40,.45)}
  .rod{margin-top:16px;font-size:13px;color:#5E7385}
  .rod a{color:#0A9C97}
</style></head><body>
<div class="card">
  <img src="/icone-180.png" alt="">
  <h1>Turminha a Bordo</h1>
  <p class="sub">Coloque o app na tela inicial do seu celular — abre com um toque, como um aplicativo.</p>
  <div class="passos so" id="ios">
    <div class="t">No iPhone (Safari):</div>
    1. Toque em <b>Compartilhar</b> (o quadrado com a setinha ↑)<br>
    2. Escolha <b>Adicionar à Tela de Início</b><br>
    3. Toque em <b>Adicionar</b>
  </div>
  <div class="passos so" id="android">
    <div class="t">No Android (Chrome):</div>
    1. Toque nos <b>três pontinhos ⋮</b> lá em cima<br>
    2. Escolha <b>Adicionar à tela inicial</b> (ou <b>Instalar app</b>)<br>
    3. Confirme em <b>Adicionar</b>
  </div>
  <a class="btn" href="https://turminhaabordo.streamlit.app/">Abrir o app agora</a>
  <div class="rod">Dúvidas? <a href="mailto:contato@turminhaabordo.com.br">contato@turminhaabordo.com.br</a> ·
    <a href="https://www.instagram.com/turminha_abordo/">@turminha_abordo</a></div>
</div>
<script>
  var ua = navigator.userAgent || "";
  var ios = /iPhone|iPad|iPod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  document.getElementById(ios ? "ios" : "android").style.display = "block";
  if (!/Android/i.test(ua) && !ios) { document.getElementById("ios").style.display = "block"; }
</script>
</body></html>"""

MANIFEST = """{"name":"Turminha a Bordo","short_name":"Turminha","start_url":"/app","scope":"/","display":"standalone",
"background_color":"#14B8B0","theme_color":"#14B8B0","lang":"pt-BR",
"icons":[{"src":"/icone-180.png","sizes":"180x180","type":"image/png"},
{"src":"/icone-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]}"""

JS = f"""// Turminha a Bordo — turminhaabordo.com.br
// /app            -> página para colocar o app na tela inicial (nome e ícone certos no atalho)
// qualquer outro  -> redireciona para o app (mantém caminho e parâmetros)
const APP = "https://turminhaabordo.streamlit.app";
const HTML = {HTML!r};
const MANIFEST = {MANIFEST!r};
const I180 = "{i180}";
const I512 = "{i512}";

function png(b64) {{
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Response(bytes, {{ headers: {{ "content-type": "image/png", "cache-control": "public, max-age=86400" }} }});
}}

export default {{
  async fetch(request) {{
    const url = new URL(request.url);
    const p = url.pathname.replace(/\\/+$/, "") || "/";
    if (p === "/app") return new Response(HTML, {{ headers: {{ "content-type": "text/html; charset=utf-8", "cache-control": "no-cache" }} }});
    if (p === "/manifest.json") return new Response(MANIFEST, {{ headers: {{ "content-type": "application/manifest+json" }} }});
    if (p === "/icone-180.png" || p === "/apple-touch-icon.png" || p === "/apple-touch-icon-precomposed.png") return png(I180);
    if (p === "/icone-512.png") return png(I512);
    if (p === "/favicon.ico") return png(I180);
    return Response.redirect(APP + url.pathname + url.search, 301);
  }},
}};
"""
(D / "worker.js").write_text(JS)
print(len(JS))
