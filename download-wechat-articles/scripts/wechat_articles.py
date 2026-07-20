#!/usr/bin/env python3
"""Download WeChat Official Account articles through an authorized MP session."""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import stat
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

try:
    import requests
except ImportError as exc:  # pragma: no cover - user-facing dependency path
    raise SystemExit(
        "Missing dependency 'requests'. Install scripts/requirements.txt first."
    ) from exc


SHANGHAI = ZoneInfo("Asia/Shanghai")
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36"
    ),
    "Referer": "https://mp.weixin.qq.com/",
}


class WeChatError(RuntimeError):
    """A safe, user-facing WeChat operation error."""


@dataclass(frozen=True)
class AuthData:
    token: str
    cookies: List[Dict[str, Any]]


@dataclass(frozen=True)
class DateWindow:
    start: datetime
    end: datetime

    @property
    def start_date(self) -> date:
        return self.start.date()

    @property
    def end_date(self) -> date:
        return self.end.date()

    def contains_timestamp(self, timestamp: int) -> bool:
        value = datetime.fromtimestamp(timestamp, SHANGHAI)
        return self.start <= value <= self.end


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'; expected YYYY-MM-DD"
        ) from exc


def resolve_window(
    *,
    days: Optional[int],
    start: Optional[date],
    end: Optional[date],
    today: Optional[date] = None,
) -> DateWindow:
    current = today or datetime.now(SHANGHAI).date()
    if days is not None:
        if end is not None:
            raise WeChatError("Do not combine --days with --end")
        if days < 1:
            raise WeChatError("--days must be at least 1")
        start_date = current - timedelta(days=days - 1)
        end_date = current
    else:
        if start is None:
            raise WeChatError("Provide --days or --start")
        start_date = start
        end_date = end or current
        if end_date < start_date:
            raise WeChatError("--end cannot be earlier than --start")

    return DateWindow(
        start=datetime.combine(start_date, datetime_time.min, SHANGHAI),
        end=datetime.combine(end_date, datetime_time.max, SHANGHAI),
    )


def normalize_auth_payload(payload: Any) -> AuthData:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        raise WeChatError("Unsupported authentication file format")

    token = payload.get("token") or payload.get("TOKEN")
    cookies = payload.get("cookies") or payload.get("COOKIES")
    if not token or not isinstance(cookies, list) or not cookies:
        raise WeChatError("Authentication file is missing token or cookies")
    return AuthData(token=str(token), cookies=cookies)


def discover_auth_path(explicit: Optional[Path], cwd: Path) -> Path:
    candidates: List[Path] = []
    if explicit:
        candidates.append(explicit.expanduser())
    env_path = os.environ.get("WECHAT_MP_AUTH_FILE")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(
        [cwd / ".wechat-mp-auth.json", cwd / "WeChat_Article" / "cookie.json"]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    searched = ", ".join(str(item) for item in candidates)
    raise WeChatError(f"No authentication file found. Checked: {searched}")


def load_auth(path: Path) -> AuthData:
    try:
        return normalize_auth_payload(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise WeChatError(f"Authentication file is not valid JSON: {path}") from exc


def save_auth(path: Path, auth: AuthData) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"token": auth.token, "cookies": auth.cookies},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def sanitize_filename(value: str, max_length: int = 100) -> str:
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value[:max_length].rstrip(" .") or "untitled")


def check_api_response(payload: Dict[str, Any], operation: str) -> None:
    base = payload.get("base_resp") or {}
    code = base.get("ret", payload.get("ret", 0))
    message = base.get("err_msg") or payload.get("errmsg") or "unknown error"
    if code not in (None, 0):
        raise WeChatError(f"{operation} failed ({code}): {message}")


class WeChatMPClient:
    def __init__(
        self,
        auth: AuthData,
        *,
        session: Optional[requests.Session] = None,
        delay: float = 5.0,
        timeout: Tuple[float, float] = (20.0, 60.0),
    ) -> None:
        self.auth = auth
        self.session = session or requests.Session()
        self.delay = delay
        self.timeout = timeout
        self.session.headers.update(DEFAULT_HEADERS)
        for cookie in auth.cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value is not None:
                cookie_options: Dict[str, Any] = {"path": cookie.get("path") or "/"}
                if cookie.get("domain"):
                    cookie_options["domain"] = cookie["domain"]
                self.session.cookies.set(name, value, **cookie_options)
        self.session.cookies.set("wxtokenkey", "777")

    def _get_json(self, url: str, params: Dict[str, Any], operation: str) -> Dict[str, Any]:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WeChatError(
                f"{operation} request failed ({type(exc).__name__})"
            ) from exc
        check_api_response(payload, operation)
        return payload

    def validate_auth(self) -> None:
        try:
            response = self.session.get(
                "https://mp.weixin.qq.com/cgi-bin/home",
                params={
                    "t": "home/index",
                    "lang": "zh_CN",
                    "token": self.auth.token,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WeChatError(
                f"Could not validate WeChat login ({type(exc).__name__})"
            ) from exc
        if "token=" not in response.url and ("登录" in response.text or "login" in response.url):
            raise WeChatError("WeChat login has expired; run the login command again")

    def search_account(self, query: str) -> Dict[str, Any]:
        payload = self._get_json(
            "https://mp.weixin.qq.com/cgi-bin/searchbiz",
            {
                "action": "search_biz",
                "token": self.auth.token,
                "lang": "zh_CN",
                "f": "json",
                "ajax": 1,
                "random": random.random(),
                "query": query,
                "begin": 0,
                "count": 20,
            },
            "search account",
        )
        accounts = payload.get("list") or []
        if not accounts:
            raise WeChatError(f"No WeChat Official Account matched '{query}'")

        lowered = query.strip().casefold()
        exact = [
            item
            for item in accounts
            if str(item.get("nickname", "")).strip().casefold() == lowered
            or str(item.get("alias", "")).strip().casefold() == lowered
        ]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            accounts = exact
        if len(accounts) > 1:
            choices = "; ".join(
                f"{item.get('nickname', '?')} ({item.get('alias') or 'no alias'})"
                for item in accounts[:10]
            )
            raise WeChatError(
                f"Account name is ambiguous. Use an exact nickname or alias. Matches: {choices}"
            )
        return accounts[0]

    def iter_articles(
        self, fakeid: str, window: DateWindow, *, page_size: int = 5
    ) -> Iterable[Dict[str, Any]]:
        begin = 0
        while True:
            payload = self._get_json(
                "https://mp.weixin.qq.com/cgi-bin/appmsg",
                {
                    "token": self.auth.token,
                    "lang": "zh_CN",
                    "f": "json",
                    "ajax": 1,
                    "random": random.random(),
                    "action": "list_ex",
                    "begin": begin,
                    "count": page_size,
                    "query": "",
                    "fakeid": fakeid,
                    "type": 9,
                },
                "list articles",
            )
            articles = payload.get("app_msg_list") or []
            if not articles:
                return

            oldest_timestamp: Optional[int] = None
            for article in articles:
                timestamp = int(article.get("update_time") or 0)
                if not timestamp:
                    continue
                oldest_timestamp = (
                    timestamp
                    if oldest_timestamp is None
                    else min(oldest_timestamp, timestamp)
                )
                if window.contains_timestamp(timestamp):
                    yield article

            if oldest_timestamp is not None:
                oldest = datetime.fromtimestamp(oldest_timestamp, SHANGHAI)
                if oldest < window.start:
                    return

            begin += page_size
            total = int(payload.get("app_msg_cnt") or 0)
            if total and begin >= total:
                return
            time.sleep(self.delay + random.uniform(0, min(1.5, self.delay / 2)))

    def fetch_article_html(self, url: str, expected_title: Optional[str] = None) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
            "mp.weixin.qq.com",
            "weixin.qq.com",
        }:
            raise WeChatError(f"Refusing unexpected article URL: {url}")
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WeChatError(f"Article download failed: {exc}") from exc
        title_matches = bool(
            expected_title
            and (
                expected_title in response.text
                or html.escape(expected_title, quote=False) in response.text
            )
        )
        if "rich_media_content" not in response.text and not title_matches:
            raise WeChatError("Response did not contain a WeChat article body")
        return response.text


def build_index(
    account: Dict[str, Any], window: DateWindow, records: Sequence[Dict[str, Any]]
) -> str:
    items = "\n".join(
        "<li><time>{published}</time> <a href=\"{file}\">{title}</a></li>".format(
            published=html.escape(record["published_at"]),
            file=html.escape(record["file"], quote=True),
            title=html.escape(record["title"]),
        )
        for record in records
        if record.get("status") == "downloaded"
    )
    nickname = html.escape(str(account.get("nickname") or "Unknown account"))
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{nickname} 文章归档</title>
<style>body{{max-width:860px;margin:2rem auto;padding:0 1rem;font:16px/1.7 system-ui,sans-serif}}time{{color:#666}}li{{margin:.65rem 0}}</style>
</head><body><h1>{nickname} 文章归档</h1>
<p>{window.start_date.isoformat()} 至 {window.end_date.isoformat()}，共 {len(records)} 条记录。</p>
<ol>{items}</ol></body></html>"""


def escape_markdown_table(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def build_title_markdown(
    account: Dict[str, Any], window: DateWindow, records: Sequence[Dict[str, Any]]
) -> str:
    days = (window.end_date - window.start_date).days + 1
    nickname = escape_markdown_table(account.get("nickname") or "Unknown account")
    lines = [
        f"# {window.end_date.isoformat()}（最近{days}天）",
        "",
        (
            f"自动同步自「{nickname}」公众号，覆盖 "
            f"{window.start_date.isoformat()} 至 {window.end_date.isoformat()} "
            f"发布的文章。共 {len(records)} 篇 / 1 个号。"
        ),
        "",
        f"## {nickname}（{len(records)} 篇）",
        "",
        "|标题|发布时间|链接|",
        "|---|---|---|",
    ]
    for record in records:
        published = datetime.fromisoformat(record["published_at"]).strftime("%Y-%m-%d %H:%M")
        title = escape_markdown_table(record["title"])
        url = str(record["url"]).replace(" ", "%20")
        lines.append(f"|{title}|{published}|[打开原文]({url})|")
    lines.extend(["", "> （注：文章版权归原作者及原公众号所有）", ""])
    return "\n".join(lines)


def build_multi_account_markdown(
    window: DateWindow,
    results: Sequence[Dict[str, Any]],
    account_errors: Sequence[Dict[str, str]] = (),
) -> str:
    days = (window.end_date - window.start_date).days + 1
    total_articles = sum(len(result.get("articles") or []) for result in results)
    lines = [
        f"# {window.end_date.isoformat()}（最近{days}天）",
        "",
        (
            "自动同步多个对标公众号，覆盖 "
            f"{window.start_date.isoformat()} 至 {window.end_date.isoformat()} "
            f"发布的文章。共 {total_articles} 篇 / {len(results)} 个号。"
        ),
        "",
    ]
    for result in results:
        account = result.get("account") or {}
        records = result.get("articles") or []
        nickname = escape_markdown_table(account.get("nickname") or result.get("account_query"))
        lines.extend(
            [
                f"## {nickname}（{len(records)} 篇）",
                "",
                "|标题|发布时间|链接|",
                "|---|---|---|",
            ]
        )
        for record in records:
            published = datetime.fromisoformat(record["published_at"]).strftime(
                "%Y-%m-%d %H:%M"
            )
            title = escape_markdown_table(record["title"])
            url = str(record["url"]).replace(" ", "%20")
            lines.append(f"|{title}|{published}|[打开原文]({url})|")
        lines.append("")

    if account_errors:
        lines.extend(["## 抓取失败", ""])
        for failure in account_errors:
            lines.append(
                f"- {escape_markdown_table(failure['account'])}："
                f"{escape_markdown_table(failure['error'])}"
            )
        lines.append("")

    lines.extend(["> （注：文章版权归原作者及原公众号所有）", ""])
    return "\n".join(lines)


def write_multi_account_summary(
    *,
    window: DateWindow,
    results: Sequence[Dict[str, Any]],
    account_errors: Sequence[Dict[str, str]],
    output_root: Path,
) -> Dict[str, Any]:
    range_dir = output_root / f"{window.start_date.isoformat()}_{window.end_date.isoformat()}"
    range_dir.mkdir(parents=True, exist_ok=True)
    day_count = (window.end_date - window.start_date).days + 1
    titles_filename = f"{window.end_date.isoformat()}（最近{day_count}天）.md"
    summary = {
        "start_date": window.start_date.isoformat(),
        "end_date": window.end_date.isoformat(),
        "account_count": len(results),
        "failed_account_count": len(account_errors),
        "downloaded": sum(int(result.get("downloaded") or 0) for result in results),
        "failed": sum(int(result.get("failed") or 0) for result in results),
        "accounts": list(results),
        "account_errors": list(account_errors),
        "output_dir": str(range_dir.resolve()),
        "titles_file": titles_filename,
        "manifest_file": "manifest.json",
    }
    (range_dir / titles_filename).write_text(
        build_multi_account_markdown(window, results, account_errors), encoding="utf-8"
    )
    (range_dir / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def download_articles(
    client: WeChatMPClient,
    *,
    account_query: str,
    window: DateWindow,
    output_root: Path,
) -> Dict[str, Any]:
    account = client.search_account(account_query)
    fakeid = account.get("fakeid")
    if not fakeid:
        raise WeChatError("Matched account did not include a fakeid")

    account_dir = output_root / sanitize_filename(str(account.get("nickname") or account_query))
    range_dir = account_dir / f"{window.start_date.isoformat()}_{window.end_date.isoformat()}"
    range_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    seen_links = set()
    for article in client.iter_articles(str(fakeid), window):
        link = str(article.get("link") or "")
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        timestamp = int(article["update_time"])
        published = datetime.fromtimestamp(timestamp, SHANGHAI)
        title = str(article.get("title") or "Untitled")
        filename = (
            f"{published.strftime('%Y-%m-%d_%H%M%S')}_"
            f"{sanitize_filename(title)}.html"
        )
        record: Dict[str, Any] = {
            "title": title,
            "url": link,
            "published_at": published.isoformat(),
            "file": filename,
            "status": "pending",
        }
        try:
            article_html = client.fetch_article_html(link, expected_title=title)
            (range_dir / filename).write_text(article_html, encoding="utf-8")
            record["status"] = "downloaded"
            print(f"Downloaded: {published:%Y-%m-%d} {title}")
        except (OSError, WeChatError) as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            print(f"Failed: {title}: {exc}", file=sys.stderr)
        records.append(record)
        time.sleep(client.delay)

    manifest = {
        "account_query": account_query,
        "account": {
            "nickname": account.get("nickname"),
            "alias": account.get("alias"),
            "fakeid": fakeid,
        },
        "start_date": window.start_date.isoformat(),
        "end_date": window.end_date.isoformat(),
        "downloaded": sum(item["status"] == "downloaded" for item in records),
        "failed": sum(item["status"] == "failed" for item in records),
        "articles": records,
    }
    day_count = (window.end_date - window.start_date).days + 1
    titles_filename = f"{window.end_date.isoformat()}（最近{day_count}天）.md"
    manifest["output_dir"] = str(range_dir.resolve())
    manifest["index_file"] = "index.html"
    manifest["titles_file"] = titles_filename
    (range_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (range_dir / "index.html").write_text(
        build_index(account, window, records), encoding="utf-8"
    )
    (range_dir / titles_filename).write_text(
        build_title_markdown(account, window, records), encoding="utf-8"
    )
    return manifest


def login(auth_path: Path, timeout_seconds: int) -> None:
    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError as exc:  # pragma: no cover - user-facing dependency path
        raise WeChatError(
            "Login requires Selenium. Install scripts/requirements.txt first."
        ) from exc

    print("Opening the official WeChat MP login page in Chrome...")
    driver = webdriver.Chrome()
    try:
        driver.get("https://mp.weixin.qq.com/")

        def logged_in(browser: Any) -> bool:
            return "token=" in browser.current_url and "mp.weixin.qq.com" in browser.current_url

        WebDriverWait(driver, timeout_seconds).until(logged_in)
        match = re.search(r"[?&]token=([^&]+)", driver.current_url)
        if not match:
            raise WeChatError("Login completed but no token was present in the URL")
        save_auth(auth_path, AuthData(token=match.group(1), cookies=driver.get_cookies()))
        print(f"Authentication saved to {auth_path.resolve()} with user-only permissions")
    finally:
        driver.quit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download WeChat Official Account articles as HTML"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    login_parser = subparsers.add_parser("login", help="Create an auth file interactively")
    login_parser.add_argument("--auth", type=Path, default=Path(".wechat-mp-auth.json"))
    login_parser.add_argument("--timeout", type=int, default=600)

    download_parser = subparsers.add_parser("download", help="Download matching articles")
    download_parser.add_argument(
        "--account",
        action="append",
        dest="accounts",
        required=True,
        help="Exact nickname or WeChat ID; repeat for multiple accounts",
    )
    date_group = download_parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument("--days", type=int, help="Inclusive calendar-day window")
    date_group.add_argument("--start", type=parse_iso_date, help="Start date, YYYY-MM-DD")
    download_parser.add_argument("--end", type=parse_iso_date, help="End date, YYYY-MM-DD")
    download_parser.add_argument("--auth", type=Path)
    download_parser.add_argument("--output", type=Path, default=Path("downloads/wechat"))
    download_parser.add_argument("--delay", type=float, default=5.0)
    download_parser.add_argument(
        "--skip-auth-check",
        action="store_true",
        help="Skip the initial backend session check",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "login":
            login(args.auth.expanduser(), args.timeout)
            return 0

        if args.delay < 1:
            raise WeChatError("--delay must be at least 1 second")
        window = resolve_window(days=args.days, start=args.start, end=args.end)
        auth_path = discover_auth_path(args.auth, Path.cwd())
        client = WeChatMPClient(load_auth(auth_path), delay=args.delay)
        if not args.skip_auth_check:
            client.validate_auth()
        output_root = args.output.expanduser()
        results: List[Dict[str, Any]] = []
        account_errors: List[Dict[str, str]] = []
        for index, account_query in enumerate(args.accounts):
            print(f"Processing account: {account_query}")
            try:
                results.append(
                    download_articles(
                        client,
                        account_query=account_query,
                        window=window,
                        output_root=output_root,
                    )
                )
            except WeChatError as exc:
                print(f"Account failed: {account_query}: {exc}", file=sys.stderr)
                account_errors.append({"account": account_query, "error": str(exc)})
            if index + 1 < len(args.accounts):
                time.sleep(args.delay)

        if len(args.accounts) == 1:
            if account_errors:
                raise WeChatError(account_errors[0]["error"])
            result = results[0]
        else:
            result = write_multi_account_summary(
                window=window,
                results=results,
                account_errors=account_errors,
                output_root=output_root,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["failed"] == 0 and not account_errors else 2
    except WeChatError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
