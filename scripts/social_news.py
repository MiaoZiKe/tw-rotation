"""新聞貼文自動產稿＋排程（2026-10-28，Andy：「可以，接上排程，單位改成億美元，CEO並安排人員持續優化，
依據不同的內容後台紀錄，後續慢慢改善收斂成大家喜歡的主題、內容、版面、風格」）。

「主題文章」（新聞／題材／知識長文貼文，每篇 IG 單圖＋Threads 串文）每天全自動：
  交易日：盤前 1 篇＋盤後 1 篇（主貼文發出後 15 分鐘；新聞挑不到才用常備文庫補，盤後至少 1 篇）；
  週末與休市日：週末精選 2 篇（10:30 新聞優先、19:30 常備文庫優先），另有「備案」時段保證每天至少 1 篇。
  （2026-10-29 Andy：「每天至少開盤會有四到五篇……週末也會有一到兩篇，這些都需要自動化」；
    3 篇主貼文＋主題文章 1～2 篇。舊版每段 3～5 篇已改成每段名額 SLOTS[...]["n"]。）
Actions 上沒有 Claude、OpenAI 額度用完，所以全部用「模板」產稿，不呼叫任何 LLM：
  選題：資料湖 data/news（cnyes／udn／technews）→ 相似標題分群 → 熱度（幾家媒體報、幾則、有沒有數字、多新）
        × 每週成效權重（social/news/weights.json）→ 前 80% 依分數、保留 20% 探索（隨機挑其他主題）。
  數字：只取新聞內文的數字；同一數字另一家媒體也寫到 → 標「兩家來源」，否則每條註明出處媒體。
  文案：口袋證券長文結構（標題兩行 hashtag → 導言 → 📊 重點數字 → 🔎 數字怎麼看 → 👀 為什麼值得注意 → 法遵句 → 網址一行）。
  圖卡：docs/marketing/posts/render_news_cards.py 的 --pal D 定案版（card_v4），預設無 AI 圖（AI 圖未經 art-director 審不得發）。
  法遵：scripts/news_legal.py 自動改寫＋檢查，不過就不排程；圖卡重疊檢查 >0 筆也不排程。
寫入 social/ig/queue、social/threads/queue（status: approved＋publish_at），由既有的 ig_post.yml／threads_post.yml 每 15 分鐘發出。

用法：
  python scripts/social_news.py --slot pre|intra|post|auto [--date YYYY-MM-DD] [--posted state/posted.json]
                                [--dry-run --out <資料夾>] [--now 2026-10-28T08:35+08:00] [--force]
  --slot auto：依 posted.json 看今天哪幾段主貼文已發、新聞文還沒排 → 逐段產生。
  --dry-run：不寫 queue，只把圖卡、文案、meta 寫到 --out（樣本用）。
說明文件：docs/marketing/social_unit/news_auto.md
"""
from __future__ import annotations

import argparse
import email.utils
import hashlib
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from news_legal import check as legal_check, clean_ok, is_promo, sanitize  # noqa: E402

TPE = timezone(timedelta(hours=8))
SITE = "https://liguligu-puipui.com/"
IG_Q = ROOT / "social" / "ig" / "queue"
TH_Q = ROOT / "social" / "threads" / "queue"
IMG_DIR = ROOT / "social" / "ig" / "images" / "news"
WEIGHTS = ROOT / "social" / "news" / "weights.json"
LOG_DIR = ROOT / "social" / "news" / "log"

# 時段：主貼文的 posted.json 鍵、固定最早發文時間（台北）、新聞時間窗
# n＝這段最多幾篇；floor＝新聞挑不夠時用常備文庫補到至少幾篇；off＝休市日（週末／國定假日）才跑；after＝auto 模式最早幾點才排
# 2026-10-29：每天主題文章交易日 2 篇（盤前 1＋盤後 1）、休市日 2 篇（wk1＋wk2）；盤中名額 0（主貼文已密集），要開把 n 改 1。
SLOTS = {
    "pre":   dict(name="盤前", key="premarket", fixed="08:35", since=(-1, "13:30"), n=1, floor=1),   # 10-29 Andy：「主題文章怎麼沒有發 盤前的」→ 盤前也保底（新聞全擋時補常備文庫）
    "intra": dict(name="盤中", key="intraday",  fixed="12:16", since=(0, "07:30"),  n=1, floor=1),   # 10-29 Andy：「都沒發文」→ 盤中也發 1 篇主題文章（含保底）
    "post":  dict(name="盤後", key="close",     fixed=None,    since=(0, "11:30"),  n=1, floor=1),
    "wk1":   dict(name="週末", key=None, fixed="10:30", since=(-1, "13:30"), n=1, floor=1, off=True, after="10:00"),
    "wk2":   dict(name="週末", key=None, fixed="19:30", since=(0, "06:00"),  n=1, floor=1, off=True, after="18:45", evergreen_first=True),
    "fb":    dict(name="備案", key=None, fixed="21:15", since=(0, "06:00"),  n=1, floor=1, off=False, after="20:50", evergreen_first=True),
}
WEEKDAY_SLOTS = ("pre", "intra", "post")
OFFDAY_SLOTS = ("wk1", "wk2")
EVERGREEN = ROOT / "social" / "news" / "evergreen.json"
EVG_USAGE = ROOT / "social" / "news" / "log" / "evergreen_usage.json"
EVG_COOLDOWN = 30                 # 同一篇常備文 30 天內不重發（庫存用完才輪回最久沒用的）
EVG_MIN_BODY = 350
N_MIN, N_MAX = 1, 5               # 保留舊名稱（外部腳本可能 import）；實際名額看 SLOTS[...]["n"]
EXPLORE = 0.2
STATUS = "approved" if os.environ.get("NEWS_AUTO_APPROVE") == "1" else "draft"   # 預設 draft：品質修完、CEO 確認後 workflow 才設 NEWS_AUTO_APPROVE=1
# 休市日／備案時段／常備文庫的貼文另用一個開關（2026-10-29 新增）：TOPIC_AUTO_APPROVE=1 才寫 approved，否則 draft（不會發）。
# 交易日的新聞稿仍照 NEWS_AUTO_APPROVE。要全開：兩個環境變數都設 "1"（.github/workflows/social_news.yml 的「產稿」那一步）。
TOPIC_STATUS = "approved" if os.environ.get("TOPIC_AUTO_APPROVE") == "1" else "draft"
GAP_MIN = 5                       # 同一段多篇之間錯開 5 分鐘，避免洗版
SRC_NAME = {"cnyes": "鉅亨", "udn": "經濟日報", "technews": "科技新報"}
CATS = ["台股", "財報", "總經", "科技", "美股"]
STYLES = ["口袋長文", "精簡重點"]
LAYOUT = "D-無圖大數字"

# ---------------- 分類 ----------------
KW = {
    "財報": r"財報|EPS|每股(純益|盈餘|賺|稅後)|毛利率|營益率|自結|營收|法說|獲利|淨利|財測",
    "總經": r"Fed|聯準會|央行|利率|降息|升息|CPI|PCE|通膨|非農|GDP|殖利率|美元指數|新台幣|匯率|油價|金價|關稅|PMI|失業率|景氣|天然氣|原油|布蘭特|西德州|大宗商品",
    "美股": r"美股|道瓊|那斯達克|標普|費半|費城半導體|S&P|Nasdaq|輝達|NVIDIA|微軟|蘋果|Apple|Alphabet|Google|Meta|亞馬遜|特斯拉|博通|超微|AMD|甲骨文|ADR",
    "台股": r"台股|加權指數|大盤|三大法人|外資|投信|自營商|成交值|櫃買|集中市場|台指期",
}
CTYPE = [
    ("財報數字", r"財報|EPS|每股|毛利率|自結|營收|淨利|獲利|財測|營益率"),
    ("盤勢數字", r"加權指數|大盤|三大法人|外資|投信|自營商|成交值|台指期|收盤|櫃買"),
    ("總經數據", r"Fed|聯準會|央行|利率|CPI|PCE|通膨|非農|GDP|殖利率|匯率|新台幣|油價|金價|PMI|天然氣|原油|布蘭特|TTF|大宗商品"),
    ("產業趨勢", r"AI|伺服器|半導體|晶片|CoWoS|HBM|記憶體|PCB|散熱|光通訊|機器人|電動車|資料中心"),
]


def topic_of(text: str, src_cat: str) -> str:
    for cat in ("財報", "美股"):
        if re.search(KW[cat], text):
            return cat
    if re.search(r"台股|加權指數|三大法人|集中市場|櫃買", text):
        return "台股"
    if re.search(KW["總經"], text):
        return "總經"
    if src_cat == "科技":
        return "科技"
    if re.search(KW["台股"], text):
        return "台股"
    return {"總經": "總經", "科技": "科技"}.get(src_cat, "台股")


def ctype_of(text: str) -> str:
    for name, pat in CTYPE:
        if re.search(pat, text):
            return name
    return "公司動態"


# ---------------- 讀資料湖 ----------------
def _ts(row) -> datetime | None:
    s = str(row.get("published_at") or "")
    try:
        if re.match(r"\d{4}-\d{2}-\d{2}T", s):
            return datetime.fromisoformat(s).astimezone(TPE)
        return email.utils.parsedate_to_datetime(s).astimezone(TPE)
    except Exception:
        try:
            return datetime.fromisoformat(str(row.get("date"))[:10]).replace(tzinfo=TPE)
        except Exception:
            return None


def load_news(t0: datetime, t1: datetime) -> list[dict]:
    import pandas as pd
    fs = sorted((ROOT / "data" / "news").glob("**/*.parquet"))
    if not fs:
        return []
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True).fillna("")
    import html as _h
    for col in ("title", "summary"):
        df[col] = df[col].astype(str).map(lambda x: re.sub(r"\s*\[…\]|\s*\[\.\.\.\]", "", _h.unescape(x)).strip())
        df[col] = df[col].map(lambda x: re.sub(r"\s*\n+\s*", "，", x).strip("， "))
    lo = (t0 - timedelta(days=1)).strftime("%Y-%m-%d")
    df = df[df["date"].astype(str) >= lo]
    out = []
    for r in df.to_dict("records"):
        ts = _ts(r)
        if ts and t0 <= ts <= t1:
            r["ts"] = ts
            out.append(r)
    return out


def clean_name(v: str) -> str:
    """社群稿比對用的簡稱：拿掉「*」與 -KY／-創／-DR 後綴（「矽力*-KY」→「矽力」）。只用在這支，不動資料湖。"""
    return re.sub(r"[-－](KY|創|DR)$", "", re.sub(r"[*＊]", "", str(v)).strip()).strip()


def names_map() -> dict[str, str]:
    try:
        import pandas as pd
        fs = sorted((ROOT / "data" / "company_info").glob("**/*.parquet"))
        d = pd.concat([pd.read_parquet(f) for f in fs])
        # 「譜瑞-KY」「XX-創」這類後綴拿掉，標題裡寫的是簡稱（10-29：譜瑞法說被判成找不到主體）
        return {k: clean_name(v) for k, v in zip(d["code"].astype(str), d["name"].astype(str))}
    except Exception:
        return {}


# ---------------- 分群與熱度 ----------------
def _bigrams(s: str) -> set[str]:
    s = re.sub(r"[^一-鿿A-Za-z0-9]", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def cluster(news: list[dict]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    sigs: list[tuple[set, set]] = []
    for n in sorted(news, key=lambda x: x["ts"]):
        bg = _bigrams(n["title"])
        codes = {c for c in str(n.get("codes") or "").split(",") if c and not c.startswith("US-")}
        keys = {k for k in (m.group("num").replace(",", "").lstrip("+-").split(".")[0] for m in NUMRE.finditer(n["title"])) if len(k) >= 3}
        codes |= {"#" + k for k in keys}          # 標題裡同一個 3 位數以上的數字（例 939.35 點）視為同一事件
        hit = None
        for gi, (gb, gc) in enumerate(sigs):
            j = len(bg & gb) / max(1, len(bg | gb))
            share = codes & gc
            if j >= 0.3 or (share and j >= 0.2) or (any(x.startswith("#") for x in share) and j >= 0.1):
                hit = gi
                break
        if hit is None:
            groups.append([n]); sigs.append((bg, codes))
        else:
            groups[hit].append(n); sigs[hit][0].update(bg); sigs[hit][1].update(codes)
    return groups


# 商品報價單位（2026-10-29 第二輪：「97.35歐元/MWh」抓不到 → 歐洲天然氣那則被判「沒有可當主旨的關鍵數字」）
COMMOD_UNIT = (r"(?:美元|歐元|美分|便士|英鎊|日圓|人民幣|元)\s*/\s*"
               r"(?:桶|盎司|英兩|公噸|噸|MWh|MMBtu|mmBtu|百萬英熱單位|therm|英斗|蒲式耳|磅|公斤|克|度)")
# num：可帶區間（「季增1-3%」「185～195億美元」，2026-10-29 第二輪：舊版把「1-3%」讀成「-3%」）；前面緊貼數字的正負號不算正負號。
# 「成」＝N×10%（「季減約2成」）；排除「成長／成本／成員／成交…」這類詞。
NUMRE = re.compile(r"(?P<pre>逾|約|近|超過)?(?P<num>(?<![\d.])[+-]?\d[\d,]*(?:\.\d+)?(?:\s*[-~～]\s*\d[\d,]*(?:\.\d+)?)?)\s*"
                   r"(?P<unit>" + COMMOD_UNIT + r"|兆韓元|兆美元|億美元|萬美元|美元|億元|萬元|萬張|兆元|兆|億|元|%|％|點|倍|家|張"
                   r"|成(?![長本員交立績功為熟果分品都年效型])"
                   r")")
CN_DIGIT = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
SPLIT = re.compile(r"[，。；：、！？\s（）()「」『』〈〉【】/／|｜]")
CHG = ("年增", "季增", "月增", "年減", "季減", "月減", "增加", "減少")


def numbers_of(text: str) -> list[dict]:
    """從新聞文字抓「標籤＋數字＋單位」；標籤＝同一子句裡數字前面的字。"""
    out, prev, last_lab = [], "", ""
    # 「年增五成」「季減三成」：中文數字＋成 → 阿拉伯數字（「一成不變」「九成九」這類不算）
    text = re.sub(r"(?<![一二三四五六七八九十])([一二兩三四五六七八九])成(?![長本員交立績功為熟果分品都年效型不一二三四五六七八九])",
                  lambda mm: f"{CN_DIGIT[mm.group(1)]}成", text)
    ms = list(NUMRE.finditer(text))
    for k, m in enumerate(ms):
        last_end = ms[k - 1].end() if k else 0
        head = text[:m.start()]
        if re.search(r"[A-Za-z\u4e00-\u9fff] $", head):     # 「EPS 4.55元」：數字前一個空白不當子句分界（10-29 第二輪：標題的 EPS 全被漏掉）
            head = head[:-1]
        # 中英交界的空白（「荷蘭 TTF 近月期貨」）也不是子句分界：先換成不斷行的佔位字，標籤取完再換回空白
        head = re.sub(r"(?<=[\u4e00-\u9fff]) (?=[A-Za-z])|(?<=[A-Za-z]) (?=[\u4e00-\u9fff])", "\u2007", head)
        cut = max((head.rfind(c) for c in "，。；：、！？ （(「/／|｜）)」』"), default=-1)
        same_clause = k > 0 and cut <= last_end - 1
        cut = max(cut, last_end - 1)              # 同一子句裡前面還有數字 → 標籤從那個數字之後算
        lab = head[cut + 1:].replace("\u2007", " ").strip()
        unit0 = m.group("unit")
        raw_lab = lab
        if unit0 in ("%", "％", "成", "點") and re.search(r"(上漲|下跌|漲|跌|下挫|走高|走低|攀升|回落|上升|下降|成長|衰退|增長|增加|減少)$", lab):
            pass                                  # 「期貨漲1.2%」：漲跌是比較，不能拿掉（拿掉會變成「期貨 1.2%」）
        elif not any(lab.endswith(c) for c in CHG):
            lab = re.sub(r"(衝上|衝|站上|突破|創|寫下|達到|達|為|約|至|到|來到|共|僅|有|是|再|則|合計|攀升至|升至|降至|增至|減至|增|減|漲|跌|(?<!營)收|上漲|下跌|賺)$", "", lab)
        if same_clause and len(lab) < 2 and re.fullmatch(r"(至|到|來到|升至|降至|攀升至|漲至|跌至|達|為|收|收在|報)?", raw_lab) and last_lab:
            lab = re.sub(r"(上漲|下跌|漲|跌|下挫|走高|走低|攀升|回落|年增|年減|季增|季減|月增|月減|增加|減少)$", "", last_lab)   # 「期貨漲1.2%至97.35歐元/MWh」→ 97.35 的標籤＝「期貨」
        lab = re.sub(r"^[〈【\[][^〉】\]]{1,8}[〉】\]]", "", lab)          # 標題的「〈財報〉」標頭不進標籤
        lab = re.sub(r"^(並|且|而|但|雖|其中|另|也|較|比|與|和|及)", "", lab).strip()
        if any(lab.endswith(c) or lab == c for c in CHG) and prev and len(lab) <= 4:
            lab = prev + lab
        mp = re.search(r"(?:估|預估|預期|預計)?(今年|明年|去年|後年)$", lab)
        if mp and mp.start() >= 2:                                    # 「核心通膨估今年」→「今年核心通膨」（期間放前面，不被 JUNK 的「年$」擋）
            lab = mp.group(1) + lab[:mp.start()]
        per = r"(19|20)\d\d年|今年|明年|去年|後年"
        if re.fullmatch(per, lab) and prev and re.search(per, prev):      # 只有期間 → 套用前一個標籤、換掉期間
            m0 = re.search(per, prev)
            tail = prev[m0.end():]
            lab = lab + tail if tail else prev[:m0.start()] + lab        # 「今年GDP成長率」→「2027年GDP成長率」；「通膨估今年」→「通膨估明年」
        num = re.sub(r"\s*[-~～]\s*(?=\d)", "～", m.group("num")) if re.search(r"\d\s*[-~～]\s*\d", m.group("num")) else m.group("num")
        last_lab = lab
        if re.fullmatch(r"(19|20)\d\d", num.replace(",", "")) and m.group("unit") in ("元",):
            continue
        unit = re.sub(r"\s+", "", m.group("unit")).replace("％", "%")
        mu = re.search(r"每(桶|盎司|英兩|公噸|噸|磅|英斗|蒲式耳)$", lab)
        if mu and unit in ("美元", "歐元", "元", "人民幣", "日圓"):          # 「布蘭特原油每桶85美元」→ 85 美元/桶
            unit = f"{unit}/{mu.group(1)}"; lab = lab[:mu.start()]
        if not (2 <= len(lab) <= 14) or not re.search(r"[一-鿿]", lab) or re.search(r"\d{4,}$", lab):
            prev = lab if 2 <= len(lab) <= 10 else prev
            continue
        x = dict(label=lab, value=(m.group("pre") or "") + num, unit=unit)
        if unit == "成":                          # N 成 ＝ N×10%；原文寫法另存，內文對照用
            x["orig"] = x["value"] + "成"
            x["value"] = (m.group("pre") or "") + "～".join(f"{float(v.replace(',', '')) * 10:g}" for v in num.split("～"))
            x["unit"] = unit = "%"
        if "～" in num:
            x["range"] = True
        x["key"] = x["value"].lstrip("約逾近超過").replace(",", "") + unit
        out.append(x)
        if not any(lab.endswith(c) for c in CHG):
            prev = lab
    seen, uniq = set(), []
    for x in out:
        if x["key"] not in seen:
            seen.add(x["key"]); uniq.append(x)
    return uniq


def score(group: list[dict], w: dict) -> dict:
    srcs = {n["source"] for n in group}
    lead = max(group, key=lambda n: (len(numbers_of(n["title"] + "，" + n["summary"])), len(n["summary"])))
    text = sanitize(lead["title"] + "，" + lead["summary"])
    nums = [x for x in numbers_of(text) if clean_ok(x["label"])]
    other = " ".join(n["title"] + n["summary"] for n in group if n["source"] != lead["source"])
    other_keys = {x["key"] for x in numbers_of(other)}
    for x in nums:
        x["verified"] = x["key"] in other_keys
    cat = topic_of(lead["title"] + lead["summary"], lead.get("category", ""))
    ct = ctype_of(lead["title"] + lead["summary"])
    newest = max(n["ts"] for n in group)
    heat = 2.0 * len(srcs) + 1.0 * len(group) + 0.6 * min(len(nums), 4) + 1.5 * sum(x["verified"] for x in nums[:3])
    heat *= w.get("topic_category", {}).get(cat, 1.0) * w.get("content_type", {}).get(ct, 1.0)
    return dict(group=group, lead=lead, text=text, nums=nums, cat=cat, ctype=ct, heat=round(heat, 3),
                srcs=sorted(srcs), newest=newest)


def load_weights() -> dict:
    try:
        return json.loads(WEIGHTS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick(cands: list[dict], n: int, rng: random.Random, explore: float) -> list[dict]:
    """前 (1-explore) 依熱度；其餘從「還沒選到的主題」隨機挑（探索），每個主題最多 2 篇，同主題不連發。"""
    cands = sorted(cands, key=lambda c: -c["heat"])
    n_exp = max(1, round(n * explore)) if len(cands) > n else 0
    chosen, per = [], {}
    for c in cands:
        if len(chosen) >= n - n_exp:
            break
        if per.get(c["cat"], 0) >= 2 or (c["ctype"] == "盤勢數字" and per.get("盤勢", 0) >= 1):
            continue                     # 盤勢數字主貼文已經發過，新聞文最多 1 篇，避免同一件事連發
        chosen.append(c); per[c["cat"]] = per.get(c["cat"], 0) + 1; c["explore"] = False
        if c["ctype"] == "盤勢數字":
            per["盤勢"] = 1
    rest = [c for c in cands if c not in chosen]
    rest = [c for c in rest if not (c["ctype"] == "盤勢數字" and per.get("盤勢"))]
    fresh = [c for c in rest if c["cat"] not in per] or rest
    rng.shuffle(fresh)
    for c in fresh[:n_exp]:
        c["explore"] = True; chosen.append(c)
    return chosen


# ---------------- 文案模板 ----------------
EXPLAIN = [
    (r"毛利率", lambda x: f"毛利率 {x['value']}% 代表每 100 元營收，扣掉直接成本後約剩 {x['value'].lstrip('約逾近')} 元毛利（本站換算）。"),
    (r"每股|EPS", lambda x: "每股純益（EPS）是稅後淨利除以股數，適合跟同一家公司過去各期比較；不同公司股本不同，不適合直接比大小。"),
    (r"年增|年減", lambda x: "年增減是和去年同一期比較，可以排除季節性的影響。"),
    (r"季增|季減", lambda x: "季增減是和上一季比較，反映最近一季的變化，但會受淡旺季影響。"),
    (r"月增|月減", lambda x: "月增減是和上個月比較，單月數字波動較大，通常要搭配年增一起看。"),
    (r"買超|賣超", lambda x: "買超、賣超是當天買的金額減掉賣的金額的差，只反映當天的資金進出，不代表後續走勢。"),
    (r"資本支出", lambda x: "資本支出是花在廠房、設備等長期資產的錢，常用來觀察公司對產能的規劃。"),
    (r"成交值|成交量", lambda x: "成交值是當天市場實際交易的總金額，用來觀察市場參與的程度。"),
    (r"營收", lambda x: "營收是公司銷售產品與服務的總金額，還沒扣掉成本與費用，所以要和毛利率、獲利一起看。"),
    (r"指數|點", lambda x: "指數點數反映整體上市股票市值的變化，權值股的影響比較大。"),
]
SUBQ = {"財報數字": "和前期比，差多少？", "盤勢數字": "今天的關鍵數字有哪些？", "總經數據": "這個數字代表什麼？",
        "產業趨勢": "報導提到哪些數字？", "公司動態": "公告的重點數字是什麼？"}
ROUTE = {"財報": "earnings", "台股": "overview", "總經": "overview", "科技": "industry", "美股": "overview"}
TAG = {"財報": "財報", "台股": "台股", "總經": "總經", "科技": "科技新聞", "美股": "美股"}


def _clean_title(t: str) -> str:
    t = sanitize(t)
    t = re.sub(r"^[〈【\[].{1,6}?[〉】\]]", "", t).strip()
    if "／" in t:
        a, b = t.split("／", 1)
        if len(a) <= 7 and len(b) >= 6:
            a = re.sub(r"(財報|獲利|營收|收盤|快訊|盤後|盤前|焦點|法說)$", "", a)
            t = f"{a} {b}" if a and a not in b else b
    return re.sub(r"\s+", " ", t).strip(" ！!")


def _lines(t: str, per: int, nmax: int = 2) -> list[str]:
    """切成最多 nmax 行、每行 ≤ per 字；只在空白／標點／中英數交界切，不切斷數字；放不下的尾段整段捨去。"""
    toks = re.findall(r"[A-Za-z0-9.,%+\-]+|[^A-Za-z0-9.,%+\-]", t)
    out, cur = [], ""
    for tk in toks:
        if len(cur) + len(tk) <= per:
            cur += tk
            continue
        if cur.strip(" ，、"):
            out.append(cur.strip(" ，、"))
        if len(out) >= nmax:
            break
        cur = tk.lstrip(" ，、")
    else:
        if cur.strip(" ，、"):
            out.append(cur.strip(" ，、"))
    out = out[:nmax]
    # 盡量在空白或標點斷：最後一行若以半個子句結尾，回退到最後一個空白／標點
    if out and len("".join(out)) < len(t.replace(" ", "")) - 1:
        last = out[-1]; k = max(last.rfind(" "), last.rfind("，"), last.rfind("、"), last.rfind("！"), last.rfind("？"))
        if k >= 4:
            out[-1] = last[:k].strip(" ，、！？")
    return out


def _lead_sentence(c: dict) -> str:
    """導言句：同群各篇摘要的第一句；含法遵禁用字眼的子句整段拿掉（只刪不改），剩不到 12 字就換下一篇，都不行退回標題。"""
    for n in [c["lead"]] + [x for x in c["group"] if x is not c["lead"]]:
        s = sanitize(n["summary"] or "")
        first = "，".join(re.split(r"(?<=。)", s)[:2]).replace("。", "，").strip("， ")
        first = re.sub(r"[A-Za-z0-9\u4e00-\u9fff]{1,12}：(?=，|$)", "", first)      # 去掉黏在句尾的「來源：」殘段
        keep = [x for x in first.split("，") if x.strip() and clean_ok(x)]
        out = ""
        for x in keep:
            if len(out) + len(x) > 180:
                break
            out = f"{out}，{x}" if out else x
        out = out.rstrip("、，；： ")
        if len(out) >= 12:
            c["lead_src"] = n["source"]
            return out + "。"
    c["lead_src"] = c["lead"]["source"]
    return _clean_title(c["lead"]["title"]) + "。"


def _who(c: dict, names: dict, title: str) -> str:
    codes = [x for x in str(c["lead"].get("codes") or "").split(",") if x and not x.startswith("US-")]
    if codes and names.get(codes[0]):
        return names[codes[0]]
    hits = [v for v in set(names.values()) if len(v) >= 2 and v in title and not re.search(r"[A-Za-z0-9]", v)]
    return max(hits, key=len) if hits else ""


# ---------------- v2 結構化產稿（CEO 10-28 退件後：標題由欄位組、大數字＝主旨、具體解讀、觀察點、品質閘） ----------------
ENT = ["SK海力士", "三星", "輝達", "NVIDIA", "微軟", "蘋果", "Alphabet", "Google", "Meta", "亞馬遜", "特斯拉", "博通", "超微", "AMD",
       "甲骨文", "英特爾", "高通", "美光", "恩智浦", "安謀", "CoreWeave", "OpenAI", "Anthropic", "SpaceX", "費半", "道瓊", "那斯達克",
       "標普", "聯準會", "Fed", "日銀", "歐洲央行", "TrendForce", "IDC", "加權指數", "台股", "三大法人", "外資", "投信", "自營商",
       "長鑫存儲", "長鑫", "中芯", "華為"]
METRICS = [("EPS", r"每股(純益|盈餘|稅後|賺)|每股$|EPS"), ("經濟成長率", r"GDP|經濟成長"), ("通膨", r"通膨|物價"), ("虧損", r"淨虧|虧損"), ("毛利率", r"毛利率"), ("營業利益", r"營業利益|營益"), ("淨利", r"淨利|純益|獲利|盈餘"),
           ("營收", r"營收"), ("資本支出", r"資本支出"), ("財測", r"財測|指引"), ("指數", r"加權指數|指數|道瓊|那斯達克|標普|費半"),
           ("買超", r"買超"), ("賣超", r"賣超"), ("成交值", r"成交值|成交額"), ("殖利率", r"殖利率"), ("利率", r"利率"), ("融資", r"融資|籌資|增資"), ("產值", r"產值"), ("出貨", r"出貨"), ("餘額", r"餘額"),
           ("市值", r"市值"), ("訂單", r"訂單|合約"), ("油價", r"油價|金價|布蘭特|西德州"), ("股價", r"股價|收盤價|盤後")]
METRICS_PAT = dict(METRICS)
FIN = {"EPS", "毛利率", "營業利益", "淨利", "虧損", "營收", "財測", "資本支出"}
EVENTW = {"指數": "收盤", "買超": "法人動向", "賣超": "法人動向", "成交值": "成交", "殖利率": "利率", "利率": "利率",
          "資本支出": "資本支出", "財測": "財測", "融資": "融資", "價格": "價格"}
# 標題寫「財報」的條件：報導本身是在講這一期的財報／法說（2026-10-29 第二輪：Google 那則講 TPU 外售、順帶提第 2 季雲端營收，標題卻寫「第2季財報」）
EARN_EV = r"財報|法說|自結|財務報告|營運報告|季報|每股(純益|盈餘|稅後|賺)|EPS|公布.{0,6}(季|年度?)(營收|業績|獲利)"
GUIDE = r"估|預估|預期|展望|可望|目標|財測|指引|上看|料|將"
# 分部營收的限定詞：標題要帶出來（「雲端營收」不能寫成「營收」）
SEG = r"雲端|AI|資料中心|車用|伺服器|手機|PC|晶圓代工|記憶體|廣告|硬體|軟體|網通|光通訊|遊戲|訂閱|海外|美國|中國|核心|晶片|TPU|GPU"
UNIT_NOTE = {"MWh": "MWh 是百萬瓦時（1 MWh＝1,000 度電），歐洲天然氣批發價習慣以每 MWh 計價",
             "therm": "therm（撒姆）是熱量單位（約 10 萬英熱單位），英國天然氣以每 therm 計價",
             "MMBtu": "MMBtu 是百萬英熱單位，美國天然氣與亞洲液化天然氣常用這個單位計價",
             "桶": "原油以「桶」計價，1 桶約 159 公升",
             "盎司": "黃金、白銀以金衡盎司計價，1 盎司約 31.1 公克",
             "英兩": "黃金、白銀以金衡盎司（英兩）計價，1 英兩約 31.1 公克"}
JUNK = r"跌停|漲停|家數|檔|張|名|人|歲|年$"
GROWTH = r"年增|季增|月增|年減|季減|月減|較|同期|成長|衰退|增加|減少|上漲|下跌|漲|跌|下挫|升至|降至|新高|新低|上升|下降|增長|翻倍"
EMPTY = ["指數點數反映", "家媒體", "則報導", "營收是公司銷售", "每股純益（EPS）是", "年增減是", "季增減是", "月增減是", "成交值是當天"]
REL = {"cpi": "美國 CPI 物價", "pce": "美國 PCE 物價", "gdp": "美國 GDP", "nfp": "美國非農就業", "payems": "美國非農就業",
       "fomc": "聯準會 FOMC 利率決議", "ppi": "美國 PPI", "retail": "美國零售銷售", "unrate": "美國失業率"}
TITLE_MAX = 12
GENERIC = {"全台", "材料", "台灣", "中華", "國際", "美國", "大眾", "統一", "華南", "第一", "合庫", "新光", "全國", "亞洲", "世界", "大立", "東方",
           "通訊"}     # 「通訊」(6404) 會被「光通訊」誤認（10-29 第二輪：康寧、穩懋兩則主體變成「通訊」）
# 金額類指標的主旨數字不能是百分比（「光通訊營收飆44%」「AI營收占比25%」是成長率／占比，不是營收本身）
TW_MARKET = {"指數", "融資", "買超", "賣超", "成交值", "餘額"}     # 台股盤勢／籌碼類：封面用台股通用圖，不照內文順帶的產業字配圖
AMOUNT_METRIC = {"營收", "淨利", "營業利益", "EPS", "資本支出", "市值", "出貨", "訂單", "產值", "餘額", "買超", "賣超", "成交值", "融資", "虧損"}
IG_MAX = 2000          # IG 貼文說明上限 2,200 字；留 200 字餘裕，與 run_slot 的 2,000 字閘一致
MIN_BODY = 400          # 10-29：500 擋掉 443／453 字、段落都有實際數字的稿；空泛句另有 EMPTY 與「和前期比」閘把關


class Skip(Exception):
    pass


def metric_of(label: str) -> str | None:
    for k, pat in METRICS:
        if re.search(pat, label):
            return k
    return None


def period_of(text: str) -> str:
    m = re.search(r"第[一二三四1-4]季|Q[1-4]|前三季|上半年|全年|[1-9]{1,2}月(?!\d)", text)
    if not m:
        return ""
    p = m.group(0)
    return {"Q1": "第1季", "Q2": "第2季", "Q3": "第3季", "Q4": "第4季"}.get(p, p)


# 主體辨識的補充規則（2026-10-29 盤前 9 則全被判「找不到主體」後補）：機構、商品、括號標頭、登興櫃、標題開頭的專有名詞
BANKS = r"(?:泰國|美國|日本|英國|南韓|韓國|澳洲|紐西蘭|加拿大|瑞士|瑞典|挪威|印度|印尼|菲律賓|馬來西亞|越南|巴西|墨西哥|土耳其|俄羅斯|南非|中國|台灣|我國|歐洲|新加坡|香港)?(?:央行|中央銀行)"
INST = ["聯準會", "Fed", "FOMC", "歐洲央行", "ECB", "日銀", "日本銀行", "英格蘭銀行", "人行", "人民銀行", "金管會", "主計總處", "國發會",
        "經濟部", "財政部", "美國商務部", "美國勞工部", "OPEC+", "OPEC", "IMF", "世界銀行", "WTO"]
COMMOD = r"(?:(?:歐洲|美國|亞洲|國際|紐約|倫敦)?(?:天然氣|原油|布蘭特原油|西德州原油|油價|金價|黃金|白銀|銀價|銅價|鐵礦砂|小麥|黃豆|比特幣))"
STOPW = {"核心", "房產", "房市", "焦點股", "風向球", "財報", "法說", "營收", "快訊", "焦點", "盤前", "盤後", "台股", "美股", "陸股", "港股", "日股", "市場", "外資", "投信", "分析師", "專家",
         "今年", "明年", "去年", "全年", "公司", "業者", "法人", "官方", "政府", "報告", "研調", "調查", "美國", "中國", "全球", "國際", "亞洲", "歐洲"}
ENG_STOP = {"IPO", "AI", "CEO", "CFO", "EPS", "ETF", "GDP", "CPI", "PCE", "HBM", "GPU", "CPU", "ASIC", "Q1", "Q2", "Q3", "Q4", "PC", "EV"}
VERBS = r"(?:搭上|宣布|公布|推出|發布|發表|營收|獲利|淨利|股價|市值|財報|法說|擬|將|攜手|砸|收購|併購|上市|掛牌|登|第[一二三四1-4]季|Q[1-4]|前三季|上半年|每股|今年|明日|今日|再|又|首度|大舉|傳)"


def _alias(names: dict) -> dict[str, str]:
    """簡稱 → 代號（同名取第一個）；排掉含英數字的（ETF、債券）與太泛的字。"""
    out = {}
    for k, v in names.items():
        if len(v) >= 2 and not re.search(r"[A-Za-z0-9]", v) and v not in GENERIC:
            out.setdefault(v, k)
    return out


def _proper(t: str) -> str:
    """標題裡的專有名詞（外國公司、未上市公司）：英文大小寫混合的字，或子句開頭 2～6 個中文字後面接動詞／期間。"""
    for m in re.finditer(r"(?<![A-Za-z])([A-Z][a-z][A-Za-z0-9&.]{1,20}|[A-Z]{2,}[a-z][A-Za-z]*)(?![A-Za-z])", t):
        w = m.group(1)
        if w not in ENG_STOP:
            return w
    t = re.sub(r"(?<=[\u4e00-\u9fff]) (?=Q[1-4]|\d)", "", t)       # 「康寧 Q3 核心營收」：名字後面隔一個空白接期間也算
    for seg in re.split(r"[ 　，,、！!？?：:；;〈〉【】「」『』（）()／]+", t):
        m = re.match(r"([\u4e00-\u9fff]{2,6}?)" + VERBS, seg)
        if m and m.group(1) not in STOPW and not re.search(r"[增減漲跌賺虧億萬元點%]", m.group(1)) \
                and not re.match(r"房市|房價|市場|台股|美股|陸股|港股|傳統|人類", m.group(1)) \
                and not re.match(r"[本上下單今明去前近首全各多逾約該此這那其兩三四五六七八九十]", m.group(1)):   # 「本季」「上半年」這類不是名字
            return m.group(1)
    return ""


FLOW_WHO = {"三大法人", "外資", "投信", "自營商"}


def subject_of(c: dict, names: dict) -> tuple[str, str]:
    """(主體名稱, 台股代號或空)；找不到回 ('', '')。
    順序：標題裡的上市櫃／興櫃簡稱與已知機構（取最前面的；新聞代號清單裡有的優先；籌碼類以被買賣的公司為主）→〈XX法說〉括號標頭 → 央行／機構 →
    「XX…登興櫃」→ 商品與地區市場 → 新聞代號（只有一檔、或摘要寫到它）→ 標題開頭的專有名詞（外國公司）。"""
    t = sanitize(c["lead"]["title"])
    codes = [x for x in str(c["lead"].get("codes") or "").split(",") if x and not x.startswith("US-")]
    al = _alias(names)
    if codes and names.get(codes[0]) and names[codes[0]] in t:
        al.setdefault(names[codes[0]], codes[0])          # 名字含英數字（M31）或太泛被 _alias 排掉的，只要真的出現在標題也算

    def first(words):
        best = None
        for v in words:
            k = t.find(v)
            if k >= 0 and (best is None or (k, -len(v)) < (best[0], -len(best[1]))):
                best = (k, v)
        return best
    # 10-29：新聞自帶的代號清單常常是「內文提到的所有個股」，第一個不一定是主體（「外資大砍友達…」帶 2330,2409 → 被判成台積電，
    # 相關公司也跟著列錯）。改成以標題為準：標題裡最先出現的公司／機構＝主詞；代號只在標題完全沒有主體時才當備援。
    tagged = [v for v in al if al[v] in codes]
    co = first(tagged) or first(al)                        # 台股公司：先找新聞代號清單裡、標題也寫到的那家
    if co and codes and co[1] not in tagged and len(co[1]) <= 2:
        co = None                                          # 兩個字的簡稱又不在代號清單 → 多半是一般詞（「回收及再生」的再生、「衛星通訊」的星通）
    en = first(ENT + INST)                                 # 外國公司、機構、指數、法人
    if en and co and en[1] in FLOW_WHO:
        en = None                                          # 籌碼類（外資／投信／自營商／三大法人買賣某檔）：以被買賣的那家為主
    best = min([x for x in (co, en) if x], key=lambda x: (x[0], -len(x[1])), default=None)
    if best:
        return best[1], al.get(best[1], "")
    m = re.match(r"^[〈【\[]\s*([^〉】\]]{2,8}?)\s*(?:法說|財報|營收|獲利|股東會|重訊|快訊)?[〉】\]]", t)
    if m and m.group(1) not in STOPW:
        return m.group(1), al.get(m.group(1), "")
    m = re.search(BANKS, t)
    if m:
        return m.group(0), ""
    m = re.search(r"([\u4e00-\u9fff]{2,6}?)(?:明日|今日|今天|即將|將|於)?[^，。 ]{0,20}?登(?:錄)?(?:興櫃|創新板|上櫃|上市)", t)
    if m and m.group(1) not in STOPW:
        return m.group(1), al.get(m.group(1), "")
    m = re.search(COMMOD, t)
    if m:
        return m.group(0), ""
    summ = sanitize(c["lead"].get("summary") or "")
    if len(codes) == 1 and names.get(codes[0]) or codes and names.get(codes[0]) and names[codes[0]] in summ:
        return names[codes[0]], codes[0]       # 標題沒寫公司名、摘要開頭寫了 → 才用新聞自帶的代號
    w = _proper(t)
    if not w and not codes:                    # 標題只寫「沙烏地航運巨頭」→ 摘要裡的英文公司名（Bahri）；有台股代號的新聞不這樣撈（10-29：選股專欄被撈成 Anthropic）
        m = re.search(r"(?<![A-Za-z])([A-Z][a-z][A-Za-z0-9&.]{1,20})(?![A-Za-z])", sanitize(c["lead"].get("summary") or ""))
        w = m.group(1) if m and m.group(1) not in ENG_STOP else ""
    return (w, al.get(w, "")) if w else ("", "")


def chain_of(code: str) -> str:
    try:
        import yaml
        cfg = yaml.safe_load((ROOT / "pipeline" / "groups" / "groups.yaml").read_text("utf-8")) or {}
        for g in (cfg.get("groups") or {}).values():
            if isinstance(g, dict) and code in [str(x) for x in g.get("codes") or []] and g.get("chain"):
                return g["chain"]
    except Exception:
        pass
    return ""


def landing(c: dict, code: str) -> str:
    """落點（法遵：不導個股頁）：台股公司 → #industry/<產業鏈>；財報 → #earnings；台股盤勢 → #market/inst；
    半導體／AI → #industry/semiconductor；其餘首頁。規則同 social_snap.pick_landing。"""
    if code:
        ch = chain_of(code)
        if ch:
            return f"industry/{ch}"
    if c["ctype"] == "財報數字" or c["cat"] == "財報":
        return "earnings"
    if c["cat"] == "台股":
        return "market/inst"
    if re.search(r"半導體|晶片|AI|記憶體|HBM|CoWoS|伺服器", c["text"]):
        return "industry/semiconductor"
    return ""


# ---------------- 相關公司（10-29 Andy：「可以的話需要附上相關股票 公司做哪塊 簡單補充」「以後文章都是，但是跟這類有關才要」） ----------------
# 資料來源一律是 Andy 維護的 pipeline/groups/supply_chain.yaml（環節＋公司 tech）與 groups.yaml（族群），不憑記憶編。
# 只列台股（4 碼代號）；對不到族群／環節的文章（總經、央行、匯率、商品、盤勢籌碼）整節省略，不硬湊。
# 這一節只是產業分工說明：不寫買賣、推薦、受惠這類字；整節過不了 news_legal.check 就拿掉這一節，不擋整篇。
REL_HEAD = "🏢 #相關公司"
REL_FOOT = "（依本站產業地圖整理的產業分工說明）"
REL_RE = re.compile(re.escape(REL_HEAD) + r"\n.*?" + re.escape(REL_FOOT), re.S)
_SC = None
# 外國公司／產業新聞：標題（含主體名）命中關鍵字 → 對應環節的台股。由上往下第一個命中為準（專有名詞在前、泛稱在後）。
# (產品／技術關鍵字：比對標題＋主體, 外國公司名：只比對主體, 對應環節)。由上往下第一個命中為準（專有名詞在前、泛稱在後）。
# 外國公司名只看主體，不看標題順帶提到的（10-29 試跑：「Google 找上甲骨文 搶輝達 AI 晶片生意」主體是 Google，不該因為「輝達」帶出 AI 伺服器組裝廠）。
TOPIC_SEG = [
    (r"ABF|載板", "", [dict(seg="abf_pcb", n=3)]),
    (r"CoWoS|先進封裝|SoIC", "", [dict(seg="foundry", codes=["2330"]), dict(seg="osat_test", codes=["3711"]), dict(seg="pkg_equipment", n=2)]),
    (r"HBM|記憶體|DRAM|NAND", r"SK海力士|海力士|美光|Micron|鎧俠|Kioxia|SanDisk|三星", [dict(seg="dram_nor", n=3), dict(seg="osat_test", codes=["6239"])]),
    (r"散熱|液冷|水冷", "", [dict(seg="thermal", n=4)]),
    (r"光通訊|CPO|矽光子|光模組|光收發", "", [dict(seg="optical", n=3)]),
    (r"CCL|銅箔基板", "", [dict(seg="ccl", n=3)]),
    (r"PCB|電路板", "", [dict(seg="hdi_pcb", n=3)]),
    (r"交換器", "", [dict(seg="switch", n=1), dict(seg="ic_design", codes=["2379"])]),
    (r"ASIC", r"博通|Broadcom|Marvell|邁威爾", [dict(seg="ip_eda", codes=["3443", "3661", "3035"])]),
    (r"AI ?伺服器|GB[23]00", r"輝達|NVIDIA", [dict(seg="assembly", codes=["2317", "2382", "3231"]), dict(seg="foundry", codes=["2330"])]),
    (r"晶圓代工", r"英特爾|Intel", [dict(seg="foundry", n=3)]),
]
REL_SKIP_SUBJ = r"央行|聯準會|Fed|FOMC|ECB|日銀|英格蘭銀行|人行|金管會|主計總處|國發會|指數|台股|美股|油價|金價|天然氣|原油|黃金|白銀|銅價|比特幣"


def _supply_chain() -> dict:
    global _SC
    if _SC is None:
        try:
            import yaml
            _SC = yaml.safe_load((ROOT / "pipeline" / "groups" / "supply_chain.yaml").read_text("utf-8")) or {}
        except Exception:
            _SC = {}
    return _SC


def _tw(c: dict) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(c.get("ticker") or "")))


def rel_role(c: dict) -> str:
    """「做哪一塊」：環節短名＋「做」tech 前一兩項（例：「IC 載板，做 ABF 載板、HDI」）。全部取自 supply_chain.yaml。"""
    seg = {s["id"]: s for s in _supply_chain().get("segments") or []}.get(c.get("segment"), {})
    name = re.split(r"\s*[（(]", str(seg.get("name") or ""))[0].replace(" / ", "／").strip()
    tech, n = [], 0
    for t in (re.sub(r"（[^）]*）|\([^)]*\)", "", str(x)).strip() for x in (c.get("tech") or [])):
        if not t:
            continue
        if tech and (n + len(t) > 22 or len(tech) >= 2):
            break                          # 只取前面的主力項目；不跳著挑（跳著挑會挑到跟主題無關的副業）
        tech.append(t); n += len(t)
    if tech and name:
        return f"{name}，做{' ' if re.match(r'[A-Za-z0-9]', tech[0]) else ''}{'、'.join(tech)}"
    return name or "、".join(tech)


def rel_line(c: dict) -> str:
    return f"・{re.sub(r'[-－](KY|創|DR)$', '', c['name'])}（{c['ticker']}）：{rel_role(c)}"


def rel_from_spec(spec: list[dict], exclude: set[str] | None = None, cap: int = 6) -> list[str]:
    """spec：[{seg: 環節 id, n: 取前幾家} 或 {seg, codes: [指定代號]}]，依 supply_chain.yaml 的公司順序。"""
    ex = set(exclude or ()); out = []
    comps = [c for c in _supply_chain().get("companies") or [] if _tw(c)]
    for sp in spec or []:
        pool = [c for c in comps if c.get("segment") == sp.get("seg") and str(c["ticker"]) not in ex]
        if sp.get("codes"):
            order = [str(x) for x in sp["codes"]]
            pool = sorted([c for c in pool if str(c["ticker"]) in order], key=lambda c: order.index(str(c["ticker"])))
        for c in pool[: sp.get("n", len(pool))]:
            if len(out) >= cap:
                break
            ex.add(str(c["ticker"])); out.append(rel_line(c))
    return out


def rel_for_code(code: str, names: dict | None = None, cap: int = 5) -> list[str]:
    """台股主體：同環節其他公司（≤2）＋上游供應商（≤2）＋下游客戶（≤1），取自 supply_chain.yaml 的 segment 與 supplies 邊；
    supply_chain 沒有這家 → groups.yaml 同族群的其他公司（角色＝族群名稱與說明）。"""
    sc = _supply_chain(); comps = sc.get("companies") or []
    me = next((c for c in comps if str(c.get("ticker")) == code), None)
    if me:
        byid = {c["id"]: c for c in comps}
        same = [c for c in comps if c is not me and c.get("segment") == me.get("segment") and _tw(c)][:2]
        sup = [e for e in sc.get("edges") or [] if e.get("rel") == "supplies"]
        up = [byid[e["from"]] for e in sup if e.get("to") == me["id"] and e.get("from") in byid and _tw(byid[e["from"]])][:2]
        down = [byid[e["to"]] for e in sup if e.get("from") == me["id"] and e.get("to") in byid and _tw(byid[e["to"]])][:1]
        out, seen = [], {code}
        for c in same + up + down:
            if str(c["ticker"]) not in seen and len(out) < cap:
                seen.add(str(c["ticker"])); out.append(rel_line(c))
        if out:
            return out
    try:
        import yaml
        cfg = yaml.safe_load((ROOT / "pipeline" / "groups" / "groups.yaml").read_text("utf-8")) or {}
    except Exception:
        return []
    names = names or {}
    for g in (cfg.get("groups") or {}).values():
        codes = [str(x) for x in (g.get("codes") or [])] if isinstance(g, dict) else []
        if code in codes:
            role = str(g.get("name") or "").strip()
            known = {str(c.get("ticker")): c for c in comps if _tw(c)}
            out = [rel_line(known[x]) if x in known else f"・{names[x]}（{x}）：{role}"     # supply_chain 有的用它的「做哪一塊」，沒有才用族群名稱
                   for x in codes if x != code and (x in known or names.get(x))]
            return out[:min(cap, 4)]
    return []


def rel_section(lines: list[str], note: str = "", min_n: int = 2) -> str:
    """組「🏢 #相關公司」一節；家數不足或過不了法遵就回空字串（整節省略，不擋整篇）。"""
    if len(lines) < min_n:
        return ""
    sec = REL_HEAD + "\n" + (note.strip() + "\n" if note.strip() else "") + "\n".join(lines[:6]) + "\n" + REL_FOOT
    return "" if any(re.search(p, sec) for p, _ in __import__("news_legal").FORBID) else sec


def rel_news(c: dict, subj: str, code: str, names: dict) -> str:
    """新聞稿的相關公司：台股主體 → 同環節＋上下游；外國公司／產業 → 標題命中的題材環節；總經、央行、商品、盤勢 → 省略。"""
    if c.get("cat") == "總經" or c.get("ctype") in ("總經數據", "盤勢數字") or re.search(REL_SKIP_SUBJ, subj or ""):
        return ""
    if code:
        sec = rel_section(rel_for_code(code, names))
        if sec:
            return sec
    t = sanitize(c["lead"]["title"])                     # 產品關鍵字只看標題（主體若是從摘要撈的英文字，不拿來對題材）
    for pat, who, spec in TOPIC_SEG:
        if re.search(pat, t) or (who and re.search(who, subj or "")):
            return rel_section(rel_from_spec(spec, exclude={code} if code else None, cap=5))
    return ""


def rel_evergreen(e: dict) -> str:
    """常備文庫：evergreen.json 的 related＝{segs: [spec...], note: 前言}；沒有 related 或空 → 不放（總經、籌碼、財報名詞）。"""
    r = e.get("related") or {}
    return rel_section(rel_from_spec(r.get("segs") or []), r.get("note", ""), min_n=3) if r.get("segs") else ""


EARN_VERB = re.compile(r"(公布|發布|揭曉|出爐|舉行|召開|登場|發表)[^，。；]{0,8}(財報|法說|業績|季報|財務報告|營運成果)"
                       r"|(財報|法說會?|業績)[^，。；]{0,4}(將於|預計|訂於|定於)|(財報|法說會?)[^，。；]{0,3}(陸續)?(登場|出爐|揭曉)")
WD = "一二三四五六日"


def _event_date(cl: str, ts: datetime):
    """子句裡的日期 → (起, 迄)；相對日期（周四、下周二、今晚、明天）以報導發布日推算；只寫「本週／下週」回那一週（週一～週日）。
    推不出回 None；已經過去的由呼叫端判斷。"""
    from datetime import date
    base = ts.date()
    m = re.search(r"(\d{1,2})月(\d{1,2})日|(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])", cl)
    if m:
        mo, dd = int(m.group(1) or m.group(3)), int(m.group(2) or m.group(4))
        y = base.year + (1 if mo < base.month - 6 else 0)
        try:
            return (date(y, mo, dd),) * 2
        except ValueError:
            return None
    m = re.search(r"[（(](\d{1,2})日[）)]", cl)
    if m:
        dd = int(m.group(1)); mo, y = (base.month, base.year) if dd >= base.day else (base.month % 12 + 1, base.year + (base.month == 12))
        try:
            return (date(y, mo, dd),) * 2
        except ValueError:
            return None
    mon = base - timedelta(days=base.weekday())
    m = re.search(r"(下)?(?:周|週|星期)([一二三四五六日])", cl)
    if m:
        d0 = mon + timedelta(days=WD.index(m.group(2)) + (7 if m.group(1) else 0))
        return (d0, d0) if d0 >= base else None
    if re.search(r"明天|明日|明晚", cl):
        return (base + timedelta(days=1),) * 2
    if re.search(r"今天|今日|今晚|稍晚", cl):
        return (base, base)
    m = re.search(r"(本|這|下)(?:周|週)", cl)
    if m:
        w0 = mon + timedelta(days=7 if m.group(1) == "下" else 0)
        return (w0, w0 + timedelta(days=6))
    return None


def next_corp_event(subj: str, day: str, before: datetime) -> str:
    # before＝這則報導的時間：同一天「今天公布財報」講的就是這則報導本身，不算「下一次」
    """資料湖新聞裡「<主體>…將於 X 公布財報／舉行法說會」→ 下一次財報日（只取今天以後、60 天內最近的一個）。
    2026-10-29 第二輪：美國公司的「接下來觀察」一律接非農，改成先找公司自己的下一次財報日。"""
    from datetime import date
    al = aliases_of(subj)
    d0 = date.fromisoformat(day)
    best = None
    for n in _hist_news(before):
        for cl in re.split(r"[，。；！？]", (n["title"] or "") + "，" + (n["summary"] or "")):
            if not any(a in cl for a in al):
                continue
            mv = EARN_VERB.search(cl)
            if not mv:
                continue
            rng_ = _event_date(cl, n["ts"])
            if not rng_ or rng_[1] < d0 or rng_[1] <= before.date() or rng_[0] > d0 + timedelta(days=60):
                continue
            what = "舉行法說會" if "法說" in mv.group(0) else "公布財報"
            exact = rng_[0] == rng_[1]
            cand = (not exact, rng_[1], -n["ts"].timestamp(), rng_, what, n)     # 確切日期優先，其次最近、最新的報導
            if best is None or cand[:3] < best[:3]:
                best = cand
    if not best:
        return ""
    _, _, _, (a0, a1), what, n = best
    when = f"{a0.month}/{a0.day} " if a0 == a1 else f"{a0.month}/{a0.day}～{a1.month}/{a1.day} 這一週"
    return (f"{subj}預計 {when}{what}（{SRC_NAME.get(n['source'], n['source'])} {n['ts'].month}/{n['ts'].day} 的報導），"
            f"可以對照這次報導提到的數字，看實際公布的結果。")


# 找不到公司自己的財報日 → 跟這個產業／主題相關的總經數據，寫清楚為什麼相關（偵測順序＝表格順序；先看主體與標題，沒中才看摘要）
MACRO_WHY = [
    (r"天然氣|原油|油價|布蘭特|西德州|OPEC|能源|油輪|煉油|LNG",
     (("cpi", "能源價格是 CPI 物價的組成項目，油氣價格的變動會反映在下一次公布的通膨數字"),
      ("pce", "能源價格是 PCE 物價的組成項目，油氣價格的變動會反映在下一次公布的通膨數字"))),
    (r"金價|黃金|白銀|銀價",
     (("fomc", "金價對美元利率很敏感，聯準會的利率決議會影響持有黃金的機會成本"),
      ("cpi", "金價對通膨與利率預期很敏感，CPI 物價會影響市場對聯準會利率走向的判斷"))),
    (r"央行|聯準會|Fed|FOMC",
     (("fomc", "各國央行調整利率時常參考美國聯準會的動向，FOMC 的決議會牽動全球利率"),)),
    (r"(?<!獲)利率|殖利率|公債|美債|債券|公司債|融資成本",
     (("fomc", "債券殖利率與企業的融資成本跟市場利率連動，聯準會的利率決議會直接影響借錢的成本"),)),
    (r"銀行|金融|保險|放款|房貸|信貸",
     (("fomc", "金融業的利差與資金成本跟利率直接相關，聯準會的利率決議會影響這個產業的獲利"),)),
    (r"零售|消費|電商|餐飲|蘋果|Apple|亞馬遜|Amazon|特斯拉|Tesla|電動車|汽車|手機",
     (("pce", "這類公司的營收跟美國民眾的消費力道直接相關，PCE 物價與個人消費支出會反映消費者的購買力"),
      ("cpi", "這類公司的營收跟美國民眾的消費力道直接相關，CPI 物價高低會影響消費者的實質購買力"))),
    (r"AI|雲端|晶片|半導體|伺服器|記憶體|HBM|GPU|TPU|ASIC|資料中心|軟體|科技|輝達|微軟|Google|Alphabet|Meta|博通|超微|甲骨文|美光",
     (("cpi", "大型科技與 AI 股的估值對利率較敏感，CPI 物價的高低會影響市場對聯準會降息時點的預期"),
      ("fomc", "大型科技與 AI 股的估值對利率較敏感，聯準會的利率決議會直接影響這類股票的評價"))),
    (r"經濟成長|GDP|景氣|出口|製造業",
     (("gdp", "經濟成長率直接反映整體景氣的冷熱"), ("nfp", "非農就業反映美國整體景氣與企業的用人需求"))),
]
MACRO_DEFAULT = (("nfp", "非農就業反映美國整體景氣與企業的用人需求"), ("cpi", "CPI 物價會影響市場對聯準會利率走向的判斷"))


def _macro_dates(day: str) -> dict[str, str]:
    """{release: 下一個公布日（美東）}；CPI／PCE／GDP／非農用資料湖 macro_calendar，FOMC 用 pipeline/calendar/macro_events.yaml。"""
    out: dict[str, str] = {}
    try:
        import pandas as pd
        fs = sorted((ROOT / "data" / "macro_calendar").glob("**/*.parquet"))
        mc = pd.concat([pd.read_parquet(f) for f in fs])
        for r in mc[mc["date"].astype(str) > day].sort_values("date").to_dict("records"):
            out.setdefault(str(r["release"]).lower(), str(r["date"])[:10])
    except Exception:
        pass
    try:
        import yaml
        cfg = yaml.safe_load((ROOT / "pipeline" / "calendar" / "macro_events.yaml").read_text("utf-8")) or {}
        ends = sorted(str(m["end"]) for m in (cfg.get("fomc") or {}).get("meetings", []) if str(m.get("end", "")) > day)
        if ends:
            out["fomc"] = ends[0]
    except Exception:
        pass
    return out


def macro_watch(day: str, focus: str, extra: str = "") -> str:
    """跟主題相關的下一個總經數據＋為什麼相關。focus＝主體＋標題（先比對），extra＝摘要（沒中才比對）。"""
    prefs = MACRO_DEFAULT
    for txt in (focus, extra):
        hit = next((p for pat, p in MACRO_WHY if re.search(pat, txt)), None)
        if hit:
            prefs = hit
            break
    dates = _macro_dates(day)
    got = sorted((dates[r], r, w) for r, w in prefs if r in dates)        # 同一主題的幾個相關數據，取最近公布的那個
    if not got:
        return ""
    dd, r, why = got[0]
    return f"下一個要看的是 {int(dd[5:7])}/{int(dd[8:10])}（美國時間）公布的{REL[r]}：{why}。"


def watch_point(day: str, tw: bool, ctype: str, subj: str = "", focus: str = "", extra: str = "", before: datetime | None = None) -> str:
    """接下來觀察：① 主體自己的下一次財報日／法說會（新聞裡有寫日期才用）② 台股公司 → 月營收公布期限
    ③ 其他（美國公司、商品、央行）→ 跟這個產業相關的下一個總經數據，並寫出為什麼相關。"""
    corp = next_corp_event(subj, day, before) if subj and before else ""
    d = datetime.fromisoformat(day)
    if tw:
        nm = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
        s = f"上市櫃公司每月 10 日前公告上月營收，{d.month} 月營收最晚 {nm.month}/10 公布，可以對照這次的數字。"
        if ctype == "財報數字":
            s += "第 4 季（全年）財報依規定在明年 3 月底前公告。"
        return (corp + s) if corp else s
    if corp:
        return corp
    return macro_watch(day, focus, extra)


_HIST = None
# 外國公司的中英別名：「之前的報導」找舊聞、「接下來觀察」找下一次財報日都要認得同一家（Google＝Alphabet＝谷歌）
SUBJ_ALIAS = {"Google": ["Google", "Alphabet", "谷歌", "GOOGL"], "Alphabet": ["Alphabet", "Google", "谷歌", "GOOGL"],
              "輝達": ["輝達", "NVIDIA", "Nvidia", "NVDA"], "NVIDIA": ["NVIDIA", "輝達", "Nvidia", "NVDA"],
              "微軟": ["微軟", "Microsoft", "MSFT"], "蘋果": ["蘋果", "Apple", "AAPL"], "亞馬遜": ["亞馬遜", "Amazon", "AWS", "AMZN"],
              "特斯拉": ["特斯拉", "Tesla", "TSLA"], "博通": ["博通", "Broadcom", "AVGO"], "超微": ["超微", "AMD"], "AMD": ["AMD", "超微"],
              "甲骨文": ["甲骨文", "Oracle", "ORCL"], "英特爾": ["英特爾", "Intel", "INTC"], "美光": ["美光", "Micron"], "高通": ["高通", "Qualcomm"],
              "Meta": ["Meta", "臉書"], "台積電": ["台積電", "TSMC"], "SK海力士": ["SK海力士", "海力士"], "三星": ["三星", "Samsung"]}


def aliases_of(subj: str) -> list[str]:
    return SUBJ_ALIAS.get(subj, [subj])


def _hist_news(before: datetime) -> list[dict]:
    global _HIST
    if _HIST is None:
        _HIST = load_news(before - timedelta(days=45), before + timedelta(days=1))
    return _HIST


HIST_METRIC = r"^(第[一二三四1-4]季|Q[1-4]|前三季|前[1-4]季|上半年|全年|今年|單季|[1-9]{1,2}月)?(合併)?(營收|毛利率|營益率|營業利益|EPS|每股|稅後|稅前|淨利|純益|獲利|資本支出|出貨)"


def _other_entity(cl: str, subj: str, names: dict | None) -> bool:
    al = set(aliases_of(subj))
    pool = ENT + INST + ([v for v in _alias(names)] if names else [])
    return any(v in cl and v not in al and not any(v in a or a in v for a in al) for v in pool if len(v) >= 2)


def hist_clause(cl: str, subj: str, names: dict | None = None) -> str:
    """「之前的報導」一個子句：有寫主體 → 原樣；沒寫主體但開頭就是財報指標、且沒提到別家 → 補上主體；其他 → 丟掉（回空字串）。
    2026-10-29 第二輪：出現「10/23 經濟日報：年增24.2％。」這種看不出是誰的片段。"""
    cl = cl.strip()
    if len(cl) < 6:
        return ""
    if any(a in cl for a in aliases_of(subj)):
        return cl
    if re.match(HIST_METRIC, cl) and not _other_entity(cl, subj, names):
        return subj + cl
    return ""


def history(subj: str, before: datetime, n: int = 2, names: dict | None = None) -> list[str]:
    """資料湖裡同一主體在本則之前 45 天內、含數字的報導重點（給「背景」段做前期對照）；每個子句都要看得出主體。"""
    al = aliases_of(subj)
    rows = [x for x in _hist_news(before) if x["ts"] < before - timedelta(hours=12) and any(a in x["title"] for a in al)]
    out, seen = [], set()
    for x in sorted(rows, key=lambda x: x["ts"], reverse=True):
        cl = [c for c in sanitize(x["summary"] or x["title"]).replace("。", "，").split("，") if c.strip() and clean_ok(c) and NUMRE.search(c)]
        cl = [h for h in (hist_clause(c, subj, names) for c in cl) if h][:2]
        k = "".join(cl)
        if cl and k not in seen:
            seen.add(k)
            out.append(f"{x['ts'].month}/{x['ts'].day} {SRC_NAME.get(x['source'], x['source'])}：{'，'.join(cl)}。")
        if len(out) >= n:
            break
    return out


def _fmt(x: dict) -> str:
    return f"{x['value']}{'' if x['unit'] == '%' else ' '}{x['unit']}"


def _fmt_full(x: dict) -> str:
    """內文用：原文寫「約2成」的，換算成 % 後把原文寫法附在後面，讀者對得上報導。"""
    return _fmt(x) + (f"（報導寫「{x['orig']}」）" if x.get("orig") else "")


def _quarter_unfinished(period: str, day: str) -> bool:
    """標題期間還沒結束（10 月講「第4季」、年中講「全年」）→ 這個數字只能是預估，不能叫「財報」。"""
    d = datetime.fromisoformat(day)
    m = re.match(r"第([一二三四1-4])季", period)
    if m:
        q = {"一": 1, "二": 2, "三": 3, "四": 4}.get(m.group(1)) or int(m.group(1))
        return q == (d.month - 1) // 3 + 1
    return period == "全年" and d.month >= 4


def title_parts(key: dict, title: str, summary: str, day: str) -> tuple[str, str, str]:
    """(期間, 事件, 分部限定詞)：期間優先取主旨數字自己的標籤；標籤沒寫期間，只有標題本身在講財報時才借標題的期間。
    事件：財報類指標＋期間 → 報導是在講財報才寫「財報」；數字是預估（標籤有估／可望、或期間還沒結束）寫「展望」；都不是就不寫事件。"""
    km, lab = key["metric"], key["label"]
    earn = bool(re.search(EARN_EV, title)) or bool(re.search(EARN_EV, summary[:80]))
    period = period_of(lab) or (period_of(title) if earn and km in FIN else "")
    seg = ""
    if km in ("營收", "營業利益", "淨利"):
        mp = re.search(METRICS_PAT[km], lab)
        ms = re.search(r"(" + SEG + r")$", lab[:mp.start()]) if mp else None
        seg = ms.group(1) if ms else ""
    if km in FIN and period:
        if re.search(GUIDE, lab) or _quarter_unfinished(period, day):
            ev = "展望"
        else:
            ev = "財報" if earn and not seg else ""
    else:
        ev = EVENTW.get(km, "")
        if km == "殖利率":
            ev = "債券" if re.search(r"債", title) else ""      # 「CoreWeave債券殖利率飆15%」→「CoreWeave債券」，不是「CoreWeave利率」
        if km == "指數" and re.search(r"盤中|早盤|開盤|午盤", title):
            ev = "盤中"                   # 「盤中速報」不是收盤
    return period, ev, seg


def compose(c: dict, slot: str, idx: int, day: str, style: str, names: dict) -> dict:
    """結構化產稿；資料不足或品質閘不過丟 Skip(原因)。"""
    lead = c["lead"]; ymd = day.replace("-", ""); md = f"{lead['ts'].month}/{lead['ts'].day}"
    subj, code = subject_of(c, names)
    if not subj:
        raise Skip("找不到主體（公司／機構／指數）")
    nums = [x for x in c["nums"] if not re.search(JUNK, x["label"])]
    fx = set(re.findall(r"人民幣|日圓|日幣|韓元|歐元|港元|港幣|英鎊", c["text"]))
    if len(fx) == 1 and not re.search(r"新台幣|台幣", c["text"]):       # 外幣報導：「萬元」實為人民幣等，單位寫清楚（10-29 摩爾線程）
        cur = fx.pop()
        for x in nums:
            if x["unit"] in ("元", "萬元", "億元", "兆元"):
                x["unit"] = x["unit"][:-1] + cur
    for x in nums:
        x["metric"] = metric_of(x["label"]) or ("價格" if "/" in x["unit"] else None)
        x["growth"] = bool(re.search(GROWTH, re.sub(r"(經濟)?成長率", "", x["label"]) if x["metric"] == "經濟成長率" else x["label"]))
    title_raw = sanitize(lead["title"])
    m_close = re.search(r"收(?:在)?\s*([\d,]+(?:\.\d+)?)\s*點", title_raw)
    if c["cat"] == "台股" and m_close:         # 台股盤勢：主旨＝加權指數收盤，漲跌點數當前期比較
        nums = [dict(label="加權指數收盤", value=m_close.group(1), unit="點", key="close", metric="指數", growth=False, verified=False)] + nums
        m_chg = re.search(r"(上漲|下跌|漲|跌)\s*([\d,]+(?:\.\d+)?)\s*點", title_raw)
        if m_chg:
            nums.insert(1, dict(label=f"較前一交易日{'下跌' if '跌' in m_chg.group(1) else '上漲'}", value=m_chg.group(2), unit="點",
                                key="chg", metric="指數", growth=True, verified=False))
    keyc = [x for x in nums if x["metric"] and not x["growth"] and not x.get("range")
            and not (x["unit"] == "%" and x["metric"] in AMOUNT_METRIC)]
    key = next((x for x in keyc if x["value"].lstrip("約逾近超過") in title_raw), keyc[0] if keyc else None)
    if not key:
        raise Skip("沒有可當主旨的關鍵數字")
    km = key["metric"]
    if km == "指數" and re.search(r"櫃買", title_raw):        # 指數新聞的主體是指數本身，不是新聞順帶標的個股代號（10-29：盤中速報被標成「創意」）
        subj, code = "櫃買指數", ""
    elif km == "指數" and re.search(r"加權指數|集中市場|台股|大盤", title_raw):
        subj, code = "台股", ""
    period, ev, seg = title_parts(key, title_raw, sanitize(lead.get("summary") or ""), day)
    if subj.endswith("價") and ev == "價格":
        ev = ""                           # 「金價價格」→「金價」
    l1 = f"{subj}{period}{seg if not ev else ''}{ev}"
    if len(l1) > TITLE_MAX:
        l1 = f"{subj}{period}{ev}"
    if len(l1) > TITLE_MAX:
        l1 = f"{subj}{ev}"
    if len(l1) > TITLE_MAX:
        l1 = subj                         # 主體太長：事件改由第二行的指標名稱帶出
    kmd = (seg + km) if seg and seg not in l1 else km
    l2 = f"{kmd} {_fmt(key).replace(' ', '')}" if re.match(r"[A-Za-z]", kmd[-1]) else f"{kmd}{_fmt(key).replace(' ', '')}"
    if len(l2) > TITLE_MAX and kmd != km:
        l2 = f"{km} {_fmt(key).replace(' ', '')}" if re.match(r"[A-Za-z]", km) else f"{km}{_fmt(key).replace(' ', '')}"
    if km == "指數":
        l2 = ("加權" if c["cat"] == "台股" else "") + _fmt(key).replace(" ", "")
    if km == "價格":
        l2 = _fmt(key).replace(" ", "")       # 「歐洲天然氣價格」／「97.35歐元/MWh」
    cover = [l1, l2]
    # 資訊列：主旨數字＋同一族（財報類／同指標）的相關數字
    fam = FIN if km in FIN else {km}
    rel = [x for x in nums if x is not key and (x["metric"] in fam or (x["growth"] and (x["metric"] in fam or x["metric"] is None)))]
    if len(rel) < 2:
        rel += [x for x in nums if x is not key and x not in rel and x["growth"]]
    def _f(v):
        try:
            return float(re.sub(r"[^\d.]", "", v))
        except ValueError:
            return None
    kv = _f(key["value"])
    rel = [x for x in rel if not (x["unit"] == key["unit"] and kv and _f(x["value"]) and abs(_f(x["value"]) - kv) <= kv * 0.01)]
    _seen = {(key["value"], key["unit"])}
    rel = [x for x in rel if not ((x["value"], x["unit"]) in _seen or _seen.add((x["value"], x["unit"])))]   # 同一個數字只列一次（「較前一交易日上漲 939.35」「上漲 939.35」）
    rows = [key] + rel[:2]
    if len(rows) < 2:
        raise Skip("圖卡資訊列不足 2 列（與主旨相關的數字太少）")
    _cs = set()
    comps = [x for x in nums if x["growth"] and not ((x["value"], x["unit"]) in _cs or _cs.add((x["value"], x["unit"])))]
    hi = re.search(r"[^，。]*(新高|新低|首度|首次|上修|下修|連續第?[\d一二三四五六七八九十]+[次度個])[^，。]*", c["text"])
    if not comps and not hi:
        raise Skip("沒有與前期的比較數字（季增／年增／前高）")
    tw = bool(code) or c["cat"] == "台股"
    wp = watch_point(day, tw, c["ctype"], subj, subj + " " + title_raw, sanitize(lead.get("summary") or ""), lead["ts"])
    if c["cat"] == "台股" and c["ctype"] == "盤勢數字":
        try:
            from social_gate import load_holidays, next_open
            nx = next_open(lead["ts"].strftime("%Y-%m-%d"), load_holidays())
            wp = f"下一個交易日 {nx.month}/{nx.day} 09:00 開盤；三大法人買賣超通常在收盤後下午公布，可以對照今天的收盤與法人動向。"
        except Exception:
            pass
    if not wp:
        raise Skip("找不到下一個觀察點（公布日／數據日）")
    srcname = SRC_NAME.get(lead["source"], lead["source"])
    cite = lambda x: "（兩家來源）" if x.get("verified") else f"（{srcname}報導）"
    route = landing(c, code)
    ucode = f"news{slot}{idx}"
    url_ig = f"{SITE}?u=ig-{ucode}-{ymd}" + (f"#{route}" if route else "")
    url_th = f"{SITE}?u=th-{ucode}-{ymd}" + (f"#{route}" if route else "")
    head = [f"#{subj} {l2}" if l1 == subj else f"#{subj} {l1}：{l2}", f"#{TAG[c['cat']]} {SUBQ[c['ctype']]}", ""]
    intro = f"{md}，{srcname}報導：{_lead_sentence(c)}（{SRC_NAME.get(c.get('lead_src'), srcname)}報導摘述）"
    shown = [x for x in nums if (x["metric"] or x["growth"]) and len(x["label"]) >= 2 and not re.match(r"[含約共逾近]", x["label"])]
    sec_num = "📊 #重點數字\n" + "\n".join(f"▪ {x['label']} {_fmt_full(x)}{cite(x)}" for x in shown[:5])
    cmp_lines = [f"▪ {x['label']} {_fmt_full(x)}" for x in comps[:3]]
    if hi:
        cmp_lines.append(f"▪ 報導提到「{hi.group(0).strip()}」")
    sec_cmp = "🔁 #和前期比\n" + "\n".join(cmp_lines)
    mean = []
    if km == "EPS":
        net = next((x for x in nums if x["metric"] == "淨利" and not x["growth"]), None)
        mean.append(f"{subj}{period}每股賺 {key['value']} 元" + (f"，對應稅後淨利 {_fmt(net)}" if net else "") + "。")
    gm = next((x for x in nums if x["metric"] == "毛利率" and not x["growth"]), None)
    if gm:
        mean.append(f"毛利率 {gm['value']}%，代表每 100 元營收扣掉直接成本後約剩 {gm['value'].lstrip('約逾近')} 元毛利（本站換算）。")
    idx_mode = km == "指數" and c["cat"] == "台股"
    if idx_mode:
        chg = next((x for x in nums if x.get("key") == "chg"), None)
        pct = re.search(r"漲幅\s*([\d.]+)%|跌幅\s*([\d.]+)%", c["text"])
        high = re.search(r"最高\s*([\d,]+(?:\.\d+)?)\s*點", c["text"])
        s1 = f"加權指數收在 {key['value']} 點"
        if chg:
            s1 += f"，{chg['label']} {chg['value']} 點" + (f"（{pct.group(0)}）" if pct else "")
        mean.append(s1 + "。")
        if high:
            hv = float(high.group(1).replace(",", "")); cv = float(key["value"].replace(",", ""))
            mean.append(f"盤中最高 {high.group(1)} 點，收盤距離當天最高點約 {hv - cv:,.2f} 點（本站計算），代表收在接近當天高點的位置。")
    for x in ([] if idx_mode else comps[:2]):
        dn = re.search(r"減|衰退|較.*少|跌|下挫", x["label"])
        lb = x["label"]
        base = ("一個月前" if re.search(r"近一?個?月", lb) else "一週前" if re.search(r"近一?[週周]|本[週周]|單[週周]|[週周][漲跌]", lb)
                else "今年初" if re.search(r"今年以來|年初至今", lb) else "去年同期" if re.search(r"年增|年減|同期|去年|年成長|年衰退", lb) else "上一季" if re.search(r"季增|季減|上季|前季", lb)
                else "上個月" if re.search(r"月增|月減|上月|前月", lb) else "前一交易日" if re.search(r"漲|跌|挫|走高|走低", lb)
                else "")
        if not base:
            continue                              # 看不出跟哪一期比（「營收增加近1800%」「未來2年產能較目前擴編近6倍」），不硬套「去年同期」
        updown = ("下跌" if dn else "上漲") if re.search(r"漲|跌|挫|走高|走低", x["label"]) else ("減少" if dn else "增加")
        mean.append(f"{x['label']} {_fmt_full(x)}，代表和{base}相比{updown}約 {x['value'].lstrip('+-約逾近')}{x['unit']}。")
    if km == "價格":                              # 商品報價：單位白話（MWh、therm、桶、盎司）
        unote = next((v for k, v in UNIT_NOTE.items() if key["unit"].endswith("/" + k)), "")
        sp = lambda t: " " if re.search(r"[A-Za-z]$", t) else ""
        mean.insert(0, f"{key['label']}{sp(key['label'])}報價 {_fmt(key)}" + (f"；{unote}。" if unote else "。"))
        for x in nums:
            if x is not key and x["metric"] == "價格":
                un = next((v for k, v in UNIT_NOTE.items() if x["unit"].endswith("/" + k)), "")
                mean.append(f"{x['label']}{sp(x['label'])}報價 {_fmt(x)}" + (f"；{un}。" if un and un not in "".join(mean) else "。"))
    for mk in ("經濟成長率", "通膨"):              # 總經預測：同一指標兩個期間 → 算差幾個百分點（10-29 泰國央行）
        ps = [x for x in nums if x["metric"] == mk and x["unit"] == "%" and not x["growth"]][:2]
        if len(ps) == 2:
            a0, a1 = (float(x["value"].lstrip("約逾近")) for x in ps)
            dlt = round(a1 - a0, 2)
            how = "持平" if dlt == 0 else f"{'高' if dlt > 0 else '低'} {abs(dlt):g} 個百分點"
            mean.append(f"{ps[0]['label']} {ps[0]['value']}%、{ps[1]['label']} {ps[1]['value']}%，後者比前者{how}（本站計算）。")
    if km not in ("EPS",) and not mean:
        mean.append(f"{key['label']} {_fmt(key)} 是這則報導的核心數字。")
    sec_mean = "🔎 #這些數字代表什麼\n" + "".join(mean)
    other = []
    for n in c["group"]:
        if n is lead or n["source"] == lead["source"]:
            continue
        cl = [x for x in sanitize(n["summary"]).split("，") if x.strip() and clean_ok(x)][:2]
        if cl:
            other.append(f"{SRC_NAME.get(n['source'], n['source'])}報導：{'，'.join(cl)}。")
    sec_more = ("📰 #其他媒體怎麼寫\n" + "\n".join(other[:2])) if other else ""
    hist = history(subj, lead["ts"], names=names)
    sec_hist = ("📌 #之前的報導\n" + "\n".join(hist)) if hist else ""
    sec_watch = "👀 #接下來觀察\n" + wp
    sec_rel = rel_news(c, subj, code, names)
    tail = "以上為公開資料整理，非投資建議"
    body = [intro, sec_num, sec_cmp] + ([sec_mean] if style != "精簡重點" else []) + ([sec_more] if sec_more else []) + ([sec_hist] if sec_hist else []) + ([sec_rel] if sec_rel else []) + [sec_watch]
    link_line = "👉 更多詳細資料可以點擊以下連結："
    cap_ig = "\n".join(head) + "\n" + "\n\n".join(body) + f"\n\n{tail}\n{link_line}\n{url_ig}"
    if sec_rel and len(cap_ig) > IG_MAX:          # IG 文案上限 2,200 字：放不下就拿掉相關公司這節，不擋整篇
        body.remove(sec_rel); sec_rel = ""
        cap_ig = "\n".join(head) + "\n" + "\n\n".join(body) + f"\n\n{tail}\n{link_line}\n{url_ig}"
    threads = pack_threads(["\n".join(head[:2]) + "\n\n" + intro] + body[1:] + [f"{tail}\n{link_line}\n{url_th}"])
    card = dict(title=l1 + l2, subtitle=SUBQ[c["ctype"]], numbers=[{k: x[k] for k in ("label", "value", "unit")} for x in rows],
                category=c["cat"], subject=subj, foot="資料：" + "、".join(dict.fromkeys(SRC_NAME.get(n["source"], n["source"]) for n in c["group"])) + "・本站整理", cover_title=cover, cover_desc=_lines("、".join(f"{x['label']} {_fmt(x)}" for x in comps[:2]) or SUBQ[c["ctype"]], 22),
                hero=key["value"].lstrip("約逾近超過") + key["unit"], hl=_fmt(key).replace(" ", "") if _fmt(key).replace(" ", "") in l2 else "",
                tw=bool(code) or c["cat"] == "台股", photo_hint="tw_market" if km in TW_MARKET and (bool(code) or c["cat"] == "台股") else "",
                photo_text=sanitize(lead.get("summary") or "")[:200])
    d = dict(id=f"{slot}{idx}", slot=slot, data_date=f"{day} 台北", caption_ig=cap_ig, caption_threads=threads,
             card=card, link=url_th, u_code=ucode,
             sources=[{"name": SRC_NAME.get(n["source"], n["source"]) + "：" + n["title"], "url": n["url"],
                       "date": n["ts"].isoformat(timespec="minutes")} for n in c["group"][:6]],
             meta=dict(topic_category=c["cat"], content_type=c["ctype"], layout=LAYOUT, style=style,
                       has_ai_image="false", explore=str(bool(c.get("explore"))).lower(), heat=str(c["heat"]),
                       news_ids=",".join(n["news_id"] for n in c["group"][:8]), u_code=ucode))
    bad = quality_gate(d, key)
    if bad:
        raise Skip("品質閘：" + "；".join(bad))
    return d


def quality_gate(d: dict, key: dict) -> list[str]:
    out = []
    ct = d["card"]["cover_title"]
    for l in ct:
        if not l or len(l) > TITLE_MAX:
            out.append(f"標題行長度 {len(l)}（上限 {TITLE_MAX}）：{l}")
        if "  " in l or l != l.strip() or re.search(r"[\d,]$", l) and not re.search(r"\d$", key["value"]):
            out.append(f"標題斷行或空白異常：{l!r}")
    hv = key["value"].lstrip("約逾近超過")
    if hv not in ct[1] or not d["card"]["hero"].startswith(hv):
        out.append("封面大數字與標題主旨不同")
    body = REL_RE.sub("", d["caption_ig"].rsplit("以上為公開資料整理", 1)[0])    # 相關公司那節不算內文字數（不讓它把太薄的稿撐過門檻）
    if len(body) < MIN_BODY:
        out.append(f"內文 {len(body)} 字（最少 {MIN_BODY}）")
    for w in EMPTY:
        if w in d["caption_ig"]:
            out.append(f"空泛句：{w}")
    if "#stock/" in d["caption_ig"] or any("#stock/" in t for t in d["caption_threads"]):
        out.append("落點不得為個股頁")
    return out


def _tlen(s: str) -> int:
    try:
        from threads_post import _tlen as t
        return t(s)
    except Exception:
        return len(s.encode("utf-8")) // 2


def pack_threads(secs: list[str], lim: int = 480) -> list[str]:
    """依小節邊界拆串，每串 ≤ lim（含串尾 (k/n)）；單一小節太長就在句號處切。"""
    pieces = []
    for s in secs:
        if _tlen(s) <= lim - 10:
            pieces.append(s)
        else:
            cur = ""
            for sent in re.split(r"(?<=[。\n])", s):
                if _tlen(cur + sent) > lim - 10 and cur:
                    pieces.append(cur.strip()); cur = ""
                cur += sent
            if cur.strip():
                pieces.append(cur.strip())
    chunks, cur = [], ""
    for p in pieces:
        nxt = (cur + "\n\n" + p) if cur else p
        if _tlen(nxt) > lim - 10 and cur:
            chunks.append(cur); cur = p
        else:
            cur = nxt
    if cur:
        chunks.append(cur)
    n = len(chunks)
    return [f"{x}\n({i}/{n})" if n > 1 else x for i, x in enumerate(chunks, 1)]


# ---------------- 常備文庫（不靠新聞、不放 AI 圖的備案稿） ----------------
def load_evergreen() -> list[dict]:
    try:
        return json.loads(EVERGREEN.read_text(encoding="utf-8")).get("items", [])
    except Exception:
        return []


def evg_usage() -> dict:
    try:
        return json.loads(EVG_USAGE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick_evergreen(day: str, k: int, taken: set[str], rng: random.Random, prefer: str = "") -> list[dict]:
    """依「最久沒用」輪替挑 k 篇；30 天內用過的排在最後（庫存不夠才輪回）。同分隨機（以日期＋時段為種子，可重現）。
    prefer：想優先的主題分類（例：週末晚上偏產業／總經知識），只是排序加權，不是篩選。"""
    use = evg_usage(); lib = [e for e in load_evergreen() if e["id"] not in taken]
    cut = (datetime.fromisoformat(day) - timedelta(days=EVG_COOLDOWN)).strftime("%Y-%m-%d")
    def key(e):
        last = max(use.get(e["id"], [""]) or [""])
        return (last >= cut, last, rng.random())
    lib.sort(key=key)
    return lib[:k]


def compose_evergreen(e: dict, slot: str, idx: int, day: str) -> dict:
    """常備文庫條目 → 與 compose() 同格式的貼文 dict（法遵與長度閘不過丟 Skip）。"""
    ymd = day.replace("-", ""); ucode = f"news{slot}{idx}"; route = e.get("route", "")
    url_ig = f"{SITE}?u=ig-{ucode}-{ymd}" + (f"#{route}" if route else "")
    url_th = f"{SITE}?u=th-{ucode}-{ymd}" + (f"#{route}" if route else "")
    head = list(e["head"]) + [""]
    sec_watch = "👀 #為什麼值得知道\n" + e["watch"]
    tail = "以上為公開資料整理，非投資建議"
    link_line = "👉 更多詳細資料可以點擊以下連結："
    sec_rel = rel_evergreen(e)
    secs = list(e["sections"]) + ([sec_rel] if sec_rel else [])
    body = [e["intro"]] + secs + [sec_watch]
    cap_ig = "\n".join(head) + "\n" + "\n\n".join(body) + f"\n\n{tail}\n{link_line}\n{url_ig}"
    if sec_rel and len(cap_ig) > 2000:            # 常備文庫 IG 上限沿用 2,000（留 200 字餘裕）：放不下就拿掉相關公司，不擋整篇
        secs.remove(sec_rel); body = [e["intro"]] + secs + [sec_watch]
        cap_ig = "\n".join(head) + "\n" + "\n\n".join(body) + f"\n\n{tail}\n{link_line}\n{url_ig}"
    threads = pack_threads(["\n".join(head[:2]) + "\n\n" + e["intro"]] + secs + [sec_watch, f"{tail}\n{link_line}\n{url_th}"])
    card = dict(title=" ".join(e["cover_title"]), subtitle=e["ctype"], numbers=e["rows"], category=e["cat"], subject="",
                cover_title=e["cover_title"], cover_desc=e["cover_desc"], hero=e["hero"], hero_label=e.get("hero_label", ""),
                hl="", hdr=e["ctype"], foot="資料：公開資料整理・本站編輯", photo_cats=e.get("photo_cats") or [])
    d = dict(id=f"{slot}{idx}", slot=slot, data_date=f"{day} 台北", caption_ig=cap_ig, caption_threads=threads, card=card,
             link=url_th, u_code=ucode, evergreen=True, sources=[dict(name=x, url="", date="") for x in e.get("sources", [])],
             meta=dict(topic_category=e["cat"], content_type=e["ctype"], layout="D-知識卡(實景)", style="常備文庫", has_ai_image="false",
                       explore="false", heat="0", news_ids="", u_code=ucode, evergreen="true", topic_id=e["id"]))
    bad = []
    for l in e["cover_title"]:
        if not l or len(l) > TITLE_MAX + 2:
            bad.append(f"標題行長度 {len(l)}：{l}")
    body_len = len(REL_RE.sub("", cap_ig.rsplit("以上為公開資料整理", 1)[0]))
    if body_len < EVG_MIN_BODY:
        bad.append(f"內文 {body_len} 字（最少 {EVG_MIN_BODY}）")
    if "#stock/" in cap_ig:
        bad.append("落點不得為個股頁")
    v = legal_check(cap_ig + "\n" + "\n".join(threads) + "\n" + json.dumps(card, ensure_ascii=False))
    if v:
        bad.append("法遵：" + "；".join(v))
    if len(cap_ig) > 2000:
        bad.append("IG 文案超過 2,000 字")
    if bad:
        raise Skip("常備文庫 " + e["id"] + "：" + "；".join(bad))
    return d


# ---------------- 圖卡 ----------------
PHOTO_USAGE = LOG_DIR / "photo_usage.json"     # 圖池使用紀錄 {"<slug>/<檔名>": ["YYYY-MM-DD", ...]}，給 14 天輪替用


def load_usage(path: Path = PHOTO_USAGE) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def note_usage(used: dict, key: str, day: str, keep: int = 30) -> None:
    used.setdefault(key, [])
    if day not in used[key]:
        used[key] = (used[key] + [day])[-keep:]


def render_cards(posts: list[dict], slot: str, out: Path, day: str = "", usage_path: Path | None = PHOTO_USAGE) -> dict[str, int]:
    """用 render_news_cards.card_auto 逐張渲染＋重疊檢查；回傳 {id: 重疊筆數}；layout／photo_kind 寫回 meta。
    選圖（Andy 10-28 v2）：公司已審圖池（近 14 天用過的避開）→ 類別圖池 → 灰框大數字。
    layout：D-實景(公司)／D-實景(產品)／D-實景(類別)／D-無圖大數字，週報比較用。"""
    pdir = ROOT / "docs" / "marketing" / "posts"
    sys.path.insert(0, str(pdir))
    import render_news_cards as R
    from lib_dplus import BASE, CHECK
    from playwright.sync_api import sync_playwright
    import io
    from PIL import Image
    out.mkdir(parents=True, exist_ok=True)
    bad = {}
    used = load_usage(usage_path) if usage_path else {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None)
        R._PG = b.new_page(); R._PG.set_content("<body></body>")
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i, d in enumerate(posts, 1):
            # 2026-10-29 Andy：「封面沒圖片需要添加」→ 封面一律實景照片；有重疊先換精簡版（副標 1 行、資訊列 2 列）再查，
            # 仍重疊或圖庫選不到圖 → 這篇不排（bad>0），不退回無圖大數字卡。
            html, lay, pick = R.card_auto(d, i, len(posts), slot, used=used, today=day or None)
            d["meta"]["layout"] = "D-知識卡(實景)" if d.get("evergreen") else lay
            res = {"bad": ["選不到封面照片"]}
            if pick:
                d["meta"]["has_photo"] = "true"; d["meta"]["photo_kind"] = pick["kind"]; d["meta"]["photo"] = pick["key"]
                pg.set_content(f"<html><head><meta charset=utf-8><style>{BASE}</style></head>{html}</html>")
                pg.wait_for_timeout(300)
                res = pg.evaluate(CHECK)
                if res["bad"]:
                    c0 = d["card"]; slim = dict(d, card=dict(c0, cover_desc=(R.lines_of(c0.get("cover_desc")) or [""])[:1], numbers=c0["numbers"][:2]))
                    html, lay, pick = R.card_auto(slim, i, len(posts), slot, used=used, today=day or None)
                    pg.set_content(f"<html><head><meta charset=utf-8><style>{BASE}</style></head>{html}</html>")
                    pg.wait_for_timeout(300); res = pg.evaluate(CHECK)
            bad[d["id"]] = len(res["bad"])
            if pick and not res["bad"]:
                note_usage(used, pick["key"], day)      # 同一輪後面的卡也會避開這張
            Image.open(io.BytesIO(pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}))).convert("RGB") \
                .save(out / f"{d['id']}.jpg", quality=92)
        b.close()
    if usage_path and day:
        usage_path.parent.mkdir(parents=True, exist_ok=True)
        usage_path.write_text(json.dumps(used, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return bad


# ---------------- 主流程 ----------------
def publish_base(slot: str, day: str, posted: dict, now: datetime) -> datetime | None:
    """主貼文發出時間 +15 分（10-28 Andy：「貼文在早一點發布」）；固定時間（盤前 08:35、盤中 12:16）較晚就用固定時間；不早於 now+5 分。主貼文還沒發 → None。"""
    key = f"{SLOTS[slot]['key']}-{day}"
    if key not in posted:
        return None
    at = posted[key].get("at")
    base = (datetime.fromisoformat(at).astimezone(TPE) + timedelta(minutes=15)) if at else now + timedelta(minutes=15)
    fx = SLOTS[slot]["fixed"]
    if fx:
        base = max(base, datetime.fromisoformat(f"{day}T{fx}:00+08:00"))
    return max(base, now + timedelta(minutes=5)).replace(second=0, microsecond=0)


def already(slot: str, day: str) -> bool:
    return any(IG_Q.glob(f"{day}_news-{slot}-*.md")) or (LOG_DIR / f"{day}-{slot}.json").exists()


def used_news_ids(day: str) -> set[str]:
    """同一天其他時段已入選的新聞（避免週末兩篇、盤前盤後選到同一則）。"""
    ids: set[str] = set()
    for f in LOG_DIR.glob(f"{day}-*.json"):
        try:
            for x in json.loads(f.read_text(encoding="utf-8")).get("posted", []):
                ids |= set(str(x.get("news_ids", "")).split(","))
        except Exception:
            pass
    return ids - {""}


def used_topic_ids(day: str, out: Path | None = None) -> set[str]:
    """同一天其他時段已用的常備文庫條目（演練時也看 --out 資料夾裡先前存的 <slot>.json）。"""
    ids: set[str] = set()
    for f in LOG_DIR.glob(f"{day}-*.json"):
        try:
            ids |= {x.get("topic_id") for x in json.loads(f.read_text(encoding="utf-8")).get("posted", [])}
        except Exception:
            pass
    if out and out.exists():
        for f in out.glob("*.json"):
            try:
                ids |= {(x.get("meta") or {}).get("topic_id") for x in json.loads(f.read_text(encoding="utf-8")) if isinstance(x, dict)}
            except Exception:
                pass
    return ids - {None, ""}


def run_slot(slot: str, day: str, now: datetime, posted: dict, dry: bool, out: Path | None, force: bool) -> dict:
    cfg = SLOTS[slot]
    nmax = cfg["n"]
    log = dict(slot=slot, date=day, run_at=now.isoformat(timespec="minutes"), posted=[], skipped=[])
    if nmax <= 0:
        return dict(log, note="這段名額 0（SLOTS 設定），不排")
    if not dry and not force and already(slot, day):
        return dict(log, note="今天這段已排過，跳過")
    offday = cfg["key"] is None                  # 週末／休市日／備案：不看主貼文
    if offday:
        fx = datetime.fromisoformat(f"{day}T{cfg['fixed']}:00+08:00")
        when = max(fx, now + timedelta(minutes=5)).replace(second=0, microsecond=0)
    else:
        when = publish_base(slot, day, posted, now) if not force else now + timedelta(minutes=30)
        if when is None and not dry:
            return dict(log, note=f"主貼文 {cfg['key']}-{day} 還沒發，先不排")
        at = (posted.get(f"{cfg['key']}-{day}") or {}).get("at")
        if at and not force and not dry and now - datetime.fromisoformat(at).astimezone(TPE) > timedelta(hours=3):
            return dict(log, note="主貼文已發超過 3 小時，新聞時效已過，這段不補排")
    when = when or now + timedelta(minutes=30)
    dd, hh = cfg["since"]
    t0 = datetime.fromisoformat(f"{day}T{hh}:00+08:00") + timedelta(days=dd)
    news = [n for n in load_news(t0, now) if not is_promo(n["title"] + n["summary"])] if not cfg.get("evergreen_first") else []
    w = load_weights()
    cands = [score(g, w) for g in cluster(news)]
    cands = [c for c in cands if len(c["nums"]) >= 2]
    taken_ids = used_news_ids(day)
    cands = [c for c in cands if not ({n["news_id"] for n in c["group"]} & taken_ids)]
    if offday:               # 休市日：盤勢數字（收盤、法人）當天沒有新資料，不選
        cands = [c for c in cands if c["ctype"] != "盤勢數字"]
    if slot == "pre":        # 盤前：前一天台股收盤主貼文已講，只留隔夜美股／國際／今日事件（排掉台股盤勢與台股公司）
        names0 = names_map()
        cands = [c for c in cands if c["cat"] != "台股" and c["ctype"] != "盤勢數字" and not subject_of(c, names0)[1]]
    rng = random.Random(int(hashlib.md5(f"{day}{slot}".encode()).hexdigest()[:8], 16))
    chosen = pick(cands, nmax + 8, rng, w.get("explore", EXPLORE))      # 多挑 8 篇當備胎（品質閘、法遵或重疊被擋時遞補）
    names = names_map()
    sw = w.get("style", {})
    posts = []
    for c in chosen:
        if len(posts) >= nmax:
            break
        style = rng.choice(STYLES) if c.get("explore") else max(STYLES, key=lambda s: (sw.get(s, 1.0), s == STYLES[0]))
        try:
            d = compose(c, slot, len(posts) + 1, day, style, names)
        except Skip as ex:
            log["skipped"].append(dict(title=c["lead"]["title"], why=str(ex))); continue
        full = d["caption_ig"] + "\n" + "\n".join(d["caption_threads"]) + "\n" + json.dumps(d["card"], ensure_ascii=False)
        v = legal_check(full)
        if v:
            log["skipped"].append(dict(title=c["lead"]["title"], why="法遵：" + "；".join(v))); continue
        if len(d["caption_ig"]) > 2000:
            log["skipped"].append(dict(title=c["lead"]["title"], why="IG 文案超過 2,000 字")); continue
        posts.append(d)
    # 常備文庫：新聞品質閘不過就少發，但保底（floor）一定要有——交易日盤後至少 1 篇、休市日每段 1 篇
    need = (nmax if cfg.get("evergreen_first") else cfg["floor"]) - len(posts)
    if cfg.get("evergreen_first"):
        need = nmax - len(posts)
    if need > 0:
        taken = {x["meta"].get("topic_id") for x in posts} | used_topic_ids(day, out)
        for e in pick_evergreen(day, need + 3, taken, rng):
            if need <= 0:
                break
            try:
                posts.append(compose_evergreen(e, slot, len(posts) + 1, day)); need -= 1
            except Skip as ex:
                log["skipped"].append(dict(title=e["id"], why=str(ex)))
        log["evergreen"] = [x["meta"]["topic_id"] for x in posts if x.get("evergreen")]
    if len(posts) < nmax:
        log["note"] = f"可發的只有 {len(posts)} 篇（名額 {nmax}），寧可少發也不湊數"
    if not posts:
        return log
    img_out = (out / slot) if dry else IMG_DIR / f"{day}-{slot}"
    bad = render_cards(posts, slot, img_out, day, None if dry else PHOTO_USAGE)
    keep = []
    for d in posts:
        if bad[d["id"]]:
            log["skipped"].append(dict(title=d["card"]["title"], why=f"圖卡重疊或沒有封面照片 {bad[d['id']]} 筆"))
            (img_out / f"{d['id']}.jpg").unlink(missing_ok=True)
        else:
            keep.append(d)
    log["overlap"] = f"重疊檢查：程式 {len(posts)} 張 {sum(bad.values())} 筆（有重疊的不排程）"
    for i, d in enumerate(keep):
        t = when + timedelta(minutes=GAP_MIN * i)
        pa = t.strftime("%Y-%m-%dT%H:%M+08:00")
        d["publish_at"] = pa
        img_rel = (img_out / f"{d['id']}.jpg").relative_to(ROOT).as_posix() if not dry else f"{slot}/{d['id']}.jpg"
        meta = "\n".join(f"{k}: {v}" for k, v in d["meta"].items())
        ttl = f"{cfg['name']}{'知識' if d.get('evergreen') else '新聞'} {day} #{i + 1}：{d['card']['title']}"
        status = TOPIC_STATUS if (offday or d.get("evergreen")) else STATUS
        ig = f"---\nstatus: {status}\npublish_at: {pa}\ntitle: {ttl}\nimages: {img_rel}\n{meta}\n---\n{d['caption_ig']}\n"
        th = f"---\nstatus: {status}\npublish_at: {pa}\ntitle: {ttl}\nimages: {img_rel}\n{meta}\n---\n" + "\n-----\n".join(d["caption_threads"]) + "\n"
        name = f"{day}_news-{slot}-{i + 1}.md"
        if dry:
            (out / "ig").mkdir(parents=True, exist_ok=True); (out / "threads").mkdir(parents=True, exist_ok=True)
            (out / "ig" / name).write_text(ig, encoding="utf-8"); (out / "threads" / name).write_text(th, encoding="utf-8")
        else:
            (IG_Q / name).write_text(ig, encoding="utf-8"); (TH_Q / name).write_text(th, encoding="utf-8")
        log["posted"].append(dict(file=name, publish_at=pa, title=d["card"]["title"], **d["meta"]))
    if dry:
        (out / f"{slot}.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    else:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / f"{day}-{slot}.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
        used = evg_usage()
        for d in keep:
            if d.get("evergreen"):
                used.setdefault(d["meta"]["topic_id"], []).append(day)
        if any(d.get("evergreen") for d in keep):
            EVG_USAGE.write_text(json.dumps(used, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return log


def is_trading(day: str) -> bool:
    try:
        from datetime import date
        from social_gate import load_holidays, is_open_day
        return is_open_day(date.fromisoformat(day), load_holidays())
    except Exception:
        return datetime.fromisoformat(day).weekday() < 5


def auto_slots(day: str, now: datetime, posted: dict) -> list[str]:
    """交易日：主貼文已發的盤前／盤中／盤後；20:50 後盤後還沒排任何一篇 → 加「備案」（主貼文沒發也要有 1 篇）。
    休市日（週末、國定假日、颱風假）：wk1（10:00 起）、wk2（18:45 起）。"""
    hm = now.strftime("%H:%M")
    if is_trading(day):
        out = [s for s in WEEKDAY_SLOTS if SLOTS[s]["n"] > 0 and f"{SLOTS[s]['key']}-{day}" in posted]
        if hm >= SLOTS["fb"]["after"] and not any(IG_Q.glob(f"{day}_news-post-*.md")) and not any(IG_Q.glob(f"{day}_news-fb-*.md")):
            out.append("fb")
        return out
    return [s for s in OFFDAY_SLOTS if hm >= SLOTS[s]["after"]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", default="auto", choices=list(SLOTS) + ["auto"])
    ap.add_argument("--date", default="")
    ap.add_argument("--now", default="")
    ap.add_argument("--posted", default="state/posted.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="")
    ap.add_argument("--force", action="store_true", help="不看主貼文有沒有發（測試用）")
    a = ap.parse_args(argv)
    now = datetime.fromisoformat(a.now).astimezone(TPE) if a.now else datetime.now(TPE)
    day = a.date or now.strftime("%Y-%m-%d")
    try:
        posted = json.loads(Path(a.posted).read_text(encoding="utf-8"))
    except Exception:
        posted = {}
    out = Path(a.out) if a.out else None
    if a.dry_run and not out:
        ap.error("--dry-run 要搭配 --out")
    slots = [a.slot] if a.slot != "auto" else auto_slots(day, now, posted)
    if not slots:
        print(f"{day} 目前沒有該排的主題文章時段（交易日要等主貼文發出；休市日要等排定時間）")
    for s in slots:
        log = run_slot(s, day, now, posted, a.dry_run, out, a.force)
        print(json.dumps(log, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
