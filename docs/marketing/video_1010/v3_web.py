"""第 3 版網頁版逐鏡規格（節奏改回第 2 版速度：每鏡 2～3.5 秒；目標約 100 秒）。

播放鏡頭（資金輪動 ▶／分流樹 ▶）等 _v3c 重錄素材到齊再補；個股頁 AI 分析等 v3d 素材到齊再補（見 TODO 標記）。
"""
from __future__ import annotations

import render_v3 as R
import v3_cards as K
from v3_core import Focus4, Op, Rec4, Shot4, Fn

C = "_desktop"


def act(T, D, speed=1.0, lead=0.8):
    s0 = max(0.0, T - lead * speed)
    return [(0, s0), (D, s0 + D * speed)]


def stat(s, D):
    return [(0, s), (D, s)]


def F(rect, label, clip, t_draw=0.5, **kw):
    return Focus4(rect, label=label, clip=clip + C, t_draw=t_draw, **kw)


def feat(sid, D, clip, srcmap, head, hl, sub, pill, focus=None, idle="talk_happy", extra=(), soft_hover=False, use_events=True):
    rec = Rec4(clip + C, srcmap, focus=focus)
    op = Op(rec, idle=idle, extra=extra, soft_hover=soft_hover, use_events=use_events)
    return Shot4(sid, D, [rec], pill=pill, head=head, hl=hl, sub=sub, op=op)


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def build():
    S = []
    S.append(card("01", 2.5, K.chaos_fn(), [(0, "pop")]))
    S.append(card("02", 2.0, K.tidy_fn("V01_desktop"), [(0, "swish"), (0.7, "ding")]))
    S.append(card("03", 3.5, K.intro_fn(), [(0, "pop"), (1.4, "ding")]))

    S.append(feat("04", 2.5, "V01", stat(0.5, 2.5), "① 一頁看完今天", "一頁看完", "早上不用開 5 個 App，這頁十秒看完今天", "總覽",
                  focus=F((440, 100, 3140, 410), "四張摘要卡", "V01", 0.5, t_zoom=1.0), idle=[(0, "talk_happy"), (1.5, "face_nod")]))
    S.append(feat("05", 3.0, "V02", act(2.0, 3.0, 1.0, 0.8), "今日事件不漏看", "不漏看", "國際、科技、總經消息，按時間排好", "總覽",
                  focus=F((2360, 60, 3186, 1500), "今日事件清單", "V02", 1.7, t_zoom=2.2), idle="news"))
    S.append(feat("06", 3.0, "V27", act(2.4, 3.0, 1.4, 0.8), "想看什麼，打幾個字就到", "打幾個字", "點搜尋，熱門股票和最近看過的先列給你", "搜尋",
                  focus=F((20, 150, 800, 1300), "搜尋下拉", "V27", 2.1, t_zoom=2.6), idle="face_wink"))
    S.append(feat("07", 3.0, "V27", [(0, 5.0), (3.0, 9.0)], "打代號或名稱", "代號", "打代號或名稱，點一下直接到那一頁", "搜尋",
                  focus=F((20, 150, 900, 440), "搜尋框與建議", "V27", 1.0, zoom=False), idle=[(0, "face_wink"), (2.0, "talk_excited")]))
    S.append(feat("08", 3.0, "V03", [(0, 3.1), (0.7, 3.1), (0.7001, 9.9), (3.0, 13.35)], "② 大日子排一起", "大日子", "財報、法說、FED 公布日，一張月曆排好", "財經日曆",
                  focus=F((2300, 300, 3150, 1720), "本週重點與說明", "V03", 1.8, zoom=False), idle="calendar"))
    S.append(feat("09", 2.5, "V04", stat(2.0, 2.5), "③ 錢往哪裡跑", "錢", "每個族群在領先還是落後，一看就知道", "資金流向",
                  focus=F((600, 480, 1960, 1640), "資金輪盤", "V04", 0.5, t_zoom=1.0), idle=[(0, "face_think"), (1.4, "talk_explain")]))
    S.append(feat("10", 2.5, "V05", [(0, 3.0), (2.5, 5.5)], "大盤的錢分去哪", "分去哪", "從大盤分到產業鏈、族群，再到代表股", "資金流向",
                  focus=F((440, 520, 2150, 1250), "分流樹", "V05", 0.5, t_zoom=1.0), idle="spotlight"))
    S.append(feat("11", 2.0, "V07", stat(3.3, 2.0), "法人資金在哪", "法人", "法人的錢集中在哪幾個族群，也整理好了", "資金流向",
                  focus=F((480, 100, 1820, 1290), "族群×法人", "V07", 0.4, zoom=False), idle="magnifier"))
    S.append(feat("12", 2.5, "V08", stat(3.1, 2.5), "④ 哪裡熱一眼看", "一眼看", "整個台股一張圖：越大成交越多，紅漲綠跌", "熱力圖",
                  focus=F((480, 200, 2260, 1120), "半導體區塊", "V08", 0.5, t_zoom=1.0), idle=[(0, "magnifier"), (1.5, "face_star")]))
    S.append(feat("13", 3.0, "V09", [(0, 3.1), (0.6, 3.1), (0.6001, 12.4), (3.0, 15.5)], "題材資金熱力", "題材", "題材有多熱？資金、法人、新聞合成 0～100 分", "熱力圖",
                  focus=F((440, 110, 3140, 1480), "題材熱力圖", "V09", 0.3, zoom=False), idle=[(0, "fire"), (2.0, "face_love")]))
    S.append(feat("14", 2.0, "V08", act(13.3, 2.0, 1.0, 0.8), "點進產業鏈", "產業鏈", "看到熱的，點下去就進產業鏈", "熱力圖",
                  idle=[(0, "face_star")]))
    S.append(feat("15", 2.0, "V11", stat(0.5, 2.0), "⑤ 產業鏈地圖", "產業鏈", "半導體、AI 伺服器…每條產業鏈都拆好了", "產業地圖",
                  focus=F((440, 70, 3130, 250), "產業鏈分頁", "V11", 0.4, zoom=False), idle="talk_explain"))
    S.append(feat("16", 2.5, "V11", stat(15.0, 2.5), "2D 看懂產業鏈", "2D", "圓圈編號對到說明卡，每段在做什麼都寫好", "產業地圖",
                  focus=F((440, 360, 3150, 1500), "2D 剖析圖", "V11", 0.5, t_zoom=1.0), idle=[(0, "talk_explain"), (1.5, "face_nod")]))
    S.append(feat("17", 2.0, "V12a", [(0, 1.2), (2.0, 2.9)], "切到 3D！", "3D", "點「3D」，整台機櫃立體拆開看", "產業地圖",
                  focus=F((2480, 215, 2740, 285), "2D｜3D 切換", "V12a", 0.4, zoom=False), idle="3dglasses"))
    S.append(feat("18", 3.0, "V12a", [(0, 3.2), (3.0, 9.0)], "拖一下就轉", "拖一下", "AI 伺服器 3D：拖曳旋轉，換個角度看", "產業地圖",
                  idle="face_star"))
    S.append(feat("19", 3.5, "V12e", [(0, 3.1), (1.5, 4.6), (1.5001, 8.5), (3.5, 10.5)], "零件是誰做的", "誰做的", "點零件，就知道哪家公司負責、在產業鏈哪一層", "產業地圖",
                  focus=F((520, 740, 3120, 1130), "CCL 銅箔基板說明卡", "V12e", 2.0, zoom=False), idle="face_proud"))
    S.append(card("20", 3.0, K.grid_fn(3.0, 1.9), [(0, "swish")]))
    S.append(card("21", 2.0, K.more_fn(), [(0.5, "pop")]))
    # TODO（個股頁 v3d 素材到齊後補）：總覽 4、AI 分析 8～10（多鏡逐區塊框出）、營收 3、獲利 3、法人 3、其餘合 3
    S.append(feat("22", 3.0, "V14", act(4.3, 3.0, 1.6, 0.8), "⑥ 個股一頁全有", "一頁全有", "K 線、多週期、營收、獲利、籌碼，一頁全看得到", "個股",
                  focus=F((480, 380, 3150, 1000), "K 線", "V14", 1.5, zoom=False), idle="face_nod"))
    S.append(feat("23", 2.5, "V15", act(1.8, 2.5, 1.0, 0.8), "營收一眼看", "營收", "月營收、年增率，每個月都有", "個股",
                  idle="face_nod"))
    S.append(feat("24", 2.5, "V15", act(7.4, 2.5, 1.0, 0.8), "法人動向", "法人", "三大法人買賣，資券、大戶散戶也在", "個股",
                  idle="face_think"))
    S.append(feat("25", 2.5, "V16", act(3.4, 2.5, 1.3, 0.8), "⑦ 完整名單", "完整名單", "漲跌分佈、法人連買賣、排行，完整名單都能排序", "市場明細",
                  focus=F((1880, 230, 3140, 340), "分頁列", "V16", 1.4, zoom=False), idle="face_nod"))
    S.append(feat("26", 2.5, "V17", act(6.6, 2.5, 1.0, 0.8), "⑧ 公開條件篩", "條件篩", "用公開條件篩一遍，省下自己翻的時間", "選股策略",
                  focus=F((440, 330, 3150, 1500), "條件卡", "V17", 1.4, zoom=False), idle="face_think"))
    S.append(feat("27", 2.0, "V18", stat(3.3, 2.0), "⑨ 週期統計", "週期", "每個族群過去在各月份的表現，一張表看完", "週期統計",
                  focus=F((2500, 230, 2790, 1320), "本月欄", "V18", 0.4, t_zoom=0.95), idle="hourglass"))
    S.append(feat("28", 2.5, "V19", act(4.3, 2.5, 1.3, 0.8), "⑩ ETF 配息日曆", "配息日曆", "哪天除息、配多少、多久填息，月曆全寫好", "ETF",
                  focus=F((1150, 540, 3150, 1300), "當日除息清單", "V19", 1.5, zoom=False), idle="piggy"))
    S.append(feat("29", 2.5, "V20", act(3.1, 2.5, 1.5, 0.8), "各類前五名", "前五名", "每一類最受歡迎、報酬、殖利率前五名，一目了然", "ETF",
                  focus=F((440, 180, 3150, 900), "前五名三張卡", "V20", 1.5, zoom=False), idle="trophy"))
    S.append(feat("30", 3.0, "V21", act(4.3, 3.0, 1.6, 0.8), "報酬放一起比", "一起比", "幾檔一起比，含息不含息分開算", "ETF",
                  focus=F((460, 540, 2050, 1230), "報酬走勢圖", "V21", 2.0, zoom=False), idle="face_think"))
    S.append(feat("31", 2.5, "V22", act(3.4, 2.5, 1.8, 0.8), "現金流試算", "現金流", "想每月都有配息？組合幫你排好", "ETF",
                  focus=F((440, 500, 3150, 1500), "試算圖表", "V22", 1.7, zoom=False), idle="calc"))
    S.append(feat("32", 2.5, "V23", [(0, 1.0), (1.5, 2.5), (2.5, 5.5)], "複利看得到", "複利", "配息再投入差多少，三條線並排看", "ETF",
                  focus=F((460, 400, 2150, 1330), "三條線", "V23", 1.8, zoom=False), idle="growth"))
    S.append(feat("33", 3.0, "V24", act(3.9, 3.0, 1.6, 0.8), "⑪ 存自己的股", "存自己", "想追蹤的股票存起來，每天打開就看到", "自選清單",
                  focus=F((440, 420, 3150, 1000), "自選清單", "V24", 1.9, zoom=False), idle="star_save"))
    S.append(feat("34", 2.5, "V25", act(2.0, 2.5, 1.5, 0.8), "看不懂？問比比", "問比比", "每一頁都有導覽，常見問題右下角點我", "導覽",
                  idle="face_wink"))
    S.append(feat("35", 2.5, "V26", act(13.2, 2.5, 1.0, 0.8), "一直在進步", "進步", "功能持續新增，想要什麼跟我說！", "願望清單",
                  focus=F((2362, 368, 3158, 1642), "客服面板", "V26", 1.6, zoom=False), idle="heart_wish"))
    S.append(card("36", 3.0, K.benefits_fn(), [(0.3, "pop"), (0.65, "pop"), (1.0, "pop"), (1.35, "pop")]))
    S.append(card("37", 3.0, K.end_fn(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("38", 5.0, K.disclaimer_fn()))
    return S
