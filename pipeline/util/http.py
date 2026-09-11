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


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        timeout: int | None = None, retries: int | None = None,
        expect_json: bool = True) -> Any | None:
    """帶指數退避的 GET。回傳 dict/list（JSON）或 str（文字）；失敗回 None。"""
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
                log.warning("%s 回 %s，判定為阻擋，不重試", url, r.status_code)
                return None
            if r.status_code == 429 or 500 <= r.status_code < 600:
                last_err = f"HTTP {r.status_code}"
            else:
                log.warning("%s 回 %s，不重試", url, r.status_code)
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

    payload = get(config.FINMIND_API, params=params)
    if not isinstance(payload, dict):
        return None
    if payload.get("status") != 200:
        if _is_rate_limited(payload):
            log.warning("FinMind 伺服器端額度用盡（%s/%s）：%s",
                        dataset, data_id, payload.get("msg"))
            finmind_mark_exhausted()
            return None
        log.warning("FinMind %s/%s 回應狀態 %s：%s",
                    dataset, data_id, payload.get("status"), payload.get("msg"))
        return None
    return payload.get("data") or []
