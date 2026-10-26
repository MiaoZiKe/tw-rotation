"""台指期第四輪：換方向——「預設滿倉做多，只在高信心的危險訊號出現時才出場」，並用規則調曝險（不是單純加槓桿）。

為什麼換方向：前三輪證明 1 倍台指期永遠持有在 2013 年後就輸 0050（0050 含息、台指期價格不含息），
任何『進場擇時』都只會更少曝險、更輸。反過來想：平常就滿倉（不錯過反彈），只在危險訊號（跌破 200 日線、VIX 飆高、
逆價差深、週K 轉空、距高點回檔過深、前一晚美股重挫、外資現貨連續賣超）出現時才空手；並測「趨勢強時 1.2～1.5 倍、危險時 0 倍」的動態曝險。
主結果的**平均曝險不得超過 1.2 倍**，並列出平均曝險（含空手日）。

季節性（Sell in May、年底作帳、農曆年前後）一律當成『危險訊號的加權項』或『曝險加碼窗口』，不單獨使用。

資料切法（Andy 指示）：搜尋與選參只用 2008～2016；2017～2020 與 2021 起「都已被看過」（第二、三輪看過），
所以只能用 walk-forward＋參數鄰域防過擬合，最後兩段都列出且明寫「已被看過」；冠軍必須兩段都贏 0050。
開發過程中**不看 2017 以後的數字**：所有調整只依據 2008～2016；2017 以後只在最後揭露一次（鎖檔）。
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402
from pipeline.compute import futures_lab2 as G  # noqa: E402
from pipeline.compute import futures_lab3 as L3  # noqa: E402

OUT = ROOT / "docs" / "futures_lab" / "round4"
TRAIN = L3.TRAIN                 # 2008-01-02 ~ 2016-12-31
SEEN1 = ("2017-01-01", "2021-01-01")
SEEN2 = ("2021-01-01", None)
WF_TEST = ["2011-01-01", "2013-01-01", "2015-01-01"]
WF_END = "2017-01-01"
BAND = 0.2
AVG_EXPO_MAX = 1.2


@G.njit(cache=True)
def _state_nb(raw, m):
    """危險狀態：raw 為真就進入；要連續 m 天 raw 都為假才解除。"""
    n = len(raw); out = np.zeros(n, np.bool_); s = False; clear = 0
    for i in range(n):
        if raw[i]:
            s = True; clear = 0
        elif s:
            clear += 1
            if clear >= m:
                s = False
        out[i] = s
    return out


@G.njit(cache=True)
def _sim_lev_fx(o, h, l, c, tgt, rollday, fee, slip, tax, roll_pts, m_init, m_maint, band, cash_d, e0, cm):
    """同 futures_lab2._sim_lev，但手續費／滑價／換月成本乘上 cm[i]（價格被往回調整後，每口實際成本要換算回原價格口徑）。"""
    n = len(c)
    r = np.zeros(n); qa = np.zeros(n); liq = np.zeros(n)
    E = e0; q = 0.0
    for i in range(1, n):
        f_i = fee * cm[i]; s_i = slip * cm[i]; r_i = roll_pts * cm[i]
        Eo = E + q * 200.0 * (o[i] - c[i - 1])
        if Eo <= 0:
            Eo = 1e-6
        qt = tgt[i - 1] * Eo / (o[i] * 200.0)
        qmax = Eo / (m_init * o[i] * 200.0)
        if qt > qmax:
            qt = qmax
        do = False
        if q == 0.0 and qt > 0.0:
            do = True
        elif qt == 0.0 and q > 0.0:
            do = True
        elif q > 0.0 and abs(qt - q) > band * q:
            do = True
        if do:
            dq = qt - q
            Eo -= abs(dq) * (f_i + 200.0 * s_i) + tax * abs(dq) * 200.0 * o[i]
            q = qt
        if q > 0.0:
            eadv = Eo + q * 200.0 * (l[i] - o[i])
            if eadv < m_maint * q * 200.0 * l[i]:
                Eo = eadv - q * (f_i + 200.0 * s_i) - tax * q * 200.0 * l[i]
                if Eo <= 0:
                    Eo = 1e-6
                liq[i] = 1.0
                q = 0.0
                Ec = Eo * (1.0 + cash_d)
                r[i] = Ec / E - 1.0; E = Ec; qa[i] = 0.0
                continue
        Ec = Eo + q * 200.0 * (c[i] - o[i])
        if rollday[i] and q > 0.0:
            Ec -= q * (r_i * 200.0 + 2.0 * f_i)
        if Ec <= 0:
            Ec = 1e-6
        Ec *= (1.0 + cash_d)
        r[i] = Ec / E - 1.0; E = Ec; qa[i] = q
    return r, qa, liq


def roll_adjust(lab, idx):
    """換月跳點修正（本輪發現的重大問題，見 README 第二節）。
    台指期近月連續序列在結算後換到下一個月合約，新合約價格已內含預期股利而較低，序列在『結算日隔天』出現向下跳點；
    但真實持倉換月並不會因此虧損（舊合約按結算價了結、新合約以新價買進），而長期持有期貨本來就會因為遠月折價收斂而賺到股利（等於總報酬）。
    實測：2008～2016 結算日隔天的平均『期貨報酬 - 現貨報酬』= -406 bp／年，與加權指數的現金股利殖利率（約 4%）同量級，且集中在除息旺季（6 月 -130 bp）。
    修正：結算日隔天的報酬改用現貨加權指數當天的報酬，並把之前的價格乘上調整係數（比例往回調整）。
    回傳 (o,h,l,c 調整後, cm 成本換算係數＝調整後價格／原始價格 的倒數縮放)。"""
    L = lab.lab
    import glob
    d = pd.concat([pd.read_parquet(f) for f in glob.glob(str(ROOT / "data" / "index_ohlc" / "**" / "*.parquet"), recursive=True)])
    d["date"] = pd.to_datetime(d["date"])
    tse = d[d.symbol == "TSE"].drop_duplicates("date").set_index("date").close.reindex(idx).ffill()
    tr = tse.pct_change().to_numpy()
    c = L.c; n = len(c)
    k = np.ones(n)
    for i in np.where(L.settle)[0]:
        t = i + 1
        if t < n and np.isfinite(tr[t]):
            k[t] = (c[t] / c[t - 1]) / (1.0 + tr[t])          # 作用在 t 之前所有 bar
    # factor[j] = prod_{t>j} k[t]
    fac = np.ones(n)
    acc = 1.0
    for j in range(n - 1, -1, -1):
        fac[j] = acc
        acc *= k[j]
    return L.o * fac, L.h * fac, L.l * fac, L.c * fac, fac


def cny_windows(idx: pd.DatetimeIndex):
    """用交易日曆的『農曆年前後最長休市』推出每年封關／開紮日，不靠外部日期表。
    回傳 (pre, post) 兩個布林陣列：封關前 10 個交易日、開紮後 5 個交易日。"""
    pre = np.zeros(len(idx), bool); post = np.zeros(len(idx), bool)
    d = pd.Series(idx)
    for y in range(idx[0].year, idx[-1].year + 1):
        m = (d >= f"{y}-01-10") & (d <= f"{y}-03-05")
        s = d[m]
        if len(s) < 5:
            continue
        gaps = s.diff().dt.days
        j = gaps.idxmax()
        if gaps[j] < 5:
            continue
        pos = s.index.get_loc(j)             # j 是開紮日（休市後第一個交易日）
        first_after = s.index[pos]
        last_before = s.index[pos - 1]
        pre[max(0, last_before - 9):last_before + 1] = True
        post[first_after:first_after + 5] = True
    return pre, post


class Lab4(L3.Lab3):
    def __init__(self):
        super().__init__()
        L = self.lab; idx = self.idx
        self.ao, self.ah, self.al, self.c, self.fac = roll_adjust(self, idx)
        c = self.c
        self.ma = {n: pd.Series(c).rolling(n).mean().to_numpy() for n in (50, 100, 150, 200, 250)}
        self.dd250 = c / pd.Series(c).rolling(250, min_periods=60).max().to_numpy() - 1
        self.vix = self.us["vix"].to_numpy()
        self.bas = L.X["bas"]
        self.spx_night = self.us_night["spx"]
        self.sox_night = self.us_night["sox"]
        # 外資現貨：全市場外資買賣超金額（股數 x 當日收盤），2012 起；20 日累計
        self.fn20 = self._foreign_cash(idx)
        self.month = idx.month.to_numpy()
        self.cny_pre, self.cny_post = cny_windows(idx)
        self.reg = F.weekly_regime(pd.Series(self.c, index=idx), 30)
        self.fee = F.FEE_NTD
        self.cash_d = F.CASH_Y / F.PPY
        self.tcache = {}

    def _foreign_cash(self, idx):
        try:
            a = L3._rd("inst_daily", ["date", "code", "foreign_total"])
            p = L3._rd("price_daily", ["date", "code", "close"])
            a["date"] = pd.to_datetime(a["date"]); p["date"] = pd.to_datetime(p["date"])
            m = a.merge(p, on=["date", "code"], how="inner")
            v = (m["foreign_total"].astype(float) * m["close"].astype(float)).groupby(m["date"]).sum()
            v = v.reindex(idx)
            return v.rolling(20, min_periods=15).sum().to_numpy()
        except Exception:                                          # noqa: BLE001
            return np.full(len(idx), np.nan)

    # ---------------------------------------------------------------- 危險旗標
    def flags(self, p):
        fl = {}
        n = p.get("n", 200)
        c = self.c
        if "T" in p["set"]:
            m = self.ma[n]
            fl["T"] = np.where(np.isnan(m), False, c < m)
        if "V" in p["set"]:
            fl["V"] = np.where(np.isnan(self.vix), False, self.vix > p["vix"])
        if "B" in p["set"]:
            fl["B"] = np.where(np.isnan(self.bas), False, self.bas < -p["bas"])
        if "W" in p["set"]:
            fl["W"] = self.reg == -1
        if "DD" in p["set"]:
            fl["DD"] = np.where(np.isnan(self.dd250), False, self.dd250 < -p["dd"])
        if "FN" in p["set"]:
            fl["FN"] = np.where(np.isnan(self.fn20), False, self.fn20 < 0)
        if "SM" in p["set"]:
            fl["SM"] = (self.month >= 5) & (self.month <= 10)
        if "U" in p["set"]:
            fl["U"] = np.where(np.isnan(self.spx_night), False, self.spx_night <= -0.02)
        return fl

    def target(self, p):
        key = json.dumps(p, sort_keys=True, default=str)
        if key in self.tcache:
            return self.tcache[key]
        fl = self.flags(p)
        cnt = sum(v.astype(int) for v in fl.values())
        raw = cnt >= p["k"]
        st = _state_nb(raw, int(p["m"]))
        if p["base"] == "dyn":
            vx = np.where(np.isnan(self.vix), 0.0, self.vix)
            strong = (self.c > self.ma[50]) & (self.ma[50] > self.ma[200]) & (vx < 20)
            expo = np.where(strong, 1.5, 1.0)
        else:
            expo = np.full(len(self.c), float(p["base"]))
        if p.get("boost"):
            expo = np.where((self.month == 12) | self.cny_pre, expo + 0.2, expo)
        tgt = np.where(st, 0.0, expo)
        self.tcache[key] = tgt
        return tgt

    def run_t(self, tgt, fix=True):
        L = self.lab
        if fix:
            o, h, l, c = self.ao, self.ah, self.al, self.c
            cm = 1.0 / self.fac
        else:                                                   # 對照：不修正換月跳點（前三輪的口徑）
            o, h, l, c = L.o, L.h, L.l, L.c
            cm = np.ones(len(c))
        r, q, liq = _sim_lev_fx(o, h, l, c, tgt, L.settle, F.FEE_NTD, F.SLIP_PTS, F.TAX, F.ROLL_PTS,
                                G.M_INIT, G.M_MAINT, BAND, self.cash_d, G.E0, cm)
        r = pd.Series(r, index=self.idx)
        E = G.E0 * (1 + r).cumprod()
        expo = pd.Series(q * c * 200.0 / E.to_numpy(), index=self.idx)
        return r, expo, liq

    def gap_series(self, theta=0.015, w=0.5):
        """方向 4：美股前一晚（S&P）跌幅 >= theta -> 隔日開盤買、同日收盤賣（日內單，事前規則，只靠開盤前已知的美股收盤）。
        回傳 (逐日報酬貢獻, 訊號日旗標)；報酬 = w x (收-開-成本點數)/前收，成本＝兩腳滑價＋兩腳手續費＋兩腳期交稅。"""
        L = self.lab
        sig = np.where(np.isnan(self.spx_night), False, self.spx_night <= -theta)
        r = np.zeros(len(L.c)); fl = np.zeros(len(L.c), bool)
        for i in np.where(sig)[0]:
            j = i + 1
            if j < len(L.c):
                cost = 2 * F.SLIP_PTS + 2 * F.FEE_NTD / 200.0 + 2 * F.TAX * L.o[j]
                r[j] = w * ((L.c[j] - L.o[j]) - cost) / L.c[i]
                fl[j] = True
        return pd.Series(r, index=self.idx), pd.Series(fl, index=self.idx)

    def run_p(self, p):
        key = "R" + json.dumps(p, sort_keys=True, default=str)
        if key not in self.tcache:
            r, e, l = self.run_t(self.target(p))
            if p.get("gap"):
                gr, gf = self.gap_series()
                r = (1 + r) * (1 + gr) - 1                     # 同日疊加（兩者報酬都小，近似可加）
                e = e + gf.astype(float) * 0.5
            self.tcache[key] = (r, e, l)
        return self.tcache[key]

    def hold(self, lev, fix=True):
        return self.run_t(np.full(len(self.c), float(lev)), fix)


def window_stats(lab, r, expo, a, b=None):
    x = G.sl(r, a, b)
    s = F.stats(x)
    e = G.sl(expo, a, b)
    s["avg_expo"] = float(e.mean()); s["invested_expo"] = float(e[e > 0.01].mean()) if (e > 0.01).any() else 0.0
    s["in_days"] = float((e > 0.01).mean())
    return s


def grid4():
    SETS = [("T",), ("T", "V"), ("T", "B"), ("T", "V", "B"), ("W",), ("W", "V"), ("DD",), ("V",), ("T", "DD"), ("T", "FN"),
            ("T", "SM"), ("T", "V", "SM"), ("T", "U"), ("T", "V", "FN"), ("W", "DD")]
    out = []
    for st in SETS:
        ks = [2] if "SM" in st else ([1] if len(st) == 1 else [1, 2])
        for k in ks:
            axes = dict(
                n=[150, 200, 250] if "T" in st else [200],
                vix=[25, 30, 35] if "V" in st else [30],
                bas=[0.003, 0.005] if "B" in st else [0.003],
                dd=[0.10, 0.15, 0.20] if "DD" in st else [0.15],
                m=[1, 3, 5], base=[1.0, 1.2, "dyn"], boost=[0, 1], gap=[0, 1])
            keys = list(axes)
            for vals in itertools.product(*[axes[x] for x in keys]):
                p = dict(zip(keys, vals)); p["set"] = st; p["k"] = k
                out.append(p)
    return out


AXES = dict(n=[150, 200, 250], vix=[25, 30, 35], bas=[0.003, 0.005], dd=[0.10, 0.15, 0.20], m=[1, 3, 5], base=[1.0, 1.2, "dyn"], boost=[0, 1], gap=[0, 1])


def neighbors4(p, pool=None):
    res = []
    for key, vals in AXES.items():
        if key == "n" and "T" not in p["set"] or key == "vix" and "V" not in p["set"] or key == "bas" and "B" not in p["set"] or key == "dd" and "DD" not in p["set"]:
            continue
        i = vals.index(p[key])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(p); q[key] = vals[j]
                res.append(q)
    return res


def pstr(p):
    return f"{'+'.join(p['set'])}|k={p['k']}" + "".join(f"|{k}={p[k]}" for k in ("n", "vix", "bas", "dd") if (k == "n" and "T" in p["set"]) or (k == "vix" and "V" in p["set"]) or (k == "bas" and "B" in p["set"]) or (k == "dd" and "DD" in p["set"])) + f"|m={p['m']}|base={p['base']}|boost={p['boost']}|gap={p['gap']}"


# ------------------------------------------------------------------ 搜尋（只用 2008～2016）
def fp(x, d=1):
    return F.fmt(x, True, d)


def md(df):
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def score(lab, p, a, b):
    r, e, l = lab.run_p(p)
    s = window_stats(lab, r, e, a, b); bb = lab.b50(a, b)
    if s["avg_expo"] > AVG_EXPO_MAX or s["mdd"] < bb["mdd"]:
        return -1 + s["mdd"], s
    return s["cagr"], s


def select(lab, pool, a, b):
    best, bs = None, -9
    for p in pool:
        sc, _ = score(lab, p, a, b)
        if sc > bs:
            best, bs = p, sc
    return best, bs


def wf(lab, pool):
    ends = WF_TEST[1:] + [WF_END]
    rows, parts = [], []
    for a, b in zip(WF_TEST, ends):
        p, tr = select(lab, pool, TRAIN[0], a)
        r, e, l = lab.run_p(p)
        s = window_stats(lab, r, e, a, b); bb = lab.b50(a, b)
        rows.append(dict(a=a, b=b, p=p, train=tr, cagr=s["cagr"], mdd=s["mdd"], b50=bb["cagr"], b50mdd=bb["mdd"], expo=s["avg_expo"], beat=s["cagr"] >= bb["cagr"]))
        parts.append(G.sl(r, a, b))
    return rows, pd.concat(parts)


def run_search(lab):
    grid = grid4()
    fams = list(dict.fromkeys(g["set"] for g in grid))
    a, b = TRAIN
    bb = lab.b50(a, b)
    reg = []
    for p in grid:
        r, e, l = lab.run_p(p)
        s = window_stats(lab, r, e, a, b)
        reg.append(dict(策略=pstr(p), 搜尋期年化=s["cagr"], 搜尋期回撤=s["mdd"], 平均曝險=s["avg_expo"], 強平=int(l[(lab.idx >= a) & (lab.idx < b)].sum())))
    rows = []
    fin = {}
    for st in fams:
        pool = [g for g in grid if g["set"] == st]
        ch, sc = select(lab, pool, a, b)
        wrows, oos = wf(lab, pool)
        wins = sum(x["beat"] for x in wrows)
        nb = [q for q in neighbors4(ch, pool)]
        nbs = []
        for q in nb:
            _, s = score(lab, q, a, b)
            nbs.append(s)
        nbeat = float(np.mean([s["cagr"] >= bb["cagr"] and s["avg_expo"] <= AVG_EXPO_MAX for s in nbs])) if nbs else np.nan
        _, sch = score(lab, ch, a, b)
        calmar = sch["cagr"] / max(abs(sch["mdd"]), 1e-6)
        rows.append(dict(危險訊號組合="+".join(st), 冠軍參數=pstr(ch), 搜尋期年化=sch["cagr"], 搜尋期回撤=sch["mdd"], 平均曝險=sch["avg_expo"], 持倉日占比=sch["in_days"],
                         WF贏段=f"{wins}/{len(wrows)}", 鄰域贏0050比例=nbeat, 鄰域數=len(nbs), 關卡1=wins > len(wrows) / 2, 關卡2=(nbeat >= 2 / 3) if nbs else False,
                         Calmar=calmar, _p=ch, _wf=wrows))
    df = pd.DataFrame(rows)
    ch_all, _ = select(lab, grid, a, b)
    return dict(grid_n=len(grid), reg=reg, fam=df, ch_all=ch_all, b50=bb)


# ------------------------------------------------------------------ 分析表（只用 2008～2016）
def analysis_tables(lab):
    a, b = TRAIN
    L = lab.lab; idx = lab.idx
    adj = pd.Series(lab.c, index=idx)
    cc = adj.pct_change().fillna(0.0)
    m = (idx >= a) & (idx < b)
    tt = lambda x, y: (x.mean() - y.mean()) / np.sqrt(x.var() / len(x) + y.var() / len(y))
    rows = []
    for nm, w in (("5～10 月（Sell in May）", (lab.month >= 5) & (lab.month <= 10)), ("12 月（年底作帳）", lab.month == 12),
                  ("農曆年前 10 個交易日", lab.cny_pre), ("農曆年後 5 個交易日", lab.cny_post), ("結算日當天", L.settle)):
        x = cc[m & w]; y = cc[m & ~w]
        rows.append({"窗口": nm, "窗內天數": len(x), "窗內日均報酬(bp)": f"{x.mean() * 1e4:.1f}", "窗外日均(bp)": f"{y.mean() * 1e4:.1f}", "t 值": f"{tt(x, y):.2f}"})
    season = pd.DataFrame(rows)
    # 事件偏移
    def study(days, label):
        out = {}
        for off in (-2, -1, 0, 1, 2):
            v = [cc.iloc[i + off] for i in days if 0 <= i + off < len(cc) and m[i]]
            out[f"t{off:+d}"] = f"{np.mean(v) * 1e4:.1f}" if v else "-"
        n = sum(1 for i in days if m[i])
        return {"事件": label, "窗內事件數": n, **out}
    st = np.where(L.settle)[0]
    dl = [idx.searchsorted(pd.Timestamp(f"{y}-{md}")) for y in range(2008, 2017) for md in ("03-31", "05-15", "08-14", "11-14")]
    nfp = []
    for y in range(2008, 2017):
        for mth in range(1, 13):
            d0 = pd.Timestamp(y, mth, 1); fri = d0 + pd.Timedelta(days=(4 - d0.weekday()) % 7)
            i = idx.searchsorted(fri)
            if i < len(idx) and idx[i] == fri:
                nfp.append(i + 1)
    event = pd.DataFrame([study(list(st), "結算日"), study(dl, "財報／營收法定截止日（3/31、5/15、8/14、11/14）"),
                          study(nfp, "美國非農就業公布（每月第一個週五；台股次一交易日為 t+0，近似）")])
    # 跳空回補
    o = pd.Series(L.o, index=idx); c = pd.Series(L.c, index=idx); spx = pd.Series(lab.spx_night, index=idx)
    gr = []
    for th in (0.01, 0.015, 0.02):
        sig = spx <= -th
        day = c.shift(-1) - o.shift(-1)
        cost = 2 * F.SLIP_PTS + 2 * F.FEE_NTD / 200.0 + 2 * F.TAX * o.shift(-1)
        net = (day - cost)[sig & m].dropna()
        gr.append({"美股前一晚跌幅門檻": f">= {th:.1%}", "筆數": len(net), "淨每筆(點)": f"{net.mean():.1f}", "t 值": f"{net.mean() / net.std() * np.sqrt(len(net)):.2f}", "勝率": fp((net > 0).mean(), 0)})
    gap = pd.DataFrame(gr)
    return season, event, gap


# ------------------------------------------------------------------ 逐段筆記（出場期間與持有期間）
def episodes(lab, p, a, b=None, tag=""):
    r, e, l = lab.run_t(lab.target(p))
    fl = lab.flags(p)
    pos = (e.to_numpy() > 0.01)
    idx = lab.idx; c = lab.c
    rows = []
    n = len(idx); i = 1
    while i < n:
        j = i
        while j + 1 < n and pos[j + 1] == pos[i]:
            j += 1
        if idx[i] >= pd.Timestamp(a) and (b is None or idx[i] < pd.Timestamp(b)):
            mk = c[min(j, n - 1)] / c[i - 1] - 1
            sr = float((1 + r.iloc[i:j + 1]).prod() - 1)
            mae = float(((1 + r.iloc[i:j + 1]).cumprod() / np.maximum.accumulate(np.r_[1.0, (1 + r.iloc[i:j + 1]).cumprod().to_numpy()])[1:] - 1).min())
            trig = [k for k, v in fl.items() if i - 1 >= 0 and v[i - 1]] if not pos[i] else []
            if pos[i]:
                last = [k for k, v in fl.items() if j + 1 < n and v[j]]
                rv = ("持有期間賺到：" if sr > 0 else "持有期間虧損：") + (f"{sr:.1%}；之後因 {'+'.join(last) or '訊號'} 轉空手" if j + 1 < n else "；仍持有")
                if mae < -0.10:
                    rv += f"；期間最大回撤 {mae:.0%}，危險訊號出得太慢"
                kind = "持有"
            else:
                rv = ("避開下跌（空手期間指數 %.1f%%）" % (mk * 100)) if mk < -0.03 else ("錯過反彈（空手期間指數 +%.1f%%）" % (mk * 100) if mk > 0.03 else "空手期間指數變動不大")
                kind = "空手"
            rows.append(dict(版本=tag, 類型=kind, 開始=idx[i].date(), 結束=idx[j].date(), 天數=j - i + 1, 策略報酬=round(sr, 4), 指數報酬=round(mk, 4), 觸發旗標=("+".join(trig) if kind == "空手" else ""),
                             最大回撤=round(mae, 4) if kind == "持有" else None, 事後檢討=rv))
        i = j + 1
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 揭露（2017 起，只一次）
def reveal(lab, specs):
    lock = OUT / "_reveal_done.json"
    if lock.exists():
        raise RuntimeError("2017 起的揭露已經做過一次，依規則不再重跑：" + lock.read_text(encoding="utf-8")[:200])
    res = {"0050": {}, "TX持有": {}, "策略": {}}
    wins = {"搜尋期": TRAIN, "已看過1(2017-2020)": SEEN1, "已看過2(2021起)": SEEN2}
    for wn, (a, b) in wins.items():
        res["0050"][wn] = lab.b50(a, b)
        for nm, (fix, lev) in {"台指期持有1x(修正換月)": (True, 1.0), "台指期持有1x(未修正，前三輪口徑)": (False, 1.0), "台指期持有1.2x(修正)": (True, 1.2)}.items():
            r, e, l = lab.hold(lev, fix)
            res["TX持有"].setdefault(nm, {})[wn] = window_stats(lab, r, e, a, b)
    for nm, p in specs.items():
        r, e, l = lab.run_p(p)
        r0, e0, l0 = lab.run_t(lab.target(p), fix=False)
        d = {}
        for wn, (a, b) in wins.items():
            s = window_stats(lab, r, e, a, b); s["liq"] = int(l[(lab.idx >= a) & ((lab.idx < b) if b else True)].sum())
            d[wn] = s
        yrs = {}
        for y in range(2008, 2027):
            x = G.sl(r, f"{y}-01-01", f"{y + 1}-01-01")
            if len(x) > 20:
                yrs[y] = dict(s=float((1 + x).prod() - 1), b=float((1 + lab.lab.bh_0050(f"{y}-01-01", f"{y + 1}-01-01")).prod() - 1))
        res["策略"][nm] = dict(p=p, label=pstr(p), 視窗=d, 年度=yrs,
                              未修正換月_已看過=window_stats(lab, r0, e0, *SEEN1) if False else None)
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


BACK = ("2003-07-01", "2008-01-01")


def backcheck(lab, specs):
    """2003-07～2007-12：本輪所有設計、選參都沒有用過的更早期間（0050 2003-06 才上市；VIX／美股資料 2008 才有，所以 V、U 旗標在此期間無資料＝不觸發）。
    只跑一次（鎖檔 _backcheck_done.json）。"""
    lock = OUT / "_backcheck_done.json"
    if lock.exists():
        return json.loads(lock.read_text(encoding="utf-8"))
    a, b = BACK
    res = {"0050": lab.b50(a, b), "持有": {}, "策略": {}}
    for nm, (fix, lev) in {"台指期持有1x(修正換月)": (True, 1.0), "台指期持有1.2x(修正)": (True, 1.2)}.items():
        r, e, l = lab.hold(lev, fix); res["持有"][nm] = window_stats(lab, r, e, a, b)
    for nm, p in specs.items():
        r, e, l = lab.run_p(p); res["策略"][nm] = window_stats(lab, r, e, a, b)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


def roll_month_table(lab):
    import glob
    d = pd.concat([pd.read_parquet(f) for f in glob.glob(str(ROOT / "data" / "index_ohlc" / "**" / "*.parquet"), recursive=True)])
    d["date"] = pd.to_datetime(d["date"])
    idx = lab.idx
    tse = d[d.symbol == "TSE"].drop_duplicates("date").set_index("date").close.reindex(idx).ffill()
    fr = pd.Series(lab.lab.c, index=idx).pct_change(); tr = tse.pct_change(); diff = fr - tr
    st = np.where(lab.lab.settle)[0]
    a, b = TRAIN
    rows = [(idx[i + 1].month, diff.iloc[i + 1] * 1e4) for i in st if i + 1 < len(idx) and a <= str(idx[i + 1].date()) < b]
    x = pd.DataFrame(rows, columns=["月", "bp"]).groupby("月").bp.agg(["mean", "count"])
    t = pd.DataFrame({"月": [f"{m}月" for m in x.index], "換月隔日『期貨報酬 - 現貨報酬』平均(bp)": x["mean"].round(0).astype(int).to_numpy(), "樣本數": x["count"].to_numpy()})
    return t, float(x["mean"].sum())


SPEC_CH = {}


def write_docs(lab, R, V):
    a0 = lab.b50(*TRAIN)
    hold = V["TX持有"]; b50 = V["0050"]
    fam = R["fam"]
    L = ["# 台指期第四輪：預設滿倉、只在危險訊號時出場（含重大發現：前三輪的換月跳點偏誤）\n"]
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單。淘汰規則：年化輸同期含息扣成本的 0050 -> 淘汰；主結果平均曝險 <= 1.2 倍，並列出平均曝險。\n")
    L.append("> **資料切法**：搜尋與選參只用 2008～2016；**2017～2020 與 2021 起這兩段都已被看過**（第二、三輪看過）。開發過程沒有看這兩段的數字，最後只揭露一次（鎖檔 `_reveal_done.json`）；"
             "防過擬合靠 walk-forward、參數鄰域與預先寫死的關卡。冠軍必須在這兩段**都**贏 0050。\n")
    # 0
    finals = [r for _, r in fam.iterrows() if r["關卡1"] and r["關卡2"]]
    cand = []
    for r in finals:
        cand.append((f"關卡全過：{r['危險訊號組合']}", r["_p"], True))
    best = fam.sort_values("Calmar", ascending=False).iloc[0]
    if not any(c[1] == best["_p"] for c in cand):
        cand.append((f"參考（搜尋期 Calmar 最高，未過關卡）：{best['危險訊號組合']}", best["_p"], False))
    rows = []
    champ = []
    for lab_, p, gate in cand:
        sv = V["策略"][pstr(p)]["視窗"]
        w1, w2 = sv["已看過1(2017-2020)"], sv["已看過2(2021起)"]
        beat1 = w1["cagr"] > b50["已看過1(2017-2020)"]["cagr"]; beat2 = w2["cagr"] > b50["已看過2(2021起)"]["cagr"]
        ok = gate and beat1 and beat2
        if ok:
            champ.append(lab_)
        rows.append({"候選": lab_, "參數": pstr(p),
                     "搜尋期年化／0050": f"{fp(sv['搜尋期']['cagr'])} ／ {fp(a0['cagr'])}", "2017-20（已被看過）年化／0050": f"{fp(w1['cagr'])} ／ {fp(b50['已看過1(2017-2020)']['cagr'])}",
                     "2021 起（已被看過）年化／0050": f"{fp(w2['cagr'])} ／ {fp(b50['已看過2(2021起)']['cagr'])}",
                     "最大回撤 搜尋／2017-20／2021 起（0050）": f"{fp(sv['搜尋期']['mdd'])}／{fp(w1['mdd'])}／{fp(w2['mdd'])}（{fp(a0['mdd'])}／{fp(b50['已看過1(2017-2020)']['mdd'])}／{fp(b50['已看過2(2021起)']['mdd'])}）",
                     "平均曝險 搜尋／2017-20／2021 起": f"{sv['搜尋期']['avg_expo']:.2f}／{w1['avg_expo']:.2f}／{w2['avg_expo']:.2f}",
                     "判定": ("**冠軍**（三關全過且兩段都贏 0050；兩段皆已被看過）" if ok else "淘汰／不採用：" + ("；".join(x for x, f in (("2017-20 輸 0050", not beat1), ("2021 起輸 0050", not beat2), ("未過搜尋期關卡", not gate)) if f)))})
    for nm, d in hold.items():
        rows.append({"候選": "對照 " + nm, "參數": "永遠持有", "搜尋期年化／0050": f"{fp(d['搜尋期']['cagr'])} ／ {fp(a0['cagr'])}",
                     "2017-20（已被看過）年化／0050": f"{fp(d['已看過1(2017-2020)']['cagr'])} ／ {fp(b50['已看過1(2017-2020)']['cagr'])}",
                     "2021 起（已被看過）年化／0050": f"{fp(d['已看過2(2021起)']['cagr'])} ／ {fp(b50['已看過2(2021起)']['cagr'])}",
                     "最大回撤 搜尋／2017-20／2021 起（0050）": f"{fp(d['搜尋期']['mdd'])}／{fp(d['已看過1(2017-2020)']['mdd'])}／{fp(d['已看過2(2021起)']['mdd'])}",
                     "平均曝險 搜尋／2017-20／2021 起": f"{d['搜尋期']['avg_expo']:.2f}／{d['已看過1(2017-2020)']['avg_expo']:.2f}／{d['已看過2(2021起)']['avg_expo']:.2f}", "判定": "基準／對照（不是策略）"})
    L.append("## 〇、通過／淘汰清單\n")
    L.append(md(pd.DataFrame(rows)))
    for lab_, p, gate in cand:
        sv = V["策略"][pstr(p)]["視窗"]; w2 = sv["已看過2(2021起)"]; d2 = w2["cagr"] - b50["已看過2(2021起)"]["cagr"]
        if abs(d2) < 0.005:
            L.append(f"\n註：{lab_.split('：')[-1]} 在 2021 起年化 {w2['cagr'] * 100:.2f}%，0050 {b50['已看過2(2021起)']['cagr'] * 100:.2f}%，差 {d2 * 100:+.2f} 個百分點，依規則（年化低於 0050 即淘汰）仍算輸。\n")
    L.append(f"\n**結論：{('有冠軍：' + '、'.join(champ)) if champ else '沒有冠軍'}。**這個結論所用的 2017～2020 與 2021 起兩段資料**都已經被看過**，只能當作交叉驗證，不是乾淨的樣本外證據。\n")
    # 1 重大發現
    rt, ssum = roll_month_table(lab)
    L.append("## 一、重大發現：前三輪（含第一輪『1 倍台指期結構上輸 0050』）有換月跳點偏誤\n")
    L.append("台指期近月連續序列在每月結算後換到下一個月合約。新合約價格已內含預期股利而較低，所以序列在『結算日隔天』出現向下跳點；"
             "但**真實持倉換月不會因此虧損**（舊合約按結算價了結、新合約以新價買進），而且長期持有期貨本來就會因遠月折價收斂而賺到股利——長期做多台指期等於持有總報酬（價格＋股利，扣掉資金成本、加回保證金以外現金的利息）。"
             "前三輪把跳點當成虧損，等於每年憑空扣掉約一個股利殖利率。\n")
    L.append(f"**實測（2008～2016，結算日隔天『期貨日報酬 - 現貨加權指數日報酬』平均）**：全年 12 個月加總 **{ssum:.0f} bp（約 {ssum / 100:.1f}%／年）**，與加權指數現金股利殖利率（約 4%）同量級，且集中在除息旺季（6 月最大），符合『股利折價』的解釋：\n\n" + md(rt))
    L.append("**修正方法**：結算日隔天的報酬改用現貨加權指數當天的報酬，並把之前的價格乘上調整係數（比例往回調整）；手續費、滑價、換月成本按原價格口徑換算，不被調整係數放大。結算日當天的差異（約 -219 bp／年）保守地保留為真實損益。\n")
    L.append("**影響**（永遠持有 1 倍台指期，修正前＝前三輪口徑）：\n")
    h = []
    for nm in ("台指期持有1x(未修正，前三輪口徑)", "台指期持有1x(修正換月)", "台指期持有1.2x(修正)"):
        d = hold[nm]
        h.append({"口徑": nm, "搜尋期 2008-16": fp(d["搜尋期"]["cagr"]), "2017-20（已被看過）": fp(d["已看過1(2017-2020)"]["cagr"]), "2021 起（已被看過）": fp(d["已看過2(2021起)"]["cagr"])})
    h.append({"口徑": "0050（含息扣成本）", "搜尋期 2008-16": fp(b50["搜尋期"]["cagr"]), "2017-20（已被看過）": fp(b50["已看過1(2017-2020)"]["cagr"]), "2021 起（已被看過）": fp(b50["已看過2(2021起)"]["cagr"])})
    L.append(md(pd.DataFrame(h)))
    L.append("**這表示前三輪的結論要重新檢視**：『1 倍台指期結構上輸 0050』主要是這個偏誤造成的；前三輪的每一個策略報酬都被低估，低估量與『持倉跨結算日的時間』成正比。"
             "那三輪的保留期已經用掉（鎖檔），我沒有重跑；是否在修正後重做，需要另外決定。**我建議修正後重做第一～三輪的搜尋期（不碰保留期鎖檔）**。\n")
    L.append("獨立旁證：修正後 1 倍持有的年化接近『加權指數價格報酬＋股利殖利率』，而且與 0050 的差距縮小到合理的幾個百分點（0050 含台積電集中度與追蹤差異、台指期有換月與保證金現金利息的假設）。這個修正我只用搜尋期（2008～2016）驗證其合理性，沒有用 2017 以後的數字決定怎麼修。\n")
    # 2 families
    bk = V.get("_back")
    if bk:
        rows = [{"候選": "0050", "年化": fp(bk["0050"]["cagr"]), "最大回撤": fp(bk["0050"]["mdd"]), "平均曝險": "-"}]
        for nm, d in bk["持有"].items():
            rows.append({"候選": "對照 " + nm, "年化": fp(d["cagr"]), "最大回撤": fp(d["mdd"]), "平均曝險": f"{d['avg_expo']:.2f}"})
        for nm, d in bk["策略"].items():
            rows.append({"候選": nm, "年化": fp(d["cagr"]), "最大回撤": fp(d["mdd"]), "平均曝險": f"{d['avg_expo']:.2f}"})
        L.append("**額外對照：更早的 2003-07～2007-12**（本輪所有設計與選參都沒有用過這段；只跑一次；VIX／美股資料 2008 才有，V、U 旗標在此期間不觸發；這段是 2003～2007 的大多頭，0050 剛上市）：\n\n" + md(pd.DataFrame(rows)))
    L.append("## 二、方向 1：預設滿倉，只在危險訊號出現時出場（搜尋期 2008～2016；平均曝險 <= 1.2）\n")
    L.append("危險旗標：T＝收盤跌破長均線；V＝VIX 高於門檻；B＝5 日平均基差深度逆價差；W＝週K 轉空頭；DD＝距 250 日高點回檔過深；FN＝外資現貨 20 日累計賣超（2012 起）；"
             "SM＝5～10 月（Sell in May，只能與其他旗標同時成立才出場）；U＝前一晚 S&P 跌 >=2%。k＝至少幾個旗標同時成立才轉空手；m＝危險解除要連續幾天才回場；base＝無危險時的曝險（1.0／1.2 倍／趨勢強時 1.5 否則 1.0）；"
             "boost＝12 月與農曆年前加碼 0.2；gap＝開盤跳空回補日內單（方向 4，見下）。\n")
    t = fam.drop(columns=["_p", "_wf"]).copy()
    for c in ("搜尋期年化", "搜尋期回撤", "持倉日占比", "鄰域贏0050比例"):
        t[c] = t[c].map(fp)
    t["平均曝險"] = t["平均曝險"].map(lambda x: f"{x:.2f}"); t["Calmar"] = t["Calmar"].map(lambda x: f"{x:.2f}")
    t["關卡1"] = t["關卡1"].map(lambda x: "過" if x else "未過"); t["關卡2"] = t["關卡2"].map(lambda x: "過" if x else "未過")
    L.append(md(t))
    L.append(f"關卡 1：walk-forward（訓練窗 2008-01 起擴張；測試窗 2011–12、2013–14、2015–16）多數段贏 0050；關卡 2：冠軍參數的鄰域（只動一個維度、相鄰一格）>= 2/3 贏 0050 且平均曝險 <= 1.2。全部 {R['grid_n']} 組都登記在 `registry.csv`。\n")
    # 3 other directions
    season, event, gap = analysis_tables(lab)
    L.append("## 三、其他方向\n")
    L.append("**方向 5 季節性（搜尋期 2008～2016，日報酬，窗內 vs 窗外）** —— 只當旗標或加碼窗口，不單獨使用：\n\n" + md(season))
    L.append("Sell in May 的方向與文獻一致但 t 值只有約 -1.6（未達 2）；農曆年前 10 日的方向與民間說法相反；年底、年後偏正但不顯著。所以只有 SM 以『需與趨勢旗標同時成立』的方式進入策略，沒有單獨使用。\n")
    L.append("**方向 3 事件日（搜尋期；日報酬 bp，t+0 為事件日）**：\n\n" + md(event))
    L.append("原始序列在結算日隔天有約 -34 bp 的換月跳點（第一節；本表已用修正後的價格，所以 t+1 只剩約 -6 bp），不是可交易的事件效應；其餘事件沒有一致的偏移，**未納入策略**。"
             "FRED 的 CPI／FOMC 歷史發布日需要 FRED API，本容器對 FRED 出口被擋（403）、macro_calendar 只有 2026 年未來日期，所以 CPI／FOMC 沒有測；只測了可由規則推得的結算日、財報截止日、非農（每月第一個週五）。\n")
    L.append("**方向 4 夜盤與跳空：美股前一晚重挫 -> 隔日開盤買、同日收盤賣（事前規則：美股收盤在台股開盤前已知；搜尋期）**：\n\n" + md(gap))
    L.append("淨每筆為正且 t 值 2～2.8；門檻只試 3 個，策略內採用 1.5%（中間值）、權重 0.5 倍、只算日內，成本已扣（兩腳滑價、手續費、期交稅）。這是本輪少數在搜尋期有統計意義的訊號，但仍是 2008～2016 的樣本，2008 金融海嘯占很大比重。\n")
    L.append("**方向 6 法人與融資**：外資現貨買賣超由 `inst_daily`（2012 起）逐股股數乘當日收盤價加總，20 日累計為負＝FN 旗標，已進入第二節的搜尋（家族 T+FN、T+V+FN）；"
             "**融資餘額（margin_daily／margin_total）只有 2021 起**，搜尋期沒有，無法用 2008～2016 驗證，未納入。\n")
    L.append("**方向 2 選擇權資料**：期交所選擇權每日行情簡表可查到 2001-12 起（單日查詢）；FinMind 有 TaiwanOptionDaily（逐契約，未能在本容器驗證欄位）。"
             "已新增 `pipeline/sources/optpc.py`（把逐契約資料算成每日買賣權成交量比與未平倉量比，存進新表 `opt_pc`）並接進 `run_backfill`（只用 `store.append()`，按月游標回補），**尚未在 Actions 實跑、資料還沒進湖**，所以本輪以 VIX（V 旗標）與基差（B 旗標）當情緒代理。出處：[期交所選擇權每日行情](https://www.taifex.com.tw/cht/3/optDailyMarketSummary)。\n")
    # 4 sources
    L.append("## 四、查到的文獻與出處\n")
    L.append("| 主題 | 出處 | 取用的點 |\n|---|---|---|\n"
             "| 長均線出場（危險訊號出場） | [QuantConnect 論壇：Faber GTAA 5（10 個月均線）](https://www.quantconnect.com/forum/discussion/8285/a-quantitative-approach-to-tactical-asset-allocation-gtaa-5-with-simplemovingaverage/)、[TradingView：Mebane Faber GTAA 5](https://www.tradingview.com/script/pFE8Udyy-Mebane-Faber-GTAA-5) | 站上 10 個月（約 200 日）均線持有、跌破轉現金，主要效果是降低波動與回撤；轉述自二手來源，未讀原論文。 |\n"
             "| Sell in May | [Auburn 碩士論文：Sell in May 跨 70 個市場](https://auetd.auburn.edu/handle/10415/3898)、[股感：台股季節性](https://www.stockfeel.com.tw/?p=276941) | 跨國 11～4 月報酬高於 5～10 月；台股民間說法只是評論，作者也提醒規律被廣泛知道後會弱化。 |\n"
             "| 跳空回補 | [NexusFi：gap trading futures](https://nexusfi.com/a/strategies/gap-trading-futures)、[arXiv 2605.04004：OHLCV 日內動能的結構限制](https://arxiv.org/pdf/2605.04004) | 實務說法『約六成跳空當日回補』無方法細節；學術檢驗提醒毛邊際常小於交易成本——所以本輪只做事前（美股前一晚）規則並扣全成本。 |\n"
             "| 選擇權 P/C 資料 | [期交所選擇權每日行情簡表](https://www.taifex.com.tw/cht/3/optDailyMarketSummary)、[wantgoo 法人買賣權](https://www.wantgoo.com/option/institutional-investors-call-put) | 逐契約每日資料；P/C 比需自行計算。 |\n"
             "| FRED 發布日 | [FRED API：release/dates](https://fred.stlouisfed.org/docs/api/fred/release_dates.html) | 需 API key 與網路，容器被擋，未取得。 |\n")
    # 5 notes
    L.append("## 五、逐段交易筆記與檢討\n")
    notes = []
    for lab_, p, gate in cand:
        for per, (a, b) in (("搜尋期2008-16", TRAIN), ("已看過2017-20", SEEN1), ("已看過2021起", SEEN2)):
            notes.append(episodes(lab, p, a, b, tag=f"{lab_.split('：')[-1]}／{per}"))
    nt = pd.concat(notes)
    nt.to_csv(OUT / "trades_round4.csv", index=False, encoding="utf-8-sig")
    N = ["# 台指期第四輪逐段筆記（持有期間與空手期間）\n", "『持有』＝曝險 > 0 的連續區間；『空手』＝危險訊號期間。每段記錄策略報酬、同期指數報酬、觸發的危險旗標與事後檢討（規則式自動產生）。2017 起標『已看過』。\n"]
    for tag, g in nt.groupby("版本", sort=False):
        N.append(f"\n## {tag}（{len(g)} 段）\n")
        for _, r in g.iterrows():
            N.append(f"- **{r['類型']} {r['開始']} ～ {r['結束']}**（{r['天數']} 天）｜策略 {r['策略報酬']:.2%}｜指數 {r['指數報酬']:.2%}" + (f"｜觸發旗標 {r['觸發旗標']}" if r['觸發旗標'] else "") + (f"｜期間最大回撤 {r['最大回撤']:.1%}" if r['最大回撤'] == r['最大回撤'] and r['最大回撤'] is not None else "") + f"｜**檢討**：{r['事後檢討']}")
    (OUT / "trades_notes_round4.md").write_text("\n".join(N), encoding="utf-8")
    base = nt[nt.類型 == "空手"]
    miss = base[base.指數報酬 > 0.03]; avoid = base[base.指數報酬 < -0.03]
    L.append(f"完整逐段見 `trades_notes_round4.md`、`trades_round4.csv`（共 {len(nt)} 段）。空手期間：避開下跌 {len(avoid)} 段（平均指數 {avoid.指數報酬.mean():.1%}）、錯過反彈 {len(miss)} 段（平均指數 +{miss.指數報酬.mean():.1%}）。\n")
    L.append("## 六、優化空間與限制\n")
    L.append("- 優化空間：危險訊號的價值在『避開空頭』，代價是『錯過 V 型反彈』（見筆記的錯過反彈段）；回場條件（m 天）與加碼（boost、動態曝險）是主要可調處；跳空回補日內單目前只用美股前一晚的單一規則，可再測量能與開盤方向確認。\n"
             "- 限制：搜尋期只有 9 年且含 2008 單一大空頭；兩段『已被看過』資料不是乾淨證據；換月修正用現貨日報酬近似，仍可能殘留誤差（結算日當天差異未修）；保證金與資金利息為假設（原始 10%／維持 8%、閒置資金年息 1%）；P/C 比、CPI／FOMC、融資餘額的搜尋期資料缺。\n")
    L.append("## 七、重現\n\n`python -m pipeline.compute.futures_lab4`（搜尋期約 2 分鐘）；`--reveal` 才揭露 2017 起（已揭露過，鎖檔存在時直接讀鎖檔）。測試：`pytest tests/test_futures_lab4.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")


def main(do_reveal=False):
    OUT.mkdir(parents=True, exist_ok=True)
    lab = Lab4()
    R = run_search(lab)
    pd.DataFrame(R["reg"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    print(R["fam"].drop(columns=["_p", "_wf"]).round(3).to_string())
    if not do_reveal:
        return lab, R, None
    fam = R["fam"]
    cand = [r["_p"] for _, r in fam.iterrows() if r["關卡1"] and r["關卡2"]]
    best = fam.sort_values("Calmar", ascending=False).iloc[0]["_p"]
    if best not in cand:
        cand.append(best)
    lock = OUT / "_reveal_done.json"
    V = json.loads(lock.read_text(encoding="utf-8")) if lock.exists() else reveal(lab, {pstr(p): p for p in cand})
    V["_back"] = backcheck(lab, {pstr(p): p for p in cand})
    write_docs(lab, R, V)
    return lab, R, V


if __name__ == "__main__":
    main(do_reveal="--reveal" in sys.argv)
