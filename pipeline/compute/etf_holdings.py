"""ETF 成分股 → site/data/etf_holdings.json（前端 industry.js tabHoldings 讀）。

輸入：資料湖 etf_holdings（各投信 PCF，pipeline/sources/etf_pcf.py）＋ etf_holdings_monthly（公會每月前十大，sources/sitca.py）
      ＋ 人工整理檔 pipeline/etf/holdings_manual.yaml。
規則：
- 每檔 ETF 取資料湖裡**最新一個持股基準日**的那一份。
- 投信沒給權重（元大只給股數）→ 用「股數 × 該日（或之前最近一日）收盤價」占股票部位的比例推算，標 est=true，
  前端註明「依股數×收盤價推算」。查不到價的成分（外股）不算進分母、權重留空。
- 自動來源沒有、但人工檔有 → 用人工檔，標 manual=true 與資料日期、來源網址（前端標「人工整理・資料日期 X」）。
  兩者都有時以日期較新的為準（人工檔是補洞用的，不蓋過每天自動更新的資料）。
- 兩者都沒有 → 不放進 etfs；issuers[代號] 仍給發行投信名，前端據此寫「此檔發行投信（X）資料尚未接上」。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd
import yaml

from ..sources.etf_pcf import CONNECTED, NOT_CONNECTED_WHY, bond_terms, issuer_of

log = logging.getLogger(__name__)

MANUAL = Path(__file__).resolve().parents[1] / "etf" / "holdings_manual.yaml"


def load_manual(path: Path = MANUAL) -> dict:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 —— 人工檔寫壞不該讓整份 payload 掛掉
        log.warning("讀 %s 失敗：%s", path, exc)
        return {}
    return doc.get("etfs") or {}


def _est_weights(g: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    """股數×收盤價 → 占股票部位 %。px：price_daily（date, code, close），取 ≤ 持股基準日的最近一筆。"""
    day = str(g["date"].iloc[0])
    p = px[(px["date"].astype(str) <= day) & px["code"].astype(str).isin(g["code"].astype(str))]
    if p.empty:
        return g.assign(weight=None)
    last = p.sort_values("date").groupby("code")["close"].last()
    mv = g["code"].astype(str).map(last) * pd.to_numeric(g["shares"], errors="coerce")
    tot = mv.sum(skipna=True)
    g = g.copy()
    g["weight"] = (mv / tot * 100).where(mv.notna()) if tot and tot > 0 else None
    return g


SITCA_NAME = "投信投顧公會（各投信每月申報的前十大）"


def _monthly_records(monthly: pd.DataFrame | None, names: dict[str, str]) -> dict[str, dict]:
    """公會每月前十大（pipeline/sources/sitca.py → 資料湖 etf_holdings_monthly）→ {代號: 前端格式}。每檔取湖裡最新的月份。"""
    out: dict[str, dict] = {}
    if monthly is None or monthly.empty or "etf" not in monthly.columns:
        return out
    m = monthly[monthly["etf"].notna() & (monthly["etf"].astype(str) != "")].copy()
    if m.empty:
        return out
    m["date"] = m["date"].astype(str)
    m["etf"] = m["etf"].astype(str)
    m = m[m["date"] == m.groupby("etf")["date"].transform("max")]
    for etf, g in m.groupby("etf"):
        g = g.sort_values("rank") if "rank" in g.columns else g
        items = []
        for r in g.itertuples(index=False):
            w = getattr(r, "weight", None)
            if w is None or pd.isna(w):
                continue
            it = {"code": str(r.code), "name": str(r.name or ""), "w": round(float(w), 4), "shares": None}
            if not re.match(r"^\d{4,6}[A-Z]?$", it["code"]):
                cpn, mat = bond_terms(it["name"])
                if mat:
                    it["cpn"], it["mat"] = cpn, mat
            items.append(it)
        if not items:
            continue
        items.sort(key=lambda x: -(x["w"] or 0))
        out[etf] = {"asof": str(g["date"].iloc[0]), "issuer": (issuer_of(names.get(etf, "")) or str(g["issuer"].iloc[0] or "")) if "issuer" in g else (issuer_of(names.get(etf, "")) or ""),
                    "src": str(g["src"].iloc[0]) if "src" in g else "", "src_name": SITCA_NAME,
                    "monthly": True, "top_n": len(items), "est": False, "items": items}
    return out


def build(hold: pd.DataFrame, price: pd.DataFrame, names: dict[str, str],
          etf_codes: set[str] | None = None, manual: dict | None = None,
          monthly: pd.DataFrame | None = None) -> dict:
    """來源優先順序（2026-10-08 Andy：「每一檔用第一個成功的來源」）：
    ① 發行投信官網每日公告（資料湖 etf_holdings，每檔取湖裡自己最近一次）
    ② 投信投顧公會每月前十大（資料湖 etf_holdings_monthly，月資料）
    ③ 人工整理檔（pipeline/etf/holdings_manual.yaml）；人工檔比 ① 新時仍以人工檔為準（舊規則，補洞用）。"""
    manual = load_manual() if manual is None else manual
    etfs: dict[str, dict] = {}
    srcs: set[str] = set()
    if hold is not None and not hold.empty:
        h = hold.copy()
        h["date"] = h["date"].astype(str)
        h["etf"] = h["etf"].astype(str)
        latest = h.groupby("etf")["date"].transform("max")
        h = h[h["date"] == latest]
        px = price[["date", "code", "close"]] if price is not None and not price.empty else pd.DataFrame(columns=["date", "code", "close"])
        for etf, g in h.groupby("etf"):
            est = g["weight"].isna().all()
            if est:
                g = _est_weights(g, px)
            items = []
            for r in g.itertuples(index=False):
                w = None if pd.isna(r.weight) else round(float(r.weight), 4)
                sh = None if pd.isna(r.shares) else float(r.shares)
                it = {"code": str(r.code), "name": str(r.name or ""), "w": w,
                      "shares": None if sh is None else int(round(sh))}
                # 債券成分（代號不是台股那種 4～6 碼數字）：從名稱讀票面利率與到期日給前端多顯示一行（讀不出來就不帶）
                if not re.match(r"^\d{4,6}[A-Z]?$", it["code"]):
                    cpn, mat = bond_terms(it["name"])
                    if mat:
                        it["cpn"], it["mat"] = cpn, mat
                items.append(it)
            items.sort(key=lambda x: -(x["w"] or 0))
            issuer = str(g["issuer"].iloc[0]) if "issuer" in g else ""
            src = str(g["src"].iloc[0]) if "src" in g else ""
            srcs.add(issuer)
            etfs[etf] = {"asof": str(g["date"].iloc[0]), "issuer": issuer, "src": src, "est": bool(est), "items": items}
    for code, rec in _monthly_records(monthly, names).items():
        if code not in etfs:            # ① 沒有才用 ②；官網每日公告永遠優先
            etfs[code] = rec
    for code, m in (manual or {}).items():
        code = str(code)
        asof = str(m.get("asof") or "")
        if code in etfs and (etfs[code].get("monthly") or etfs[code]["asof"] >= asof):
            continue                     # 有 ①（而且比人工檔新）或有 ② → 不用人工檔
        items = [{"code": str(x.get("code")), "name": str(x.get("name") or ""),
                  "w": None if x.get("w") is None else float(x["w"]),
                  "shares": None if x.get("shares") is None else int(x["shares"])} for x in (m.get("items") or [])]
        items = [x for x in items if x["w"] is not None]
        if not items:
            continue
        etfs[code] = {"asof": asof, "issuer": m.get("issuer") or issuer_of(names.get(code, "")) or "",
                      "src": m.get("src") or "", "src_name": m.get("src_name") or "", "manual": True,
                      "note": m.get("note") or "", "items": items}
    codes = set(etf_codes or ()) | set(etfs)
    issuers = {c: (issuer_of(names.get(c, "")) or "") for c in sorted(codes)}
    asof = max((v["asof"] for v in etfs.values()), default="")
    return {"asof": asof,
            "source": "各發行投信官網每日公告之申購買回清單（PCF）／基金持股明細；抓不到的用投信投顧公會每月前十大（月資料）或人工整理（標明）",
            "connected": sorted(CONNECTED),
            "why": dict(NOT_CONNECTED_WHY),   # 還沒接上的投信 → 原因（前端成分股分頁照抄，不再只寫「尚未接上」）
            "issuers": issuers,
            "etfs": etfs}
