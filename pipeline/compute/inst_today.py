"""當日三大法人買賣超（全市場彙總＋各法人買超／賣超前 10）。

Andy 2026-10-20：「也需要在盤後提供當天即時的法人買賣超狀況」。
市場明細「法人連買賣」只回答「連續幾天」，沒有回答「今天誰買了多少」。

口徑（寫死在這裡，docs/inst_today.md 同步）：
  · 外資 ＝ inst_daily.foreign_total（外陸資＋外資自營商，與證交所「三大法人買賣超日報」的外資口徑一致）
    投信 ＝ trust、自營商 ＝ dealer（自行買賣＋避險）、合計 ＝ inst_total。
    實測 inst_total == foreign_total + trust + dealer（誤差 0）。
  · inst_daily 的單位是「股」。張數 ＝ 股 ÷ 1000；
    金額（元）＝ 股數 × 當天收盤價（資料湖沒有逐筆成交均價，這是估算；前端標「約」）。
  · 取哪一天：法人表比價量晚一輪、上市上櫃分開落地，直接取最新日會只剩幾十檔。
    取「涵蓋檔數 ≥ 近 10 日最多那天的 60%」裡最新的一天（與 build_payload 的 inst_list_date 同規則），
    並把日期寫進 payload，前端標「MM/DD」—— 不拿前一天冒充今天，而是講明是哪一天。
  · 排行以金額排序（張數會被低價股灌水）；沒有收盤價的代號不進金額與排行，但張數仍計入彙總張數。
"""
from __future__ import annotations

import pandas as pd

WHO_COLS = {"foreign": "foreign_total", "trust": "trust", "dealer": "dealer", "total": "inst_total"}
TOP_N = 10
COVER = 0.6


def pick_date(inst: pd.DataFrame) -> tuple[str | None, int, int]:
    """回傳（日期, 當日涵蓋檔數, 近 10 日最多檔數）。"""
    if inst is None or inst.empty:
        return None, 0, 0
    cnt = inst.groupby("date").size().sort_index().tail(10)
    ok = cnt[cnt >= cnt.max() * COVER]
    if ok.empty:
        return None, 0, 0
    d = ok.index[-1]
    return str(d), int(ok.iloc[-1]), int(cnt.max())


def payload(inst: pd.DataFrame, price: pd.DataFrame, names: dict) -> dict:
    d, n, nmax = pick_date(inst)
    if d is None:
        return {"date": None, "who": {}, "top": {}}
    day = inst[inst["date"].astype(str) == d].drop_duplicates("code", keep="last").copy()
    px = price[price["date"].astype(str) == d].drop_duplicates("code", keep="last").set_index("code")["close"]
    day["close"] = day["code"].map(px)
    who, top = {}, {}
    for k, col in WHO_COLS.items():
        sh = pd.to_numeric(day[col], errors="coerce").fillna(0.0)
        amt = sh * day["close"]
        has = day["close"].notna()
        who[k] = {
            "net_lots": int(round(sh.sum() / 1000)),
            "net_amt": round(float(amt[has].sum()), 0),
            "buy_amt": round(float(amt[has & (amt > 0)].sum()), 0),
            "sell_amt": round(float(amt[has & (amt < 0)].sum()), 0),
        }
        t = day.assign(sh_=sh, amt_=amt)
        t = t[t["close"].notna() & (t["sh_"] != 0)]

        def rows(df):
            return [{"code": str(r.code), "name": names.get(r.code) or str(r.code),
                     "lots": int(round(r.sh_ / 1000)), "amt": round(float(r.amt_), 0),
                     "close": float(r.close)} for r in df.itertuples()]
        top[k] = {"buy": rows(t[t["sh_"] > 0].nlargest(TOP_N, "amt_")),
                  "sell": rows(t[t["sh_"] < 0].nsmallest(TOP_N, "amt_"))}
    # 個股排行加族群篩選要用：全市場每檔「三大法人合計」（代號、張、金額億元）。
    # 只放合計、只放有收盤價且淨額非 0 的列，約 1,800 筆、幾十 KB。前端用 stocks.json 的 group 對族群。
    allr = day[day["close"].notna() & (day["close"] > 0)].copy()
    allr["sh_"] = pd.to_numeric(allr["inst_total"], errors="coerce").fillna(0.0)
    allr = allr[allr["sh_"] != 0]
    all_total = [[str(r.code), int(round(r.sh_ / 1000)), round(float(r.sh_ * r.close) / 1e8, 3)]
                 for r in allr.itertuples()]
    # 外資／投信各自的全市場逐檔（同樣 [代號, 張, 億元]）：前端「當日買賣超」切身分後仍可用族群篩選，不被前 10 名卡住
    all_by = {}
    for k in ("foreign", "trust"):
        a = day[day["close"].notna() & (day["close"] > 0)].copy()
        a["sh_"] = pd.to_numeric(a[WHO_COLS[k]], errors="coerce").fillna(0.0)
        a = a[a["sh_"] != 0]
        all_by[k] = [[str(r.code), int(round(r.sh_ / 1000)), round(float(r.sh_ * r.close) / 1e8, 3)] for r in a.itertuples()]
    all_by["total"] = all_total
    win = _windows(inst, price, d)
    return {"all": all_total, "all_by": all_by, "win": win, "date": d, "n": n, "n_max": nmax,
            "basis": "金額＝股數×當日收盤價（估算）；外資含外資自營商；自營商含自行買賣與避險",
            "who": who, "top": top}


WIN_DAYS = (5, 21, 63, 126)   # 個股元件的期間：近 5 日／1 月／3 月／6 月（交易日數，與日報期間鈕同一把尺）
WIN_TOP = 250                 # 每個身分、每個期間、買／賣各留前 250 檔（金額排序），控制 payload 大小


def _windows(inst: pd.DataFrame, price: pd.DataFrame, d: str) -> dict:
    """期間累計買賣超（逐檔）：近 N 個交易日每天「股數×當日收盤」加總。

    Andy 10-20：「都需要有時間切換」→ 個股元件跟日報共用期間鈕。每天用當天收盤估金額，與單日口徑一致。
    回傳 {"5": {"foreign": [[代號, 張, 億元], ...], "trust": ..., "total": ...}, ...}
    """
    try:
        dates = sorted({str(x) for x in inst["date"].astype(str).unique() if str(x) <= d})
        out: dict = {}
        px = price[["date", "code", "close"]].copy()
        px["date"] = px["date"].astype(str)
        for n in WIN_DAYS:
            ds = set(dates[-n:])
            sub = inst[inst["date"].astype(str).isin(ds)].copy()
            sub["date"] = sub["date"].astype(str)
            sub = sub.merge(px, on=["date", "code"], how="left")
            sub = sub[sub["close"].notna() & (sub["close"] > 0)]
            out[str(n)] = {}
            for k, col in (("foreign", "foreign_total"), ("trust", "trust"), ("total", "inst_total")):
                sh = pd.to_numeric(sub[col], errors="coerce").fillna(0.0)
                g = pd.DataFrame({"code": sub["code"].astype(str), "sh": sh, "amt": sh * sub["close"]}).groupby("code").sum()
                g = g[g["sh"] != 0]
                pick = pd.concat([g.nlargest(WIN_TOP, "amt"), g.nsmallest(WIN_TOP, "amt")]).loc[lambda x: ~x.index.duplicated()]
                out[str(n)][k] = [[c, int(round(r.sh / 1000)), round(float(r.amt) / 1e8, 3)] for c, r in pick.iterrows()]
        return out
    except Exception:
        return {}
