"""新聞流。

鉅亨網的 JSON API 每則新聞自帶兩個欄位，這是整個 M4 事件面能自動化的關鍵：
  market  -> 相關股票代號清單（直接掛到個股）
  keyword -> 題材標籤（直接掛到族群，也用來偵測「新題材出現」）

經濟日報 RSS 當備援，確保鉅亨改版時新聞流不會整段消失。
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

import pandas as pd

from .. import config
from ..util import http

log = logging.getLogger(__name__)

_CNYES_HEADERS = {
    "Origin": "https://news.cnyes.com",
    "Referer": "https://news.cnyes.com/",
    "Accept": "application/json",
}


def cnyes(limit: int = 100) -> pd.DataFrame:
    payload = http.get(config.CNYES_NEWS, params={"limit": limit},
                       headers=_CNYES_HEADERS)
    if not isinstance(payload, dict):
        return pd.DataFrame()
    items = (payload.get("items") or {}).get("data") or []
    if not items:
        log.warning("鉅亨新聞回應無資料")
        return pd.DataFrame()

    rows = []
    for it in items:
        ts = it.get("publishAt")
        try:
            published = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
            day = datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
        except (TypeError, ValueError):
            published, day = None, None

        markets = it.get("market") or []
        codes = []
        for m in markets:
            if isinstance(m, dict):
                c = m.get("code") or m.get("symbol")
                if c:
                    codes.append(str(c).replace(".TW", "").strip())
            elif isinstance(m, str):
                codes.append(m.replace(".TW", "").strip())

        kws = it.get("keyword") or []
        keywords = [str(k) for k in kws if k]

        rows.append({
            "news_id": f"cnyes-{it.get('newsId')}",
            "source": "cnyes",
            "date": day,
            "published_at": published,
            "title": it.get("title"),
            "summary": it.get("summary") or "",
            "url": f"https://news.cnyes.com/news/id/{it.get('newsId')}",
            "codes": ",".join(dict.fromkeys(codes)),
            "keywords": ",".join(dict.fromkeys(keywords)),
        })
    df = pd.DataFrame(rows)
    log.info("鉅亨新聞：%d 則", len(df))
    return df


def udn_money() -> pd.DataFrame:
    """經濟日報 RSS 備援。沒有股票代號標記，只當新聞量與標題來源。"""
    try:
        import feedparser
    except ImportError:
        log.warning("未安裝 feedparser，跳過 udn 新聞")
        return pd.DataFrame()

    text = http.get(config.UDN_MONEY_RSS, expect_json=False)
    if not text:
        return pd.DataFrame()

    feed = feedparser.parse(text)
    rows = []
    for e in feed.entries:
        link = getattr(e, "link", "") or ""
        nid = "udn-" + hashlib.md5(link.encode()).hexdigest()[:16]
        published = getattr(e, "published", None)
        day = None
        if getattr(e, "published_parsed", None):
            day = datetime(*e.published_parsed[:3]).date().isoformat()
        rows.append({
            "news_id": nid,
            "source": "udn",
            "date": day,
            "published_at": published,
            "title": getattr(e, "title", ""),
            "summary": getattr(e, "summary", "")[:500],
            "url": link,
            "codes": "",
            "keywords": "",
        })
    df = pd.DataFrame(rows)
    log.info("經濟日報 RSS：%d 則", len(df))
    return df


def collect() -> pd.DataFrame:
    frames = [f for f in (cnyes(), udn_money()) if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates("news_id")
