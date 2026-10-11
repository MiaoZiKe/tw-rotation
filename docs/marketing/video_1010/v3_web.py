"""第 3 版網頁版逐鏡規格（節奏改回第 2 版速度：每鏡 2～3.5 秒；目標約 100 秒）。

播放鏡頭（資金輪動 ▶／分流樹 ▶）等 _v3c 重錄素材到齊再補；個股頁 AI 分析等 v3d 素材到齊再補（見 TODO 標記）。
"""
from __future__ import annotations

import render_v3 as R
import v3_cards as K
from v3_core import Focus4, Lay, Op, Rec4, Shot4, Fn, solve_pan

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


def feat(sid, D, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), soft_hover=False, use_events=True, main=None):
    rec = Rec4(clip + C, srcmap, focus=focus, main=main)
    op = Op(rec, idle=idle, extra=extra, soft_hover=soft_hover, use_events=use_events)
    return Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def FV(rect, label, clip_full, t_draw=0.5, **kw):
    kw["zoom"] = False
    return Focus4(rect, label=label, clip=clip_full, t_draw=t_draw, **kw)


def featv(sid, D, clip_full, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), soft_hover=False, use_events=True, main=None):
    rec = Rec4(clip_full, srcmap, focus=focus, main=main)
    op = Op(rec, idle=idle, extra=extra, soft_hover=soft_hover, use_events=use_events)
    return Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def build():
    S = []
    S.append(card("01a", 2.8, K.chaos_fn(1), [(0, "pop")]))
    S.append(card("01b", 2.8, K.chaos_fn(2), [(0, "pop")]))
    S.append(card("01c", 2.8, K.chaos_fn(3), [(0, "pop")]))
    S.append(card("02", 2.0, K.tidy_fn("V01_desktop"), [(0, "swish"), (0.7, "ding")]))
    S.append(card("03", 3.5, K.intro_fn(), [(0, "pop"), (1.4, "ding")]))

    S.append(feat("04", 2.5, "V01", stat(0.5, 2.5), "① 一頁看完今天", "一頁看完", '我把今天的行情排在同一頁，你一眼就看完', "總覽",
                  focus=F((440, 100, 3140, 410), "四張摘要卡", "V01", 0.5, t_zoom=1.0), idle=[(0, 'talk_explain'), (1.5, 'face_nod')], main=[(480, 100, 3168, 1470)]))
    S.append(feat("05", 3.0, "V02", act(2.0, 3.0, 1.0, 0.8), "今日事件不漏看", "不漏看", '重要消息我幫你按時間排好，你不怕漏看', "總覽",
                  focus=F((2360, 60, 3186, 1500), "今日事件清單", "V02", 1.7, t_zoom=2.2), idle=[(0, 'news'), (1.6, 'face_shock')], main=[(480, 60, 3200, 1800)]))
    S.append(feat("06", 3.0, "V27", act(2.4, 3.0, 1.4, 0.8), "想看什麼，打幾個字就到", "打幾個字", '想看哪一檔？打幾個字，我幫你找出來', "搜尋",
                  focus=F((20, 150, 800, 1300), "搜尋下拉", "V27", 2.1, t_zoom=2.6), idle=[(0, 'magnifier'), (1.6, 'face_wink')], main=[(0, 100, 1800, 1000)]))
    S.append(feat("07", 3.0, "V27", [(0, 5.0), (3.0, 9.0)], "打代號或名稱", "代號", '代號或名稱都行，點一下我就帶你過去', "搜尋",
                  focus=F((20, 150, 900, 440), "搜尋框與建議", "V27", 1.0, zoom=False), idle=[(0, 'talk_excited'), (1.8, 'face_nod')], main=[(0, 0, 3200, 1800)]))
    S.append(feat("08", 3.0, "V03", [(0, 3.1), (0.7, 3.1), (0.7001, 9.9), (3.0, 13.35)], "② 大日子排一起", "大日子", '重要的日子，我幫你排在一張月曆裡，不怕漏掉', "財經日曆",
                  focus=F((2300, 300, 3150, 1720), "FED 事件說明卡", "V03", 1.8, zoom=False), idle=[(0, 'face_shock'), (1.5, 'calendar')]))
    S.append(feat("09", 2.5, "V04", stat(2.0, 2.5), "③ 錢往哪裡跑", "錢", '錢往哪裡跑？我幫你標出誰領先、誰落後', "資金流向",
                  focus=F((600, 480, 1960, 1640), "資金輪動", "V04", 0.5, t_zoom=1.0), idle=[(0, 'face_curious'), (1.3, 'face_love')]))
    S.append(featv("09b", 3.8, "V04_desktop_v3c", [(0, 5.0), (3.8, 8.8)], "按播放，輪盤就動起來", "播放", '按下播放鍵，我幫你播，看族群怎麼輪動', "資金流向",
                   idle=[(0, 'coins'), (1.6, 'face_star')]))
    S.append(feat("10", 2.5, "V05", [(0, 3.0), (2.5, 5.5)], "大盤的錢分去哪", "分去哪", '大盤的錢分到哪？我一路追到代表股', "資金流向",
                  focus=F((440, 520, 2150, 1250), "分流樹", "V05", 0.5, t_zoom=1.0), idle=[(0, 'spotlight'), (1.4, 'face_think')]))
    S.append(feat("11", 2.0, "V07", stat(3.3, 2.0), "法人資金在哪", "法人", '法人的錢集中在哪，我也幫你整理好了', "資金流向",
                  focus=F((480, 100, 1820, 1290), "族群×法人", "V07", 0.4, zoom=False), idle=[(0, 'magnifier'), (1.1, 'face_nod')]))
    S.append(feat("12", 2.5, "V08", stat(3.1, 2.5), "④ 哪裡熱一眼看", "一眼看", '哪裡熱？整個台股我幫你畫成一張圖', "熱力圖",
                  focus=F((480, 200, 2260, 1120), "半導體", "V08", 0.5, t_zoom=1.0), idle=[(0, 'magnifier'), (1.4, 'face_star')]))
    S.append(feat("13", 3.0, "V09", [(0, 3.1), (0.6, 3.1), (0.6001, 12.4), (3.0, 15.5)], "題材資金熱力", "題材", '題材有多熱，我用 0～100 分幫你算好', "熱力圖",
                  focus=F((440, 110, 3140, 1480), "題材資金熱力", "V09", 0.3, zoom=False), idle=[(0, 'fire'), (1.8, 'face_love')]))
    S.append(feat("14", 2.0, "V08", act(13.3, 2.0, 1.0, 0.8), "點進產業鏈", "產業鏈", '看到熱的，點下去我就帶你進產業鏈', "熱力圖",
                  idle=[(0, 'face_wink')]))
    S.append(feat("15", 2.0, "V11", stat(0.5, 2.0), "⑤ 產業鏈地圖", "產業鏈", '產業鏈我都拆好了，一條一條選', "產業地圖",
                  focus=F((440, 70, 3130, 250), "產業鏈分頁", "V11", 0.4, zoom=False), idle=[(0, 'talk_explain')]))
    S.append(feat("16", 2.5, "V11", stat(15.0, 2.5), "2D 看懂產業鏈", "2D", '圓圈編號對到說明卡，我一段一段講給你', "產業地圖",
                  focus=F((440, 360, 3150, 1500), "2D 剖析圖", "V11", 0.5, t_zoom=1.0), idle=[(0, 'face_nod'), (1.5, 'talk_happy')]))
    S.append(feat("17", 2.0, "V12a", [(0, 1.2), (2.0, 2.9)], "切到 3D！", "3D", '點「3D」，整台機櫃我幫你立體拆開', "產業地圖",
                  focus=F((2480, 215, 2740, 285), "2D｜3D 切換", "V12a", 0.4, zoom=False), idle=[(0, '3dglasses')]))
    S.append(feat("18", 3.0, "V12a", [(0, 3.2), (3.0, 9.0)], "拖一下就轉", "拖一下", '拖一下就能轉，換個角度看清楚', "產業地圖",
                  idle=[(0, 'face_cool'), (1.6, 'face_star')]))
    S.append(feat("19", 3.5, "V12e", [(0, 3.1), (1.5, 4.6), (1.5001, 8.5), (3.5, 10.5)], "零件是誰做的", "誰做的", '點零件，我告訴你哪家公司負責哪一層', "產業地圖",
                  focus=F((520, 740, 3120, 1130), "CCL 銅箔基板說明卡", "V12e", 2.0, zoom=False), idle=[(0, 'face_proud'), (1.8, 'face_nod')]))
    S.append(card("20", 3.0, K.grid_fn(3.0, 1.9), [(0, "swish")]))
    S.append(card("21", 2.0, K.more_fn(), [(0.5, "pop")]))
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
    S.append(featv("23c", 2.0, D2, [(0, 8.6), (2.0, 10.6)], "切到籌碼面", "籌碼面", '切到籌碼面，法人買賣我幫你看', "個股",
                   focus=FV((0, 0, 1, 1), "AI 分析卡（籌碼面）", D2, 1.4, zoom=False), idle=[(0, 'face_curious')]))
    S.append(featv("23d", 1.8, D2, [(0, 13.6), (1.8, 15.4)], "切到基本面", "基本面", '基本面也一鍵切換，營運估值一次看', "個股",
                   idle=[(0, 'face_think')]))
    S.append(featv("23e", 1.8, D2, [(0, 18.2), (1.8, 20.0)], "切到消息面", "消息面", '消息面，我把新聞整理成一面給你', "個股",
                   idle=[(0, 'news')]))
    S.append(featv("24a", 2.4, "D06_desktop_v3d", [(0, 8.0), (2.4, 10.4)], "K 線、指標、畫線", "K 線", 'K 線想切週期、加指標、畫線，都行', "個股",
                   idle=[(0, 'face_star'), (1.2, 'face_proud')], use_events=False))
    S.append(featv("24b", 2.2, "D05_desktop_v3d", [(0, 10.0), (2.2, 12.2)], "資券一頁看", "資券", '融資融券的變化，我幫你一頁排好', "個股",
                   idle=[(0, 'face_curious')], use_events=False))
    S.append(featv("24c", 2.2, "D07_desktop_v3d", [(0, 10.0), (2.2, 12.2)], "除權息紀錄", "除權息", '歷年股利、除息日，一頁看完', "個股",
                   idle=[(0, 'piggy')], use_events=False))
    S.append(feat("25", 2.5, "V16", act(3.4, 2.5, 1.3, 0.8), "⑦ 完整名單", "完整名單", '完整名單我排給你，點欄位就能排序', "市場明細",
                  focus=F((1880, 230, 3140, 340), "分頁列", "V16", 1.4, zoom=False), idle=[(0, 'hourglass'), (1.5, 'face_nod')]))
    S.append(feat("26", 2.5, "V17", act(6.6, 2.5, 1.0, 0.8), "⑧ 公開條件篩", "條件篩", '用公開條件篩一遍，省下你自己翻的時間', "選股策略",
                  focus=F((440, 330, 3150, 1500), "條件卡", "V17", 1.4, zoom=False), idle=[(0, 'face_think'), (1.6, 'pointer_r')]))
    S.append(feat("27", 2.0, "V18", stat(3.3, 2.0), "⑨ 週期統計", "週期", '各族群每個月份的表現，我排成一張表', "週期統計",
                  focus=F((2500, 230, 2790, 1320), "本月欄", "V18", 0.4, t_zoom=0.95), idle=[(0, 'face_curious')]))
    S.append(feat("28", 2.5, "V19", act(4.3, 2.5, 1.3, 0.8), "⑩ ETF 配息日曆", "配息日曆", '哪天除息、配多少，月曆我全寫好了', "ETF",
                  focus=F((1150, 540, 3150, 1300), "當日除息清單", "V19", 1.5, zoom=False), idle=[(0, 'piggy'), (1.6, 'face_love')]))
    S.append(feat("29", 2.5, "V20", act(3.1, 2.5, 1.5, 0.8), "各類前五名", "前五名", '每一類前五名，我幫你挑出來', "ETF",
                  focus=F((440, 180, 3150, 900), "前五名三張卡", "V20", 1.5, zoom=False), idle=[(0, 'trophy'), (1.7, 'face_proud')]))
    S.append(feat("30", 3.0, "V21", act(4.3, 3.0, 1.6, 0.8), "報酬放一起比", "一起比", '幾檔一起比，含息不含息我分開算', "ETF",
                  focus=F((460, 540, 2050, 1230), "報酬走勢圖", "V21", 2.0, zoom=False), idle=[(0, 'calc'), (1.8, 'face_think')]))
    S.append(feat("31", 2.5, "V22", act(3.4, 2.5, 1.8, 0.8), "現金流試算", "現金流", '想每月都有配息？我幫你排組合', "ETF",
                  focus=F((440, 500, 3150, 1500), "試算圖表", "V22", 1.7, zoom=False), idle=[(0, 'boba'), (1.5, 'face_relief')]))
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
    return S
