"""第 4 版手機版逐鏡規格（storyboard_v4_mobile.md）：同網頁版台詞與頁序，素材換手機錄影。
版面（CEO 10-12）：標題、比比＋泡泡、小字都在上方 Reels 安全區；網站框 1000×1480 在下（見 v3_core.Lay 的 V4 分支）。
"""
from __future__ import annotations

import v4_cards as K4
from v3_core import Lay, Op, Rec4, Shot4, plan_dwell
from v4_web import GRID_M, GRID_W, _hl, card, grid_card, idle_sub, nofab

_LM = Lay("mobile")
_CUR = {}


def shot(sid, page, clip, segs, head, sub, idle, pan=None, chain=None, cont=False, fixed=None, hl=None, limit=None, keys=None, min_cap=None, noev=False, wk=None):
    """pan＝(ya, yb)：沒有點擊的鏡頭慢慢平移；有點擊的鏡頭由 plan_mobile 依點擊與內容區自動排（只看上段重點，不滑到底）。
    fixed＝y：整鏡視窗固定在這個高度（例：自選清單避開「1／5 頁」字樣）。"""
    clip = nofab(clip)
    a0 = segs[0][0]
    prev = _CUR.get(clip)
    if prev is not None and a0 < prev - 1e-6:
        d = prev - a0
        segs = [(a + d, b + d) for a, b in segs]
    pts, loc = [], 0.0
    for a, b in segs:
        pts.append((loc + 1e-4, a) if pts else (0.0, a))
        loc += b - a
        pts.append((loc, b))
    D = round(loc, 2)
    pan_ = None
    if fixed is not None:
        pan_ = (fixed, fixed, 0.3, 0.3)
    elif pan:
        pan_ = (pan[0], pan[1], 0.3, 0.3 + 0.6 * D) if abs(pan[1] - pan[0]) > 1 else (pan[0], pan[0], 0.3, 0.3)
    rec = Rec4(clip, pts, pan=pan_)
    rec.meta = {}
    if wk:
        rec.win_keys = wk      # 手機推近（來源座標，寬 ≥1000 → 倍率 ≤1.0）；只用在沒有點擊的鏡頭
    rec.top_only = True
    op = Op(rec, idle=idle_sub(idle), chain=chain, use_events=not noev)
    D, dw = plan_dwell(rec, op, D, sub, _LM, pan_, chain, no_solve=fixed is not None, cont=cont, min_cap=min_cap)
    sh = Shot4(sid, D, [rec], pill=page, head=head, hl=hl or _hl(head), sub=sub, op=op)
    if fixed is not None:
        rec.pan_keys = keys or [(0.0, fixed), (1.0, fixed)]
        dw["note"] = (dw.get("note") or "") + f"視窗固定 y={fixed}（避開畫面上的字樣）"
    if chain:
        dw = {"units": 1, "min_req": 0, "reading": round(len(sub) / 6.5 + 0.3, 2), "D": D, "reached": True, "hold": 0.0, "note": "連續點擊（比比直接彈到下一顆）", "ok": True}
    sh.dwell = dw
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


def build():
    _CUR.clear()
    S = []
    S.append(card("a01", 2.0, K4.opening_fn(1), [(0, "pop")]))
    S.append(card("a02", 2.0, K4.opening_fn(2), [(0, "pop")]))
    S.append(card("a03", 2.0, K4.opening_fn(3), [(0, "ding")]))
    S.append(card("a04", 2.0, K4.logo_fn(), [(0, "swish"), (0.4, "ding")]))
    S.append(card("a05", 3.0, K4.intro4_fn(), [(0.2, "pop")]))
    S.append(shot("b01", "總覽", "V01_mobile", [(0.0, 2.2)], "① 每天先看這頁", "我先帶你看今天大盤", [(0, "talk_explain"), (1.2, "folder")], pan=(0, 300)))
    S.append(shot("b02", "總覽", "V02_mobile", [(3.6, 7.4)], "今日事件不漏看", "重要消息我幫你列好", [(0, "news"), (1.8, "face_surprise_happy")]))
    S.append(shot("b03", "總覽", "V27_mobile", [(5.8, 8.8)], "打幾個字就到", "想查哪檔，打簡稱就找到", [(0, "magnifier"), (2.4, "face_relief")], min_cap=3.2))
    S.append(shot("c01", "財經日曆", "V03_mobile_v3b", [(9.4, 11.8)], "② 財經日曆", "財報、法說、FED 我排好了", [(0, "calendar"), (1.2, "face_think")], cont=True))
    S.append(shot("c02", "財經日曆", "V03_mobile_v3b", [(12.4, 16.6)], "重要日子不漏看", "點一下，說明馬上出來", [(0, "face_shock"), (1.6, "globe"), (3.2, "face_nod")]))
    S.append(shot("d01", "資金流向", "V04_mobile_v3c", [(1.4, 3.6)], "③ 錢往哪裡跑", "錢跑去哪？我帶你看", [(0, "talk_happy"), (1.2, "face_curious")], pan=(300, 500)))
    S.append(shot("d02", "資金流向", "V04_mobile_v3c", [(3.6, 7.2)], "按播放看輪動", "族群怎麼輪，一路播給你", [(0, "coins"), (2.2, "face_surprise_happy")]))
    S.append(shot("d03", "資金流向", "V06_mobile_v3c", [(2.4, 4.28)], "資金分流樹", "大盤的錢分去哪？", [(0, "talk_explain"), (1.0, "face_think")], cont=True))
    S.append(shot("d04", "資金流向", "V06_mobile_v3c", [(7.0, 10.0)], "每天分流一路播", "錢從哪流到哪，一看就懂", [(0, "spotlight"), (2.0, "face_love")], pan=(200, 700)))
    S.append(shot("e01", "熱力圖", "V08_mobile", [(0.05, 3.05)], "④ 哪裡熱一眼看", "方塊越大，錢越多", [(0, "magnifier"), (1.5, "face_shock")], pan=(300, 700), min_cap=3.0))
    S.append(shot("e02", "熱力圖", "I01_mobile_v3i", [(2.7, 5.5)], "題材熱度", "熱門題材，我拆開給你看", [(0, "talk_excited"), (1.4, "fire")], cont=True, min_cap=3.2))
    S.append(shot("e03", "熱力圖", "I01_mobile_v3i", [(6.4, 9.4)], "一步一步看懂", "從晶片到整櫃，照順序看", [(0, "bulb"), (1.6, "face_thinking_bulb")], chain="solo"))
    S.append(shot("f01", "產業地圖", "V11_mobile", [(14.9, 17.9)], "⑤ 產業鏈 2D", "上下游怎麼排，一張看懂", [(0, "talk_explain"), (1.4, "pointer_r")], wk=[(0.0, (70, 880, 1070, 2360))]))
    S.append(shot("f02", "產業地圖", "V12a_mobile", [(2.0, 6.0)], "3D 拆開看", "戴上眼鏡，推一下就轉！", [(0, "3dglasses"), (2.0, "face_star")], pan=(700, 700)))
    S.append(grid_card("f03", GRID_M))
    # 手機錄影沒有「滑過」動作（hover 落在畫面外、連線不亮），台詞改成畫面實際有的：上下游供貨關係一張連起來；視窗固定在關聯圖本體
    S.append(shot("f04", "產業地圖", "V13_mobile_v3b", [(1.2, 3.3)], "上下游一張連", "上下游供貨關係，連成一張圖", [(0, "point_r"), (2.0, "face_love")], fixed=1250, noev=True, limit=4.1))
    D10 = "D10_mobile_v3j"
    S.append(shot("g01", "個股", D10, [(1.1, 3.4)], "⑥ 個股一頁看", "這檔的走勢，我幫你打開", [(0, "talk_explain"), (1.0, "face_curious")], pan=(300, 300)))
    S.append(shot("g02", "個股", D10, [(3.9, 7.0)], "週期一鍵切", "日、週、月，點一下切換", [(0, "face_nod")]))
    S.append(shot("g03", "個股", D10, [(8.9, 11.1)], "下方看總覽", "基本面、籌碼，重點整理好", [(0, "bulb"), (1.0, "face_thinking_bulb")], pan=(0, 300)))
    S.append(shot("g04", "個股", D10, [(11.5, 12.6), (14.9, 16.6)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", [(0, "face_proud"), (0.9, "magnifier")], hl="營收獲利"))
    S.append(shot("g05", "個股", D10, [(20.3, 21.4), (23.7, 25.4)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", [(0, "face_proud"), (1.0, "face_nod")], hl="營收獲利"))
    S.append(shot("h01", "市場明細", "V16_mobile", [(7.8, 10.0)], "⑦ 市場明細", "法人連買賣，名單直接看", [(0, "pointer_l"), (1.4, "face_curious")], min_cap=3.0))
    S.append(shot("h02", "選股策略", "V17_mobile", [(6.1, 9.1)], "⑧ 條件分好類", "技術、籌碼，分面向整理", [(0, "folder"), (1.4, "face_nod")]))
    S.append(shot("h03", "週期統計", "V18_mobile", [(3.8, 6.8)], "⑨ 週期統計", "歷年月份規律，一張表", [(0, "hourglass"), (1.4, "face_think")]))
    S.append(shot("i01", "ETF", "V19_mobile_v3b", [(3.6, 6.8)], "⑩ ETF 配息曆", "存 ETF？哪天除息我標好", [(0, "piggy"), (1.6, "face_love")]))
    # 手機 ETF 順序：報酬比較（配息型）→ 各類前五名（配息型→市值型），類型只往前切、不回頭（錄影 V21 的類型＝V20 開場的類型）
    S.append(shot("i02", "ETF", "V21_mobile_v3b", [(10.9, 12.9)], "報酬一起比", "含息不含息分開算", [(0, "face_think"), (1.2, "point_ur")], pan=(0, 700)))
    S[-1].note = "過去表現不代表未來"
    S.append(shot("i03", "ETF", "V20_mobile", [(2.4, 5.6)], "各類前五名", "配息、市值型，前五名", [(0, "trophy"), (1.6, "face_proud")], min_cap=3.2))
    S[-1].note = "過去表現不代表未來"
    S.append(shot("i04", "ETF", "V13b_mobile_v3e", [(5.6, 9.0)], "三張圖一起亮", "點一檔，現金流三圖連動", [(0, "calc"), (2.0, "face_surprise_happy")], min_cap=3.4))
    S.append(shot("i05", "ETF", "V23_mobile", [(2.6, 5.7)], "複利怎麼長大", "再投入和領現金，並排看", [(0, "face_determined"), (1.0, "growth")], hl="長大"))
    S.append(shot("j01", "自選清單", "V24_mobile", [(6.6, 10.4)], "⑪ 自選清單", "常看的收進來，一開就有", [(0, "star_save"), (2.2, "face_love")], fixed=540))
    S.append(shot("j02", "導覽", "V25_mobile", [(1.4, 4.8)], "看不懂有導覽", "每一頁我都一步步帶你", [(0, "talk_happy"), (1.8, "face_wink")], chain="solo", min_cap=3.0))
    S.append(shot("j03", "願望清單", "V26_mobile", [(13.3, 16.9)], "歡迎許願", "想要什麼功能，跟我說！", [(0, "heart_wish"), (1.6, "face_love")], chain="solo", fixed=800))
    S.append(card("k01", 3.0, K4.end4_fn(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("k02", 5.0, K4.disclaimer4_fn()))
    return S
