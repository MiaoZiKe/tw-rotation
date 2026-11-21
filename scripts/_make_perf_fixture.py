"""產生「效能重構的護欄」：固定輸入 ＋ 現在這版的輸出。

為什麼要這支：2026-09-18 量出部署那 866 秒幾乎全在 `build_payload` 的個股那一圈，
其中 `mtf.build` 一檔就要 180ms（全市場 419 秒）。要把它改快，就一定要有辦法證明
**改快之後算出來的東西一模一樣** —— 不然就是拿正確性換速度，那不叫優化。

用法：
    python scripts/_make_perf_fixture.py          # 從資料湖重新產生 fixture 與 golden
    pytest tests/test_perf_golden.py -q           # 驗現在的程式跟 golden 一致

**只有在刻意要改變演算法時才可以重跑這支**（然後在 commit 訊息裡講清楚哪裡變了、為什麼）。
純粹是改快的重構，重跑等於把護欄拆了。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIX = ROOT / "tests" / "fixtures"
BARS = FIX / "perf_bars.json"
GOLD = FIX / "perf_golden.json"

N_CODES = 5
N_BARS = 700          # 約 2.8 年：1M 週期要 24 根月線，1w 要 40 根週線，這樣都夠


def pick(price: pd.DataFrame) -> dict[str, list]:
    """挑幾檔有完整歷史的股票，把日 K 存成固定輸入。"""
    cnt = price.groupby("code").size()
    codes = [c for c in cnt[cnt >= N_BARS].index.tolist() if c.isdigit() and len(c) == 4][:N_CODES]
    out = {}
    for c in codes:
        g = price[price["code"] == c].sort_values("date").tail(N_BARS)
        cols = ["date", "open", "high", "low", "close"] + (["volume"] if "volume" in g else [])
        rows = g[cols].to_numpy(dtype=object).tolist()
        for r in rows:
            r[0] = str(r[0])
        out[c] = rows
    return out


def daily_df(rows: list[list]) -> pd.DataFrame:
    cols = ["date", "open", "high", "low", "close", "volume"][:len(rows[0])]
    df = pd.DataFrame(rows, columns=cols)
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def fake_60m(df: pd.DataFrame) -> pd.DataFrame:
    """從日 K 推出一組「形狀合理」的 60 分 K。

    本機資料湖的 intraday_60m 是空的（那是雲端每天累積的），但 mtf 的 60m/240m 分支
    一定要被走到，不然護欄只擋得住一半。這裡用日 K 切成一天 5 根、開高低收在日內線性走，
    **完全決定性**（同樣的輸入永遠得到同樣的輸出），所以拿來當 golden 沒有問題。
    """
    out = []
    for _, r in df.tail(200).iterrows():
        o, h, l, c = float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])
        for i in range(5):
            f0, f1 = i / 5, (i + 1) / 5
            a = o + (c - o) * f0
            b = o + (c - o) * f1
            out.append({"ts": f"{r['date']} {9 + i:02d}:00:00", "open": a, "high": max(a, b, h if i == 2 else a),
                        "low": min(a, b, l if i == 3 else a), "close": b,
                        "volume": float(r.get("volume") or 0) / 5})
    return pd.DataFrame(out)


def outputs(bars: dict[str, list]) -> dict:
    from pipeline import indicators
    from pipeline.compute import mtf, scoring, technical
    got = {}
    for code, rows in bars.items():
        df = daily_df(rows)
        cols = [c for c in ("date", "open", "high", "low", "close", "volume") if c in df.columns]
        ind = indicators.compute_all(df[cols])
        last = ind.iloc[-1]
        verdict = technical.evaluate(ind, avg_turnover=1e8)
        got[code] = {
            "technical_score": indicators.technical_score(last),
            "verdict": verdict,
            "scoring": scoring.evaluate(last=last, ind=ind, verdict=verdict,
                                        base_tech=indicators.technical_score(last),
                                        inst=None, holders=None, broker=None, fx={}, avg_turnover=1e8),
            "mtf": mtf.build(df[cols], fake_60m(df), None),
            # 指標本身也釘住：compute_all 動到的話這裡會先亮
            "ind_tail": {c: [None if pd.isna(v) else float(v) for v in ind[c].tail(3)]
                         for c in ind.columns if c not in ("date",) and pd.api.types.is_numeric_dtype(ind[c])},
        }
    return got


def main() -> None:
    from pipeline.util import store
    price = store.read("price_daily")
    if price.empty:
        raise SystemExit("資料湖是空的，沒辦法產生 fixture")
    bars = pick(price)
    if not bars:
        raise SystemExit("找不到歷史夠長的股票")
    FIX.mkdir(parents=True, exist_ok=True)
    BARS.write_text(json.dumps(bars, ensure_ascii=False), encoding="utf-8")
    GOLD.write_text(json.dumps(outputs(bars), ensure_ascii=False, default=str, sort_keys=True),
                    encoding="utf-8")
    print(f"固定輸入：{BARS}（{len(bars)} 檔 × {N_BARS} 根）")
    print(f"現況輸出：{GOLD}（{GOLD.stat().st_size / 1024:.0f} KB）")


if __name__ == "__main__":
    main()
