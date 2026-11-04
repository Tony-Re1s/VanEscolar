"""Publica o post do dia no Instagram @turminha_abordo pela API oficial do Instagram (Graph API da Meta).

Roda no GitHub Actions todo dia (.github/workflows/instagram.yml) — não depende do computador de ninguém ligado.

Fluxo:
  1. pega na pauta (marketing/instagram/pauta.json) o 1º post "pendente" com data_sugerida <= hoje (que ainda não saiu);
  2. gera as artes/Reels (estudio.py) e converte as imagens para JPEG (a API só aceita JPEG);
  3. sobe os arquivos para o branch `instagram-midia` (fora do main, para não mexer no app publicado)
     e usa o link do jsDelivr (espelho público do GitHub) como endereço das mídias;
  4. cria o container na API (imagem, carrossel ou Reels), espera processar e publica; depois publica o story;
  5. registra em `estado.json` (no mesmo branch): id, data, link do post — assim nunca publica o mesmo post 2 vezes.

Variáveis (Secrets do repositório):
  IG_TOKEN   token de acesso do Instagram (longa duração, 60 dias)
  NEON_URL   banco do app — o token renovado fica guardado na tabela config (chave "instagram"),
             porque o token muda a cada renovação e o Secret do GitHub não se atualiza sozinho.
Opções:  --seco  (gera e mostra o que faria, sem subir nem publicar)   --id 003 (publica um post específico)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

D = Path(__file__).resolve().parent
RAIZ = D.parent.parent
sys.path.insert(0, str(D))
import estudio  # noqa: E402

# Token de "usuário do sistema" do portfólio Turminha a Bordo (começa com EAA, não expira) → graph.facebook.com.
# Token de login do Instagram (começa com IG, 60 dias, renovável) → graph.instagram.com.
API = "https://graph.instagram.com/v23.0"
API_FB = "https://graph.facebook.com/v23.0"
IG_USER_ID = os.environ.get("IG_USER_ID") or "17841480781860954"     # @turminha_abordo
REPO = os.environ.get("GITHUB_REPOSITORY", "Tony-Re1s/VanEscolar")
BRANCH = "instagram-midia"
MIDIA = RAIZ / "_midia"          # worktree do branch de mídias (criado pelo workflow)
HOJE = datetime.now(ZoneInfo("America/Sao_Paulo")).date()


class IGErro(Exception):
    pass


# ---------------------------------------------------------------- HTTP
def _req(metodo: str, url: str, dados: dict | None = None) -> dict:
    corpo = urllib.parse.urlencode(dados).encode() if dados is not None else None
    req = urllib.request.Request(url, data=corpo, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
            msg = err.get("message") or str(e)
            # "Fatal" sozinho não diz nada — o motivo real vem em code/subcode/user_msg
            extra = [f"{k}={err[k]}" for k in ("code", "error_subcode", "error_user_title", "error_user_msg",
                                                "fbtrace_id") if err.get(k)]
            if extra:
                msg += " [" + "; ".join(str(x) for x in extra) + "]"
        except Exception:  # noqa: BLE001
            msg = str(e)
        raise IGErro(f"{metodo} {url.split('?')[0].replace(API, '')}: {msg}") from e


# ---------------------------------------------------------------- token (renova sozinho a cada 7 dias)
def _motor():
    url = os.environ.get("NEON_URL")
    if not url:
        return None
    sys.path.insert(0, str(RAIZ))
    from core.backup import motor      # mesma conexão usada pelo backup e pela sincronização do Asaas
    return motor(url)


def token() -> str:
    from sqlalchemy import text
    eng = _motor()
    salvo = None
    if eng is not None:
        with eng.begin() as s:
            r = s.execute(text("select valor from config where chave = 'instagram'")).first()
            salvo = r[0] if r and isinstance(r[0], dict) else None
    if (os.environ.get("IG_TOKEN") or "").startswith("EAA"):    # usuário do sistema: não expira, não renova
        global API
        API = API_FB
        return os.environ["IG_TOKEN"]
    tok = (salvo or {}).get("token") or os.environ.get("IG_TOKEN")
    if not tok:
        raise IGErro("Sem token do Instagram (Secret IG_TOKEN).")
    renovado = (salvo or {}).get("renovado_em")
    if eng is not None and (not renovado or datetime.fromisoformat(renovado).date() <= HOJE - timedelta(days=7)):
        try:
            novo = _req("GET", "https://graph.instagram.com/refresh_access_token?" +
                        urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": tok}))["access_token"]
            with eng.begin() as s:
                s.execute(text("""insert into config (chave, valor) values ('instagram', cast(:v as jsonb))
                                  on conflict (chave) do update set valor = excluded.valor"""),
                          dict(v=json.dumps({"token": novo, "renovado_em": HOJE.isoformat()})))
            tok = novo
            print("token renovado")
        except IGErro as e:          # token novo demais para renovar (< 24 h) etc. — segue com o atual
            print("aviso: não renovei o token:", e)
    return tok


# ---------------------------------------------------------------- API de publicação
def _criar(uid: str, tok: str, **campos) -> str:
    return _req("POST", f"{API}/{uid}/media", dict(campos, access_token=tok))["id"]


def _esperar(cid: str, tok: str, limite=600):
    t0 = time.time()
    while time.time() - t0 < limite:
        st = _req("GET", f"{API}/{cid}?fields=status_code,status&access_token={tok}")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise IGErro(f"processamento da mídia falhou: {st.get('status')}")
        time.sleep(8)
    raise IGErro("a mídia demorou demais para processar")


def _ja_publicado(uid: str, tok: str, cid: str) -> str | None:
    """Depois de um erro no media_publish: o post às vezes sai mesmo assim. Devolve o id se saiu."""
    try:
        if _req("GET", f"{API}/{cid}?fields=status_code&access_token={tok}").get("status_code") == "PUBLISHED":
            recentes = _req("GET", f"{API}/{uid}/media?fields=id,timestamp&limit=1&access_token={tok}").get("data", [])
            return recentes[0]["id"] if recentes else cid
    except IGErro:
        pass
    return None


def _publicar(uid: str, tok: str, cid: str, tentativas=4) -> str:
    """Publica o container. Erro genérico da Meta ("Fatal", "unexpected error"…) é passageiro:
    espera, confere se o post saiu mesmo assim (nunca duplica) e só então tenta de novo."""
    _esperar(cid, tok)
    for n in range(1, tentativas + 1):
        try:
            return _req("POST", f"{API}/{uid}/media_publish", {"creation_id": cid, "access_token": tok})["id"]
        except IGErro as e:
            print(f"aviso: publicação falhou (tentativa {n}/{tentativas}): {e}")
            time.sleep(45 * n)
            pid = _ja_publicado(uid, tok, cid)
            if pid:
                print("o post saiu mesmo com o erro — não vou publicar de novo")
                return pid
            if n == tentativas:
                raise


def _publicar_reels(uid: str, tok: str, urls: dict, legenda: str) -> str:
    """Reels: 1º com a capa personalizada; se a Meta recusar, um container novo sem capa (usa um quadro do vídeo).
    _publicar já confere se o anterior saiu antes de desistir, então não duplica."""
    base = dict(media_type="REELS", video_url=urls["reels"], caption=legenda, share_to_feed="true")
    if urls.get("capa"):
        try:
            return _publicar(uid, tok, _criar(uid, tok, **base, cover_url=urls["capa"]), tentativas=2)
        except IGErro as e:
            print("aviso: Reels com capa falhou — tentando sem a capa:", e)
    return _publicar(uid, tok, _criar(uid, tok, **base, thumb_offset="1000"), tentativas=2)


def publicar(post: dict, urls: dict, legenda: str, tok: str) -> dict:
    if tok.startswith("EAA"):
        uid = IG_USER_ID
        eu = _req("GET", f"{API}/{uid}?fields=username&access_token={tok}")
    else:
        eu = _req("GET", f"{API}/me?fields=user_id,username&access_token={tok}")
        uid = eu.get("user_id") or eu["id"]
    if post["formato"] == "reels":
        mid = _publicar_reels(uid, tok, urls, legenda)
    elif len(urls["imagens"]) == 1:
        cid = _criar(uid, tok, image_url=urls["imagens"][0], caption=legenda)
    else:
        filhos = [_criar(uid, tok, image_url=u, is_carousel_item="true") for u in urls["imagens"]]
        for f in filhos:
            _esperar(f, tok)
        cid = _criar(uid, tok, media_type="CAROUSEL", children=",".join(filhos), caption=legenda)
    if post["formato"] != "reels":
        mid = _publicar(uid, tok, cid)
    link = _req("GET", f"{API}/{mid}?fields=permalink&access_token={tok}").get("permalink")
    story = None
    if urls.get("story"):
        try:
            story = _publicar(uid, tok, _criar(uid, tok, media_type="STORIES", image_url=urls["story"]))
        except IGErro as e:        # o post do feed já saiu; story é bônus
            print("aviso: story não publicado:", e)
    return {"media_id": mid, "link": link, "story_id": story, "usuario": eu.get("username")}


# ---------------------------------------------------------------- mídias públicas (branch instagram-midia)
def _jpeg(png: Path) -> Path:
    from PIL import Image
    jpg = png.with_suffix(".jpg")
    Image.open(png).convert("RGB").save(jpg, quality=92, optimize=True)
    return jpg


def subir_midias(post: dict, pasta: Path) -> dict:
    """Copia para o worktree do branch de mídias, faz commit/push e devolve os links raw (fixos no commit)."""
    destino = MIDIA / "posts" / post["id"]
    destino.mkdir(parents=True, exist_ok=True)
    nomes = {"imagens": []}
    for f in sorted(pasta.iterdir()):
        if f.suffix == ".png" and f.stem != "story":
            j = _jpeg(f)
            (destino / j.name).write_bytes(j.read_bytes())
            nomes["imagens"].append(j.name)
        elif f.stem == "story" and f.suffix == ".png":
            j = _jpeg(f)
            (destino / "story.jpg").write_bytes(j.read_bytes())
            nomes["story"] = "story.jpg"
        elif f.name in ("reels.mp4", "capa.jpg", "legenda.txt"):
            (destino / f.name).write_bytes(f.read_bytes())
            if f.name == "reels.mp4":
                nomes["reels"] = f.name
            if f.name == "capa.jpg":
                nomes["capa"] = f.name
    sha = _git_commit(f"mídias do post {post['id']}")
    # jsDelivr (CDN que espelha o GitHub) entrega com o tipo certo (image/jpeg, video/mp4) — o Instagram baixa daqui
    base = f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/posts/{post['id']}/"
    urls = {"imagens": [base + n for n in nomes["imagens"]]}
    for k in ("story", "reels", "capa"):
        if nomes.get(k):
            urls[k] = base + nomes[k]
    for u in urls["imagens"] + [urls.get("reels")] + [urls.get("story")]:   # espera o link responder
        if u:
            for _ in range(20):
                try:
                    with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=20) as r:
                        if r.status == 200:
                            break
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(3)
    return urls


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(MIDIA), *args], check=True, capture_output=True, text=True).stdout.strip()


def _git_commit(msg: str) -> str:
    _git("add", "-A")
    if _git("status", "--porcelain"):
        _git("-c", "user.name=Turminha Bot", "-c", "user.email=contato@turminhaabordo.com.br", "commit", "-m", msg)
        _git("push", "origin", f"HEAD:{BRANCH}")
    return _git("rev-parse", "HEAD")


def estado() -> dict:
    arq = MIDIA / "estado.json"
    return json.loads(arq.read_text()) if arq.exists() else {"publicados": {}}


def salvar_estado(e: dict, msg: str):
    (MIDIA / "estado.json").write_text(json.dumps(e, ensure_ascii=False, indent=1))
    _git_commit(msg)


# ---------------------------------------------------------------- principal
def escolher(pauta: list[dict], feitos: dict, forcado: str | None) -> dict | None:
    if forcado:
        return next(p for p in pauta if p["id"] == forcado)
    for p in pauta:
        if p["id"] in feitos or p.get("status") == "pulado":
            continue
        if not p.get("data_sugerida") or datetime.fromisoformat(p["data_sugerida"]).date() <= HOJE:
            return p
    return None


def main():
    seco = "--seco" in sys.argv
    forcado = sys.argv[sys.argv.index("--id") + 1] if "--id" in sys.argv else None
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not 18 <= agora.hour < 23 and not forcado:
        # o agendador do GitHub atrasa horas; fora da janela da noite não publica (evita post de madrugada)
        print(f"Agendamento do GitHub chegou atrasado ({agora:%H:%M}) — fora da janela 18h–23h, não publico.")
        return
    e = estado() if MIDIA.exists() else {"publicados": {}}
    hoje_ja = [k for k, v in e["publicados"].items() if v.get("data") == HOJE.isoformat()]
    if hoje_ja and not forcado:
        print("Já saiu post hoje:", hoje_ja)
        return
    post = escolher(estudio.carregar(), e["publicados"], forcado)
    if not post:
        print("Nada para publicar hoje (pauta acabou ou próximos posts são para os próximos dias).")
        return
    print("post:", post["id"], post["formato"], "—", post["tema"])
    pasta = estudio.gerar(post)
    leg = estudio.legenda(post)
    if seco:
        print(leg)
        print(sorted(f.name for f in pasta.iterdir()))
        return
    urls = subir_midias(post, pasta)
    res = publicar(post, urls, leg, token())
    e["publicados"][post["id"]] = dict(res, data=HOJE.isoformat(), tema=post["tema"], formato=post["formato"])
    salvar_estado(e, f"publicado {post['id']}")
    print("PUBLICADO:", res.get("link"))


if __name__ == "__main__":
    try:
        main()
    except IGErro as err:
        print("ERRO:", err)
        sys.exit(1)
