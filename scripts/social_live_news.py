"""盤中／盤後貼文的「📰 新聞焦點」段（2026-10-29 Andy：「盤前、盤中、盤後……除了基本的盤面解讀之外，
還需要搭配當下的一些新聞消息，三到五個主題」）。

· 挑法沿用盤前（scripts/social_premarket.py 的 pick_news：相關度 → 幾家媒體報導 → 幾篇），每則一行「短標題：一句描述」
  （_clause／_desc，跟盤前「📌 今日焦點」同一套）。
· 時間窗：盤中＝當天 07:30 到發文當下；盤後＝當天 11:30 到發文當下（NEWS_FROM）。
· 排除：盤前 SKIP_RE（喊盤、權證…）＋這裡的 LIVE_SKIP_RE（基金募集、講座、抽獎這類業配／活動）；
  同一天盤前已用過的（site/articles/premarket.json 當天那筆，網址或標題相同、或標題很像）不再用；相似標題去重。
· 資料：資料湖 data/news（跟盤前同一個讀法）；workflow 另加 --fresh-news 時當場再抓一次鉅亨／科技新報／聯合
  （資料湖的新聞輪是 09:07、12:07，12:00 的盤中只讀湖會缺 09:00 之後的新聞；只併進記憶體，不寫湖）。
· 至少 3 則、最多 5 則；不足 3 則照發、有幾則放幾則（0 則就不放這段），呼叫端寫 alert，絕不擋整篇。
"""
from __future__ import annotations

import json
import re
import sys
import threading
from datetime import datetime
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

TPE = ZoneInfo("Asia/Taipei")
NEWS_FROM = {"intraday": dtime(7, 30), "close": dtime(11, 30)}
SECTION = "📰 新聞焦點："
MIN_N, MAX_N = 3, 5
# 業配／活動：基金或 ETF 募集、講座、說明會、抽獎、贈品、課程、直播、徵才、贊助（盤前 SKIP_RE 之外再多排這些）
LIVE_SKIP_RE = re.compile(r"募集|開募|限時|講座|說明會|研討會|座談|論壇|抽獎|贈品|好禮|贈送|課程|直播|徵才|贊助|廣編|業配|"
                          r"活動開跑|系列活動|活動登場|借鏡|利器|報名|優惠|折扣|開箱|懶人包|還能追|能買嗎|怎麼買|怎麼選|如何透過")
# 摘要開頭／結尾只是在交代消息來源的那一段（「根據外媒…報導」「據媒體統計」），不當描述
ATTR_RE = re.compile(r"^(根據|據|依據|綜合|外媒|知情人士|消息人士)")


def window(kind: str, now: datetime) -> tuple[datetime, datetime]:
    now = now.astimezone(TPE) if now.tzinfo else now.replace(tzinfo=TPE)
    return datetime.combine(now.date(), NEWS_FROM[kind], tzinfo=TPE), now


def _bigrams(t: str) -> set[str]:
    t = re.sub(r"[\s　，。！？、：；「」『』（）()《》〈〉【】\[\]|｜…\-—–,.!?:;'\"]+", "", str(t)).lower()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def similar(a: str, b: str, thr: float = 0.5) -> bool:
    """標題相似：兩字一組的重疊比例（對短的那則算）≥ thr 就當成同一則新聞（不同媒體同一件事的標題）。"""
    x, y = _bigrams(a), _bigrams(b)
    if not x or not y:
        return False
    return len(x & y) / min(len(x), len(y)) >= thr


def premarket_used(day: str, path: Path | None = None) -> list[dict]:
    """同一天盤前已用過的新聞（盤前工作流寫進 main 的 site/articles/premarket.json）；讀不到就回空（靠時間窗自然區隔）。"""
    p = path or ROOT / "site" / "articles" / "premarket.json"
    try:
        d = json.loads(Path(p).read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    for x in d.get("days") or []:
        if str(x.get("date")) == day:
            return [{"title": str(i.get("title") or ""), "url": str(i.get("url") or "")} for i in x.get("items") or []]
    return []


def load_news(fresh: bool = False, timeout_s: float = 60.0, log=print):
    """資料湖 news；fresh＝再當場抓一次（逾時或失敗就只用湖裡的，不擋發文）。"""
    import pandas as pd
    from pipeline.util import store
    try:
        lake = store.read("news")
    except Exception as exc:  # noqa: BLE001
        log(f"  ⚠ 讀不到資料湖 news：{str(exc)[:100]}")
        lake = pd.DataFrame()
    if not fresh:
        return lake
    box: dict = {}

    def run():
        try:
            from pipeline.sources import news as N
            box["df"] = N.collect()
        except Exception as exc:  # noqa: BLE001
            box["err"] = str(exc)[:100]
    th = threading.Thread(target=run, daemon=True)
    th.start()
    th.join(timeout_s)
    live = box.get("df")
    if th.is_alive() or live is None or live.empty:
        log(f"  ⚠ 當場抓新聞沒拿到（{'逾時' if th.is_alive() else box.get('err') or '空的'}）→ 只用資料湖")
        return lake
    log(f"  當場抓新聞 {len(live)} 則，併進資料湖的 {len(lake)} 則")
    both = pd.concat([lake, live], ignore_index=True)
    return both.drop_duplicates("news_id", keep="last") if "news_id" in both.columns else both


def pick(news, start: datetime, end: datetime, used: list[dict] | None = None, pool: int = 15) -> list[dict]:
    """時間窗內、排掉業配與盤前用過的，照盤前的挑法排好，回候選清單（最多 pool 則、已去掉相似標題）。"""
    import social_premarket as sp
    if news is None or getattr(news, "empty", True):
        return []
    used = used or []
    urls = {u["url"] for u in used if u.get("url")}
    titles = [u["title"] for u in used if u.get("title")]
    df = news[~news["title"].astype(str).str.contains(LIVE_SKIP_RE)]
    if "url" in df.columns and urls:
        df = df[~df["url"].astype(str).isin(urls)]
    df = df[~df["title"].astype(str).map(lambda t: any(similar(t, u) for u in titles))]
    out: list[dict] = []
    for it in sp.pick_news(df, start, end, n=pool):
        if any(similar(it["title"], o["title"]) for o in out):
            continue
        out.append(it)
    return out


def _d(n: dict, dl: int, c: str = "") -> str:
    """描述＝摘要第一句（同盤前 _desc）；摘要是空的（聯合新聞網、部分鉅亨），改用標題短句之後的其餘部分
    （「SK海力士財報出爐！第三季營益衝83.3兆韓元超預期」→ 短標題「SK海力士財報出爐」＋描述「第三季營益衝83.3兆韓元超預期」）。"""
    import social_premarket as sp
    d = sp._desc(strip_attr(n.get("summary") or ""), dl)
    if not d and c:
        rest = str(n["title"]).strip()
        rest = rest[len(c.rstrip("？")):] if rest.startswith(c.rstrip("？")) else ""
        d = sp._desc(re.sub(r"^[\s！!？?，,：:；;。　｜|]+", "", rest), dl)
    while d and re.search(r"[，,、；]", d) and ATTR_RE.match(re.split(r"[，,、；]", d)[-1].strip()):      # 截短後尾巴剩「據媒體…」
        d = re.split(r"[，,、；](?=[^，,、；]*$)", d)[0].strip()
    return d


def lines(items: list[dict], kn: int = MAX_N, tl: int = 30, dl: int = 40) -> list[str]:
    """每則一行「・短標題：一句描述」（跟盤前今日焦點同格式），照相關度順序；短標題取不出來的那則跳過、由後面的候選遞補。"""
    out: list[str] = []
    for n in items:
        if len(out) >= kn:
            break
        c = short_title(n["title"], tl)
        if not c:
            continue
        d = _d(n, dl, c)
        out.append(f"・{c}：{d}" if d and d != c else f"・{c}")
    return [SECTION] + out if out else []


def short_title(t: str, tl: int) -> str:
    """短標題：同盤前 _clause（到「！，：。」為止，超過 tl 字不用）；但「中文 English 中文」這種中英夾雜的空白不是斷句，
    不可以照空白切（10-29 實例：「招聘工程師使 OpenAI 採購…」被切成「招聘工程師使」）→ 這種取不出就跳過，由下一則遞補。"""
    import social_premarket as sp
    c = sp._clause(t, tl)
    m = re.match(r"(.+?)([！!？?，,：:；;。　\n]| {2,}|$)", t.strip())
    whole = m.group(1).strip() if m else ""
    core = c.rstrip("？")
    if c and len(whole) > len(core) and whole.startswith(core):      # 是照空白切出來的
        nxt = whole[len(core):].lstrip()[:1]
        if re.match(r"[A-Za-z0-9]", nxt) or re.search(r"[A-Za-z0-9]$", core):
            return ""
    return c


def strip_attr(summary: str) -> str:
    """拿掉摘要第一句裡只在交代來源的分句（開頭「根據外媒…」、結尾「據媒體…統計」），留下真正的內容。"""
    t = str(summary or "")
    m = re.search(r"[\n。]", t)
    first, rest = (t[:m.start()], t[m.start():]) if m else (t, "")
    parts = re.split(r"(?<=[，,])", first)
    while len(parts) > 1 and ATTR_RE.match(parts[0].strip()):
        parts = parts[1:]
    while len(parts) > 1 and ATTR_RE.match(parts[-1].strip()):
        parts = parts[:-1]
    if len(parts) == 1 and ATTR_RE.match(parts[0].strip()):
        return ""
    first = "".join(parts).strip().rstrip("，,")
    return first + rest


LEVELS = ((30, 40), (30, 32), (30, 26), (26, 20), (26, 0), (22, 0))


def merge(text: str, items: list[dict], hashtag: str, max_len: int) -> tuple[str, str, int]:
    """把新聞段塞進主文（盤面解讀之後、hashtag 之前）；放不下就整段改放回覆串。回 (主文, 回覆, 則數)。
    先縮描述長度（則數不減）；最短的版本主文仍超過 max_len 才移到回覆（回覆用最完整、放得下的版本）。"""
    full = lines(items)
    n = len(full) - 1 if full else 0
    if not n:
        return text, "", 0
    L = text.split("\n")
    at = L.index(hashtag) if hashtag in L else next((i for i, x in enumerate(L) if x.startswith("👉")), len(L))
    for tl, dl in LEVELS:
        sec = lines(items, MAX_N, tl, dl)
        if len(sec) - 1 < n:      # 縮短標題後取不出原本那幾則 → 不用這一級
            continue
        t = "\n".join(L[:at] + sec + L[at:])
        if len(t) <= max_len:
            return t, "", n
    for tl, dl in LEVELS:
        r = "\n".join(lines(items, MAX_N, tl, dl))
        if len(r) <= max_len:
            return text, r, len(lines(items, MAX_N, tl, dl)) - 1
    return text, "\n".join(lines(items, MAX_N, 22, 0)), n


def for_post(kind: str, text: str, now: datetime, hashtag: str, max_len: int, fresh: bool = False, log=print,
             news=None, used_path: Path | None = None) -> dict:
    """給 social_snap.main 用：回 {"text", "reply", "n", "alert"}。任何錯誤都只回原文＋alert，不擋發文。"""
    res = {"text": text, "reply": "", "n": 0, "alert": ""}
    if kind not in NEWS_FROM:
        return res
    start, end = window(kind, now)
    try:
        df = news if news is not None else load_news(fresh, log=log)
        used = premarket_used(end.date().isoformat(), used_path)
        items = pick(df, start, end, used)
        res["text"], res["reply"], res["n"] = merge(text, items, hashtag, max_len)
    except Exception as exc:  # noqa: BLE001
        res["alert"] = f"{kind} 貼文的新聞焦點產生失敗（{str(exc)[:100]}），這篇照發、少了新聞那段。"
        return res
    log(f"新聞焦點：{start:%H:%M}～{end:%H:%M} 用 {res['n']} 則（排掉盤前已用 {len(used)} 則）"
        + ("，主文放不下 → 改放回覆串" if res["reply"] else ""))
    if res["n"] < MIN_N:
        res["alert"] = (f"{kind} 貼文的新聞焦點只有 {res['n']} 則（時間窗 {start:%m/%d %H:%M}～{end:%H:%M}，至少要 {MIN_N} 則），"
                        + ("這篇照發、不放新聞那段。" if not res["n"] else "這篇照發、新聞段少幾則。"))
    return res
