"""HTTP 取用層：重試、退避、節流、以及 FinMind 的每小時額度管理。

設計原則：
- 任何抓取失敗都不能讓整條管線死掉，回 None 讓上層決定要不要跳過
- FinMind 免費層 600 req/hr，回補時會長時間高頻呼叫，需要跨程序記住已用量
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any

import requests

from .. import config

log = logging.getLogger(__name__)

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        })
        _session = s
    return _session


def _body_snippet(r) -> str:
    """回應內容的前 200 字（給 log 用）。

    為什麼一定要記這一段（2026-09-19 的教訓）：
    原本 4xx 只寫「回 400，不重試」，等於把唯一的診斷資訊丟掉。
    那天 FinMind 連續好幾輪對每一個資料集都回 400，日誌裡卻只有狀態碼，
    完全分不出是 token 失效、帳號等級不足、還是參數改了 ——
    而這三種的修法完全不同（換金鑰／改計畫／改 parser）。
    這些 API 的 4xx body 幾乎都直接寫著原因，記下來下一個人才有辦法修。"""
    try:
        return r.text[:200].replace("\n", " ").replace("\r", " ")
    except Exception:  # noqa: BLE001 —— 診斷用，絕不能因為取不到內容而讓抓取失敗
        return "<無法讀取回應內容>"


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        timeout: int | None = None, retries: int | None = None,
        expect_json: bool = True, error_body: bool = False) -> Any | None:
    """帶指數退避的 GET。回傳 dict/list（JSON）或 str（文字）；失敗回 None。

    error_body=True 時，不重試的 4xx 會把回應內容包成
    {"status": <碼>, "msg": <前 200 字>} 回傳，讓呼叫端可以判斷失敗原因
    （只有 finmind_get 用；其他來源仍然一律拿到 None，行為不變）。"""
    retries = config.HTTP_RETRIES if retries is None else retries
    timeout = config.HTTP_TIMEOUT if timeout is None else timeout
    last_err: str = ""

    for attempt in range(retries):
        try:
            r = session().get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                if not expect_json:
                    # requests 對沒宣告 charset 的 text/* 會用 ISO-8859-1 解碼，中文表頭全變亂碼；
                    # 政府開放資料 CSV 又常帶 BOM。一律自己解碼並去掉 BOM。
                    m = re.search(r"charset=([\w-]+)", r.headers.get("Content-Type", ""), re.I)
                    enc = m.group(1) if m else "utf-8"
                    try:
                        text = r.content.decode(enc, errors="replace")
                    except LookupError:
                        text = r.text
                    return text.lstrip("﻿")
                try:
                    return r.json()
                except ValueError:
                    last_err = "回應不是合法 JSON"
                    log.warning("%s 回應不是 JSON（前 200 字）：%s", url, r.text[:200])
                    return None
            if r.status_code == 402:
                # FinMind 額度用盡會回 402 + JSON 說明；把 body 交給上層判斷，
                # 不然呼叫端分不出「沒資料」和「被限流」
                try:
                    body = r.json()
                except ValueError:
                    body = {"msg": r.text[:200]}
                if isinstance(body, dict):
                    body.setdefault("status", 402)
                    return body
                return {"status": 402, "msg": str(body)[:200]}
            if r.status_code in (403, 401):
                # 反爬或權限問題，重試沒有意義
                log.warning("%s 回 %s，判定為阻擋，不重試（回應前 200 字）：%s",
                            url, r.status_code, _body_snippet(r))
                if error_body:
                    return {"status": r.status_code, "msg": _body_snippet(r)}
                return None
            if r.status_code == 429 or 500 <= r.status_code < 600:
                last_err = f"HTTP {r.status_code}"
            else:
                snippet = _body_snippet(r)
                log.warning("%s 回 %s，不重試（回應前 200 字）：%s", url, r.status_code, snippet)
                if error_body:
                    try:
                        body = r.json()
                    except ValueError:
                        body = None
                    if isinstance(body, dict):
                        body.setdefault("status", r.status_code)
                        body.setdefault("msg", snippet)
                        return body
                    return {"status": r.status_code, "msg": snippet}
                return None
        except requests.RequestException as exc:
            last_err = str(exc)

        if attempt < retries - 1:
            wait = (2 ** attempt) + random.uniform(0, 0.8)
            log.info("%s 失敗（%s），%.1fs 後重試", url, last_err, wait)
            time.sleep(wait)

    log.error("%s 重試 %d 次仍失敗：%s", url, retries, last_err)
    return None


# ------------------------------------------------------------------ FinMind 額度

_QUOTA_FILE: Path = config.STATE / "finmind_quota.json"


def _load_quota() -> dict:
    if _QUOTA_FILE.exists():
        try:
            return json.loads(_QUOTA_FILE.read_text())
        except (ValueError, OSError):
            pass
    return {"window_start": 0.0, "used": 0}


def _save_quota(q: dict) -> None:
    try:
        _QUOTA_FILE.write_text(json.dumps(q))
    except OSError:
        pass


def finmind_budget_left() -> int:
    """這個小時還剩幾次可用。"""
    q = _load_quota()
    now = time.time()
    if now - q["window_start"] >= 3600:
        return config.FINMIND_HOURLY_LIMIT
    return max(0, config.FINMIND_HOURLY_LIMIT - q["used"])


def finmind_mark_exhausted() -> None:
    """伺服器端說額度用完了（402）。本機計數器只知道這個程序用了幾次，
    不知道前一個 Actions 執行已經把同一小時的額度吃掉，所以這裡直接把
    計數器填滿，讓 finmind_budget_left() 回 0、回補迴圈停下來。"""
    q = _load_quota()
    now = time.time()
    if now - q["window_start"] >= 3600:
        q["window_start"] = now
    q["used"] = config.FINMIND_HOURLY_LIMIT
    _save_quota(q)


def _is_rate_limited(payload: dict) -> bool:
    msg = str(payload.get("msg", "")).lower()
    return payload.get("status") == 402 or "exceed" in msg or "limit" in msg


#: 最近一次 FinMind 非 200 的回應（診斷用）。
#: 2026-09-19 那天三個資料集連續好幾輪全部回 400，日誌裡只有狀態碼，
#: 沒有人能判斷是 token 失效還是資料集不開放 —— 把原文留下來，上層才寫得進進度檔。
_last_error: dict | None = None


def finmind_last_error() -> dict | None:
    """最近一次 FinMind 非 200 的回應（含 dataset / data_id / status / msg）。"""
    return dict(_last_error) if _last_error else None


def finmind_get(dataset: str, *, data_id: str | None = None,
                start_date: str | None = None, end_date: str | None = None,
                wait_when_exhausted: bool = False) -> list[dict] | None:
    """呼叫 FinMind v4 data API，自動管理每小時額度。

    額度用完時：wait_when_exhausted=True 會睡到下個視窗（回補用），
    False 直接回 None 讓上層記錄「未完成」下次再補（每日排程用）。
    """
    q = _load_quota()
    now = time.time()
    if now - q["window_start"] >= 3600:
        q = {"window_start": now, "used": 0}

    if q["used"] >= config.FINMIND_HOURLY_LIMIT:
        sleep_for = 3600 - (now - q["window_start"]) + 5
        if not wait_when_exhausted:
            log.warning("FinMind 額度用盡，需等待 %.0f 秒，本次跳過", sleep_for)
            _save_quota(q)
            return None
        log.info("FinMind 額度用盡，等待 %.0f 秒後續抓", sleep_for)
        time.sleep(max(0, sleep_for))
        q = {"window_start": time.time(), "used": 0}

    params: dict[str, str] = {"dataset": dataset}
    if data_id:
        params["data_id"] = data_id
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if config.FINMIND_TOKEN:
        params["token"] = config.FINMIND_TOKEN

    q["used"] += 1
    _save_quota(q)

    # error_body=True：4xx 也要把回應內容帶回來，不然「為什麼失敗」就消失了
    payload = get(config.FINMIND_API, params=params, error_body=True)
    if not isinstance(payload, dict):
        return None
    if payload.get("status") != 200:
        global _last_error
        _last_error = {"dataset": dataset, "data_id": data_id,
                       "status": payload.get("status"), "msg": str(payload.get("msg"))[:200]}
        if _is_rate_limited(payload):
            log.warning("FinMind 伺服器端額度用盡（%s/%s）：%s",
                        dataset, data_id, payload.get("msg"))
            finmind_mark_exhausted()
            return None
        log.warning("FinMind %s/%s 回應狀態 %s：%s",
                    dataset, data_id, payload.get("status"), payload.get("msg"))
        return None
    return payload.get("data") or []


# ------------------------------------------------------------------ 二進位（Logo 圖檔）

def get_bytes(url: str, *, headers: dict | None = None, timeout: int = 10,
              max_bytes: int = 2_000_000, retries: int = 1,
              sess: requests.Session | None = None) -> tuple[int, bytes, str, str] | None:
    """抓二進位內容（圖檔、首頁 HTML 原文），回 (狀態碼, 內容, Content-Type, 轉址後的最終網址)；
    連線失敗回 None。最終網址是給解析 <link href="相對路徑"> 用的（官網常把首頁轉到 /tw/index.html）。

    為什麼不用上面的 get()：
    - get() 只回 JSON 或解碼後的文字，圖檔需要原始位元組。
    - Logo 的來源是各家公司官網，**狀態碼本身就是訊號**（Google s2 找不到 Logo 時回 404
      並附一張地球圖示），所以這裡把 4xx 也原樣交回去，由呼叫端判定「沒有」，不要只給 None。
    - 預設只重試 1 次、逾時 10 秒：官網動輒掛掉或很慢，一輪要跑幾百家，
      照 get() 的 3 次＋30 秒，一家壞站就能卡住 90 秒。
    - max_bytes：有些官網把首頁做成幾十 MB 的單頁，只讀前 2 MB，找 <link rel=icon> 綽綽有餘。
    - sess：多執行緒抓 Logo 時每條執行緒自己帶一個 Session（requests 不保證 Session 跨執行緒安全）。
    """
    s = sess or session()
    last_err = ""
    for attempt in range(max(1, retries)):
        try:
            with s.get(url, headers=headers, timeout=timeout, stream=True,
                       allow_redirects=True) as r:
                buf = bytearray()
                for chunk in r.iter_content(64 * 1024):
                    buf.extend(chunk)
                    if len(buf) >= max_bytes:
                        break
                return (r.status_code, bytes(buf[:max_bytes]),
                        r.headers.get("Content-Type", ""), str(r.url or url))
        except requests.RequestException as exc:
            last_err = str(exc)[:200]
        if attempt < retries - 1:
            time.sleep(1 + random.uniform(0, 0.5))
    log.info("%s 連線失敗：%s", url, last_err)
    return None
