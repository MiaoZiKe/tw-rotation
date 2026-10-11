"""第 3 版網頁版逐鏡規格（節奏改回第 2 版速度：每鏡 2～3.5 秒；目標約 100 秒）。

播放鏡頭（資金輪動 ▶／分流樹 ▶）等 _v3c 重錄素材到齊再補；個股頁 AI 分析等 v3d 素材到齊再補（見 TODO 標記）。
"""
from __future__ import annotations

import render_v3 as R
import v3_cards as K
from v3_core import Focus4, Lay, Op, Rec4, Shot4, Fn, solve_pan, plan_dwell, seq_map, auto_map

_LW = Lay('web')

C = "_desktop"


def act(T, D, speed=1.0, lead=0.8):
    s0 = max(0.0, T - lead * speed)
    return [(0, s0), (D, s0 + D * speed)]


def stat(s, D):
    return [(0, s), (D, s)]


def F(rect, label, clip, t_draw=0.5, **kw):
    kw["zoom"] = False
    return Focus4(rect, label=label, clip=clip + C, t_draw=t_draw, **kw)


def feat(sid, D, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), soft_hover=False, use_events=True, main=None, chain=None):
    rec = Rec4(clip + C, srcmap, focus=focus, main=main)
    op = Op(rec, idle=idle, extra=extra, soft_hover=soft_hover, use_events=use_events, chain=chain)
    D, dw = plan_dwell(rec, op, D, sub, _LW, None, chain)
    _sh = Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)
    _sh.dwell = dw
    return _sh


def FV(rect, label, clip_full, t_draw=0.5, **kw):
    kw["zoom"] = False
    return Focus4(rect, label=label, clip=clip_full, t_draw=t_draw, **kw)


def featv(sid, D, clip_full, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), soft_hover=False, use_events=True, main=None, chain=None):
    rec = Rec4(clip_full, srcmap, focus=focus, main=main)
    op = Op(rec, idle=idle, extra=extra, soft_hover=soft_hover, use_events=use_events, chain=chain)
    D, dw = plan_dwell(rec, op, D, sub, _LW, None, chain)
    _sh = Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)
    _sh.dwell = dw
    return _sh


def seqv(sid, clip_full, segs, head, hl, sub, pill, idle="talk_happy", main=None, focus=None):
    """連續點擊序列（快節奏）：比比從上一個目標直接跳到下一個，開頭進場、結尾退場各一次。"""
    sm, D = seq_map(segs)
    rec = Rec4(clip_full, sm, focus=focus, main=main)
    op = Op(rec, idle=idle, chain="solo")
    sh = Shot4(sid, round(D, 2), [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)
    sh.dwell = {"units": 1, "min_req": 0, "reading": 0, "D": round(D, 2), "reached": True, "hold": 0.0, "note": "快節奏序列（Andy 指定）", "ok": True}
    return sh


def autov(sid, clip_full, win, head, hl, sub, pill, idle="talk_happy", focus=None, main=None, hold=1.6):
    """依錄影端「點擊後內容區」自動排時間軸：點下→內容出現並入框→停留。"""
    sm, D, meta = auto_map(clip_full, win, hold=hold)
    return featv(sid, D, clip_full, sm, head, hl, sub, pill, focus=focus, idle=idle, main=main)


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def build():
    S = []
    S.append(card("01a", 2.8, K.chaos_fn(1), [(0, "pop")]))
    S.append(card("01b", 2.8, K.chaos_fn(2), [(0, "pop")]))
    S.append(card("01c", 2.8, K.chaos_fn(3), [(0, "pop")]))
    S.append(card("02", 2.5, K.tidy_fn("V01_desktop"), [(0, "swish"), (0.7, "ding")]))
    S.append(card("03", 3.5, K.intro_fn(), [(0, "pop"), (1.4, "ding")]))

    S.append(feat("04", 2.5, "V01", stat(0.5, 2.5), "① 一頁看完今天", "一頁看完", '我把今天的行情排在同一頁，你一眼就看完', "總覽",
                  focus=F((440, 100, 3140, 410), "四張摘要卡", "V01", 0.5, t_zoom=1.0), idle=[(0, 'talk_explain'), (1.5, 'face_nod')], main=[(480, 100, 3168, 1470)]))
    S.append(feat("05", 3.0, "V02", act(2.0, 3.0, 1.0, 0.8), "今日事件不漏看", "不漏看", '重要消息我幫你按時間排好，你不怕漏看', "總覽",
                  focus=F((2360, 60, 3186, 1500), "今日事件清單", "V02", 1.7, t_zoom=2.2), idle=[(0, 'news'), (1.6, 'face_shock')], main=[(480, 60, 3200, 1800)]))
    S.append(feat("06", 3.0, "V27", act(2.4, 3.0, 1.4, 0.8), "想看什麼，打幾個字就到", "打幾個字", '想看哪一檔？打幾個字，我幫你找出來', "搜尋",
                  focus=F((20, 150, 800, 1300), "搜尋下拉", "V27", 2.1, t_zoom=2.6), idle=[(0, 'magnifier'), (1.6, 'face_wink')], main=[(0, 100, 1800, 1000)]))
    S.append(feat("07", 3.0, "V27", [(0, 5.0), (3.0, 9.0)], "打代號或名稱", "代號", '代號或名稱都行，點一下我就帶你過去', "搜尋",
                  focus=F((20, 150, 900, 440), "搜尋框與建議", "V27", 1.0, zoom=False), idle=[(0, 'talk_excited'), (1.8, 'face_nod')], main=[(0, 0, 3200, 1800)]))
    V3F = "V03b_desktop_v3f"
    S.append(featv("03a", 3.0, V3F, [(0, 2.6), (3.0, 5.6)], "② 財報日，月曆看完", "財報日", "哪天誰要公布財報，我排在一張月曆；點一家看說明", "財經日曆",
                   idle=[(0, "calendar"), (1.5, "face_shock")]))
    S.append(featv("03b", 2.6, V3F, [(0, 7.9), (2.6, 10.5)], "財報說明卡", "說明卡", "說明卡有上次數值、預期，圖表我也放進來了", "財經日曆",
                   focus=FV((2348, 293, 3108, 1585), "公司財報：說明卡", V3F, 0.45, t_end=2.3), idle="face_think"))
    S.append(featv("03c", 2.4, V3F, [(0, 13.0), (2.4, 15.4)], "公司法說也在這", "法說", "切到公司法說，哪天誰要開，我幫你排好", "財經日曆",
                   idle="face_curious"))
    S.append(featv("03d", 3.0, V3F, [(0, 17.4), (3.0, 22.8)], "點一場，重點展開", "點一場", "法說的重點和圖表，我幫你攤開給你看", "財經日曆",
                   focus=FV((2348, 293, 3108, 1585), "公司法說：說明卡", V3F, 2.1), idle=[(0, "talk_explain"), (1.6, "face_nod")]))
    S.append(featv("03e", 2.4, V3F, [(0, 27.0), (2.4, 29.4)], "FED 消息", "FED", "再切到 FED 消息，CPI、FOMC 都在這", "財經日曆",
                   idle="globe"))
    S.append(featv("03f", 3.0, V3F, [(0, 31.5), (3.0, 37.5)], "數值與預期", "數值", "點一則，數值和說明我整理好，不用自己查", "財經日曆",
                   focus=FV((2348, 293, 3108, 1585), "FED 消息：說明卡", V3F, 2.0), idle=[(0, "face_proud"), (1.7, "face_nod")]))
    S.append(feat("09", 2.5, "V04", stat(2.0, 2.5), "③ 錢往哪裡跑", "錢", '錢往哪裡跑？我幫你標出誰領先、誰落後', "資金流向",
                  focus=F((600, 480, 1960, 1640), "資金輪動", "V04", 0.5, t_zoom=1.0), idle=[(0, 'face_curious'), (1.3, 'face_love')]))
    S.append(featv("09b", 3.8, "V04_desktop_v3c", [(0, 3.6), (3.8, 7.4)], "按播放，輪盤就動起來", "播放", "按下播放鍵，我幫你播，看族群怎麼輪動", "資金流向",
                   idle=[(0, "coins"), (1.6, "face_star")]))
    S.append(feat("10", 2.5, "V05", [(0, 3.0), (2.5, 5.5)], "大盤的錢分去哪", "分去哪", "大盤的錢分到哪？我一路追到代表股", "資金流向",
                  focus=F((440, 520, 2150, 1250), "分流樹", "V05", 0.5, t_zoom=1.0), idle=[(0, 'spotlight'), (1.4, 'face_think')]))
    S.append(featv("10b", 3.8, "V06_desktop_v3c", [(0, 3.6), (3.8, 7.4)], "分流樹也能播放", "播放", "分流樹也能播，資金逐日流動我帶你看", "資金流向",
                   idle=[(0, "talk_explain"), (1.7, "face_proud")]))
    S.append(feat("11", 2.0, "V07", stat(3.3, 2.0), "法人資金在哪", "法人", '法人的錢集中在哪，我也幫你整理好了', "資金流向",
                  focus=F((480, 100, 1820, 1290), "族群×法人", "V07", 0.4, zoom=False), idle=[(0, 'magnifier'), (1.1, 'face_nod')]))
    S.append(feat("12", 2.5, "V08", stat(3.1, 2.5), "④ 哪裡熱一眼看", "一眼看", '哪裡熱？整個台股我幫你畫成一張圖', "熱力圖",
                  focus=F((480, 200, 2260, 1120), "半導體", "V08", 0.5, t_zoom=1.0), idle=[(0, 'magnifier'), (1.4, 'face_star')]))
    V7 = "V07b_desktop_v3g"
    S.append(seqv("13s", "I01_desktop_v3i", [(3.2, 4.9, 1.0), (4.9, 6.5, 2.5), (6.5, 14.4, 1.35)], "上中下游，一路看到底", "一路", "上中下游，一路看到底", "熱力圖",
                  idle=[(0, "fire"), (1.5, "pointer_r"), (2.6, "face_curious"), (3.7, "magnifier"), (4.8, "face_think"), (5.9, "face_proud")], main=[(480, 130, 3168, 1500)]))
    pass
    pass
    pass
    pass
    pass
    S.append(feat("14", 2.0, "V08", act(4.5, 2.0, 1.0, 0.8), "點進產業鏈", "產業鏈", "看到熱的，點下去我就帶你進產業鏈", "熱力圖",
                  idle=[(0, "face_wink")]))
    S.append(feat("15", 2.0, "V11", stat(0.5, 2.0), "⑤ 產業鏈地圖", "產業鏈", "半導體、AI 伺服器…每條產業鏈我都拆好了", "產業地圖",
                  focus=F((440, 70, 3130, 250), "產業鏈分頁", "V11", 0.4, zoom=False), idle='talk_explain'))
    S.append(seqv("15s", "I04_desktop_v3i", [(0.8, 1.6, 1.0), (1.6, 7.6, 1.5)], "產業鏈連著選", "連著選", "半導體、AI 伺服器、一般電子、金融，一個一個切給你看", "產業地圖",
                  idle=[(0, "face_wink"), (1.2, "pointer_r"), (2.4, "face_curious"), (3.6, "face_star")]))
    S.append(feat("16", 2.5, "V11", stat(15.0, 2.5), "2D 看懂產業鏈", "2D", '圓圈編號對到說明卡，我一段一段講給你', "產業地圖",
                  focus=F((440, 360, 3150, 1500), "2D 剖析圖", "V11", 0.5, t_zoom=1.0), idle=[(0, 'face_nod'), (1.5, 'talk_happy')]))
    S.append(feat("17", 2.0, "V12a", [(0, 1.2), (2.0, 2.9)], "切到 3D！", "3D", '點「3D」，整台機櫃我幫你立體拆開', "產業地圖",
                  focus=F((2480, 215, 2740, 285), "2D｜3D 切換", "V12a", 0.4, zoom=False), idle=[(0, '3dglasses')]))
    S.append(feat("18", 3.0, "V12a", [(0, 3.2), (3.0, 9.0)], "拖一下就轉", "拖一下", '拖一下就能轉，換個角度看清楚', "產業地圖",
                  idle=[(0, 'face_cool'), (1.6, 'face_star')]))
    S.append(feat("19", 3.5, "V12e", [(0, 3.1), (1.5, 4.6), (1.5001, 8.5), (3.5, 10.5)], "零件是誰做的", "誰做的", '點零件，我告訴你哪家公司負責哪一層', "產業地圖",
                  focus=F((520, 740, 3120, 1130), "CCL 銅箔基板說明卡", "V12e", 2.0, zoom=False), idle=[(0, 'face_proud'), (1.8, 'face_nod')]))
    S.append(card("20", 3.0, K.grid_fn(3.0, 1.9), [(0, "swish")]))
    S.append(card("21", 2.5, K.more_fn(), [(0.5, "pop")]))
    # 個股頁（v3d 素材：D01 總覽、D02 AI 分析、D05 資券、D06 K 線、D07 除權息；營收／獲利素材尚未到）
    D1, D2 = "D01_desktop_v3d", "D02_desktop_v3d"
    S.append(featv("22a", 3.0, D1, [(0, 0.9), (0.7, 1.9), (0.7001, 3.0), (1.6, 4.4), (2.3, 5.1), (2.3001, 6.5), (3.0, 7.2)], "⑥ 個股一頁全有", "一頁全有", '打幾個字，點建議，我帶你進個股頁', "個股",
                   focus=FV((24, 252, 904, 344), "搜尋下拉建議清單", D1, 1.7, zoom=False, t_end=2.3), idle=[(0, 'face_wink'), (1.6, 'talk_happy')]))
    S.append(featv("22b", 1.8, D1, stat(12.8, 1.8), "報價、K 線一眼看", "K 線", '報價、K 線、指標，我放在同一張卡', "個股",
                   focus=FV((0, 0, 1, 1), "個股報價與 K 線卡", D1, 0.5, zoom=False), idle=[(0, 'face_nod')]))
    S.append(featv("22c", 1.4, D1, stat(16.0, 1.4), "基本面一張卡", "基本面", 'EPS、ROE、本益比，基本面我幫你抓重點', "個股",
                   focus=FV((0, 0, 1, 1), "基本面卡", D1, 0.45, zoom=False), idle=[(0, 'face_think')]))
    S.append(featv("22d", 1.4, D1, stat(19.3, 1.4), "籌碼快照", "籌碼", '法人、集保、信用、當沖，一次給你看', "個股",
                   focus=FV((0, 0, 1, 1), "籌碼快照卡", D1, 0.45, zoom=False), idle=[(0, 'magnifier')]))
    S.append(featv("23a", 2.0, D2, stat(2.4, 2.0), "AI 分析：先看結論", "AI 分析", 'AI 分析先給你結論，條件到哪我也列出來', "個股",
                   focus=FV((0, 0, 1, 1), "AI 分析：結論一行", D2, 0.5, zoom=False), idle=[(0, 'bulb')]))
    S.append(featv("23b", 2.6, D2, [(0, 3.6), (2.6, 6.2)], "AI 分析：看細節", "看細節", '想知道原因？點開，我逐條講給你聽', "個股",
                   idle=[(0, 'talk_explain'), (1.5, 'face_nod')]))
    S.append(featv("23c", 2.2, D2, [(0, 10.9), (2.2, 13.1)], "切到籌碼面", "籌碼面", "切到籌碼面，法人買賣我幫你看", "個股",
                   focus=FV((0, 0, 1, 1), "AI 分析內容（籌碼面）", D2, 1.6), idle="face_curious"))
    S.append(featv("23d", 1.8, D2, [(0, 14.0), (1.8, 15.8)], "切到基本面", "基本面", "基本面也一鍵切換，營運估值一次看", "個股",
                   idle="face_think"))
    S.append(featv("23e", 1.8, D2, [(0, 17.0), (1.8, 18.8)], "切到消息面", "消息面", "消息面，我把新聞整理成一面給你", "個股",
                   idle="news"))
    D8, D9 = "D08_desktop_v3h", "D09_desktop_v3h"
    S.append(featv("24r1", 4.2, D8, [(0, 11.0), (1.4, 12.4), (2.6, 15.8), (4.2, 17.4)], "營收：月營收圖", "營收", "月營收和年增率，每個月我幫你畫好", "個股",
                   focus=FV((514, 825, 1354, 1345), "月營收圖", D8, 2.8), idle=[(0, "piggy"), (2.4, "face_proud")]))
    S.append(featv("24r2", 2.6, D8, [(0, 18.9), (2.6, 20.5)], "營收：年同期比較", "年同期", "跟去年同期比，一眼看出成長", "個股",
                   focus=FV((1446, 689, 2286, 1345), "年同期比較圖", D8, 0.4), idle="growth"))
    S.append(featv("24p1", 4.2, D9, [(0, 11.0), (1.4, 12.4), (2.6, 15.8), (4.2, 17.4)], "獲利：本益比河流圖", "獲利", "本益比河流圖，現在貴還是便宜我幫你標出來", "個股",
                   focus=FV((480, 405, 2264, 1471), "本益比河流圖", D9, 2.8), idle=[(0, "calc"), (2.4, "face_think")]))
    S.append(featv("24p2", 2.6, D9, [(0, 21.9), (2.6, 23.5)], "獲利：EPS 與毛利率", "EPS", "EPS、毛利率的變化，我整理在同一張圖", "個股",
                   focus=FV((480, 731, 2038, 1371), "EPS／毛利率圖", D9, 0.4), idle="bulb"))
    S.append(featv("24p3", 2.6, D9, [(0, 25.1), (2.6, 26.9)], "獲利：財報表", "財報表", "財報表也列好，數字我幫你排整齊", "個股",
                   focus=FV((2062, 731, 3168, 1371), "財報表", D9, 0.4), idle="folder"))
    S.append(featv("24a", 2.4, "D06_desktop_v3d", [(0, 7.1), (2.4, 9.5)], "切週期，K 線立刻換", "切週期", "切週期，K 線我立刻幫你換", "個股",
                   idle=[(0, "face_star"), (1.2, "face_proud")]))
    S.append(featv("24a3", 2.4, "D06_desktop_v3d", stat(19.9, 2.4), "四個週期並排看", "並排", "日、週、月、季四個週期，我幫你並排看", "個股",
                   focus=FV((480, 100, 3168, 1760), "四週期同看", "D06_desktop_v3d", 0.4), idle="face_cool"))
    S.append(featv("24b1", 2.6, "D05_desktop_v3d", [(0, 0.6), (2.6, 5.8)], "法人買賣一頁看", "法人", "三大法人買賣超，我幫你排成一張", "個股",
                   idle="magnifier"))
    S.append(featv("24b2", 2.4, "D05_desktop_v3d", [(0, 7.6), (2.4, 12.4)], "資券一頁看", "資券", "融資融券的變化，我幫你一頁排好", "個股",
                   idle="face_think"))
    S.append(featv("24c1", 2.2, "D07_desktop_v3d", [(0, 0.6), (2.2, 3.8)], "基本資料", "基本資料", "公司基本資料，我幫你整理好", "個股",
                   idle="folder"))
    S.append(featv("24c2", 2.4, "D07_desktop_v3d", [(0, 7.6), (2.4, 12.4)], "除權息紀錄", "除權息", "歷年股利、除息日，我幫你列出來", "個股",
                   idle="piggy"))
    S.append(feat("25", 2.5, "V16", act(3.4, 2.5, 1.3, 0.8), "⑦ 完整名單", "完整名單", "完整名單我排給你，點欄位就能排序", "市場明細",
                  focus=F((1880, 230, 3140, 340), "分頁列", "V16", 1.4, zoom=False), idle=[(0, 'hourglass'), (1.5, 'face_nod')]))
    S.append(seqv("25s", "I05_desktop_v3i", [(0.7, 10.0, 1.6)], "名單連著篩", "連著篩", "漲停、跌停、漲幅前段…一個鍵一份名單，我連著點給你看", "市場明細",
                  idle=[(0, "face_curious"), (1.5, "magnifier"), (3.0, "face_nod"), (4.5, "face_shock")]))
    S.append(feat("26", 2.5, "V17", act(6.6, 2.5, 1.0, 0.8), "⑧ 公開條件篩", "條件篩", "用公開條件篩一遍，省下你自己翻的時間", "選股策略",
                  focus=F((440, 330, 3150, 1500), "條件卡", "V17", 1.4, zoom=False), idle=[(0, 'face_think'), (1.6, 'pointer_r')]))
    S.append(seqv("26s", "I05_desktop_v3i", [(16.4, 24.2, 1.7)], "四個面向連著切", "連著切", "技術、籌碼、消息、基本，四個面向我連著切給你看", "選股策略",
                  idle=[(0, "face_think"), (1.4, "magnifier"), (2.8, "face_nod")]))
    S.append(feat("27", 2.0, "V18", stat(3.3, 2.0), "⑨ 週期統計", "週期", "各族群每個月份的表現，我排成一張表", "週期統計",
                  focus=F((2500, 230, 2790, 1320), "本月欄", "V18", 0.4, t_zoom=0.95), idle='face_curious'))
    S.append(seqv("27s", "I04_desktop_v3i", [(13.2, 19.2, 1.0), (19.2, 19.6, 3.0), (19.6, 23.8, 1.3)], "條件連著換", "連著換", "期間、報酬、月份，一個條件一個條件換給你看", "週期統計",
                  idle=[(0, "hourglass"), (1.6, "face_nod"), (3.2, "face_think"), (4.8, "face_star"), (6.4, "face_proud")]))
    S.append(feat("28", 2.5, "V19", act(4.3, 2.5, 1.3, 0.8), "⑩ ETF 配息日曆", "配息日曆", '哪天除息、配多少，月曆我全寫好了', "ETF",
                  focus=F((1150, 540, 3150, 1300), "當日除息清單", "V19", 1.5, zoom=False), idle=[(0, 'piggy'), (1.6, 'face_love')]))
    S.append(feat("29", 2.5, "V20", act(3.1, 2.5, 1.5, 0.8), "各類前五名", "前五名", "每一類最受歡迎、報酬、殖利率前五名，我幫你挑出來", "ETF",
                  focus=F((440, 180, 3150, 900), "前五名三張卡", "V20", 1.5, zoom=False), idle=[(0, 'trophy'), (1.7, 'face_proud')]))
    S.append(seqv("29s", "I03_desktop_v3i", [(14.3, 15.0, 1.0), (15.0, 28.0, 1.7)], "ETF 類型一頁一頁看", "一頁一頁", "七種 ETF 類型，每類前五名我連著點給你看", "ETF",
                  idle=[(0, "face_curious"), (1.5, "trophy"), (3.0, "face_nod"), (4.5, "face_star"), (6.0, "face_think")]))
    S.append(feat("30", 3.0, "V21", act(4.3, 3.0, 1.6, 0.8), "報酬放一起比", "一起比", "幾檔一起比，含息不含息我分開算", "ETF",
                  focus=F((460, 540, 2050, 1230), "報酬走勢圖", "V21", 2.0, zoom=False), idle=[(0, 'calc'), (1.8, 'face_think')]))
    S.append(seqv("30s", "I03_desktop_v3i", [(2.6, 3.3, 1.0), (3.3, 13.4, 1.7)], "勾幾檔，一起比", "一起比", "勾幾檔、換期間，報酬曲線馬上重畫給你", "ETF",
                  idle=[(0, "face_wink"), (1.6, "calc"), (3.2, "face_nod"), (4.8, "growth")]))
    V3E = "V13b_desktop_v3e"
    MAIN_E = [(506, 178, 3142, 1701)]
    S.append(seqv("31s", V3E, [(5.0, 6.7, 1.0), (6.7, 15.9, 3.0), (15.9, 17.0, 1.0)], "點一檔，三張圖一起亮", "一起亮", "點一檔，三張圖一起亮", "ETF",
                  idle=[(0, "calc"), (1.6, "face_love"), (2.8, "face_nod"), (4.0, "face_proud")], main=MAIN_E,
                  focus=FV((532, 313, 3116, 1679), "三張圖＋被點明細（同步高亮）", V3E, 0.4, d_draw=0.3)))
    S.append(seqv("31t", "I02_desktop_v3i", [(8.0, 8.8, 1.0), (8.8, 19.4, 1.5)], "組合 A～E 連著切", "連著切", "組合 A 到 E，每月入帳一組一組換給你看", "ETF",
                  idle=[(0, "piggy"), (1.7, "face_curious"), (3.4, "face_star"), (5.1, "boba"), (6.5, "face_proud")]))
    pass
    pass
    pass
    S.append(feat("32", 2.5, "V23", [(0, 1.0), (1.5, 2.5), (2.5, 5.5)], "複利看得到", "複利", '配息再投入，複利我畫給你看', "ETF",
                  focus=F((460, 400, 2150, 1330), "三條線", "V23", 1.8, zoom=False), idle=[(0, 'growth'), (1.5, 'face_proud')]))
    S.append(feat("33", 3.0, "V24", act(3.9, 3.0, 1.6, 0.8), "⑪ 存自己的股", "存自己", '喜歡的股票存起來，每天打開就看到', "自選清單",
                  focus=F((440, 420, 3150, 1000), "自選清單", "V24", 1.9, zoom=False), idle=[(0, 'star_save'), (1.8, 'face_love')]))
    S.append(feat("34", 2.5, "V25", act(2.0, 2.5, 1.5, 0.8), "看不懂？問比比", "問比比", '看不懂？我就在右下角，隨時問我', "導覽",
                  idle=[(0, 'face_cool'), (1.4, 'talk_happy')]))
    S.append(feat("35", 2.5, "V26", act(13.2, 2.5, 1.0, 0.8), "一直在進步", "進步", '想要什麼功能，跟我說就好', "願望清單",
                  focus=F((2362, 368, 3158, 1642), "客服面板", "V26", 1.6, zoom=False), idle=[(0, 'heart_wish'), (1.5, 'rocket')]))
    S.append(card("36", 3.0, K.benefits_fn(), [(0.3, "pop"), (0.65, "pop"), (1.0, "pop"), (1.35, "pop")]))
    S.append(card("37", 3.0, K.end_fn(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("38", 5.0, K.disclaimer_fn()))
    for _s in S:
        if _s.sid in ('13c', '13d', '13e', '13f', '31b', '31c', '31d'):
            _s.cont = True
    for _i, _s in enumerate(S):
        if _s.op and _s.op.chain in ("mid", "end"):
            _sq = S[_i - 1].op._seq() if S[_i - 1].op else []
            if _sq:
                _s.op.prev_xy = (_sq[-1]["cx"], _sq[-1]["cy"])
    return S
