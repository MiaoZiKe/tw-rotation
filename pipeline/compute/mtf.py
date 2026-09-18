"""多週期（MTF）SMC：把 15 分、60 分、4 小時、日、週、月 各算一次結構與支撐壓力區，
再統整成一段「大週期怎麼看、小週期怎麼進」的說明。

技術分析專家的規則：
- 大週期（週 > 日）決定方向，小週期（4H > 1H > 15m）只負責找進場點。
  小週期的多頭結構在大週期空頭裡只是反彈，不是趨勢。
- 每個週期的區間都要通過 technical.sr_zones 的多源交集門檻（score ≥ 3、≥ 2 來源）。
- 「關鍵價位」= 距現價最近的需求區與供給區，各標明來自哪個週期；
  大週期的區間權重高：同一價位若日線與 15 分都有，以日線標示。
- 分 K 只有 Yahoo 給的兩年（60 分）/ 60 天（15 分），樣本不足時該週期就留白，不硬算。

★ 效能（2026-09-18）：部署那 866 秒幾乎全在 build_payload 的個股迴圈，而 build() 一檔要 180ms
（全市場 419 秒）是最大的一塊。這一版把「算兩次的」與「用 pandas 逐列跑的」都拿掉，
但輸出保證一個字都沒變 —— 護欄是 tests/test_perf_golden.py（固定 5 檔 × 700 根，比對整包輸出）。
改這個檔案之前先跑那支測試，改完再跑一次。哪裡快了、為什麼，都寫在各函式的註解裡。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .. import indicators as ind
from . import technical

log = logging.getLogger(__name__)

TF_ORDER = ["15m", "60m", "240m", "1d", "1w", "1M"]
TF_LABEL = {"15m": "15 分", "60m": "1 小時", "240m": "4 小時", "1d": "日線", "1w": "週線", "1M": "月線"}
BIG_TFS = ("1M", "1w", "1d")
SMALL_TFS = ("240m", "60m", "15m")
MIN_BARS = {"15m": 80, "60m": 80, "240m": 60, "1d": 60, "1w": 40, "1M": 24}


def _f(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ resample

def _bin_codes(dt: pd.Series, rule: str) -> np.ndarray | None:
    """算出「哪幾根屬於同一根週 K / 月 K」的分組碼，與 pandas resample(rule) 的分桶完全一致。

    為什麼要自己算：`.resample(...).agg(...)` 會把整段期間的桶（含中間沒有交易日的空桶）
    全部生出來再 dropna，而下面那句取「該期間最後一個交易日」的 `.apply(lambda ...)`
    更是一個桶跑一次 Python —— 700 根日 K 就要 153 次。兩者合計 23.7ms/檔，
    佔了 build() 的 12%。改成純整數運算之後只剩 ~2ms。

    分桶定義（跟 pandas 對過，見下方 fallback 的說明）：
    - MS：以「日曆月」分桶。datetime64[M] 轉 int64 就是「距 1970-01 的月數」，天生就是月份碼。
    - W-FRI：週 K 以週五收盤為一根，也就是「週六開始、下週五結束」。
      datetime64[D] 轉 int64 是「距 1970-01-01 的天數」，而 1970-01-01 是星期四，
      所以第一個星期六在 d=2；(d - 2) // 7 就是週次碼（numpy 的整數 // 會向下取整，
      1970 以前的負數日期也對）。
    其他 rule 回 None，交給下面的 pandas 原路徑處理（正確性優先）。
    """
    d = dt.to_numpy()
    if rule == "MS":
        return d.astype("datetime64[M]").astype("int64")
    if rule == "W-FRI":
        return (d.astype("datetime64[D]").astype("int64") - 2) // 7
    return None


def _group_bounds(codes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """由分組碼算出每一組的起點／終點索引（codes 必須是排好序的）。"""
    starts = np.flatnonzero(np.concatenate(([True], codes[1:] != codes[:-1])))
    ends = np.concatenate((starts[1:] - 1, [len(codes) - 1]))
    return starts, ends


def resample_daily(daily: pd.DataFrame, rule: str, *, _dt: pd.Series | None = None) -> pd.DataFrame:
    """日 K → 週 K（W-FRI）或月 K（MS）。

    `_dt` 是已經轉好的 datetime 欄（build() 會週線、月線共用同一份，省一次 to_datetime）；
    外部呼叫不用理它。
    """
    if daily is None or daily.empty:
        return pd.DataFrame()
    dt = pd.to_datetime(daily["date"]) if _dt is None else _dt
    fast = _resample_daily_fast(daily, dt, rule)
    if fast is not None:
        return fast
    return _resample_daily_pandas(daily, dt, rule)


def _resample_daily_fast(daily: pd.DataFrame, dt: pd.Series, rule: str) -> pd.DataFrame | None:
    """resample_daily 的快路徑：純 numpy。條件不滿足就回 None 走原本的 pandas 路徑。

    把關條件是為了「語意要跟 groupby 一模一樣」，不是為了防呆：
    - 日期必須遞增：下面用「相鄰分組碼不同就切一刀」找分組邊界，沒排序會切錯。
    - OHLC 必須是 float64：pandas 的 sum 對整數欄會回整數，dtype 會跟舊版不一樣。
    - open/close 不能有 NaN：groupby 的 first/last 會「跳過 NaN 取下一個」，
      而這裡是直接取該組的第一根／最後一根。有 NaN 就退回 pandas，不要自作聰明。
    - high/low 用 np.fmax/np.fmin（會忽略 NaN，跟 groupby 的 max/min 同義），
      volume 先把 NaN 當 0 再加總（等同 groupby sum 的 min_count=0）。
    """
    codes = _bin_codes(dt, rule)
    if codes is None or not dt.is_monotonic_increasing:
        return None
    cols = ["open", "high", "low", "close"] + (["volume"] if "volume" in daily else [])
    arr = {}
    for c in cols:
        a = daily[c].to_numpy()
        if a.dtype != np.float64:
            return None
        arr[c] = a
    if np.isnan(arr["open"]).any() or np.isnan(arr["close"]).any():
        return None

    starts, ends = _group_bounds(codes)
    out = {
        "open": arr["open"][starts],
        "high": np.fmax.reduceat(arr["high"], starts),
        "low": np.fmin.reduceat(arr["low"], starts),
        "close": arr["close"][ends],
    }
    if "volume" in arr:
        out["volume"] = np.add.reduceat(np.nan_to_num(arr["volume"], nan=0.0), starts)
    # 週 K／月 K 的日期一律用「該期間最後一個交易日」，前端 KUtil.resampleDaily 也是這樣標，
    # 兩邊必須一致。以前月線用 MS 規則停在月初（2026-09-01），前端卻標月底（2026-08-31），
    # 結果 chart.js 的 setMarkers 把月線的 BOS/CHoCH 全部過濾掉、供需區的 since 也對不上，
    # 而且是靜默失敗 —— 使用者只覺得「月線好像沒結構」。
    # （日期已遞增，所以「該組最後一根」就是該組的最大日期。）
    last_day = dt.to_numpy()[ends].astype("datetime64[D]").astype(str)
    return pd.DataFrame({"date": last_day, **out})


def _resample_daily_pandas(daily: pd.DataFrame, dt: pd.Series, rule: str) -> pd.DataFrame:
    """原本的 pandas 寫法，保留給快路徑擋掉的情況（非 W-FRI/MS、日期沒排序、有 NaN、整數欄）。"""
    d = daily.copy()
    d["date"] = dt
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in d:
        agg["volume"] = "sum"
    full = d.groupby(pd.Grouper(key="date", freq=rule), sort=True).agg(agg)
    out = full.dropna(subset=["close"]).reset_index()
    if rule.startswith("W") or rule.startswith("M"):
        last_day = d.groupby(pd.Grouper(key="date", freq=rule), sort=True)["date"].max()
        # 這裡刻意保留舊版的 `[:len(out)]`：真實資料不會有「整段期間 close 全是 NaN」的桶，
        # 兩邊長度一定一樣；真的出現的話也維持舊版行為，不在效能重構裡偷偷改語意。
        out["date"] = last_day.dropna().to_numpy()[: len(out)]
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    return out


def resample_intraday(bars: pd.DataFrame, rule: str = "240min") -> pd.DataFrame:
    """60 分 K → 4 小時 K。台股 09:00–13:30，以 09:00 為錨：09:00–13:00 一根、13:00–13:30 一根。"""
    if bars is None or bars.empty:
        return pd.DataFrame()
    d = bars.copy()
    d["ts"] = pd.to_datetime(d["ts"], utc=True).dt.tz_convert("Asia/Taipei")
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = (d.set_index("ts").resample(rule, origin="start_day", offset="9h")
             .agg(agg).dropna(subset=["close"]).reset_index())
    out["ts"] = _iso_with_offset(out["ts"])
    return out


def _iso_with_offset(ts: pd.Series) -> pd.Series:
    """帶時區的時間 → "2026-09-18T09:00:00+08:00"。

    原本是 `.dt.strftime("%Y-%m-%dT%H:%M:%S%z")` 再用 regex 把 "+0800" 補成 "+08:00"，
    兩步都是逐列跑 Python，400 根就要 2.8ms（佔 resample_intraday 的四成）。
    numpy 的 datetime64 轉字串本來就是 ISO 格式（中間就是 T），一次轉完再接上時區字串，
    同樣的輸出只要 0.5ms。台北固定 +08:00，但還是先驗「全部的位移都一樣」才走快路徑 ——
    萬一以後拿來處理有日光節約的時區，不要靜默算錯。
    """
    if ts.empty or ts.dt.tz is None:
        return ts.dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d{2})(\d{2})$", r"\1:\2", regex=True)
    off = ts.dt.tz_localize(None).to_numpy("datetime64[s]").astype("int64") - \
        ts.dt.tz_convert("UTC").dt.tz_localize(None).to_numpy("datetime64[s]").astype("int64")
    if not (off == off[0]).all():
        return ts.dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(r"(\d{2})(\d{2})$", r"\1:\2", regex=True)
    sec = int(off[0])
    sign = "+" if sec >= 0 else "-"
    suffix = f"{sign}{abs(sec) // 3600:02d}:{abs(sec) % 3600 // 60:02d}"
    body = ts.dt.tz_localize(None).to_numpy("datetime64[s]").astype(str)
    return pd.Series(np.char.add(body, suffix), index=ts.index)


# ------------------------------------------------------------------ 單一週期

def _marks(x: pd.DataFrame) -> dict:
    """最近 60 根的 BOS / CHoCH / 掃蕩日期清單（前端拿去在 K 線上標記）。

    原本這裡是四個 `.iterrows()`。iterrows 每一列都要生一個 object Series，
    在這個專案實測是 `to_numpy().tolist()` 的 35 倍慢 —— 這四行就佔 build() 的 5.6%。
    改成「布林遮罩挑出來再逐個 str()」。
    ★ 坑：不要用 `x["date"].to_numpy()[mask]`。date 欄可能是字串、也可能是 datetime64，
      而 numpy 的 datetime64 轉字串是 "2026-09-18T00:00:00.000000000"，
      iterrows 拿到的 Timestamp 轉字串卻是 "2026-09-18 00:00:00" —— 輸出會悄悄變掉。
      用 pandas Series 取值才跟舊版拿到同一種物件。
    """
    base = max(0, len(x) - 60)
    # 日期與 trend 各轉一次 Python list 就好（≤60 筆）。日期欄在 pandas 3 是 arrow 字串，
    # 每取一個值都要 arrow → Python 裝箱一次，四段遮罩各自取值會重複付這筆錢。
    # .tolist() 拿到的東西跟逐列取值一模一樣（字串還是 str、datetime 還是 Timestamp）。
    dates = x["date"].iloc[base:].tolist()
    trend = x["trend"].iloc[base:].tolist()

    def where(col: str) -> np.ndarray:
        s = x[col].iloc[base:]
        if s.dtype != bool:          # 已經是 bool 就不用 fillna（bool 欄裝不下 NaN，填了也是原值）
            s = s.fillna(False)
        return np.flatnonzero(s.to_numpy(dtype=bool))

    return {
        "bos": [str(dates[i]) for i in where("bos")],
        "choch": [[str(dates[i]), int(trend[i])] for i in where("choch")],
        "sweep_low": [str(dates[i]) for i in where("sweep_low")],
        "sweep_high": [str(dates[i]) for i in where("sweep_high")],
    }


def analyze_tf(bars: pd.DataFrame, tf: str, *, precomputed: pd.DataFrame | None = None) -> dict | None:
    """回傳該週期的結構、均線排列、需求/供給區。bars 需含 open/high/low/close（date 或 ts）。

    `precomputed`：已經算好的 `indicators.compute_all(bars)`（欄位與 lookback 都要對得上）。
    傳進來就不會再算一次 —— 日線那一份呼叫端本來就算過了，見 build() 的說明。
    """
    if bars is None or len(bars) < MIN_BARS.get(tf, 60):
        return None
    x = precomputed
    if x is not None and (len(x) != len(bars) or "close" not in x.columns):
        # 對不上就當作沒給。compute_all 不會增刪列，長度不同代表呼叫端傳錯了東西，
        # 這種時候寧可多算一次，也不要拿別份資料的指標去產結論。
        log.debug("%s 傳進來的指標對不上（%s vs %s 列），改為自己重算", tf, len(x), len(bars))
        x = None
    if x is None:
        df = bars
        if "date" not in df.columns and "ts" in df.columns:
            df = df.rename(columns={"ts": "date"})
        # 這裡原本先 `bars.copy()` 再取欄位 —— 多一次整張表的複製。
        # 取子欄位本來就會產生新表、compute_all 內部也還會 copy 一次，不會動到呼叫端的資料。
        cols = ["date", "open", "high", "low", "close"] + (["volume"] if "volume" in df else [])
        try:
            x = ind.compute_all(df[cols], structure_lookback=3 if tf in ("1w", "1M") else 2)
        except Exception as exc:  # noqa: BLE001
            log.debug("%s compute_all 失敗：%s", tf, exc)
            return None
    # 量過：整列抓一次（object Series）再 .get，比逐欄 x[c].iloc[-1] 抓 8 次還快一倍
    # —— 逐欄要付 8 次 DataFrame.__getitem__ ＋ 8 次 iloc，別「順手」改回去。
    last = x.iloc[-1]
    close = float(last["close"])
    atr_val = float(last.get("atr14") or np.nan)
    if not np.isfinite(atr_val) or atr_val <= 0:
        atr_val = close * 0.02
    demand, supply = technical.sr_zones(x, atr_val)

    def _z(z):
        return {"low": round(z.low, 2), "high": round(z.high, 2), "score": round(z.score, 1),
                "sources": z.sources, "kind": z.kind, "since": z.since,
                "width_pct": round(z.width_pct, 2),
                "dist_pct": round((z.mid / close - 1) * 100, 2)}

    return {
        "tf": tf, "label": TF_LABEL.get(tf, tf), "bars": int(len(x)),
        "close": close, "trend": int(last.get("trend") or 0),
        "ma_align": int(last.get("ma_align") or 0),
        "rsi": _f(last.get("rsi14")), "k": _f(last.get("k")), "d": _f(last.get("d")),
        "osc": _f(last.get("osc")), "atr": round(atr_val, 2),
        "demand": [_z(z) for z in demand], "supply": [_z(z) for z in supply],
        "marks": _marks(x),
        "last_bar": str(x["date"].iloc[-1]),
    }


# ------------------------------------------------------------------ 統整

def _trend_word(t: int) -> str:
    return {1: "多頭", -1: "空頭"}.get(t, "盤整")


def synthesize(per_tf: dict[str, dict], close: float) -> dict:
    """把各週期結論合成：大週期方向、小週期狀態、關鍵價位、操作腳本。"""
    have = {tf: v for tf, v in per_tf.items() if v}
    if not have:
        return {"big_trend": 0, "small_trend": 0, "headline": "資料不足，無法做多週期判定",
                "script": [], "key_levels": {"support": [], "resistance": []}, "tf_used": []}

    def _first(tfs):
        for tf in tfs:
            if tf in have:
                return tf, have[tf]
        return None, None

    big_tf, big = _first(("1w", "1d", "1M"))
    small_tf, small = _first(("60m", "240m", "15m"))
    no_intraday = small is None
    if no_intraday and big_tf == "1w" and "1d" in have:
        # 還沒有分 K：用「週線 vs 日線」當大小週期，不要假裝有小週期
        small_tf, small = "1d", have["1d"]
    big_t = big["trend"] if big else 0
    small_t = small["trend"] if small else 0

    # 關鍵價位：各週期最近的需求/供給，依距離排序，大週期優先去重
    sup, res = [], []
    for tf in ("1M", "1w", "1d", "240m", "60m", "15m"):
        v = have.get(tf)
        if not v:
            continue
        for z in v["demand"][:1]:
            sup.append({**z, "tf": tf, "label": TF_LABEL[tf]})
        for z in v["supply"][:1]:
            res.append({**z, "tf": tf, "label": TF_LABEL[tf]})

    scale = max(close, 1e-9)        # 迴圈裡原本每比一次就算一次 max()，提出來算一次就好

    def _dedupe(items, key):
        out = []
        for it in sorted(items, key=key):
            if any(abs(it["low"] - o["low"]) / scale < 0.01 for o in out):
                continue
            out.append(it)
        return out[:4]

    sup = _dedupe(sup, key=lambda z: -z["high"])           # 最靠近現價的支撐在前
    res = _dedupe(res, key=lambda z: z["low"])             # 最靠近現價的壓力在前

    big_word, small_word = _trend_word(big_t), _trend_word(small_t)
    big_label = TF_LABEL.get(big_tf, "大週期") if big_tf else "大週期"
    small_label = TF_LABEL.get(small_tf, "小週期") if small_tf else "小週期"

    script = []
    if big_t > 0 and small_t > 0:
        headline = f"{big_label}{big_word}、{small_label}同步{small_word}：順勢，等小週期回測需求區再承接"
        if sup:
            script.append(f"進場：價格回到 {sup[0]['label']} 需求區 {sup[0]['low']}–{sup[0]['high']}，"
                          f"且 15 分或 1 小時出現 CHoCH 翻多再進")
        if res:
            script.append(f"目標：先看 {res[0]['label']} 供給區 {res[0]['low']}–{res[0]['high']}")
        script.append("失效：小週期跌破最近需求區下緣且 4 小時結構轉空")
    elif big_t > 0 and small_t <= 0:
        headline = f"{big_label}{big_word}、{small_label}{small_word}：大方向沒變，小週期在修正，不追高、等修正結束"
        if sup:
            script.append(f"觀察：{sup[0]['label']} 需求區 {sup[0]['low']}–{sup[0]['high']} 是否守住")
        script.append("進場條件：小週期先出現 BOS 或 CHoCH 翻多，再回測不破才進")
        script.append("失效：日線需求區失守，改看空頭腳本")
    elif big_t < 0 and small_t > 0:
        headline = f"{big_label}{big_word}、{small_label}{small_word}：只是反彈，接近大週期供給區要減碼"
        if res:
            script.append(f"反彈上限：{res[0]['label']} 供給區 {res[0]['low']}–{res[0]['high']}")
        script.append("除非日線或週線出現 CHoCH 翻多，否則不做趨勢單")
    elif big_t < 0:
        headline = f"{big_label}{big_word}、{small_label}{small_word}：空頭，觀望"
        if sup:
            script.append(f"下方觀察：{sup[0]['label']} 需求區 {sup[0]['low']}–{sup[0]['high']}，跌破後才有掃蕩反轉機會")
        script.append("轉多條件：週線或日線 CHoCH + 站回 MA20 且量能放大")
    else:
        headline = f"{big_label}盤整：區間操作，需求區進、供給區出，沒有趨勢單"
        if sup and res:
            script.append(f"區間：{sup[0]['low']}–{res[0]['high']}（{sup[0]['label']} 需求 / {res[0]['label']} 供給）")
        script.append("突破區間並在小週期回測確認後，再依突破方向操作")

    if no_intraday:
        script.append("分 K（15 分 / 1 小時 / 4 小時）尚未取得，小週期暫以日線代替；分 K 於每日盤後由 Yahoo 補入")
    return {
        "big_tf": big_tf, "small_tf": small_tf, "no_intraday": no_intraday,
        "big_trend": big_t, "small_trend": small_t,
        "headline": headline, "script": script,
        "key_levels": {"support": sup, "resistance": res},
        "tf_used": [tf for tf in TF_ORDER if tf in have],
        "per_tf": {tf: {"trend": v["trend"], "ma_align": v["ma_align"], "rsi": v["rsi"]}
                   for tf, v in have.items()},
    }


def build(daily: pd.DataFrame, m60: pd.DataFrame | None, m15: pd.DataFrame | None,
          *, daily_ind: pd.DataFrame | None = None) -> dict:
    """輸入日 K 與（可選）60 分 / 15 分 K，輸出各週期分析 + 統整。

    `daily_ind`：呼叫端已經算好的 `indicators.compute_all(daily)`。
    build_payload 的個股迴圈每一檔都會先算一次日線指標，而這裡的 "1d" 週期又會
    「用同一份日 K、同一組欄位、同一個 structure_lookback=2」再算一次 —— 整份重複。
    把它傳進來就省掉一次（實際線上 1,500 根日 K 約 46ms/檔）。
    契約：必須是同一份 daily 算出來的 compute_all 結果（預設 lookback），列數要一樣；
    不傳就是自己算，行為與以前完全相同（護欄 test_perf_golden 走的就是不傳的那條路）。
    """
    per_tf: dict[str, dict | None] = {}
    per_tf["1d"] = analyze_tf(daily, "1d", precomputed=daily_ind)
    # 週線與月線都要把 date 轉成 datetime，轉一次共用（1,500 根日 K 轉一次約 1ms）
    dt = pd.to_datetime(daily["date"]) if daily is not None and not daily.empty else None
    per_tf["1w"] = analyze_tf(resample_daily(daily, "W-FRI", _dt=dt), "1w")
    per_tf["1M"] = analyze_tf(resample_daily(daily, "MS", _dt=dt), "1M")
    if m60 is not None and not m60.empty:
        per_tf["60m"] = analyze_tf(m60, "60m")
        per_tf["240m"] = analyze_tf(resample_intraday(m60, "240min"), "240m")
    if m15 is not None and not m15.empty:
        per_tf["15m"] = analyze_tf(m15, "15m")
    close = float(daily["close"].iloc[-1])
    return {"tf": {k: v for k, v in per_tf.items() if v}, "summary": synthesize(per_tf, close)}
