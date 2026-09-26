"""個股頁「AI 分析」卡的內容：技術面（分週期）＋籌碼面＋基本面＋消息面，四段各一個結論標籤。

Andy 2026-09-26（#stock/3026 禾伸堂）：「觀望部分需要標示 AI 分析，並且需要說明原因；
AI 分析是可以收納的選項，與多週期合併，裡面分析需要分不同時間週期的說明（只到週級別）
→ 這是技術面，需要有籌碼面、基本面、消息面看法」。

⚠ 誠實標示：這裡**沒有任何大型語言模型**。每一句都是下面寫死的規則＋payload 裡的數字組出來的，
同一份資料永遠產出同一段文字。前端標題寫「AI 分析」是 Andy 要的字樣，緊接著一定要有
「規則式自動判讀，非投資建議」—— 公開網站不能讓人以為這是 AI 模型給的投資建議。

規則的共同原則：
- **結論標籤只有三種**：偏多／中性／偏空（消息面多一個「留意」，見 news_facet）。
  每個面向各自打分、各自下標籤，**四個面向不加總成一個總分** —— 那樣會把「貴」跟「法人在買」
  互相抵銷成一個沒有意義的數字。綜合狀態（可留意／觀望／偏空）只看技術面的進出場條件，
  跟站上既有的判定（technical.evaluate 的 A／B／觀望／不要碰）一致。
- **每一條依據都帶數字**，資料缺就寫「資料缺」，不拿別的東西湊。
- **文字一律描述式或條件式**（「目前…」「若…則…」），不寫「建議買進／賣出」這類指示用語
  （證券投資信託及顧問法：未經許可不得對不特定人提供個股買賣建議）。
- 無未來函數：全部用 as_of 當天（含）以前的資料；新聞以 as_of 往回算 7／30 天。
"""
from __future__ import annotations

import re
from datetime import date, timedelta

TECH_TFS = (("60m", "1 小時"), ("240m", "4 小時"), ("1d", "日線"), ("1w", "週線"))
TREND_WORD = {1: "多頭", -1: "空頭", 0: "盤整"}
ALIGN_WORD = {1: "均線多頭排列", -1: "均線空頭排列", 0: "均線糾結"}
DIR_WORD = {1: "多", -1: "空"}

# 重大訊息主旨裡出現這些字，就在消息面標「留意」。這不是情緒判讀，只是把「會改變持有前提」的
# 公告類型挑出來（mops.py 的說明：減資、解散、訴訟、重大處分、財報更正都在重大訊息裡）。
WATCH_WORDS = ("減資", "解散", "訴訟", "處分", "更正", "重編", "違約", "退票", "跳票", "重整",
               "停工", "停業", "暫停交易", "終止上市", "下市", "查封", "裁罰", "假扣押", "背信", "掏空")

# 籌碼面門檻：法人買賣超佔同期成交量的比例。20 日 ±3% 以內視為「差距不大」——
# 大型股 20 日成交量動輒幾十萬張，法人賣超幾百張只是雜訊，用絕對張數比會把雜訊當方向。
INST_RATIO_20 = 3.0
INST_RATIO_5 = 5.0
HOLDER_WEEK_PP = 0.3      # 千張大戶一週變化 ≥ 0.3 個百分點才算有方向
MARGIN_PCT_20 = 10.0      # 融資 20 日增減 ≥ 10% 才算有方向


def _f(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def _n(x, nd=1, sign=False) -> str:
    v = _f(x)
    if v is None:
        return "—"
    return f"{v:+,.{nd}f}" if sign else f"{v:,.{nd}f}"


def _px(x) -> str:
    s = _n(x, 2)
    return s.rstrip("0").rstrip(".") if "." in s else s


def _label(score: float, hi: float = 1.0) -> tuple[str, int]:
    if score >= hi:
        return "偏多", 1
    if score <= -hi:
        return "偏空", -1
    return "中性", 0


def _md(d: str) -> str:
    """'2026-09-10' → '09-10'；分 K 的 '2026-09-10T09:00:00+08:00' → '09-10 09:00'。"""
    s = str(d or "")
    if "T" in s:
        return s[5:10] + " " + s[11:16]
    return s[5:10] if len(s) >= 10 else s


# ================================================================== 技術面

def _tf_line(tf: str, label: str, v: dict | None) -> dict:
    if not v:
        why = ("這檔目前沒有 60 分 K（不在分 K 名單，或還在回補）"
               if tf in ("60m", "240m") else "K 棒數不足，無法判讀")
        return {"tf": tf, "label": label, "trend": None, "word": "無資料", "points": [why]}
    t = int(v.get("trend") or 0)
    pts = [ALIGN_WORD.get(int(v.get("ma_align") or 0), "均線糾結")]
    mk = v.get("marks") or {}
    ch = [c for c in (mk.get("choch") or []) if isinstance(c, (list, tuple)) and len(c) >= 2]
    bos = list(mk.get("bos") or [])
    last_ch = ch[-1] if ch else None
    last_bos = bos[-1] if bos else None
    if last_ch and (not last_bos or str(last_ch[0]) >= str(last_bos)):
        pts.append(f"最近 CHoCH 翻{DIR_WORD.get(int(last_ch[1]), '?')}（{_md(last_ch[0])}）")
    elif last_bos:
        pts.append(f"最近 BOS（{_md(last_bos)}）")
    else:
        pts.append("近 60 根沒有 BOS／CHoCH")
    rsi = _f(v.get("rsi"))
    if rsi is not None:
        tag = "，偏熱" if rsi >= 70 else ("，偏冷" if rsi <= 30 else "")
        pts.append(f"RSI {rsi:.0f}{tag}")
    dm = (v.get("demand") or [None])[0]
    sp = (v.get("supply") or [None])[0]
    pts.append(f"需求區 {_px(dm['low'])}–{_px(dm['high'])}（距 {_n(dm.get('dist_pct'), 1, True)}%）"
               if dm else "下方沒有通過門檻的需求區")
    pts.append(f"供給區 {_px(sp['low'])}–{_px(sp['high'])}（距 {_n(sp.get('dist_pct'), 1, True)}%）"
               if sp else "上方沒有通過門檻的供給區")
    return {"tf": tf, "label": label, "trend": t, "word": TREND_WORD.get(t, "盤整"), "points": pts}


def tech_facet(verdict: dict | None, mtf_res: dict | None) -> dict:
    """技術面：1H／4H／日／週四行＋綜合狀態（可留意／觀望／偏空）與原因＋支撐壓力區。

    標籤（偏多／中性／偏空）看**結構**：週線 ±1、日線 ±1、1 小時 ±0.5，合計 ≥1.5 偏多、≤−1.5 偏空。
    綜合狀態看**進出場條件**（technical.evaluate 的判定），兩者是不同的問題：
    3026 可以「結構偏多」但「條件不齊，觀望」—— 那正是 Andy 要我們講清楚的情形。
    """
    v = verdict or {}
    tf_all = (mtf_res or {}).get("tf") or {}
    lines = [_tf_line(tf, lb, tf_all.get(tf)) for tf, lb in TECH_TFS]
    by = {ln["tf"]: ln for ln in lines}
    tr = {tf: by[tf]["trend"] for tf in by}
    if tr["1w"] is None and tr["1d"] is None:
        return {"label": "資料缺", "tone": 0, "why": "日線與週線都不足以判讀", "tfs": lines,
                "stance": "資料不足", "reasons": [], "ifs": [], "checks": None, "levels": {}}

    score = (tr["1w"] or 0) + (tr["1d"] or 0) + 0.5 * (tr["60m"] or 0)
    label, tone = _label(score, 1.5)
    struct = "、".join(f"{by[tf]['label']}{by[tf]['word']}" for tf in ("1w", "1d", "240m", "60m")
                       if by[tf]["trend"] is not None)

    ck = v.get("checks") or {}
    grade, vword = v.get("grade"), str(v.get("verdict") or "")
    reasons: list[str] = []
    ifs: list[str] = []
    risk_a = (ck.get("risk") or {}).get("a") or {}
    if grade in ("A", "B"):
        stance = "可留意"
        reasons.append("回檔型態的條件全部成立（A 級）" if grade == "A" else "突破型態的條件全部成立（B 級）")
        if v.get("weekly_note"):
            reasons.append(v["weekly_note"])
    elif vword.startswith("觀望（逆勢"):
        stance = "觀望"
        reasons.append(f"日線條件成立，但週線是空頭結構，屬逆勢反彈（{v.get('weekly_note') or ''}）".rstrip("（）"))
    elif vword == "不要碰" and (ck.get("exclusions") or []):
        stance = "偏空" if tr["1d"] == -1 else "觀望"
        reasons.append("觸發硬性排除條件：" + "；".join(ck["exclusions"][:3]))
    elif vword == "不要碰":
        stance = "偏空"
        reasons.append((ck.get("bear") or {}).get("text") or "日線空頭結構、MACD 柱為負、KD 死叉")
    else:
        stance = "觀望"
    if stance != "可留意" and ck:
        fa = [c for c in ck.get("a", []) if not c["ok"]]
        # 沒有需求區時「價格回到需求區」與「需求區多源交集」講的是同一件事，只留前一條
        if any(c["key"] == "in_demand" for c in fa) and not (v.get("demand") or []):
            fa = [c for c in fa if c["key"] != "zone"]
        fb = [c for c in ck.get("b", []) if not c["ok"]]
        reasons.append(f"回檔型態（A）{ck.get('n_a', 6)} 條中 {ck.get('met_a', 0)} 條成立；未成立："
                       + "；".join(f"{c['name']}——{c['text']}" for c in fa[:3]) if fa else
                       f"回檔型態（A）{ck.get('n_a', 6)} 條都成立")
        reasons.append(f"突破型態（B）{ck.get('n_b', 5)} 條中 {ck.get('met_b', 0)} 條成立；未成立："
                       + "；".join(f"{c['name']}——{c['text']}" for c in fb[:3]) if fb else
                       f"突破型態（B）{ck.get('n_b', 5)} 條都成立")
        if risk_a and not risk_a.get("ok"):
            reasons.append(f"停損距離過大：{risk_a.get('text')}（規則不縮停損去湊風報比）")
    # 週期衝突：大週期與小週期方向相反，是「觀望」最常見、也最該講出來的原因
    w = tr["1w"]
    if w:
        for tf in ("1d", "240m", "60m"):
            t = tr[tf]
            if t is not None and t == -w:
                reasons.append(f"週線{TREND_WORD[w]}，但{by[tf]['label']}仍是{TREND_WORD[t]}結構、尚未翻{DIR_WORD[w]}")

    # 若…則…：哪些事發生，狀態才會改變（描述條件，不是指示）
    ca = {c["key"]: c for c in ck.get("a", [])}
    cb = {c["key"]: c for c in ck.get("b", [])}
    dz = (v.get("demand") or [None])[0]
    if stance != "可留意" and ck:
        if ca.get("in_demand") and not ca["in_demand"]["ok"]:
            if dz:
                ifs.append(f"若價格回到日線需求區 {_px(dz['low'])}–{_px(dz['high'])}，且出現 KD 低檔金叉、"
                           "MACD 柱翻正或假跌破收回其中之一，回檔型態的位置與訊號條件才會補齊")
            else:
                ifs.append("日線下方目前沒有通過門檻的需求區；若之後形成（至少兩個來源交集），回檔型態才有位置依據")
        elif ca.get("trigger") and not ca["trigger"]["ok"]:
            ifs.append("價格已在需求區內；若出現 KD 低檔金叉、MACD 柱翻正或假跌破收回其中之一，確認訊號條件才會成立")
        if cb.get("breakout") and not cb["breakout"]["ok"]:
            ifs.append(f"若帶量（量比 ≥ 1.5）收盤站上前波高點，且 20 日乖離 ≤ 8%，突破條件才會成立"
                       f"（目前：{cb['breakout']['text']}）")
        elif cb.get("vol") and not cb["vol"]["ok"]:
            ifs.append(f"已站上前高；若量比回到 1.5 以上，突破的量能條件才會成立（目前：{cb['vol']['text']}）")
        if risk_a and not risk_a.get("ok") and risk_a.get("pct") is not None:
            ifs.append(f"若停損距離（目前 {risk_a['pct']:.1f}%）縮到 {risk_a.get('max', 8):.0f}% 以內"
                       "（例如價格回到離支撐較近的位置），風險條件才會通過")
    if v.get("stop") is not None:
        ifs.append(f"若收盤跌破 {_px(v['stop'])}，規則推算的停損位失守，目前的判讀前提不再成立")

    # 支撐壓力區：多週期的關鍵價位，只留到週線（月線不在技術面範圍內）
    kl = ((mtf_res or {}).get("summary") or {}).get("key_levels") or {}
    keep = {"60m", "240m", "1d", "1w"}
    levels = {"support": [z for z in kl.get("support", []) if z.get("tf") in keep],
              "resistance": [z for z in kl.get("resistance", []) if z.get("tf") in keep]}

    why = f"{struct}；進出場條件：{stance}"
    plan = None
    if v.get("stop") is not None and v.get("tp1") is not None:
        plan = (f"規則推算：停損 {_px(v['stop'])}"
                + (f"（距現價 {v['risk_pct']:.1f}%）" if _f(v.get("risk_pct")) is not None else "")
                + f"・目標 {_px(v['tp1'])}・風報比 {_n(v.get('rr'), 1)}")
    return {"label": label, "tone": tone, "why": why, "tfs": lines, "stance": stance,
            "reasons": reasons, "ifs": ifs, "plan": plan, "levels": levels,
            "checks": ({"a": ck.get("a", []), "b": ck.get("b", []),
                        "risk": ck.get("risk"), "met_a": ck.get("met_a"), "met_b": ck.get("met_b"),
                        "n_a": ck.get("n_a"), "n_b": ck.get("n_b")} if ck else None)}


# ================================================================== 籌碼面

def _dir(v: float, pos="買超", neg="賣超") -> str:
    return pos if v >= 0 else neg


def chip_facet(inst_v3: dict | None, margin: list | None, holders: list | None,
               avg_vol20: float | None) -> dict:
    """籌碼面：三大法人 5／20 日買賣超（張）、融資增減、集保千張大戶週變化。

    打分：法人 20 日淨額佔同期成交量 ≥3% → ±1；5 日同向且 ≥5% → 再 ±0.5；
    千張大戶一週 ±0.3pp → ±0.5；融資 20 日 +10%（籌碼往散戶走）→ −0.5、−10% → +0.5。
    合計 ≥1 偏多、≤−1 偏空。法人單位是「股」，一律 ÷1000 換成張。
    """
    pts: list[str] = []
    score = 0.0
    drivers: list[str] = []
    rows = (inst_v3 or {}).get("daily") or []
    vol = _f(avg_vol20)
    if rows:
        def tot(r):
            return sum((_f(x) or 0.0) for x in r[1:4])
        s5 = sum(tot(r) for r in rows[-5:]) / 1000
        s20 = sum(tot(r) for r in rows[-20:]) / 1000
        f20 = sum((_f(r[1]) or 0.0) for r in rows[-20:]) / 1000
        t20 = sum((_f(r[2]) or 0.0) for r in rows[-20:]) / 1000
        n20 = min(20, len(rows))
        r20 = r5 = None
        if vol and vol > 0:
            r20 = s20 / (vol / 1000 * n20) * 100
            r5 = s5 / (vol / 1000 * min(5, len(rows))) * 100
        pts.append(f"三大法人近 5 日{_dir(s5)} {abs(s5):,.0f} 張、近 {n20} 日{_dir(s20)} {abs(s20):,.0f} 張"
                   + (f"（佔同期成交量 {r20:+.1f}%）" if r20 is not None else ""))
        pts.append(f"外資 {n20} 日{_dir(f20)} {abs(f20):,.0f} 張、投信 {n20} 日{_dir(t20)} {abs(t20):,.0f} 張")
        if r20 is not None:
            if r20 >= INST_RATIO_20:
                score += 1; drivers.append(f"法人 {n20} 日淨買超佔成交量 {r20:.1f}%")
            elif r20 <= -INST_RATIO_20:
                score -= 1; drivers.append(f"法人 {n20} 日淨賣超佔成交量 {abs(r20):.1f}%")
            if r5 is not None and abs(r5) >= INST_RATIO_5 and (r5 > 0) == (r20 > 0) and abs(r20) >= INST_RATIO_20:
                score += 0.5 if r5 > 0 else -0.5
    else:
        pts.append("三大法人買賣超：資料缺")
    mg = [m for m in (margin or []) if isinstance(m, (list, tuple)) and len(m) >= 2 and _f(m[1]) is not None]
    if mg:
        bal = _f(mg[-1][1])
        b5 = _f(mg[-6][1]) if len(mg) >= 6 else None
        b20 = _f(mg[-21][1]) if len(mg) >= 21 else None
        txt = f"融資餘額 {bal:,.0f} 張"
        if b5 is not None:
            d5 = bal - b5
            txt += f"，近 5 日{'增加' if d5 >= 0 else '減少'} {abs(d5):,.0f} 張"
        if b20 is not None and b20 > 0:
            d20 = bal - b20
            p20 = d20 / b20 * 100
            txt += f"、近 20 日{'增加' if d20 >= 0 else '減少'} {abs(d20):,.0f} 張（{p20:+.1f}%）"
            if p20 >= MARGIN_PCT_20:
                score -= 0.5; drivers.append(f"融資 20 日增加 {p20:.0f}%")
            elif p20 <= -MARGIN_PCT_20:
                score += 0.5; drivers.append(f"融資 20 日減少 {abs(p20):.0f}%")
        pts.append(txt)
    else:
        pts.append("融資融券：資料缺")
    hd = [h for h in (holders or []) if isinstance(h, (list, tuple)) and len(h) >= 2 and _f(h[1]) is not None]
    if hd:
        h = _f(hd[-1][1])
        txt = f"千張大戶持股 {h:.2f}%（{_md(hd[-1][0])}）"
        if len(hd) >= 2:
            d1 = h - _f(hd[-2][1])
            txt += f"，較前一週 {d1:+.2f} 個百分點"
            if d1 >= HOLDER_WEEK_PP:
                score += 0.5; drivers.append(f"千張大戶一週 +{d1:.2f}pp")
            elif d1 <= -HOLDER_WEEK_PP:
                score -= 0.5; drivers.append(f"千張大戶一週 {d1:.2f}pp")
        if len(hd) >= 5:
            txt += f"、較 4 週前 {h - _f(hd[-5][1]):+.2f}"
        else:
            txt += f"（集保資料只有 {len(hd)} 週，還不能比 4 週變化）"
        pts.append(txt)
    else:
        pts.append("集保大戶：資料缺")
    if not rows and not mg and not hd:
        return {"label": "資料缺", "tone": 0, "why": "法人、融資、集保三項都沒有資料", "points": pts}
    label, tone = _label(score)
    why = "、".join(drivers[:2]) if drivers else "法人、融資、大戶的變化都不大，沒有明顯方向"
    return {"label": label, "tone": tone, "why": why, "points": pts[:4]}


# ================================================================== 基本面

METRIC_WORD = {"pe": "本益比", "pb": "股價淨值比", "ps": "股價營收比"}


def fund_facet(fx: dict | None, revenue: dict | None, profit: dict | None) -> dict:
    """基本面：本益比與同業分位、營收 YoY 近 3 個月、EPS 近四季。

    打分：近 3 個月 YoY 全正且平均 ≥10% → +1（全負且 ≤−10% → −1；其餘看平均的正負 ±0.5）；
    近四季 EPS 合計較前四季 ≥+10% → +1、≤−10% 或虧損 → −1；同業分位 ≥80% → −0.5、≤20% → +0.5。
    合計 ≥1 偏多、≤−1 偏空。
    """
    fx = fx or {}
    pts: list[str] = []
    score = 0.0
    drivers: list[str] = []
    metric = fx.get("metric") or "pe"
    mv = _f(fx.get("metric_value")) if fx.get("metric_value") is not None else _f(fx.get("pe"))
    if mv is not None:
        txt = f"{METRIC_WORD.get(metric, metric)} {mv:.1f} 倍"
        med, pct, n = _f(fx.get("group_median")), _f(fx.get("percentile")), fx.get("group_n")
        if med is not None and pct is not None:
            txt += f"，同族群（{fx.get('group_name') or '—'}，{n} 檔）中位 {med:.1f} 倍、分位 {pct:.0f}%"
            if fx.get("thin_sample"):
                txt += "（同族群樣本少，分位僅供參考）"
            if pct >= 80:
                score -= 0.5; drivers.append(f"{METRIC_WORD.get(metric, metric)}在同業分位 {pct:.0f}%，偏貴")
            elif pct <= 20:
                score += 0.5; drivers.append(f"{METRIC_WORD.get(metric, metric)}在同業分位 {pct:.0f}%，偏便宜")
        else:
            txt += "，同族群比較：資料缺"
        pts.append(txt)
    else:
        pts.append("本益比：資料缺" + ("（近四季虧損，本益比不適用）" if fx.get("is_loss") else ""))
    mo = [r for r in ((revenue or {}).get("monthly") or []) if isinstance(r, (list, tuple)) and len(r) >= 3]
    last3 = [r for r in mo[-3:] if _f(r[2]) is not None]
    if last3:
        ys = [_f(r[2]) for r in last3]
        avg = sum(ys) / len(ys)
        txt = "月營收 YoY 近 3 個月：" + "、".join(f"{r[0][2:]} {_f(r[2]):+.1f}%" for r in last3)
        if len(ys) >= 2:
            trend = "逐月走高" if all(b > a for a, b in zip(ys, ys[1:])) else \
                    "逐月走低" if all(b < a for a, b in zip(ys, ys[1:])) else "有高有低"
            txt += f"（{trend}）"
        streak = fx.get("rev_streak")
        if streak:
            txt += f"；連續 {int(streak)} 個月年增" if int(streak) > 0 else ""
        pts.append(txt)
        if len(ys) == 3 and all(y > 0 for y in ys) and avg >= 10:
            score += 1; drivers.append(f"營收近 3 月平均年增 {avg:.0f}%")
        elif len(ys) == 3 and all(y < 0 for y in ys) and avg <= -10:
            score -= 1; drivers.append(f"營收近 3 月平均年減 {abs(avg):.0f}%")
        elif avg > 0:
            score += 0.5
        elif avg < 0:
            score -= 0.5
    else:
        pts.append("月營收：資料缺")
    q = [r for r in ((profit or {}).get("quarters") or []) if isinstance(r, (list, tuple)) and len(r) >= 6
         and _f(r[5]) is not None]
    if len(q) >= 4:
        ttm = sum(_f(r[5]) for r in q[-4:])
        txt = "近四季 EPS：" + "、".join(f"{r[0]} {_f(r[5]):.2f}" for r in q[-4:]) + f"，合計 {ttm:.2f} 元"
        if len(q) >= 8:
            prev = sum(_f(r[5]) for r in q[-8:-4])
            if prev > 0:
                g = (ttm / prev - 1) * 100
                txt += f"（前四季 {prev:.2f} 元，{g:+.0f}%）"
                if g >= 10:
                    score += 1; drivers.append(f"近四季 EPS 較前四季 {g:+.0f}%")
                elif g <= -10:
                    score -= 1; drivers.append(f"近四季 EPS 較前四季 {g:+.0f}%")
            else:
                txt += f"（前四季 {prev:.2f} 元，無法算成長率）"
        if ttm <= 0:
            score -= 1; drivers.append(f"近四季 EPS 合計 {ttm:.2f} 元（虧損）")
        pts.append(txt)
    elif q:
        pts.append(f"EPS 只有 {len(q)} 季資料，湊不滿四季")
    else:
        pts.append("EPS：資料缺")
    if mv is None and not last3 and not q:
        return {"label": "資料缺", "tone": 0, "why": "估值、營收、EPS 三項都沒有資料", "points": pts}
    label, tone = _label(score)
    why = "、".join(drivers[:3]) if drivers else "營收、獲利、估值都沒有明顯偏離"
    return {"label": label, "tone": tone, "why": why, "points": pts[:4]}


# ================================================================== 消息面

def _mentions(n: dict, code: str, name: str) -> bool:
    """跟前端 newsAbout 同一套：標題／摘要提到代號（前後不是數字）或公司名（≥2 字）才算這檔的新聞。"""
    nm = re.sub(r"-(KY|創|DR)$", "", str(name or "").replace("*", ""), flags=re.I).strip()
    t = " ".join(str(n.get(k) or "") for k in ("title", "summary", "content", "desc"))
    if re.search(r"(^|\D)" + re.escape(str(code)) + r"(\D|$)", t):
        return True
    return len(nm) >= 2 and nm in t


def news_facet(news: list | None, material: list | None, as_of: str | None,
               code: str, name: str) -> dict:
    """消息面：近 7／30 天重大訊息與新聞則數、最新 3 則、主旨是否含警示字。

    **不做情緒打分**：本站沒有可靠的中文財經情緒來源，拿關鍵字硬判「利多／利空」會錯得很有自信。
    所以標籤只有「中性（僅列事件）」與「留意（重大訊息主旨含警示字）」兩種，並把這件事寫在畫面上。
    """
    try:
        ref = date.fromisoformat(str(as_of)[:10])
    except (TypeError, ValueError):
        ref = None

    def within(d, days):
        if ref is None:
            return True
        try:
            x = date.fromisoformat(str(d)[:10])
        except (TypeError, ValueError):
            return False
        return ref - timedelta(days=days) < x <= ref

    mine = [n for n in (news or []) if _mentions(n, code, name)]
    mat = list(material or [])
    m30 = [m for m in mat if within(m.get("date"), 30)]
    n30 = [n for n in mine if within(n.get("date"), 30)]
    m7 = [m for m in m30 if within(m.get("date"), 7)]
    n7 = [n for n in n30 if within(n.get("date"), 7)]
    flagged = []
    for m in m30:
        hit = [w for w in WATCH_WORDS if w in str(m.get("subject") or "")]
        if hit:
            flagged.append((m, hit))
    items = [{"date": m.get("date"), "title": m.get("subject") or "", "kind": "重大訊息",
              "clause": m.get("clause") or "", "url": None} for m in m30] + \
            [{"date": n.get("date"), "title": n.get("title") or "", "kind": "新聞",
              "source": n.get("source") or "", "url": n.get("url")} for n in n30]
    items.sort(key=lambda x: str(x.get("date") or ""), reverse=True)
    pts = [f"重大訊息：近 7 天 {len(m7)} 則、近 30 天 {len(m30)} 則（公司自己在公開資訊觀測站發的公告）",
           f"相關新聞：近 7 天 {len(n7)} 則、近 30 天 {len(n30)} 則（標題或內文提到本檔才算）"]
    if flagged:
        m, hit = flagged[0]
        pts.append(f"重大訊息主旨含「{'、'.join(hit)}」：{_md(m.get('date'))}「{m.get('subject')}」")
        label, why = "留意", f"近 30 天有 {len(flagged)} 則重大訊息主旨含警示字（{'、'.join(flagged[0][1])}）；僅列事件，未判讀情緒"
    elif not m30 and not n30:
        label, why = "中性", "近 30 天沒有這檔的公告或新聞；僅列事件，未判讀情緒"
    else:
        label, why = "中性", "僅列事件，未判讀情緒"
    return {"label": label, "tone": 0, "why": why, "points": pts, "items": items[:3],
            "counts": {"m7": len(m7), "m30": len(m30), "n7": len(n7), "n30": len(n30)}}


# ================================================================== 組合

def build(*, verdict: dict | None, mtf_res: dict | None, inst_v3: dict | None, margin: list | None,
          holders: list | None, fundamental: dict | None, revenue: dict | None, profit: dict | None,
          news: list | None, material_news: list | None, as_of: str | None, code: str, name: str,
          avg_vol20: float | None) -> dict:
    tech = tech_facet(verdict, mtf_res)
    ck = (verdict or {}).get("checks") or {}
    ra = (ck.get("risk") or {}).get("a") or {}
    if tech["stance"] == "觀望" and ck:
        brief = f"回檔型態 {ck.get('met_a', 0)}/{ck.get('n_a', 6)}、突破型態 {ck.get('met_b', 0)}/{ck.get('n_b', 5)} 條成立"
        if ra and not ra.get("ok") and ra.get("pct") is not None:
            brief += f"；停損距離 {ra['pct']:.1f}% 超過 {ra.get('max', 8):.0f}%"
    elif tech["reasons"]:
        brief = tech["reasons"][0]
    else:
        brief = tech["why"]
    return {
        "version": 1,
        "method": "規則式自動判讀",
        "as_of": as_of,
        "headline": {"stance": tech["stance"], "grade": (verdict or {}).get("grade"), "brief": brief},
        "facets": {
            "tech": tech,
            "chip": chip_facet(inst_v3, margin, holders, avg_vol20),
            "fund": fund_facet(fundamental, revenue, profit),
            "news": news_facet(news, material_news, as_of, code, name),
        },
    }
