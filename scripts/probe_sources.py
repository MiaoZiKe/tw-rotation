"""端點探測器：在 GitHub Actions 上實際打一輪候選端點，把回應存成 fixture。

為什麼要這個東西：本機（Claude 的容器）連不出去，官方端點只有在 Actions 上打得到。
規矩是 **沒有真的 fixture 就不准寫 parser** —— 之前所有資料源的欄位都是實測過才寫的，
重大訊息這條不能破例（猜欄位名 = 上線才發現全空）。

流程：
  1. 這支程式在 Actions 上跑 → 產出 docs/fixtures/<name>.json（含狀態碼、欄位、前幾筆樣本）
  2. 工作流把 fixture commit 回 repo
  3. Claude 讀 fixture → 寫 pipeline/sources/mops.py 與 TABLES 註冊 → 再上線

用法：
  python scripts/probe_sources.py material_news      # 只跑重大訊息這組
  python scripts/probe_sources.py --list             # 看有哪些組
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "fixtures"
TW = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; tw-rotation/1.0; +https://github.com/MiaoZiKe/tw-rotation)"
TIMEOUT = 25

# 每一組 = 一個題目下的所有候選端點。probe 只讀不寫，全部 GET/POST 一次就好。
PROBES: dict[str, list[dict]] = {
    "material_news": [
        # --- 先問「有沒有官方 OpenAPI」：把整份目錄抓回來，找帶「重大訊息」的路徑
        {"id": "twse_swagger", "url": "https://openapi.twse.com.tw/v1/swagger.json",
         "note": "證交所 OpenAPI 目錄，找 summary 帶『重大訊息』的 path"},
        {"id": "tpex_swagger", "url": "https://www.tpex.org.tw/openapi/swagger.json",
         "note": "櫃買 OpenAPI 目錄，同上"},
        # --- 幾個依命名規則推測的候選（t187ap04_L 系列是公開資訊觀測站的表號）
        {"id": "twse_t187ap04_L", "url": "https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
         "note": "推測：上市公司重大訊息"},
        {"id": "twse_t187ap04_O", "url": "https://openapi.twse.com.tw/v1/opendata/t187ap04_O",
         "note": "推測：上櫃版（若在證交所目錄下）"},
        {"id": "tpex_t187ap04_O", "url": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O",
         "note": "推測：櫃買重大訊息"},
        # --- FinMind：先看資料集清單裡有沒有公告類的
        {"id": "finmind_datalist", "url": "https://api.finmindtrade.com/api/v4/datalist",
         "note": "FinMind 有哪些 dataset（找 Announcement / News / Material）"},
    ],
    # ---- 台指期夜盤（Andy 2026-09-18 圖一：「台指期需要顯示夜盤」，
    #      2026-09-20 他又說：「台指期夜盤怎麼可能沒數據，幫我更新走勢圖以及 K 線上去」）
    #
    #      2026-09-19 第一輪探測的結論（docs/fixtures/taifex_night_probe.json）：
    #        getQuoteList（MarketType 0/1）→ 200，但**只回當下一筆快照**，沒有序列
    #        getQuoteDetail            → 200，一樣是快照
    #        getChartData1M            → 400，訊息是
    #          `Cannot deserialize instance of java.lang.String out of START_ARRAY token
    #           ... GetChartData1MReqDto["SymbolID"]`
    #      ★ 400 的內容才是重點：**這支端點存在**，它只是要一個 **字串**，
    #        而我們送了陣列 `{"SymbolID": ["TXFJ6-F"]}`。也就是說
    #        「夜盤沒有分時序列」這個結論是在還沒正確問過一次的情況下下的，不算數。
    #        這一輪就是把它問對：SymbolID 改成字串，夜盤用 `-M` 結尾的代號。
    #
    #      合約代號（2026-09-19 實測）：日盤 `TXFJ6-F`、夜盤 `TXFJ6-M`，
    #      第一筆 `TXF-S`／`TXF-P` 是臺指**現貨**參考列要跳過。
    #      月份代碼每個月都在換，所以這裡**不寫死** —— 用 `symbol_from`
    #      從上面那兩支 getQuoteList 的回應裡挑「成交量最大的那一支」（＝近月）。
    #      寫死的 default 只是整組都失敗時的退路。
    "taifex_night": [
        {"id": "taifex_quotelist_day", "method": "POST",
         "url": "https://mis.taifex.com.tw/futures/api/getQuoteList",
         "json": {"MarketType": "0", "SymbolType": "F", "KindID": "1", "CID": "TXF",
                  "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"},
         "note": "日盤報價清單：確認欄位名，並從這裡取出日盤近月的 SymbolID（-F）"},
        {"id": "taifex_quotelist_night", "method": "POST",
         "url": "https://mis.taifex.com.tw/futures/api/getQuoteList",
         "json": {"MarketType": "1", "SymbolType": "F", "KindID": "1", "CID": "TXF",
                  "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"},
         "note": "夜盤報價清單：MarketType=1，夜盤近月的 SymbolID 是 -M 結尾"},
        # ★ 這一支才是這輪的主角：SymbolID 送**字串**（上一輪送陣列被回 400）
        {"id": "taifex_chartdata_1m_night", "method": "POST",
         "url": "https://mis.taifex.com.tw/futures/api/getChartData1M",
         "json": {"SymbolID": "TXFJ6-M"},
         "symbol_from": {"probe": "taifex_quotelist_night", "suffix": "-M"},
         "series_stats": {"path": "RtData.Ticks", "session": "RtData.Info.Sessions",
                          "total": "RtData.Quote.CTotalVolume"},
         "note": "★夜盤 1 分鐘分時：SymbolID 改成字串（上一輪送陣列被回 400），代號取夜盤近月"},
        # 日盤同一支端點：拿得到的話可以跟證交所 futures_chart.txt 對帳，
        # 確認欄位意義（時間是不是台北、價是不是成交價、量是不是該分鐘口數）。
        {"id": "taifex_chartdata_1m_day", "method": "POST",
         "url": "https://mis.taifex.com.tw/futures/api/getChartData1M",
         "json": {"SymbolID": "TXFJ6-F"},
         "symbol_from": {"probe": "taifex_quotelist_day", "suffix": "-F"},
         "series_stats": {"path": "RtData.Ticks", "session": "RtData.Info.Sessions",
                          "total": "RtData.Quote.CTotalVolume"},
         "note": "日盤 1 分鐘分時：拿來跟證交所 futures_chart.txt 對帳，確認欄位口徑"},
        # 有些 Spring DTO 會要求帶日期或型態；最小請求被打回票時這一支才有診斷價值。
        {"id": "taifex_chartdata_1m_night_full", "method": "POST",
         "url": "https://mis.taifex.com.tw/futures/api/getChartData1M",
         "json": {"SymbolID": "TXFJ6-M", "MarketType": "1", "Interval": "1"},
         "symbol_from": {"probe": "taifex_quotelist_night", "suffix": "-M"},
         "note": "同上但多帶 MarketType/Interval：最小請求被打回票時，用它分辨是缺欄位還是不支援"},
        {"id": "taifex_quotedetail", "method": "POST",
         "url": "https://mis.taifex.com.tw/futures/api/getQuoteDetail",
         "json": {"SymbolID": "TXFJ6-M"},
         "symbol_from": {"probe": "taifex_quotelist_night", "suffix": "-M"},
         "note": "夜盤單一合約明細：上一輪送陣列也回 200，這裡改字串確認兩種都吃"},
        # ★ 萬一 getChartData1M 這條路走不通，要有第二個答案可以接下去，
        #   而不是再等一輪。行情看板自己的頁面會把它用到的端點寫在 JS 裡，
        #   把 `futures/api/xxx` 全部撈出來，下一步就有候選清單。
        {"id": "taifex_mis_page", "method": "GET",
         "url": "https://mis.taifex.com.tw/futures/",
         "grep": [r"/futures/api/[A-Za-z0-9_]+", r"[A-Za-z0-9_/.-]+\.js"],
         "note": "行情看板首頁：把它引用的 api 路徑與 JS 檔名全部撈出來當候選清單"},
    ],
    # ---- 金十數據（Andy 2026-09-21：「並且需要多一項 金十數據」）
    #
    #      金十數據 jin10.com 是中國的即時財經快訊站，以總經／央行／商品／地緣政治的
    #      即時快訊為主 —— 這個站現在的「總經」格正好缺這一塊。
    #
    #      ★★ 這一組**先問合規，不是先問欄位**。順序是刻意的：前三支是 robots.txt
    #      與版權／免責頁，後面才是資料端點。理由：
    #        1. CLAUDE.md 第一條紅線就是「只用免費且合規的來源」，
    #           `www.twse.com.tw/rwd/...` 被永久封殺就是因為使用條款，不是因為技術。
    #        2. 2026-09-21 用 WebSearch 查到的二手說法是「金十的版權聲明寫
    #           『未經授權，不得將本站的資訊、數據、行情用於 AI 訓練或其他商業用途』」，
    #           而且開放平台（open.jin10.com）是**付費**的，只給 15 天試用。
    #           但那是搜尋摘要，不是原文 —— 這個 repo 的規矩是不拿二手摘要當結論，
    #           所以這裡把原文抓回來，讓人讀了再決定。
    #        3. Claude 的容器打不到 jin10（出口代理對 jin10.com / www.jin10.com /
    #           flash-api.jin10.com 一律 403），所以只有 Actions 問得到。
    #
    #      ★ 刻意**不帶** `x-app-id` / `x-version`：網路上流傳的那組值
    #      （RSSHub 寫死的 `bVBF4FyRTn5NJF5n`）是從官網前端逆向出來的 app 憑證，
    #      帶著它去打等於繞過反爬、冒用它的用戶端身分 —— 那是 CLAUDE.md 明令禁止的事。
    #      這裡就是要看「**不作假、規規矩矩地問**」拿不拿得到；
    #      拿不到（401/403/502）本身就是答案：這條路對我們是關的。
    "jin10": [
        {"id": "jin10_robots", "method": "GET", "url": "https://www.jin10.com/robots.txt",
         "note": "★先看這個：robots.txt 有沒有禁止抓取。整份都會存進 sample_text"},
        {"id": "jin10_copyright", "method": "GET",
         "url": "https://www.jin10.com/about/index.html",
         "grep": [r"未經[^，。；]{0,40}", r"未经[^，。；]{0,40}", r"禁止[^，。；]{0,40}",
                  r"不得[^，。；]{0,40}", r"商業用途|商业用途|爬蟲|爬虫|AI 訓練|AI训练"],
         "note": "★版權／免責頁：把「未經」「不得」「禁止」的句子整句撈出來，原文說了算"},
        {"id": "jin10_open_platform", "method": "GET", "url": "https://open.jin10.com/",
         "grep": [r"免費|免费|試用|试用|價格|价格|收費|收费|元/月|API"],
         "note": "官方開放平台：確認是不是付費、有沒有免費層。有官方授權的路就走官方的"},
        # --- 以下三支才是資料端點，而且一律不帶偽造的用戶端標頭
        {"id": "jin10_flash_newest_js", "method": "GET",
         "url": "https://www.jin10.com/flash_newest.js",
         "grep": [r"\"id\":\"[0-9a-zA-Z-]+\"", r"\"time\":\"[^\"]+\"", r"\"type\":[0-9]+"],
         "note": "官網首頁自己會載的快訊 JS（公開靜態檔，不需要任何標頭）：看結構與筆數"},
        {"id": "jin10_flash_api_plain", "method": "GET",
         "url": "https://flash-api.jin10.com/get_flash_list?channel=-8200&vip=1",
         "note": "★不帶 x-app-id 直接問：拿得到就代表它是公開的；被擋就代表這條路要繞反爬，不走"},
        {"id": "jin10_rss_try", "method": "GET", "url": "https://xnews.jin10.com/rss.xml",
         "note": "有沒有官方 RSS。有的話最乾淨（RSS 本來就是給人訂閱的），沒有就記 404"},
    ],
}


# 序列型的回應動輒好幾百筆（夜盤 14 小時的 1 分 K 就有 ~840 筆）。
# 整份存進 fixture 會肥到沒人想打開，但「只留前三筆」又看不出尾端長什麼樣，
# 所以一律留頭 5 筆 ＋ 尾 2 筆，中間換成一句「…（省略 N 筆）」。
SAMPLE_HEAD, SAMPLE_TAIL = 5, 2


def shrink(v, depth: int = 0):
    """把回應裡的長串截短，但把「原本有幾筆」記在截斷標記裡（判斷夠不夠用就靠這個數字）。"""
    if depth > 6:
        return "…（太深，略）"
    if isinstance(v, list):
        if len(v) > SAMPLE_HEAD + SAMPLE_TAIL + 1:
            head = [shrink(x, depth + 1) for x in v[:SAMPLE_HEAD]]
            tail = [shrink(x, depth + 1) for x in v[-SAMPLE_TAIL:]]
            return head + [f"…（中間省略 {len(v) - SAMPLE_HEAD - SAMPLE_TAIL} 筆，整串共 {len(v)} 筆）"] + tail
        return [shrink(x, depth + 1) for x in v]
    if isinstance(v, dict):
        return {k: shrink(x, depth + 1) for k, x in v.items()}
    if isinstance(v, str) and len(v) > 400:
        return v[:400] + f"…（共 {len(v)} 字）"
    return v


def _dig(obj, path: str):
    """`"RtData.Ticks"` → 一路往下取值；中途取不到就回 None。"""
    cur = obj
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _mins(t: str, start_min: int) -> int | None:
    """期交所分時的時間欄位 `HHMMSS` → 台北分鐘數；跨午夜的往後加 1440。

    ★ 為什麼要寫得這麼囉嗦：2026-09-20 的夜盤 fixture 裡出現了 `"046000"` ——
    硬切 HHMMSS 會得到 **04:60:00**，不是合法時間。CLAUDE.md 記過同一類坑
    （重大訊息的 `70003` 要補零成 `07:00:03`）：時間格式看起來單純，每個來源都有自己的怪癖。
    這裡把 `MM=60` 當成「進位到下一個小時」處理，並把它算進 `weird` 讓人看見，
    而不是默默丟掉 —— 探測腳本的工作是把事實攤開，不是替上游圓場。
    """
    s = str(t).strip()
    if not s.isdigit() or len(s) not in (5, 6):
        return None
    s = s.zfill(6)
    h, mi, se = int(s[0:2]), int(s[2:4]), int(s[4:6])
    m = h * 60 + mi + (1 if se >= 60 else 0)
    if mi >= 60:              # 04:60 → 05:00
        m = h * 60 + 60
    if m < start_min:         # 跨午夜（夜盤 15:00 開始、翌日 05:00 結束）
        m += 24 * 60
    return m


def series_stats(j: dict, spec: dict) -> dict:
    """把整串序列（**截短之前**）的事實算出來，一次回答「這個時間格式有沒有坑」。

    為什麼非得在這裡算：fixture 為了不肥會把中間截掉（`shrink()`），
    所以「822 筆裡面有幾個怪時間、缺哪幾分鐘」事後從 fixture 是**數不出來**的。
    2026-09-20 就是這樣：拿回來的 fixture 只有頭 5 尾 2，
    看到 `046000` 卻沒辦法確認它是偶發還是每個整點都有。這支就是為了不要再發生一次。
    """
    rows = _dig(j, spec["path"])
    if not isinstance(rows, list) or not rows:
        return {"n": 0, "note": "序列是空的或路徑不對"}
    sess = _dig(j, spec.get("session") or "") or []
    st = str((sess[0] or {}).get("Start") or "0000") if sess else "0000"
    en = str((sess[0] or {}).get("End") or "0000") if sess else "0000"
    start_min = int(st[:2]) * 60 + int(st[2:4])
    end_min = int(en[:2]) * 60 + int(en[2:4])
    if end_min <= start_min:
        end_min += 24 * 60                      # 夜盤跨午夜
    ts = [str(r[0]) for r in rows if isinstance(r, (list, tuple)) and r]
    weird = {}                                   # 不合法的 HHMMSS → 出現幾次、在第幾筆
    mins = []
    for i, t in enumerate(ts):
        s6 = t.zfill(6)
        if len(s6) != 6 or not s6.isdigit() or int(s6[2:4]) >= 60 or int(s6[4:6]) != 0 \
           or int(s6[0:2]) >= 24:
            w = weird.setdefault(t, {"n": 0, "at": []})
            w["n"] += 1
            if len(w["at"]) < 5:
                w["at"].append(i)
        m = _mins(t, start_min)
        if m is not None:
            mins.append(m)
    grid = set(range(start_min + 1, end_min + 1))     # 第一根是「開盤後第一分鐘」
    got = set(mins)
    dup = sorted({m for m in mins if mins.count(m) > 1}) if len(mins) != len(got) else []
    vol = 0.0
    for r in rows:
        try:
            vol += float(r[5])
        except (TypeError, ValueError, IndexError):
            pass
    out = {
        "n": len(rows),
        "session": {"start": st, "end": en, "grid_minutes": len(grid)},
        "first": ts[0] if ts else None, "last": ts[-1] if ts else None,
        # ★ 這三個就是「時間格式有沒有坑」的答案
        "weird_times": weird,
        "duplicate_minutes": dup[:40],
        "missing_minutes": sorted(grid - got)[:60],
        "missing_n": len(grid - got),
        "monotonic": all(mins[i] <= mins[i + 1] for i in range(len(mins) - 1)),
        "volume_sum": vol,
    }
    tot = _dig(j, spec.get("total") or "")
    if tot not in (None, ""):
        try:
            out["quote_total_volume"] = float(tot)
            out["volume_matches_quote"] = abs(vol - float(tot)) < 1e-6
        except (TypeError, ValueError):
            pass
    return out


def pick_symbol(rec: dict, suffix: str) -> str | None:
    """從 getQuoteList 的回應裡挑近月合約代號。

    近月＝跳過臺指**現貨**參考列（`TXF-S` / `TXF-P`，代號裡沒有月份）之後，
    `CTotalVolume` 最大的那一支。不寫死月份代碼的理由很單純：
    每個月都在換，寫死的探測腳本下個月就問錯合約，回空還會被誤判成「沒有這個端點」。
    """
    try:
        lst = ((rec.get("sample") or {}).get("RtData") or {}).get("QuoteList") or []
    except Exception:  # noqa: BLE001
        return None
    best, best_v = None, -1.0
    for q in lst:
        if not isinstance(q, dict):
            continue
        sid = str(q.get("SymbolID") or "")
        # 代號長這樣：TXF + 月份碼 + 年 + 時段（-F 日盤／-M 夜盤）；
        # `TXF-S` / `TXF-P` 中間沒有月份，那是臺指**現貨**參考列，不是合約。
        if not sid.endswith(suffix) or sid.startswith("TXF-"):
            continue
        try:
            vol = float(q.get("CTotalVolume") or 0)
        except (TypeError, ValueError):
            vol = 0.0
        if vol > best_v:
            best, best_v = sid, vol
    return best


def one(p: dict, prev: dict | None = None) -> dict:
    """打一個端點，把「夠不夠寫 parser」需要知道的東西全部記下來。

    `prev` 是同一組裡**前面已經打完**的結果（id → rec）。有 `symbol_from` 的探測
    會從那裡撈出當下真正的近月合約代號，取代寫死的預設值。
    """
    rec: dict = {"id": p["id"], "url": p["url"], "note": p.get("note", ""),
                 "method": p.get("method", "GET"), "probed_at": datetime.now(TW).isoformat(timespec="seconds")}
    body_json = p.get("json")
    sf = p.get("symbol_from")
    if sf and isinstance(body_json, dict):
        body_json = dict(body_json)
        got = pick_symbol((prev or {}).get(sf["probe"]) or {}, sf["suffix"])
        # 撈不到就沿用寫死的預設值，並記下來 —— 不然事後看 fixture 會分不清
        # 「問錯合約」和「端點真的沒資料」。
        rec["symbol_used"] = got or body_json.get("SymbolID")
        rec["symbol_source"] = "上一支回應" if got else "寫死的預設值（沒撈到）"
        body_json["SymbolID"] = rec["symbol_used"]
    rec["req"] = body_json if body_json is not None else p.get("data")
    t0 = time.time()
    try:
        hdr = {"User-Agent": UA, "Accept": "application/json, */*"}
        # 期交所那幾支要帶 Referer，不帶會被擋（跟 mis.twse 同一個脾氣）
        if "taifex" in p["url"]:
            hdr["Referer"] = "https://mis.taifex.com.tw/futures/"
            hdr["Origin"] = "https://mis.taifex.com.tw"
        r = requests.request(rec["method"], p["url"], headers=hdr,
                             data=p.get("data"), json=body_json, timeout=TIMEOUT)
        rec["status"] = r.status_code
        rec["elapsed_ms"] = int((time.time() - t0) * 1000)
        rec["content_type"] = r.headers.get("Content-Type", "")
        rec["bytes"] = len(r.content)
        body = r.text
        try:
            j = r.json()
        except Exception:
            j = None
        if j is None:
            rec["kind"] = "text"
            rec["sample_text"] = body[:1500]
            # HTML/JS 這種「不是資料、是線索」的回應：把要找的東西用正規式撈出來，
            # 不然 1500 字的截斷幾乎一定切在沒用的地方。
            for pat in (p.get("grep") or []):
                hits = sorted(set(re.findall(pat, body)))
                rec.setdefault("grep", {})[pat] = hits[:80]
        elif isinstance(j, list):
            rec["kind"] = "list"
            rec["n"] = len(j)
            rec["fields"] = sorted(j[0].keys()) if j and isinstance(j[0], dict) else None
            # 最外層是陣列的來源（TWSE opendata 那一類）照舊只留前三筆 ——
            # 那種回應每一筆都長一樣，留三筆就夠看欄位；shrink 是給**巢狀的長序列**用的。
            rec["sample"] = shrink(j[:3])
        elif isinstance(j, dict):
            rec["kind"] = "dict"
            rec["keys"] = sorted(j.keys())[:60]
            # swagger 目錄：只留下跟重大訊息／公告有關的 path，整份存下來太肥
            if "paths" in j:
                hits = {}
                for path, spec in (j.get("paths") or {}).items():
                    blob = json.dumps(spec, ensure_ascii=False)
                    if any(k in blob for k in ("重大訊息", "重大", "公告", "訊息", "News", "Announcement")):
                        get = (spec or {}).get("get") or {}
                        hits[path] = {"summary": get.get("summary"), "description": (get.get("description") or "")[:200]}
                rec["matched_paths"] = hits
                rec["all_paths_n"] = len(j.get("paths") or {})
            else:
                # 整份存下來（經過 shrink 截短）—— 序列型回應真正要看的是
                # 「一共幾筆、每一筆有哪些欄位、尾端長什麼樣」，只留前 8 個 key 會漏掉。
                rec["sample"] = shrink({k: j[k] for k in list(j)[:12]})
                # 序列在哪一層、有幾筆：直接算給人看，省得自己數
                seqs = {}

                def _walk(node, path):
                    if isinstance(node, dict):
                        for k, v in node.items():
                            _walk(v, f"{path}.{k}" if path else k)
                    elif isinstance(node, list) and len(node) > 3:
                        seqs[path] = {"n": len(node),
                                      "fields": sorted(node[0].keys()) if isinstance(node[0], dict) else None}

                _walk(j, "")
                if seqs:
                    rec["sequences"] = seqs
                # ★ 一定要在 shrink 之前算：截短之後就數不出來了
                if p.get("series_stats"):
                    try:
                        rec["series_stats"] = series_stats(j, p["series_stats"])
                    except Exception as exc:  # noqa: BLE001
                        rec["series_stats"] = {"error": f"{type(exc).__name__}: {exc}"}
    except Exception as e:  # 連不上也是結果，要記下來
        rec["status"] = None
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    return rec


def run(name: str) -> Path:
    probes = PROBES[name]
    # 一支一支照順序打：後面的探測要用前面撈到的合約代號（symbol_from）
    done: dict[str, dict] = {}
    results = []
    for p in probes:
        rec = one(p, done)
        done[rec["id"]] = rec
        results.append(rec)
    out = {"probe": name, "at": datetime.now(TW).isoformat(timespec="seconds"),
           "results": results}
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{name}_probe.json"
    f.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in out["results"]:
        mark = "OK " if r.get("status") == 200 else "-- "
        extra = ""
        if r.get("matched_paths") is not None:
            extra = f" 命中 {len(r['matched_paths'])} 個路徑（全部 {r.get('all_paths_n')} 個）"
        elif r.get("series_stats"):
            st2 = r["series_stats"]
            extra = (f" {st2.get('n')} 筆 {st2.get('first')}~{st2.get('last')}"
                     f" 缺 {st2.get('missing_n')} 分鐘"
                     f" 怪時間 {list((st2.get('weird_times') or {}).keys())[:4]}"
                     f" 量對帳 {st2.get('volume_matches_quote')}")
        elif r.get("sequences"):
            extra = " 序列：" + "、".join(f"{k} {v['n']} 筆" for k, v in list(r["sequences"].items())[:3])
        elif r.get("grep"):
            extra = " 命中：" + "、".join(f"{len(v)} 個" for v in r["grep"].values())
        elif r.get("kind") == "list":
            extra = f" {r.get('n')} 筆，欄位 {r.get('fields')}"
        sym = f" [{r['symbol_used']}]" if r.get("symbol_used") else ""
        print(f"{mark}{r['id']:30s} {r.get('status')} {r.get('bytes', 0)}B{sym}{extra}"
              f"{'  ' + r['error'] if r.get('error') else ''}")
    try:
        print(f"\n寫到 {f.relative_to(ROOT)}")
    except ValueError:       # 測試會把輸出目錄換掉，印絕對路徑就好
        print(f"\n寫到 {f}")
    return f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("probe", nargs="?", default="material_news")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, v in PROBES.items():
            print(f"{k}：{len(v)} 個候選端點")
        sys.exit(0)
    if a.probe not in PROBES:
        print(f"沒有這組：{a.probe}（有 {', '.join(PROBES)}）")
        sys.exit(1)
    run(a.probe)
