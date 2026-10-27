"""自選日報／自設提醒的事實資料層（2026-10-27，Andy 拍板 T-4；規格 docs/marketing/tier_plan_1027.md W7、法遵 L-13）。

為什麼算在 pipeline、而不是 Worker：資料全在資料湖，盤後 build_payload 本來就整批讀過一次，順手多產一份
site/data/digest.json 最省（不新增任何抓取、Worker 不必碰資料湖）。前端拿這份「全市場事實表」，
依會員自己的自選清單／自設條件在瀏覽器裡組日報、判斷提醒 —— 所以自選清單與提醒條件不會被送到任何第三方。

★ 欄位白名單（法遵 L-13）：只放事實 ——
    收盤價、前收、成交量；三大法人當日買賣超與連續買賣超天數；最新一期月營收（金額、年增、月增、公布日）；
    公告事件（除息日、法說會日期、財報公布日）。
  不放：評分、排名、技術燈號、AI 分析、進出場時機、買賣建議。測試 tests/test_digest.py 會掃整份輸出的鍵名與字串。
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

# 輸出裡允許出現的鍵（白名單）；測試用它比對，新增欄位要先改這裡並過法遵
ALLOWED_KEYS = {"n", "c", "pc", "v", "i", "ia", "k", "r", "x", "e"}
R_KEYS = {"ym", "rev", "yoy", "mom", "ann"}
CODE_OK = re.compile(r"^[0-9][0-9A-Z]{3,5}$")
EV_KIND = {"conf": "法說會", "invite": "法說會", "report": "財報公布"}


def _streaks(inst: pd.DataFrame, latest: str, cols: list[str], n_days: int = 40) -> tuple[dict, str | None]:
    """每檔「截至最新一天，連續買超（正）／賣超（負）幾天」。0＝最新一天剛好不買不賣或沒資料。"""
    if inst is None or inst.empty:
        return {}, None
    d = inst[inst["date"].astype(str) <= latest]
    dates = sorted(d["date"].astype(str).unique())[-n_days:]
    if not dates:
        return {}, None
    d = d[d["date"].astype(str).isin(dates)]
    out: dict[str, list[int]] = {}
    for col in cols:
        pv = d.pivot_table(index="date", columns="code", values=col, aggfunc="sum").reindex(dates).fillna(0.0)
        sg = np.sign(pv.to_numpy())                      # 日 × 檔
        last = sg[-1]
        run = np.zeros(sg.shape[1], dtype=int)
        alive = last != 0
        for row in sg[::-1]:
            alive = alive & (row == last)
            run += alive.astype(int)
            if not alive.any():
                break
        val = (run * last).astype(int)
        for code, v in zip(pv.columns, val):
            out.setdefault(str(code), []).append(int(v))
    return out, dates[-1]


def build(price: pd.DataFrame, inst: pd.DataFrame, revenue: pd.DataFrame, div_events: pd.DataFrame,
          mops: list[dict], latest: str, names: dict | None = None) -> dict:
    names = names or {}
    p = price[price["date"].astype(str) <= latest]
    dates = sorted(p["date"].astype(str).unique())
    today = p[p["date"].astype(str) == latest].drop_duplicates("code", keep="last")
    prev_d = dates[-2] if len(dates) > 1 else None
    prev = p[p["date"].astype(str) == prev_d].drop_duplicates("code", keep="last").set_index("code")["close"] if prev_d else pd.Series(dtype=float)

    # 三大法人：最新一天的買賣超（張）＋連續天數（外資、投信、三大合計）
    streak, inst_date = _streaks(inst, latest, ["foreign_total", "trust", "inst_total"])
    inst_now = {}
    if inst_date:
        di = inst[inst["date"].astype(str) == inst_date].drop_duplicates("code", keep="last").set_index("code")
        for code, r in di.iterrows():
            inst_now[str(code)] = [round(float(r.get(c) or 0) / 1000) for c in ("foreign_total", "trust", "dealer", "inst_total")]

    # 月營收：每檔最新一期；年增、月增用同表的去年同月、上月自己算（表上的 yoy/mom 欄多半是空的）
    rev_out: dict[str, dict] = {}
    if revenue is not None and not revenue.empty:
        rv = revenue.dropna(subset=["revenue"]).copy()
        rv["ym"] = rv["ym"].astype(str)
        rv["code"] = rv["code"].astype(str)
        last_ym = rv.groupby("code")["ym"].transform("max")
        cur = rv[rv["ym"] == last_ym].drop_duplicates("code", keep="last").set_index("code")
        piv = rv.pivot_table(index="code", columns="ym", values="revenue", aggfunc="last")

        def shift(ym: str, months: int) -> str:
            y, m = int(ym[:4]), int(ym[5:7])
            t = y * 12 + (m - 1) + months
            return f"{t // 12:04d}-{t % 12 + 1:02d}"

        for code, r in cur.iterrows():
            ym = str(r["ym"]); v = float(r["revenue"])
            ly = piv.at[code, shift(ym, -12)] if shift(ym, -12) in piv.columns else np.nan
            pm = piv.at[code, shift(ym, -1)] if shift(ym, -1) in piv.columns else np.nan
            d = {"ym": ym, "rev": round(v / 1e8, 2), "ann": str(r.get("announce_date") or "")[:10] or None}
            d["yoy"] = round((v / ly - 1) * 100, 1) if pd.notna(ly) and ly > 0 else None
            d["mom"] = round((v / pm - 1) * 100, 1) if pd.notna(pm) and pm > 0 else None
            rev_out[str(code)] = d

    # 事件：除息（今天起 60 天內、現金股利）；法說會／財報公布（近 3 天到未來 45 天）
    ex_out: dict[str, dict] = {}
    if div_events is not None and not div_events.empty:
        de = div_events[(div_events["kind"] == "cash") & div_events["ex_date"].notna()].copy()
        de["ex_date"] = de["ex_date"].astype(str)
        de = de[(de["ex_date"] >= latest) & (de["ex_date"] <= (pd.Timestamp(latest) + pd.Timedelta(days=60)).strftime("%Y-%m-%d"))]
        for code, g in de.sort_values("ex_date").groupby("code"):
            r = g.iloc[0]
            ex_out[str(code)] = {"d": r["ex_date"], "a": round(float(r["amount"]), 4) if pd.notna(r["amount"]) else None}
    ev_out: dict[str, list] = {}
    lo = (pd.Timestamp(latest) - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    hi = (pd.Timestamp(latest) + pd.Timedelta(days=45)).strftime("%Y-%m-%d")
    for e in mops or []:
        if e.get("k") in EV_KIND and lo <= str(e.get("d")) <= hi:
            row = [EV_KIND[e["k"]], e["d"]]
            lst = ev_out.setdefault(str(e["code"]), [])
            if row not in lst:
                lst.append(row)

    stocks: dict[str, dict] = {}
    for _, r in today.iterrows():
        code = str(r["code"])
        if not CODE_OK.match(code):
            continue
        close = float(r["close"]) if pd.notna(r["close"]) else None
        if not close:
            continue
        s: dict = {"n": str(names.get(code) or r.get("name") or code), "c": close,
                   "v": round(float(r["volume"] or 0) / 1000)}
        if code in prev.index and pd.notna(prev[code]):
            s["pc"] = float(prev[code])
        if code in inst_now:
            s["i"] = inst_now[code]
            s["k"] = streak.get(code, [0, 0, 0])
        if code in rev_out:
            s["r"] = rev_out[code]
        if code in ex_out:
            s["x"] = ex_out[code]
        if code in ev_out:
            s["e"] = ev_out[code]
        stocks[code] = s
    return {"v": 1, "asof": latest, "prev": prev_d, "ia": inst_date,
            "unit": {"v": "張", "i": "張（外資、投信、自營商、三大合計）", "rev": "億元", "yoy": "%", "mom": "%"},
            "s": stocks}
