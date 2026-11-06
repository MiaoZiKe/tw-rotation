"""每週檢查：官方有沒有把「臺股儀表板」那類資料（全市場擔保維持率、追繳／處分戶數與金額）開放出來（2026-11-06）。

為什麼要有這一支：
  Andy 11-06 想在信用交易頁放證交所臺股儀表板的「全市場擔保維持率、追繳戶數、追繳金額、處分戶數、處分金額」。
  查證結果：那些數字只在儀表板頁出現，背後是 www.twse.com.tw/rwd 與櫃買 tpex-api 網頁介面（條款禁止自動擷取，
  DECISIONS #1／#265），openapi.twse.com.tw、www.tpex.org.tw/openapi、data.gov.tw、FinMind 免費版都沒有 → 不做。
  但官方隨時可能把它放進 OpenAPI。這支每週掃一次兩家 OpenAPI 的 swagger 與 FinMind 的資料集清單，
  一旦出現就寫進 data/_state/official_open_watch.json，build_payload 帶進 meta.json，資料狀態提示「官方已開放，可以接上」。
  不寄信（Andy 11-06）。

比對規則（寫死、不調）：
  · 強關鍵字：維持率、追繳、儀表板、dashboard、maintenance —— 摘要／路徑／資料集名命中就算；
  · 「處分」單獨太寬（「取得或處分資產」之類），要同時出現 融資／信用／擔保／margin 才算。
  · 狀態檔的 ignore 清單保留跨週：確認是誤判的端點寫進去，之後不再提示。
用法：python -m pipeline.open_watch（Actions：.github/workflows/open-data-watch.yml，每週一次）。
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from . import config
from .util import http

log = logging.getLogger(__name__)

STATE_FILE = config.STATE / "official_open_watch.json"
SWAGGERS = (("twse", config.TWSE_OPENAPI + "/swagger.json"), ("tpex", "https://www.tpex.org.tw/openapi/swagger.json"))
# FinMind 官方 Python 套件的資料集列舉（公開 GitHub 原始碼；api.finmindtrade.com 沒有「列出全部資料集」的端點）
FINMIND_LIST = "https://raw.githubusercontent.com/FinMind/FinMind/master/FinMind/schema/data.py"
# 直接試的候選資料集名（FinMind 若有維持率，命名慣例會長這樣）；回 200 且有資料＝目前這把 token 的等級可用
FINMIND_PROBE = ("TaiwanStockMarginMaintenanceRatio", "TaiwanTotalMarginMaintenanceRatio", "TaiwanStockTotalMarginMaintenance")
STRONG = re.compile(r"維持率|追繳|儀表板|dashboard|maintenance", re.I)
DISPOSE = re.compile(r"處分")
CREDIT = re.compile(r"融資|信用|擔保|margin", re.I)


def is_hit(text: str) -> bool:
    """一段文字（摘要＋路徑，或資料集名）是不是我們要找的東西。"""
    t = str(text or "")
    return bool(STRONG.search(t) or (DISPOSE.search(t) and CREDIT.search(t)))


def swagger_hits(sw: dict | None) -> tuple[int, list[dict]]:
    """swagger.json → (路徑總數, 命中清單[{path, summary}])。"""
    paths = (sw or {}).get("paths") or {}
    hits = []
    for p, spec in paths.items():
        summ = " ".join(str((op or {}).get("summary", "")) + " " + str((op or {}).get("description", ""))
                        for op in (spec or {}).values() if isinstance(op, dict)).strip()
        if is_hit(p + " " + summ):
            hits.append({"path": p, "summary": summ[:120]})
    return len(paths), hits


def finmind_names(src: str | None) -> list[str]:
    """FinMind schema/data.py 原始碼 → 資料集名稱清單（抓 `Xxx = "Xxx"` 這種列舉值，抓不到回空）。"""
    if not src:
        return []
    return sorted(set(re.findall(r"""=\s*["']((?:Taiwan|US|Euro|Japan|UK|Crypto|Gold|Crude|Government|Interest|Exchange|Cnn|Fear|Total)[A-Za-z0-9]+)["']""", src)))


def _load() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run(fetch=http.get, fm_get=http.finmind_get) -> dict:
    """掃一輪，回傳新的狀態並寫檔。fetch／fm_get 可替換（測試用）。

    狀態格式：{checked_at, sources:{twse:{ok,n_paths}, tpex:{...}, finmind:{ok,n_datasets,listed,probe}},
              hits:[{src, path, summary, first_seen}], ignore:[path...], open: bool, msg}
    open＝有任何未忽略的命中；msg 是前端資料狀態直接顯示的一句話。"""
    old = _load()
    ignore = list(old.get("ignore") or [])
    seen = {(h.get("src"), h.get("path")): h.get("first_seen") for h in old.get("hits") or []}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    srcs, hits = {}, []
    for name, url in SWAGGERS:
        sw = fetch(url, headers={"Referer": "https://www.tpex.org.tw/"} if name == "tpex" else None)
        ok = isinstance(sw, dict) and bool(sw.get("paths"))
        n, h = swagger_hits(sw if ok else None)
        srcs[name] = {"ok": ok, "n_paths": n}
        for x in h:
            hits.append({"src": name, **x})
    src = fetch(FINMIND_LIST, expect_json=False)
    names = finmind_names(src if isinstance(src, str) else None)
    fm = {"ok": bool(names), "n_datasets": len(names), "probe": {}}
    # FinMind 清單裡有名字不等於免費版拿得到（2026-11-06 第一輪就掃到 TaiwanStockMarginMaintenance）：
    # 清單命中的名字＋猜的名字都用目前這把 token 實際問一次（先全市場、再帶 2330），拿得到資料才算「可以接上」；
    # 只在清單上、拿不到的記成 listed（多半是贊助會員限定），不亮提示。每週最多多花十幾次額度。
    start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    listed = [nm for nm in names if is_hit(nm)]
    fm["listed"] = listed
    for ds in list(dict.fromkeys(listed + list(FINMIND_PROBE))):
        rows = fm_get(ds, start_date=start) or fm_get(ds, data_id="2330", start_date=start)
        fm["probe"][ds] = bool(rows)
        if rows:
            hits.append({"src": "finmind", "path": ds, "summary": "FinMind 資料集（目前 token 等級取得到資料）"})
    srcs["finmind"] = fm
    for h in hits:
        h["first_seen"] = seen.get((h["src"], h["path"])) or now
    live = [h for h in hits if h["path"] not in ignore]
    st = {"checked_at": now, "sources": srcs, "hits": hits, "ignore": ignore, "open": bool(live),
          "msg": ("官方已開放融資維持率／追繳／處分相關資料（" + "、".join(f"{h['src']} {h['path']}" for h in live[:3])
                  + "），可以接上") if live else ""}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    log.info("官方開放檢查：%s；命中 %d 筆（未忽略 %d）", {k: v.get("ok") for k, v in srcs.items()}, len(hits), len(live))
    return st


def for_meta() -> dict:
    """給 build_payload 的 meta.json：只帶前端要的幾個欄位。檔案不在／壞掉回 {}。"""
    s = _load()
    if not s:
        return {}
    return {"checked_at": s.get("checked_at"), "open": bool(s.get("open")), "msg": s.get("msg") or "",
            "ok": {k: bool((v or {}).get("ok")) for k, v in (s.get("sources") or {}).items()}}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(json.dumps(run(), ensure_ascii=False, indent=1)[:3000])
