---
name: download-wechat-articles
description: Download public WeChat Official Account articles for one or multiple account names and a publication time range, saving complete HTML plus a grouped Markdown title collection, HTML indexes, and JSON manifests. Use when the user asks to download, archive, mirror, export, collect titles, or collect WeChat public account articles from the last N days or between explicit dates.
---

# Download WeChat Articles

Complete the workflow end to end with the bundled `scripts/wechat_articles.py` CLI. Do not ask the user to clone repositories or type terminal commands unless they explicitly request manual CLI instructions. The tool relies on a valid login session for the user's own WeChat Official Account backend; it does not bypass authentication.

## Workflow

1. Parse the requested account and time range.
   - "最近 3 天" -> `--days 3`.
   - Explicit dates -> `--start YYYY-MM-DD --end YYYY-MM-DD`.
   - If only a start date is supplied, use today as the end date.
   - Treat relative days as inclusive calendar days in `Asia/Shanghai`.
2. Resolve this Skill's directory from the loaded `SKILL.md`, then use its bundled `scripts/wechat_articles.py` and `scripts/requirements.txt` by absolute path.
3. Prepare a project-local runtime.
   - Prefer `.venv-wechat-skill` in the user's current project.
   - If the environment or dependencies are missing, briefly explain that `requests` and Selenium are required, request approval, create the virtual environment, and install `scripts/requirements.txt`.
   - Do not install into the system Python when a project-local virtual environment can be used.
4. Locate authentication in this order:
   - An explicit `--auth PATH` supplied by the user.
   - `WECHAT_MP_AUTH_FILE`.
   - `./.wechat-mp-auth.json`.
   - `./WeChat_Article/cookie.json` for compatibility with the cloned project.
5. If authentication is absent or expired, ask before opening a browser. Run the login command with the project-local virtual environment:

   ```bash
   .venv-wechat-skill/bin/python /absolute/path/to/scripts/wechat_articles.py login --auth .wechat-mp-auth.json
   ```

   On Windows, use `.venv-wechat-skill\Scripts\python.exe`. The user must finish the official `mp.weixin.qq.com` login in Chrome. Never request the user's password in chat.
6. Run the download command from the user's project directory with the same project-local Python:

   ```bash
   .venv-wechat-skill/bin/python /absolute/path/to/scripts/wechat_articles.py download \
     --account "公众号名称" \
     --account "另一个公众号" \
     --days 7 \
     --output downloads/wechat
   ```

7. Accept repeated `--account` arguments. Continue processing other accounts if one account fails.
8. Preserve the generated Markdown title collection named `YYYY-MM-DD（最近N天）.md`. It must contain a summary and a table with title, publication time, and original link, grouped by account. For multiple accounts, use the aggregate file in the date-range collection directory.
9. Report resolved account nicknames, requested interval, number of matching articles, output directory, and any failed accounts or downloads. Link the Markdown title collection, `index.html`, and `manifest.json`.

## Explicit Date Range

```bash
.venv-wechat-skill/bin/python /absolute/path/to/scripts/wechat_articles.py download \
  --account "公众号名称" \
  --start 2026-07-01 \
  --end 2026-07-15 \
  --output downloads/wechat
```

## Safety and Reliability

- Use only the user's authorized WeChat backend login and public article content.
- Never commit auth files. Before login, ensure the chosen auth path is ignored by Git or lies outside a repository.
- Do not print tokens or cookie values.
- Keep the default request interval. Increase `--delay` after frequency-control errors; do not rotate accounts or evade platform controls.
- Treat `searchbiz` and `appmsg` as private, unstable backend interfaces. If WeChat changes them, diagnose response metadata before editing the script.
- HTML files preserve the server response and may reference remote WeChat images, audio, video, or scripts; they are not guaranteed to be fully offline.

## Test Without WeChat Credentials

Run the deterministic offline tests:

```bash
.venv-wechat-skill/bin/python /absolute/path/to/scripts/test_wechat_articles.py
```
