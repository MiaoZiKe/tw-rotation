"""前向模擬盤（紙上交易）：凍結第五輪「最接近的三組」，每天盤後用資料湖最新資料重算持股、換股訊號與模擬帳，
並同步計算 0050（還原含息、扣同樣成本）同期報酬，兩者並列。

只讀資料湖、不下單、不寫 data/、不接券商。參數凍結：FROZEN 之後不准改（tests/test_paper_lab5.py 會比對第五輪的
near_champions_pool200_only.csv，被改動會紅燈）。

設計：無狀態、可重現——每次都從固定起點（REPLAY_START）重放到資料湖最新一天，所以不需要保存持股檔，
排程重跑多少次結果都一樣。起點到 FORWARD_FROM 之前是「回放」，**只用來驗證流程跑得通，不算成績、不准拿來調參**；
FORWARD_FROM 之後（資料湖新增的交易日）才是前向成績。
成交：訊號用收盤、隔日開盤成交；成本同前幾輪（手續費 0.1425%x2、證交稅 0.3%、滑價 0.1%/邊）；不在窗尾清倉。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import swing_lab5 as S  # noqa: E402

OUT = ROOT / "docs" / "strategy_lab" / "paper"
REPLAY_START = "2026-01-02"          # 回放起點（只測流程）
FORWARD_FROM = "2026-10-23"          # 之後的資料才算前向成績（第五輪回測與回放的資料最後一天是 2026-10-22）
POOL = 200

# 第五輪「最接近的三組」（僅前 200 檔池成立，未達冠軍條件）。凍結，不得修改。
FROZEN = {
    "F1 風險調整動能+新高 N5 緩衝帶 季換股 廣度濾網": dict(N=5, buf=True, fam="riskmom", mf="br200", rebal="Q", withnh=True),
    "F2 新高動能+個股站上200日線 N15 季換股 廣度濾網": dict(N=15, above200=True, buf=False, fam="nh", mf="br200", nhmin=0.0, rebal="Q", withmom=True),
    "F3 新高動能+個股站上200日線 N10 季換股 廣度濾網": dict(N=10, above200=True, buf=False, fam="nh", mf="br200", nhmin=0.0, rebal="Q", withmom=True),
}
FROZEN["F3 新高動能+個股站上200日線 N10 季換股 廣度濾網"]["N"] = 10


def bench_equity(P, lo, hi):
    """0050 還原含息價，窗首開盤買進（手續費＋滑價），之後持有不賣（紙上帳不清倉，與策略同口徑）。"""
    idx = P["idx"]
    i0, i1 = idx.searchsorted(pd.Timestamp(lo)), idx.searchsorted(pd.Timestamp(hi), side="right") - 1
    return P["c50"].iloc[i0:i1 + 1] / P["o50"].iloc[i0] / (1 + S.SLIP) / (1 + S.FEE)


def is_signal_day(idx, t, quarterly=True):
    """t 是不是換股訊號日（該月／季最後一個交易日）。
    資料湖還沒有 t 的下一個交易日時，用「下一個營業日（只排除週末）跨月／季」判斷；遇到未預期的假日時，
    下一個交易日的重跑會以資料定義的訊號日為準（本函式只用來預告隔日要下的單）。"""
    freq = "Q" if quarterly else "M"
    nxt = idx[t + 1] if t + 1 < len(idx) else idx[t] + pd.offsets.BDay(1)
    return nxt.to_period(freq) != idx[t].to_period(freq)


def target_for(P, spec, s, held_idx):
    """在 s 日收盤後的目標持股（與 run_periodic 同一套規則，含大盤濾網與緩衝帶）。"""
    if not S.mkt_state(P, spec, s, POOL):
        return [], {}
    if spec.get("buf"):
        ranked, scs = S.pick(P, spec, s, POOL, nret=2 * spec["N"])
        keep = [i for i in ranked if i in held_idx][:spec["N"]]
        return keep + [i for i in ranked if i not in keep][:spec["N"] - len(keep)], scs
    return S.pick(P, spec, s, POOL)


def next_orders(P, name, spec, held_idx, t):
    """若 t（最新一天）是換股訊號日，列出明天開盤要賣／買的清單；否則說明下次換股日。"""
    idx = P["idx"]
    quarterly = spec["rebal"] == "Q"
    if is_signal_day(idx, t, quarterly):
        tgt, scs = target_for(P, spec, t, set(held_idx))
        rows = []
        for i in held_idx:
            if i not in tgt:
                rows.append(dict(策略=name, 動作="賣出", 代號=P["cols"][i], 理由="掉出目標名單或大盤濾網關閉" if tgt else "大盤濾網關閉，全部出清", 分數=np.nan))
        for i in tgt:
            if i not in held_idx:
                rows.append(dict(策略=name, 動作="買進", 代號=P["cols"][i], 理由="進入目標名單，隔日開盤等權買進", 分數=scs.get(int(i), np.nan)))
        for i in tgt:
            if i in held_idx:
                rows.append(dict(策略=name, 動作="續抱", 代號=P["cols"][i], 理由="仍在目標名單", 分數=scs.get(int(i), np.nan)))
        if not rows:
            rows.append(dict(策略=name, 動作="空手", 代號="", 理由="大盤濾網關閉或無合格標的", 分數=np.nan))
        return rows
    m = idx[t].to_period("Q" if quarterly else "M")
    return [dict(策略=name, 動作="無", 代號="", 理由=f"最新一天 {idx[t].date()} 不是換股訊號日；下一個訊號日＝{m.end_time.date()} 前後的最後一個交易日（收盤後產生、隔日開盤成交）", 分數=np.nan)]


def run_paper(P=None, end=None, replay_start=REPLAY_START, forward_from=FORWARD_FROM, out=OUT, specs=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    P = P or S.build_features(S.load5())
    specs = specs or FROZEN
    idx = P["idx"]
    end = pd.Timestamp(end) if end is not None else idx[-1]
    t = idx.searchsorted(end, side="right") - 1
    eq, ledger, holdings, orders, summ = {}, [], [], [], []
    for name, spec in specs.items():
        r = S.run_periodic(P, spec, POOL, replay_start, str(end.date()), trades=True, liquidate=False)
        eq[name] = r["eq"]
        if len(r["trades"]):
            ledger.append(r["trades"].assign(策略=name, 持有天數=(r["trades"]["exit"] - r["trades"]["entry"]).dt.days))
        last = r["eq"].iloc[-1]
        for code, h in r["held"].items():
            holdings.append(dict(策略=name, 代號=code, 進場日=h["entry"].date(), 進場價=round(h["entry_px"], 2), 最新收盤=round(h["last"], 2),
                                 未實現報酬=round(h["last"] / h["entry_px"] - 1, 4), 占權益=round(h["shares"] * h["last"] / last, 4)))
        held_cash = 1 - sum(x["占權益"] for x in holdings if x["策略"] == name)
        holdings.append(dict(策略=name, 代號="現金", 占權益=round(held_cash, 4)))
        orders += next_orders(P, name, spec, set(r["sh_idx"]), t)
    b = bench_equity(P, replay_start, str(end.date()))
    df = pd.DataFrame(eq).join(b.rename("0050 含息(扣成本)"))
    df["段"] = np.where(df.index < pd.Timestamp(forward_from), "回放(不算成績)", "前向(算成績)")
    df.round(5).to_csv(out / "equity.csv", encoding="utf-8-sig", index_label="date")
    pd.DataFrame(holdings).to_csv(out / "holdings_latest.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(orders).to_csv(out / "orders_next.csv", index=False, encoding="utf-8-sig")
    (pd.concat(ledger) if ledger else pd.DataFrame()).to_csv(out / "trades_ledger.csv", index=False, encoding="utf-8-sig")
    for name in list(specs) + ["0050 含息(扣成本)"]:
        s_ = df[name]
        fw = df[df["段"].str.startswith("前向")][name]
        mdd = float((s_ / s_.cummax() - 1).min())
        summ.append(dict(策略=name, 起點=str(df.index[0].date()), 最新=str(df.index[-1].date()), 回放期間報酬=float(s_[df["段"].str.startswith("回放")].iloc[-1] - 1),
                         全期報酬=float(s_.iloc[-1] - 1), 最大回撤=mdd,
                         前向交易日數=int(len(fw)), 前向報酬=(float(fw.iloc[-1] / s_[df["段"].str.startswith("回放")].iloc[-1] - 1) if len(fw) else np.nan)))
    sm = pd.DataFrame(summ)
    sm.to_csv(out / "summary.csv", index=False, encoding="utf-8-sig")
    md = ["# 前向模擬盤最新摘要（自動產生）", "", f"資料最新一天：{df.index[-1].date()}；回放起點 {replay_start}；前向從 {forward_from} 起算。",
          "**回放只測流程，不算成績；前向天數為 0 時沒有任何成績可言。**", "",
          "| 策略 | 回放期間報酬 | 全期報酬 | 最大回撤 | 前向交易日 | 前向報酬 |", "|---|---|---|---|---|---|"]
    f = lambda x: "-" if pd.isna(x) else f"{x*100:.1f}%"
    for r in sm.itertuples():
        md.append(f"| {r.策略} | {f(r.回放期間報酬)} | {f(r.全期報酬)} | {f(r.最大回撤)} | {r.前向交易日數} | {f(r.前向報酬)} |")
    (out / "latest_summary.md").write_text("\n".join(md), encoding="utf-8")
    return df, sm, pd.DataFrame(orders), pd.DataFrame(holdings)


if __name__ == "__main__":
    run_paper()
