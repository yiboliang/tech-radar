#!/usr/bin/env python3
"""抓取 GitHub 热门仓库，输出 docs/trending.json / trending.js。

两个榜单:
  new_stars  — 近7天创建、star 最多的新项目
  ai_active  — 近3天有更新的 AI/LLM 高星项目

环境变量 GITHUB_TOKEN 可选（GitHub Actions 自带，提升限额）。
依赖: pip install requests
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "docs"

API = "https://api.github.com/search/repositories"
HEADERS = {"Accept": "application/vnd.github+json",
           "User-Agent": "tech-radar-bot"}
if os.environ.get("GITHUB_TOKEN"):
    HEADERS["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]

now = datetime.now(timezone.utc)
d7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
d3 = (now - timedelta(days=3)).strftime("%Y-%m-%d")


def search(q, per_page=25):
    try:
        r = requests.get(API, headers=HEADERS, timeout=30,
                         params={"q": q, "sort": "stars", "order": "desc",
                                 "per_page": per_page})
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception as e:
        print(f"[warn] search failed: {q} ({e})")
        return []


def simplify(items):
    out = []
    for it in items:
        out.append({
            "name": it["full_name"],
            "url": it["html_url"],
            "desc": (it.get("description") or "")[:200],
            "stars": it["stargazers_count"],
            "lang": it.get("language") or "",
            "created": it.get("created_at", ""),
            "pushed": it.get("pushed_at", ""),
        })
    return out


data = {
    "updated": now.isoformat(),
    "new_stars": simplify(search(f"created:>{d7} stars:>50")),
    "ai_active": simplify(search(
        f"pushed:>{d3} stars:>2000 topic:llm")) or simplify(search(
        f"pushed:>{d3} stars:>2000 llm OR agent in:name,description")),
}

OUT_DIR.mkdir(parents=True, exist_ok=True)
payload = json.dumps(data, ensure_ascii=False, indent=1)
(OUT_DIR / "trending.json").write_text(payload, encoding="utf-8")
(OUT_DIR / "trending.js").write_text(
    "window.RADAR_TRENDING = " + payload + ";", encoding="utf-8")
print(f"OK: new_stars={len(data['new_stars'])} ai_active={len(data['ai_active'])}")
