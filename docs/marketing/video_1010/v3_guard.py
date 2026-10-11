"""第 4 版出片前守門：來回切換檢查、錯誤畫面排除（bad_spans）、畫質（推近倍率／成片規格）。
違反就報錯、不出片（v3_build／v3_sections 會呼叫 guard()；--allow 才能放行，成片模式不可放行）。

  來回切換：① 同一鏡內來源時間不可倒退（只能前進或往前跳）；② 同一素材跨鏡，後一鏡不可從比前面更早的畫面開始；
            ③ 同一素材中途換去別的素材又換回來（A→B→A）＝來回；④ 分頁（pill）離開後不可再出現；⑤ 分頁順序依 PAGE_ORDER 單調。
  錯誤畫面：raw_v3/bad_spans.json（錄影端提供：每支素材含付費彈窗／升級／上限／登入／載入中的時段）。
            渲染使用的來源時段只要碰到就報錯。檔案不存在：預覽模式只警告，成片模式（strict）直接報錯。
            已知壞素材 BAD_KNOWN（例：ETF 報酬比較 I03 勾選超過 8 檔會跳「目前方案最多 8 檔，升級 Pro 不限」）
            在 bad_spans.json 對該素材給出明確可用時段之前，整支禁用。
"""
from __future__ import annotations

import json
from pathlib import Path

import v3_core as K

# 網站導覽順序（左側欄由上到下）；別名＝同一頁。分鏡改版時改這裡。
PAGE_ORDER = ["總覽", "財經日曆", "資金流向", "熱力圖", "產業地圖", "個股", "市場明細", "選股策略", "週期統計", "ETF", "自選清單", "導覽", "願望清單"]
PAGE_ALIAS = {"搜尋": "總覽", "今日事件": "總覽"}

# 已知會出現付費／上限視窗的素材（前綴比對）：在 bad_spans.json 給出該素材的明確時段之前整支禁用
BAD_KNOWN = {
    "I03": "ETF 報酬比較：勾選超過 8 檔會跳出「目前方案最多 8 檔，升級 Pro 不限」付費視窗（Andy 10-12）",
}

BAD_SPANS_PATH = K.RAW3 / "bad_spans.json"

# 分鏡師抽格確認的避開時段（storyboard_v4_*.md 第 7 節）：跟 bad_spans.json 一樣，碰到就報錯
_E = 9999.0
STORY_AVOID = {
    "V02_desktop": [(16.4, _E, "點新聞個股跳頁")], "V08_desktop": [(3.1, _E, "點方塊跳產業鏈")], "V11_desktop": [(2.2, 14.2, "點錯目標、點不到")],
    "V16_desktop": [(17.6, _E, "今日關注")], "V21_desktop": [(3.1, 10.9, "下拉選單「已選 7／8」上限暗示")], "V24_desktop": [(0.0, 5.6, "空清單")],
    "V26_desktop": [(0.0, 12.1, "常見問題含付費方案")], "V27_desktop": [(8.2, _E, "進個股頁（個股頁提前出現）")],
    "V02_mobile": [(18.8, _E, "點新聞個股跳頁")], "V08_mobile": [(3.1, _E, "點方塊跳產業鏈")], "V11_mobile": [(2.2, 14.9, "點到深色模式鈕、點不到"), (18.1, _E, "開說明抽屜")],
    "V13_mobile_v3b": [(4.2, _E, "滑過點座標在畫面外")], "V16_mobile": [(17.9, _E, "今日關注")], "V21_mobile_v3b": [(3.1, 10.9, "下拉選單「已選 7／8」上限暗示")],
    "V21_mobile": [(3.1, 10.9, "下拉選單「已選 7／8」上限暗示")], "V24_mobile": [(0.0, 5.6, "空清單")], "V26_mobile": [(0.0, 12.1, "常見問題含付費方案")],
    "V27_mobile": [(8.6, _E, "進個股頁（個股頁提前出現）")],
}


def _norm(clip):
    return clip.replace(".mp4", "")


def load_bad_spans():
    """回傳 (spans: {素材: [(t0, t1, 原因)]}, unchecked: set, 檔案是否存在)。
    錄影端格式：{"spans": {檔名(.mp4): [[t0, t1, 原因], ...]}, "unchecked": [素材, ...]}；也容忍 {"clips": ...} 或直接 {素材: [...]}。
    spans 裡有列（即使是空清單）＝量過；沒列或在 unchecked＝還沒量。"""
    if not BAD_SPANS_PATH.exists():
        return {}, set(), False
    d = json.loads(BAD_SPANS_PATH.read_text())
    unchecked = set()
    if isinstance(d, dict):
        unchecked = {_norm(x) for x in (d.get("unchecked") or [])}
        if isinstance(d.get("spans"), dict):
            d = d["spans"]
        elif isinstance(d.get("clips"), dict):
            d = d["clips"]
    out = {}
    for clip, v in (d.items() if isinstance(d, dict) else []):
        if clip in ("unchecked",):
            continue
        items = v.get("spans", v.get("bad", [])) if isinstance(v, dict) else v
        if not isinstance(items, list):
            continue
        lst = out.setdefault(_norm(clip), [])
        for it in items:
            if isinstance(it, dict):
                t0 = it.get("t_start", it.get("t0", it.get("start")))
                t1 = it.get("t_end", it.get("t1", it.get("end")))
                why = it.get("reason", it.get("why", it.get("kind", "")))
            else:
                t0, t1 = it[0], it[1]
                why = it[2] if len(it) > 2 else ""
            if t0 is None or t1 is None:
                continue
            lst.append((float(t0), float(t1), str(why)))
    return out, unchecked, True


def used_ranges(rec, D):
    """這一鏡實際會播出的來源時間區段 [(a, b)]（跳點不算播出；尾端凍結算一個點）。"""
    pts = list(rec.srcmap)
    out = []
    for (l0, s0), (l1, s1) in zip(pts, pts[1:]):
        if l0 >= D - 1e-9:
            break
        if l1 - l0 < 2e-3:
            continue                                  # 跳點
        if l1 > D:
            s1 = s0 + (s1 - s0) * (D - l0) / (l1 - l0)
            l1 = D
        out.append((min(s0, s1), max(s0, s1)))
    if pts:
        if pts[-1][0] < D - 1e-9:
            out.append((pts[-1][1], pts[-1][1]))      # 尾端凍結
        if not out:
            out.append((pts[0][1], pts[0][1]))
    return out


def _recs(shot):
    return [ly for ly in shot.layers if isinstance(ly, K.Rec4)]


def rank(pill):
    p = PAGE_ALIAS.get(pill, pill)
    return PAGE_ORDER.index(p) if p in PAGE_ORDER else None


def flow_check(S):
    """回傳 (違規列, 警告列)；每列 (鏡, 說明)。"""
    bad, warn = [], []
    seen_pills, last_pill, last_rank = [], None, -1
    clip_max = {}          # 素材 -> 前面鏡用到的最大來源秒
    clip_last = None
    clip_closed = set()    # 已離開的素材
    for s in S:
        recs = _recs(s)
        for r in recs:
            ps = [p for p in r.srcmap]
            for (l0, a), (l1, b) in zip(ps, ps[1:]):
                if b < a - 1e-6 and l1 > l0 - 1e-9:
                    bad.append((s.sid, f"鏡內來源時間倒退：{r.clip} {a:.2f}s → {b:.2f}s（來回切換）"))
        pill = s.pill
        if pill:
            if pill != last_pill:
                if pill in seen_pills:
                    bad.append((s.sid, f"分頁「{pill}」講完又回來（頁序必須單調）"))
                seen_pills.append(pill)
                rk = rank(pill)
                if rk is None:
                    warn.append((s.sid, f"分頁「{pill}」不在 PAGE_ORDER，未檢查順序"))
                else:
                    if rk < last_rank:
                        bad.append((s.sid, f"分頁順序倒退：「{pill}」排在前一頁之前（依網站導覽順序）"))
                    last_rank = max(last_rank, rk)
                last_pill = pill
        use = {}
        for (c, a, b) in _uses(s):
            lo, hi = use.get(c, (a, b))
            use[c] = (min(lo, a), max(hi, b))
        multi = len(use) > 1          # 四宮格這種一鏡多素材：各自檢查單調，不算 A→B→A
        for c, (lo, hi) in use.items():
            if not multi and c in clip_closed and c != clip_last:
                bad.append((s.sid, f"素材 {c} 中途換走又換回來（A→B→A，來回切換）"))
            if c in clip_max and lo < clip_max[c] - 0.05:
                bad.append((s.sid, f"素材 {c} 從 {lo:.2f}s 開始，但前面的鏡已經播到 {clip_max[c]:.2f}s（回頭重播）"))
            clip_max[c] = max(clip_max.get(c, 0.0), hi)
        if use and not multi:
            c = next(iter(use))
            if clip_last and clip_last != c:
                clip_closed.add(clip_last)
            clip_last = c
    return bad, warn


def _uses(s):
    """這一鏡用到的 (素材, 來源區段)：網站畫面圖層＋卡片自行宣告的素材（例：3D 四宮格）。"""
    out = []
    for r in _recs(s):
        out += [(_norm(r.clip), a, b) for a, b in used_ranges(r, s.dur)]
    for (c, a, b) in getattr(s, "uses", []) or []:
        out.append((_norm(c), a, b))
    return out


def freeze_check(S, limit=0.5):
    """停格檢查（CEO 10-12：全片任何停格不准超過 0.5 秒）：鏡內來源時間停住不動的連續時間、播超過素材尾端（停在最後一格）都算。"""
    bad = []
    for s in S:
        for r in _recs(s):
            pts = list(r.srcmap)
            for (l0, a), (l1, b) in zip(pts, pts[1:]):
                l1c = min(l1, s.dur)
                if l1c - l0 > limit and abs(b - a) < 1e-3:
                    bad.append((s.sid, f"停格 {l1c - l0:.2f} 秒（{r.clip} 停在 {a:.2f}s）"))
            if pts and s.dur - pts[-1][0] > limit:
                bad.append((s.sid, f"停格 {s.dur - pts[-1][0]:.2f} 秒（時間軸結束後停在 {pts[-1][1]:.2f}s）"))
            try:
                cd = K.clip_dur(r.clip)
            except Exception:
                cd = None
            if cd:
                hi = max(b for _, b in used_ranges(r, s.dur))
                if hi > cd - 0.02:
                    bad.append((s.sid, f"播到素材尾端 {cd:.2f}s 之後（停在最後一格）"))
    return bad


def span_check(S, strict=False):
    """錯誤畫面排除：回傳 (違規列, 警告列, 檔案存在)。
    strict（成片）：bad_spans.json 必須存在；素材還沒量（unchecked 或沒列）一律當壞素材擋下。"""
    spans, unchecked, exists = load_bad_spans()
    bad, warn = [], []
    if not exists:
        (bad if strict else warn).append(("全部", f"尚未提供 {BAD_SPANS_PATH.name}（錄影端的壞畫面時段表）" + ("，成片模式不可出片" if strict else "，目前只用 BAD_KNOWN 與分鏡避開時段擋")))
    seen_unc = set()
    for s in S:
        for (c, a, b) in _uses(s):
            for pre, why in BAD_KNOWN.items():
                if c.startswith(pre) and c not in spans:
                    bad.append((s.sid, f"素材 {c} 禁用：{why}（待 bad_spans.json 給出可用時段）"))
            if exists and (c in unchecked or c not in spans) and c not in seen_unc:
                seen_unc.add(c)
                (bad if strict else warn).append((s.sid, f"素材 {c} 錄影端還沒量壞畫面時段（unchecked）" + ("，成片不可用" if strict else "，預覽先用")))
            sp = list(spans.get(c, [])) + [(a_, b_, "分鏡避開：" + w_) for a_, b_, w_ in STORY_AVOID.get(c, [])]
            for (t0, t1, why) in sp:
                if a < t1 and b > t0:
                    bad.append((s.sid, f"素材 {c} 使用 {a:.2f}–{b:.2f}s，落在壞畫面時段 {t0:.2f}–{t1:.2f}s（{why}）"))
    return bad, warn, exists


def guard(S, work, label, strict=False):
    """寫 flow_check.md、bad_span_check.md；回傳違規數。"""
    work = Path(work)
    fb, fw = flow_check(S)
    fz = freeze_check(S)
    fb = fb + fz
    sb, sw, ex = span_check(S, strict)
    L1 = [f"# 來回切換檢查（{label}）", "", f"違規 {len(fb)} 筆（其中停格 {len(fz)} 筆）；警告 {len(fw)} 筆。規則：鏡內來源時間不倒退、同素材不回頭重播、不 A→B→A、分頁講完不回來、分頁順序依 PAGE_ORDER 單調；停格（來源時間停住或播過素材尾端）不得超過 0.5 秒。", "",
          "| 鏡 | 說明 |", "|---|---|"]
    L1 += [f"| {a} | {b} |" for a, b in fb] or ["| — | 全部通過 |"]
    if fw:
        L1 += ["", "警告：", *[f"- {a}：{b}" for a, b in fw]]
    (work / "flow_check.md").write_text("\n".join(L1))
    L2 = [f"# 錯誤畫面排除檢查（{label}）", "", f"bad_spans.json：{'已提供' if ex else '尚未提供'}；違規 {len(sb)} 筆。", "", "| 鏡 | 說明 |", "|---|---|"]
    L2 += [f"| {a} | {b} |" for a, b in sb] or ["| — | 全部通過 |"]
    if sw:
        L2 += ["", "警告：", *[f"- {a}：{b}" for a, b in sw]]
    (work / "bad_span_check.md").write_text("\n".join(L2))
    for a, b in fb + sb:
        print(f"  ✗ {a}：{b}")
    return len(fb) + len(sb)
