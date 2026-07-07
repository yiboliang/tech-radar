#!/usr/bin/env python3
"""读取 docs/data.json，生成过去24小时 HTML 日报并通过 Gmail SMTP 发送。

环境变量:
  SMTP_USER  Gmail 地址（发件人）
  SMTP_PASS  Gmail 应用专用密码 (https://myaccount.google.com/apppasswords)
用法: python send_email.py
"""
import json
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.header import Header
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / "keywords.json").read_text(encoding="utf-8"))
DATA = json.loads((ROOT / "docs" / "data.json").read_text(encoding="utf-8"))

email_cfg = CONFIG["email"]
window = timedelta(hours=email_cfg.get("hours_window", 24))
cutoff = datetime.now(timezone.utc) - window

recent = [it for it in DATA["items"]
          if datetime.fromisoformat(it["published"]) >= cutoff]

if not recent:
    print("过去24小时无新文章，跳过发送")
    sys.exit(0)

# 按主题分组（一篇文章只归入其第一个主题，避免重复）
groups = {t: [] for t in DATA["topics"]}
for it in recent:
    groups[it["topics"][0]].append(it)

today = datetime.now().strftime("%Y-%m-%d")
parts = [f"""<div style="font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:680px;margin:0 auto;color:#24292f">
<h2 style="border-bottom:2px solid #0969da;padding-bottom:8px">📡 行业日报 · {today}</h2>
<p style="color:#57606a;font-size:13px">共 {len(recent)} 条 · 过去 {email_cfg.get('hours_window',24)} 小时 · AI / 光互联 / 半导体</p>"""]

for topic, items in groups.items():
    if not items:
        continue
    parts.append(f'<h3 style="color:#0969da;margin:22px 0 8px">{topic}（{len(items)}）</h3>')
    for it in items[:15]:
        t = datetime.fromisoformat(it["published"]).strftime("%m-%d %H:%M")
        parts.append(
            f'<div style="margin-bottom:10px;padding:10px 12px;background:#f6f8fa;border-radius:8px">'
            f'<a href="{it["link"]}" style="color:#24292f;font-weight:600;text-decoration:none;font-size:14px">{it["title"]}</a>'
            f'<div style="color:#57606a;font-size:12px;margin-top:4px">{it["source"]} · {t} UTC</div></div>'
        )

parts.append('<p style="color:#8b949e;font-size:12px;margin-top:24px">由 tech-radar 自动生成 · GitHub Actions</p></div>')
html_body = "".join(parts)

user = os.environ.get("SMTP_USER")
pwd = os.environ.get("SMTP_PASS")
if not user or not pwd:
    print("缺少 SMTP_USER / SMTP_PASS 环境变量", file=sys.stderr)
    sys.exit(1)

msg = MIMEText(html_body, "html", "utf-8")
msg["Subject"] = Header(f"{email_cfg['subject_prefix']} {today}（{len(recent)}条）", "utf-8")
msg["From"] = user
msg["To"] = email_cfg["to"]

with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
    s.login(user, pwd)
    s.sendmail(user, [email_cfg["to"]], msg.as_string())

print(f"已发送 {len(recent)} 条到 {email_cfg['to']}")
