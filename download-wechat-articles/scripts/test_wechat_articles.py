#!/usr/bin/env python3
"""Offline tests for the WeChat article downloader."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from wechat_articles import (
    AuthData,
    DateWindow,
    WeChatError,
    WeChatMPClient,
    download_articles,
    build_title_markdown,
    build_multi_account_markdown,
    normalize_auth_payload,
    resolve_window,
    sanitize_filename,
)


class FakeResponse:
    def __init__(self, *, payload=None, text="", url="https://mp.weixin.qq.com/"):
        self._payload = payload
        self.text = text
        self.url = url

    def raise_for_status(self):
        return None

    def json(self):
        if self._payload is None:
            raise ValueError("not JSON")
        return self._payload


class FakeCookies:
    def set(self, *args, **kwargs):
        return None


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.cookies = FakeCookies()

    def get(self, *args, **kwargs):
        if not self.responses:
            raise AssertionError("Unexpected request")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class DateWindowTests(unittest.TestCase):
    def test_recent_days_are_inclusive(self):
        window = resolve_window(days=3, start=None, end=None, today=date(2026, 7, 21))
        self.assertEqual(window.start_date, date(2026, 7, 19))
        self.assertEqual(window.end_date, date(2026, 7, 21))

    def test_rejects_reversed_range(self):
        with self.assertRaises(WeChatError):
            resolve_window(
                days=None,
                start=date(2026, 7, 21),
                end=date(2026, 7, 20),
            )

    def test_rejects_days_combined_with_end(self):
        with self.assertRaises(WeChatError):
            resolve_window(
                days=3,
                start=None,
                end=date(2026, 7, 21),
                today=date(2026, 7, 21),
            )


class AuthTests(unittest.TestCase):
    def test_accepts_original_project_cookie_format(self):
        auth = normalize_auth_payload(
            [{"TOKEN": "123", "COOKIES": [{"name": "x", "value": "y"}]}]
        )
        self.assertEqual(auth.token, "123")
        self.assertEqual(auth.cookies[0]["name"], "x")

    def test_client_accepts_cookie_without_domain(self):
        client = WeChatMPClient(
            AuthData("token", [{"name": "cookie", "value": "value"}]),
            delay=1,
        )
        self.assertEqual(client.session.cookies.get("cookie"), "value")

    def test_network_error_does_not_expose_token(self):
        import requests

        client = WeChatMPClient(
            AuthData("secret-token", [{"name": "cookie", "value": "value"}]),
            session=FakeSession(
                [requests.ConnectionError("request failed with token=secret-token")]
            ),
            delay=1,
        )
        with self.assertRaises(WeChatError) as context:
            client.search_account("测试")
        self.assertNotIn("secret-token", str(context.exception))
        self.assertIn("ConnectionError", str(context.exception))


class DownloaderTests(unittest.TestCase):
    def test_sanitizes_filename(self):
        self.assertEqual(sanitize_filename('a/b:*?"<>| c'), "a_b_______ c")

    def test_accepts_client_rendered_page_with_exact_title(self):
        session = FakeSession(
            [FakeResponse(text='<html><script>window.title="新版文章"</script></html>')]
        )
        client = WeChatMPClient(
            AuthData("token", [{"name": "cookie", "value": "value"}]),
            session=session,
            delay=1,
        )
        result = client.fetch_article_html(
            "https://mp.weixin.qq.com/s/client-rendered",
            expected_title="新版文章",
        )
        self.assertIn("新版文章", result)

    def test_title_markdown_matches_collection_format(self):
        window = resolve_window(days=3, start=None, end=None, today=date(2026, 7, 21))
        content = build_title_markdown(
            {"nickname": "测试公众号"},
            window,
            [
                {
                    "title": "含|竖线的标题",
                    "url": "https://mp.weixin.qq.com/s/test",
                    "published_at": "2026-07-20T10:15:00+08:00",
                }
            ],
        )
        self.assertIn("# 2026-07-21（最近3天）", content)
        self.assertIn("## 测试公众号（1 篇）", content)
        self.assertIn("含\\|竖线的标题", content)
        self.assertIn("2026-07-20 10:15", content)

    def test_multi_account_markdown_groups_accounts(self):
        window = resolve_window(days=3, start=None, end=None, today=date(2026, 7, 21))
        content = build_multi_account_markdown(
            window,
            [
                {
                    "account": {"nickname": "账号甲"},
                    "articles": [
                        {
                            "title": "甲文章",
                            "url": "https://mp.weixin.qq.com/s/a",
                            "published_at": "2026-07-21T08:00:00+08:00",
                        }
                    ],
                },
                {"account": {"nickname": "账号乙"}, "articles": []},
            ],
        )
        self.assertIn("共 1 篇 / 2 个号", content)
        self.assertIn("## 账号甲（1 篇）", content)
        self.assertIn("## 账号乙（0 篇）", content)

    @patch("wechat_articles.time.sleep", return_value=None)
    def test_downloads_only_articles_inside_window(self, _sleep):
        inside = int(datetime(2026, 7, 20, 10, 0).timestamp())
        old = int(datetime(2026, 7, 10, 10, 0).timestamp())
        responses = [
            FakeResponse(
                payload={
                    "base_resp": {"ret": 0},
                    "list": [{"nickname": "测试公众号", "alias": "test", "fakeid": "fid"}],
                }
            ),
            FakeResponse(
                payload={
                    "base_resp": {"ret": 0},
                    "app_msg_cnt": 2,
                    "app_msg_list": [
                        {
                            "title": "保留文章",
                            "link": "https://mp.weixin.qq.com/s/inside",
                            "update_time": inside,
                        },
                        {
                            "title": "过期文章",
                            "link": "https://mp.weixin.qq.com/s/old",
                            "update_time": old,
                        },
                    ],
                }
            ),
            FakeResponse(text='<html><div id="js_content" class="rich_media_content">ok</div></html>'),
        ]
        client = WeChatMPClient(
            AuthData("token", [{"name": "cookie", "value": "value"}]),
            session=FakeSession(responses),
            delay=1,
        )
        window = resolve_window(days=3, start=None, end=None, today=date(2026, 7, 21))

        with tempfile.TemporaryDirectory() as tmp:
            result = download_articles(
                client,
                account_query="测试公众号",
                window=window,
                output_root=Path(tmp),
            )
            output = Path(result["output_dir"])
            self.assertEqual(result["downloaded"], 1)
            self.assertEqual(result["failed"], 0)
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "2026-07-21（最近3天）.md").is_file())
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual([item["title"] for item in manifest["articles"]], ["保留文章"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
