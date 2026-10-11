"""第 3 版手機版逐鏡規格（框寬 1000×高 1480；內容比框高就慢慢往下滑；每鏡 2～3.5 秒，目標約 85 秒）。"""
from __future__ import annotations

import v3_cards as K
from v3_core import Focus4, Op, Rec4, Shot4
from v3_web import act, stat


def F(rect, label, clip, t_draw=0.5, **kw):
    return Focus4(rect, label=label, clip=clip, t_draw=t_draw, zoom=False, **kw)


def pan(ya, yb, D, t0=0.3):
    """慢慢往下滑：滑動時間佔鏡長約 60%（ease in/out）。"""
    return (ya, yb, t0, t0 + 0.6 * D)


PAN_LOG = []


def solve_pan(rec, op, D, pan_):
    """點擊目標必須在點下那一刻落在畫面框內：不在就調整捲動（先固定到含所有點擊的視窗，點完才慢慢滑）。"""
    from render_1010 import reader
    src = reader(rec.clip).get(0)
    sw, sh = src.size
    wh = 1480 * sw / 1000
    maxy = max(0, sh - wh)
    taps = [(tp["t"], tp["y"]) for tp in op.taps if not tp["hover"]]
    ya, yb, t0, t1 = pan_ or (0, 0, 0.3, 0.3)
    ya, yb = min(max(ya, 0), maxy), min(max(yb, 0), maxy)
    if not taps:
        return (ya, yb, t0, t1)

    def ok(tt, y):
        import math
        u = 0 if t1 <= t0 else min(1, max(0, (tt - t0) / (t1 - t0)))
        u = u * u * (3 - 2 * u)
        w0 = ya + (yb - ya) * u
        return w0 + 40 <= y <= w0 + wh - 40
    if all(ok(tt, y) for tt, y in taps):
        return (ya, yb, t0, t1)
    lo, hi = min(y for _, y in taps) - 70, max(y for _, y in taps) + 70
    if hi - lo > wh:
        lo = hi = taps[0][1]
        lo -= 70
        hi += 70
    w0 = min(max(lo - max(0, (wh - (hi - lo)) / 2) , 0), maxy)
    last = max(tt for tt, _ in taps)
    ya2 = w0
    yb2 = min(max(yb, 0), maxy)
    if yb2 > ya2 and all(w0 + 40 <= y <= yb2 + wh - 40 or True for _, y in taps):
        t0n = last + 0.55
        if t0n + 0.9 > D:
            yb2 = ya2
            t0n = D
        PAN_LOG.append((rec.clip, "調整", (ya, yb, t0, t1), (ya2, yb2, t0n, D - 0.15)))
        return (ya2, yb2, t0n, max(t0n + 0.9, D - 0.15))
    PAN_LOG.append((rec.clip, "靜止", (ya, yb, t0, t1), (ya2, ya2, 0.3, 0.9)))
    return (ya2, ya2, 0.3, 0.9)


def feat(sid, D, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), pan_=None, use_events=True):
    rec = Rec4(clip, srcmap, focus=focus, pan=pan_)
    op = Op(rec, idle=idle, extra=extra, use_events=use_events)
    rec.pan = solve_pan(rec, op, D, pan_)
    return Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def build():
    S = []
    S.append(card("01", 2.5, K.chaos_fn(), [(0, "pop")]))
    S.append(card("02", 2.0, K.tidy_fn("V01_mobile_v3b"), [(0, "swish"), (0.7, "ding")]))
    S.append(card("03", 3.5, K.intro_fn(), [(0, "pop"), (1.4, "ding")]))

    S.append(feat("04", 3.0, "V01_mobile_v3b", act(3.4, 3.0, 1.2, 0.8), "① 一頁看完今天", "一頁", "不用開 5 個 App，這頁就看完今天", "總覽",
                  focus=F((20, 720, 1150, 1650), "分段鈕與主圖", "V01_mobile_v3b", 0.4), idle="face_nod", pan_=pan(0, 900, 3.0)))
    S.append(feat("05", 2.5, "V02_mobile", act(2.0, 2.5, 1.0, 0.8), "今日事件不漏看", "不漏看", "國際、科技、總經消息排好了", "總覽",
                  idle="news", pan_=pan(0, 0, 2.5)))
    S.append(feat("06", 3.0, "V27_mobile", act(2.4, 3.0, 1.3, 0.8), "想看什麼，打幾個字就到", "打幾個字", "點搜尋，熱門股票和最近看過的先列給你", "搜尋",
                  focus=F((0, 0, 1170, 760), "搜尋框與下拉", "V27_mobile", 2.0), idle="face_wink"))
    S.append(feat("07", 3.0, "V27_mobile", [(0, 5.5), (3.0, 9.9)], "打代號或名稱", "代號", "打代號或名稱，點一下直接到那一頁", "搜尋",
                  idle=[(0, "face_wink"), (1.8, "talk_excited")]))
    S.append(feat("08", 3.0, "V03_mobile_v3b", [(0, 3.1), (0.7, 3.1), (0.7001, 9.9), (3.0, 12.2)], "② 大日子排一起", "大日子", "財報、法說、FED，一張月曆排好", "財經日曆",
                  idle="calendar", pan_=pan(0, 900, 3.0)))
    S.append(feat("09", 2.5, "V04_mobile_v3b", stat(2.5, 2.5), "③ 錢往哪裡跑", "錢", "族群在領先還是落後，一看就知道", "資金流向",
                  focus=F((110, 1400, 1060, 2280), "資金輪盤", "V04_mobile_v3b", 1.0), idle=[(0, "face_think"), (1.5, "talk_explain")], pan_=pan(600, 1000, 2.5)))
    S.append(feat("10", 2.5, "V05_mobile_v3b", [(0, 3.0), (2.5, 5.5)], "大盤的錢分去哪", "分去哪", "從大盤分到產業鏈、族群、代表股", "資金流向",
                  focus=F((40, 700, 1130, 2200), "分流樹", "V05_mobile_v3b", 1.2), idle="spotlight", pan_=pan(0, 800, 2.5)))
    S.append(feat("11", 2.0, "V07_mobile", stat(3.3, 2.0), "法人資金在哪", "法人", "法人的錢集中在哪，也整理好了", "資金流向",
                  idle="magnifier", pan_=pan(0, 700, 2.0)))
    S.append(feat("12", 2.5, "V08_mobile", stat(3.1, 2.5), "④ 哪裡熱一眼看", "一眼看", "越大成交越多，紅漲綠跌", "熱力圖",
                  idle=[(0, "magnifier"), (1.5, "face_star")], pan_=pan(0, 400, 2.5)))
    S.append(feat("13", 3.0, "V09_mobile", [(0, 3.1), (0.6, 3.1), (0.6001, 12.4), (3.0, 15.5)], "題材資金熱力", "題材", "題材熱度 0～100，資金、法人、新聞一起算", "熱力圖",
                  idle=[(0, "fire"), (2.0, "face_love")], pan_=pan(0, 900, 3.0)))
    S.append(feat("14", 2.5, "V11_mobile", [(0, 14.8), (2.5, 17.6)], "⑤ 2D 看產業鏈", "2D", "零件編號對說明，每段在做什麼都寫好", "產業地圖",
                  idle=[(0, "talk_explain"), (1.5, "face_nod")], pan_=pan(600, 1000, 2.5)))
    S.append(feat("15", 3.0, "V12a_mobile", [(0, 2.0), (3.0, 9.0)], "3D：AI 伺服器", "3D", "拖曳旋轉，整台機櫃一層一層看", "產業地圖",
                  idle="3dglasses", pan_=pan(700, 700, 3.0)))
    S.append(feat("16", 3.0, "V12e_mobile", act(3.9, 3.0, 1.0, 0.8), "零件是誰做的", "誰做的", "點零件，就知道哪家公司負責哪一層", "產業地圖",
                  idle="face_proud", pan_=pan(700, 800, 3.0)))
    S.append(card("17", 3.0, K.grid_fn(3.0, 1.9), [(0, "swish")]))
    S.append(card("18", 2.0, K.more_fn(), [(0.5, "pop")]))
    S.append(feat("19", 3.0, "V14_mobile", act(4.3, 3.0, 1.5, 0.8), "⑥ 個股一頁全有", "一頁全有", "K 線、多週期、營收、獲利、籌碼都在這", "個股",
                  idle="face_nod"))
    S.append(feat("20", 2.5, "V15_mobile", act(1.8, 2.5, 1.0, 0.8), "營收一眼看", "營收", "月營收、年增率，每個月都有", "個股", idle="face_nod"))
    S.append(feat("21", 2.5, "V15_mobile", act(7.4, 2.5, 1.0, 0.8), "法人動向", "法人", "三大法人買賣，資券、大戶散戶也在", "個股", idle="face_think"))
    S.append(feat("22", 2.5, "V16_mobile", act(3.4, 2.5, 1.3, 0.8), "⑦ 完整名單", "完整名單", "漲跌分佈、法人連買賣、排行都能排序", "市場明細",
                  idle="face_nod", pan_=pan(0, 400, 2.5)))
    S.append(feat("23", 2.5, "V17_mobile", act(6.6, 2.5, 1.0, 0.8), "⑧ 公開條件篩", "條件篩", "用公開條件篩一遍，省下自己翻的時間", "選股策略",
                  idle="face_think"))
    S.append(feat("24", 2.0, "V18_mobile", stat(3.3, 2.0), "⑨ 週期統計", "週期", "族群過去各月份表現，一張看完", "週期統計",
                  idle="hourglass", pan_=pan(0, 400, 2.0)))
    S.append(feat("25", 2.5, "V19_mobile_v3b", act(4.3, 2.5, 1.3, 0.8), "⑩ ETF 配息日曆", "配息日曆", "哪天除息、配多少，月曆寫好", "ETF",
                  idle="piggy", pan_=pan(0, 900, 2.5)))
    S.append(feat("26", 2.5, "V20_mobile", act(3.1, 2.5, 1.5, 0.8), "各類前五名", "前五名", "每一類最熱門、報酬、殖利率前五", "ETF",
                  idle="trophy", pan_=pan(0, 600, 2.5)))
    S.append(feat("27", 3.0, "V21_mobile_v3b", act(4.3, 3.0, 1.6, 0.8), "報酬放一起比", "一起比", "含息不含息，分開算給你看", "ETF",
                  idle="face_think", pan_=pan(0, 900, 3.0)))
    S.append(feat("28", 2.5, "V22_mobile", act(3.4, 2.5, 1.5, 0.8), "現金流試算", "現金流", "想每月都有配息？組合幫你排好", "ETF",
                  idle="calc", pan_=pan(0, 700, 2.5)))
    S.append(feat("29", 2.5, "V23_mobile", [(0, 1.0), (1.5, 2.5), (2.5, 5.5)], "複利看得到", "複利", "配息再投入差多少，三條線並排看", "ETF",
                  idle="growth", pan_=pan(0, 600, 2.5)))
    S.append(feat("30", 3.0, "V24_mobile", act(3.9, 3.0, 1.6, 0.8), "⑪ 存自己的股", "存自己", "想追蹤的股票存起來，打開就看到", "自選清單",
                  idle="star_save", pan_=pan(0, 300, 3.0)))
    S.append(feat("31", 2.5, "V25_mobile", act(2.0, 2.5, 1.5, 0.8), "看不懂？問比比", "問比比", "每頁都有導覽，右下角點我", "導覽", idle="face_wink"))
    S.append(feat("32", 2.5, "V26_mobile", act(13.2, 2.5, 1.0, 0.8), "一直在進步", "進步", "功能持續新增，想要什麼跟我說！", "願望清單",
                  idle="heart_wish", pan_=pan(0, 300, 2.5)))
    S.append(card("33", 3.0, K.benefits_fn(), [(0.3, "pop"), (0.65, "pop"), (1.0, "pop"), (1.35, "pop")]))
    S.append(card("34", 3.0, K.end_fn(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("35", 5.0, K.disclaimer_fn()))
    return S
