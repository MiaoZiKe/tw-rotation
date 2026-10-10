"""第 3 版手機版（1080×1920）逐鏡規格，對照 storyboard_v3_mobile.md（31 鏡、115.4 秒）。

素材：raw_v3/Vxx_mobile.mp4（1170×2532）；V01／V03／V10／V13／V19 優先用重錄的 *_v3b。
第一拍手機畫面完整（小卡）→ 魔法棒畫框 → 推近到大卡；比比在右欄，推近後縮到卡片左下。
"""
from __future__ import annotations

import render_v3 as R
import v3_web as W
from v3_core import Focus4, Op, Rec4, Shot4

Wf = W.F


def feat(sid, dur, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), types=(), scrub=(), mode="card", win0=None,
         soft_hover=False, use_events=True):
    rec = Rec4(clip, srcmap, focus=focus, scrub=scrub, mode=mode, win0=win0)
    op = Op(rec, idle=idle, extra=extra, types=types, soft_hover=soft_hover, use_events=use_events, tap_scale=0.7)
    return Shot4(sid, dur, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def F(rect, t_draw=1.0, **kw):
    return Focus4(rect, t_draw=t_draw, **kw)


EMAIL_M = (30, 2010, 1140, 2215, 10.0, 19.3, (45, 2004))


def build():
    W.MOBILE_FRAGS[:] = [("V14_mobile", 2.5, (0, 500, 1170, 1400)), ("V16_mobile", 1.0, (0, 300, 1170, 1200)), ("V20_mobile", 1.0, (0, 600, 1170, 1500)),
                         ("V09_mobile", 2.5, (0, 500, 1170, 1400)), ("V18_mobile", 2.5, (0, 400, 1170, 1300)), ("V21_mobile", 2.5, (0, 500, 1170, 1400))]
    S = []
    hold, rt = W.hold, W.rt
    S.append(Shot4("01", 3.0, [], kind="card", foot=False, custom=W.custom_chaos(3.0, mobile=True), cues=[(0, "pop")]))

    def fn02(cv, t, shot):
        W.reveal_shot("02", 3.0, "V01_mobile_v3b", 1.0, mobile=True)(cv, t, shot)
        W.center_head(cv, shot.L, "這些我們整理好了", max(0, t - 0.2), "整理好", y=180)
        name = "reveal" if t < 1.4 else "talk_happy"
        from v3_core import put_sprite, anim_frame
        put_sprite(cv, name, anim_frame(name, t, "hold" if name == "reveal" else "loop"), (540, 1620), 420)
        W.sub_center(cv, shot.L, "別擔心，都幫你整理成圖了", max(0, t - 0.4))
    S.append(Shot4("02", 3.0, [], kind="card", foot=False, custom=fn02, cues=[(0, "swish"), (1.0, "ding")]))
    S.append(Shot4("03", 3.0, [], kind="card", foot=False, custom=W.intro_shot(3.0, mobile=True), cues=[(0, "pop"), (1.4, "ding")]))

    S.append(feat("04", 4.2, "V01_mobile_v3b", hold(2.2, 0.9, 2.9, 4.2), "① 一頁看完今天", "一頁", "不用開 5 個 App，這頁就看完今天", "總覽",
                  focus=F((20, 720, 1150, 1650), 2.0, t_zoom=2.6), idle="face_nod"))
    S.append(feat("05", 3.0, "V02_mobile", [(0, 1.3), (0.7, 2.0), (1.9, 4.4), (3.0, 6.0)], "今日事件不漏看", "不漏看", "國際、科技、總經消息排好了", "總覽",
                  focus=F((420, 100, 1170, 2400), 2.2, t_zoom=2.6, zoom=True), idle="news"))
    S.append(feat("06", 5.4, "V27_mobile", [(0, 1.6), (0.8, 2.4), (1.5, 3.9), (2.2, 5.5), (3.2, 7.3), (4.4, 9.7), (5.4, 11.0)], "想看什麼，打幾個字就到", "打幾個字",
                  "打代號或名稱，點一下就到那一頁", "搜尋", focus=F((0, 0, 1170, 760), 1.7, t_zoom=2.0), idle=[(0, "face_wink"), (3.6, "talk_excited")],
                  types=[(2.2, 3.2, (495, 78))]))
    S.append(feat("07", 3.6, "V03_mobile_v3b", hold(3.1, 0.7, 9.9, 3.6), "② 大日子排一起", "大日子", "財報、法說、FED，一張月曆排好", "財經日曆",
                  focus=F((0, 420, 1170, 1500), 2.1, t_zoom=2.7), idle="calendar"))
    wheel = (150, 1340, 1040, 2170)
    S.append(feat("08", 4.2, "V04_mobile", [(0, 1.1), (2.0, 3.1), (4.2, 3.1)], "③ 錢往哪裡跑", "錢", "族群在領先還是落後，一看就知道", "資金流向",
                  focus=F(wheel, 1.0, t_zoom=1.7), idle=[(0, "face_think"), (2.0, "talk_explain")]))
    S.append(feat("09", 3.6, "V04_mobile", rt(3.5, 3.6), "按播放看輪動", "播放", "我踩播放，20 天怎麼輪一路播", "資金流向",
                  focus=F(wheel, 1.4, frame=False, t_zoom=1.4), idle=[(0, "face_shock"), (1.5, "coins")]))
    S.append(feat("10", 4.2, "V06_mobile", rt(1.3, 4.2), "大盤的錢分去哪", "分去哪", "從大盤分到產業鏈、族群、代表股", "資金流向",
                  focus=F((40, 780, 1130, 2300), 1.0, t_zoom=1.7), idle="spotlight"))
    S.append(feat("11", 3.0, "V07_mobile", hold(3.3, 0.6, 3.7, 3.0), "法人資金在哪", "法人", "法人的錢集中在哪，也整理好了", "資金流向",
                  focus=F((40, 900, 1130, 2300), 1.7, zoom=False), idle="magnifier"))
    S.append(feat("12", 3.6, "V08_mobile", hold(3.1, 1.0, 11.9, 3.6), "④ 哪裡熱一眼看", "一眼看", "越大成交越多，紅漲綠跌；點下去進產業鏈", "熱力圖",
                  focus=F((30, 560, 640, 1100), 0.9, zoom=False), idle=[(0, "magnifier"), (1.5, "face_star")]))
    S.append(feat("13", 4.8, "V09_mobile", hold(3.1, 1.0, 11.9, 4.8), "題材資金熱力", "題材", "題材熱度 0～100，資金、法人、新聞一起算", "熱力圖",
                  focus=F((20, 600, 1150, 2000), 1.0, t_zoom=1.7), idle=[(0, "fire"), (3.0, "face_love")]))
    S.append(feat("14", 4.2, "V11_mobile", [(0, 14.8), (2.8, 17.6), (4.2, 17.8)], "⑤ 2D 看產業鏈", "2D", "零件編號對說明，每段在做什麼都寫好", "產業地圖",
                  focus=F((20, 860, 1140, 1650), 1.0, t_zoom=1.7), idle=[(0, "talk_explain"), (2.0, "face_nod")]))
    S.append(feat("15", 4.8, "V12e_mobile", [(0, 1.1), (1.2, 2.6), (1.2001, 2.5), (4.8, 6.1)], "零件是誰做的", "誰做的", "點零件，就知道哪家公司負責哪一層", "產業地圖",
                  focus=F((300, 950, 920, 1860), 3.2, zoom=False), idle=[(0, "3dglasses"), (3.0, "face_proud")]))
    for sid, clip, head, hl, sub, idle, rect in [
            ("16", "V12b_mobile", "3D：先進封裝", "先進封裝", "晶片、中介層、載板這樣疊", "face_surprise_happy", (250, 940, 930, 1820)),
            ("17", "V12c_mobile", "3D：HBM", "HBM", "記憶體疊起來，站在運算晶片旁", "magnifier", (250, 940, 930, 1820)),
            ("18", "V12d_mobile", "3D：液冷", "液冷", "從冷板到 CDU，熱這樣帶走", "boba", (200, 900, 970, 1850))]:
        S.append(feat(sid, 4.2, clip, [(0, 1.1), (4.2, 5.3)] if False else [(0, 1.5), (4.2, 5.7)], head, hl, sub, "產業地圖",
                      focus=F(rect, 3.0, zoom=False), idle=idle))
    S.append(feat("19", 3.6, "V13_mobile_v3b", rt(1.1, 3.6), "上下游一張連", "一張連", "誰供貨給誰，一張串起來", "產業地圖",
                  focus=F((0, 1480, 1170, 2300), 0.8, t_zoom=1.5), idle="pointer_r", use_events=False))
    S.append(feat("20", 3.0, "V15_mobile", rt(1.0, 3.0), "⑥ 個股一頁全有", "一頁全有", "K 線、營收、獲利、籌碼都在這", "個股",
                  focus=F((0, 340, 1170, 1500), 1.6, zoom=False), idle="face_nod"))
    S.append(feat("21", 4.2, "V17_mobile", [(0, 1.0), (0.8, 2.2), (0.8001, 5.4), (4.2, 8.8)], "⑦⑧ 完整名單＋條件", "完整名單", "市場完整名單、公開條件篩選都有", "市場明細",
                  focus=F((0, 480, 1170, 1500), 2.8, zoom=False), idle=[(0, "talk_explain"), (2.4, "face_think")]))
    S.append(feat("22", 3.0, "V18_mobile", [(0, 1.1), (2.2, 3.3), (3.0, 3.3)], "⑨ 週期統計", "週期", "族群過去各月份表現，一張看完", "週期統計",
                  focus=F((900, 740, 1070, 1900), 0.8, t_zoom=1.5), idle="hourglass"))
    S.append(feat("23", 3.0, "V19_mobile_v3b", hold(3.1, 0.6, 3.1, 3.0), "⑩ ETF 配息日曆", "配息日曆", "哪天除息、配多少，月曆寫好", "ETF",
                  focus=F((0, 560, 1170, 1500), 0.6, zoom=False), idle="piggy"))
    S.append(feat("24", 3.6, "V20_mobile", hold(2.2, 0.6, 2.2, 3.6), "各類前五名", "前五名", "每一類最熱門、報酬、殖利率前五", "ETF",
                  focus=F((30, 640, 1140, 1900), 2.1, zoom=False), idle="trophy"))
    S.append(feat("25", 3.0, "V21_mobile", hold(3.1, 0.5, 5.4, 3.0), "報酬放一起比", "一起比", "含息不含息，分開算給你看", "ETF",
                  focus=F((20, 560, 1150, 1700), 0.3, zoom=False), idle="face_think"))
    S.append(feat("26", 4.2, "V22_mobile", [(0, 0.8), (1.0, 2.2), (1.0001, 9.6), (4.2, 12.8)], "現金流＋複利", "複利", "每月配息排好，複利也算給你看", "ETF",
                  focus=F((20, 1250, 1150, 2500), 3.0, zoom=False), idle=[(0, "calc"), (2.8, "growth")]))
    S.append(feat("27", 3.0, "V24_mobile", [(0, 2.0), (0.9, 3.9), (1.8, 5.6), (3.0, 7.2)], "⑪ 存自己的股", "存自己", "想追蹤的股票存起來，打開就看到", "自選清單",
                  focus=F((20, 520, 1150, 1500), 2.0, zoom=False), idle=[(0, "face_wink"), (2.0, "star_save")]))
    S.append(feat("28", 3.0, "V25_mobile", [(0, 1.2), (0.8, 2.0), (1.4, 4.4), (3.0, 6.0)], "看不懂？問比比", "問比比", "每頁都有導覽，右下角點我", "導覽",
                  focus=F((50, 1880, 1120, 2500), 2.2, zoom=False), idle="face_wink"))
    S.append(feat("29", 3.0, "V26_mobile", rt(12.2, 3.0), "一直在進步", "進步", "功能持續新增，想要什麼跟我說！", "願望清單",
                  focus=F((30, 900, 1140, 2300), 1.6, zoom=False), idle="heart_wish", scrub=[EMAIL_M]))
    ec = R.end_card(3.6)
    S.append(Shot4("30", 3.6, [], kind="card", foot=False, custom=ec.layers[0].fn, cues=[(0, "pop"), (1.2, "ding")]))
    dc = R.disclaimer_card(5.0, prev=S[-1])
    S.append(Shot4("31", 5.0, [], kind="card", foot=False, custom=dc.layers[0].fn))
    for a, b in zip(S, S[1:]):
        b.prev = a
    return S
