"""社群選題清單：每天從資料湖產出「總經／科技」兩條軌道的候選題目，給 finance-content-editor 查證。

用法：python scripts/social_topics.py [--date YYYY-MM-DD] [--n 8] [--root <專案根目錄>]
輸出：docs/marketing/social_unit/daily_topics/<台北日期>.md 與同名 .json

為什麼這樣設計（docs/marketing/social_unit/today_events_feed.md 第 4 點）：
  · 只讀資料湖（data/ 底下的 Parquet）與 pipeline/ 的 YAML，不連外、不寫 data/。
  · 新聞再散布授權未確認（docs/launch_gap_legal_1009.md F2），所以只輸出「標題＋來源＋連結」，
    絕不輸出 summary 內文；「重點」欄一律留空，由編輯用自己的話填。
  · 這是「題目建議」：不下結論、不推薦買賣。法說會只列公司公告的事實，放在 B 軌附註。
  · 每一則都標「待查證」—— 新聞摘要會自己補出原文沒有的對應關係（CLAUDE.md 的 WebSearch 地雷），
    編輯要用第二個獨立來源確認才能用。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TAIPEI = timezone(timedelta(hours=8))
STALE_DAYS = 2            # 資料湖最新新聞日期落後超過這麼多天就在檔頭警告
SIM_THRESHOLD = 0.7       # 標題相似度門檻（去重）
DEFAULT_N = 8
LECTURE_AHEAD_DAYS = 7    # 「本週法說會」往後看幾天
CONF = "待查證"

# 產業別 → 延伸題模板。{g}＝族群名、{s}＝產業鏈環節名、{c}＝公司名（可能為空）。
# 挑選順序＝清單順序，取前 3~5 個；環節 id 有特別模板就排在前面。
_SEG_TOPICS = {
    "foundry": ["晶圓代工的製程流程怎麼走（從矽晶圓到完成 IC 的主要步驟）", "先進製程為什麼這麼貴、卡在哪裡"],
    "adv_pkg": ["先進封裝（CoWoS 等）是什麼、為什麼 AI 晶片需要", "先進封裝產能目前邁向哪個階段"],
    "osat_test": ["IC 封裝與測試要經過哪些程序（完成一顆 IC 的後段流程）", "封測廠和晶圓廠、IC 設計公司怎麼分工"],
    "ic_design": ["IC 設計公司做什麼、和晶圓代工怎麼合作", "完成一顆 IC 要哪些程序（設計→製造→封測）"],
    "hbm": ["HBM 高頻寬記憶體是什麼、為什麼 AI 伺服器需要", "記憶體供應鏈上下游誰跟誰合作"],
    "dram_nor": ["DRAM／NOR 的應用與景氣循環怎麼看", "記憶體產業目前邁向哪個階段（供需與報價）"],
    "storage": ["儲存（NAND／SSD）供應鏈介紹", "AI 時代為什麼儲存需求變強"],
    "abf_pcb": ["ABF 載板是什麼、在晶片封裝裡的位置", "載板材料與上游供應鏈介紹"],
    "hdi_pcb": ["PCB／HDI 在 AI 伺服器裡扮演什麼角色", "CCL（銅箔基板）到 PCB 的製程流程怎麼走"],
    "ccl": ["CCL 銅箔基板的上游材料有哪些（銅箔、玻纖布、樹脂）", "高階 CCL 為什麼是 AI 板材的關鍵"],
    "thermal": ["AI 伺服器為什麼需要散熱升級（氣冷到液冷）", "散熱模組的供應鏈介紹"],
    "power": ["AI 伺服器電源供應的架構與供應鏈", "高功率電源為什麼需求變強"],
    "optical": ["光通訊（含 CPO）在 AI 資料中心的角色", "光通訊供應鏈上下游介紹"],
    "switch": ["交換器與網通設備在 AI 叢集裡做什麼", "網通供應鏈介紹"],
    "assembly": ["AI 伺服器組裝（ODM）的流程與主要客戶關係", "伺服器供應鏈上下游誰跟誰合作"],
    "fab_equipment": ["半導體設備在製程流程的哪一步", "設備、材料、耗材的供應鏈介紹"],
    "test_interface": ["測試介面（探針卡、測試座）在 IC 測試的位置", "測試流程怎麼走"],
}
_CHAIN_TOPICS = {
    "semiconductor": ["半導體製程流程怎麼走（設計→製造→封裝→測試）", "半導體上下游合作關係：誰供貨給誰",
                      "這個環節目前邁向哪個階段", "台股半導體供應鏈介紹（依環節）", "完成一顆 IC 要哪些程序"],
    "ai_server": ["為何 AI 伺服器需求強（雲端業者資本支出與模型訓練）", "AI 伺服器供應鏈介紹：哪個零件由誰做",
                  "上下游合作關係：誰供貨給誰", "這個環節目前邁向哪個階段", "台股 AI 伺服器供應鏈介紹（依環節）"],
    "electronics": ["這個電子零組件在終端產品裡的位置", "上下游合作關係：誰供貨給誰",
                    "景氣目前邁向哪個階段", "台股電子零組件供應鏈介紹"],
    "software": ["這類軟體／資訊服務的商業模式怎麼賺錢", "台股軟體與資訊服務族群介紹", "AI 對這個產業的影響是什麼"],
    "financial": ["利率與這類金融業獲利的關係（描述機制，不下結論）", "台股金融族群介紹"],
}
_GENERIC_TOPICS = ["這件事的來龍去脈：背景與時間線", "對台股相關族群的影響路徑（描述，不下結論）",
                   "相關產業的供應鏈介紹", "數字怎麼看：名詞解釋與歷史對照"]
_MACRO_TOPICS = ["這件事的來龍去脈：背景與時間線", "它對利率、匯率、油價或台股資金流的傳導路徑（描述，不預測）",
                 "過去類似事件發生時市場怎麼反應（歷史對照）", "名詞解釋：讀者最常搞混的地方"]
_TECH_TOPICS = ["這項技術或產品是什麼（一張圖看懂）", "它在 AI／半導體供應鏈的位置", "台股相關供應鏈介紹（依環節）",
                "目前邁向哪個階段（研發、試產、量產）"]


# ------------------------------------------------------------------ 讀資料（只讀）
def _read_parquet_dir(root: Path, table: str):
    import pandas as pd
    files = sorted((root / "data" / table).glob("**/*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def load_lake(root: Path) -> dict:
    """讀新聞、重大訊息、macro_calendar、公司名稱對照。缺表回空 DataFrame，不讓整支掛掉。"""
    out = {}
    for t in ("news", "material_news", "macro_calendar", "company_info"):
        try:
            out[t] = _read_parquet_dir(root, t)
        except Exception as exc:  # noqa: BLE001
            print(f"[警告] 讀不到 {t}：{exc}", file=sys.stderr)
            import pandas as pd
            out[t] = pd.DataFrame()
    return out


def load_structure(root: Path) -> dict:
    """groups.yaml / supply_chain.yaml / macro_events.yaml → 查表用的字典。"""
    import yaml

    def _y(p: Path) -> dict:
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            print(f"[警告] 讀不到 {p}：{exc}", file=sys.stderr)
            return {}
    g = _y(root / "pipeline" / "groups" / "groups.yaml")
    s = _y(root / "pipeline" / "groups" / "supply_chain.yaml")
    m = _y(root / "pipeline" / "calendar" / "macro_events.yaml")
    return {"groups": g.get("groups") or {}, "supply": s, "macro_cfg": m}


# ------------------------------------------------------------------ 對照：公司 → 族群／環節
def build_company_index(structure: dict, company_info=None) -> dict:
    """回傳 {code: {name, groups:[{id,name,chain}], segs:[{id,name,chain}]}}。

    名稱優先 supply_chain.companies（人工校訂），其次 company_info。
    """
    segs = {x["id"]: x for x in (structure.get("supply") or {}).get("segments") or []}
    idx: dict = {}

    def ent(code):
        return idx.setdefault(str(code), {"name": "", "groups": [], "segs": []})

    for gid, g in (structure.get("groups") or {}).items():
        for c in g.get("codes") or []:
            e = ent(str(c).strip())
            e["groups"].append({"id": gid, "name": g.get("name", gid), "chain": g.get("chain", "")})
    for co in (structure.get("supply") or {}).get("companies") or []:
        t = str(co.get("ticker") or "").strip()
        if not t:
            continue
        e = ent(t)
        e["name"] = co.get("name") or e["name"]
        sg = segs.get(co.get("segment"))
        if sg:
            e["segs"].append({"id": sg["id"], "name": sg.get("name", sg["id"]), "chain": sg.get("chain", "")})
    if company_info is not None and len(company_info):
        for code, name in zip(company_info["code"].astype(str), company_info["name"].astype(str)):
            if code in idx and not idx[code]["name"]:
                idx[code]["name"] = name
    return idx


_CODE_RE = re.compile(r"^\d{4,6}$")
# 公司簡稱本身是一般詞彙，用「標題含名稱」比對會大量誤中（實測「世界」「全新」），一律不用名稱比對
# （codes 欄仍採用）。清單靠實跑累積，發現新誤中就加。
NAME_MATCH_STOPLIST = {"世界", "全新", "大成", "中華", "台灣", "國際", "聯合", "環球", "大眾", "新光", "正新", "遠東", "亞洲", "東方", "金融"}


def find_companies(title: str, codes: str, idx: dict) -> list[str]:
    """從 codes 欄與標題內的公司名找出台股代號（只回在 idx 裡、也就是有族群歸屬的）。"""
    found: list[str] = []
    for c in str(codes or "").split(","):
        c = c.strip()
        if _CODE_RE.match(c) and c in idx:
            found.append(c)
    t = title or ""
    for code, e in idx.items():
        nm = e.get("name") or ""
        # 名稱太短（1 字）容易誤中，至少 2 字
        if len(nm) >= 2 and nm not in NAME_MATCH_STOPLIST and nm in t and code not in found:
            found.append(code)
    return list(dict.fromkeys(found))


# ------------------------------------------------------------------ 去重
_PUNCT = re.compile(r"[\s\W_]+", re.UNICODE)


def _norm_title(t: str) -> str:
    return _PUNCT.sub("", str(t or "")).lower()


def _tw_codes(codes: str) -> frozenset:
    return frozenset(c.strip() for c in str(codes or "").split(",") if _CODE_RE.match(c.strip()))


def dedupe(items: list[dict], threshold: float = SIM_THRESHOLD) -> list[dict]:
    """標題相似度 ≥ 門檻、或台股 codes 完全相同（且非空）→ 合併成一則，
    被併入的來源記在 also，保留先出現（排序在前）的那則。"""
    kept: list[dict] = []
    for it in items:
        nt, cs = _norm_title(it["title"]), _tw_codes(it.get("codes", ""))
        hit = None
        for k in kept:
            if SequenceMatcher(None, nt, _norm_title(k["title"])).ratio() >= threshold:
                hit = k
                break
            if cs and cs == _tw_codes(k.get("codes", "")) and it.get("category") == k.get("category"):
                hit = k
                break
        if hit is None:
            it = dict(it)
            it["also"] = []
            kept.append(it)
        else:
            hit["also"].append({"source": it["source"], "title": it["title"], "url": it["url"]})
    return kept


# ------------------------------------------------------------------ 選新聞
def pick_news(news, category: str, target: date, n: int) -> list[dict]:
    """近 2 日（target-1 ~ target）某分類新聞，新的在前，去重後取前 n。"""
    import pandas as pd
    if news is None or news.empty:
        return []
    lo, hi = (target - timedelta(days=1)).isoformat(), target.isoformat()
    d = news[(news["category"] == category) & (news["date"] >= lo) & (news["date"] <= hi)].copy()
    if d.empty:
        return []
    d["_ts"] = pd.to_datetime(d["published_at"], utc=True, errors="coerce", format="mixed")
    d = d.sort_values(["date", "_ts"], ascending=[False, False])
    items = [{
        "title": str(r["title"] or "").strip(), "source": str(r["source"] or ""), "url": str(r["url"] or ""),
        "date": str(r["date"]), "codes": str(r["codes"] or ""), "category": category,
    } for _, r in d.iterrows() if str(r["title"] or "").strip()]
    return dedupe(items)[:n]


# ------------------------------------------------------------------ 延伸題
def extension_topics(item: dict, idx: dict, track: str) -> dict:
    """依新聞提到的公司找族群／環節，產 3~5 個延伸題建議。回 {groups, companies, topics}。"""
    codes = find_companies(item["title"], item.get("codes", ""), idx)
    groups, companies, chains, seg_ids = [], [], [], []
    for c in codes:
        e = idx[c]
        companies.append({"code": c, "name": e["name"]})
        for g in e["groups"]:
            if g["name"] not in groups:
                groups.append(g["name"])
            chains.append(g["chain"])
        for s in e["segs"]:
            seg_ids.append(s["id"])
            chains.append(s["chain"])
            if s["name"] not in groups:
                groups.append(s["name"])
    topics: list[str] = []
    for sid in seg_ids:
        topics += _SEG_TOPICS.get(sid, [])
    for ch in chains:
        topics += _CHAIN_TOPICS.get(ch, [])
    topics += (_MACRO_TOPICS if track == "A" else _TECH_TOPICS) if not topics else []
    topics += _GENERIC_TOPICS
    topics = list(dict.fromkeys(topics))
    # 有族群歸屬給 5 個；沒有給 3 個（題目沒有針對性，不要硬湊）
    topics = topics[: 5 if groups else 3]
    return {"groups": groups[:4], "companies": companies[:4], "topics": topics}


# ------------------------------------------------------------------ 總經日程
def macro_schedule(structure: dict, cal, target: date) -> list[dict]:
    """未來 7 天＋過去 2 天的總經日程。沿用 earnings.macro_events()（FRED 優先、YAML 退回）。"""
    try:
        from pipeline.compute import earnings
        evs = earnings.macro_events(structure.get("macro_cfg") or {}, cal,
                                    (target - timedelta(days=2)).isoformat(),
                                    (target + timedelta(days=7)).isoformat())
    except Exception as exc:  # noqa: BLE001
        print(f"[警告] 總經日程讀取失敗：{exc}", file=sys.stderr)
        return []
    out = []
    for e in sorted(evs, key=lambda x: (x["d"], x["k"])):
        past = e["d"] < target.isoformat()
        out.append({
            "date_et": e["d"], "tw_time": e.get("tw", ""), "kind": e["k"], "title": e["title"],
            "ref": e.get("ref") or "", "org": e.get("src", ""), "via": e.get("via", ""),
            "phase": "已過公布日" if past else ("今天" if e["d"] == target.isoformat() else "未來"),
            "confidence": CONF,
        })
    return out


# ------------------------------------------------------------------ 本週法說會
_LECT = re.compile(r"法人說明會|法說會")
_ROC = re.compile(r"(\d{2,3})年(\d{1,2})月(\d{1,2})日")


def lectures(mat, target: date) -> list[dict]:
    """重大訊息裡的法說會（公司自己公告的事實；不是推薦）。日期：主旨寫了就用，否則用事實發生日。"""
    if mat is None or mat.empty:
        return []
    lo, hi = target.isoformat(), (target + timedelta(days=LECTURE_AHEAD_DAYS)).isoformat()
    out, seen = [], set()
    for _, r in mat.iterrows():
        subj = str(r.get("subject") or "")
        if not _LECT.search(subj) or re.search(r"更正|取消|延期", subj):
            continue
        d = str(r.get("occurred") or "")[:10]
        m = _ROC.search(subj)
        if m:
            d = f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        if not (lo <= d <= hi):
            continue
        key = (str(r["code"]), d)
        if key in seen:
            continue
        seen.add(key)
        out.append({"date": d, "code": str(r["code"]), "name": str(r.get("name") or ""),
                    "note": "公司重大訊息公告（公開資訊觀測站），僅列事實，非推薦", "confidence": CONF})
    return sorted(out, key=lambda x: (x["date"], x["code"]))


# ------------------------------------------------------------------ 組裝
def build(lake: dict, structure: dict, target: date, n: int = DEFAULT_N) -> dict:
    news = lake.get("news")
    idx = build_company_index(structure, lake.get("company_info"))
    data_date = str(news["date"].max()) if news is not None and not news.empty else ""
    warn = ""
    if not data_date:
        warn = "資料湖沒有新聞資料，無法產出選題。"
    else:
        lag = (target - date.fromisoformat(data_date)).days
        if lag > STALE_DAYS:
            warn = f"資料湖最新新聞日期是 {data_date}，落後目標日 {target.isoformat()} 已 {lag} 天（> {STALE_DAYS} 天），選題可能過時。"

    def decorate(items, track):
        res = []
        for it in items:
            ext = extension_topics(it, idx, track)
            res.append({
                "title": it["title"], "source": it["source"], "url": it["url"], "date": it["date"],
                "groups": ext["groups"], "companies": ext["companies"],
                "also_reported_by": [{"source": a["source"], "url": a["url"]} for a in it["also"]],
                "key_point": "",             # 編輯用自己的話填；程式不輸出內文摘要（授權未確認）
                "confidence": CONF, "extension_topics": ext["topics"],
            })
        return res

    return {
        "target_date": target.isoformat(), "data_date": data_date, "warning": warn, "n": n,
        "track_a": {
            "name": "A 總經",
            "schedule": macro_schedule(structure, lake.get("macro_calendar"), target),
            "news": decorate(pick_news(news, "總經", target, n), "A"),
        },
        "track_b": {
            "name": "B 科技",
            "news": decorate(pick_news(news, "科技", target, n), "B"),
            "lectures": lectures(lake.get("material_news"), target),
        },
    }


def render_md(r: dict) -> str:
    L = [f"# 社群選題清單 {r['target_date']}", ""]
    L.append(f"- 資料日期（資料湖最新新聞）：{r['data_date'] or '無'}")
    L.append("- 用途：供 finance-content-editor 查證。**所有項目信心提示＝待查證**；題目建議不構成投資建議，不推薦買賣。")
    L.append("- 授權提醒：只列標題＋來源＋連結，不貼新聞內文；「重點」欄請用自己的話寫（尚未確認再散布授權）。")
    if r["warning"]:
        L += ["", f"> ⚠ 警告：{r['warning']}"]
    L += ["", "## A 總經", "", "### 日程（美東日期；括號內為台灣時間）", ""]
    sch = r["track_a"]["schedule"]
    if not sch:
        L.append("- （區間內無日程，或日程檔讀取失敗）")
    for e in sch:
        ref = f"（{e['ref']}）" if e["ref"] else ""
        L.append(f"- {e['date_et']} 美東／台灣 {e['tw_time']}｜{e['title']}{ref}｜{e['phase']}｜{e['org']}｜{CONF}")
    L += ["", f"### 總經新聞（近 2 日，前 {r['n']} 則）", ""]
    L += _md_news(r["track_a"]["news"])
    L += ["", "## B 科技", "", f"### 科技新聞（近 2 日，前 {r['n']} 則）", ""]
    L += _md_news(r["track_b"]["news"])
    L += ["", "### 附註：本週法說會（公司公告的事實，非推薦）", ""]
    lec = r["track_b"]["lectures"]
    if not lec:
        L.append("- （區間內沒有公告）")
    for x in lec:
        L.append(f"- {x['date']}｜{x['code']} {x['name']}｜{CONF}")
    return "\n".join(L) + "\n"


def _md_news(items: list[dict]) -> list[str]:
    if not items:
        return ["- （近 2 日沒有符合的新聞）"]
    L = []
    for i, it in enumerate(items, 1):
        L.append(f"{i}. **{it['title']}**")
        L.append(f"   - 來源：{it['source']}｜日期：{it['date']}｜[連結]({it['url']})｜信心：{it['confidence']}")
        L.append(f"   - 所屬族群：{'、'.join(it['groups']) or '（未對到）'}")
        if it["also_reported_by"]:
            L.append("   - 另有相似報導：" + "、".join(a["source"] for a in it["also_reported_by"]))
        L.append(f"   - 重點（編輯填）：{it['key_point']}")
        L.append("   - 延伸題建議：")
        L += [f"     - {t}" for t in it["extension_topics"]]
    return L


def write_outputs(result: dict, root: Path) -> tuple[Path, Path]:
    out = root / "docs" / "marketing" / "social_unit" / "daily_topics"
    out.mkdir(parents=True, exist_ok=True)
    md, js = out / f"{result['target_date']}.md", out / f"{result['target_date']}.json"
    md.write_text(render_md(result), encoding="utf-8")
    js.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="產出每日社群選題清單")
    ap.add_argument("--date", help="台北日期 YYYY-MM-DD，預設今天（台北）")
    ap.add_argument("--n", type=int, default=DEFAULT_N, help="每條軌道最多幾則新聞")
    ap.add_argument("--root", default=str(ROOT), help="專案根目錄（測試用）")
    a = ap.parse_args(argv)
    target = date.fromisoformat(a.date) if a.date else datetime.now(TAIPEI).date()
    root = Path(a.root)
    res = build(load_lake(root), load_structure(root), target, a.n)
    md, js = write_outputs(res, root)
    print(f"已產出 {md} 與 {js.name}")
    if res["warning"]:
        print("警告：" + res["warning"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
