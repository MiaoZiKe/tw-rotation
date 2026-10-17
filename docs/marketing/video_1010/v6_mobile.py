"""第 6 版手機版逐鏡規格（storyboard_v6_mobile.md）：從 v4_mobile.py 複製改寫（v4 檔不改）。台詞、頁序、兩拍表情同網頁版。
點擊一律「指尖圓點＋漣漪」（B），比比留在窄帶待機位；漣漪圓心＝錄影當下量到的元素中心經平移換算。
"""
from __future__ import annotations

import v4_cards as K4
import v6_cards as K6
from v3_core import Lay, Op, Rec4, Shot4, plan_dwell
from v4_web import GRID_M, GRID_W, _hl, fresh_nofab, nofab
from v6_web import _find, card, first_tap, tap_times, two_beats

_LM = Lay("mobile")
_CUR = {}
SHIFTS = []


def shot(sid, page, clip, segs, head, sub, talk, react, mv=None, pan=None, cont=False, fixed=None, hl=None, limit=None, keys=None, min_cap=None,
         noev=False, wk=None, no_host=False, react_t=None):
    clip = nofab(clip)
    a0 = segs[0][0]
    prev = _CUR.get(clip)
    if prev is not None and a0 < prev - 1e-6:
        d = prev - a0     # 上一鏡被停留規則拉長、播過頭：這一鏡整段往後挪（來源只往前），並記下來
        print(f"⚠ {sid}：來源起點 {a0} 早於上一鏡已播到 {prev:.2f}，整段往後挪 {d:.2f} 秒")
        SHIFTS.append((sid, a0, round(d, 2)))
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
    ft = None if noev else first_tap(clip, segs[0][0], segs[-1][1])
    rt = react_t
    if rt is None:
        rt = 1.0
        if ft is not None:
            from v3_core import inv_srcmap
            lt = inv_srcmap(pts, ft)
            if lt is not None:
                rt = lt + 0.3
    rec = Rec4(clip, pts, pan=pan_)
    rec.meta = {}
    if wk:
        rec.win_keys = wk
    rec.top_only = True
    op = Op(rec, idle=two_beats(talk, react, rt, mv), use_events=not noev, mode_b=True, no_host=no_host)
    D, dw = plan_dwell(rec, op, D, sub, _LM, pan_, None, no_solve=fixed is not None, cont=cont, min_cap=min_cap)
    sh = Shot4(sid, D, [rec], pill=page, head=head, hl=hl or _hl(head), sub=sub, op=op)
    if fixed is not None:
        rec.pan_keys = keys or [(0.0, fixed), (1.0, fixed)]
        dw["note"] = (dw.get("note") or "") + f"視窗固定 y={fixed}"
    sh.dwell = dw
    from v3_guard import used_ranges
    if limit is not None and max(b for _, b in used_ranges(rec, D)) > limit:
        keep = [(l_, s_) for l_, s_ in pts if s_ <= limit + 1e-6]
        l_last, s_last = keep[-1]
        if s_last < limit - 1e-3:
            keep.append((l_last + (limit - s_last), limit))
        keep.append((max(D, keep[-1][0] + 0.01), keep[-1][1]))
        rec.srcmap = keep
        sh.dwell["note"] = (sh.dwell.get("note") or "") + f"素材播到 {limit}s 停格（之後是避開時段）"
    _CUR[clip] = max(b for _, b in used_ranges(rec, D))
    return sh


def grid_card(sid, D=2.6):
    sh = card(sid, D, K4.grid4_fn(GRID_W, GRID_M), [(0, "pop"), (0.4, "pop"), (0.8, "pop")])
    sh.uses = [(c, st, st + D) for c, _, _, st in GRID_M]
    return sh


ART_M = "V28_mobile_v6_nofab"
PLAY_M = "V29_mobile_v6"


def build():
    _CUR.clear()
    S = []
    S.append(card("a01", 2.8, K6.opening6(1), [(0, "pop")]))
    S.append(card("a02", 2.8, K6.opening6(2), [(0, "pop")]))
    S.append(card("a03", 2.8, K6.opening6(3), [(0, "ding")]))
    S.append(card("a04", 1.8, K6.logo6(), [(0, "swish"), (0.4, "ding")]))
    S.append(card("a05", 2.8, K4.intro4_fn(), [(0.2, "pop")]))
    S.append(shot("b01", "總覽", "V01_mobile", [(0.0, 2.2)], "① 每天先看這頁", "我先帶你看今天大盤", "talk_happy_v2", "folder", mv="hop_l", pan=(0, 300)))
    S.append(shot("b02", "總覽", "V02_mobile", [(1.7, 2.4), (4.1, 6.4)], "今日事件不漏看", "重要消息我幫你列好", "news", "face_surprise_happy", fixed=0))
    S.append(shot("b03", "總覽", "V27_mobile", [(5.7, 8.5)], "打幾個字就到", "想查哪檔，打簡稱就找到", "magnifier", "face_relief", min_cap=3.2))
    S.append(shot("c01", "財經日曆", "V03_mobile_v3b", [(10.2, 12.4)], "② 財經日曆", "財報、法說、FED 我排好了", "calendar", "talk_excited_v2", mv="slide_l", fixed=300, cont=True))
    S.append(shot("c02", "財經日曆", "V03_mobile_v3b", [(12.8, 15.6)], "重要日子不漏看", "點一下，說明馬上出來", "globe", "wow"))
    S.append(shot("d01", "資金流向", "V04_mobile_v3c", [(1.4, 3.4)], "③ 錢往哪裡跑", "錢跑去哪？我帶你看", "talk_happy_v2", "face_curious", mv="hop_l", pan=(300, 500)))
    S.append(shot("d02", "資金流向", "V04_mobile_v3c", [(3.9, 7.3)], "按播放看輪動", "族群怎麼輪，一路播給你", "coins", "face_surprise_happy", fixed=500))
    S.append(shot("d03", "資金流向", "V06_mobile_v3c", [(2.3, 4.3)], "資金分流樹", "大盤的錢分去哪？", "talk_happy_v2", "tilt", fixed=200, cont=True))
    S.append(shot("d04", "資金流向", "V06_mobile_v3c", [(7.0, 9.4)], "每天分流一路播", "錢從哪流到哪，一看就懂", "spotlight", "face_love", pan=(200, 700)))
    S.append(shot("e01", "熱力圖", "V08_mobile", [(0.05, 2.65)], "④ 哪裡熱一眼看", "方塊越大，錢越多", "magnifier", "face_shock", mv="hop_r", pan=(300, 700), min_cap=2.6))
    S.append(shot("e02", "熱力圖", "I01_mobile_v3i", [(3.5, 6.3)], "題材熱度", "熱門題材，我拆開給你看", "fire", "talk_excited_v2", fixed=400, cont=True))
    S.append(shot("e03", "熱力圖", "I01_mobile_v3i", [(6.4, 7.0), (8.6, 11.0)], "一步一步看懂", "從晶片到整櫃，照順序看", "bulb", "face_thinking_bulb", fixed=400))
    S.append(shot("f01", "產業地圖", "V11_mobile", [(15.0, 17.6)], "⑤ 產業鏈 2D", "上下游怎麼排，一張看懂", "talk_happy_v2", "spotlight", mv="hop_l", wk=[(0.0, (70, 880, 1070, 2360))], min_cap=2.4))
    S.append(shot("f02", "產業地圖", "V12a_mobile", [(2.0, 5.4)], "3D 拆開看", "戴上眼鏡，推一下就轉！", "3dglasses", "face_star", pan=(700, 700)))
    S.append(grid_card("f03"))
    S.append(shot("f04", "產業地圖", "V13_mobile_v3b", [(1.2, 3.3)], "上下游一張連", "上下游供貨關係，連成一張圖", "talk_happy_v2", "face_love", fixed=1000, noev=True, limit=4.1))
    D10 = "D10_mobile_v3j"
    S.append(shot("g01", "個股", D10, [(1.1, 3.1)], "⑥ 個股一頁看", "這檔的走勢，我幫你打開", "slide_l", "face_cool", fixed=120))
    S.append(shot("g02", "個股", D10, [(4.2, 6.6)], "週期一鍵切", "日、週、月，點一下切換", "talk_happy_v2", "face_nod_v2", fixed=120))
    S.append(shot("g03", "個股", D10, [(8.9, 11.1)], "下方看總覽", "基本面、籌碼，重點整理好", "bulb", "face_thinking_bulb", pan=(0, 300)))
    S.append(shot("g04", "個股", D10, [(11.8, 12.6), (14.9, 16.5)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", "calc", "face_proud", hl="營收獲利"))
    S.append(shot("g05", "個股", D10, [(20.6, 21.4), (23.7, 24.9)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", "magnifier", "face_nod_v2", hl="營收獲利"))
    S.append(shot("h01", "市場明細", "V16_mobile", [(8.1, 10.3)], "⑦ 市場明細", "法人連買賣，名單直接看", "coins", "face_curious", mv="slide_r", min_cap=2.2))
    S.append(shot("h02", "選股策略", "V17_mobile", [(6.3, 6.9), (7.9, 9.5)], "⑧ 條件分好類", "技術、籌碼，分面向整理", "folder", "face_nod_v2", mv="hop_l", fixed=0))
    S.append(shot("h03", "週期統計", "V18_mobile", [(3.9, 6.1)], "⑨ 週期統計", "歷年月份規律，一張表", "hourglass", "tilt", mv="hop_r", fixed=300))
    S.append(shot("i01", "ETF", "V19_mobile_v3b", [(3.8, 6.4)], "⑩ ETF 配息曆", "存 ETF？哪天除息我標好", "piggy", "face_love", mv="hop_l", fixed=300))
    S.append(shot("i02", "ETF", "V21_mobile_v3b", [(10.9, 13.3)], "報酬一起比", "含息不含息分開算", "magnifier", "face_curious", pan=(0, 700)))
    S[-1].note = "過去表現不代表未來"
    S.append(shot("i03", "ETF", "V20_mobile", [(2.8, 5.0)], "各類前五名", "配息、市值型，前五名", "trophy", "face_proud", fixed=0, min_cap=2.2))
    S[-1].note = "過去表現不代表未來"
    S.append(shot("i04", "ETF", "V13b_mobile_v3e", [(6.4, 9.2)], "兩張圖一起亮", "點一檔，甜甜圈和時鐘一起亮", "calc", "face_surprise_happy", fixed=1650))
    S.append(shot("i05", "ETF", "V23_mobile", [(1.7, 4.3)], "複利怎麼長大", "再投入和領現金，並排看", "growth", "face_star", hl="長大", fixed=0))
    S.append(shot("j01", "自選清單", "V24_mobile", [(7.6, 10.2)], "⑪ 自選清單", "常看的收進來，一開就有", "star_save", "face_love", mv="hop_r", fixed=540))
    # 12 精選文章（新）：n05 走備案（CEO 10-17）
    tk = tap_times(ART_M, "click")
    t_know = _find(tk, "比比知識")
    t_card = _find(tk, "CoWoS")
    t_e1 = _find(tk, "HBM")
    t_e2 = _find(tk, "GPU")
    S.append(shot("n01", "精選文章", ART_M, [(0.0, 2.0)], "⑫ 精選文章", "產業新知，我整理成文章", "phone", "talk_excited_v2", mv="slide_l", fixed=0, react_t=1.0))
    S.append(shot("n02", "精選文章", ART_M, [(max(2.0, t_know - 0.5), t_know + 1.5)], "分類一點就換", "快訊、產業鏈、知識分好類", "folder", "face_curious", fixed=0))
    S.append(shot("n03", "精選文章", ART_M, [(t_card - 0.4, t_card + 1.4)], "3 分鐘看懂", "點進來，重點先給你", "talk_happy_v2", "face_star"))
    S.append(shot("n04", "精選文章", ART_M, [(t_e1 - 4.7, t_e1 - 3.1), (t_e1 - 0.5, t_e1 + 1.4), (t_e2 - 0.2, t_e2 + 1.0)], "插圖拆給你看", "點一下零件，那層就亮", "bulb", "wow", min_cap=2.7, cont=True))
    S.append(shot("j02", "導覽", "V25_mobile", [(4.1, 7.1)], "看不懂有導覽", "每一頁我都一步步帶你", "talk_happy_v2", "face_wink", mv="hop_l", min_cap=2.6))
    # 14 跟比比玩（新）：視窗固定在畫面底（客服鈕與小圈都在框內），主持人不疊
    pk = tap_times(PLAY_M, "click")
    fabs = [t for t, lab in pk if "客服" in (lab or "")]
    t_ball, t_grass, t_pet, t_bub = _find(pk, "玩球"), _find(pk, "餵牧草"), _find(pk, "摸摸頭"), _find(pk, "吹泡泡")

    def fab_before(t):
        return max(x for x in fabs if x < t)
    Y = 801
    S.append(shot("p01", "跟比比玩", PLAY_M, [(fab_before(t_ball) - 0.6, t_ball - 0.3)], "⑭ 跟比比玩", "", "hop_r", "invite_nod", fixed=Y, no_host=True, min_cap=1.4))
    S.append(shot("p02", "跟比比玩", PLAY_M, [(t_ball - 0.3, t_ball + 4.3)], "丟球，比比去接", "", "hop_r", "hop_r", fixed=Y, no_host=True, min_cap=1.0))
    S.append(shot("p03", "跟比比玩", PLAY_M, [(fab_before(t_grass) - 0.3, t_grass + 2.2)], "牧草放地上吃", "", "hop_r", "hop_r", fixed=Y, no_host=True, min_cap=1.0))
    S.append(shot("p04", "跟比比玩", PLAY_M, [(fab_before(t_pet) - 0.3, t_pet + 1.6)], "摸摸頭好舒服", "", "hop_r", "hop_r", fixed=Y, no_host=True, min_cap=1.0))
    S.append(shot("p05", "跟比比玩", PLAY_M, [(fab_before(t_bub) - 0.3, t_bub + 1.8)], "還有玩具六件", "", "hop_r", "hop_r", fixed=Y, no_host=True, min_cap=1.0))
    if fresh_nofab("V26w_mobile"):
        S.append(shot("j03", "願望清單", "V26w_mobile", [(5.4, 8.2)], "歡迎許願", "想要什麼功能，跟我說！", "sign_text", "heart_wish", mv="hop_l", fixed=800))
    else:
        S.append(shot("j03", "願望清單", "V26_mobile", [(15.0, 17.8)], "歡迎許願", "想要什麼功能，跟我說！", "sign_text", "heart_wish", mv="hop_l", fixed=800))
    S.append(card("k01", 3.0, K6.end6(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("k02", 5.0, K4.disclaimer4_fn()))
    return S
