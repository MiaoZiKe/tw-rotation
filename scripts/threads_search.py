"""Threads 關鍵字搜尋（keyword_search）共用程式（2026-11-09）。

給兩支程式用：
  · scripts/threads_hot_collect.py —— 研調用：抓熱門財經串、做字數／句型／時段統計（只讀）。
  · scripts/auto_reply.py 的 B 層 —— 找別人的熱門串當回覆候選（B 層預設關閉）。

官方端點：GET https://graph.threads.net/v1.0/keyword_search?q=<關鍵字>&search_type=TOP|RECENT&fields=...
  · 權限：threads_basic ＋ threads_keyword_search。
  · ★ threads_keyword_search 還沒通過 App 審查（Advanced Access）前，官方文件寫明「只會搜到自己帳號的貼文」。
    所以本程式用「搜回來的貼文是不是全都是自己的」判斷權限有沒有真的生效（permission_state()）。
  · 欄位：id、text、media_type、permalink、timestamp、username、has_replies、is_quote_post、is_reply……
    讚數／回覆數屬於 insights，只有「自己的貼文」查得到；別人的貼文查不到（會記成 None，不是 0）。
說明文件：docs/marketing/social_unit/auto_reply.md
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

TAIPEI = timezone(timedelta(hours=8))
FIELDS_FULL = "id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply,like_count,reply_count"
FIELDS_BASIC = "id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post"
DEFAULT_KEYWORDS = ("台股", "外資", "台積電", "ETF", "高股息", "財報", "輝達", "AI伺服器", "美股", "降息", "股市", "0050")


class SearchError(Exception):
    pass


def _call(method: str, path: str, token: str, params: dict | None = None) -> dict:
    import threads_post as TP   # 延後載入：測試可以換掉 _call
    try:
        return TP._call(method, path, token, params)
    except TP.PostError as e:
        raise SearchError(str(e)) from None


def search(token: str, q: str, search_type: str = "TOP", limit: int = 50, call=None) -> tuple[list[dict], str]:
    """回傳（貼文清單, 用了哪組欄位）。先要完整欄位；Meta 不收某個欄位（HTTP 400）就退回基本欄位再試一次。"""
    call = call or _call
    rows: list[dict] = []
    used = FIELDS_FULL
    for fields in (FIELDS_FULL, FIELDS_BASIC):
        try:
            d = call("GET", "/keyword_search", token,
                     {"q": q, "search_type": search_type, "fields": fields, "limit": str(min(max(limit, 1), 100))})
            rows, used = list(d.get("data") or []), fields
            break
        except SearchError as e:
            if fields == FIELDS_BASIC or "HTTP 400" not in str(e):
                raise
    for r in rows:
        r["keyword"] = q
    return rows[:limit], used


def permission_state(rows: list[dict], me: str) -> str:
    """'approved'＝搜到別人的貼文；'own_only'＝只搜到自己的（權限還沒過審）；'empty'＝什麼都沒搜到。"""
    if not rows:
        return "empty"
    users = {r.get("username") for r in rows if r.get("username")}
    return "own_only" if users and users <= {me} else "approved"


# ── 統計 ────────────────────────────────────────────────────────────────
_URL = re.compile(r"https?://\S+")
_EMOJI = re.compile(r"[\U0001F000-\U0001FFFF☀-➿]")
EMOTION_WORDS = ("哭", "笑死", "崩", "爽", "慘", "怕", "嚇", "瘋", "扯", "傻眼", "完了", "沒了", "救命", "天啊", "唉", "哈", "！", "!")


def clen(s: str) -> int:
    """字數：不算空白與換行、不算網址。"""
    return len(re.sub(r"\s", "", _URL.sub("", s or "")))


def first_sentence(s: str) -> str:
    t = (s or "").strip().splitlines()[0] if (s or "").strip() else ""
    m = re.match(r"(.+?[。！？!?…]|.+$)", t)
    return (m.group(1) if m else t).strip()


def opener_type(text: str) -> str:
    """第一句句型：問句／數字開頭／情緒句／陳述。順序有意義（問句優先）。"""
    f = first_sentence(text)
    if not f:
        return "空白"
    if re.search(r"[？?]$|嗎$|呢$|還是", f):
        return "問句"
    if re.match(r"[\d０-９一二三四五六七八九十百千萬億]+[\d,.％%０-９]*\s*(?:[%％點元億萬張檔天年月日倍]|$)", f) or re.match(r"[\d０-９]", f):
        return "數字開頭"
    if any(w in f for w in EMOTION_WORDS) or _EMOJI.search(f):
        return "情緒句"
    return "陳述"


def length_bucket(n: int) -> str:
    for hi, lab in ((30, "0-30"), (80, "31-80"), (150, "81-150"), (300, "151-300")):
        if n <= hi:
            return lab
    return "300以上"


def hour_tpe(ts: str) -> int | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(TAIPEI).hour
    except (TypeError, ValueError):
        return None


def stats(rows: list[dict]) -> dict:
    """字數分布、第一句句型、發文時段（台北）、有圖比例、帳號集中度。去重以貼文 id。
    ★ 2026-11-09 CEO 拍板：只留統計。帳號只記「次數」不記名字（account_post_counts＝前 15 名各出現幾則，名字丟掉）；
    不存全文、帳號名、permalink。"""
    seen, uniq = set(), []
    for r in rows:
        if r.get("id") and r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    n = len(uniq)
    lens = sorted(clen(r.get("text", "")) for r in uniq)
    hours = Counter(h for h in (hour_tpe(r.get("timestamp", "")) for r in uniq) if h is not None)
    media = Counter(r.get("media_type") or "?" for r in uniq)
    with_img = sum(v for k, v in media.items() if k in ("IMAGE", "CAROUSEL_ALBUM", "VIDEO"))
    likes = [r["like_count"] for r in uniq if isinstance(r.get("like_count"), int)]
    by_kw = Counter(r.get("keyword") for r in rows)
    return {
        "posts": n,
        "per_keyword": dict(by_kw),
        "length": {
            "median": lens[n // 2] if n else None,
            "p25": lens[n // 4] if n else None,
            "p75": lens[(3 * n) // 4] if n else None,
            "buckets": dict(Counter(length_bucket(x) for x in lens)),
        },
        "opener": dict(Counter(opener_type(r.get("text", "")) for r in uniq)),
        "hour_taipei": {str(h): hours[h] for h in sorted(hours)},
        "media": dict(media),
        "with_media_ratio": round(with_img / n, 3) if n else None,
        "has_url_ratio": round(sum(1 for r in uniq if _URL.search(r.get("text") or "")) / n, 3) if n else None,
        "unique_accounts": len({r.get("username") for r in uniq if r.get("username")}),
        "account_post_counts": [c for _, c in Counter(r.get("username") for r in uniq if r.get("username")).most_common(15)],
        "like_count_available": bool(likes),
        "like_median": sorted(likes)[len(likes) // 2] if likes else None,
    }


def stats_md(st: dict, day: str, perm: str) -> str:
    L = [f"# Threads 熱門財經串統計 {day}", "",
         f"權限狀態：{ {'approved': '已生效（搜得到別人的貼文）', 'own_only': '只搜得到自己的貼文（threads_keyword_search 還沒過審）', 'empty': '搜不到任何貼文', 'missing_permission': '權杖缺 threads_keyword_search 權限（API 直接拒絕）'}.get(perm, perm) }",
         f"不重複貼文：{st['posts']} 則", ""]
    if not st["posts"]:
        return "\n".join(L) + "\n"
    ln = st["length"]
    L += [f"字數：中位 {ln['median']}、四分位 {ln['p25']}～{ln['p75']}；分布 {ln['buckets']}",
          f"第一句句型：{st['opener']}",
          f"發文時段（台北，小時：則數）：{st['hour_taipei']}",
          f"有圖／影片比例：{st['with_media_ratio']}；帶網址比例：{st['has_url_ratio']}；媒體類型 {st['media']}",
          f"讚數：{'中位 ' + str(st['like_median']) if st['like_count_available'] else '別人的貼文 API 不給讚數／回覆數'}",
          f"帳號：不重複 {st['unique_accounts']} 個；出現最多的前 15 個帳號各有幾則（不記名）：{st['account_post_counts']}",
          f"各關鍵字筆數：{st['per_keyword']}", ""]
    return "\n".join(L) + "\n"
