"""「台指期策略」頁（#futures）的前端資料：只讀資料湖 paper/ledger，不另外抓任何資料。

> 免責：研究用，不是買賣建議，不會下單。

內容分兩塊：
  1. 前向模擬：F2（台指期 1.3 倍持有）與 BENCH（0050 含息）每天一列的帳本（pipeline/compute/live_signals.py 寫入，只增不改）。
     今日訊號取 F2 最後一列的 sig；績效曲線取 plan_cum（F2）與 bench_cum（0050 含息），都是「相對起始日的累積報酬」。
  2. 回測依據：策略委員會第三回合定案（分支 claude/elegant-fermi-scpgme 的
     docs/strategy_lab/council/r3_final.md 與 r3_results.csv）F0～F4 五列的結論數字。
     這是寫死的常數、不是每天重算（回測在已被看過的資料上，不會每天變）；改數字要改來源檔再同步這裡。

為什麼段落名跟任務單不一樣：來源檔的固定段是 A 2003-07～2014、B 2015～2020、C 2021 起、另附 2017～2020，
這裡照來源檔的定義寫，不自己改切法（改了就對不上 r3_results.csv）。
"""
from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

from pipeline.util import store

log = logging.getLogger(__name__)

T_LEDGER = "paper/ledger"
PLAN = "F2"
START = "2026-10-27"
DISCLAIMER = "研究用，不是買賣建議，不會下單。"

# 來源：r3_results.csv（a／b／c／d＝gap_A／gap_B／gap_C／gap_17-20，年化報酬贏同期含息 0050 幾個百分點；
#       roll5＝滾動 5 年窗口年化贏 0050 的比例（214 個窗口）；mdd／mdd09＝最大回撤（全期／2009 後））。
# 0050 含息同期全期年化 14.0%。
BACKTEST = {
    "source": "策略委員會第三回合 r3_final（統一口徑回測，2003-07 起）",
    "bench_cagr": 14.0,
    "segments": [
        {"k": "a", "t": "2003-07～2014"},
        {"k": "b", "t": "2015～2020"},
        {"k": "c", "t": "2021 起"},
        {"k": "d", "t": "2017～2020"},
    ],
    "rows": [
        {"id": "F0", "x": 1.0, "name": "1.0 倍", "a": 2.1, "b": -1.3, "c": -5.3, "d": -1.5, "cagr": 13.5, "roll5": 43, "worst5": -7.1, "mdd": -55, "mdd09": -30, "pmdd60": 3},
        {"id": "F1", "x": 1.2, "name": "1.2 倍", "a": 3.1, "b": 1.3, "c": -0.2, "d": 2.1, "cagr": 15.9, "roll5": 75, "worst5": -2.7, "mdd": -65, "mdd09": -35, "pmdd60": 12},
        {"id": "F2", "x": 1.3, "name": "1.3 倍（採用）", "a": 3.2, "b": 2.7, "c": 2.5, "d": 4.1, "cagr": 16.9, "roll5": 87, "worst5": -2.6, "mdd": -69, "mdd09": -39, "pmdd60": 17, "pick": True},
        {"id": "F3", "x": 1.5, "name": "1.5 倍", "a": 4.5, "b": 4.8, "c": 7.5, "d": 6.8, "cagr": 19.2, "roll5": 90, "worst5": -2.8, "mdd": -75, "mdd09": -46, "pmdd60": 31},
        {"id": "F4", "x": None, "name": "均線 1.5／1.0 倍", "a": 3.1, "b": 3.8, "c": 7.3, "d": 5.3, "cagr": 18.1, "roll5": 84, "worst5": -3.0, "mdd": -63, "mdd09": -35, "pmdd60": 11},
    ],
}


def _sig(raw: Any) -> dict:
    try:
        v = json.loads(raw) if isinstance(raw, str) else (raw or {})
        return v if isinstance(v, dict) else {}
    except (TypeError, ValueError):
        return {}


def build(ledger: pd.DataFrame | None = None) -> dict:
    """回傳 {signal, series, backtest, disclaimer}。帳本還沒有 F2 時 signal／series 為空（前端顯示「尚無」）。"""
    led = store.read(T_LEDGER) if ledger is None else ledger
    out: dict[str, Any] = {"plan": PLAN, "start": START, "backtest": BACKTEST, "disclaimer": DISCLAIMER, "signal": None, "series": []}
    if led is None or led.empty:
        return out
    led = led.copy()
    led["date"] = pd.to_datetime(led["date"]).dt.strftime("%Y-%m-%d")
    f2 = led[led["plan"] == PLAN].sort_values("date")
    if f2.empty:
        return out
    last = f2.iloc[-1]
    sg = _sig(last.get("sig"))
    out["signal"] = {
        "date": last["date"],
        "fut_close": sg.get("fut_close"),
        "target_x": sg.get("target_x", last.get("target")),
        "contracts_big": sg.get("contracts_big"),
        "contracts_micro": sg.get("contracts_micro"),
        "next_settle": sg.get("next_settle"),
        "next_check": sg.get("next_check"),
        "roll_tomorrow": bool(sg.get("roll_tomorrow")),
        "check_tomorrow": bool(sg.get("check_tomorrow")),
        "nav": float(last["nav"]),
    }
    # 績效曲線：F2 的 plan_cum ＝ 自己相對起始日的累積報酬；bench_cum ＝ 同期含息 0050（帳本裡每列都附）
    out["series"] = [
        {"d": r["date"], "f": round(float(r["plan_cum"]), 5), "b": round(float(r["bench_cum"]), 5), "nav": round(float(r["nav"]))}
        for _, r in f2.iterrows()
    ]
    return out
