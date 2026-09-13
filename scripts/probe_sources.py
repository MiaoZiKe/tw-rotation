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
}


def one(p: dict) -> dict:
    """打一個端點，把「夠不夠寫 parser」需要知道的東西全部記下來。"""
    rec: dict = {"id": p["id"], "url": p["url"], "note": p.get("note", ""),
                 "method": p.get("method", "GET"), "probed_at": datetime.now(TW).isoformat(timespec="seconds")}
    t0 = time.time()
    try:
        r = requests.request(rec["method"], p["url"], headers={"User-Agent": UA, "Accept": "application/json, */*"},
                             data=p.get("data"), timeout=TIMEOUT)
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
        elif isinstance(j, list):
            rec["kind"] = "list"
            rec["n"] = len(j)
            rec["fields"] = sorted(j[0].keys()) if j and isinstance(j[0], dict) else None
            rec["sample"] = j[:3]
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
                rec["sample"] = {k: j[k] for k in list(j)[:8]}
    except Exception as e:  # 連不上也是結果，要記下來
        rec["status"] = None
        rec["error"] = f"{type(e).__name__}: {e}"
        rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    return rec


def run(name: str) -> Path:
    probes = PROBES[name]
    out = {"probe": name, "at": datetime.now(TW).isoformat(timespec="seconds"),
           "results": [one(p) for p in probes]}
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{name}_probe.json"
    f.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in out["results"]:
        mark = "OK " if r.get("status") == 200 else "-- "
        extra = ""
        if r.get("matched_paths") is not None:
            extra = f" 命中 {len(r['matched_paths'])} 個路徑（全部 {r.get('all_paths_n')} 個）"
        elif r.get("kind") == "list":
            extra = f" {r.get('n')} 筆，欄位 {r.get('fields')}"
        print(f"{mark}{r['id']:22s} {r.get('status')} {r.get('bytes', 0)}B{extra}{'  ' + r['error'] if r.get('error') else ''}")
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
