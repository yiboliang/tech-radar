# 行业雷达 tech-radar

AI / 光互联 / 半导体资讯聚合网站 + 每日邮件日报。完全免费运行（GitHub Pages + GitHub Actions）。

## 功能

- 每 3 小时自动抓取 Google News（中英文）+ 36氪 / IT之家 / TechCrunch 等 RSS
- 按 6 个主题自动分类：AI、光互联、半导体、CPO/OCS/光模块、HBM/先进封装、GPU/算力集群
- 网页支持主题切换、全文搜索、**自定义关键词增删**（存在浏览器本地，点击开关过滤）
- 每天北京时间早 7:00 自动发送 HTML 日报到 boscoliang44@gmail.com

## 部署（约 10 分钟）

### 1. 建仓库并上传

在 GitHub 新建仓库（如 `tech-radar`），把本文件夹全部内容上传（注意包含隐藏目录 `.github/`）。

命令行方式：

```bash
cd tech-radar
git init && git add -A && git commit -m "init"
git remote add origin https://github.com/<你的用户名>/tech-radar.git
git push -u origin main
```

### 2. 开启 GitHub Pages

仓库 Settings → Pages → Source 选 **Deploy from a branch**，Branch 选 `main`，目录选 `/docs`，保存。
几分钟后网站地址为 `https://<你的用户名>.github.io/tech-radar/`。

### 3. 配置邮件密钥

1. 到 https://myaccount.google.com/apppasswords 为 Gmail 生成一个**应用专用密码**（需先开启两步验证）
2. 仓库 Settings → Secrets and variables → Actions → New repository secret，添加两个：
   - `SMTP_USER` = 你的 Gmail 地址
   - `SMTP_PASS` = 刚生成的应用专用密码

### 4. 启用并测试

仓库 Actions 页面 → 如提示则点 "Enable workflows"。
手动测试：打开「抓取资讯并更新网站」→ Run workflow；再打开「每日邮件日报」→ Run workflow，检查邮箱。

之后全自动：每 3 小时更新网站，每天早 7 点发日报。

## 自定义

- **改主题/关键词/RSS 源**：编辑 `keywords.json`（`queries` 是 Google News 搜索词，`match` 是分类匹配词，`extra_feeds` 加 RSS 源）
- **改邮件收件人/频率**：`keywords.json` 的 `email` 段；发送时间改 `.github/workflows/daily-email.yml` 的 cron（UTC 时间，北京时间减 8）
- **网页上加关键词**：直接在页面关键词栏输入回车即可（仅本浏览器生效，用于过滤展示）

## 本地运行

```bash
pip install feedparser requests
python fetch_news.py            # 生成 docs/data.json
python -m http.server -d docs   # 打开 http://localhost:8000
SMTP_USER=xx@gmail.com SMTP_PASS=xxxx python send_email.py   # 手动发一封
```

## 文件结构

```
keywords.json                    # 全部配置：主题、关键词、RSS源、邮件
fetch_news.py                    # 抓取+分类+去重 → docs/data.json
send_email.py                    # 生成24小时日报并发邮件
docs/index.html                  # 网站（GitHub Pages 托管）
docs/data.json                   # 数据（自动生成）
.github/workflows/update.yml     # 每3小时抓取
.github/workflows/daily-email.yml# 每天 UTC 23:00（北京 7:00）发日报
```

注：当前 `docs/data.json` 是演示样例数据，首次运行抓取后会被真实数据覆盖。
