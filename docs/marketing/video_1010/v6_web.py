"""第 6 版網頁版逐鏡規格（storyboard_v6_web.md）：從 v4_web.py 複製改寫（v4 檔不改）。

跟第 5 版不同：
- 點擊一律「游標＋漣漪」（分鏡第 1 節 B）：比比留在待機位不跳去踩；漣漪圓心＝游標熱點＝錄影當下量到的元素中心（clicks.json）經鏡頭換算。
- 恢復第 5 版拿掉的點擊（鏡頭起點移到點擊前，來源時間仍只往前）。
- 新增「精選文章」（V28）與「跟比比玩」（V29，網站上的比比是主角，主持人不疊）。
- 比比每鏡兩拍：說話拍 → 反應拍（點擊後 0.3 秒換；沒有點擊在 1.0 秒換）；每頁第一鏡先做移動動作（hop／slide／peek）。
"""
from __future__ import annotations

import v4_cards as K4
import v6_cards as K6
from v3_core import Lay, Op, Rec4, Shot4, events_for, plan_dwell
from v4_web import GRID_W, _hl, fresh_nofab, nofab

_LW = Lay("web")
_CUR = {}
SHIFTS = []

# 分鏡第 3 節第 5 點：有前掌、舉手、握拳的素材全片禁用（防呆，分鏡已避開）
BANNED = {"wave", "talk_explain", "face_think", "face_determined", "face_clap", "face_thumbs", "face_shy", "magic_frame",
          "pointer_l", "pointer_r", "point_r", "point_ur", "point_dr", "face_sweat"}


def two_beats(talk, react, rt, mv=None):
    seq = []
    if mv:
        seq.append((0.0, mv))
        seq.append((0.45, talk))
    else:
        seq.append((0.0, talk))
    seq.append((max(rt, 0.5 if not mv else 0.95), react))
    for _, n in seq:
        assert n not in BANNED, n
    return seq


def first_tap(clip, a, b):
    ts = [e["t"] for e in events_for(clip) if e["kind"] in ("tap", "hover") and a <= e["t"] <= b]
    return min(ts) if ts else None


def shot(sid, page, clip, segs, head, sub, talk, react, mv=None, cont=False, main=None, hl=None, limit=None, win_max=None, win_keys=None,
         min_cap=None, no_host=False, react_t=None, hov=None):
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
    # 反應拍時間：第一個點擊／滑過之後 0.3 秒；沒有就 1.0 秒
    ft = first_tap(clip, segs[0][0], segs[-1][1])
    rt = react_t
    if rt is None:
        rt = 1.0
        if ft is not None:
            from v3_core import inv_srcmap
            lt = inv_srcmap(pts, ft)
            if lt is not None:
                rt = lt + 0.3
    rec = Rec4(clip, pts, main=main)
    rec.win_max = win_max
    rec.win_keys = win_keys
    op = Op(rec, idle=two_beats(talk, react, rt, mv), mode_b=True, no_host=no_host, soft_hover=hov)
    D, dw = plan_dwell(rec, op, D, sub, _LW, None, None, cont=cont, min_cap=min_cap)
    sh = Shot4(sid, D, [rec], pill=page, head=head, hl=hl or _hl(head), sub=sub, op=op)
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


def card(sid, D, fn, cues=()):
    return Shot4(sid, D, [], kind="card", foot=False, custom=fn, cues=cues)


def grid_card(sid, grid, D=2.6):
    sh = card(sid, D, K4.grid4_fn(GRID_W, GRID_M_), [(0, "pop"), (0.4, "pop"), (0.8, "pop")])
    sh.uses = [(c, st, st + D) for c, _, _, st in grid]
    return sh


from v4_web import GRID_M as GRID_M_  # noqa: E402


def tap_times(clip, kind="click"):
    """新素材（_v6）點擊／滑過的來源秒（錄影 log），給分鏡「每鏡起點＝點擊前 0.2～0.3 秒」用。"""
    from v3_core import load_all, _clip_keys
    allj = load_all()
    for key in _clip_keys(clip):
        ts = [(float(it["t"]), it.get("label", "")) for it in (allj.get(key) or {}).get("targets", []) if it.get("kind") == kind]
        if ts:
            return ts
    return []


# 精選文章／跟比比玩：素材名（錄影 --set v6）
ART_W = "V28_desktop_v6_nofab"
PLAY_W = "V29_desktop_v6_dsf6_close"   # 近景重錄：只截右下角 566×315 css、DPR 6（3396×1890）（CEO 10-17 審片：比比太小，近景要 ≥350px）
# 跟比比玩：推近右下角（客服鈕＋小圈＋網站比比跑去玩的範圍），1920×1080 來源視窗（輸出 1766 寬 → 倍率 ≤1，不超過原解析度）
PLAY_FULL_W = (0, 0, 3396, 1890)      # 小圈整圈＋接球路徑
PLAY_TIGHT_W = (1630, 897, 3396, 1890)  # 比比近景（倍率 1.0）


def _find(ts, key):
    for t, lab in ts:
        if key in (lab or ""):
            return t
    raise KeyError(key)


SHORT_DROP = {"b03", "d04", "e02", "f03", "g03", "g05", "i03"}


def build():
    _CUR.clear()
    S = []
    # 0 開場（13.0 秒）：三張痛點卡 1.2 倍速 2.8 秒
    S.append(card("a01", 2.8, K6.opening6(1), [(0, "pop")]))
    S.append(card("a02", 2.8, K6.opening6(2), [(0, "pop")]))
    S.append(card("a03", 2.8, K6.opening6(3), [(0, "ding")]))
    S.append(card("a04", 1.8, K6.logo6(), [(0, "swish"), (0.4, "ding")]))
    S.append(card("a05", 2.8, K4.intro4_fn(), [(0.2, "pop")]))
    # 1 總覽
    S.append(shot("b01", "總覽", "V01_desktop", [(0.0, 2.2)], "① 每天先看這頁", "我先帶你看今天大盤", "talk_happy_v2", "folder", mv="hop_l"))
    S.append(shot("b02", "總覽", "V02_desktop", [(1.6, 4.2)], "今日事件不漏看", "重要消息我幫你列好", "news", "face_surprise_happy"))
    S.append(shot("b03", "總覽", "V27_desktop", [(4.4, 6.8)], "打幾個字就到", "想查哪檔，打簡稱就找到", "magnifier", "face_relief", min_cap=3.2))
    # 2 財經日曆
    S.append(shot("c01", "財經日曆", "V03_desktop", [(10.2, 12.4)], "② 財經日曆", "財報、法說、FED 我排好了", "calendar", "talk_excited_v2", mv="slide_l", cont=True))
    S.append(shot("c02", "財經日曆", "V03_desktop", [(12.8, 13.6), (15.2, 17.2)], "重要日子不漏看", "點一下，說明馬上出來", "globe", "wow", min_cap=2.1))
    # 3 資金流向
    S.append(shot("d01", "資金流向", "V04_desktop_v3c", [(1.4, 3.4)], "③ 錢往哪裡跑", "錢跑去哪？我帶你看", "talk_happy_v2", "face_curious", mv="hop_l"))
    S.append(shot("d02", "資金流向", "V04_desktop_v3c", [(3.9, 7.3)], "按播放看輪動", "族群怎麼輪，一路播給你", "coins", "face_surprise_happy"))
    S.append(shot("d03", "資金流向", "V06_desktop_v3c", [(2.3, 4.3)], "資金分流樹", "大盤的錢分去哪？", "talk_happy_v2", "tilt", cont=True, limit=4.3))
    S.append(shot("d04", "資金流向", "V06_desktop_v3c", [(5.1, 7.5)], "每天分流一路播", "錢從哪流到哪，一看就懂", "spotlight", "face_love"))
    # 4 熱力圖
    S.append(shot("e01", "熱力圖", "V08_desktop", [(0.05, 2.55)], "④ 哪裡熱一眼看", "方塊越大，錢越多", "magnifier", "face_shock", mv="hop_r", min_cap=2.5))
    S.append(shot("e02", "熱力圖", "I01_desktop_v3i", [(4.0, 6.4)], "題材熱度", "熱門題材，我拆開給你看", "fire", "talk_excited_v2", cont=True))
    S.append(shot("e03", "熱力圖", "I01_desktop_v3i", [(6.5, 9.5)], "一步一步看懂", "從晶片到整櫃，照順序看", "bulb", "face_thinking_bulb"))
    # 5 產業地圖
    S.append(shot("f01", "產業地圖", "V11_desktop_nofab", [(11.7, 14.3)], "⑤ 產業鏈 2D", "上下游怎麼排，一張看懂", "talk_happy_v2", "spotlight", mv="hop_l"))
    S.append(shot("f02", "產業地圖", "V12a_desktop", [(2.0, 5.4)], "3D 拆開看", "戴上眼鏡，推一下就轉！", "3dglasses", "face_star"))
    S.append(grid_card("f03", GRID_W))
    S.append(shot("f04", "產業地圖", "V13_desktop", [(3.6, 6.6)], "上下游一張連", "滑過去，供貨關係就亮", "talk_happy_v2", "face_love", hov=True))
    # 6 個股
    D10 = "D10_desktop_v3j"
    S.append(shot("g01", "個股", D10, [(1.1, 3.1)], "⑥ 個股一頁看", "這檔的走勢，我幫你打開", "slide_l", "face_cool"))
    S.append(shot("g02", "個股", D10, [(4.2, 6.6)], "週期一鍵切", "日、週、月，點一下切換", "talk_happy_v2", "face_nod_v2"))
    S.append(shot("g03", "個股", D10, [(9.1, 11.3)], "下方看總覽", "基本面、籌碼，重點整理好", "bulb", "face_thinking_bulb"))
    S.append(shot("g04", "個股", D10, [(12.2, 12.9), (14.0, 14.8), (15.5, 16.4)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", "calc", "face_proud", hl="營收獲利"))
    S.append(shot("g05", "個股", D10, [(18.6, 19.2), (22.0, 23.4)], "旁邊看營收獲利", "營收、獲利，旁邊點就有", "magnifier", "face_nod_v2", hl="營收獲利"))
    # 7～9
    S.append(shot("h01", "市場明細", "V16_desktop", [(7.8, 10.0)], "⑦ 市場明細", "法人連買賣，名單直接看", "coins", "face_curious", mv="slide_r", min_cap=2.2))
    S.append(shot("h02", "選股策略", "V17_desktop", [(6.3, 6.9), (7.9, 9.5)], "⑧ 條件分好類", "技術、籌碼，分面向整理", "folder", "face_nod_v2", mv="hop_l", min_cap=2.2))
    S.append(shot("h03", "週期統計", "V18_desktop", [(4.2, 6.4)], "⑨ 週期統計", "歷年月份規律，一張表", "hourglass", "tilt", mv="hop_r", min_cap=2.2))
    # 10 ETF
    S.append(shot("i01", "ETF", "V19_desktop", [(3.8, 6.4)], "⑩ ETF 配息曆", "存 ETF？哪天除息我標好", "piggy", "face_love", mv="hop_l"))
    S.append(shot("i02", "ETF", "V20_desktop", [(2.8, 5.2)], "各類前五名", "配息、市值型，前五名", "trophy", "face_proud"))
    S[-1].note = "過去表現不代表未來"
    S.append(shot("i03", "ETF", "V20_desktop", [(5.3, 7.5)], "報酬一起比", "含息不含息分開算", "magnifier", "face_curious", limit=8.0))
    S[-1].note = "過去表現不代表未來"
    S.append(shot("i04", "ETF", "V13b_desktop_v3e", [(7.5, 10.1)], "三張圖一起亮", "點一檔，現金流三圖連動", "calc", "face_surprise_happy"))
    S.append(shot("i05", "ETF", "V23_desktop", [(1.7, 4.3)], "複利怎麼長大", "再投入和領現金，並排看", "growth", "face_star", hl="長大",
                  win_keys=[(0.0, (0, 0, 3200, 1700))]))
    # 11 自選清單
    S.append(shot("j01", "自選清單", "V24_desktop", [(7.6, 10.2)], "⑪ 自選清單", "常看的收進來，一開就有", "star_save", "face_love", mv="hop_r",
                  win_keys=[(0.0, (0, 0, 2990, 1682))]))
    # 12 精選文章（新）：素材 V28（--set v6 --nofab）；n05 影片區塊依 CEO 10-17 決定走備案（刪 n05，n04 滑過 HBM 與 GPU 兩個零件）
    tk = tap_times(ART_W, "click")
    hv = tap_times(ART_W, "hover")
    t_know = _find(tk, "比比知識")
    t_card = _find(tk, "CoWoS")
    t_h1 = _find(hv, "HBM")
    t_h2 = _find(hv, "GPU")
    S.append(shot("n01", "精選文章", ART_W, [(0.0, 2.0)], "⑫ 精選文章", "產業新知，我整理成文章", "phone", "talk_excited_v2", mv="slide_l", react_t=1.0))
    S.append(shot("n02", "精選文章", ART_W, [(max(2.0, t_know - 0.5), t_know + 1.5)], "分類一點就換", "快訊、產業鏈、知識分好類", "folder", "face_curious"))
    S.append(shot("n03", "精選文章", ART_W, [(t_card - 0.4, t_card + 1.4)], "3 分鐘看懂", "點進來，重點先給你", "talk_happy_v2", "face_star"))
    S.append(shot("n04", "精選文章", ART_W, [(t_h1 - 1.0, t_h1 + 1.6), (t_h2 - 0.1, t_h2 + 1.6)], "插圖拆給你看", "滑到零件，那一層就亮", "bulb", "wow"))
    # 13 導覽
    S.append(shot("j02", "導覽", "V25_desktop", [(5.3, 7.9)], "看不懂有導覽", "每一頁我都一步步帶你", "talk_happy_v2", "face_wink", mv="hop_l", min_cap=2.6))
    # 14 跟比比玩（新）：網站上的比比是主角，主持人不疊、不放主持人泡泡
    pk = tap_times(PLAY_W, "click")
    ph = tap_times(PLAY_W, "hover")
    t_open = ph[0][0] if ph else pk[0][0] - 0.8
    t_ball, t_grass, t_pet, t_bub = _find(pk, "玩球"), _find(pk, "餵牧草"), _find(pk, "摸摸頭"), _find(pk, "吹泡泡")
    full = [(0.0, PLAY_FULL_W)]

    def tight(a, t_item):
        return [(0.0, PLAY_FULL_W), (t_item - a + 0.5, PLAY_TIGHT_W, 1.2)]   # 點完小圈後 1.2 秒慢慢推近比比
    a1, a2, a3, a4, a5 = t_open - 0.8, t_ball - 0.3, t_grass - 0.6, t_pet - 0.6, t_bub - 0.6
    S.append(shot("p01", "跟比比玩", PLAY_W, [(a1, t_ball - 0.3)], "⑭ 跟比比玩", "", "hop_r", "invite_nod", no_host=True, win_keys=full, min_cap=1.4))
    S.append(shot("p02", "跟比比玩", PLAY_W, [(a2, t_ball + 3.7)], "丟球，比比去接", "", "hop_r", "hop_r", no_host=True, win_keys=full, min_cap=1.0))
    S.append(shot("p03", "跟比比玩", PLAY_W, [(a3, t_grass + 2.2)], "牧草放地上吃", "", "hop_r", "hop_r", no_host=True, win_keys=tight(a3, t_grass), min_cap=1.0))
    S.append(shot("p04", "跟比比玩", PLAY_W, [(a4, t_pet + 1.6)], "摸摸頭好舒服", "", "hop_r", "hop_r", no_host=True, win_keys=tight(a4, t_pet), min_cap=1.0))
    S.append(shot("p05", "跟比比玩", PLAY_W, [(a5, t_bub + 1.8)], "還有玩具六件", "", "hop_r", "hop_r", no_host=True, win_keys=tight(a5, t_bub), min_cap=1.0))
    for sh in S[-5:]:
        sh.foot_top = True
    if fresh_nofab("V26w_desktop"):
        S.append(shot("j03", "願望清單", "V26w_desktop", [(5.4, 8.2)], "歡迎許願", "想要什麼功能，跟我說！", "sign_text", "heart_wish", mv="hop_l",
                      win_keys=[(0.0, (1290, 716, 3170, 1726))]))
    else:
        S.append(shot("j03", "願望清單", "V26_desktop", [(15.0, 17.8)], "歡迎許願", "想要什麼功能，跟我說！", "sign_text", "heart_wish", mv="hop_l",
                      win_keys=[(0.0, (1290, 716, 3170, 1726))]))
    # 16～17 片尾與警語
    S.append(card("k01", 3.0, K6.end6(), [(0, "pop"), (1.0, "ding")]))
    S.append(card("k02", 5.0, K4.disclaimer4_fn()))
    import os
    if os.environ.get("V6_SHORT") == "1":
        # 精簡版（Andy 10-17「給我兩個版本」：≤125 秒）：每頁開頭鏡與點擊重點鏡都留，拿掉同頁的補充鏡
        S = [sh for sh in S if sh.sid not in SHORT_DROP]
    return S
