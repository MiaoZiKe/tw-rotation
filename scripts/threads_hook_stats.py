"""Threads 改版前後成效比較（2026-11-01 Andy：「IG Thread 上面也需要進行優化 讓熱度提升」）。

把三份 social-snaps 上的紀錄串起來（都不需要新金鑰；成效由 social_insights.py 每晚 23:10 用既有權杖抓）：
  state/posted.json        主貼文每個時段鍵 → Threads 貼文 id／連結
  state/hook_history.json  v2 每篇用了哪個鉤子模板、開頭類型、情緒、標籤（鍵＝posted.json 的時段鍵）
  state/posts_catalog.json 每篇貼文的 views／likes／replies／reposts／quotes／shares
另讀 repo 的 social/threads/queue/*_news-*.md（主題文章；檔頭有 hook_type／emotion／hook_id 與 urls）。
輸出 state/hook_stats.json：改版前（v1）／改版後（v2）、依開頭類型、依情緒、依模板、依時段的平均瀏覽與互動率。

用法：python scripts/threads_hook_stats.py --posted state/posted.json --hooks state/hook_history.json \
        --catalog state/posts_catalog.json --out state/hook_stats.json
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V2_START = "2026-11-02"       # 正式套用日（第一個交易日盤前）
INTER = ("likes", "replies", "reposts", "quotes", "shares")


def _load(p) -> dict:
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _norm(u: str) -> str:
    return (u or "").rstrip("/").replace("threads.net", "threads.com")


def threads_metrics(catalog: dict) -> tuple[dict, dict]:
    by_id, by_link = {}, {}
    for k, v in (catalog.get("posts") or {}).items():
        if (v.get("platform") or k.split(":")[0]).startswith("threads") or "threads" in str(v.get("permalink", "")):
            mt = v.get("metrics") or {}
            by_id[str(v.get("id") or k.split(":")[-1])] = mt
            if v.get("permalink"):
                by_link[_norm(v["permalink"])] = mt
    return by_id, by_link


def rows(posted: dict, hooks: dict, catalog: dict, root: Path = ROOT) -> list[dict]:
    by_id, by_link = threads_metrics(catalog)
    hk = {h.get("key"): h for h in hooks.get("history", []) if h.get("key")}
    out = []
    for key, rec in posted.items():
        th = rec.get("threads") if isinstance(rec, dict) else None
        if not th:
            continue
        mt = by_id.get(str(th.get("id"))) or by_link.get(_norm(th.get("link", "")))
        if not mt:
            continue
        day = (rec.get("at") or "")[:10] or re.sub(r"^\D*", "", key)[:10]
        h = hk.get(key, {})
        out.append(dict(src="主貼文", key=key, kind=key.split("-")[0], date=day, ver="v2" if (h or day >= V2_START) else "v1",
                        hook_type=h.get("type", ""), emotion=h.get("emotion", ""), template=h.get("template", ""), metrics=mt))
    for f in sorted((root / "social/threads/queue").glob("*_news-*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.match(r"\A---\s*\n(.*?)\n---", t, re.S)
        meta = {a.strip(): b.strip() for a, _, b in (l.partition(":") for l in (m.group(1).splitlines() if m else [])) if _}
        if meta.get("status") != "posted":
            continue
        first = _norm((meta.get("urls") or "").split(" ")[0])
        mt = by_link.get(first)
        if not mt:
            continue
        out.append(dict(src="主題文章", key=f.stem, kind="article", date=f.stem[:10],
                        ver="v2" if meta.get("format") == "threads_v2" else "v1", hook_type=meta.get("hook_type", ""),
                        emotion=meta.get("emotion", ""), template=meta.get("hook_id", ""), metrics=mt))
    return out


def agg(rs: list[dict], dim: str) -> dict:
    g: dict = {}
    for r in rs:
        k = r.get(dim) or "（無）"
        a = g.setdefault(k, dict(n=0, views=0, inter=0))
        a["n"] += 1
        a["views"] += int(r["metrics"].get("views") or 0)
        a["inter"] += sum(int(r["metrics"].get(x) or 0) for x in INTER)
    for a in g.values():
        a["avg_views"] = round(a["views"] / a["n"], 1)
        a["avg_inter"] = round(a["inter"] / a["n"], 2)
        a["inter_rate"] = round(a["inter"] / a["views"], 4) if a["views"] else None
    return g


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--posted", default="state/posted.json")
    ap.add_argument("--hooks", default="state/hook_history.json")
    ap.add_argument("--catalog", default="state/posts_catalog.json")
    ap.add_argument("--out", default="state/hook_stats.json")
    a = ap.parse_args(argv)
    rs = rows(_load(a.posted), _load(a.hooks), _load(a.catalog))
    res = dict(updated=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="minutes"), v2_start=V2_START, posts=len(rs),
               by_version=agg(rs, "ver"), by_version_kind={v: agg([r for r in rs if r["ver"] == v], "kind") for v in ("v1", "v2")},
               by_hook_type=agg([r for r in rs if r["ver"] == "v2"], "hook_type"),
               by_emotion=agg([r for r in rs if r["ver"] == "v2"], "emotion"),
               by_template=agg([r for r in rs if r["ver"] == "v2"], "template"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"成效比較：{len(rs)} 篇；" + "；".join(f"{k} {v['n']} 篇 平均瀏覽 {v['avg_views']}" for k, v in res["by_version"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
