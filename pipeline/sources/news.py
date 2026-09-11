"""新聞流：鉅亨三分類 ＋ TechNews ＋ 經濟日報備援，以及券商目標價的引述抽取。

分類直接用鉅亨網官方的 category（爬蟲專家實測可用）：
  tw_stock 台股 · tech 科技 · wd_macro 國際政經
不自己做 NLP 分類 —— 官方分好的就直接用。

券商目標價：這**不是我們的預估**，是新聞裡引述的券商看法。
一律帶券商名、日期、新聞連結，頁面上標明「券商觀點（新聞引述）」。
"""
from __future__ import annotations

import hashlib
import logging
import re
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


def _codes_from(markets) -> list[str]:
    codes = []
    for m in markets or []:
        c = None
        if isinstance(m, dict):
            c = m.get("code") or m.get("symbol")
        elif isinstance(m, str):
            c = m
        if c:
            c = str(c).replace("TWS:", "").replace(".TW", "").replace(":STOCK", "").strip()
            if c:
                codes.append(c)
    return list(dict.fromkeys(codes))


def cnyes(category: str = "tw_stock", limit: int = 60) -> pd.DataFrame:
    payload = http.get(config.CNYES_NEWS_BASE + category,
                       params={"limit": limit}, headers=_CNYES_HEADERS)
    if not isinstance(payload, dict):
        return pd.DataFrame()
    items = (payload.get("items") or {}).get("data") or []
    if not items:
        log.warning("鉅亨 %s 回應無資料", category)
        return pd.DataFrame()

    rows = []
    for it in items:
        ts = it.get("publishAt")
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            published, day = dt.isoformat(), dt.date().isoformat()
        except (TypeError, ValueError):
            published, day = None, None
        # 爬蟲專家實測欄位叫 stock，舊版叫 market，兩個都試
        codes = _codes_from(it.get("stock") or it.get("market"))
        kws = [str(k) for k in (it.get("keyword") or []) if k]
        rows.append({
            "news_id": f"cnyes-{it.get('newsId')}",
            "source": "cnyes",
            "category": config.CNYES_CATEGORIES.get(category, category),
            "date": day,
            "published_at": published,
            "title": it.get("title"),
            "summary": (it.get("summary") or "")[:600],
            "url": f"https://news.cnyes.com/news/id/{it.get('newsId')}",
            "codes": ",".join(codes),
            "keywords": ",".join(dict.fromkeys(kws)),
        })
    df = pd.DataFrame(rows)
    log.info("鉅亨 %s：%d 則", category, len(df))
    return df


def _rss(url: str, source: str, category: str) -> pd.DataFrame:
    try:
        import feedparser
    except ImportError:
        log.warning("未安裝 feedparser，跳過 %s", source)
        return pd.DataFrame()
    text = http.get(url, expect_json=False)
    if not text:
        return pd.DataFrame()
    feed = feedparser.parse(text)
    rows = []
    for e in feed.entries:
        link = getattr(e, "link", "") or ""
        nid = f"{source}-" + hashlib.md5(link.encode()).hexdigest()[:16]
        day = None
        if getattr(e, "published_parsed", None):
            day = datetime(*e.published_parsed[:3]).date().isoformat()
        tags = [t.get("term") for t in getattr(e, "tags", []) if t.get("term")]
        rows.append({
            "news_id": nid, "source": source, "category": category,
            "date": day, "published_at": getattr(e, "published", None),
            "title": getattr(e, "title", ""),
            "summary": re.sub(r"<[^>]+>", "", getattr(e, "summary", ""))[:600],
            "url": link, "codes": "", "keywords": ",".join(tags[:8]),
        })
    df = pd.DataFrame(rows)
    log.info("%s RSS：%d 則", source, len(df))
    return df


def technews() -> pd.DataFrame:
    """TechNews 科技新報，補半導體 / AI 的深度報導（RSS 帶分類標籤）。"""
    return _rss(config.TECHNEWS_RSS, "technews", "科技")


def udn_money() -> pd.DataFrame:
    return _rss(config.UDN_MONEY_RSS, "udn", "台股")


def collect() -> pd.DataFrame:
    frames = [cnyes(c) for c in config.CNYES_CATEGORIES]
    frames += [technews(), udn_money()]
    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates("news_id")


# ------------------------------------------------------------------ 券商目標價抽取

# 常見寫法：「目標價 1,500 元」「目標價上調至 1500」「喊到 1,500 元」「目標價由 1200 升至 1500」
_TARGET_RE = re.compile(
    r"目標價[^\d\n]{0,12}?(?:至|到|為|看|喊|升至|上調至|調升至|調高至|下修至|降至|調降至)?\s*"
    r"((?:\d{1,3}(?:,\d{3})+|\d{2,6})(?:\.\d+)?)\s*元?"     # 1,500 / 1500 / 88.5 都要接得住
)
# 券商名單：出現在同一則新聞裡就當作引述來源
_BROKERS = [
    "高盛", "摩根士丹利", "大摩", "摩根大通", "小摩", "美銀", "美林", "花旗", "瑞銀", "瑞士信貸",
    "麥格理", "匯豐", "野村", "大和", "里昂", "傑富瑞", "Jefferies", "巴克萊", "德意志",
    "凱基", "元大", "富邦", "統一", "國泰", "永豐", "群益", "兆豐", "玉山", "中信", "台新",
    "宏遠", "康和", "第一金", "華南永昌", "日盛", "元富", "亞東", "國票",
    "外資", "法人", "券商",
]
_BROKER_RE = re.compile("|".join(re.escape(b) for b in _BROKERS))
_ACTION_RE = re.compile(r"(上調|調升|調高|升至|上修|下修|調降|調低|降至|重申|維持|首評|給予|喊)")
_RATING_RE = re.compile(r"(買進|買入|加碼|優於大盤|中立|持有|減碼|劣於大盤|賣出|Buy|Overweight|Neutral|Underweight|Sell)", re.I)


def extract_broker_views(news: pd.DataFrame) -> pd.DataFrame:
    """從新聞標題與摘要抽出「某券商對某股的目標價」。

    只抽有明確股票代號、明確數字的；抽不出券商名就標「未具名」。
    這是引述，不是我們的判斷 —— 表格與頁面都會這樣標。
    """
    if news is None or news.empty:
        return pd.DataFrame()
    rows = []
    for _, n in news.iterrows():
        text = f"{n.get('title') or ''}。{n.get('summary') or ''}"
        m = _TARGET_RE.search(text)
        if not m:
            continue
        try:
            target = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if not (5 <= target <= 20000):
            continue
        codes = [c for c in str(n.get("codes") or "").split(",") if c]
        if not codes:
            continue
        broker_m = _BROKER_RE.search(text)
        broker = broker_m.group(0) if broker_m else "未具名"
        action_m = _ACTION_RE.search(text)
        rating_m = _RATING_RE.search(text)
        # 一則新聞若掛多檔股票，只把目標價掛到第一檔（其餘通常是順帶提及）
        rows.append({
            "news_id": n["news_id"],
            "code": codes[0],
            "date": n.get("date"),
            "broker": broker,
            "target_price": target,
            "action": action_m.group(1) if action_m else None,
            "rating": rating_m.group(1) if rating_m else None,
            "title": n.get("title"),
            "url": n.get("url"),
            "source": n.get("source"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        log.info("券商目標價引述：%d 筆", len(df))
    return df
