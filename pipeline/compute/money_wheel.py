"""資金輪盤（成交值占比版）：和「強弱輪動」（rrg.py，價格相對大盤）並排、可切換的另一張盤。

★ 為什麼要有這一支（Andy 2026-10-30 拍板「改名＋再做真正資金輪盤」；依據 docs/research/20261030_rrg_audit.md A 節）：
  原本叫「資金輪盤」的那張圖，兩軸其實是族群**價格**相對大盤（rrg.py 的 RS-Ratio／RS-Momentum），
  成交值占比只拿來濾小族群與決定點的大小。它被改名為「強弱輪動」之後，
  「錢往哪個族群集中」需要一張真的用成交值占比畫的盤 —— 就是這一支。

口徑（細節與理由見 docs/research/20261030_money_wheel_spec.md）：
  · 水準 x ＝ 100 × 近 5 日平均占比 ÷ 近 20 日平均占比。100＝這個族群吃的成交值跟它自己的長期水準一樣；
    >100＝近期吃得比平常多（資金集中），<100＝比平常少。用「比值」而不是 flow.rotation_radar 的「差值（pp）」，
    是為了讓大族群（占比 20%）與小族群（占比 1%）的偏離可以放在同一張盤上比 ——
    差 1pp 對小族群是翻倍、對大族群只是 5%；比值才公平。差值版仍留在 flow.rotation_radar（熱力圖資金流向模式在用），不動它。
  · 動能 y ＝ 100 + 100 × (x 的今天 ÷ x 的 5 天前 − 1)。＝水準的 5 日變動率，中心 100：
    >100＝資金集中度還在往上、<100＝在往下。
  · 四象限沿用 rrg.quadrant_of（x、y 以 100 為界），位置幾何與強弱輪動完全相同，
    前端軌跡／腳印／時間軸回放／象限面板可以直接共用：領先＝集中（水準高、還在升）、改善＝升溫（水準低、動能向上）、
    轉弱＝退燒（水準高、動能轉下）、落後＝冷落（水準低、還在降）。

★ 誠實界線：成交值占比的變化跟價格是**同步**發生的，不是提前訊號
  （docs/research/20261030_flow_vs_price.md：隔夜 IC +0.006，不顯著）。這張盤回答「錢現在集中在哪」，不回答「接下來會漲」。

輸出格式刻意和 rrg.rrg() 的 points 一致（group_id／group_name／chain／x／y／quadrant／share／turnover／trail／live_state），
前端把它當成另一份 rrg 餵給同一組繪圖函式。

★ 不碰 rrg.py／flow.py 的權重與口徑（另一位同事在改）；這支只**讀** group_hist 的 turnover_share。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .rrg import _v, quadrant_of

SHORT = 5      # 水準分子：近幾日平均占比
LONG = 20      # 水準分母：近幾日平均占比（＝自身長期均值）
MOM = 5        # 動能：水準的幾日變動率


def money_axes(g: pd.DataFrame) -> pd.DataFrame:
    """在 `g`（欄位 group_id／date／turnover_share，已依 date 排序）上加 ms／ml／x／y 四欄。

    min_periods 用**滿窗**：窗口沒滿時均值只由少數幾天決定，比值會誇張，會把前端的正規化尺度撐開
    （同 rrg.rrg_axes 的理由）。歷史不足的族群寧可不畫。"""
    g = g.copy()
    gg = g.groupby("group_id")["turnover_share"]
    g["ms"] = gg.transform(lambda s: s.rolling(SHORT, min_periods=SHORT).mean())
    g["ml"] = gg.transform(lambda s: s.rolling(LONG, min_periods=LONG).mean())
    g["x"] = np.where(g["ml"] > 0, 100 * g["ms"] / g["ml"], np.nan)
    g["y"] = 100 + 100 * (g["x"] / g.groupby("group_id")["x"].shift(MOM) - 1)
    return g


def money_rrg(group_hist: pd.DataFrame, trail: int = 31, min_share: float = 0.3) -> dict:
    """資金輪盤的資料。trail 存 31 筆的理由同 rrg.rrg（前端拉Bar 最多 30 天前）。"""
    if group_hist is None or group_hist.empty:
        return {"points": [], "date": None, "kind": "money"}
    g = group_hist.sort_values("date").copy()
    g["date"] = g["date"].astype(str)
    g = money_axes(g)
    latest = g["date"].max()
    today = g[g["date"] == latest]
    keep = set(today[today["turnover_share"] >= min_share]["group_id"])
    points = []
    for gid, sub_all in g[g["group_id"].isin(keep)].groupby("group_id"):
        sub = sub_all.dropna(subset=["x", "y"]).tail(trail)
        if sub.empty or sub["date"].iloc[-1] != latest:
            continue
        last = sub.iloc[-1]
        x, y = float(last["x"]), float(last["y"])
        sh = sub_all["turnover_share"].tolist()
        points.append({
            "group_id": gid, "group_name": last["group_name"], "chain": last.get("chain"),
            "x": _v(x), "y": _v(y), "quadrant": quadrant_of(x, y),
            "share": _v(last["turnover_share"]), "turnover": _v(last["turnover"], 0),
            "trail": [[d, _v(a), _v(b)] for d, a, b in zip(sub["date"], sub["x"], sub["y"])],
            # 盤中即時續算用：前端拿到「今天這一刻的估算占比 s」就能接出今天那一點，
            #   x_new ＝ 100 × mean(sh_tail[-(SHORT-1):] + [s]) ÷ mean(sh_tail[-(LONG-1):] + [s])
            #   y_new ＝ 100 + 100 × (x_new ÷ x(5 天前) − 1)    x(5 天前)＝trail 倒數第 MOM 筆
            # 只送最近 LONG-1 筆占比（EMA 不需要，SMA 只要窗口內那幾筆）。
            "live_state": {"sh_tail": [_v(v, 4) for v in sh[-(LONG - 1):]]},
        })
    points.sort(key=lambda p: -(p["turnover"] or 0))
    return {"date": latest, "points": points, "trail_days": trail, "kind": "money",
            "live_params": {"short": SHORT, "long": LONG, "mom": MOM, "kind": "money"},
            "note": f"x＝近 {SHORT} 日平均成交值占比 ÷ 近 {LONG} 日平均占比（中心 100，>100＝資金集中）；"
                    f"y＝x 的 {MOM} 日變動率（中心 100）。與價格同步，不是提前訊號。"}
