"""Threads 熱門財經串採集器（2026-11-09；只讀，不發文、不回覆）。

為什麼：研調員只能用 WebSearch，看不到 Threads 貼文本身；容器連不上 graph.threads.net，但 GitHub Actions 連得上。
做法：對每個關鍵字呼叫 keyword_search（search_type=TOP），每個取前 N 則（預設 50），只輸出統計：
  <out>/<日期>_stats.json、<日期>_stats.md。工作流程把它們寫到 social-snaps 分支 research/threads_hot/。
★ 2026-11-09 CEO 拍板：原始資料（全文、帳號名、permalink）只留在這支程式執行期間的記憶體，跑完就丟，不寫檔、不 commit。
  帳號只記次數不記名字（threads_search.stats）。

用法：
  python scripts/threads_hot_collect.py --out research/threads_hot            （讀 THREADS_ACCESS_TOKEN）
  python scripts/threads_hot_collect.py --keywords 台股,外資 --limit 25
結束碼：0＝有抓到（含「只搜得到自己的貼文」，那是權限問題不是程式壞）；1＝權杖無效或全部關鍵字都失敗。
權限不夠時 <日期>_stats.md 最上面會寫「只搜得到自己的貼文」→ 照 docs/marketing/social_unit/auto_reply.md 第六節請 Andy 授權。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import threads_search as S  # noqa: E402

def collect(token: str, keywords, limit: int, search_type: str = "TOP", call=None) -> tuple[list[dict], dict, list[str]]:
    rows, errs, used = [], [], {}
    for kw in keywords:
        try:
            got, fields = S.search(token, kw, search_type, limit, call=call)
            rows += got
            used[kw] = "完整欄位" if fields == S.FIELDS_FULL else "基本欄位（Meta 不收讚數欄位）"
        except S.SearchError as e:
            errs.append(f"{kw}：{str(e)[:160]}")
    return rows, used, errs


def write(out: Path, day: str, st: dict, perm: str, meta: dict) -> list[Path]:
    """只寫統計（不含任何貼文全文、帳號名、permalink）。"""
    out.mkdir(parents=True, exist_ok=True)
    j, m = out / f"{day}_stats.json", out / f"{day}_stats.md"
    j.write_text(json.dumps({"date": day, "permission": perm, "meta": meta, "stats": st},
                            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    m.write_text(S.stats_md(st, day, perm), encoding="utf-8")
    return [j, m]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Threads 熱門財經串採集（只讀）")
    ap.add_argument("--keywords", default=",".join(S.DEFAULT_KEYWORDS))
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--search-type", default="TOP", choices=("TOP", "RECENT"))
    ap.add_argument("--out", default="research/threads_hot")
    a = ap.parse_args(argv)
    tok = (os.environ.get("THREADS_ACCESS_TOKEN") or "").strip()
    if not tok:
        print("✗ 沒有 THREADS_ACCESS_TOKEN")
        return 1
    try:
        me = str(S._call("GET", "/me", tok, {"fields": "id,username"}).get("username") or "")
    except S.SearchError as e:
        print(f"✗ 權杖無效：{e}")
        return 1
    kws = [k.strip() for k in a.keywords.split(",") if k.strip()]
    rows, used, errs = collect(tok, kws, a.limit, a.search_type)
    perm = S.permission_state(rows, me)
    if errs and any("threads_keyword_search" in e or "permission" in e.lower() or "(#10)" in e for e in errs):
        perm = "missing_permission"
    st = S.stats(rows)
    day = datetime.now(S.TAIPEI).strftime("%Y-%m-%d")
    meta = {"search_type": a.search_type, "limit": a.limit, "keywords": kws, "fields": used, "errors": errs,
            "collected_at": datetime.now(S.TAIPEI).isoformat(timespec="seconds")}
    del rows                                   # 原始資料用完就丟
    for p in write(Path(a.out), day, st, perm, meta):
        print(f"寫出 {p}")
    print(S.stats_md(st, day, perm))
    for e in errs:
        print(f"⚠ {e}")
    print(f"PERMISSION={perm}")
    if gh := os.environ.get("GITHUB_OUTPUT"):
        with open(gh, "a", encoding="utf-8") as f:
            f.write(f"permission={perm}\nposts={st['posts']}\n")
    return 1 if errs and len(errs) == len(kws) else 0


if __name__ == "__main__":
    sys.exit(main())
