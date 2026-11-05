"""Diagnóstico temporário do Reels (erro 2207085). Testa, em ordem, parando no 1º que publicar:
1) Story de vídeo  2) Reels sem legenda/capa/share_to_feed. Uso manual pelo workflow instagram-diag."""
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import estudio  # noqa: E402
import publicar as p  # noqa: E402

post = next(x for x in estudio.carregar() if x["id"] == sys.argv[1])
pasta = estudio.gerar(post)
arq = p._recodificar(pasta / "reels.mp4", "reels_sem.mp4", "sem")
tok = p.token()
uid = p.IG_USER_ID
# o token do login do Instagram (IG…), se ainda estiver guardado no banco, usa o outro caminho (graph.instagram.com)
from sqlalchemy import text  # noqa: E402
eng = p._motor()
with eng.begin() as s_:
    r_ = s_.execute(text("select valor from config where chave = 'instagram'")).first()
salvo = (r_[0] if r_ and isinstance(r_[0], dict) else {}) or {}
print("token guardado no banco:", (salvo.get("token") or "")[:3] or "nenhum", "renovado_em", salvo.get("renovado_em"))
if (salvo.get("token") or "").startswith("IG") and "--ig" in sys.argv:
    p.API = "https://graph.instagram.com/v23.0"
    tok = salvo["token"]
    eu = p._req("GET", f"{p.API}/me?fields=user_id,username&access_token={tok}")
    print("caminho graph.instagram.com:", eu)
    uid = eu.get("user_id") or eu["id"]
print("conta:", p._req("GET", f"{p.API}/{uid}?fields=username&access_token={tok}"))
try:
    print("limite:", p._req("GET", f"{p.API}/{uid}/content_publishing_limit?fields=config,quota_usage&access_token={tok}"))
except p.IGErro as e:
    print("limite: erro", e)
for nome, campos in [("story de vídeo", dict(media_type="STORIES"))]:
    print("== testando:", nome)
    try:
        r = p._req("POST", f"{p.API}/{uid}/media", dict(campos, upload_type="resumable", access_token=tok))
        p._subir_video(tok, r["uri"], arq)
        p._esperar(r["id"], tok)
        print("status:", p._req("GET", f"{p.API}/{r['id']}?fields=status_code,status&access_token={tok}"))
        mid = p._publicar(uid, tok, r["id"], tentativas=1)
        print("SAIU:", nome, mid)
        break
    except p.IGErro as e:
        print("FALHOU:", nome, e)
