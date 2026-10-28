"""新聞貼文自動產稿＋排程（2026-10-28，Andy：「可以，接上排程，單位改成億美元，CEO並安排人員持續優化，
依據不同的內容後台紀錄，後續慢慢改善收斂成大家喜歡的主題、內容、版面、風格」）。

盤前／盤中／盤後三段自動文發完後 30 分鐘，各發 3～5 篇新聞貼文（每篇 IG 單圖＋Threads 串文）。
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
SLOTS = {
    "pre":   dict(name="盤前", key="premarket", fixed="08:35", since=(-1, "13:30")),
    "intra": dict(name="盤中", key="intraday",  fixed="12:16", since=(0, "07:30")),
    "post":  dict(name="盤後", key="close",     fixed=None,    since=(0, "11:30")),
}
N_MIN, N_MAX = 3, 5
EXPLORE = 0.2
STATUS = "approved" if os.environ.get("NEWS_AUTO_APPROVE") == "1" else "draft"   # 預設 draft：品質修完、CEO 確認後 workflow 才設 NEWS_AUTO_APPROVE=1
GAP_MIN = 5                       # 同一段多篇之間錯開 5 分鐘，避免洗版
SRC_NAME = {"cnyes": "鉅亨", "udn": "經濟日報", "technews": "科技新報"}
CATS = ["台股", "財報", "總經", "科技", "美股"]
STYLES = ["口袋長文", "精簡重點"]
LAYOUT = "D-無圖大數字"

# ---------------- 分類 ----------------
KW = {
    "財報": r"財報|EPS|每股(純益|盈餘|賺|稅後)|毛利率|營益率|自結|營收|法說|獲利|淨利|財測",
    "總經": r"Fed|聯準會|央行|利率|降息|升息|CPI|PCE|通膨|非農|GDP|殖利率|美元指數|新台幣|匯率|油價|金價|關稅|PMI|失業率|景氣",
    "美股": r"美股|道瓊|那斯達克|標普|費半|費城半導體|S&P|Nasdaq|輝達|NVIDIA|微軟|蘋果|Apple|Alphabet|Google|Meta|亞馬遜|特斯拉|博通|超微|AMD|甲骨文|ADR",
    "台股": r"台股|加權指數|大盤|三大法人|外資|投信|自營商|成交值|櫃買|集中市場|台指期",
}
CTYPE = [
    ("財報數字", r"財報|EPS|每股|毛利率|自結|營收|淨利|獲利|財測|營益率"),
    ("盤勢數字", r"加權指數|大盤|三大法人|外資|投信|自營商|成交值|台指期|收盤|櫃買"),
    ("總經數據", r"Fed|聯準會|央行|利率|CPI|PCE|通膨|非農|GDP|殖利率|匯率|新台幣|油價|金價|PMI"),
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


def names_map() -> dict[str, str]:
    try:
        import pandas as pd
        fs = sorted((ROOT / "data" / "company_info").glob("**/*.parquet"))
        d = pd.concat([pd.read_parquet(f) for f in fs])
        return {k: v.strip(" *＊") for k, v in zip(d["code"].astype(str), d["name"].astype(str))}
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


NUMRE = re.compile(r"(?P<pre>逾|約|近|超過)?(?P<num>[+-]?\d[\d,]*(?:\.\d+)?)\s*(?P<unit>兆韓元|兆美元|億美元|萬美元|美元|億元|萬元|萬張|兆元|兆|億|元|%|％|點|倍|家|張)")
SPLIT = re.compile(r"[，。；：、！？\s（）()「」『』〈〉【】/／|｜]")
CHG = ("年增", "季增", "月增", "年減", "季減", "月減", "增加", "減少")


def numbers_of(text: str) -> list[dict]:
    """從新聞文字抓「標籤＋數字＋單位」；標籤＝同一子句裡數字前面的字。"""
    out, prev = [], ""
    ms = list(NUMRE.finditer(text))
    for k, m in enumerate(ms):
        last_end = ms[k - 1].end() if k else 0
        head = text[:m.start()]
        cut = max((head.rfind(c) for c in "，。；：、！？ （(「/／|｜"), default=-1)
        cut = max(cut, last_end - 1)              # 同一子句裡前面還有數字 → 標籤從那個數字之後算
        lab = head[cut + 1:].strip()
        if not any(lab.endswith(c) for c in CHG):
            lab = re.sub(r"(衝上|衝|站上|突破|創|寫下|達到|達|為|約|至|到|來到|共|僅|有|是|再|則|合計|攀升至|升至|降至|增至|減至|增|減|漲|跌|(?<!營)收|上漲|下跌|賺)$", "", lab)
        lab = re.sub(r"^(並|且|而|但|雖|其中|另|也|較|比|與|和|及)", "", lab).strip()
        if any(lab.endswith(c) or lab == c for c in CHG) and prev and len(lab) <= 4:
            lab = prev + lab
        num = m.group("num")
        if re.fullmatch(r"(19|20)\d\d", num.replace(",", "")) and m.group("unit") in ("元",):
            continue
        if not (2 <= len(lab) <= 14) or not re.search(r"[一-鿿]", lab) or re.search(r"\d{4,}$", lab):
            prev = lab if 2 <= len(lab) <= 10 else prev
            continue
        unit = m.group("unit").replace("％", "%")
        out.append(dict(label=lab, value=(m.group("pre") or "") + num, unit=unit, key=num.replace(",", "") + unit))
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
       "標普", "聯準會", "Fed", "日銀", "歐洲央行", "TrendForce", "IDC", "加權指數", "台股", "三大法人", "外資", "投信", "自營商"]
METRICS = [("EPS", r"每股(純益|盈餘|稅後|賺)|EPS"), ("毛利率", r"毛利率"), ("營業利益", r"營業利益|營益"), ("淨利", r"淨利|純益|獲利|盈餘"),
           ("營收", r"營收"), ("資本支出", r"資本支出"), ("財測", r"財測|指引"), ("指數", r"加權指數|指數|道瓊|那斯達克|標普|費半"),
           ("買超", r"買超"), ("賣超", r"賣超"), ("成交值", r"成交值|成交額"), ("殖利率", r"殖利率"), ("利率", r"利率"), ("融資", r"融資|籌資|增資"), ("產值", r"產值"), ("出貨", r"出貨"), ("餘額", r"餘額"),
           ("市值", r"市值"), ("訂單", r"訂單|合約"), ("油價", r"油價|金價|布蘭特|西德州"), ("股價", r"股價|收盤價|盤後")]
FIN = {"EPS", "毛利率", "營業利益", "淨利", "營收", "財測", "資本支出"}
EVENTW = {"指數": "收盤", "買超": "法人動向", "賣超": "法人動向", "成交值": "成交", "殖利率": "利率", "利率": "利率",
          "資本支出": "資本支出", "財測": "財測", "融資": "融資"}
JUNK = r"跌停|漲停|家數|檔|張|名|人|歲|年$"
GROWTH = r"年增|季增|月增|年減|季減|月減|較|同期|成長|衰退|增加|減少|上漲|下跌|漲|跌|下挫|升至|降至|新高|新低"
EMPTY = ["指數點數反映", "家媒體", "則報導", "營收是公司銷售", "每股純益（EPS）是", "年增減是", "季增減是", "月增減是", "成交值是當天"]
REL = {"cpi": "美國 CPI 物價", "pce": "美國 PCE 物價", "gdp": "美國 GDP", "nfp": "美國非農就業", "payems": "美國非農就業",
       "fomc": "FOMC 利率決議", "ppi": "美國 PPI", "retail": "美國零售銷售", "unrate": "美國失業率"}
TITLE_MAX = 12
GENERIC = {"全台", "台灣", "中華", "國際", "美國", "大眾", "統一", "華南", "第一", "合庫", "新光", "全國", "亞洲", "世界", "大立", "東方"}
MIN_BODY = 500


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


def subject_of(c: dict, names: dict) -> tuple[str, str]:
    """(主體名稱, 台股代號或空)；找不到回 ('', '')。"""
    t = c["lead"]["title"]
    codes = [x for x in str(c["lead"].get("codes") or "").split(",") if x and not x.startswith("US-")]
    if codes and names.get(codes[0]):
        return names[codes[0]], codes[0]
    best = None
    for v in set(names.values()):
        if len(v) >= 2 and not re.search(r"[A-Za-z0-9]", v) and v not in GENERIC:
            k = t.find(v)
            if k >= 0 and (best is None or (k, -len(v)) < (best[0], -len(best[1]))):
                best = (k, v)
    for v in ENT:
        k = t.find(v)
        if k >= 0 and (best is None or k < best[0]):
            best = (k, v)
    if not best:
        return "", ""
    code = next((k for k, v in names.items() if v == best[1]), "")
    return best[1], code


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


def watch_point(day: str, tw: bool, ctype: str) -> str:
    d = datetime.fromisoformat(day)
    if tw:
        nm = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
        s = f"上市櫃公司每月 10 日前公告上月營收，{d.month} 月營收最晚 {nm.month}/10 公布，可以對照這次的數字。"
        if ctype == "財報數字":
            s += "第 4 季（全年）財報依規定在明年 3 月底前公告。"
        return s
    try:
        import pandas as pd
        fs = sorted((ROOT / "data" / "macro_calendar").glob("**/*.parquet"))
        mc = pd.concat([pd.read_parquet(f) for f in fs])
        mc = mc[mc["date"].astype(str) > day].sort_values("date")
        for r in mc.to_dict("records"):
            nm = REL.get(str(r["release"]).lower())
            if nm:
                dd = str(r["date"])[:10]
                return f"下一個要看的總經數據是 {int(dd[5:7])}/{int(dd[8:10])}（美國時間）公布的{nm}，市場會拿來對照這次的數字。"
    except Exception:
        pass
    return ""


_HIST = None


def history(subj: str, before: datetime, n: int = 2) -> list[str]:
    """資料湖裡同一主體在本則之前 45 天內、含數字的報導重點（給「背景」段做前期對照）。"""
    global _HIST
    if _HIST is None:
        _HIST = load_news(before - timedelta(days=45), before + timedelta(days=1))
    rows = [x for x in _HIST if x["ts"] < before - timedelta(hours=12) and subj in x["title"]]
    out, seen = [], set()
    for x in sorted(rows, key=lambda x: x["ts"], reverse=True):
        cl = [c for c in sanitize(x["summary"] or x["title"]).replace("。", "，").split("，") if c.strip() and clean_ok(c) and NUMRE.search(c)][:2]
        k = "".join(cl)
        if cl and k not in seen:
            seen.add(k)
            out.append(f"{x['ts'].month}/{x['ts'].day} {SRC_NAME.get(x['source'], x['source'])}：{'，'.join(cl)}。")
        if len(out) >= n:
            break
    return out


def _fmt(x: dict) -> str:
    return f"{x['value']}{'' if x['unit'] == '%' else ' '}{x['unit']}"


def compose(c: dict, slot: str, idx: int, day: str, style: str, names: dict) -> dict:
    """結構化產稿；資料不足或品質閘不過丟 Skip(原因)。"""
    lead = c["lead"]; ymd = day.replace("-", ""); md = f"{lead['ts'].month}/{lead['ts'].day}"
    subj, code = subject_of(c, names)
    if not subj:
        raise Skip("找不到主體（公司／機構／指數）")
    nums = [x for x in c["nums"] if not re.search(JUNK, x["label"])]
    for x in nums:
        x["metric"] = metric_of(x["label"]); x["growth"] = bool(re.search(GROWTH, x["label"]))
    title_raw = sanitize(lead["title"])
    m_close = re.search(r"收(?:在)?\s*([\d,]+(?:\.\d+)?)\s*點", title_raw)
    if c["cat"] == "台股" and m_close:         # 台股盤勢：主旨＝加權指數收盤，漲跌點數當前期比較
        nums = [dict(label="加權指數收盤", value=m_close.group(1), unit="點", key="close", metric="指數", growth=False, verified=False)] + nums
        m_chg = re.search(r"(上漲|下跌|漲|跌)\s*([\d,]+(?:\.\d+)?)\s*點", title_raw)
        if m_chg:
            nums.insert(1, dict(label=f"較前一交易日{'下跌' if '跌' in m_chg.group(1) else '上漲'}", value=m_chg.group(2), unit="點",
                                key="chg", metric="指數", growth=True, verified=False))
    keyc = [x for x in nums if x["metric"] and not x["growth"]]
    key = next((x for x in keyc if x["value"].lstrip("約逾近超過") in title_raw), keyc[0] if keyc else None)
    if not key:
        raise Skip("沒有可當主旨的關鍵數字")
    km = key["metric"]
    period = period_of(key["label"]) or period_of(title_raw)
    ev = "財報" if km in FIN and period else EVENTW.get(km, "")
    l1 = f"{subj}{period}{ev}"
    if len(l1) > TITLE_MAX:
        l1 = f"{subj}{ev}"
    if len(l1) > TITLE_MAX:
        l1 = subj                         # 主體太長：事件改由第二行的指標名稱帶出
    l2 = f"{km} {_fmt(key).replace(' ', '')}" if re.match(r"[A-Za-z]", km) else f"{km}{_fmt(key).replace(' ', '')}"
    if km == "指數":
        l2 = ("加權" if c["cat"] == "台股" else "") + _fmt(key).replace(" ", "")
    cover = [l1, l2]
    # 資訊列：主旨數字＋同一族（財報類／同指標）的相關數字
    fam = FIN if km in FIN else {km}
    rel = [x for x in nums if x is not key and (x["metric"] in fam or (x["growth"] and (x["metric"] in fam or x["metric"] is None)))]
    if len(rel) < 2:
        rel += [x for x in nums if x is not key and x not in rel and x["growth"]]
    rows = [key] + rel[:2]
    if len(rows) < 2:
        raise Skip("圖卡資訊列不足 2 列（與主旨相關的數字太少）")
    comps = [x for x in nums if x["growth"]]
    hi = re.search(r"[^，。]*(新高|新低|首度|首次)[^，。]*", c["text"])
    if not comps and not hi:
        raise Skip("沒有與前期的比較數字（季增／年增／前高）")
    tw = bool(code) or c["cat"] == "台股"
    wp = watch_point(day, tw, c["ctype"])
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
    sec_num = "📊 #重點數字\n" + "\n".join(f"▪ {x['label']} {_fmt(x)}{cite(x)}" for x in shown[:5])
    cmp_lines = [f"▪ {x['label']} {_fmt(x)}" for x in comps[:3]]
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
        base = "去年同期" if "年" in x["label"] or "同期" in x["label"] else "上一季" if "季" in x["label"] else "上個月" if "月" in x["label"] else "前一交易日" if re.search(r"漲|跌|挫", x["label"]) else "比較基期"
        mean.append(f"{x['label']} {_fmt(x)}，代表和{base}相比{'減少' if dn else '增加'}約 {x['value'].lstrip('+-約逾近')}{x['unit']}。")
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
    hist = history(subj, lead["ts"])
    sec_hist = ("📌 #之前的報導\n" + "\n".join(hist)) if hist else ""
    sec_watch = "👀 #接下來觀察\n" + wp
    tail = "以上為公開資料整理，非投資建議"
    body = [intro, sec_num, sec_cmp] + ([sec_mean] if style != "精簡重點" else []) + ([sec_more] if sec_more else []) + ([sec_hist] if sec_hist else []) + [sec_watch]
    link_line = "👉 更多詳細資料可以點擊以下連結："
    cap_ig = "\n".join(head) + "\n" + "\n\n".join(body) + f"\n\n{tail}\n{link_line}\n{url_ig}"
    threads = pack_threads(["\n".join(head[:2]) + "\n\n" + intro] + body[1:] + [f"{tail}\n{link_line}\n{url_th}"])
    card = dict(title=l1 + l2, subtitle=SUBQ[c["ctype"]], numbers=[{k: x[k] for k in ("label", "value", "unit")} for x in rows],
                category=c["cat"], subject=subj, cover_title=cover, cover_desc=_lines("、".join(f"{x['label']} {_fmt(x)}" for x in comps[:2]) or SUBQ[c["ctype"]], 22),
                hero=key["value"].lstrip("約逾近超過") + key["unit"], hl=_fmt(key).replace(" ", "") if _fmt(key).replace(" ", "") in l2 else "")
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
    body = d["caption_ig"].rsplit("以上為公開資料整理", 1)[0]
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
            html, lay, pick = R.card_auto(d, i, len(posts), slot, used=used, today=day or None)
            d["meta"]["layout"] = lay
            if pick:
                d["meta"]["has_photo"] = "true"; d["meta"]["photo_kind"] = pick["kind"]
            pg.set_content(f"<html><head><meta charset=utf-8><style>{BASE}</style></head>{html}</html>")
            pg.wait_for_timeout(300)
            res = pg.evaluate(CHECK)
            if res["bad"] and pick:           # 實景版有重疊 → 退回灰框大數字版，不擋整篇
                html = R.card_v4(d, i, len(posts), None, slot); d["meta"]["layout"] = "D-無圖大數字"
                d["meta"].pop("has_photo", None); d["meta"].pop("photo_kind", None); pick = None
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


def run_slot(slot: str, day: str, now: datetime, posted: dict, dry: bool, out: Path | None, force: bool) -> dict:
    cfg = SLOTS[slot]
    log = dict(slot=slot, date=day, run_at=now.isoformat(timespec="minutes"), posted=[], skipped=[])
    if not dry and not force and already(slot, day):
        return dict(log, note="今天這段已排過，跳過")
    when = publish_base(slot, day, posted, now) if not force else now + timedelta(minutes=30)
    if when is None and not dry:
        return dict(log, note=f"主貼文 {cfg['key']}-{day} 還沒發，先不排")
    at = (posted.get(f"{cfg['key']}-{day}") or {}).get("at")
    if at and not force and not dry and now - datetime.fromisoformat(at).astimezone(TPE) > timedelta(hours=3):
        return dict(log, note="主貼文已發超過 3 小時，新聞時效已過，這段不補排")
    when = when or now + timedelta(minutes=30)
    dd, hh = cfg["since"]
    t0 = datetime.fromisoformat(f"{day}T{hh}:00+08:00") + timedelta(days=dd)
    news = [n for n in load_news(t0, now) if not is_promo(n["title"] + n["summary"])]
    w = load_weights()
    cands = [score(g, w) for g in cluster(news)]
    cands = [c for c in cands if len(c["nums"]) >= 2]
    if slot == "pre":        # 盤前：前一天台股收盤主貼文已講，只留隔夜美股／國際／今日事件（排掉台股盤勢與台股公司）
        names0 = names_map()
        cands = [c for c in cands if c["cat"] != "台股" and c["ctype"] != "盤勢數字" and not subject_of(c, names0)[1]]
    rng = random.Random(int(hashlib.md5(f"{day}{slot}".encode()).hexdigest()[:8], 16))
    chosen = pick(cands, N_MAX + 8, rng, w.get("explore", EXPLORE))      # 多挑 3 篇當備胎（法遵或重疊被擋時遞補）
    names = names_map()
    sw = w.get("style", {})
    posts = []
    for c in chosen:
        if len(posts) >= N_MAX:
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
    if len(posts) < N_MIN:
        log["note"] = f"可發的只有 {len(posts)} 篇（< {N_MIN}），寧可少發也不湊數：照發 {len(posts)} 篇"
    if not posts:
        return log
    img_out = (out / slot) if dry else IMG_DIR / f"{day}-{slot}"
    bad = render_cards(posts, slot, img_out, day, None if dry else PHOTO_USAGE)
    keep = []
    for d in posts:
        if bad[d["id"]]:
            log["skipped"].append(dict(title=d["card"]["title"], why=f"圖卡重疊 {bad[d['id']]} 筆"))
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
        ttl = f"{cfg['name']}新聞 {day} #{i + 1}：{d['card']['title']}"
        ig = f"---\nstatus: {STATUS}\npublish_at: {pa}\ntitle: {ttl}\nimages: {img_rel}\n{meta}\n---\n{d['caption_ig']}\n"
        th = f"---\nstatus: {STATUS}\npublish_at: {pa}\ntitle: {ttl}\n{meta}\n---\n" + "\n-----\n".join(d["caption_threads"]) + "\n"
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
    return log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", default="auto", choices=["pre", "intra", "post", "auto"])
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
    slots = [a.slot] if a.slot != "auto" else [s for s in SLOTS if f"{SLOTS[s]['key']}-{day}" in posted]
    if not slots:
        print(f"{day} 還沒有任何一段主貼文發出，不排新聞文")
    for s in slots:
        log = run_slot(s, day, now, posted, a.dry_run, out, a.force)
        print(json.dumps(log, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
