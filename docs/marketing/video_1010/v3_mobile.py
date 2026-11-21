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


from v3_core import solve_pan as _solve_core, PAN_LOG, Lay, plan_dwell, seq_map, auto_map, plan_follow  # noqa: E402

_LM = Lay('mobile')


def solve_pan(rec, op, D, pan_):
    return _solve_core(rec, op, D, pan_, _LM)


def feat(sid, D, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), pan_=None, use_events=True, no_solve=False, chain=None, meta=None, top_only=False):
    rec = Rec4(clip, srcmap, focus=focus, pan=pan_)
    rec.meta = meta or {}
    rec.top_only = top_only
    op = Op(rec, idle=idle, extra=extra, use_events=use_events, chain=chain)
    D, dw = plan_dwell(rec, op, D, sub, _LM, pan_, chain, no_solve)
    _sh = Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)
    _sh.dwell = dw
    return _sh


def featp(sid, D, clip, ev_clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", pan_=None):
    """播放鏡頭：用 _v3c（60fps）素材原速，不凍結不丟格；點擊事件借用同鏡原檔的事件表。"""
    from v3_core import events_for
    rec = Rec4(clip, srcmap, focus=focus, pan=pan_)
    op = Op(rec, idle=idle, events=(events_for(clip) or events_for(ev_clip)))
    rec.pan = solve_pan(rec, op, D, pan_)
    _sh = Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)
    _sh.dwell = {"units": 1, "min_req": 2.35, "reading": 0, "D": D, "reached": True, "hold": 0.0, "note": "播放鏡頭（原速）", "ok": True}
    return _sh


def seqm(sid, clip, segs, head, hl, sub, pill, idle="talk_happy", focus=None):
    """連續點擊序列（快節奏，手機）。"""
    sm, D = seq_map(segs)
    rec = Rec4(clip, sm, focus=focus)
    op = Op(rec, idle=idle, chain="solo")
    rec.pan_keys = plan_follow(rec, op, _LM)
    sh = Shot4(sid, round(D, 2), [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)
    sh.dwell = {"units": 1, "min_req": 0, "reading": 0, "D": round(D, 2), "reached": True, "hold": 0.0, "note": "快節奏序列（Andy 指定）", "ok": True}
    return sh


def autom(sid, clip, win, head, hl, sub, pill, idle="talk_happy", focus=None, hold=1.6, top_only=False, ff=3.0):
    """依錄影端「點擊後內容區」自動排時間軸（手機）：點下→內容出現並入框→停留；內容高就慢滑到底。"""
    sm, D, meta = auto_map(clip, win, hold=hold, ff=ff)
    if not sm:
        raise ValueError(f'autom {sid} {clip} {win} 沒有點擊事件')
    return feat(sid, D, clip, sm, head, hl, sub, pill, focus=focus, idle=idle, meta=meta, top_only=top_only)


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def build():
    S = []
    S.append(card("01a", 2.8, K.chaos_fn(1), [(0, "pop")]))
    S.append(card("01b", 2.8, K.chaos_fn(2), [(0, "pop")]))
    S.append(card("01c", 2.8, K.chaos_fn(3), [(0, "pop")]))
    S.append(card("02", 2.5, K.tidy_fn("V01_mobile_v3b"), [(0, "swish"), (0.7, "ding")]))
    S.append(card("03", 3.5, K.intro_fn(), [(0, "pop"), (1.4, "ding")]))

    V1 = "V01_mobile_v3b"
    S.append(feat("04a", 3.0, V1, [(0, 2.4), (3.0, 5.4)], "① 一頁看完今天", "一頁", '我帶你逛總覽：四張卡左右滑，一眼看完', "總覽",
                  idle=[(0, 'talk_explain'), (1.6, 'face_nod')], pan_=pan(0, 0, 3.0)))
    S.append(feat("04b", 2.6, V1, [(0, 5.2), (2.6, 7.8)], "資金流向、熱度分頁", "分頁", '點分頁，資金和熱度我幫你切好', "總覽",
                  idle=[(0, 'face_think'), (1.5, 'face_relief')], pan_=pan(0, 0, 2.6)))
    S.append(feat("04c", 2.4, V1, [(0, 7.4), (2.4, 9.8)], "加權、櫃買、台指期", "三條走勢", '加權、櫃買、台指期，點一下就切換', "總覽",
                  idle=[(0, 'talk_happy'), (1.3, 'face_nod')], pan_=pan(0, 0, 2.4)))
    S.append(feat("04d", 3.0, V1, stat(11.0, 3.0), "走勢圖慢慢看", "走勢", '走勢圖我慢慢給你看，昨收線也標好了', "總覽",
                  focus=F((24, 900, 1146, 2100), "走勢圖", V1, 1.6), idle=[(0, 'magnifier'), (1.5, 'face_star')], pan_=pan(0, 700, 3.0)))
    S.append(feat("04e", 3.0, V1, stat(12.0, 3.0), "漲跌家數分佈", "漲跌家數", '漲跌幾家？分佈圖讓你一眼看懂', "總覽",
                  focus=F((24, 2330, 1146, 3590), "漲跌家數長條圖", V1, 2.3), idle=[(0, 'face_surprise_happy'), (1.5, 'face_nod')], pan_=pan(700, 2018, 3.0)))
    S.append(feat("05", 2.5, "V02_mobile", act(2.0, 2.5, 1.0, 0.8), "今日事件不漏看", "不漏看", '國際、科技消息，我幫你按時間排好', "總覽",
                  idle=[(0, 'news'), (1.3, 'face_relief')], pan_=pan(0, 0, 2.5)))
    S.append(feat("06", 3.0, "V27_mobile", act(2.4, 3.0, 1.3, 0.8), "想看什麼，打幾個字就到", "打幾個字", '想找哪一檔？熱門和最近看過的我先列給你', "搜尋",
                  focus=F((0, 0, 1170, 760), "搜尋框與下拉", "V27_mobile", 2.0), idle=[(0, 'magnifier'), (1.6, 'face_wink')]))
    S.append(feat("07", 3.0, "V27_mobile", [(0, 5.5), (3.0, 9.9)], "打代號或名稱", "代號", '打代號或名稱，點一下我就帶你去', "搜尋",
                  idle=[(0, 'talk_excited'), (1.7, 'face_nod')]))
    M3 = "V03b_mobile_v3f"
    M3 = "V03b_mobile_v3f"
    S.append(autom("03a", M3, (3.6, 5.2), "② 財報日，月曆看完", "財報日", "哪天誰要公布財報，我排在一張月曆；點一家看說明", "財經日曆",
                   idle=[(0, "calendar"), (1.5, "face_shock")]))
    S.append(autom("03c", M3, (13.9, 15.3), "公司法說也在這", "法說", "切到公司法說，哪天誰要開，我幫你排好", "財經日曆",
                   idle="face_curious"))
    S.append(autom("03d", M3, (18.8, 20.2), "點一場，重點展開", "點一場", "法說的重點和圖表，我幫你攤開給你看", "財經日曆",
                   idle=[(0, "talk_explain"), (1.5, "face_nod")]))
    S.append(autom("03e", M3, (28.9, 30.4), "FED 消息", "FED", "再切到 FED 消息，CPI、FOMC 都在這", "財經日曆",
                   idle="globe"))
    S.append(autom("03f", M3, (33.9, 35.4), "數值與預期", "數值", "點一則，數值和說明我整理好，不用自己查", "財經日曆",
                   idle=[(0, "face_proud"), (1.6, "face_nod")]))
    pass
    pass
    pass
    pass
    pass
    S.append(feat("03g", 2.0, M3, [(0, 51.6), (2.0, 53.6)], "往下滑看完整頁", "整頁", "清單和本週重點，我慢慢滑給你看", "財經日曆",
                  idle="news", pan_=pan(0, 0, 2.0)))
    S.append(feat("09", 2.5, "V04_mobile_v3b", stat(2.5, 2.5), "③ 錢往哪裡跑", "錢", '我幫你看資金往哪裡跑', "資金流向",
                  focus=F((110, 1400, 1060, 2280), "資金輪盤", "V04_mobile_v3b", 1.0), idle=[(0, 'face_curious'), (1.3, 'face_love')], pan_=pan(600, 1000, 2.5)))
    S.append(featp("09b", 3.6, "V04_mobile_v3c", "V04_mobile", [(0, 3.6), (3.6, 7.2)], "按播放，輪盤就動起來", "播放", '按下播放鍵，我播給你看', "資金流向",
                   idle=[(0, 'coins'), (1.5, 'face_star')]))
    S.append(feat("10", 2.5, "V05_mobile_v3b", [(0, 3.0), (2.5, 5.5)], "大盤的錢分去哪", "分去哪", '大盤的錢分到哪？我一路追到代表股', "資金流向",
                  idle=[(0, 'spotlight'), (1.3, 'face_think')], pan_=pan(300, 1500, 2.5)))
    S.append(featp("10b", 3.6, "V06_mobile_v3c", "V06_mobile", [(0, 3.6), (3.6, 7.2)], "分流樹也能播放", "▶", '分流樹也能播，一路看到代表股', "資金流向",
                   idle=[(0, 'talk_explain'), (1.6, 'face_proud')]))
    S.append(feat("11", 2.0, "V07_mobile", stat(3.3, 2.0), "法人資金在哪", "法人", '法人的錢集中在哪，我也整理好了', "資金流向",
                  idle=[(0, 'magnifier'), (1.0, 'face_nod')], pan_=pan(0, 700, 2.0)))
    S.append(feat("12", 2.5, "V08_mobile", stat(3.1, 2.5), "④ 哪裡熱一眼看", "一眼看", '哪裡熱？整個台股我幫你畫成一張圖', "熱力圖",
                  idle=[(0, 'magnifier'), (1.4, 'face_star')], pan_=pan(0, 400, 2.5)))
    M7 = "V07b_mobile_v3g"
    S.append(seqm("13s", "I01_mobile_v3i", [(3.2, 4.9, 1.0), (4.9, 6.5, 2.5), (6.5, 14.6, 1.35)], "上中下游，一路看到底", "一路", "上中下游，一路看到底", "熱力圖",
                  idle=[(0, "fire"), (1.5, "pointer_r"), (2.6, "face_curious"), (3.7, "magnifier"), (4.8, "face_think"), (5.9, "face_proud")]))
    pass
    pass
    pass
    pass
    pass
    S.append(feat("14", 2.5, "V11_mobile", [(0, 14.8), (2.5, 17.6)], "⑤ 2D 看產業鏈", "2D", '圓圈編號對到說明卡，我一段一段講給你', "產業地圖",
                  idle=[(0, 'face_nod'), (1.5, 'talk_happy')], pan_=pan(600, 1000, 2.5)))
    S.append(seqm("14s", "I04_mobile_v3i", [(0.8, 1.6, 1.0), (1.6, 7.6, 1.5)], "產業鏈連著選", "連著選", "半導體、AI 伺服器、一般電子、金融，一個一個切給你看", "產業地圖",
                  idle=[(0, "face_wink"), (1.2, "pointer_r"), (2.4, "face_curious"), (3.6, "face_star")]))
    S.append(feat("15", 3.0, "V12a_mobile", [(0, 2.0), (3.0, 9.0)], "3D：AI 伺服器", "3D", '拖一下就能轉，整台機櫃我幫你拆開給你看', "產業地圖",
                  idle=[(0, '3dglasses'), (1.6, 'face_star')], pan_=pan(700, 700, 3.0)))
    S.append(feat("16", 3.0, "V12e_mobile", act(3.9, 3.0, 1.0, 0.8), "零件是誰做的", "誰做的", '點零件，我告訴你哪家公司負責哪一層', "產業地圖",
                  idle=[(0, 'face_proud'), (1.8, 'face_nod')], pan_=pan(700, 800, 3.0)))
    S.append(card("17", 3.0, K.grid_fn(3.0, 1.9), [(0, "swish")]))
    S.append(card("18", 2.5, K.more_fn(), [(0.5, "pop")]))
    D1, D2M, D5M, D6M, D7M, D8M, D9M = ("D01_mobile_v3d", "D02_mobile_v3d", "D05_mobile_v3d", "D06_mobile_v3d", "D07_mobile_v3d", "D08_mobile_v3h", "D09_mobile_v3h")
    # 個股頁（Andy 退件重排）：K 線區 → 分頁列由左到右；每個分頁只留一個重點圖表鏡（內容高就只看上段，不再滑到底）
    S.append(autom("h01", D1, (1.0, 9.4), "⑥ 個股一頁全有", "一頁全有", "打幾個字，點建議，我帶你進個股頁", "個股",
                   idle=[(0, "face_wink"), (1.6, "talk_happy")], top_only=True, ff=5.0, hold=1.5))
    S.append(feat("h02", 2.2, D6M, stat(16.2, 2.2), "先看報價和 K 線", "K 線", "最上面是報價和 K 線，先看這張", "個股",
                  focus=F((0, 0, 1, 1), "個股走勢卡", D6M, 0.4), idle="face_nod", pan_=(250, 250, 0.3, 0.3)))
    S.append(autom("h03", D6M, (7.0, 8.4), "切週期，K 線立刻換", "切週期", "切週期，K 線我立刻幫你換", "個股",
                   idle=[(0, "face_star"), (1.2, "face_proud")], top_only=True, hold=1.5))
    _i = feat("h04", 2.8, D6M, [(0, 18.07), (2.8, 20.87)], "指標一鍵加上去", "指標", "指標設定點進去，要看哪個就打勾", "個股",
              idle=[(0, "magnifier"), (1.4, "face_think")], pan_=(200, 200, 0.3, 0.3), no_solve=True)
    _i.rec.pan_keys = [(0.0, 200), (1.1, 200), (1.9, 800), (2.8, 800)]
    _i.dwell["note"] = "點下設定後視窗下移看底部面板"
    S.append(_i)
    S.append(autom("h05", D7M, (0.9, 2.4), "基本資料", "基本資料", "公司基本資料，我幫你整理好", "個股",
                   idle="folder", top_only=True, hold=1.5))
    S.append(autom("h06", D8M, (12.8, 14.4), "營收：月營收長條與年增率", "營收", "月營收長條加年增率，每個月我幫你畫好", "個股",
                   idle=[(0, "piggy"), (2.0, "face_proud")], top_only=True, hold=1.5, ff=5.0))
    S.append(autom("h07", D9M, (12.8, 14.4), "獲利：EPS 與毛利率", "獲利", "EPS 和毛利率的變化，我整理在同一張圖", "個股",
                   idle=[(0, "calc"), (2.0, "face_think")], top_only=True, hold=1.5, ff=5.0))
    S.append(autom("h08", D1, (17.3, 18.8), "總覽：基本面", "基本面", "EPS、ROE、本益比，基本面我幫你抓重點", "個股",
                   idle="face_think", top_only=True, hold=1.5))
    S.append(autom("h09", D1, (23.2, 24.7), "總覽：籌碼快照", "籌碼快照", "法人、集保、信用、當沖，一次給你看", "個股",
                   idle="magnifier", top_only=True, hold=1.5))
    S.append(autom("h10", D1, (29.1, 30.6), "AI 分析：先看結論", "AI 分析", "AI 分析先給你結論，條件到哪我也列出來", "個股",
                   idle="bulb", top_only=True, hold=1.5))
    S.append(autom("h11", D2M, (4.0, 5.4), "AI 分析：看條件細節", "看細節", "想知道原因？點開，我逐條講給你聽", "個股",
                   idle=[(0, "talk_explain"), (1.4, "face_nod")], top_only=True, hold=1.5))
    S.append(autom("h12", D7M, (7.3, 8.8), "除權息紀錄", "除權息", "歷年股利、除息日，我幫你列出來", "個股",
                   idle="piggy", top_only=True, hold=1.5))
    S.append(autom("h13", D5M, (0.9, 2.4), "法人買賣一頁看", "法人", "三大法人買賣超，我幫你排成一張", "個股",
                   idle="magnifier", top_only=True, hold=1.5))
    S.append(autom("h14", D5M, (10.1, 11.6), "資券一頁看", "資券", "融資融券的變化，我幫你一頁排好", "個股",
                   idle="face_think", top_only=True, hold=1.5))
    S.append(autom("h15", D5M, (19.3, 20.8), "大戶與散戶", "大戶散戶", "大戶、散戶持股比例的變化，我畫給你看", "個股",
                   idle="face_curious", top_only=True, hold=1.5))
    S.append(autom("h16", D7M, (16.5, 18.0), "公告與新聞", "公告新聞", "重大公告和新聞，我幫你整理在最後一頁", "個股",
                   idle="news", top_only=True, hold=1.5))
    S.append(feat("22", 2.5, "V16_mobile", act(3.4, 2.5, 1.3, 0.8), "⑦ 完整名單", "完整名單", '完整名單我排給你，點欄位就能排序', "市場明細",
                  idle=[(0, 'hourglass'), (1.5, 'face_nod')], pan_=pan(0, 400, 2.5)))
    S.append(seqm("22s", "I05_mobile_v3i", [(0.7, 10.0, 1.6)], "名單連著篩", "連著篩", "漲停、跌停、漲幅前段…一個鍵一份名單，我連著點給你看", "市場明細",
                  idle=[(0, "face_curious"), (1.5, "magnifier"), (3.0, "face_nod"), (4.5, "face_shock")]))
    S.append(feat("23", 2.5, "V17_mobile", act(6.6, 2.5, 1.0, 0.8), "⑧ 公開條件篩", "條件篩", '用公開條件篩一遍，省下你自己翻的時間', "選股策略",
                  idle=[(0, 'face_think'), (1.6, 'pointer_r')]))
    S.append(seqm("23s", "I05_mobile_v3i", [(11.0, 23.4, 1.7)], "四個面向連著切", "連著切", "技術、籌碼、消息、基本，四個面向我連著切給你看", "選股策略",
                  idle=[(0, "face_think"), (1.4, "magnifier"), (2.8, "face_nod"), (4.2, "face_proud")]))
    S.append(feat("24", 2.0, "V18_mobile", stat(3.3, 2.0), "⑨ 週期統計", "週期", '各族群每個月份的表現，我排成一張表', "週期統計",
                  idle=[(0, 'face_curious')], pan_=pan(0, 400, 2.0)))
    S.append(seqm("24s", "I04_mobile_v3i", [(13.2, 26.5, 1.4)], "條件連著換", "連著換", "期間、報酬、月份，一個條件一個條件換給你看", "週期統計",
                  idle=[(0, "hourglass"), (1.6, "face_nod"), (3.2, "face_think"), (4.8, "face_star"), (6.4, "face_proud")]))
    S.append(feat("25", 2.5, "V19_mobile_v3b", act(4.3, 2.5, 1.3, 0.8), "⑩ ETF 配息日曆", "配息日曆", '哪天除息、配多少，月曆我全寫好了', "ETF",
                  idle=[(0, 'piggy'), (1.6, 'face_love')], pan_=pan(0, 900, 2.5)))
    S.append(feat("26", 2.5, "V20_mobile", act(3.1, 2.5, 1.5, 0.8), "各類前五名", "前五名", '每一類前五名，我幫你挑出來', "ETF",
                  idle=[(0, 'trophy'), (1.7, 'face_proud')], pan_=pan(0, 600, 2.5)))
    S.append(seqm("26s", "I03_mobile_v3i", [(11.2, 11.9, 1.0), (11.9, 24.6, 1.7)], "ETF 類型一頁一頁看", "一頁一頁", "七種 ETF 類型，每類前五名我連著點給你看", "ETF",
                  idle=[(0, "face_curious"), (1.5, "trophy"), (3.0, "face_nod"), (4.5, "face_star"), (6.0, "face_think")]))
    S.append(feat("27", 3.0, "V21_mobile_v3b", act(4.3, 3.0, 1.6, 0.8), "報酬放一起比", "一起比", '幾檔一起比，含息不含息我分開算', "ETF",
                  idle=[(0, 'calc'), (1.8, 'face_think')], pan_=pan(0, 900, 3.0)))
    S.append(seqm("27s", "I03_mobile_v3i", [(2.6, 3.3, 1.0), (3.3, 10.2, 1.7)], "勾幾檔，一起比", "一起比", "勾幾檔、換期間，報酬曲線馬上重畫給你", "ETF",
                  idle=[(0, "face_wink"), (1.6, "calc"), (3.2, "face_nod")]))
    ME = "V13b_mobile_v3e"
    ME = "V13b_mobile_v3e"
    _s31 = seqm("28s", ME, [(4.4, 6.0, 1.0), (6.0, 15.4, 3.0), (15.4, 16.5, 1.0)], "點一檔，三張圖一起亮", "一起亮", "點一檔，三張圖一起亮", "ETF",
                idle=[(0, "calc"), (1.6, "face_love"), (2.8, "face_nod"), (4.0, "face_proud")])
    _tl = _s31.op._seq()
    _s31.rec.pan_keys = [(0.0, 3380), (_tl[-1]["t"] + 0.4, 3380), (_tl[-1]["t"] + 1.5, 1550)]
    S.append(_s31)
    S.append(seqm("28t", "I02_mobile_v3i", [(8.0, 8.8, 1.0), (8.8, 19.4, 1.5)], "組合 A～E 連著切", "連著切", "組合 A 到 E，每月入帳一組一組換給你看", "ETF",
                  idle=[(0, "piggy"), (1.7, "face_curious"), (3.4, "face_star"), (5.1, "boba"), (6.5, "face_proud")]))
    pass
    pass
    pass
    S.append(feat("29", 2.5, "V23_mobile", [(0, 1.0), (1.5, 2.5), (2.5, 5.5)], "複利看得到", "複利", '配息再投入，複利我畫給你看', "ETF",
                  idle=[(0, 'growth'), (1.5, 'face_proud')], pan_=pan(0, 600, 2.5)))
    S.append(feat("30", 3.0, "V24_mobile", act(3.9, 3.0, 1.6, 0.8), "⑪ 存自己的股", "存自己", '喜歡的股票存起來，每天打開就看到', "自選清單",
                  idle=[(0, 'star_save'), (1.8, 'face_love')], pan_=pan(0, 300, 3.0)))
    S.append(feat("31", 2.5, "V25_mobile", act(2.0, 2.5, 1.5, 0.8), "看不懂？問比比", "問比比", '看不懂？我就在右下角，隨時問我', "導覽", idle=[(0, 'face_cool'), (1.4, 'talk_happy')]))
    S.append(feat("32", 2.5, "V26_mobile", act(13.2, 2.5, 1.0, 0.8), "一直在進步", "進步", '想要什麼功能，跟我說就好', "願望清單",
                  idle=[(0, 'heart_wish'), (1.5, 'rocket')], pan_=pan(0, 300, 2.5)))
    S.append(card("33", 3.0, K.benefits_fn(), [(0.3, "pop"), (0.65, "pop"), (1.0, "pop"), (1.35, "pop")]))
    S.append(card("34", 3.0, K.end_fn(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("35", 5.0, K.disclaimer_fn()))
    for _s in S:
        if _s.sid in ('13c', '13d', '13e', '13f', '28b', '28c', '28d'):
            _s.cont = True
    for _i, _s in enumerate(S):
        if _s.op and _s.op.chain in ("mid", "end"):
            _sq = S[_i - 1].op._seq() if S[_i - 1].op else []
            if _sq:
                _s.op.prev_xy = (_sq[-1]["cx"], _sq[-1]["cy"])
    return S
