"""風險警示牌（P-1107-02）：注意股／處置股 → site/data/risk_flags.json。

輸入是資料湖 risk_notice／risk_punish（sources/risk.py，交易所公告原文）＋價量日（交易日曆）＋族群成分。
只做「數」與「整理」，不推算：
  · 近 10 個交易日被列注意幾次 ＝ 湖裡在那 10 個交易日內、這一檔出現在注意公告的天數（同一天上市＋上櫃算一次）。
    湖是 2026-11-09 才開始存（端點只給最新一期），所以 since（湖裡第一天）晚於視窗起點時，前端要寫明「本站自 X 起記錄」。
  · 處置期間、撮合方式、預收款券全是公告原文欄位；不判斷「會不會達處置標準」。
  · 「處置中／即將處置」由前端拿讀者當下的台北日期比 start／end（JSON 隔週末也不會把已結束的當成處置中）；
    這裡只把「訖日早於參考日」的舊處置濾掉。
"""
from __future__ import annotations

import pandas as pd

WINDOW = 10      # 近 N 個交易日


def _s(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def build_json(notice: pd.DataFrame | None, punish: pd.DataFrame | None, trade_dates: list[str],
               membership: pd.DataFrame | None, names: dict | None = None) -> dict:
    notice = notice if notice is not None else pd.DataFrame()
    punish = punish if punish is not None else pd.DataFrame()
    names = names or {}
    nd = sorted(set(notice["date"].dropna().astype(str))) if not notice.empty else []
    pdts = sorted(set(punish["date"].dropna().astype(str))) if not punish.empty else []
    td = sorted(set(str(x) for x in (trade_dates or [])))
    # 參考日：交易日曆、注意、處置公告三者最新的一天（全是回應裡的日期，不是執行當天）
    ref = max([x for x in (td[-1:] + nd[-1:] + pdts[-1:]) if x] or [None]) if (td or nd or pdts) else None
    # 視窗：參考日以前（含）最近 10 個交易日。交易日曆沒有的公告日（例如曆還沒進來的今天）也算一天。
    days = sorted(set([d for d in td if ref and d <= ref] + [d for d in nd if ref and d <= ref]))
    window = days[-WINDOW:]
    stocks: dict[str, dict] = {}

    def ent(code, name=None, market=None):
        e = stocks.setdefault(str(code), {"name": None, "market": None})
        if name and not e["name"]:
            e["name"] = str(name)
        if market and not e["market"]:
            e["market"] = str(market)
        return e

    if not notice.empty and window:
        w = notice[notice["date"].astype(str).isin(window)].copy()
        w = w.sort_values(["date", "market"])
        for code, g in w.groupby("code", sort=False):
            last = g.iloc[-1]
            dates = sorted(set(g["date"].astype(str)))
            e = ent(code, _s(last.get("name")) or names.get(str(code)), _s(last.get("market")))
            e["notice"] = {"last": dates[-1], "reason": _s(last.get("reason")), "n10": len(dates), "dates": dates}

    if not punish.empty and ref:
        p = punish.copy()
        p = p[p["end"].notna() & (p["end"].astype(str) >= ref)]
        p = p.sort_values(["code", "start", "date"])
        for code, g in p.groupby("code", sort=False):
            rows = []
            seen = set()
            for _, r in g.iterrows():
                k = (str(_s(r.get("start"))), str(_s(r.get("end"))))
                if k in seen:            # 同一段處置被重複公告（上市＋上櫃都列、或隔天又列一次）只留一筆
                    continue
                seen.add(k)
                rows.append({"date": str(r["date"]), "start": _s(r.get("start")), "end": _s(r.get("end")),
                             "reason": _s(r.get("reason")), "measure": _s(r.get("measure")),
                             "match": _s(r.get("match")), "prepay": bool(_s(r.get("prepay")) or False)})
            e = ent(code, _s(g.iloc[-1].get("name")) or names.get(str(code)), _s(g.iloc[-1].get("market")))
            e["punish"] = rows

    groups: dict[str, list[str]] = {}
    if membership is not None and not membership.empty and stocks:
        m = membership[membership["code"].astype(str).isin(stocks.keys())]
        for gid, g in m.groupby("group_id"):
            groups[str(gid)] = sorted(set(g["code"].astype(str)))

    return {
        "date": ref,
        "notice_date": nd[-1] if nd else None,
        "since": nd[0] if nd else None,
        "window": window,
        "markets": ["TWSE", "TPEX"],
        "stocks": stocks,
        "groups": groups,
    }
