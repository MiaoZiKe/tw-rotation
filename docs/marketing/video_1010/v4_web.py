"""第 4 版網頁版逐鏡規格（storyboard_v4_web.md）：一頁一段連續操作、來源時間只往前、頁序固定。

每鏡＝(頁, 素材, 來源起訖或分段, 大字, 泡泡, 比比待機序列)。點擊由錄影端事件自動帶入（比比踩下、漣漪、音效）。
同一素材相鄰兩鏡：後一鏡起點自動 ≥ 前一鏡實際終點（停留規則把前一鏡拉長時，後一鏡跟著往後挪，不回頭）。
"""
from __future__ import annotations

import v4_cards as K4
from v3_core import Lay, Op, Rec4, Shot4, plan_dwell

_LW = Lay("web")
_CUR = {}      # 素材 -> 已播到的來源秒（給下一鏡接續用）


def _hl(head):
    h = head.lstrip("①②③④⑤⑥⑦⑧⑨⑩⑪ ")
    return h[-4:] if len(h) > 4 else h


def shot(sid, page, clip, segs, head, sub, idle, chain=None, cont=False, main=None, hl=None, limit=None, win_max=None, win_keys=None, min_cap=None):
    """segs＝[(來源起, 來源迄), ...]（原速，多段＝往前跳接）。"""
    a0 = segs[0][0]
    prev = _CUR.get(clip)
    if prev is not None and a0 < prev - 1e-6:
        d = prev - a0
        segs = [(a + d, b + d) for a, b in segs]
    pts, loc = [], 0.0
    for a, b in segs:
        if pts:
            pts.append((loc + 1e-4, a))
        else:
            pts.append((0.0, a))
        loc += b - a
        pts.append((loc, b))
    D = round(loc, 2)
    rec = Rec4(clip, pts, main=main)
    rec.win_max = win_max
    rec.win_keys = win_keys
    op = Op(rec, idle=idle, chain=chain)
    D, dw = plan_dwell(rec, op, D, sub, _LW, None, chain, cont=cont, min_cap=min_cap)
    sh = Shot4(sid, D, [rec], pill=page, head=head, hl=hl or _hl(head), sub=sub, op=op)
    if chain:
        dw = {"units": 1, "min_req": 0, "reading": round(len(sub) / 6.5 + 0.3, 2), "D": D, "reached": True, "hold": 0.0, "note": "連續點擊（比比直接彈到下一顆）", "ok": True}
    sh.dwell = dw
    # 實際播到的來源秒
    from v3_guard import used_ranges
    if limit is not None and max(b for _, b in used_ranges(rec, D)) > limit:
        # 停留規則把鏡頭拉長、但素材之後是避開時段：播到 limit 就停在那一格（凍結），不往後播
        keep = [(l_, s_) for l_, s_ in pts if s_ <= limit + 1e-6]
        l_last, s_last = keep[-1]
        if s_last < limit - 1e-3:
            keep.append((l_last + (limit - s_last), limit))
        keep.append((max(D, keep[-1][0] + 0.01), keep[-1][1]))
        rec.srcmap = keep
        sh.dwell["note"] = (sh.dwell.get("note") or "") + f"素材播到 {limit}s 停格（之後是避開時段）"
    _CUR[clip] = max(b for _, b in used_ranges(rec, D))
    return sh


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def grid_card(sid, grid, D=3.0):
    """3D 四宮格卡片：宣告用到的素材與來源區段，讓守門也檢查到（來回切換、壞畫面）。"""
    sh = card(sid, D, K4.grid4_fn(GRID_W, GRID_M), [(0, "pop"), (0.4, "pop"), (0.8, "pop")])
    sh.uses = [(c, st, st + D) for c, _, _, st in grid]
    return sh


GRID_W = [("V12a_desktop", "AI 伺服器", (900, 523, 2600, 1437), 6.0), ("V12b_desktop", "CoWoS-L 先進封裝", (1030, 663, 2730, 1577), 3.5),
          ("V12c_desktop", "HBM 記憶體", (1030, 643, 2730, 1557), 3.5), ("V12d_desktop", "液冷散熱", (1050, 443, 2750, 1357), 3.5)]
GRID_M = [("V12a_mobile", "AI 伺服器", (235, 900, 935, 1900), 6.2), ("V12b_mobile", "CoWoS-L 先進封裝", (235, 900, 935, 1900), 3.1),
          ("V12c_mobile", "HBM 記憶體", (235, 900, 935, 1900), 3.1), ("V12d_mobile", "液冷散熱", (235, 900, 935, 1900), 3.1)]


def build():
    _CUR.clear()
    S = []
    # 0 開場（11.0 秒）
    S.append(card("a01", 2.0, K4.opening_fn(1), [(0, "pop")]))
    S.append(card("a02", 2.0, K4.opening_fn(2), [(0, "pop")]))
    S.append(card("a03", 2.0, K4.opening_fn(3), [(0, "ding")]))
    S.append(card("a04", 2.0, K4.logo_fn(), [(0, "swish"), (0.4, "ding")]))
    S.append(card("a05", 3.0, K4.intro4_fn(), [(0.2, "pop")]))
    # 1 總覽（含今日事件、搜尋）
    S.append(shot("b01", "總覽", "V01_desktop", [(0.0, 2.2)], "① 每天先看這頁", "我先帶你看今天大盤", [(0, "talk_explain"), (1.2, "folder")]))
    S.append(shot("b02", "總覽", "V02_desktop", [(1.4, 4.8)], "今日事件不漏看", "重要消息我幫你列好", [(0, "news"), (1.8, "face_surprise_happy")]))
    S.append(shot("b03", "總覽", "V27_desktop", [(1.7, 5.3)], "打幾個字就到", "想查哪檔，打簡稱就找到", [(0, "magnifier"), (2.4, "face_relief")]))
    # 2 財經日曆（一段連續錄影）
    S.append(shot("c01", "財經日曆", "V03_desktop", [(9.4, 11.8)], "② 財經日曆", "財報、法說、FED 我排好了", [(0, "calendar"), (1.2, "face_think")], cont=True))
    S.append(shot("c02", "財經日曆", "V03_desktop", [(12.4, 16.6)], "重要日子不漏看", "點一下，說明馬上出來", [(0, "face_shock"), (1.6, "globe"), (3.2, "face_nod")]))
    # 3 資金流向（播放鏡用 60fps 素材）
    S.append(shot("d01", "資金流向", "V04_desktop_v3c", [(1.4, 3.6)], "③ 錢往哪裡跑", "錢跑去哪？我帶你看", [(0, "talk_happy"), (1.2, "face_curious")]))
    S.append(shot("d02", "資金流向", "V04_desktop_v3c", [(3.6, 7.2)], "按播放看輪動", "族群怎麼輪，一路播給你", [(0, "coins"), (2.2, "face_surprise_happy")]))
    S.append(shot("d03", "資金流向", "V06_desktop_v3c", [(2.4, 4.4)], "資金分流樹", "大盤的錢分去哪？", [(0, "talk_explain"), (1.0, "face_think")], cont=True))
    S.append(shot("d04", "資金流向", "V06_desktop_v3c", [(4.4, 7.4)], "每天分流一路播", "錢從哪流到哪，一看就懂", [(0, "spotlight"), (2.0, "face_love")]))
    # 4 熱力圖
    S.append(shot("e01", "熱力圖", "V08_desktop", [(0.05, 3.05)], "④ 哪裡熱一眼看", "方塊越大，錢越多", [(0, "magnifier"), (1.5, "face_shock")], min_cap=3.0))
    S.append(shot("e02", "熱力圖", "I01_desktop_v3i", [(1.2, 4.2)], "題材熱度", "熱門題材，我拆開給你看", [(0, "talk_excited"), (1.4, "fire")], cont=True))
    S.append(shot("e03", "熱力圖", "I01_desktop_v3i", [(6.4, 9.4)], "一步一步看懂", "從晶片到整櫃，照順序看", [(0, "bulb"), (1.6, "face_thinking_bulb")], chain="solo"))
    # 5 產業地圖（2D → 3D → 四宮格 → 關聯圖）
    S.append(shot("f01", "產業地圖", "V11_desktop", [(14.2, 17.2)], "⑤ 產業鏈 2D", "上下游怎麼排，一張看懂", [(0, "talk_explain"), (1.4, "pointer_r")]))
    S.append(shot("f02", "產業地圖", "V12a_desktop", [(2.0, 6.0)], "3D 拆開看", "戴上眼鏡，推一下就轉！", [(0, "3dglasses"), (2.0, "face_star")]))
    S.append(grid_card("f03", GRID_W))
    S.append(shot("f04", "產業地圖", "V13_desktop", [(1.1, 4.3)], "上下游一張連", "滑過去，供貨關係就亮", [(0, "point_r"), (2.2, "face_love")]))
    # 6 個股（K 線＋切一次週期 → 下方總覽 → 旁邊點營收、獲利）
    # 個股：錄影端補錄的 D10（一開場就是日 K，沒有分時圖、沒有「非即時」浮水印）一段連續操作：日 K → 點週 → 往下看總覽 → 點營收 → 點獲利
    D10 = "D10_desktop_v3j"
    S.append(shot("g01", "個股", D10, [(1.1, 3.4)], "⑥ 個股一頁看", "這檔的走勢，我幫你打開", [(0, "talk_explain"), (1.0, "face_curious")]))
    S.append(shot("g02", "個股", D10, [(3.9, 7.0)], "週期一鍵切", "日、週、月，點一下切換", [(0, "face_nod")]))
    S.append(shot("g03", "個股", D10, [(9.1, 11.3)], "下方看總覽", "基本面、籌碼，重點整理好", [(0, "bulb"), (1.0, "face_thinking_bulb")]))
    S.append(shot("g04", "個股", D10, [(11.9, 13.0), (15.5, 17.2)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", [(0, "face_proud"), (0.9, "magnifier")], hl="營收獲利"))
    S.append(shot("g05", "個股", D10, [(18.3, 19.4), (21.9, 23.6)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", [(0, "face_proud"), (1.0, "face_nod")], hl="營收獲利"))
    S.append(shot("h01", "市場明細", "V16_desktop", [(2.9, 5.6)], "⑦ 市場明細", "漲停、成交值，名單直接看", [(0, "pointer_l"), (1.4, "face_curious")]))
    S.append(shot("h02", "選股策略", "V17_desktop", [(6.1, 9.1)], "⑧ 條件分好類", "技術、籌碼，分面向整理", [(0, "folder"), (1.4, "face_nod")]))
    S.append(shot("h03", "週期統計", "V18_desktop", [(4.0, 6.8)], "⑨ 週期統計", "歷年月份規律，一張表", [(0, "hourglass"), (1.4, "face_think")]))
    # 10 ETF（I03 不用；報酬比較用 V21 勾選完成後的結果段）
    S.append(shot("i01", "ETF", "V19_desktop", [(3.6, 6.8)], "⑩ ETF 配息曆", "存 ETF？哪天除息我標好", [(0, "piggy"), (1.6, "face_love")]))
    S.append(shot("i02", "ETF", "V20_desktop", [(2.4, 5.4)], "各類前五名", "配息、市值型，前五名", [(0, "trophy"), (1.6, "face_proud")]))
    S.append(shot("i03", "ETF", "V21_desktop", [(10.9, 13.4)], "報酬一起比", "含息不含息分開算", [(0, "face_think"), (1.2, "point_ur")]))
    S.append(shot("i04", "ETF", "V13b_desktop_v3e", [(7.1, 10.3)], "三張圖一起亮", "點一檔，現金流三圖連動", [(0, "calc"), (2.0, "face_surprise_happy")]))
    S.append(shot("i05", "ETF", "V23_desktop", [(1.5, 2.3), (5.3, 7.4)], "複利怎麼長大", "再投入和領現金，並排看", [(0, "face_determined"), (1.0, "growth")], hl="長大"))
    # 11～13 自選清單／導覽／願望清單
    S.append(shot("j01", "自選清單", "V24_desktop", [(6.6, 10.4)], "⑪ 自選清單", "常看的收進來，一開就有", [(0, "star_save"), (2.2, "face_love")],
                  win_keys=[(0.0, (0, 0, 2990, 1682))]))
    S.append(shot("j02", "導覽", "V25_desktop", [(1.4, 4.6)], "看不懂有導覽", "每一頁我都一步步帶你", [(0, "talk_happy"), (1.8, "face_wink")]))
    S.append(shot("j03", "願望清單", "V26_desktop", [(12.5, 16.1)], "歡迎許願", "想要什麼功能，跟我說！", [(0, "heart_wish"), (1.6, "face_love")], chain="solo"))
    # 14～15 片尾與警語
    S.append(card("k01", 3.0, K4.end4_fn(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("k02", 5.0, K4.disclaimer4_fn()))
    return S
