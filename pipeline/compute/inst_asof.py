"""法人連買賣（inst_streak／trust_streak）與「當日法人」的資料日：只看法人表自己到齊了沒。

2026-11-09 事故：盤後貼文的「外資／投信個股買賣超排名」卡標 11-06，但法人表 11-09 已經有資料、
「個股三大法人」與同日的「法人買賣超日報」卡都標 11-09。
根因：build_payload 與 social_close_payload 把法人表用「價量最新交易日」（last_complete_date）整個切掉。
那天價量上市那一半沒進湖（openapi 還停在 11-06、mis 補抓失敗），價量只剩櫃買 1013 檔，
於是連帶把法人也切回 11-06。連買賣只用法人資料，不該借價量表的日期。

修法：資料日改由法人表自己決定 —— 近 10 個有法人資料的日子裡，上市檔數最多那天的 60% 以上才算「到齊」，
取最新一個到齊的日子。上市代號由價量表的 market 欄位對照（沒有 market 欄位就全部代號一起算）。
連買賣只保留「正好在這一天有資料」的代號，免得一檔 2014 年的舊資料混進今天的排行。
到不了最新一天時（例如 11-09 上市只有 456 檔、最多 1336 檔）→ 照實停在前一個到齊的日子，
並把原因寫進 reason，讓卡片與 inst_today 都講得出「為什麼是這一天」，不默默冒充最新。
"""
from __future__ import annotations

import pandas as pd

from . import flow

PRIMARY = "TWSE"     # 上市：跟 build_payload.last_complete_date 一樣，以上市為到齊的主要判準
COVER = 0.6          # 到齊門檻：近 N 日上市檔數最多那天的 60%
LOOKBACK = 10


def as_of(inst: pd.DataFrame, price: pd.DataFrame | None) -> dict:
    """回傳 {"date": 法人表到齊的最後一天（None＝沒有）, "last": 法人表最新一天, "n": 該天上市檔數,
    "n_max": 近 N 日上市檔數最多, "reason": 停在這一天的原因（到齊時為空字串）}。"""
    out = {"date": None, "last": None, "n": 0, "n_max": 0, "reason": ""}
    if inst is None or inst.empty:
        out["reason"] = "法人表沒有資料"
        return out
    dates = inst["date"].astype(str)
    out["last"] = str(dates.max())

    codes = None
    if price is not None and not price.empty and {"market", "code"} <= set(price.columns):
        pm = price[price["market"] == PRIMARY]
        if not pm.empty:
            codes = set(pm["code"].astype(str))
    sub = inst if codes is None else inst[inst["code"].astype(str).isin(codes)]
    cnt = (sub.assign(_d=sub["date"].astype(str)).groupby("_d")["code"].nunique()
           .sort_index().tail(LOOKBACK))
    if cnt.empty:
        out["reason"] = f"法人表近 {LOOKBACK} 日沒有{PRIMARY}資料"
        return out
    ref = int(cnt.max())
    ok = cnt[cnt >= COVER * ref]
    if ok.empty:
        out["n_max"] = ref
        out["reason"] = f"法人表近 {LOOKBACK} 日都沒到齊（最多 {ref} 檔）"
        return out
    d = str(ok.index[-1])
    out.update(date=d, n=int(cnt[d]) if d in cnt.index else 0, n_max=ref)
    if d != out["last"]:
        out["reason"] = (f"法人表 {out['last']} 的{PRIMARY}只有 {cnt.get(out['last'], 0)} 檔"
                         f"（近 {LOOKBACK} 日最多 {ref} 檔，未達 {COVER:.0%}），連買賣與當日法人停在 {d}")
    return out


def cut(inst: pd.DataFrame, asof: str | None) -> pd.DataFrame:
    """法人表裁到 asof（含）。asof 為空就原樣回傳。"""
    if inst is None or inst.empty or not asof:
        return inst
    return inst[inst["date"].astype(str) <= asof]


def streaks(inst_cut: pd.DataFrame, who: str, side: str, asof: str | None, min_days: int = 2) -> pd.DataFrame:
    """連買（賣）排行，只留「asof 當天有資料」的代號。

    flow.trust_streak 對每檔各算一次連續天數，最後一天可能是很久以前（例如 2014 年）。
    那種代號不是「今天還在連買」，留著會把舊資料當成今天的排行，所以這裡一律過濾掉。
    """
    df = flow.trust_streak(inst_cut, min_days=min_days, who=who, side=side)
    if df.empty or not asof:
        return df
    return df[df["date"].astype(str) == asof].reset_index(drop=True)
