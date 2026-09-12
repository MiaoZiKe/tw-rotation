"""候選名單的四個面向評分與「為何選它」理由。

Andy 的要求：候選名單要能用「綜合／籌碼／技術／基本面」分別篩選，而且每一檔都要
說得出「你為何選擇他」。所以這裡把散在各處的訊號整理成四個 0–100 的分數，
每個分數同時吐出人話理由（正面 pros、負面 cons），前端直接顯示。

設計原則：
- 資料不足就回 None，不要用 50 分硬湊 —— 前端顯示「—」比顯示假分數好。
- 理由必須寫出實際數字（「投信連買 5 天、合計 3,200 張」），不要寫「籌碼不錯」。
- 分數只是排序工具，不是買賣建議；技術面的買賣結論仍由 technical.evaluate 負責。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 綜合分的權重。某一面向缺資料時，剩下的面向按比例吃掉它的權重。
WEIGHTS = {"tech": 0.40, "chip": 0.30, "fund": 0.30}

FACETS = ("all", "chip", "tech", "fund")
FACET_LABEL = {"all": "綜合", "chip": "籌碼", "tech": "技術", "fund": "基本面"}


def _clip(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return float(min(max(v, lo), hi))


def _num(v):
    """把 NaN / None / 非數字統一成 None，其餘轉 float。"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def _lot(shares) -> str:
    """股數 → 張數字串（1 張 = 1000 股）。"""
    v = _num(shares)
    if v is None:
        return "—"
    return f"{v / 1000:,.0f} 張"


# ------------------------------------------------------------------ 技術面

def tech_score(last: pd.Series, ind: pd.DataFrame, verdict: dict,
               base: float) -> tuple[float, list[str], list[str]]:
    """技術面 0–100。base 是 indicators.technical_score 的輸出。"""
    s = float(base) * 0.65 + 17.5      # 先壓到 17.5–82.5，留空間給結構加減分
    pros: list[str] = []
    cons: list[str] = []

    grade = verdict.get("grade")
    if grade == "A":
        s += 14
        pros.append("技術判定 A 級：結構、位置、訊號、風報比四項都過")
    elif grade == "B":
        s += 9
        pros.append("技術判定 B 級：帶量突破前高，位置還不算追高")
    elif verdict.get("verdict", "").startswith("不要碰"):
        s -= 22
        cons.append("被硬性條件排除：" + (verdict.get("reasons") or ["條件不足"])[0])

    align = last.get("ma_align")
    if align == 1:
        s += 5
        pros.append("均線多頭排列（MA5 > MA20 > MA60 > MA120）")
    elif align == -1:
        s -= 8
        cons.append("均線空頭排列，反彈容易被壓回")

    close = _num(last.get("close"))
    ma60 = _num(last.get("ma60"))
    if close is not None and ma60 is not None:
        if close > ma60:
            s += 3
        else:
            s -= 5
            cons.append(f"收盤 {close:.1f} 在季線 {ma60:.1f} 之下")

    rr = _num(verdict.get("rr"))
    if rr is not None:
        s += _clip((rr - 1) / 2 * 8, -4, 8)
        if rr >= 2:
            pros.append(f"風報比 {rr:.1f}：停損 {verdict.get('stop'):.1f}、第一目標 {verdict.get('tp1'):.1f}")
        elif rr < 1.2:
            cons.append(f"風報比只有 {rr:.1f}，賺賠不划算")

    if bool(last.get("sweep_low")):
        s += 4
        pros.append("盤中破前低收回，是洗掉停損的假跌破")
    k, d = _num(last.get("k")), _num(last.get("d"))
    if k is not None and d is not None and k > d and k < 50:
        s += 4
        pros.append(f"KD 在低檔剛金叉（K={k:.0f}），還沒漲多")
    osc = _num(last.get("osc"))
    if osc is not None and len(ind) > 1:
        prev = _num(ind["osc"].iloc[-2])
        if prev is not None and prev <= 0 < osc:
            s += 4
            pros.append("MACD 柱由負轉正，動能剛翻多")

    vr = _num(last.get("vol_ratio"))
    if vr is not None and vr >= 1.5:
        s += 3
        pros.append(f"量比 {vr:.1f} 倍，有量在推")
    elif vr is not None and vr < 0.6:
        cons.append(f"量比只有 {vr:.1f} 倍，沒人氣")

    b20 = _num(last.get("bias20"))
    if b20 is not None and b20 > 12:
        s -= 6
        cons.append(f"20 日乖離 {b20:.0f}%，短線過熱")

    if len(ind) >= 60 and close is not None:
        hi60 = _num(ind["high"].tail(60).max())
        if hi60 is not None and close >= hi60:
            s += 3
            pros.append("收盤創 60 日新高")

    return _clip(s), pros, cons


# ------------------------------------------------------------------ 籌碼面

def _streak(series: pd.Series) -> int:
    """從最後一筆往回數，連續為正的天數。"""
    n = 0
    for v in reversed(series.tolist()):
        f = _num(v)
        if f is not None and f > 0:
            n += 1
        else:
            break
    return n


def chip_score(inst: pd.DataFrame | None, holders: list[dict] | None,
               broker: list[dict] | None, avg_turnover: float | None,
               close: float | None) -> tuple[float | None, list[str], list[str]]:
    """籌碼面 0–100。inst 是該檔近 60 日的法人買賣超（股數）。"""
    if inst is None or inst.empty or len(inst) < 5:
        return None, [], []
    df = inst.sort_values("date")
    pros: list[str] = []
    cons: list[str] = []
    s = 50.0

    trust = pd.to_numeric(df.get("trust"), errors="coerce").fillna(0)
    foreign = pd.to_numeric(df.get("foreign_total"), errors="coerce").fillna(0)
    dealer = pd.to_numeric(df.get("dealer"), errors="coerce").fillna(0)

    t5, f5 = float(trust.tail(5).sum()), float(foreign.tail(5).sum())
    t20, f20 = float(trust.tail(20).sum()), float(foreign.tail(20).sum())
    d5 = float(dealer.tail(5).sum())

    ts, fs = _streak(trust), _streak(foreign)
    if ts >= 3:
        s += min(ts, 8) * 2.2
        pros.append(f"投信連買 {ts} 天，5 日合計 {_lot(t5)}")
    elif ts == 0 and t5 < 0:
        s -= 6
        cons.append(f"投信 5 日賣超 {_lot(abs(t5))}")
    if fs >= 3:
        s += min(fs, 8) * 1.8
        pros.append(f"外資連買 {fs} 天，5 日合計 {_lot(f5)}")
    elif fs == 0 and f5 < 0:
        s -= 5
        cons.append(f"外資 5 日賣超 {_lot(abs(f5))}")

    # 法人 5 日淨買金額佔日均成交值的比例 —— 買超「相對於這檔的量」才有意義
    if avg_turnover and close:
        net_value = (t5 + f5 + d5) * float(close)
        ratio = net_value / (avg_turnover * 5)
        s += _clip(ratio * 100, -12, 18)
        if ratio > 0.08:
            pros.append(f"三大法人 5 日淨買約佔同期成交值 {ratio * 100:.0f}%，吃貨明顯")
        elif ratio < -0.08:
            cons.append(f"三大法人 5 日淨賣約佔同期成交值 {abs(ratio) * 100:.0f}%")

    if t20 > 0 and f20 > 0:
        s += 6
        pros.append("投信、外資 20 日同步站買方")
    elif t20 < 0 and f20 < 0:
        s -= 6
        cons.append("投信、外資 20 日同步站賣方")

    # 大戶（400 張以上）持股比例：近 4 週變化
    if holders and len(holders) >= 5:
        cur = _num(holders[-1].get("pct"))
        prev = _num(holders[-5].get("pct"))
        if cur is not None and prev is not None:
            diff = cur - prev
            s += _clip(diff * 6, -10, 12)
            if diff >= 0.3:
                pros.append(f"大戶持股 4 週增加 {diff:.1f} 個百分點（{prev:.1f}% → {cur:.1f}%）")
            elif diff <= -0.3:
                cons.append(f"大戶持股 4 週減少 {abs(diff):.1f} 個百分點（{prev:.1f}% → {cur:.1f}%）")

    # 券商目標價：近期有調升
    if broker:
        ups = [b for b in broker[:6] if str(b.get("action") or "").find("調升") >= 0]
        if ups:
            s += 5
            b0 = ups[0]
            tp = _num(b0.get("target_price"))
            pros.append(f"{b0.get('broker') or '券商'} 調升目標價"
                        + (f"至 {tp:.0f}" if tp else ""))

    return _clip(s), pros, cons


# ------------------------------------------------------------------ 基本面

def _scale(v: float | None, lo: float, hi: float) -> float | None:
    """把一個原始值線性映到 0–100（lo 以下 = 0，hi 以上 = 100）。"""
    if v is None:
        return None
    return _clip((v - lo) / (hi - lo) * 100)


# 基本面各成分的權重。缺的成分把權重讓給其他成分（跟綜合分同一個做法），
# 用加權平均而不是「50 分再逐項加」—— 加法會讓好股票全部擠在 95 分以上，排不出順序。
#
# 四個營收欄位（YoY、近三月 YoY、連增月數、動能分）講的其實是同一件事，
# 全給高權重等於把營收算四遍，估值與獲利品質就被稀釋掉了。
# 所以營收整塊佔 45%，估值分位 35%，ROE 20%。
FUND_WEIGHTS = {"yoy": 0.18, "yoy3m": 0.12, "streak": 0.07, "momentum": 0.08,
                "value": 0.35, "roe": 0.20}


def fund_score(fx: dict | None) -> tuple[float | None, list[str], list[str]]:
    """基本面 0–100，來源是 fundamental.py 算好的估值與營收動能。"""
    if not fx:
        return None, [], []
    pros: list[str] = []
    cons: list[str] = []
    parts: dict[str, float] = {}

    yoy = _num(fx.get("rev_yoy"))
    if yoy is not None:
        # YoY 超過 100% 多半是併購或一次性，超過的部分不再加分
        parts["yoy"] = _scale(min(yoy, 80.0), -20, 60)
        note = f"（{fx['rev_yoy_note']}）" if fx.get("rev_yoy_note") else ""
        if yoy >= 15:
            pros.append(f"{fx.get('rev_ym') or ''} 月營收 YoY +{yoy:.0f}%{note}")
        elif yoy <= -10:
            cons.append(f"{fx.get('rev_ym') or ''} 月營收 YoY {yoy:.0f}%{note}")
    if fx.get("rev_flag_spike"):
        cons.append("營收 YoY 超過 100%，可能是併購或一次性，不能直接當成長")

    streak = fx.get("rev_streak")
    if streak is not None:
        parts["streak"] = _scale(float(streak), 0, 12)
        if int(streak) >= 3:
            pros.append(f"月營收連續 {int(streak)} 個月 YoY 正成長")
    if fx.get("rev_record_high"):
        pros.append("最新月營收創歷史新高")

    yoy3 = _num(fx.get("rev_yoy_3m"))
    if yoy3 is not None:
        parts["yoy3m"] = _scale(min(yoy3, 70.0), -20, 55)

    mom = _num(fx.get("momentum_score"))
    if mom is not None:
        parts["momentum"] = _clip(mom)

    pct = _num(fx.get("percentile"))
    if pct is not None:
        parts["value"] = _clip(100 - pct)      # 分位越低＝相對同業越便宜
        metric = {"pe": "本益比", "pb_roe": "股價淨值比", "ps": "股價營收比"}.get(
            fx.get("metric"), "估值")
        n = fx.get("group_n")
        if pct <= 30:
            pros.append(f"{metric}在同族群第 {pct:.0f} 分位（{n or '—'} 檔比較），相對便宜")
        elif pct >= 80:
            cons.append(f"{metric}在同族群第 {pct:.0f} 分位，已經不便宜")
        if fx.get("thin_sample"):
            cons.append("同族群樣本太少，分位參考性有限")

    roe = _num(fx.get("roe"))
    if roe is not None:
        parts["roe"] = _scale(roe, 0, 30)
        if roe >= 15:
            pros.append(f"股東權益報酬率 {roe:.0f}%")

    if len(parts) < 2:
        return None, pros, cons

    total_w = sum(FUND_WEIGHTS[k] for k in parts)
    s = sum(parts[k] * FUND_WEIGHTS[k] for k in parts) / total_w

    if fx.get("is_loss"):
        s -= 18
        cons.append("近四季本業虧損，本益比無意義")
    if fx.get("ttm_complete") is False:
        s -= 4
        cons.append("最近四季財報還沒補齊，估值只能參考")

    return _clip(s), pros, cons


# ------------------------------------------------------------------ 綜合

def blend(tech: float | None, chip: float | None, fund: float | None) -> float | None:
    """綜合分：缺的面向把權重按比例讓給其他面向。"""
    parts = {"tech": tech, "chip": chip, "fund": fund}
    avail = {k: v for k, v in parts.items() if v is not None}
    if not avail:
        return None
    total_w = sum(WEIGHTS[k] for k in avail)
    return round(sum(avail[k] * WEIGHTS[k] for k in avail) / total_w, 1)


def evaluate(*, last: pd.Series, ind: pd.DataFrame, verdict: dict, base_tech: float,
             inst: pd.DataFrame | None, holders: list[dict] | None,
             broker: list[dict] | None, fx: dict | None,
             avg_turnover: float | None) -> dict:
    """一檔股票的四個面向分數 + 理由，直接塞進候選名單那一列。"""
    close = _num(last.get("close"))
    t, t_pro, t_con = tech_score(last, ind, verdict, base_tech)
    c, c_pro, c_con = chip_score(inst, holders, broker, avg_turnover, close)
    f, f_pro, f_con = fund_score(fx)
    a = blend(t, c, f)

    why = {
        "tech": {"pros": t_pro[:4], "cons": t_con[:3]},
        "chip": {"pros": c_pro[:4], "cons": c_con[:3]},
        "fund": {"pros": f_pro[:4], "cons": f_con[:3]},
    }
    # 綜合的理由：每個面向挑最強的一條，湊不滿就退回技術面
    top: list[str] = []
    for k in ("chip", "tech", "fund"):
        if why[k]["pros"]:
            top.append(why[k]["pros"][0])
    if not top:
        top = t_pro[:2] or [(verdict.get("reasons") or ["條件不足，只是相對排名靠前"])[0]]
    all_cons = c_con[:1] + t_con[:1] + f_con[:1]
    why["all"] = {"pros": top[:3], "cons": all_cons[:2]}

    return {
        "score_all": a, "score_chip": round(c, 1) if c is not None else None,
        "score_tech": round(t, 1), "score_fund": round(f, 1) if f is not None else None,
        "why": why,
    }
