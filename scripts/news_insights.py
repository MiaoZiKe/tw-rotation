"""新聞貼文成效回收＋每週優化（2026-10-28，Andy：「依據不同的內容後台紀錄，後續慢慢改善收斂成大家喜歡的主題、內容、版面、風格」）。

資料來源（都不需要新金鑰）：
  · social/{ig,threads}/queue/*_news-*.md：每篇的標籤（topic_category、content_type、layout、style、has_ai_image、explore、u_code）
    與發出後回寫的 urls（貼文網址）。
  · state/posts_catalog.json（social_insights.yml 每晚更新）：每篇貼文的觸及／瀏覽／讚／留言／分享／儲存。
  · 點擊（?u= 漏斗）：漏斗數字在帳號 Worker 的管理區（需要管理者登入），Actions 拿不到；
    若環境變數 FUNNEL_JSON 指到 {"newspre1_20261029": 進站次數, ...} 的檔案就一起算，沒有就記 null。

用法：
  python scripts/news_insights.py --catalog state/posts_catalog.json --out state/news_insights.json
  python scripts/news_insights.py --catalog ... --weekly docs/marketing/news_weekly/2026-11-02.md --weights social/news/weights.json
權重規則（docs/marketing/social_unit/news_auto.md 第五節）：
  各標籤值的「互動率」（互動數 ÷ 瀏覽數）對全體平均的比值，按樣本數收斂（n/(n+5)），夾在 0.6～1.6；樣本 < 3 篇維持 1.0。
  探索比例固定 20%（social_news.py 每段保留 1 篇隨機主題／風格），避免只收斂在早期碰巧表現好的類別。
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPE = timezone(timedelta(hours=8))
DIMS = ["topic_category", "content_type", "layout", "style", "has_ai_image", "slot"]
DIM_NAME = {"topic_category": "主題", "content_type": "內容型態", "layout": "版面", "style": "風格", "has_ai_image": "AI 圖", "slot": "時段"}
SLOT_NAME = {"pre": "盤前", "intra": "盤中", "post": "盤後"}
EXPLORE = 0.2


def parse_md(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---", t, re.S)
    meta = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(":")
        if _:
            meta[k.strip()] = v.strip()
    return meta


def interactions(platform: str, mt: dict) -> int:
    keys = ["likes", "comments", "shares", "saved"] if platform == "ig" else ["likes", "replies", "reposts", "quotes", "shares"]
    return sum(int(mt.get(k) or 0) for k in keys)


def collect(catalog: dict, funnel: dict, root: Path = ROOT) -> list[dict]:
    by_link = {}
    for v in (catalog.get("posts") or {}).values():
        if v.get("permalink"):
            by_link[v["permalink"].rstrip("/")] = v
    rows = []
    for plat, q in (("ig", root / "social/ig/queue"), ("threads", root / "social/threads/queue")):
        for f in sorted(q.glob("*_news-*.md")):
            meta = parse_md(f)
            mm = re.match(r"(\d{4}-\d{2}-\d{2})_news-(pre|intra|post)-(\d+)", f.stem)
            if not mm or meta.get("status") != "posted":
                continue
            day, slot, _ = mm.groups()
            link = (meta.get("urls") or "").split()[0].rstrip("/") if meta.get("urls") else ""
            cat = by_link.get(link, {})
            mt = cat.get("metrics") or {}
            ucode = f"{meta.get('u_code', '')}_{day.replace('-', '')}"
            rows.append(dict(file=f.name, platform=plat, date=day, slot=slot, link=link,
                             **{d: meta.get(d, "") for d in DIMS if d != "slot"},
                             explore=meta.get("explore", "false"),
                             views=mt.get("views"), reach=mt.get("reach"), likes=mt.get("likes"),
                             replies=mt.get("replies", mt.get("comments")), shares=mt.get("shares"), saved=mt.get("saved"),
                             interactions=interactions(plat, mt) if mt else None,
                             clicks=funnel.get(ucode) if funnel else None, measured=bool(mt)))
    return rows


def aggregate(rows: list[dict]) -> dict:
    out = {}
    for d in DIMS:
        g = {}
        for r in rows:
            if not r["measured"]:
                continue
            k = r.get(d) or "（未標）"
            a = g.setdefault(k, dict(n=0, views=0, interactions=0, shares=0, saved=0, clicks=0, clicks_n=0))
            a["n"] += 1
            a["views"] += int(r["views"] or 0); a["interactions"] += int(r["interactions"] or 0)
            a["shares"] += int(r["shares"] or 0); a["saved"] += int(r["saved"] or 0)
            if r["clicks"] is not None:
                a["clicks"] += int(r["clicks"]); a["clicks_n"] += 1
        for a in g.values():
            a["eng_rate"] = round(a["interactions"] / a["views"], 4) if a["views"] else 0.0
            a["avg_views"] = round(a["views"] / a["n"], 1) if a["n"] else 0.0
        out[d] = g
    return out


def weights(agg: dict) -> dict:
    w = {"explore": EXPLORE}
    for d in ("topic_category", "content_type", "style", "layout"):
        g = agg.get(d, {})
        tv = sum(a["views"] for a in g.values()); ti = sum(a["interactions"] for a in g.values())
        base = ti / tv if tv else 0
        dw = {}
        for k, a in g.items():
            if a["n"] < 3 or not base:
                dw[k] = 1.0; continue
            ratio = (a["eng_rate"] / base) if base else 1.0
            shrink = a["n"] / (a["n"] + 5)
            dw[k] = round(min(1.6, max(0.6, 1 + (ratio - 1) * shrink)), 3)
        w[d] = dw
    return w


def weekly_md(rows: list[dict], agg: dict, w: dict, day: str) -> str:
    m = [f"# 新聞貼文週報（{day}）", "",
         "> 自動產生（scripts/news_insights.py，social_style_weekly.yml 每週一）。指標：互動率＝互動數 ÷ 瀏覽數；"
         "互動＝IG 讚＋留言＋分享＋儲存／Threads 讚＋回覆＋轉發＋引用＋分享。點擊（?u= 漏斗）Actions 讀不到時顯示「—」。", "",
         f"統計範圍：最近 14 天已發出的新聞貼文 {len(rows)} 則（已回收成效 {sum(r['measured'] for r in rows)} 則；"
         f"探索篇 {sum(r['explore'] == 'true' for r in rows)} 則）。", ""]
    for d in DIMS:
        g = agg.get(d, {})
        if not g:
            continue
        m += [f"## {DIM_NAME[d]}排名", "", "| 名次 | 值 | 篇數 | 平均瀏覽 | 互動率 | 分享 | 儲存 | 點擊 | 下週權重 |", "|---|---|---|---|---|---|---|---|---|"]
        for i, (k, a) in enumerate(sorted(g.items(), key=lambda kv: (-kv[1]["eng_rate"], -kv[1]["n"])), 1):
            name = SLOT_NAME.get(k, k) if d == "slot" else k
            ww = w.get(d, {}).get(k, "—")
            ck = a["clicks"] if a["clicks_n"] else "—"
            m.append(f"| {i} | {name} | {a['n']} | {a['avg_views']} | {a['eng_rate']*100:.2f}% | {a['shares']} | {a['saved']} | {ck} | {ww} |")
        m.append("")
    m += ["## 下週加權建議", ""]
    for d in ("topic_category", "content_type", "style", "layout"):
        dw = w.get(d, {})
        up = [k for k, v in dw.items() if v > 1.05]; dn = [k for k, v in dw.items() if v < 0.95]
        m.append(f"- {DIM_NAME[d]}：提高 {'、'.join(up) or '（無）'}；降低 {'、'.join(dn) or '（無）'}；其餘維持 1.0。")
    m += [f"- 探索比例維持 {int(EXPLORE*100)}%：每段至少 1 篇從還沒選到的主題隨機挑，風格也隨機，避免過早收斂。",
          "- 樣本少於 3 篇的值一律不調權重（1.0）。權重已寫入 `social/news/weights.json`，下一次選題自動套用。",
          "", "## 人工覆核點", "",
          "- 排名第一與最後一名各抽 1 篇看原文：是內容好壞，還是發文時段、同日大事件造成的差異？",
          "- 權重變動超過 ±0.3 的類別，請 CEO 確認不是單篇爆量造成。", ""]
    return "\n".join(m)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="state/posts_catalog.json")
    ap.add_argument("--out", default="state/news_insights.json")
    ap.add_argument("--weekly", default="")
    ap.add_argument("--weights", default=str(ROOT / "social/news/weights.json"))
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args(argv)
    try:
        catalog = json.loads(Path(a.catalog).read_text(encoding="utf-8"))
    except Exception:
        catalog = {}
    funnel = {}
    if os.environ.get("FUNNEL_JSON"):
        try:
            funnel = json.loads(Path(os.environ["FUNNEL_JSON"]).read_text(encoding="utf-8"))
        except Exception:
            funnel = {}
    now = datetime.now(TPE)
    lo = (now - timedelta(days=a.days)).strftime("%Y-%m-%d")
    rows = [r for r in collect(catalog, funnel) if r["date"] >= lo]
    agg = aggregate(rows)
    w = weights(agg)
    res = dict(updated=now.isoformat(timespec="seconds"), window_days=a.days, posts=rows, agg=agg, weights=w)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"新聞貼文 {len(rows)} 則（已回收 {sum(r['measured'] for r in rows)} 則）→ {a.out}")
    if a.weekly:
        w["updated"] = now.strftime("%Y-%m-%d")
        Path(a.weights).parent.mkdir(parents=True, exist_ok=True)
        Path(a.weights).write_text(json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
        Path(a.weekly).parent.mkdir(parents=True, exist_ok=True)
        Path(a.weekly).write_text(weekly_md(rows, agg, w, now.strftime("%Y-%m-%d")), encoding="utf-8")
        print(f"週報 → {a.weekly}；權重 → {a.weights}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
