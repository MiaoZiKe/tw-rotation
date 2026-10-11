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


from v3_core import solve_pan as _solve_core, PAN_LOG, Lay  # noqa: E402

_LM = Lay('mobile')


def solve_pan(rec, op, D, pan_):
    return _solve_core(rec, op, D, pan_, _LM)


def feat(sid, D, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), pan_=None, use_events=True, no_solve=False):
    rec = Rec4(clip, srcmap, focus=focus, pan=pan_)
    op = Op(rec, idle=idle, extra=extra, use_events=use_events)
    if not no_solve:
        rec.pan = solve_pan(rec, op, D, pan_)
    return Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def featp(sid, D, clip, ev_clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", pan_=None):
    """播放鏡頭：用 _v3c（60fps）素材原速，不凍結不丟格；點擊事件借用同鏡原檔的事件表。"""
    from v3_core import events_for
    rec = Rec4(clip, srcmap, focus=focus, pan=pan_)
    op = Op(rec, idle=idle, events=events_for(ev_clip))
    rec.pan = solve_pan(rec, op, D, pan_)
    return Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def build():
    S = []
    S.append(card("01a", 2.8, K.chaos_fn(1), [(0, "pop")]))
    S.append(card("01b", 2.8, K.chaos_fn(2), [(0, "pop")]))
    S.append(card("01c", 2.8, K.chaos_fn(3), [(0, "pop")]))
    S.append(card("02", 2.0, K.tidy_fn("V01_mobile_v3b"), [(0, "swish"), (0.7, "ding")]))
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
    S.append(feat("03a", 3.0, M3, [(0, 2.5), (3.0, 5.5)], "② 財報日，月曆看完", "財報日", "哪天誰要公布財報，我排在一張月曆；點一家看說明", "財經日曆",
                  idle=[(0, "calendar"), (1.5, "face_shock")], pan_=pan(0, 0, 3.0)))
    S.append(feat("03b", 2.6, M3, [(0, 10.2), (2.6, 12.8)], "財報說明卡", "說明卡", "說明卡有上次數值、預期，圖表我也放進來了", "財經日曆",
                  focus=F((48, 175, 1122, 1795), "公司財報：說明卡（圖表／數值區", M3, 0.9), idle="face_think", pan_=pan(0, 0, 2.6)))
    S.append(feat("03c", 2.2, M3, [(0, 13.0), (2.2, 15.2)], "公司法說也在這", "法說", "切到公司法說，哪天誰要開，我幫你排好", "財經日曆",
                  idle="face_curious", pan_=pan(0, 0, 2.2)))
    S.append(feat("03d", 2.8, M3, [(0, 17.4), (2.8, 22.2)], "點一場，重點展開", "點一場", "法說的重點和圖表，我幫你攤開給你看", "財經日曆",
                  idle=[(0, "talk_explain"), (1.5, "face_nod")], pan_=pan(0, 0, 2.8)))
    S.append(feat("03e", 2.2, M3, [(0, 27.6), (2.2, 29.8)], "FED 消息", "FED", "再切到 FED 消息，CPI、FOMC 都在這", "財經日曆",
                  idle="globe", pan_=pan(0, 0, 2.2)))
    S.append(feat("03f", 2.8, M3, [(0, 32.2), (2.8, 38.0)], "數值與預期", "數值", "點一則，數值和說明我整理好，不用自己查", "財經日曆",
                  idle=[(0, "face_proud"), (1.6, "face_nod")], pan_=pan(0, 0, 2.8)))
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
    S.append(feat("13a", 3.0, M7, [(0, 5.0), (3.0, 8.0)], "題材資金熱力", "題材", "點進一個題材，我帶你看它的上中下游", "熱力圖",
                  idle=[(0, "fire"), (1.6, "face_shock")], pan_=pan(0, 0, 3.0)))
    S.append(feat("13b", 2.8, M7, [(0, 12.3), (2.8, 15.1)], "① GPU／ASIC 與封裝", "上游", "GPU、ASIC 與封裝：這一環誰在做，我點給你看", "熱力圖",
                  idle="pointer_r", pan_=pan(0, 1300, 2.8)))
    S.append(feat("13c", 2.8, M7, [(0, 16.900000000000002), (2.8, 19.700000000000003)], "② 上板", "上板", "接著往下游，上板這一環也一樣", "熱力圖",
                  idle="face_curious", pan_=pan(0, 1300, 2.8)))
    S.append(feat("13d", 2.8, M7, [(0, 21.5), (2.8, 24.3)], "③ 電源與散熱", "電源散熱", "電源與散熱，每家負責什麼我標好了", "熱力圖",
                  idle="magnifier", pan_=pan(0, 1300, 2.8)))
    S.append(feat("13e", 2.8, M7, [(0, 28.6), (2.8, 31.400000000000002)], "④ 托盤組裝", "托盤", "托盤組裝，離整櫃交付又近一步", "熱力圖",
                  idle="face_think", pan_=pan(0, 1300, 2.8)))
    S.append(feat("13f", 2.8, M7, [(0, 35.599999999999994), (2.8, 38.4)], "⑤ 整櫃交付", "整櫃交付", "整櫃交付，上中下游一路看到底", "熱力圖",
                  idle="face_proud", pan_=pan(0, 1300, 2.8)))
    S.append(feat("14", 2.5, "V11_mobile", [(0, 14.8), (2.5, 17.6)], "⑤ 2D 看產業鏈", "2D", '圓圈編號對到說明卡，我一段一段講給你', "產業地圖",
                  idle=[(0, 'face_nod'), (1.5, 'talk_happy')], pan_=pan(600, 1000, 2.5)))
    S.append(feat("15", 3.0, "V12a_mobile", [(0, 2.0), (3.0, 9.0)], "3D：AI 伺服器", "3D", '拖一下就能轉，整台機櫃我幫你拆開給你看', "產業地圖",
                  idle=[(0, '3dglasses'), (1.6, 'face_star')], pan_=pan(700, 700, 3.0)))
    S.append(feat("16", 3.0, "V12e_mobile", act(3.9, 3.0, 1.0, 0.8), "零件是誰做的", "誰做的", '點零件，我告訴你哪家公司負責哪一層', "產業地圖",
                  idle=[(0, 'face_proud'), (1.8, 'face_nod')], pan_=pan(700, 800, 3.0)))
    S.append(card("17", 3.0, K.grid_fn(3.0, 1.9), [(0, "swish")]))
    S.append(card("18", 2.0, K.more_fn(), [(0.5, "pop")]))
    D1 = "D01_mobile_v3d"
    S.append(feat("19a", 3.4, D1, [(0, 1.0), (0.9, 2.0), (0.9001, 2.9), (1.4, 3.4), (1.4001, 4.5), (2.0, 5.9), (2.0001, 8.0), (3.4, 9.0)], "⑥ 個股一頁全有", "一頁全有", '打幾個字，點建議，我帶你進個股頁', "個股",
                  idle=[(0, 'face_wink'), (1.6, 'talk_happy')], pan_=pan(0, 0, 3.4)))
    S.append(feat("19b", 1.8, D1, stat(14.5, 1.8), "報價、K 線一眼看", "K 線", '報價、K 線、指標，我放在同一張卡', "個股",
                  focus=F((0, 0, 1, 1), "個股報價與 K 線卡", D1, 0.5), idle=[(0, 'face_nod')], pan_=pan(0, 0, 1.8)))
    S.append(feat("19c", 1.6, D1, [(0, 17.0), (1.6, 19.2)], "基本面一張卡", "基本面", 'EPS、ROE、本益比，基本面我幫你抓重點', "個股",
                  idle=[(0, 'face_think')], pan_=pan(380, 900, 1.6)))
    S.append(feat("19d", 1.6, D1, [(0, 20.4), (1.6, 22.0)], "籌碼快照", "籌碼", '法人、集保、信用、當沖，一次給你看', "個股",
                  idle=[(0, 'magnifier')], pan_=pan(380, 900, 1.6)))
    S.append(feat("19e", 2.0, D1, [(0, 24.3), (2.0, 26.3)], "AI 分析", "AI 分析", 'AI 分析先給你結論，條件到哪我也列出來', "個股",
                  idle=[(0, 'bulb')], pan_=pan(380, 900, 2.0)))
    S.append(feat("19f", 2.2, "D06_mobile_v3d", [(0, 8.0), (2.2, 10.2)], "K 線、指標、畫線", "K 線", 'K 線想切週期、加指標、畫線，都行', "個股",
                  idle=[(0, 'face_star'), (1.2, 'face_proud')], use_events=False, pan_=pan(0, 0, 2.2)))
    S.append(feat("19g", 2.0, "D05_mobile_v3d", [(0, 10.0), (2.0, 12.0)], "資券一頁看", "資券", '融資融券的變化，我幫你一頁排好', "個股",
                  idle=[(0, 'face_curious')], use_events=False, pan_=pan(0, 500, 2.0)))
    S.append(feat("19h", 2.0, "D07_mobile_v3d", [(0, 10.0), (2.0, 12.0)], "除權息紀錄", "除權息", '歷年股利、除息日，一頁看完', "個股",
                  idle=[(0, 'piggy')], use_events=False, pan_=pan(0, 500, 2.0)))
    S.append(feat("22", 2.5, "V16_mobile", act(3.4, 2.5, 1.3, 0.8), "⑦ 完整名單", "完整名單", '完整名單我排給你，點欄位就能排序', "市場明細",
                  idle=[(0, 'hourglass'), (1.5, 'face_nod')], pan_=pan(0, 400, 2.5)))
    S.append(feat("23", 2.5, "V17_mobile", act(6.6, 2.5, 1.0, 0.8), "⑧ 公開條件篩", "條件篩", '用公開條件篩一遍，省下你自己翻的時間', "選股策略",
                  idle=[(0, 'face_think'), (1.6, 'pointer_r')]))
    S.append(feat("24", 2.0, "V18_mobile", stat(3.3, 2.0), "⑨ 週期統計", "週期", '各族群每個月份的表現，我排成一張表', "週期統計",
                  idle=[(0, 'face_curious')], pan_=pan(0, 400, 2.0)))
    S.append(feat("25", 2.5, "V19_mobile_v3b", act(4.3, 2.5, 1.3, 0.8), "⑩ ETF 配息日曆", "配息日曆", '哪天除息、配多少，月曆我全寫好了', "ETF",
                  idle=[(0, 'piggy'), (1.6, 'face_love')], pan_=pan(0, 900, 2.5)))
    S.append(feat("26", 2.5, "V20_mobile", act(3.1, 2.5, 1.5, 0.8), "各類前五名", "前五名", '每一類前五名，我幫你挑出來', "ETF",
                  idle=[(0, 'trophy'), (1.7, 'face_proud')], pan_=pan(0, 600, 2.5)))
    S.append(feat("27", 3.0, "V21_mobile_v3b", act(4.3, 3.0, 1.6, 0.8), "報酬放一起比", "一起比", '幾檔一起比，含息不含息我分開算', "ETF",
                  idle=[(0, 'calc'), (1.8, 'face_think')], pan_=pan(0, 900, 3.0)))
    ME = "V13b_mobile_v3e"
    S.append(feat("28a", 2.6, ME, stat(4.6, 2.6), "現金流試算組合", "試算組合", "組合 B：甜甜圈、12 個月時鐘、每月入帳長條、明細", "ETF",
                  idle=[(0, "calc"), (1.4, "boba")], pan_=pan(1500, 3500, 2.6), no_solve=True))
    S.append(feat("28b", 2.8, ME, [(0, 6.0), (2.8, 8.8)], "點一檔，三張圖一起亮", "一起亮", "點一檔，三張圖一起亮", "ETF",
                  idle="face_love", pan_=(3500, 1550, 1.1, 2.3), no_solve=True))
    S.append(feat("28c", 2.8, ME, [(0, 9.5), (2.8, 12.3)], "再點一檔", "再點", "哪個月領多少，一眼看懂", "ETF",
                  idle="face_nod", pan_=(3500, 1550, 1.1, 2.3), no_solve=True))
    S.append(feat("28d", 2.8, ME, [(0, 12.9), (2.8, 15.7)], "每月入帳跟著變", "跟著變", "換一檔，每月入帳立刻跟著變", "ETF",
                  idle="face_proud", pan_=(3500, 1550, 1.1, 2.3), no_solve=True))
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
    return S
