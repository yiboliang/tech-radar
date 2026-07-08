#!/usr/bin/env python3
"""通过 Nitter 镜像 RSS 抓取 X (Twitter) 账号动态，输出 docs/x.json / x.js。

说明: Nitter 为第三方镜像，稳定性有限；脚本会在多个镜像间自动切换，
全部失败的账号会跳过（保留上次数据由前端容错）。
依赖: pip install feedparser requests
"""
import json
import html
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "keywords.json").read_text(encoding="utf-8"))
OUT_DIR = ROOT / "docs"

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"}
MAX_AGE = timedelta(days=3)
PER_ACCOUNT = 8

now = datetime.now(timezone.utc)
cutoff = now - MAX_AGE
instances = CONFIG.get("nitter_instances", ["nitter.net"])
good_instances = list(instances)  # 成功过的镜像优先


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_account(user):
    global good_instances
    for inst in list(good_instances):
        url = f"https://{inst}/{user}/rss"
        try:
            r = requests.get(url, headers=UA, timeout=15)
            if r.status_code != 200 or b"<rss" not in r.content[:2000]:
                raise ValueError(f"status={r.status_code}")
            feed = feedparser.parse(r.content)
            if not feed.entries:
                raise ValueError("empty feed")
            # 该镜像可用，移到列表最前
            good_instances.remove(inst)
            good_instances.insert(0, inst)
            out = []
            for e in feed.entries[:30]:
                t = e.get("published_parsed")
                ts = datetime(*t[:6], tzinfo=timezone.utc) if t else now
                if ts < cutoff:
                    continue
                text = clean(e.get("title", ""))
                if not text:
                    continue
                link = e.get("link", "")
                # 把 nitter 链接换回 x.com
                link = re.sub(r"https?://[^/]+/", "https://x.com/", link, count=1).split("#")[0]
                out.append({
                    "user": user,
                    "text": text[:400],
                    "link": link,
                    "time": ts.isoformat(),
                    "rt": text.startswith("RT by") or text.startswith("RT @"),
                })
                if len(out) >= PER_ACCOUNT:
                    break
            print(f"  @{user}: {len(out)} via {inst}")
            return out
        except Exception:
            continue
    print(f"  @{user}: all instances failed")
    return []


items = []
for user in CONFIG.get("x_accounts", []):
    items.extend(fetch_account(user))

items.sort(key=lambda x: x["time"], reverse=True)

data = {"updated": now.isoformat(),
        "accounts": CONFIG.get("x_accounts", []),
        "items": items}

OUT_DIR.mkdir(parents=True, exist_ok=True)
payload = json.dumps(data, ensure_ascii=False, indent=1)
(OUT_DIR / "x.json").write_text(payload, encoding="utf-8")
(OUT_DIR / "x.js").write_text("window.RADAR_X = " + payload + ";", encoding="utf-8")
print(f"OK: {len(items)} tweets")
