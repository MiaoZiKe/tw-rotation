"""交付護欄：擋住「宣稱完成、實際上是壞的」。

為什麼要有這一整個檔（Andy 2026-09-19：「需要在完成項目多驗證機制」）
====================================================================
2026-09-19 這一天，光是回頭稽核就抓到四件「標 ✅ 但其實不能用」的事：

  1. 第 17 項「族群頁下鑽」標 ✅ —— 實際上 35 個法定產業別裡有 **34 個是空頁**
     （hash 沒 decodeURIComponent，中文 id 永遠比不中）。
  2. 第 41 項「只看低於族群中位」標 ✅ —— 實際上**從上線第一天就永遠篩出 0 筆**
     （後端回比值、前端判負數）。
  3. 第 8／2／C5 項標 ✅ —— 實際上只有 400 檔左右有資料，其餘 1,900 多檔是空的
     （回補被 LIMIT=500 封死）。
  4. 每日管線連續兩輪 failure、網站在週末與盤前根本不更新 —— 沒有任何關卡發現
     （`return 0 if trade_date else 1` 對 news phase 永遠成立）。

四件事的共通點：**「功能寫好了」跟「使用者真的用得到」之間沒有任何機器檢查。**
pytest 驗演算法、_preview 驗版面、_uitest 驗互動 —— 三道關卡在
「資料到底有沒有」「宣稱完成的東西是不是真的成立」這件事上是全盲的。

這個檔就是補那個盲區。原則：
  · 只放**能用機器判定**的條件，不放「看起來對不對」那種
  · 全部寫成**棘輪**（只准變好），這樣現況不會立刻變紅，但倒退一定會被擋
  · 每一條都要說明「壞掉的時候使用者會看到什麼」，不然下一個人不知道為什麼要守
"""
from __future__ import annotations

import glob
import json

import pytest
import yaml

from pipeline import config

# --------------------------------------------------------------------------
# 資料覆蓋率棘輪
# --------------------------------------------------------------------------
# 這幾個數字是 2026-09-19 的實測值，**刻意貼著現況**訂 —— 加進來的當下不會紅，
# 但只要回補倒退、或哪天有人把 LIMIT 改回 500，它就會紅。
#
# ★ 為什麼門檻訂得比現況低一點（留 5% 緩衝）：
#   資料湖每天都在動，日線分割會跨年、停牌股會進出，卡太死會變成每天都要來調數字的
#   假紅燈 —— 那種棘輪最後一定會被當成雜訊關掉。
#
# ★ 這些數字現在很難看（2,336 檔裡只有 392 檔有 250 天以上的價量）。
#   **不要把它當成「標準」**，它是「今天的地板」。回補跑順之後要往上調。
COVERAGE_FLOOR = {
    "price_daily_250d": 370,      # 實測 392：能算 MA120／季節性的檔數
    "revenue_13m": 460,           # 實測 488：能算營收 YoY 的檔數
    "financial_4q": 470,          # 實測 503：能算 TTM EPS／本益比的檔數
}


def _price_depth() -> dict[str, int]:
    import pandas as pd

    files = sorted(glob.glob(str(config.DATA / "price_daily" / "year=*" / "part.parquet")))
    if not files:
        pytest.skip("沒有 data/price_daily，跳過（這是資料護欄，不是邏輯測試）")
    px = pd.concat([pd.read_parquet(f, columns=["date", "code"]) for f in files], ignore_index=True)
    n = px.groupby("code").size()
    return {"ge250": int((n >= 250).sum()), "total": int(len(n))}


def test_價量深度沒有倒退():
    """壞掉的時候使用者會看到什麼：個股頁的 MA120、季節性、多週期判讀整段消失，
    頁面退成「歷史價量還在回補」。2026-09-19 有 1,933 個頁面長這樣。"""
    d = _price_depth()
    assert d["ge250"] >= COVERAGE_FLOOR["price_daily_250d"], (
        f"能算 MA120 的檔數掉到 {d['ge250']}（地板 {COVERAGE_FLOOR['price_daily_250d']}，"
        f"全市場 {d['total']} 檔）。回補是不是又被擋住了？"
        f"先看 data/_state/backfill_progress.json 的 complete 旗標與 backfill.yml 的 LIMIT"
    )


def _table_codes(table: str, col: str, need: int) -> int:
    import pandas as pd

    files = sorted(glob.glob(str(config.DATA / table / "**" / "*.parquet"), recursive=True))
    if not files:
        pytest.skip(f"沒有 data/{table}，跳過")
    df = pd.concat([pd.read_parquet(f, columns=["code", col]) for f in files], ignore_index=True)
    n = df.drop_duplicates(["code", col]).groupby("code").size()
    return int((n >= need).sum())


def test_月營收深度沒有倒退():
    """壞掉的時候：個股頁與候選名單的「營收 YoY」「連增月」整欄變成「—」。"""
    got = _table_codes("revenue_monthly", "ym", 13)
    assert got >= COVERAGE_FLOOR["revenue_13m"], (
        f"能算營收 YoY（≥13 個月）的檔數掉到 {got}（地板 {COVERAGE_FLOOR['revenue_13m']}）"
    )


# --------------------------------------------------------------------------
# 「宣稱完成」與「可驗證」的對應
# --------------------------------------------------------------------------
# 今天抓到的第 17、41 項都是「功能在、但資料或口徑讓它永遠沒有輸出」。
# 這一段用**資料本身**去確認那些功能有東西可吃 —— 不依賴前端跑起來。

def test_每個法定產業別族群都有成分股():
    """第 17 項。壞掉的時候：點「半導體業」「金融保險」進去看到「0 檔 · 沒有符合的股票」。
    2026-09-19 因為 hash 沒解碼，35 個裡有 34 個長這樣。
    這裡驗的是**資料**這一側 —— 前端那一側由 _uitest 的 t_group_pages 驗，兩邊都要有。"""
    p = config.SITE / "data" / "groups_detail.json"
    if not p.exists():
        pytest.skip("還沒產生 site/data/groups_detail.json（先跑 build_payload）")
    d = json.loads(p.read_text(encoding="utf-8"))
    g = d.get("groups", d)
    ind = {k: v for k, v in g.items() if k.startswith("ind_")}
    assert len(ind) >= 20, f"法定產業別只有 {len(ind)} 個，資料本身就不對"
    empty = [k for k, v in ind.items() if not (v.get("members") or v.get("codes") or [])]
    assert not empty, f"這些法定產業別一檔成分股都沒有：{empty[:6]}"


def test_低於族群中位篩得出東西():
    """第 41 項。壞掉的時候：勾「只看低於族群中位」→ 0 筆，畫面寫「沒有符合條件的股票」，
    看起來像今天剛好沒有便宜股，其實是那個勾選框從來沒作用過。

    根因是 vs_median 的口徑：後端回**比值**、前端判**負數**，而本益比恆正。
    這一條直接釘住「一定要有負的」—— 只要有人把口徑改回比值，它就會紅。"""
    p = config.SITE / "data" / "fundamental.json"
    if not p.exists():
        pytest.skip("還沒產生 site/data/fundamental.json")
    d = json.loads(p.read_text(encoding="utf-8"))
    rows = d["rows"] if isinstance(d, dict) and "rows" in d else (
        list(d.values()) if isinstance(d, dict) else d)
    vs = [r.get("vs_median") for r in rows if isinstance(r, dict) and r.get("vs_median") is not None]
    assert len(vs) >= 100, f"有 vs_median 的只有 {len(vs)} 筆，樣本太少"
    neg = sum(1 for v in vs if v < 0)
    assert neg > 0, (
        "沒有任何一檔的 vs_median 是負的 —— 那表示口徑又變回『比值』了。"
        "本益比恆正，比值永遠 > 0，所以「只看低於族群中位」會永遠篩出 0 筆。"
        "vs_median 的定義是『相對族群中位的百分比差』：-30 ＝ 比中位便宜 30%"
    )


def test_每檔股票都有個股頁():
    """第 31／61／63 項。壞掉的時候：搜尋得到、點進去卻是「個股頁還沒產生」。"""
    idx = config.SITE / "data" / "stocks.json"
    if not idx.exists():
        pytest.skip("還沒產生 site/data/stocks.json")
    d = json.loads(idx.read_text(encoding="utf-8"))
    codes = [s["code"] for s in (d.get("stocks") or d)] if not isinstance(d, list) else [s["code"] for s in d]
    pages = {p.split("/")[-1][:-5] for p in glob.glob(str(config.SITE / "data" / "stock" / "*.json"))}
    missing = [c for c in codes if c not in pages]
    assert not missing, f"索引裡有 {len(codes)} 檔，但這 {len(missing)} 檔沒有個股頁：{missing[:8]}"


# --------------------------------------------------------------------------
# 三個 YAML 之間的口徑一致性
# --------------------------------------------------------------------------
# 今天抓到好幾個「同一家公司在族群頁算得到、在產業鏈圖上不存在」的不一致
#（3264 欣銓、8150 南茂、6196 帆宣、4958 臻鼎）。這種錯不會報錯，只會讓
# M1 的族群量能與產業鏈圖各說各話。

def _load(name):
    return yaml.safe_load((config.GROUPS_DIR / name).read_text(encoding="utf-8"))


def test_供應鏈圖的台股都在族群或題材裡():
    """壞掉的時候：產業鏈圖上點一家公司，卻在任何族群頁都找不到它 ——
    使用者會覺得這兩個頁面在講不同的市場。"""
    sc = _load("supply_chain.yaml")
    g = _load("groups.yaml")
    th = _load("themes.yaml")
    known = set()
    for blk in (g.get("groups") or {}).values():
        known |= {str(c) for c in (blk.get("codes") or [])}
    for blk in (th.get("themes") or {}).values():
        known |= {str(c) for c in (blk.get("codes") or [])}

    orphan = []
    for co in sc["companies"]:
        t = str(co.get("ticker") or "")
        if co.get("foreign") or not (len(t) == 4 and t.isdigit()):
            continue          # 外商與非台股代號不管
        if t not in known:
            orphan.append(f"{t} {co.get('name')}")
    assert not orphan, (
        "這些公司在 supply_chain.yaml 有節點，但 groups.yaml 與 themes.yaml 都沒有收：\n  "
        + "\n  ".join(orphan)
        + "\n（M1 的族群量能吃的是 groups.yaml，沒收等於這家公司的資金流沒被算進任何族群）"
    )


def test_環節名稱不會長到跑出色塊():
    """壞掉的時候：關聯圖的環節標題壓到色塊外面，蓋到旁邊的卡片。
    _uitest 有量畫面上的實際寬度，這裡先用字數擋在前面 —— 早一步發現省一輪 14 分鐘。"""
    sc = _load("supply_chain.yaml")
    def w(s):   # CJK 約 13px、半形約 7px，欄寬 178 扣留白後約 155px
        return sum(13 if ord(c) > 127 else 7 for c in s)
    long = [(s["name"], w(s["name"])) for s in sc["segments"] if w(s["name"]) > 150]
    assert not long, f"這些環節名稱太長（估算寬度 > 150px，欄寬只有 ~155px）：{long}"


# --------------------------------------------------------------------------
# 族群成分的「產業別離群值」白名單
# --------------------------------------------------------------------------
# 2026-09-19：用證交所產業別掃過所有族群，找「這一格裡只有它是這個產業別」的成員。
# 一掃就抓到三個真錯（都是 WebSearch 獨立確認過的）：
#   · 3105 穩懋在 panel（面板）—— 它是全球最大砷化鎵晶圓代工廠，做手機射頻 PA
#   · 6266 泰詠在 passive（被動元件）—— 它是 EMS 代工商，被動元件是它的**供應商**
#   · 1101 台泥在 petrochemical（塑化）—— 它是水泥業，那一格其餘是台塑四寶
#
# 但同一次也產生 5 個**誤報** —— 跨產業別本身很常見（記憶體模組廠掛「電腦及週邊」、
# IC 載板廠掛「半導體業」）。所以這條**不能寫成「不准有離群值」**，
# 那種測試太吵，兩週內一定會被人關掉。
#
# 改成白名單：已經人工確認過的離群登記在下面並附理由，**只有沒登記過的才會紅**。
# 這樣既擋得住「有人又放錯一家」，又不會每天對著已知的合理跨界鬼叫。
# ★ 2026-09-21：族群換成 tide-tw.app 的 110 個板塊，舊的 6 筆 key 有 4 個板塊已不存在
# （memory / semi_equipment / pcb_abf / optical_comm），新的切法帶出 26 筆跨產業別離群。
# 每一筆都逐檔查過證交所產業別與公司主體業務才登記在這裡 ——
# 這張表的意義是「我確認過而且說得出理由」，不是「讓測試變綠」。
ALLOWED_OUTLIERS = {
    # ── 仍然有效的舊登記 ──
    ("ai_server_odm", "2317"):     "鴻海歸『其他電子』，但它是 AI 整櫃出貨龍頭",
    ("petrochemical", "6505"):     "台塑化歸『油電燃氣』，但它是台塑四寶之一的煉油石化廠",
    ("factory_service", "6196"):   "帆宣歸『其他電子』，但主體是半導體廠務與設備整合",
    ("abf_substrate", "3189"):     "景碩是 IC 載板廠，證交所把載板歸『半導體業』而非電子零組件",

    # ── 半導體鏈 ──
    ("cxl", "5289"):               "宜鼎歸『電腦及週邊』，2026-02 推 CXL 2.0 Type 3 擴充卡",
    ("memory_module", "5289"):     "宜鼎是工業級記憶體模組廠，證交所歸『電腦及週邊』但主體是記憶體",
    ("optical_sensing", "3059"):   "華晶科歸『光電』，做的是影像感測模組",
    ("pkg_equipment", "6438"):     "迅得歸『其他電子』，做的是載板與 PCB 製程自動化設備",
    ("pkg_metrology", "6217"):     "中探針歸『電子零組件』，做的是測試探針（測試介面）",
    ("ic_test_service", "6830"):   "汎銓歸『其他電子』，做的是材料分析與可靠度驗證服務",
    ("semi_facility", "4770"):     "上品歸『化學工業』，主體是氟塑料內襯管道、化學品儲槽與 ISO Tank，"
                                   "近九成營收來自晶圓廠與電子級化學品廠"
                                   "（2026-09-21 查證後從 glass_substrate 移來，見 docs/tide_deviations.md）",
    ("hbm", "2467"):               "志聖歸『電子零組件』，供應 HBM 製程用烘烤設備",
    ("leadframe_chem", "2486"):    "一詮歸『光電』（原 LED 導線架廠），導線架仍是第二大產品線",
    ("silicon_photonics", "3450"): "聯鈞歸『半導體業』，做的是雷射二極體封測，屬光通訊鏈",
    ("microled", "6854"):          "錼創歸『半導體業』，做的是 Micro LED 磊晶與巨量轉移",

    # ── AI 伺服器鏈 ──
    ("air_cooling", "2486"):       "一詮歸『光電』，散熱元件 2026-01 已占營收 44.18%（超過導線架）",
    ("air_cooling", "3324"):       "雙鴻歸『其他電子類』，是散熱模組廠",
    ("server_psu", "2301"):        "光寶科歸『電腦及週邊』，AI 伺服器這塊做的是 PSU 與電源架",
    ("server_psu", "6409"):        "旭隼歸『其他電子』，做的是不斷電系統與工業／伺服器電源",
    ("bbu", "6781"):               "AES-KY 歸『電子零組件』，是伺服器 BBU 核心供應商",
    ("bbu", "6558"):               "興能高歸『其他電子』，做的是電芯與 BBU 電池模組",
    ("ai_interconnect", "3665"):   "貿聯-KY 歸『其他電子』，做的是高速線束與連接器",

    # ── 一般電子 ──
    ("ems", "2312"):               "金寶歸『其他電子』，主體是消費性電子代工（EMS）",
    ("ems", "2328"):               "廣宇歸『電子零組件』，主體是鴻海集團的代工組裝",
    ("smartphone", "4938"):        "和碩歸『電腦及週邊』，是 iPhone 主要組裝廠",
    ("smartphone", "3008"):        "大立光歸『光電』，主體是手機鏡頭",
    ("smartphone", "4915"):        "致伸歸『電子零組件』，做的是手機相機模組與周邊",
    ("panel", "6143"):             "振曜歸『通信網路』，做的是電子書閱讀器（電子紙模組）代工",

    # ── 傳產與其他 ──
    ("factory_automation", "6739"): "竹陞科技歸『其他電子類』，做的是半導體廠自動化軟體與設備",
    ("defense", "8033"):           "雷虎歸『其他』，做的是無人機與軍用載具",
}


def test_族群沒有未登記的產業別離群值():
    """壞掉的時候使用者會看到什麼：點一個族群進去，裡面混著一家完全不同產業的公司
    —— 而且 M1 的族群量能會把那家公司的資金算進來，讓「錢往哪個族群跑」這個主結論失真。

    這正是 2026-09-19 抓到的一整批錯（直播平台在半導體材料、醋酸纖維絲束在半導體設備、
    砷化鎵代工廠在面板、EMS 代工商在被動元件、水泥廠在塑化）。
    """
    import collections

    import pandas as pd

    files = glob.glob(str(config.DATA / "company_info" / "**" / "*.parquet"), recursive=True)
    if not files:
        pytest.skip("沒有 data/company_info，跳過")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).drop_duplicates("code")
    ind = dict(zip(df["code"].astype(str), df["industry"]))

    g = _load("groups.yaml")["groups"]
    found = []
    for gid, blk in g.items():
        codes = [str(c) for c in (blk.get("codes") or [])]
        cnt = collections.Counter(ind.get(c, "?") for c in codes)
        if len(cnt) < 2:
            continue
        main, n_main = cnt.most_common(1)[0]
        if n_main < 3:          # 樣本太小，看不出「主流產業別」是什麼
            continue
        for c in codes:
            if cnt[ind.get(c, "?")] == 1 and (gid, c) not in ALLOWED_OUTLIERS:
                found.append(f"{gid} 裡的 {c}（{ind.get(c, '?')}），這一格主要是「{main}」")
    assert not found, (
        "這些成員的證交所產業別跟所屬族群的其他成員對不上，請逐一確認是不是放錯：\n  "
        + "\n  ".join(found)
        + "\n\n確認過是對的（跨產業別很常見）就登記到 ALLOWED_OUTLIERS 並寫明理由；"
        "確認是錯的就從 groups.yaml 拿掉。"
    )


# ---------------------------------------------------------------- 環節顏色不准被新環節洗掉
def test_環節顏色的索引吃的是yaml原始順序():
    """新增一個環節，不可以害既有環節的顏色全部換一輪。

    壞掉的時候使用者會看到什麼
    --------------------------
    前端的環節色是 `PALETTE[索引 % 14]`，而**全站只認這個顏色**：剖析圖的零件、
    關聯圖的節點、環節色標、族群卡片、族群連結的小圓點都用它。
    以前那個索引是「依 layer 排序後的陣列位置」，所以只要在 layer 0／1／2
    插進一個新環節（例如一般電子鏈的「面板材料」），後面每一個既有環節的位置都會 +1
    —— 於是半導體鏈與 AI 鏈**所有環節的顏色一起變**，而且不會有任何錯誤訊息。
    Andy 會看到「我只加了一條電子鏈，為什麼台積電那格從藍色變成紫色」。

    修法：`loader.supply_chain()` 在排序**之前**把 YAML 原始順序記成 `color_idx`，
    前端改吃 `color_idx`。這條測試釘住兩件事：欄位還在，而且值真的是原始順序。
    """
    from pipeline.groups import loader

    raw = _load("supply_chain.yaml")
    raw_order = [s["id"] for s in raw["segments"]]
    out = loader.supply_chain()["segments"]

    missing = [s["id"] for s in out if s.get("color_idx") is None]
    assert not missing, f"這些環節沒有 color_idx，前端會退回用陣列位置配色：{missing}"

    wrong = [(s["id"], s["color_idx"], raw_order.index(s["id"]))
             for s in out if s["color_idx"] != raw_order.index(s["id"])]
    assert not wrong, f"color_idx 必須等於 YAML 的原始位置，這幾個對不上：{wrong}"

    # 排序本身還要成立（環節要照 layer 由上游排到下游）
    layers = [s.get("layer", 0) for s in out]
    assert layers == sorted(layers), "環節仍必須依 layer 排序，只是配色不再吃排序後的位置"


def test_前端真的改吃color_idx():
    """光是 loader 送出 color_idx 沒有用，前端沒接就白做。

    這條是「兩邊口徑一致」那類的檢查（同 CLAUDE.md 對 KInd 的要求）：
    只驗 `site/app.js` 建 `L.sidx` 的那一行有提到 color_idx，
    不驗顏色本身（顏色要靠 _uitest 的眼睛）。
    """
    import pathlib

    src = (pathlib.Path(__file__).resolve().parent.parent / "site" / "app.js").read_text(encoding="utf-8")
    line = [ln for ln in src.splitlines() if "L.sidx[" in ln and "forEach" in ln]
    assert line, "找不到 site/app.js 裡建 L.sidx 的那一行（改過名字就把這條測試一起改）"
    assert any("color_idx" in ln for ln in line), (
        "site/app.js 建 L.sidx 時沒有讀 color_idx —— "
        "loader 送出來了但前端沒接，新增環節還是會把全站顏色洗掉")


# ---------------------------------------------------------------- 畫面上不准出現 "nan"
def test_送到前端的名稱不會是nan():
    """壞掉的時候使用者會看到什麼：資金去向桑基圖的代表股那一欄整排寫著「nan」。

    根因（2026-09-20，Andy 直接截圖回報）
    ------------------------------------
    `price_daily` 的 `name` 欄是後來才加的，只有 2026-09-09 之後的列有值。
    取名字的地方寫成 `px.drop_duplicates("code")` —— 預設留**第一筆**，
    而 px 通常已經切到最近 60 天、起點在三個月前，所以每一檔拿到的都是 NaN，
    再被 `str()` 變成字串 "nan" 寫進 JSON。

    ★ 同一行在兩個地方各寫了一次（`rrg.sankey_daily` 與 `flow.concentration_members`），
      Andy 只看到桑基圖那一個，另一個是掃 JSON 才抓到的 —— 所以這條測試**掃整個
      site/data/**，不是只驗那兩支函式。有第三個地方再犯，這條會直接紅。
    """
    import pathlib

    out = pathlib.Path(__file__).resolve().parent.parent / "site" / "data"
    files = sorted(out.glob("*.json"))
    if not files:
        pytest.skip("還沒有 site/data，跳過（乾淨 checkout 的 CI）")

    bad = []
    for f in files:
        txt = f.read_text(encoding="utf-8")
        # ★ 2026-09-25：以前這裡特別排除 tasks.json（任務板散文會正當地提到 nan bug）。
        #   tasks.json 已經不再產出（內部作業文字不該上 public 網站），排除條件跟著拿掉 ——
        #   留著的話，哪天有人把它加回來，這條護欄也會默默放行。
        n = txt.count('"nan"') + txt.count('"NaN"') + txt.count('"None"')
        if n:
            bad.append(f"{f.name}：{n} 處")
    assert not bad, (
        "這些送到前端的 JSON 裡有字串 \"nan\"／\"None\"，畫面上會直接印出來：\n  "
        + "\n  ".join(bad)
        + "\n\n取名字一律走 pipeline/compute/names.py 的 latest_names() 與 name_or_code()，"
        "不要再自己寫一次 drop_duplicates(\"code\")。"
    )


def test_取名字的地方沒有人再自己寫一次():
    """把「不要再有第三個地方各寫一次」釘成機器檢查。

    壞掉的時候：某個新功能又自己寫了 `px.drop_duplicates("code")...["name"]`，
    於是那一塊畫面又開始印 nan，而且要等 Andy 截圖回報才會發現。
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent / "pipeline"
    pat = re.compile(r'drop_duplicates\(\s*["\']code["\']\s*\)[^\n]*\[\s*["\']name["\']\s*\]')
    hits = []
    for f in root.rglob("*.py"):
        if f.name == "names.py":
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(ln):
                hits.append(f"{f.relative_to(root.parent)}:{i}  {ln.strip()}")
    assert not hits, (
        "這幾行又在自己組「代號 → 名稱」了，會重演 2026-09-20 的 nan：\n  "
        + "\n  ".join(hits)
        + "\n\n改用 pipeline/compute/names.py 的 latest_names()。"
    )
