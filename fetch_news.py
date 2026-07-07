#!/usr/bin/env python3
"""抓取 Google News RSS + 行业 RSS，去重分类后输出 docs/data.json。

依赖: pip install feedparser requests
用法: python fetch_news.py
"""
import json
import re
import hashlib
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "keywords.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs" / "data.json"

UA = {"User-Agent": "Mozilla/5.0 (compatible; TechRadarBot/1.0)"}
TIMEOUT = 20


def fetch_feed(url):
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception as e:
        print(f"  [warn] fetch failed: {url} ({e})")
        return None


def entry_time(e):
    for key in ("published_parsed", "updated_parsed"):
        t = e.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def google_news_urls():
    urls = []
    gn = CONFIG.get("google_news", {})
    if not gn.get("enabled"):
        return urls
    for topic, cfg in CONFIG["topics"].items():
        for q in cfg.get("queries", []):
            for ed in gn.get("editions", []):
                # 中文版跑所有 query；英文版只跑含 ASCII 的 query
                if ed["hl"].startswith("en") and not re.search(r"[A-Za-z]", q):
                    continue
                url = (
                    "https://news.google.com/rss/search?q="
                    + quote(f"{q} when:3d")
                    + f"&hl={ed['hl']}&gl={ed['gl']}&ceid={quote(ed['ceid'])}"
                )
                urls.append((f"GoogleNews[{topic}]", url, topic))
    return urls


def match_topics(text):
    hits = []
    low = text.lower()
    for topic, cfg in CONFIG["topics"].items():
        for kw in cfg.get("match", []):
            if kw.lower() in low:
                hits.append(topic)
                break
    return hits


def main():
    max_age = timedelta(days=CONFIG.get("max_age_days", 3))
    now = datetime.now(timezone.utc)
    cutoff = now - max_age

    jobs = google_news_urls() + [
        (f["name"], f["url"], None) for f in CONFIG.get("extra_feeds", [])
    ]

    items = {}
    def work(job):
        name, url, topic = job
        feed = fetch_feed(url)
        if not feed:
            return []
        out = []
        for e in feed.entries[:60]:
            title = clean(e.get("title", ""))
            link = e.get("link", "")
            if not title or not link:
                continue
            t = entry_time(e)
            if t and t < cutoff:
                continue
            source = clean(getattr(e, "source", {}).get("title", "") if hasattr(e, "source") else "") or name
            summary = clean(e.get("summary", ""))[:300]
            topics = set(match_topics(title + " " + summary))
            if topic:
                topics.add(topic)
            if not topics:
                continue  # 与任何主题无关则丢弃
            out.append({
                "title": title,
                "link": link,
                "source": source,
                "published": (t or now).isoformat(),
                "summary": summary,
                "topics": sorted(topics),
            })
        return out

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(work, j) for j in jobs]
        for f in as_completed(futures):
            for it in f.result():
                # 标题归一化去重（Google News 标题常带 " - 来源"）
                norm = re.sub(r"\s*[-–—|]\s*[^-–—|]{2,30}$", "", it["title"]).lower()
                key = hashlib.md5(norm.encode()).hexdigest()
                if key in items:
                    items[key]["topics"] = sorted(set(items[key]["topics"]) | set(it["topics"]))
                else:
                    items[key] = it

    all_items = sorted(items.values(), key=lambda x: x["published"], reverse=True)

    # 每主题限量
    cap = CONFIG.get("max_items_per_topic", 40)
    counts = {t: 0 for t in CONFIG["topics"]}
    final = []
    for it in all_items:
        keep = False
        for t in it["topics"]:
            if counts.get(t, 0) < cap:
                counts[t] = counts.get(t, 0) + 1
                keep = True
        if keep:
            final.append(it)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "updated": now.isoformat(),
        "topics": list(CONFIG["topics"].keys()),
        "items": final,
    }, ensure_ascii=False, indent=1)
    OUT.write_text(payload, encoding="utf-8")
    # data.js: 供 file:// 直接打开 index.html 时回退加载
    (OUT.parent / "data.js").write_text("window.RADAR_DATA = " + payload + ";", encoding="utf-8")
    print(f"OK: {len(final)} items -> {OUT}")
    for t, c in counts.items():
        print(f"  {t}: {c}")


if __name__ == "__main__":
    main()
