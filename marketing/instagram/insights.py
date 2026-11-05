"""Relatório de desempenho do @turminha_abordo (GitHub Actions → "Instagram — insights", na mão).

Usa o mesmo token da publicação (publicar.token()). Imprime: seguidores, alcance/visitas/interações da conta nos
últimos dias e, por post, alcance, visualizações, curtidas, comentários, salvamentos e compartilhamentos.
Também grava o resultado em insights.json (artefato do workflow).
"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import publicar as P  # noqa: E402


def get(caminho: str, **q):
    q["access_token"] = TOK
    try:
        return P._req("GET", f"{P.API}/{caminho}?" + urllib.parse.urlencode(q))
    except P.IGErro as e:
        return {"erro": str(e)[:200]}


TOK = P.token()
UID = P.IG_USER_ID
out = {"gerado_em": datetime.now(timezone.utc).isoformat()}
out["conta"] = get(UID, fields="username,followers_count,follows_count,media_count")
fim = datetime.now(timezone.utc)
ini = fim - timedelta(days=int(os.environ.get("DIAS", "7")))
for m in ("reach", "profile_views", "accounts_engaged", "total_interactions", "follows_and_unfollows", "website_clicks",
          "views"):
    r = get(f"{UID}/insights", metric=m, period="day", metric_type="total_value",
            since=int(ini.timestamp()), until=int(fim.timestamp()))
    out[f"conta_{m}"] = r.get("data", r)
posts = get(f"{UID}/media", fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count",
            limit=30).get("data", [])
out["posts"] = []
for p in posts:
    ins = {}
    for m in ("reach", "views", "saved", "shares", "total_interactions", "profile_visits", "follows"):
        r = get(f"{p['id']}/insights", metric=m)
        if "data" in r and r["data"]:
            ins[m] = r["data"][0].get("values", [{}])[0].get("value", r["data"][0].get("total_value", {}).get("value"))
    out["posts"].append({"data": p["timestamp"][:10], "tipo": p.get("media_product_type") or p.get("media_type"),
                         "link": p["permalink"], "legenda": (p.get("caption") or "")[:60].replace("\n", " "),
                         "curtidas": p.get("like_count"), "comentarios": p.get("comments_count"), **ins})
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open("insights.json", "w"), ensure_ascii=False, indent=1)
