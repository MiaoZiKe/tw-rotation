"""全體測試共用的隔離設定。

2026-10-03（DECISIONS #311）：`http` 的 FinMind 錯誤紀錄是模組層級狀態（全域最後一次＋每個資料集各一筆），
不清掉的話，上一支測試留下的錯誤會被下一支測試當成「這個資料集的封印理由」——
那正是 #311 要修的正式環境 bug 在測試裡的翻版。每支測試開始前一律清空。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.util import http  # noqa: E402


@pytest.fixture(autouse=True)
def _清空FinMind錯誤紀錄(monkeypatch):
    monkeypatch.setattr(http, "_last_error", None)
    monkeypatch.setattr(http, "_last_errors", {})
    yield


@pytest.fixture(autouse=True)
def _續補不打整天全市場法人(monkeypatch):
    """2026-10-20：refresh_stale_inst 開頭會先試 inst_bulk.fill_inst_bulk（讀真實資料湖＋打 FinMind）。
    續補的既有測試不測它，一律換成空的替身；inst_bulk 本身的測試（test_data_fresh_1020）直接呼叫真模組，不受影響。"""
    import types

    import pandas as pd

    from pipeline import run_backfill
    monkeypatch.setattr(run_backfill, "inst_bulk", types.SimpleNamespace(
        fill_inst_bulk=lambda *a, **k: pd.DataFrame(), site_codes=lambda: []))
    yield


@pytest.fixture(autouse=True)
def _官方法人來源不打網路(monkeypatch):
    """2026-10-20：inst_bulk.fill_inst_bulk 開頭會打官方法人端點（證交所／櫃買）。
    既有測試一律換成空替身；inst_official 自己的測試（test_inst_official）直接換 _get，不受影響。"""
    import pandas as pd

    from pipeline.sources import inst_official
    inst_official._cache.clear()
    monkeypatch.setattr(inst_official, "fetch_all", lambda *a, **k: pd.DataFrame())
    yield


class 測試連了真網路(RuntimeError):
    """測試呼叫了沒被替身的外部網路。"""


@pytest.fixture(autouse=True)
def _禁止連真網路(monkeypatch):
    """2026-10-20：雲端 daily.yml 的 pytest 因為有測試偷打真網路（mis.twse、FinMind、Yahoo…）卡超過 1 小時。
    測試的原則是「結果不依賴外部服務」：這裡把所有 requests 呼叫與非本機 socket 連線換成立刻 raise，
    以後誰新增測試漏了替身，會當場紅（附上網址），而不是卡住或默默吃真資料。
    刻意 raise 非 RequestException 的例外：http.get 會對 RequestException 重試＋sleep，
    吃掉的話測試只是變慢；要它直接紅才抓得到漏洞。
    需要真連線的測試（本機伺服器 127.0.0.1／localhost）不受影響。"""
    import socket

    import requests

    def _擋_send(self, request, **kw):
        raise 測試連了真網路(f"測試不准連真網路：{request.method} {request.url}")

    monkeypatch.setattr(requests.Session, "send", _擋_send)

    # yfinance 與 etf_pcf 走 curl_cffi（C 層連線，不經 requests／socket），要另外擋
    try:
        from curl_cffi.requests import Session as _CurlSession

        def _擋_curl(self, method, url, *a, **kw):
            raise 測試連了真網路(f"測試不准連真網路（curl_cffi）：{method} {url}")

        monkeypatch.setattr(_CurlSession, "request", _擋_curl)
    except ImportError:
        pass

    _原連線 = socket.create_connection

    def _擋_連線(address, *a, **kw):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
            raise 測試連了真網路(f"測試不准連真網路：{address}")
        return _原連線(address, *a, **kw)

    monkeypatch.setattr(socket, "create_connection", _擋_連線)
    yield
