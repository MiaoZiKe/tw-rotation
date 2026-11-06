"""一次性探測：10-28、10-29 盤中 5 分快照缺口，有哪些合法來源能重建。只在 probe/* 分支跑，不進 main。"""
import json, os, glob, sys
import pandas as pd, requests

TOK = os.environ.get("FINMIND_TOKEN", "")
DAYS = ["2026-10-28", "2026-10-29"]
OUT = {}
def p(k, v): OUT[k] = v; print("##", k, json.dumps(v, ensure_ascii=False, default=str)[:1500], flush=True)

# 1. FinMind 等級與資料集
try:
    r = requests.get("https://api.web.finmindtrade.com/v2/user_info", headers={"Authorization": f"Bearer {TOK}"}, timeout=30)
    p("finmind_user_info", {"status": r.status_code, "body": r.text[:300]})
except Exception as e: p("finmind_user_info", str(e))
for ds, did in [("TaiwanStockKBar", "2330"), ("TaiwanStockKBar", "6488"), ("TaiwanStockPriceTick", "2330"), ("TaiwanStockPriceTick", None)]:
    for d in DAYS[:1] + ["2026-11-05"]:
        prm = {"dataset": ds, "start_date": d, "end_date": d, "token": TOK}
        if did: prm["data_id"] = did
        try:
            r = requests.get("https://api.finmindtrade.com/api/v4/data", params=prm, timeout=60)
            j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            data = j.get("data") or []
            p(f"finmind:{ds}:{did}:{d}", {"http": r.status_code, "msg": j.get("msg"), "n": len(data), "head": data[:2], "cols": list(data[0].keys()) if data else None})
        except Exception as e: p(f"finmind:{ds}:{did}:{d}", str(e)[:200])

# 2. Yahoo 5m / 1m
import yfinance as yf
for sym in ["2330.TW", "6488.TWO"]:
    for itv, st, en in [("5m", "2026-10-28", "2026-10-31"), ("1m", "2026-10-28", "2026-10-31"), ("5m", "2026-11-05", "2026-11-06")]:
        try:
            df = yf.download(sym, interval=itv, start=st, end=en, auto_adjust=False, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            idx = pd.DatetimeIndex(df.index)
            idx = idx.tz_convert("Asia/Taipei") if idx.tz is not None else idx
            byday = pd.Series(idx.strftime("%Y-%m-%d")).value_counts().sort_index().to_dict()
            p(f"yahoo:{sym}:{itv}:{st}", {"rows": len(df), "byday": byday, "first": str(idx.min()), "last": str(idx.max()),
                "vol_sum_by_day": df.groupby(idx.strftime("%Y-%m-%d"))["Volume"].sum().to_dict() if len(df) else None})
        except Exception as e: p(f"yahoo:{sym}:{itv}:{st}", str(e)[:300])

# 3. openapi 有沒有盤中端點
try:
    r = requests.get("https://openapi.twse.com.tw/v1/swagger.json", timeout=60)
    paths = list(r.json().get("paths", {}).keys()) if r.ok else []
    hit = [x for x in paths if any(k in x.lower() for k in ("intra", "tick", "minute", "realtime", "mi_5", "5min", "fmsrfk"))]
    p("twse_openapi_paths", {"http": r.status_code, "n": len(paths), "intraday_like": hit})
except Exception as e: p("twse_openapi_paths", str(e)[:200])
try:
    r = requests.get("https://www.tpex.org.tw/openapi/swagger.json", timeout=60)
    paths = list(r.json().get("paths", {}).keys()) if r.ok else []
    hit = [x for x in paths if any(k in x.lower() for k in ("intra", "tick", "minute", "realtime", "5min"))]
    p("tpex_openapi_paths", {"http": r.status_code, "n": len(paths), "intraday_like": hit})
except Exception as e: p("tpex_openapi_paths", str(e)[:200])

# 4. 校準：拿 Yahoo 5m 對湖裡已有的 tape（10-30 ~ 11-05），看口徑對不對得上
try:
    tp = pd.concat([pd.read_parquet(f) for f in glob.glob("data/tape_5m/*/*.parquet")])
    tp["d"] = tp.ts.str[:10]
    codes = ["2330", "2317", "2454", "3037", "6488", "3008"]
    mk = {"6488": "TWO"}
    res = []
    for c in codes:
        sym = f"{c}.{mk.get(c, 'TW')}"
        df = yf.download(sym, interval="5m", start="2026-11-02", end="2026-11-06", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        idx = pd.DatetimeIndex(df.index).tz_convert("Asia/Taipei")
        df = df.copy(); df["ts0"] = idx
        df["d"] = idx.strftime("%Y-%m-%d")
        df["cum"] = df.groupby("d")["Volume"].cumsum() / 1000.0
        for d, g in df.groupby("d"):
            t = tp[(tp.code == c) & (tp.d == d)].copy()
            if t.empty: continue
            t["hm"] = t.ts.str[11:16]
            for shift in (0, 5):   # Yahoo 棒起點 + shift 分 = tape 格
                g2 = g.copy(); g2["hm"] = (g2["ts0"] + pd.Timedelta(minutes=shift)).dt.strftime("%H:%M")
                m = t.merge(g2[["hm", "Close", "cum"]], on="hm")
                if m.empty: continue
                res.append({"code": c, "d": d, "shift": shift, "n": len(m),
                            "px_exact": float(((m.price - m.Close).abs() < 0.006).mean()),
                            "lots_ratio_med": float((m.cum / m.cum_lots.replace(0, float("nan"))).median()),
                            "last_tape_lots": float(t.cum_lots.max()), "last_yahoo_lots": float(g.cum.iloc[-1])})
    p("calibrate_yahoo_vs_tape", res)
except Exception as e:
    import traceback; p("calibrate_yahoo_vs_tape", traceback.format_exc()[-600:])

os.makedirs("probe_out", exist_ok=True)
json.dump(OUT, open("probe_out/tape_gap_probe.json", "w"), ensure_ascii=False, default=str, indent=1)
