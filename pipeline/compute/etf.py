"""ETF 專區（2026-10-05）：分類、熱門排行、配息行事曆、殖利率、期間年化報酬。

口徑全部寫在 docs/etf_page_spec.md，這裡的註解只講「為什麼」。

設計重點：
- 資料湖保留真實成交價（只增不改）；分割（例：0050 2025-06-18 一拆四）在這裡偵測並還原，
  不然 3/5/10 年報酬會被一根 -75% 的假跌幅毀掉。
- 價格報酬（不含息）與含息總報酬分開算：總報酬＝配息在除息日以「除息日收盤」再投入。
- 資料不夠一律回 None ＋ 理由字串，前端照字串顯示；**不准用 0 或外插補**。
- 配息湖裡沒有、回補也還沒跑過的 ETF，含息報酬回 None（理由「配息資料尚未取得」），
  不能拿價格報酬冒充 —— 對高股息 ETF 兩者差一大截。
"""
from __future__ import annotations

import math
import re
from datetime import date, timedelta

import pandas as pd

# ------------------------------------------------------------------ 分類

LEV_RE = re.compile(r"正2|反1|反向|槓桿|正向2|2倍|-1倍")
BOND_RE = re.compile(r"債|美債|公債|投資級|非投等")
# 追蹤「大盤市值加權」指數的：台灣 50、中型 100、加權、MSCI 台灣、摩台、FTSE 台灣
MCAP_RE = re.compile(r"台灣50|台50|臺灣50|中型100|加權|MSCI台灣|摩台|富時台灣|台灣領袖")
DIV_RE = re.compile(r"高股息|高息|股息|收益|優息|月配|季配|息收|股利|優利|高利|穩利|配息|高收")
COMMODITY_RE = re.compile(r"^期|黃金|原油|白銀|黃豆|小麥|商品|美元|日圓|期街口")
MCAP_EXCLUDE = re.compile(r"正2|反1")

FILL_AVG_N = 4          # 殖利率卡的「近 N 次平均填息天數」
CATEGORIES = ["配息型", "市值型", "主題型", "債券型", "槓桿反向", "主動式", "其他"]


def is_etf_code(code: str | None) -> bool:
    """00 開頭、至少 4 碼（0050、00878、00631L、00981A、00679B）。普通股不會 0 開頭。"""
    c = str(code or "")
    return len(c) >= 4 and c.startswith("00")


def classify(code: str, name: str, freq_n: int = 0) -> str:
    """回傳單一分類。順序有意義：先排掉「性質特殊」的，再看市值型，最後才看配息。

    1. 槓桿反向：代號尾碼 L／R，或名稱含 正2／反1／反向。
    2. 債券型：代號尾碼 B，或名稱含「債」。
    3. 其他（商品／期貨／貨幣）：名稱以「期」開頭或含黃金／原油…，代號尾碼 U。
    4. 主動式：代號尾碼 A（主動式 ETF，經理人選股，不追蹤指數）。
    5. 市值型：名稱含追蹤大盤市值指數的關鍵字（台灣50／中型100／加權／MSCI台灣／摩台）。
    6. 配息型：名稱含股息類關鍵字，或近 400 天除息 ≥ 4 次（季配以上）的股票型。
    7. 主題型：剩下的股票型（產業、ESG、海外市場…）。
    """
    c = str(code)
    n = str(name or "")
    if c[-1:] in ("L", "R") or LEV_RE.search(n):
        return "槓桿反向"
    if c[-1:] == "B" or BOND_RE.search(n):
        return "債券型"
    if c[-1:] == "U" or COMMODITY_RE.search(n):
        return "其他"
    if c[-1:] == "A" or n.startswith("主動"):
        return "主動式"
    if MCAP_RE.search(n) and not MCAP_EXCLUDE.search(n):
        return "市值型"
    if DIV_RE.search(n) or freq_n >= 4:
        return "配息型"
    if not n:
        return "其他"
    return "主題型"


# 配息間隔（天）→ 頻率的區間。邊界取相鄰兩個標準間隔（30/61/91/182/365）的中點附近，
# 讓除息日每年飄幾天、遇連假順延都還落在同一格；區間外（例如 450 天以上）不硬套，回「未知」。
FREQ_BANDS = [(20, 45, "月配"), (46, 75, "雙月配"), (76, 135, "季配"),
              (136, 250, "半年配"), (251, 450, "年配")]
FREQ_RECENT = 7        # 只看最近 7 次除息（6 個間隔）：夠抗單次順延，又能反映改頻（例：季配改月配）
FREQ_MIN_GAPS = 2      # 至少 2 個間隔（3 次除息）才判；只有 1～2 次除息的新掛牌 ETF 一律「未知」


def _gap_band(g: float) -> str | None:
    for lo, hi, lab in FREQ_BANDS:
        if lo <= g <= hi:
            return lab
    return None


def freq_label_dates(dates: list[str], recent_dates: list[str] | None = None) -> str:
    """除息日序列 → 配息頻率（2026-10-07 第二版）。

    公式：取最近 FREQ_RECENT 次除息（不限 400 天窗，用全部歷史），相鄰間隔的**中位數**對照 FREQ_BANDS。
    為什麼不數次數：400 天窗裡季配最多會落 5 次（00919 2025-09-16 與 2026-09-16 都在窗內），
    「≥5 次＝雙月配」就把 00919、00713 誤標成雙月配；半年配同理會被數成 3 次＝季配。
    例外處理（寧可留白也不硬猜）：
      · 沒有任何除息 → 「不配息」；`recent_dates`（近 400 天內的除息）有給且為空 → 也是「不配息」（停配）。
      · 間隔數 < FREQ_MIN_GAPS（≤ 2 次除息）→ 「未知」。舊版 1 次就判年配，新掛牌的月配 ETF 會被標成年配。
      · 中位數落在所有區間外 → 「未知」。
      · 一半以上的間隔不落在中位數那一格（配息日不規律）→ 「未知」。
    前端只認得五種頻率＋不配息，「未知」不畫徽章。"""
    ds = sorted(set(d for d in dates if d))
    if not ds or (recent_dates is not None and not recent_dates):
        return "不配息"
    ds = ds[-FREQ_RECENT:]
    gaps = [(pd.Timestamp(b) - pd.Timestamp(a)).days for a, b in zip(ds, ds[1:])]
    if len(gaps) < FREQ_MIN_GAPS:
        return "未知"
    lab = _gap_band(float(pd.Series(gaps).median()))
    if lab is None:
        return "未知"
    if sum(1 for g in gaps if _gap_band(g) == lab) * 2 < len(gaps):
        return "未知"
    return lab


def freq_label(n: int) -> str:
    """近 400 天除息次數 → 配息頻率。用 400 天不用 365 天：除息日每年會飄幾天，
    365 天的窗常常剛好漏掉一次，季配被誤判成「一年 3 次」。"""
    if n >= 10:
        return "月配"
    if n >= 5:
        return "雙月配"
    if n >= 3:
        return "季配"
    if n == 2:
        return "半年配"
    if n == 1:
        return "年配"
    return "不配息"


# ------------------------------------------------------------------ 分割還原

_SPLITS = [1 / 10, 1 / 5, 1 / 4, 1 / 3, 1 / 2, 2, 3, 4, 5, 10]


def split_factors(dates: list[str], close: list[float]) -> list[float]:
    """回傳每一天的股數還原因子（最新一天恆為 1）。

    偵測：相鄰兩天收盤比落在 [0.55, 1.8] 之外（ETF 含槓桿 2 倍一天最多 ±20%，
    超出就只可能是分割／反分割），取最接近的常見比例，誤差 15% 內才認。
    分割當天之前的價格乘上「新／舊」比例 —— 例：一拆四，之前的價格 × 1/4。"""
    n = len(close)
    f = [1.0] * n
    acc = 1.0
    for i in range(n - 1, 0, -1):
        a, b = close[i - 1], close[i]
        f[i] = acc
        if a and b and a > 0 and b > 0:
            r = b / a
            if r < 0.55 or r > 1.8:
                best = min(_SPLITS, key=lambda s: abs(math.log(r / s)))
                if abs(r / best - 1) <= 0.15:
                    acc *= best
    f[0] = acc
    return f


# ------------------------------------------------------------------ 報酬計算

def total_return_index(px: list[float], div: list[float]) -> list[float]:
    """含息總報酬指數：TR_t ＝ TR_{t-1} × (P_t ＋ D_t) ÷ P_{t-1}。

    D_t 是除息日 t 當天除掉的現金股利（已換到同一股數基準）。等同「配息在除息日收盤再投入」。"""
    out = [1.0]
    for i in range(1, len(px)):
        p0, p1 = px[i - 1], px[i]
        if not p0:
            out.append(out[-1])
            continue
        out.append(out[-1] * (p1 + (div[i] or 0.0)) / p0)
    return out


def fill_info(close: list[float], ex_i: int) -> tuple[int | None, int | None]:
    """填息天數（2026-10-05 Andy：「記得要備註花多久填息」）。回 (填息天數, 尚未填息已經過的天數)。

    口徑沿用個股除權息分頁（compute/stockpage.dividends）：從除息日當天算第 1 個交易日，
    第一個收盤 ≥ 除息前一日收盤的那天是第幾個交易日。除息當天就收回去 ＝ 1 天。
    - 已填息 → (天數, None)
    - 到資料最後一天還沒填 → (None, 已經過的交易日數，含除息日)；前端寫「尚未填息（已 N 天）」
    - 除息日不在行情裡、或除息日是第一根（沒有前一日收盤）→ (None, None)；前端寫「—」
    close 要用分割還原後的收盤：除息後若遇到分割，用原始價比會被一根 −75% 假跌幅判成永遠填不回去。"""
    if ex_i is None or ex_i <= 0 or ex_i >= len(close) or not close[ex_i - 1]:
        return None, None
    before = close[ex_i - 1]
    for j in range(ex_i, len(close)):
        if close[j] is not None and close[j] >= before:
            return j - ex_i + 1, None
    return None, len(close) - ex_i


def annualize(ratio: float, years: float) -> float | None:
    """(終值 ÷ 起值)^(1/年) − 1。年數 ≤ 0 或比值 ≤ 0 回 None（不外插）。"""
    if ratio is None or years <= 0 or ratio <= 0:
        return None
    return ratio ** (1.0 / years) - 1.0


def period_stats(dates: list[str], px: list[float], tr: list[float] | None, div: list[float],
                 start: str, *, history_complete: bool, div_covered: bool,
                 slack_days: int = 10) -> dict:
    """單一期間的指標。start 之後第一個交易日當起點、最後一天當終點。

    資料不足的判準：湖裡第一筆日期比 start 晚超過 slack_days 天 →
      history_complete（價量回補做過）→「上市未滿 N 年」；否則 →「價量歷史尚未回補」。"""
    if not dates:
        return {"ok": False, "why": "無資料"}
    first = dates[0]
    if (pd.Timestamp(first) - pd.Timestamp(start)).days > slack_days:
        yrs_have = (pd.Timestamp(dates[-1]) - pd.Timestamp(first)).days / 365.25
        why = (f"上市未滿 {math.ceil((pd.Timestamp(dates[-1]) - pd.Timestamp(start)).days / 365.25)} 年"
               f"（有 {yrs_have:.1f} 年）") if history_complete else "價量歷史尚未回補"
        return {"ok": False, "why": why}
    i0 = next(i for i, d in enumerate(dates) if d >= start)
    years = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[i0])).days / 365.25
    if years < 0.5:
        return {"ok": False, "why": "期間不足半年"}
    p0, p1 = px[i0], px[-1]
    out = {"ok": True, "from": dates[i0], "to": dates[-1], "years": round(years, 2),
           "price_ann": annualize(p1 / p0, years) if p0 else None}
    if div_covered and tr is not None:
        out["tr_ann"] = annualize(tr[-1] / tr[i0], years) if tr[i0] else None
        cum = sum(div[i0 + 1:])
        seg = px[i0:]
        avgp = sum(seg) / len(seg) if seg else None
        out["cum_div"] = round(cum, 4)
        out["avg_yield"] = (cum / years / avgp) if avgp else None
        out["div_ann"] = annualize(1.0 + cum / p0, years) if p0 else None
    else:
        out["tr_ann"] = out["avg_yield"] = out["div_ann"] = None
        out["why_div"] = "配息資料尚未取得"
    for k in ("price_ann", "tr_ann", "avg_yield", "div_ann"):
        if out.get(k) is not None:
            out[k] = round(out[k], 5)
    return out


# ------------------------------------------------------------------ 組裝

def series_grid(adj_by: dict, every: int = 5) -> dict:
    """全部 ETF 的累積走勢，共用一條週取樣日期軸（自選比較用，etf_series.json）。

    為什麼共用日期軸：每檔各自帶日期字串，360 檔 × 數百點光日期就好幾 MB；共用之後每檔只帶起點索引＋數值。
    取樣日 D＝所有 ETF 交易日的聯集每 5 天取一點（加最後一天）；某檔在取樣日沒成交（暫停）就沿用前一個收盤。
    前端用 D.slice(i) 對回日期。"""
    alld = sorted({d for dates, _, _ in adj_by.values() for d in dates})
    if not alld:
        return {"D": [], "s": {}}
    step = list(range(0, len(alld), every))
    if step[-1] != len(alld) - 1:
        step.append(len(alld) - 1)
    grid = [alld[i] for i in step]
    out = {}
    for code, (dates, adj, tr) in adj_by.items():
        i0 = next((k for k, g in enumerate(grid) if g >= dates[0]), None)
        if i0 is None:
            continue
        p, t, j = [], [], 0
        for g in grid[i0:]:
            while j + 1 < len(dates) and dates[j + 1] <= g:
                j += 1
            p.append(round(adj[j], 4))
            if tr is not None:
                t.append(round(tr[j], 5))
        out[code] = {"i": i0, "p": p, "t": t if tr is not None else None}
    return {"D": grid, "s": out}


def _divs(div_events: pd.DataFrame, div_results: pd.DataFrame, codes: set[str]) -> pd.DataFrame:
    """每檔每個除息日一列（code, ex_date, amount, pay_date, before）。

    主來源 dividend_events（有發放日）；dividend_results 只補 events 沒有的除息日（避免重複算）。"""
    rows = []
    if div_events is not None and not div_events.empty:
        e = div_events[(div_events["code"].astype(str).isin(codes)) & (div_events["kind"] == "cash")]
        e = e.dropna(subset=["ex_date"])
        # build_payload 會把 dividend_events 與 etf_dividend_events（鍵含除息日）串在一起傳進來，
        # 同一期兩張表都有 → 先依 (代號, 除息日) 去重，不然下面 groupby sum 會把配息算成兩倍。
        e = e.assign(_x=e["ex_date"].astype(str).str[:10], _c=e["code"].astype(str))
        e = e[e["_x"].str.len() == 10].drop_duplicates(subset=["_c", "_x"], keep="last")
        for r in e.itertuples():
            rows.append({"code": str(r.code), "ex_date": str(r.ex_date)[:10],
                         "amount": float(r.amount or 0), "pay_date": (str(r.payment_date)[:10]
                                                                     if r.payment_date and str(r.payment_date) != "nan" else None)})
    df = pd.DataFrame(rows, columns=["code", "ex_date", "amount", "pay_date"])
    if div_results is not None and not div_results.empty:
        r = div_results[div_results["code"].astype(str).isin(codes)].copy()
        if "kind" in r.columns:
            r = r[r["kind"].astype(str).str.contains("息", na=False)]
        have = set(zip(df["code"], df["ex_date"]))
        extra = [{"code": str(x.code), "ex_date": str(x.date)[:10], "amount": float(x.dividend or 0),
                  "pay_date": None} for x in r.itertuples() if (str(x.code), str(x.date)[:10]) not in have]
        if extra:
            df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
    df = df[df["amount"] > 0]
    return df.groupby(["code", "ex_date"], as_index=False).agg(amount=("amount", "sum"),
                                                                pay_date=("pay_date", "first"))


def _holders(sh: pd.DataFrame, codes: set[str]) -> dict:
    """集保：最新一週與前一週的受益人數（合計列），以及總單位數（估規模用）。"""
    if sh is None or sh.empty:
        return {}
    s = sh[(sh["code"].astype(str).isin(codes)) & (sh["level"] == 17)]
    out = {}
    for code, g in s.sort_values("date").groupby("code"):
        g = g.tail(2)
        last = g.iloc[-1]
        prev = g.iloc[0] if len(g) == 2 else None
        out[str(code)] = {"date": str(last["date"]), "holders": int(last["holders"]),
                          "d_holders": (int(last["holders"] - prev["holders"]) if prev is not None else None),
                          "prev_date": (str(prev["date"]) if prev is not None else None),
                          "units": float(last["shares"])}
    return out


def build(price: pd.DataFrame, names: dict, etf_codes: set[str], div_events: pd.DataFrame,
          div_results: pd.DataFrame, shareholding: pd.DataFrame, latest: str,
          done_keys: set[str] | None = None, top_n: int = 5,
          nodata_keys: set[str] | None = None) -> dict:
    done_keys = done_keys or set()
    nodata_keys = nodata_keys or set()
    px = price[price["code"].astype(str).isin(etf_codes)].copy()
    px["code"] = px["code"].astype(str)
    px["date"] = px["date"].astype(str)
    px = px[pd.to_numeric(px["close"], errors="coerce") > 0].sort_values(["code", "date"])
    divs = _divs(div_events, div_results, etf_codes)
    div_by = {c: dict(zip(g["ex_date"], g["amount"])) for c, g in divs.groupby("code")}
    hold = _holders(shareholding, etf_codes)

    def div_done(c):
        # ★ 只認「湖裡真的有配息列」。不看回補的 done 鍵：2016 那一步把 dividend:0050、dividend:0056
        #   都標了 done，湖裡卻 0 列（0050／0056 明明年年配息）—— done 只代表「問過了」，
        #   不代表「問到了」。拿它當「確定不配息」會把 0056 的含息報酬算成跟價格報酬一樣，那是錯的。
        #   代價：真的從不配息的 ETF（槓桿反向、期貨型）也會顯示「配息資料尚未取得」，寧可少講不可講錯。
        return c in div_by

    def div_none(c):
        # 2026-10-06（Andy：「槓桿沒有配息」「其他為何沒數據」）：「確定不配息」要有證據 ——
        #   回補進度檔記了 FinMind 配息資料集對這檔明確回空（etfdiv@etfx2009 = no_data，2009 起整段問過），
        #   且湖裡真的 0 列。只有「沒問過」的不算（那是不知道，不是 0）。前端據此只畫一條「年化報酬率」。
        return (c not in div_by) and any(k in nodata_keys for k in (f"etfdiv@etfx2009:{c}", f"dividend@etf2009:{c}"))

    def px_done(c):
        return any(k in done_keys for k in (f"price:{c}", f"price@2000-01-01:{c}"))

    ld = pd.Timestamp(latest)
    yr_now = ld.year
    periods = {"3y": (ld - pd.DateOffset(years=3)).date().isoformat(),
               "5y": (ld - pd.DateOffset(years=5)).date().isoformat(),
               "10y": (ld - pd.DateOffset(years=10)).date().isoformat()}
    for y in range(2009, yr_now):
        periods[f"Y{y}"] = f"{y}-01-01"
    since400 = (ld - timedelta(days=400)).date().isoformat()
    since365 = (ld - timedelta(days=365)).date().isoformat()

    items, series, fills_by, adj_by = [], {}, {}, {}
    for code, g in px.groupby("code"):
        if g["date"].iloc[-1] < (ld - timedelta(days=30)).date().isoformat():
            continue          # 最近一個月沒成交（下市／暫停）不收
        dates = g["date"].tolist()
        raw = pd.to_numeric(g["close"], errors="coerce").tolist()
        fac = split_factors(dates, raw)
        adj = [r * f for r, f in zip(raw, fac)]
        dmap = div_by.get(code, {})
        dd = [0.0] * len(dates)
        idx = {d: i for i, d in enumerate(dates)}
        for exd, amt in dmap.items():
            if exd in idx:
                dd[idx[exd]] = amt * fac[idx[exd]]
        tr = total_return_index(adj, dd)
        # 每次已除息的填息天數（行事曆、殖利率卡用）；近 4 次的平均只算「已填息」的，未填的另外數
        fl = {exd: fill_info(adj, idx[exd]) for exd in dmap if exd in idx and exd <= latest}
        fills_by[code] = fl
        last4 = [fl[d] for d in sorted(fl)[-FILL_AVG_N:]]
        done4 = [f for f, _ in last4 if f is not None]
        n400 = sum(1 for d in dmap if since400 < d <= latest)
        name = names.get(code, "")
        cat = classify(code, name, n400)
        ttm = sum(a for d, a in dmap.items() if since365 < d <= latest)
        tv = pd.to_numeric(g["turnover"], errors="coerce").tail(20)
        close = raw[-1]
        prev = raw[-2] * fac[-2] if len(raw) > 1 else None
        h = hold.get(code, {})
        stats = {k: period_stats(dates, adj, tr, dd, s, history_complete=px_done(code),
                                 div_covered=div_done(code)) for k, s in periods.items()}
        items.append({
            "code": code, "name": name, "cat": cat,
            "close": round(close, 2),
            "chg_pct": round((adj[-1] / prev - 1) * 100, 2) if prev else None,
            "tv20": round(float(tv.mean()), 0) if tv.notna().any() else None,
            "tv": float(pd.to_numeric(g["turnover"], errors="coerce").iloc[-1] or 0),
            "freq_n": n400,
            "freq": freq_label_dates([d for d in dmap if d <= latest],
                                     [d for d in dmap if since400 < d <= latest]) if div_done(code) else None,
            "yield_ttm": round(ttm / close, 5) if (div_done(code) and close) else None,
            "div_ttm": round(ttm, 4) if div_done(code) else None,
            "holders": h.get("holders"), "d_holders": h.get("d_holders"),
            "size": round(h["units"] * close, 0) if h.get("units") else None,
            "first": dates[0], "px_done": px_done(code), "div_done": div_done(code),
            "div_none": div_none(code),
            "spark": [round(x, 3) for x in adj[-60:]],
            "fill_avg": round(sum(done4) / len(done4), 1) if done4 else None,
            "fill_n": len(last4), "fill_open": sum(1 for f, w in last4 if f is None and w is not None),
            "fill_last": (list(fl[max(fl)]) if fl else None),
            "stats": stats,
        })
        # 累積走勢：週取樣（每 5 個交易日一點＋最後一天），前端依起點自己換算
        step = list(range(0, len(dates), 5))
        if step[-1] != len(dates) - 1:
            step.append(len(dates) - 1)
        series[code] = {"d": [dates[i] for i in step], "p": [round(adj[i], 4) for i in step],
                        "t": [round(tr[i], 5) for i in step] if div_done(code) else None}
        adj_by[code] = (dates, adj, tr if div_done(code) else None)

    by = {it["code"]: it for it in items}

    def size_key(it):
        return (it["size"] is not None, it["size"] or 0, it["tv20"] or 0)

    top = {}
    for cat in ("配息型", "市值型"):
        pool = sorted((it for it in items if it["cat"] == cat), key=size_key, reverse=True)[:top_n]
        top[cat] = [it["code"] for it in pool]
    pop_holders = [it["code"] for it in sorted((it for it in items if it["d_holders"] is not None),
                                                key=lambda it: it["d_holders"], reverse=True)[:top_n]]
    pop_tv = [it["code"] for it in sorted(items, key=lambda it: it["tv20"] or 0, reverse=True)[:top_n]]
    hd = next((hold[c] for c in pop_holders if c in hold), {})

    # 行事曆：近 400 天到未來，每筆附當次殖利率（除息前一交易日收盤）
    cal = []
    close_by = {c: dict(zip(g["date"], pd.to_numeric(g["close"], errors="coerce"))) for c, g in px.groupby("code")}
    for r in divs.itertuples():
        if r.ex_date < since400 or r.code not in by:
            continue
        cb = close_by.get(r.code, {})
        before = [d for d in cb if d < r.ex_date]
        if r.ex_date <= latest and before:
            ref, basis = cb[max(before)], "除息前一日收盤"
        else:
            ref, basis = by[r.code]["close"], "最新收盤（尚未除息，估算）"
        fd, fw = fills_by.get(r.code, {}).get(r.ex_date, (None, None))
        cal.append({"code": r.code, "name": by[r.code]["name"], "ex": r.ex_date, "pay": r.pay_date,
                    "amt": round(float(r.amount), 4),
                    "y": round(float(r.amount) / ref, 5) if ref else None, "basis": basis,
                    "fill": fd, "fill_wait": fw})
    cal.sort(key=lambda x: (x["ex"], x["code"]))

    # 只送前五名會用到的走勢（整包 300 檔 × 十年週線太大）
    keep = set(sum(top.values(), [])) | set(pop_holders) | set(pop_tv)
    return {
        "asof": latest,
        "categories": CATEGORIES,
        "items": items,
        "top": top,
        "popular": {"holders": pop_holders, "turnover": pop_tv,
                    "holders_week": [hd.get("prev_date"), hd.get("date")]},
        "calendar": cal,
        "periods": periods,
        "series": {c: series[c] for c in keep if c in series},
        # 全部 ETF 的週線走勢（自選比較用）：build_payload 拆成 etf_series.json，前端要比較時才讀
        "series_all": series_grid(adj_by),
        "coverage": {"n": len(items), "div_done": sum(1 for it in items if it["div_done"]),
                     "div_rows": int(len(divs)), "px_done": sum(1 for it in items if it["px_done"]),
                     "holders": sum(1 for it in items if it["holders"] is not None)},
    }
