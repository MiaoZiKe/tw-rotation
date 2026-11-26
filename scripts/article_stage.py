"""精選文章「上中下游」分類（2026-11-26，Andy：「並且要幫我類別分類 例如半導體上 中下游等等 其他」）。

每篇文章的索引項目帶 chain_stage（up 半導體上游｜mid 半導體中游｜down 半導體下游｜ai AI 伺服器與應用｜other 其他）。
· guess(entry)：依族群代號與標題關鍵字推一個值；判不出來回 other。
· 直接執行：把 site/articles/index.json 與各頻道 site/articles/<key>/index.json 裡**還沒有** chain_stage 的項目補上，印出每篇歸到哪一類。
  已經有值的不動（人工改過的以人工為準）。scripts/article_publish.py 上架時也呼叫 guess() 帶這個欄位。
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGES = ("up", "mid", "down", "ai", "other")

G_UP = {"silicon_wafer", "ip_asic", "hpc_network_ic", "fab_equ", "fab_process_equip", "pkg_equipment", "wide_bandgap", "semi_material", "photomask", "ic_design", "eda"}
G_MID = {"foundry", "hbm", "memory_module", "nor_niche_memory"}
G_DOWN = {"ai_adv_packaging", "osat", "ic_substrate", "test_interface"}
G_AI = {"ai_server_odm", "liquid_cooling", "air_cooling", "server_psu", "bbu", "switch_wireless", "optical_module", "silicon_photonics", "ai_interconnect"}

K_UP = r"IC 設計|IC設計|EDA|矽智財|矽晶圓|光罩|光阻|特用化學|特殊氣體|設備|ASML|應材|科林|東京威力|KLA|第三代半導體|SiC|GaN"
K_MID = r"晶圓代工|IC 代工|曝光|蝕刻|沉積|離子佈植|CMP|清洗|量測|氧化|熱處理|DRAM|HBM|記憶體"
K_DOWN = r"封裝|封測|測試|CoWoS|載板|ABF"
K_AI = r"AI 伺服器|伺服器|散熱|水冷|電源|800V|PSU|BBU|光通訊|CPO|網通|交換器|光模組"


# 2026-11-26 首批歸類時人工校正（標題關鍵字判不準的）：設備廠介紹歸上游、製程步驟歸中游、純市場新聞歸其他
OVERRIDE = {
    "2026-12-11-tech-lam": "up", "2026-12-10-tech-amat": "up", "2026-12-09-tech-asml": "up", "2026-12-08-tech-resist2": "up",
    "2026-11-17-tech-yield": "mid", "2026-11-15-tech-2nm": "mid", "2026-10-19-know-ssd": "mid",
    "2026-10-16-news-tsmc-q3-call": "mid", "2026-10-14-news-tsmc-sep-revenue": "mid", "2026-10-17-news-tesla": "other",
    "2026-10-17-news-sox": "other", "2026-10-20-news-nov-earnings-gap": "other", "2026-10-19-news-week-flow": "other",
    "2026-10-19-news-tsmc-aftermath": "other", "2026-11-17-ligu-power-bill": "ai",
}


def guess(e):
    gs = {g.get("id") for g in (e.get("groups") or []) if isinstance(g, dict)}
    t = str(e.get("title") or "") + " " + " ".join(map(str, e.get("tags") or []))
    # 標題先判（文章主旨），族群後判（族群常一次掛很多個）
    if e.get("id") in OVERRIDE:
        return OVERRIDE[e["id"]]
    for st, k in (("down", K_DOWN), ("ai", K_AI), ("mid", K_MID), ("up", K_UP)):
        if re.search(k, t):
            return st
    for st, g in (("down", G_DOWN), ("ai", G_AI), ("up", G_UP), ("mid", G_MID)):
        if gs & g:
            return st
    return "other"


def _items(d):
    if isinstance(d, list):
        return d
    for k in ("articles", "posts", "list"):
        if isinstance(d.get(k), list):
            return d[k]
    return []


def main():
    files = [ROOT / "site/articles/index.json"] + sorted((ROOT / "site/articles").glob("*/index.json"))
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        n = 0
        for e in _items(d):
            if e.get("chain_stage") in STAGES:
                continue
            e["chain_stage"] = guess(e)
            n += 1
            print(f"{f.parent.name}\t{e['chain_stage']}\t{e.get('id')}\t{e.get('title')}")
        if n:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
