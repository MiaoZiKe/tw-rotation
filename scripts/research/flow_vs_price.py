"""研究：資金指標（成交值占比／輪動）與族群走勢的吻合度，以及盤中領先訊號（2026-10-30）。

只讀資料湖（intraday_60m、price_daily、company_info），不寫 data/。
用法：python scripts/research/flow_vs_price.py [prep|step1|step2|all] [--out DIR]
中間檔放 --out（預設 research_cache/，已不進版控）。

口徑盡量與 pipeline/compute/flow.py 同一把尺：
  · 族群成員與 1/n 拆分：直接呼叫 flow._attach_groups（含產業別補位的 ind_ 族群）
  · 族群漲跌：成交值加權（盤中用「到該根為止的累計成交值」當權重，不偷看後面）
  · 占比：族群成交值 ÷ 全部族群合計
  · 前收：close − change（交易所參考價，已含除權息調整），與 flow.py 相同
60 分 K 沒有成交值，用 volume × (o+h+l+c)/4 估；prep 會對照日線成交值檢查誤差。
"""
from __future__ import annotations
import sys, glob, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.util import store                      # noqa: E402
from pipeline.compute import flow, rrg as rrgmod      # noqa: E402

NB = 5  # 60 分 K 一天 5 根：09:00 10:00 11:00 12:00 13:00（13:00 這根只到 13:30）


def outdir(argv):
    if "--out" in argv:
        return Path(argv[argv.index("--out") + 1])
    return ROOT / "research_cache"


# ───────────────────────── 準備資料 ─────────────────────────
def prep(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    price = store.read("price_daily")
    company = store.read("company_info")
    price["date"] = price["date"].astype(str)
    last = price["date"].max()
    # 代號→族群對照（靜態，取最後一天算一次即可）
    att = flow._attach_groups(price[price["date"] == last].copy(), company)
    cmap = att[["code", "group_id", "group_name", "weight"]].drop_duplicates(["code", "group_id"])
    cmap.to_parquet(out / "cmap.parquet")
    codes = set(cmap["code"])

    # 日線：前收、日報酬
    p = price[price["code"].isin(codes) & (price["date"] >= "2023-09-01")].copy()
    p["ref"] = p["close"] - p["change"].fillna(0)
    p["dret"] = np.where(p["ref"] > 0, p["change"] / p["ref"], np.nan)
    p[["date", "code", "open", "close", "ref", "dret", "turnover"]].to_parquet(out / "daily.parquet")

    # 盤中 60 分 K
    fs = sorted(glob.glob(str(ROOT / "data/intraday_60m/**/*.parquet"), recursive=True))
    d = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    d = d[d["code"].isin(codes)].copy()
    d["date"] = d["ts"].str[:10]
    d["k"] = ((d["ts"].str[11:13].astype(int)) - 9).astype("int8")
    d = d[(d["k"] >= 0) & (d["k"] < NB)]
    d["tv"] = d["volume"] * (d["open"] + d["high"] + d["low"] + d["close"]) / 4
    d = d.drop_duplicates(["date", "code", "k"])
    d = d.merge(p[["date", "code", "ref"]], on=["date", "code"], how="inner")
    d = d[d["ref"] > 0]
    d[["date", "code", "k", "open", "close", "tv", "ref"]].to_parquet(out / "bars.parquet")

    # 檢查：60 分 K 估的日成交值 vs 日線成交值
    chk = d.groupby(["date", "code"])["tv"].sum().rename("tv60").reset_index().merge(
        p[["date", "code", "turnover"]], on=["date", "code"])
    chk = chk[chk["turnover"] > 0]
    ratio = (chk["tv60"] / chk["turnover"])
    day = chk.groupby("date")[["tv60", "turnover"]].sum()
    info = {"n_days": int(d["date"].nunique()), "first": d["date"].min(), "last": d["date"].max(),
            "stock_day_ratio_median": float(ratio.median()), "stock_day_ratio_p10": float(ratio.quantile(.1)),
            "stock_day_ratio_p90": float(ratio.quantile(.9)),
            "market_day_ratio_median": float((day["tv60"] / day["turnover"]).median()),
            "market_day_ratio_min": float((day["tv60"] / day["turnover"]).min())}
    (out / "prep_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    print(info)


# ───────────────────────── 建盤中族群序列 ─────────────────────────
def build_group_bars(out: Path):
    """回傳 gb：每 (date, group, k) 一列，含累計成交值、占比、走勢、擴散、後續報酬。"""
    f = out / "gb.parquet"
    if f.exists():
        return pd.read_parquet(f), pd.read_parquet(out / "mb.parquet")
    bars = pd.read_parquet(out / "bars.parquet")
    daily = pd.read_parquet(out / "daily.parquet")
    cmap = pd.read_parquet(out / "cmap.parquet")
    # ★ 資料湖的 60 分 K：09:00 這根（開盤到 10:00）幾乎沒有成交量（只有 29% 的列有量，
    #   2330 整年都是 0），價格有效。所以「成交值」只用 k>=1（10:00 起）；k=0 的量一律歸零，
    #   占比才不會因為「有些股票有、有些沒有」而失真。這是本研究最大的資料限制。
    bars.loc[bars["k"] == 0, "tv"] = 0.0
    # 髒資料：個別代號（代號重用、減資）整日價格對不上前收，|相對前收|>11.5% 的列整列丟棄（漲跌停上限 10%）
    bars = bars[(bars["close"] / bars["ref"] - 1).abs() <= 0.115]
    bars = bars.sort_values(["date", "code", "k"])
    g = bars.groupby(["date", "code"])
    bars["cumtv"] = g["tv"].cumsum()
    bars["r"] = bars["close"] / bars["ref"] - 1                      # 到該根收盤為止，相對前收
    last_close = g["close"].transform("last")
    # 之後報酬：以「下一根開盤」進場，持有到當天最後一根收盤（訊號在第 k 根收完才知道，保守不用 k 根收盤價）
    nxt_open = g["open"].shift(-1)
    bars["rem"] = (last_close / nxt_open - 1).clip(-0.12, 0.12)
    # 隔日收盤：(當天剩餘報酬) × (隔日日報酬)，隔日日報酬用交易所參考價口徑
    d2 = daily[["date", "code", "dret"]].sort_values(["code", "date"]).copy()
    d2["dret_next"] = d2.groupby("code")["dret"].shift(-1)
    bars = bars.merge(d2[["date", "code", "dret_next"]], on=["date", "code"], how="left")
    bars["rem_nd"] = (1 + bars["rem"]) * (1 + bars["dret_next"]) - 1
    # 走勢／擴散的權重改用「前一個交易日該股全日成交值」（開盤前就已知，不偷看今天；
    # 也讓 09:00 那根沒有量時，漲跌仍算得出來）。累計占比仍用當天累計成交值。
    dtv = bars.groupby(["date", "code"])["tv"].sum().rename("dtv").reset_index().sort_values(["code", "date"])
    dtv["pw"] = dtv.groupby("code")["dtv"].shift(1)
    bars = bars.merge(dtv[["date", "code", "pw"]], on=["date", "code"], how="left")
    bars["pw"] = bars["pw"].fillna(0)
    bars["up"] = (bars["r"] > 0) & (bars["pw"] > 0)

    def agg(df, keys):
        w = df["w"]
        x = pd.DataFrame({
            "cumtv": w * df["cumtv"], "tv": w * df["tv"], "pw": w * df["pw"],
            "rw": w * df["pw"] * df["r"], "remw": w * df["pw"] * df["rem"].fillna(0),
            "remw_ok": w * df["pw"] * df["rem"].notna(),
            "ndw": w * df["pw"] * df["rem_nd"].fillna(0), "ndw_ok": w * df["pw"] * df["rem_nd"].notna(),
            "up": w * df["up"], "n": w * (df["pw"] > 0)})
        for kcol in keys:
            x[kcol] = df[kcol].values
        s = x.groupby(keys).sum()
        out_ = pd.DataFrame({
            "cumtv": s["cumtv"], "tv": s["tv"],
            "ret": s["rw"] / s["pw"].where(s["pw"] > 0),
            "rem": s["remw"] / s["remw_ok"].where(s["remw_ok"] > 0),
            "rem_nd": s["ndw"] / s["ndw_ok"].where(s["ndw_ok"] > 0),
            "breadth": s["up"] / s["n"].where(s["n"] > 0), "nmem": s["n"]})
        return out_.reset_index()

    b = bars.merge(cmap[["code", "group_id", "weight"]].rename(columns={"weight": "w"}), on="code")
    gb = agg(b, ["date", "group_id", "k"])
    m = bars.assign(w=1.0)
    mb = agg(m, ["date", "k"]).rename(columns={c: "m_" + c for c in ["cumtv", "tv", "ret", "rem", "rem_nd", "breadth", "nmem"]})
    # 全部族群合計（占比的分母，與 flow.py 一致：1/n 拆分後的總和）
    tot = gb.groupby(["date", "k"])[["cumtv", "tv"]].sum().rename(columns={"cumtv": "tot_cumtv", "tv": "tot_tv"}).reset_index()
    gb = gb.merge(tot, on=["date", "k"]).merge(mb[["date", "k", "m_ret", "m_rem", "m_rem_nd"]], on=["date", "k"])
    gb["share"] = gb["cumtv"] / gb["tot_cumtv"] * 100               # 累計占比 %
    gb["bar_share"] = gb["tv"] / gb["tot_tv"] * 100                 # 單根占比 %
    gb["xret"] = gb["ret"] - gb["m_ret"]                            # 相對大盤的走勢
    gb["xrem"] = gb["rem"] - gb["m_rem"]
    gb["xrem_nd"] = gb["rem_nd"] - gb["m_rem_nd"]
    gb.to_parquet(f); mb.to_parquet(out / "mb.parquet")
    return gb, mb


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "all"
    o = outdir(a)
    if cmd in ("prep", "all"):
        prep(o)
    if cmd in ("build", "all"):
        gb, mb = build_group_bars(o); print(gb.shape, gb.date.nunique(), gb.group_id.nunique())


# ───────────────────────── 日線層：與網站同一份算法 ─────────────────────────
def build_daily(out: Path):
    """用網站的 flow.group_daily / rotation / rrg_axes 重算每日每族群：占比、漲跌、rot(pp)、RRG 象限。"""
    f = out / "gd.parquet"
    if f.exists():
        return pd.read_parquet(f)
    price = store.read("price_daily"); company = store.read("company_info")
    price["date"] = price["date"].astype(str)
    price = price[price["date"] >= "2023-03-01"]
    gh = flow.group_daily(price, company)
    g = gh.sort_values("date").copy()
    g["share_s"] = g.groupby("group_id")["turnover_share"].transform(lambda s: s.rolling(5, min_periods=2).mean())
    g["share_l"] = g.groupby("group_id")["turnover_share"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    g["rot"] = g["share_s"] - g["share_l"]               # 資金流向熱力圖／rotation_radar 的 pp
    g["dshare"] = g["turnover_share"] - g.groupby("group_id")["turnover_share"].shift(1)   # 占比相對前一日
    g["factor"] = 1 + g["chg_pct"].fillna(0) / 100
    g["gi"] = g.groupby("group_id")["factor"].cumprod()
    bench = rrgmod.market_index(price, days=1000); bench.index = bench.index.astype(str)
    g["bi"] = g["date"].map(bench)
    g = rrgmod.rrg_axes(g.dropna(subset=["bi"]), "group_id")
    g["quad"] = [rrgmod.quadrant_of(x, y) if pd.notna(x) and pd.notna(y) else None
                 for x, y in zip(g["rs_ratio"], g["rs_mom"])]
    # 前一天收盤時的象限（「今天出現在盤上的位置」是用收盤算的，盤中看到的是昨天的）
    g["quad_prev"] = g.groupby("group_id")["quad"].shift(1)
    g["mkt_chg"] = g["date"].map(bench.pct_change() * 100)
    g.to_parquet(f)
    return g


# ───────────────────────── 共用工具 ─────────────────────────
COST = 0.0047   # 一趟來回成本：手續費 0.1425%×0.6 折×2 ＋ 證交稅 0.3% ≈ 0.47%（沒算滑價；族群籃子是概念，實際得買成分股）
TRAIN_END = "2025-03-31"     # 前 ~19 個月＝訓練（選訊號），之後＝樣本外（只報一次）
KL = {0: "10:00", 1: "11:00", 2: "12:00", 3: "13:00", 4: "13:30"}   # k 根收盤時間（bar 起點標籤＋1 小時）


def universe(gb):
    """只看題材族群（不含 ind_ 補位桶），成員 ≥3 檔、平均占比 ≥0.2%（比照 rrg 的 min_share 精神，太小是雜訊）。"""
    e = gb[(gb["k"] == 4)]
    ok = e.groupby("group_id").agg(nm=("nmem", "median"), sh=("share", "mean"))
    ok = ok[(ok["nm"] >= 3) & (ok["sh"] >= 0.2)].index
    return [g for g in ok if not str(g).startswith("ind_")]


def wide(gb, groups):
    d = gb[gb["group_id"].isin(groups)].copy()
    d = d.sort_values(["group_id", "k", "date"])
    # 同一根、同一族群、過去 20 個交易日的平均（不含今天）當基準：吃掉「前半小時沒量」「各族群日內量能型態不同」的常數偏差
    for c in ("share", "bar_share", "cumtv"):
        d[c + "_b20"] = d.groupby(["group_id", "k"])[c].transform(lambda s: s.shift(1).rolling(20, min_periods=10).mean())
    d["surge"] = d["share"] - d["share_b20"]                  # 累計占比比平常多幾 pp
    d["bar_surge"] = d["bar_share"] - d["bar_share_b20"]      # 單根占比比平常多幾 pp
    d["pace"] = np.log(d["cumtv"] / d["cumtv_b20"])           # 量能放大倍數（對數）；含大盤整體放量
    return d


def newey_t(x, lag=5):
    x = pd.Series(x).dropna().values
    n = len(x)
    if n < 30:
        return np.nan, np.nan
    mu = x.mean(); e = x - mu
    v = e @ e / n
    for l in range(1, lag + 1):
        v += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    se = np.sqrt(v / n)
    return mu, mu / se


def daily_ic(df, feat, tgt):
    """逐日橫斷面 Spearman 相關，回傳每日 IC 序列。"""
    x = df[["date", feat, tgt]].dropna()
    r = x.groupby("date")[[feat, tgt]].rank()
    r["date"] = x["date"].values
    def c(g):
        return np.nan if len(g) < 15 else np.corrcoef(g[feat], g[tgt])[0, 1]
    return r.groupby("date").apply(c)


def block_boot(x, n=2000, block=5, seed=7):
    x = np.asarray(pd.Series(x).dropna()); N = len(x)
    if N < 30:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(N / block)); m = np.empty(n)
    for i in range(n):
        st = rng.integers(0, N - block + 1, nb)
        m[i] = np.concatenate([x[s:s + block] for s in st])[:N].mean()
    return tuple(np.percentile(m, [2.5, 97.5]))


# ───────────────────────── 第一步：吻合度 ─────────────────────────
def agree_rate(a, b):
    """兩個序列『同號』比例（任一為 0 的剔除），附 95% 二項信賴區間。"""
    a = np.sign(np.asarray(a, float)); b = np.sign(np.asarray(b, float))
    m = (a != 0) & (b != 0) & ~np.isnan(a) & ~np.isnan(b)
    n = int(m.sum()); p = float((a[m] == b[m]).mean()) if n else np.nan
    se = np.sqrt(p * (1 - p) / n) if n else np.nan
    return {"n": n, "agree": p, "lo": p - 1.96 * se, "hi": p + 1.96 * se}


def step1(out: Path):
    gb, mb = build_group_bars(out); gd = build_daily(out)
    U = universe(gb); w = wide(gb, U)
    R = {"n_groups": len(U)}
    # ── A. 日線層（網站同一把尺：flow.group_daily／rotation_radar 的 5日-20日 pp／rrg 象限）
    g = gd[gd["group_id"].isin(U) & (gd["date"] >= "2023-09-19")].copy()
    g["xchg"] = g["chg_pct"] - g["mkt_chg"]                       # 相對大盤（成交值加權）的漲跌 %
    g["xchg_cs"] = g["chg_pct"] - g.groupby("date")["chg_pct"].transform("mean")   # 相對「當天全族群平均」
    g = g.dropna(subset=["xchg", "rot", "dshare"])
    A = {}
    for nm, col in (("占比日變化 dshare", "dshare"), ("輪動 rot(5日-20日,pp)", "rot")):
        ic = daily_ic(g, col, "xchg_cs")
        mu, t = newey_t(ic)
        A[nm] = {"mean_ic": float(mu), "t": float(t), "n_days": int(ic.notna().sum()),
                 "agree": agree_rate(g[col] - g.groupby("date")[col].transform("mean"), g["xchg_cs"])}
    # 機械性檢查：占比變化是跟「方向」有關，還是只跟「波動大小」有關
    A["dshare~|xchg|"] = float(g[["dshare"]].assign(a=g["xchg_cs"].abs()).corr(method="spearman").iloc[0, 1])
    A["dshare~xchg"] = float(g[["dshare", "xchg_cs"]].corr(method="spearman").iloc[0, 1])
    # 分盤勢
    # 盤勢用「前一日成交值加權全市場漲跌」(mb k=4)，不用網站 rrg.market_index：
    # 後者用『當天』成交值加權，會偏向當天爆量漲停的股票，長期每天虛增約 0.7%（對照加權指數見研究報告）
    pwm = mb[mb["k"] == 4].set_index("date")["m_ret"] * 100
    g["mkt_pw"] = g["date"].map(pwm)
    g["reg"] = pd.cut(g["mkt_pw"], [-99, -1.5, -0.3, 0.3, 1.5, 99], labels=["大跌<-1.5%", "小跌", "平盤", "小漲", "大漲>1.5%"])
    A["by_regime"] = {str(k): {"days": int(v["date"].nunique()),
                               **agree_rate(v["dshare"] - v.groupby("date")["dshare"].transform("mean"), v["xchg_cs"]),
                               "mean_ic": float(daily_ic(v, "dshare", "xchg_cs").mean())}
                      for k, v in g.groupby("reg", observed=True)}
    # 分族群大小（三等分，用全期平均占比）
    sz = g.groupby("group_id")["turnover_share"].mean()
    g["size"] = g["group_id"].map(pd.qcut(sz, 3, labels=["小", "中", "大"]))
    A["by_size"] = {str(k): {**agree_rate(v["dshare"] - v.groupby("date")["dshare"].transform("mean"), v["xchg_cs"]),
                             "mean_ic": float(daily_ic(v, "dshare", "xchg_cs").mean())} for k, v in g.groupby("size", observed=True)}
    # 象限：當天收盤象限（含當天走勢，本身不獨立）與前一天象限（盤前就看得到）
    def quad_tab(col):
        t = g.dropna(subset=[col]).groupby(col).agg(n=("xchg_cs", "size"), mean_x=("xchg_cs", "mean"),
                                                   pos=("xchg_cs", lambda s: (s > 0).mean()))
        return t.round(4).to_dict("index")
    A["quad_same_day"] = quad_tab("quad"); A["quad_prev_day"] = quad_tab("quad_prev")
    # 依 rot 五分位 → 同日／次日超額（次日以前一天 rot 排序，等於『隔夜看雷達，隔天會不會續強』）
    g = g.sort_values(["group_id", "date"])
    g["rot_prev"] = g.groupby("group_id")["rot"].shift(1)
    g["rotq_prev"] = g.groupby("date")["rot_prev"].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop"))
    A["rot_prev_quintile_nextday"] = g.dropna(subset=["rotq_prev"]).groupby("rotq_prev")["xchg_cs"].agg(["size", "mean"]).round(4).to_dict("index")
    ic_prev = daily_ic(g, "rot_prev", "xchg_cs"); mu, t = newey_t(ic_prev)
    A["rot_prev→今日超額 IC"] = {"mean_ic": float(mu), "t": float(t), "ci": [float(x) for x in block_boot(ic_prev)]}
    # 占比變化按當天超額漲跌分箱（看跌的族群占比是否也上升）
    g["xb"] = pd.cut(g["xchg_cs"], [-99, -3, -1, -0.3, 0.3, 1, 3, 99])
    A["dshare_by_xchg_bin"] = g.groupby("xb", observed=True).agg(n=("dshare", "size"), dshare=("dshare", "mean")).round(4).reset_index().astype({"xb": str}).to_dict("records")
    R["daily"] = A

    # ── B. 盤中層：每一小時，占比『比平常多』與該小時相對大盤超額漲跌是否同向
    w = w.sort_values(["group_id", "date", "k"])
    w["xbar"] = w.groupby(["group_id", "date"])["xret"].diff()
    w.loc[w["k"] == 0, "xbar"] = w.loc[w["k"] == 0, "xret"]
    B = {}
    for k in (1, 2, 3, 4):
        s = w[w["k"] == k].dropna(subset=["bar_surge", "xbar"]).copy()
        s["bs_cs"] = s["bar_surge"] - s.groupby("date")["bar_surge"].transform("mean")
        s["xb_cs"] = s["xbar"] - s.groupby("date")["xbar"].transform("mean")
        ic = daily_ic(s, "bs_cs", "xb_cs"); mu, t = newey_t(ic)
        B[f"{KL[k-1]}-{KL[k]}"] = {"mean_ic": float(mu), "t": float(t), "n_days": int(ic.notna().sum()),
                                   "agree": agree_rate(s["bs_cs"], s["xb_cs"]),
                                   "abs_corr": float(s[["bs_cs"]].assign(a=s["xb_cs"].abs()).corr(method="spearman").iloc[0, 1])}
    R["intraday_hourly"] = B
    # 終盤累計：到 13:30 的累計占比比平常多 vs 全日超額漲跌
    s = w[w["k"] == 4].dropna(subset=["surge", "xret"]).copy()
    s["xret_cs"] = s["xret"] - s.groupby("date")["xret"].transform("mean")
    ic = daily_ic(s, "surge", "xret_cs"); mu, t = newey_t(ic)
    R["eod_surge_vs_xret"] = {"mean_ic": float(mu), "t": float(t), "agree": agree_rate(s["surge"] - s.groupby("date")["surge"].transform("mean"), s["xret_cs"])}
    (out / "step1.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    return R, w, g


if __name__ == "__main__" and (len(sys.argv) > 1 and sys.argv[1] in ("step1", "all")):
    R, _, _ = step1(outdir(sys.argv[1:]))
    print(json.dumps(R, ensure_ascii=False, indent=1, default=str)[:6000])


# ───────────────────────── 第二步：盤中領先訊號（walk-forward） ─────────────────────────
SIGS = {"S1 占比比平常多(surge)": "surge", "S2 族群內上漲家數比(breadth)": "breadth",
        "S3 相對大盤已漲幅(xret)": "xret", "S4 資金＋價格同向(兩者排名和)": "combo"}
TGTS = {"同日剩餘(xrem)": "xrem", "隔日收盤(xrem_nd)": "xrem_nd"}
TIMES = {1: "11:00", 2: "12:00"}


def holm(pvals):
    p = np.asarray(pvals, float); order = np.argsort(p); m = len(p); adj = np.empty(m); run = 0
    for i, j in enumerate(order):
        run = max(run, (m - i) * p[j]); adj[j] = min(1, run)
    return adj


def step2(out: Path, w=None):
    from scipy import stats
    gb, mb = build_group_bars(out)
    if w is None:
        w = wide(gb, universe(gb))
    rows = []
    allbk = {}
    for T, tl in TIMES.items():
        s = w[w["k"] == T].copy()
        s["combo"] = s.groupby("date")["surge"].rank(pct=True) + s.groupby("date")["xret"].rank(pct=True)
        for sn, col in SIGS.items():
            for tn, tc in TGTS.items():
                x = s.dropna(subset=[col, tc]).copy()
                if len(x) < 1000:
                    continue
                ic = daily_ic(x, col, tc)
                tr, te = ic[ic.index <= TRAIN_END], ic[ic.index > TRAIN_END]
                mtr, ttr = newey_t(tr); mte, tte = newey_t(te)
                # top5 籃子（等權）相對『當天全族群平均』的超額；一趟來回成本 0.47% 另外扣
                x["rk"] = x.groupby("date")[col].rank(ascending=False, method="first")
                cs = x[tc] - x.groupby("date")[tc].transform("mean")
                top = cs[x["rk"] <= 5].groupby(x.loc[x["rk"] <= 5, "date"]).mean()
                allbk[(T, col, tc)] = top
                trb, teb = top[top.index <= TRAIN_END], top[top.index > TRAIN_END]
                lo, hi = block_boot(teb)
                # 置換檢定（樣本外）：每天把特徵排名打散 2000 次，看真實籃子平均落在哪
                xt = x[x["date"] > TRAIN_END]
                rng = np.random.default_rng(11)
                groups_by_day = [g_[tc].values - g_[tc].mean() for _, g_ in xt.groupby("date")]
                feat_by_day = [g_[col].values for _, g_ in xt.groupby("date")]
                real = np.mean([gv[np.argsort(-fv)[:5]].mean() for gv, fv in zip(groups_by_day, feat_by_day)])
                null = np.array([np.mean([gv[rng.permutation(len(gv))[:5]].mean() for gv in groups_by_day]) for _ in range(300)])
                pperm = float((np.sum(null >= real) + 1) / (len(null) + 1))
                rows.append({"time": tl, "signal": sn, "target": tn, "col": col, "tc": tc,
                             "train_ic": mtr, "train_t": ttr, "train_days": int(tr.notna().sum()),
                             "test_ic": mte, "test_t": tte, "test_days": int(te.notna().sum()),
                             "test_ic_lo": block_boot(te)[0], "test_ic_hi": block_boot(te)[1],
                             "train_top5_ex": float(trb.mean()), "test_top5_ex": float(teb.mean()),
                             "test_top5_lo": lo, "test_top5_hi": hi,
                             "test_top5_net": float(teb.mean() - COST),
                             "test_hit": float((teb > 0).mean()), "perm_p": pperm,
                             "p_train": float(2 * (1 - stats.norm.cdf(abs(ttr)))) if ttr == ttr else 1.0})
    res = pd.DataFrame(rows)
    res["p_train_holm"] = holm(res["p_train"].fillna(1).values)
    res.to_csv(out / "step2.csv", index=False)
    pd.to_pickle(allbk, out / "step2_baskets.pkl")
    return res


def step2_daily(out: Path):
    """日線層『隔夜看雷達』：用前一天的 rot／dshare／象限，預測今天的超額漲跌。"""
    gb, mb = build_group_bars(out); gd = build_daily(out); U = universe(gb)
    g = gd[gd["group_id"].isin(U) & (gd["date"] >= "2023-09-19")].sort_values(["group_id", "date"]).copy()
    g["xchg_cs"] = g["chg_pct"] - g.groupby("date")["chg_pct"].transform("mean")
    for c in ("rot", "dshare"):
        g[c + "_prev"] = g.groupby("group_id")[c].shift(1)
    g["ds3_prev"] = g.groupby("group_id")["dshare"].transform(lambda s: s.rolling(3).sum().shift(1))
    rows = []
    for c in ("rot_prev", "dshare_prev", "ds3_prev"):
        ic = daily_ic(g.dropna(subset=[c, "xchg_cs"]), c, "xchg_cs")
        tr, te = ic[ic.index <= TRAIN_END], ic[ic.index > TRAIN_END]
        rows.append({"signal": c, "train_ic": newey_t(tr)[0], "train_t": newey_t(tr)[1],
                     "test_ic": newey_t(te)[0], "test_t": newey_t(te)[1],
                     "test_lo": block_boot(te)[0], "test_hi": block_boot(te)[1], "test_days": int(te.notna().sum())})
    return pd.DataFrame(rows)


if __name__ == "__main__" and (len(sys.argv) > 1 and sys.argv[1] in ("step2", "all")):
    o_ = outdir(sys.argv[1:])
    r = step2(o_); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    print(r[["time", "signal", "target", "train_ic", "train_t", "test_ic", "test_t", "test_top5_ex", "test_top5_lo", "test_top5_hi", "test_hit", "perm_p", "p_train_holm"]].round(4).to_string())
    print(step2_daily(o_).round(4).to_string())


# ───────────────────────── 圖與額外統計 ─────────────────────────
def extra(out: Path, w):
    """弱開→尾盤強的資金路徑、反例清單、10-30 個案表。"""
    X = {}
    s = w.sort_values(["group_id", "date", "k"])
    p = s.pivot_table(index=["date", "group_id"], columns="k", values=["xret", "surge", "bar_surge"])
    p.columns = [f"{a}{b}" for a, b in p.columns]
    p = p.dropna(subset=["xret0", "xret4", "surge1", "surge2", "surge3"]).reset_index()
    for c in ("xret0", "xret4"):
        p[c + "cs"] = p[c] - p.groupby("date")[c].transform("mean")
    p["rk_end"] = p.groupby("date")["xret4cs"].rank(pct=True)
    weak = p[p["xret0cs"] < -0.005].copy()
    weak["end"] = np.where(weak["rk_end"] >= 0.8, "強收", np.where(weak["rk_end"] <= 0.2, "弱收", "中間"))
    X["weak_open_n"] = int(len(weak)); X["weak_open_cnt"] = weak["end"].value_counts().to_dict()
    X["weak_path"] = weak.groupby("end")[["xret0", "xret1", "xret2", "xret3", "xret4", "bar_surge1", "bar_surge2", "bar_surge3", "bar_surge4"]].mean().round(4).to_dict("index")
    # 條件預測力：只看「10:00 落後同儕>0.5%」的族群，11:00 的占比放大能否預測 11:00 之後的剩餘超額（Andy 的情境）
    wk = s[(s["k"] == 1)].merge(weak[["date", "group_id"]], on=["date", "group_id"]).dropna(subset=["surge", "xrem"])
    ic_c = daily_ic(wk, "surge", "xrem"); mu_c, t_c = newey_t(ic_c)
    X["weak_open_cond_ic"] = {"mean_ic": float(mu_c), "t": float(t_c), "days": int(ic_c.notna().sum()), "ci": [float(v) for v in block_boot(ic_c)]}
    # 反例：收盤累計占比比平常多、但當天相對同儕大幅落後
    e = s[s["k"] == 4].dropna(subset=["surge", "xret"]).copy()
    e["xcs"] = e["xret"] - e.groupby("date")["xret"].transform("mean")
    e["rs"] = e.groupby("date")["surge"].rank(pct=True); e["rx"] = e.groupby("date")["xret"].rank(pct=True)
    cx = e[(e["rs"] >= 0.9) & (e["rx"] <= 0.1)]
    X["counter_n"] = int(len(cx)); X["eod_n"] = int(len(e))
    X["counter_top"] = cx.sort_values("surge", ascending=False).head(8)[["date", "group_id", "surge", "xcs", "ret"]].round(4).to_dict("records")
    both = e[(e["rs"] >= 0.9) & (e["rx"] >= 0.9)]; X["agree_top_n"] = int(len(both))
    X["p_up_given_top_surge"] = float((e[e["rs"] >= 0.9]["xcs"] > 0).mean())
    X["p_up_given_bottom_surge"] = float((e[e["rs"] <= 0.1]["xcs"] > 0).mean())
    X["n_top_surge"] = int((e["rs"] >= 0.9).sum())
    (out / "extra.json").write_text(json.dumps(X, ensure_ascii=False, indent=1, default=str))
    return X, weak


def figs(out: Path, img: Path, w, R, X, weak, res):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    for f_ in glob.glob("/usr/share/fonts/truetype/wqy/*.ttc"):
        fm.fontManager.addfont(f_)
    plt.rcParams.update({"font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "axes.unicode_minus": False,
                         "figure.dpi": 130, "axes.spines.top": False})
    img.mkdir(parents=True, exist_ok=True)
    tag = "20261030_"
    # 圖1：10-30 個案
    d = w[w["date"] == "2026-10-30"]
    gname = {"pcb_rigid": "PCB 硬板", "ic_substrate": "PCB 載板", "ccl": "CCL 銅箔基板"}
    e4 = d[d["k"] == 4].sort_values("xret", ascending=False)
    best = e4.iloc[0]["group_id"]
    gname[best] = "當日相對最強：" + str(best)
    ids = ["pcb_rigid", "ic_substrate", "ccl", best]
    fig, axs = plt.subplots(2, 2, figsize=(12, 7.2))
    xs = [KL[k] for k in range(5)]
    for ax, gid in zip(axs.ravel(), ids):
        s_ = d[d["group_id"] == gid].sort_values("k")
        ax.plot(xs, s_["xret"] * 100, "-o", color="#1f77b4", label="相對大盤累計漲跌(%)  左軸")
        ax.plot(xs, s_["ret"] * 100, "--", color="#7f7f7f", label="族群自身累計漲跌(%)  左軸")
        ax.axhline(0, color="#ccc", lw=.8)
        ax2 = ax.twinx(); ax2.spines["top"].set_visible(False)
        ax2.bar(xs, s_["bar_surge"].fillna(0), alpha=.35, color="#ff7f0e", width=.5, label="該小時占比比平常多(pp)  右軸")
        ax2.set_ylim(-max(1.2, s_["bar_surge"].abs().max() * 1.3), max(1.2, s_["bar_surge"].abs().max() * 1.3))
        ax.set_title(gname[gid], fontsize=11); ax.set_xlabel("到該時間為止（10:00 的量資料缺）")
    h1, l1 = axs[0, 0].get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, loc="lower center", ncol=3, frameon=False)
    fig.suptitle("2026-10-30 盤中：走勢（線）vs 資金占比變化（柱）　大盤當天 −4.4%", fontsize=13)
    fig.tight_layout(rect=(0, .05, 1, .95)); fig.savefig(img / (tag + "case_1030.png")); plt.close(fig)
    # 圖2：占比變化 vs 當天超額漲跌；分盤勢一致率
    A = R["daily"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    b = pd.DataFrame(A["dshare_by_xchg_bin"])
    ax[0].bar(range(len(b)), b["dshare"], color=["#2ca02c" if v < 0 else "#d62728" for v in b["dshare"]])
    ax[0].set_xticks(range(len(b))); ax[0].set_xticklabels([x.replace("(", "").replace("]", "").replace(", ", "~") for x in b["xb"]], rotation=30, fontsize=8)
    ax[0].set_title("當天相對漲跌(%)分箱 → 族群占比日變化平均(pp)"); ax[0].axhline(0, color="#999", lw=.8)
    for i, n in enumerate(b["n"]): ax[0].text(i, -0.15, f"n={n}", ha="center", va="bottom", fontsize=7, color="#555")
    rg = A["by_regime"]; names = list(rg.keys())
    ax[1].bar(names, [rg[k]["agree"] for k in names], yerr=[[rg[k]["agree"] - rg[k]["lo"] for k in names], [rg[k]["hi"] - rg[k]["agree"] for k in names]], color="#1f77b4", capsize=3)
    ax[1].axhline(.5, color="#d62728", ls="--", lw=1); ax[1].set_ylim(.45, .7)
    ax[1].set_title("占比增減方向 = 相對漲跌方向 的一致率（紅線＝擲銅板）"); 
    for i, k in enumerate(names): ax[1].text(i, .46, f"{rg[k]['days']}天", ha="center", fontsize=8)
    fig.tight_layout(); fig.savefig(img / (tag + "daily_agree.png")); plt.close(fig)
    # 圖3：象限（同日／前一天）
    fig, ax = plt.subplots(figsize=(7.5, 4))
    qs = ["leading", "improving", "weakening", "lagging"]; qn = {"leading": "領先", "improving": "改善", "weakening": "轉弱", "lagging": "落後"}
    xx = np.arange(4)
    ax.bar(xx - .2, [A["quad_same_day"][q]["mean_x"] for q in qs], .4, label="當天收盤象限（含當天走勢，非獨立）", color="#9ecae1")
    ax.bar(xx + .2, [A["quad_prev_day"][q]["mean_x"] for q in qs], .4, label="前一天象限 → 今天（可事前看到）", color="#3182bd")
    ax.set_xticks(xx); ax.set_xticklabels([f"{qn[q]}\nn={A['quad_prev_day'][q]['n']}" for q in qs]); ax.axhline(0, color="#999", lw=.8)
    ax.set_ylabel("相對全族群平均的當天漲跌(%)"); ax.legend(frameon=False, fontsize=8); ax.set_title("輪動雷達象限 vs 當天相對漲跌")
    fig.tight_layout(); fig.savefig(img / (tag + "quadrant.png")); plt.close(fig)
    # 圖4：弱開→強收資金路徑
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for nm, c in (("強收", "#d62728"), ("中間", "#999"), ("弱收", "#2ca02c")):
        pth = X["weak_path"][nm]
        ax[0].plot([KL[k] for k in range(5)], [pth[f"xret{k}"] * 100 for k in range(5)], "-o", color=c, label=f"{nm}（n={X['weak_open_cnt'][nm]}）")
        ax[1].plot([KL[k] for k in range(1, 5)], [pth[f"bar_surge{k}"] for k in range(1, 5)], "-o", color=c, label=nm)
    ax[0].set_title("開盤弱（10:00 落後同儕>0.5%）的族群：相對大盤漲跌(%)"); ax[1].set_title("同一批：該小時占比比平常多(pp)")
    ax[0].legend(frameon=False); ax[1].axhline(0, color="#999", lw=.8)
    fig.tight_layout(); fig.savefig(img / (tag + "weak_open_path.png")); plt.close(fig)
    # 圖5：第二步 IC 森林圖
    r = res.copy(); r["lab"] = r["time"] + " " + r["signal"].str[:2] + " " + r["target"].str[:4]
    fig, ax = plt.subplots(figsize=(8.5, 6.5)); yy = np.arange(len(r))[::-1]
    ax.errorbar(r["test_ic"], yy, xerr=[r["test_ic"] - r["test_ic_lo"], r["test_ic_hi"] - r["test_ic"]], fmt="o", color="#d62728", label="樣本外 2025-04~2026-10（95%信賴區間）", capsize=2)
    ax.plot(r["train_ic"], yy, "s", color="#7f7f7f", label="訓練 2023-09~2025-03 平均IC")
    ax.axvline(0, color="#999"); ax.set_yticks(yy); ax.set_yticklabels(r["lab"], fontsize=8); ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("盤中訊號對未來超額報酬的每日 Spearman IC（16 組，全部未過多重比較）"); fig.tight_layout(); fig.savefig(img / (tag + "step2_ic.png")); plt.close(fig)
    # 圖6：樣本外 top5 籃子累計（扣成本前後）
    bk = pd.read_pickle(out / "step2_baskets.pkl")
    fig, ax = plt.subplots(figsize=(8.5, 4))
    for (T, col, tc), s_ in bk.items():
        if col == "xret" and tc == "xrem_nd" or col == "surge" and tc == "xrem":
            t = s_[s_.index > TRAIN_END]
            ax.plot(pd.to_datetime(t.index), t.cumsum() * 100, label=f"{TIMES[T]} {col}→{tc}")
            ax.plot(pd.to_datetime(t.index), (t - COST).cumsum() * 100, ls=":", color=ax.lines[-1].get_color())
    ax.axhline(0, color="#999"); ax.legend(frameon=False, fontsize=8); ax.set_ylabel("累計超額(%)，虛線＝扣 0.47%/趟")
    ax.set_title("樣本外 top5 族群籃子累計超額（相對當天全族群平均）"); fig.tight_layout(); fig.savefig(img / (tag + "step2_basket.png")); plt.close(fig)


def main_all(out: Path, img: Path):
    R, w, g = step1(out)
    res = step2(out, w); d2 = step2_daily(out)
    X, weak = extra(out, w)
    res.to_csv(out / "step2.csv", index=False); d2.to_csv(out / "step2_daily.csv", index=False)
    figs(out, img, w, R, X, weak, res)
    print(res[["time", "signal", "target", "train_ic", "train_t", "test_ic", "test_t", "test_ic_lo", "test_ic_hi", "test_top5_ex", "test_top5_net", "test_hit", "perm_p", "p_train_holm"]].round(4).to_string())
    print(d2.round(4).to_string()); print(json.dumps(X, ensure_ascii=False, indent=1, default=str)[:3000])


if __name__ == "__main__" and (len(sys.argv) > 1 and sys.argv[1] == "report"):
    a = sys.argv[1:]
    img = Path(a[a.index("--img") + 1]) if "--img" in a else ROOT / "docs/research/img"
    main_all(outdir(a), img)
