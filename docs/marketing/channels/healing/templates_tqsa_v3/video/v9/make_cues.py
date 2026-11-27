#!/usr/bin/env python3
"""頻道④ 影片「對應畫面動作」音效排程（規則 38）。
用法：python3 v9/make_cues.py <佇列資料夾> [--cues cues.json] [--table sfx_table.md]
讀 script.json（每鏡插圖主體 subject.id、版型 layout）＋segments.json（每鏡開始秒、字詞起點）；
依插圖動作表 ACTIONS（秒數＝動作在該鏡開始後第幾秒觸發，取自 illustrations/index.json 的 desc）排 cue：
  · 每鏡 1～3 個動作音效，換幕（第 2 鏡起）加一個很輕的 whoosh；
  · 2026-11-27 不壓旁白規則：「講話區段」判法與官方 scripts/sfx/sfx-synth.py 的 cmd_mix 相同（--voice 對齊旁白 wav：
    20 ms 窗 RMS > 最大值 −26 dB 為講話、間隔 ≤0.5 秒補起來、區段前 0.1 秒就算）；
    撞擊類（stamp/coin/thump/cashier）一律固定在畫面接觸時間並標 "class":"impact"（不挪、不丟；官方工具講話中只壓到旁白下約 15.5 dB）；
    鋪陳類（whoosh/paperslide/pageturn/tick 等）落在講話區段內 → 挪到 ±0.5 秒內最近的句間停頓，找不到就不放；
  · 片尾卡（outro）之後不排；輸出 cues.json（add-sfx.sh 格式，含 endCardSec）與「音效清單」表。
"""
import json, sys, os, subprocess

# 插圖 id → [(動作開始後秒數, kind, 音量 dB 調整, params, 動作說明)]
ACTIONS = {
 'coinjar': [(0.8, 'coin', 0, {'bounces': 2}, '大硬幣落進罐子')],
 'jarpair': [(0.5, 'coin', 0, {'bounces': 1}, '硬幣落進存錢罐')],
 'scale': [(0.45, 'coin', 0, {'bounces': 1}, '硬幣落上秤盤'), (0.9, 'tick', 0, {'n': 5}, '指示數字跳動')],
 'wallet': [(0.5, 'paperslide', 0, {}, '紙鈔滑進錢包'), (1.5, 'stamp', -4, {}, '錢包扣上')],
 'envelopes': [(0.4, 'paperslide', 0, {}, '信封紙鈔探出'), (2.2, 'coin', -2, {'bounces': 1}, '硬幣倒下')],
 'tank': [(0.5, 'tick', -2, {'n': 4, 'gap': 0.12}, '水位補進')],
 'balance': [(0.45, 'coin', 0, {'bounces': 1}, '砝碼落下'), (0.9, 'tick', -2, {'n': 3, 'gap': 0.12}, '橫桿回彈')],
 'printer': [(0.2, 'tick', 0, {'n': 8, 'gap': 0.11}, '收據一格格吐出'), (1.5, 'cashier', 0, {}, '切紙刀落下')],
 'calculator': [(0.2, 'calculator', 0, {'n': 5, 'gap': 0.2}, '按鍵依序按下'), (1.3, 'cashier', -2, {}, '按下「=」')],
 'ticket': [(0.2, 'paperslide', 0, {}, '車票滑進來'), (0.85, 'stamp', 0, {}, '改期章蓋上')],
 'regdesk': [(0.3, 'tick', 0, {'n': 6}, '號碼滾動'), (1.3, 'stamp', 0, {}, '印章蓋下')],
 'calendar6': [(0.4, 'paperslide', 0, {}, '月曆落上牆'), (1.2, 'stamp', 0, {}, '蓋「>2%」章')],
 'punchclock': [(0.4, 'paperslide', -2, {}, '卡片插入'), (0.75, 'stamp', 0, {}, '打卡咔一聲')],
 'gavel_mw': [(0.55, 'thump', 0, {}, '議事槌敲下'), (3.5, 'pageturn', -6, {}, '日曆翻到 10/1'), (4.1, 'stamp', 0, {}, '核定章蓋下'), (6.48, 'coin', -2, {'bounces': 2}, '金幣落上桌面'), (7.08, 'coin', -4, {'bounces': 1}, '第 2 枚金幣落桌'), (7.68, 'coin', -4, {'bounces': 1}, '第 3 枚金幣落桌')],
 'gavel': [(0.55, 'stamp', 2, {}, '議事槌敲下')],
 'notice': [(0.3, 'stamp', -3, {}, '圖釘釘上'), (1.0, 'paperslide', -2, {}, '放大鏡滑進')],
 'rateboard': [(0.3, 'tick', 0, {'n': 9, 'gap': 0.09}, '利率數字滾動')],
 'elevator': [(0.2, 'tick', 0, {'n': 6, 'gap': 0.17}, '樓層數字跳動')],
 'odometer': [(0.2, 'tick', 0, {'n': 9, 'gap': 0.08}, '數字滾動')],
 'stairs10': [(0.2, 'tick', 0, {'n': 8, 'gap': 0.16}, '階梯逐級亮起')],
 'birthcards': [(0.15, 'paperslide', 0, {}, '卡片落下'), (0.8, 'tick', -2, {'n': 5, 'gap': 0.17}, '計數牌累加')],
 'otsheet': [(0.35, 'tick', 0, {'n': 6, 'gap': 0.2}, '加班段依序長出')],
 'desks': [(0.3, 'tick', -2, {'n': 5, 'gap': 0.15}, '計數牌累加')],
 'invites': [(0.1, 'paperslide', 0, {}, '喜帖飛進桌面'), (1.0, 'stamp', -2, {}, '封蠟壓下')],
 'boxes': [(0.2, 'stamp', -3, {}, '紙箱疊上'), (0.8, 'stamp', -4, {}, '蓋子彈開')],
 'bookshelf': [(0.3, 'paperslide', 0, {}, '年刊被抽出')],
 'guestbook': [(0.3, 'keyboard', -6, {'rate': 5}, '筆在簿子上書寫')],
 'desklamp': [(0.5, 'stamp', -6, {}, '檯燈喀一聲'), (1.0, 'pageturn', 0, {}, '書頁翻一頁')],
 'stopwatch': [(0.2, 'stamp', -6, {}, '按下碼錶'), (0.3, 'tick', -2, {'n': 8, 'gap': 0.08}, '指針快轉'), (1.1, 'pageturn', -2, {}, '工作日誌翻頁')],
 'megaphone': [(0.8, 'pageturn', -2, {}, '文件翻開一頁')],
 'resign': [(0.2, 'paperslide', 0, {}, '信封滑進桌面'), (0.8, 'keyboard', -6, {'rate': 5}, '筆畫一條線')],
 'govbuilding': [(0.1, 'paperslide', -2, {}, '信封飛向建築')],
 'phonebank': [(0.3, 'tick', 0, {'n': 2, 'gap': 0.2}, '手機震兩下'), (0.7, 'cashier', -3, {}, '入帳通知')],
 'fridge': [(0.3, 'stamp', -4, {}, '磁鐵貼上帳單'), (0.8, 'paperslide', -2, {}, '便條貼上')],
 'officedesk': [(0.2, 'paperslide', -2, {}, '辦公椅滑進'), (0.9, 'paperslide', -3, {}, '便利貼貼上')],
 'cabinet': [(0.2, 'paperslide', 0, {}, '抽屜拉出'), (1.0, 'pageturn', -2, {}, '資料夾抽起')],
 'tape': [(0.2, 'paperslide', 0, {}, '尺帶拉出')],
 'chat': [(0.4, 'tick', 0, {'n': 3, 'gap': 0.3}, '對話泡泡冒出')],
 'weekboard': [(0.2, 'tick', 0, {'n': 5, 'gap': 0.2}, '工作日色塊填滿')],
 'mixing': [(0.3, 'tick', -2, {'n': 6, 'gap': 0.15}, '液面升起')],
 'mixempty': [(0.3, 'tick', -2, {'n': 5, 'gap': 0.15}, '液面升起')],
 'nightoffice': [(0.6, 'stamp', -6, {}, '路燈喀亮起')],
 'cardrack': [(0.3, 'paperslide', -2, {}, '卡片插進卡架'), (1.1, 'paperslide', -2, {}, '卡片插進卡架')],
 'doorframe': [(0.2, 'tick', 0, {'n': 11, 'gap': 0.13}, '鉛筆畫出刻痕')],
 'rentbanner': [(0.2, 'paperslide', 0, {}, '布條垂下')], 'otrent': [(0.2, 'paperslide', -3, {}, '布條垂下')],
 'forsale': [(0.2, 'paperslide', 0, {}, '布條垂下')],
 'bento': [(0.1, 'paperslide', 0, {}, '便當盒滑上桌'), (0.8, 'stamp', -5, {}, '蓋子掀開')],
 'uniforms': [(0.2, 'paperslide', -2, {}, '制服滑進掛架')],
 'shoerack': [(1.0, 'stamp', -3, {}, '布鞋放進鞋櫃')],
 'taxreturn': [(0.71, 'coin', -2, {'bounces': 1}, '5% 硬幣落上報稅單'), (1.73, 'coin', -4, {'bounces': 1}, '退款硬幣落回年終袋')],   # 2026-11-27 第 5 輪：依新路徑逐幀量到落定 25.02／26.04（s5 起 24.31）
 'signpost': [(0.2, 'stamp', -4, {}, '路牌彈起')], 'trail': [(0.3, 'stamp', -4, {}, '步道牌彈起')],
 'stepdown': [(0.4, 'stamp', -4, {}, '房子落地')], 'stepstroller': [(0.5, 'stamp', -4, {}, '推車落地')],
 'housemodel': [(0.3, 'stamp', -3, {}, '模型落下')],
 'bricks': [(0.2, 'stamp', -5, {}, '磚塊疊上'), (1.2, 'stamp', -5, {}, '磚塊疊上')],
 'mailbox': [(0.4, 'stamp', -5, {}, '信箱旗翻起')],
}
DEFAULT = [(0.3, 'paperslide', -2, {}, '主體入場')]
WHOOSH = (-0.02, 'whoosh', 0, {'strength': 0.35}, '換幕輕掃')
MAXPER = 3
MAXPER_BY_SUBJECT = {'gavel_mw': 7}   # 這鏡 8.8 秒較長：6 個動作音效＋換幕 whoosh
MIN_SAME_GAP = 0.8   # 同種音效最短間隔（秒），避免連續叮聲太密
MIN_GAP_BY_KIND = {'coin': 0.5}   # 金幣依畫面三枚先後落桌（間隔約 0.6 秒），不可被推開
DUR_MIN = {'keyboard': 0.3, 'whoosh': 0.15, 'pageturn': 0.15}   # 秒；依種類合理下限（全域不得 <0.15）
DUR_DEFAULT = {'keyboard': 0.8, 'whoosh': 0.4}


# 【接觸時間對照｜第 9 輪審片逐幀量測】撞擊類 cue 的秒數＝插圖「接觸／落下那一刻」（相對本鏡開頭），不是物件出現時間：
#   gavel_mw 金幣：插圖 6.2／6.8／7.4 秒開始落，落地 0.28 秒 → 接觸 6.48／7.08／7.68；核定章 4.1、議事槌 0.55 本來就是接觸點
#   其餘（打卡、入帳通知、硬幣倒下）因各片鏡頭起點與旁白停頓不同，用下面 FIX_ABS 逐片寫審片量到的接觸絕對秒數
# 逐片覆寫：(佇列資料夾, 鏡頭 id, 音效種類) → 畫面接觸的絕對秒數（第 9 輪審片逐幀量到；覆寫在 snap 之後）
FIX_ABS = {
    ('20261128v_avgwage', 's1', 'cashier'): 0.58,   # 入帳通知（原 1.01）
    ('20261129v_quit', 's3', 'stamp'): 12.23,       # 打卡（原 12.49）
    ('20261205v_bonus', 's6', 'stamp'): 29.43,      # 路牌到定位（第 5 輪量：原 29.30 早 0.125）；只改本片，通用 signpost 0.2 不動
    ('20261205v_bonus', 's8', 'stamp'): 42.46,      # 步道牌到定位（第 5 輪量：原 42.28 早 0.18）；通用 trail 0.3 不動
}
# 撞擊類音效固定在畫面動作的時間，不經 snap()；撞上旁白致最差窗 <14 dB 時改降該條音量 4～6 dB，不准挪時間
IMPACT = {'stamp', 'coin', 'thump', 'cashier'}


# ── 講話區段（與官方 sfx-synth.py cmd_mix 同判法）──
HOP = 0.02; SPEECH_DB = -26.0; GAP_FILL = 0.5; LEAD = 0.10; TAIL = 0.12   # TAIL：旁白結束後多留的放開餘裕
EST_DUR = {'tick': None, 'paperslide': 0.3, 'pageturn': 0.35, 'whoosh': 0.4, 'keyboard': 0.8, 'calculator': None}


def speech_regions(voice_path):
    """回傳 [(起秒, 迄秒)]（含前導 LEAD、已補句中停頓）；判法照官方 cmd_mix。"""
    import importlib.util
    import numpy as np
    here = os.path.dirname(os.path.abspath(__file__))
    syn = None
    for up in range(3, 9):
        c = os.path.join(here, *(['..'] * up), 'scripts', 'sfx', 'sfx-synth.py')
        if os.path.exists(c): syn = c; break
    if not syn: raise SystemExit('找不到 scripts/sfx/sfx-synth.py（判斷講話區段要用官方函式）')
    sp = importlib.util.spec_from_file_location('sfx_synth_official', syn); m = importlib.util.module_from_spec(sp); sys.modules['sfx_synth_official'] = m; sys.path.insert(0, os.path.dirname(syn)); sp.loader.exec_module(m)
    v = m.read_wav(voice_path)
    hop = int(HOP * m.SR); ve = m.frame_rms(v, hop)
    thr = max(np.max(ve) * m.db(SPEECH_DB), 1e-4)
    spk = ve > thr
    filled = spk.copy(); idx = np.where(spk)[0]
    for i0, i1 in zip(idx[:-1], idx[1:]):
        if 1 < i1 - i0 <= int(GAP_FILL / HOP): filled[i0:i1] = True
    regs, st = [], None
    for i in range(len(filled) + 1):
        on = i < len(filled) and filled[i]
        if on and st is None: st = i
        if not on and st is not None: regs.append((max(0.0, st * HOP - LEAD), i * HOP + TAIL)); st = None
    return regs


def in_speech(t, regs, dur=0.0):
    """cue 的 [t, t+dur] 是否碰到講話區段。"""
    return any(t < b and t + dur > a for a, b in regs)


def snap_pause(t, regs, dur, lo, hi):
    """挪到 ±0.5 秒內最近、且整段 cue 不碰講話區段的句間停頓；找不到回 None。"""
    best = None
    k = -0.5
    while k <= 0.5001:
        c = round(t + k, 2)
        if lo <= c <= hi and not in_speech(c, regs, dur) and (best is None or abs(c - t) < abs(best - t) - 1e-9): best = c
        k += 0.01
    return best


def snap(t, words, lo, hi):
    """動作若落在字詞密集處，挪到 ±0.5 秒內最近的字間停頓。"""
    gaps = [((a + b) / 2, b - a) for a, b in zip(words, words[1:]) if b - a >= 0.22]
    if not words or not (words[0] - 0.1 <= t <= words[-1] + 0.1): return t
    inside = any(a <= t <= b and b - a < 0.22 for a, b in zip(words, words[1:]))
    if not inside: return t
    cand = [g for g, _ in gaps if abs(g - t) <= 0.5 and lo <= g <= hi]
    return min(cand, key=lambda g: abs(g - t)) if cand else t


def main():
    a = sys.argv[1:]
    d = a[0]
    sc = json.load(open(os.path.join(d, 'script.json')))
    sg = {s['id']: s for s in json.load(open(os.path.join(d, 'segments.json')))['segments']}
    vid = os.path.join(d, 'video.mp4')
    total = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', vid]).decode()) if os.path.exists(vid) else None
    regs = speech_regions(a[a.index('--voice') + 1]) if '--voice' in a else None
    if regs is None: print('警告：沒給 --voice，退回只用字詞時間判斷（不執行不壓旁白規則）')
    dropped = []
    outro = sc.get('outro') or {}
    scenes = sc['scenes']
    last_end = max(s['end'] for s in sg.values())
    end_card = (total - float(outro.get('dur') or 6.2)) if total else last_end + 0.4
    cues, rows = [], []
    for i, s in enumerate(scenes):
        g = sg.get(s['id'])
        if not g: continue
        t0 = g['start']; nxt = sg.get(scenes[i + 1]['id'])['start'] if i + 1 < len(scenes) and scenes[i + 1]['id'] in sg else end_card
        subj = (s.get('subject') or {}).get('id')
        acts = list(ACTIONS.get(subj) or ([] if s.get('layout') in ('ask',) and not subj else DEFAULT))
        if s.get('layout') == 'odometer' and not acts: acts = ACTIONS['odometer']
        acts = acts[:MAXPER_BY_SUBJECT.get(subj, MAXPER) - (1 if i else 0)]
        if i: acts = [WHOOSH] + acts
        for off, kind, gdb, prm, what in acts:
            t = max(0.0, t0 + off)
            fx = FIX_ABS.get((os.path.basename(os.path.normpath(d)), s['id'], kind))
            if regs is None:
                if kind not in IMPACT and kind != 'whoosh': t = snap(t, g.get('words', []), t0, nxt - 0.3)
                if fx is not None: t = fx
            else:
                if fx is not None: t = fx
                if kind in IMPACT:
                    pass   # 撞擊音效固定在畫面接觸時間（不挪、不丟）；講話中由官方工具標 impact 類只壓到旁白下約 15.5 dB
                else:
                    ed = EST_DUR.get(kind) or (prm.get('n', 4) * prm.get('gap', 0.1) + 0.1 if kind in ('tick', 'calculator') else 0.3)
                    if in_speech(t, regs, ed):
                        nt = snap_pause(t, regs, ed, max(0.0, t0 - 0.05), nxt - 0.1)
                        if nt is None:
                            dropped.append((round(t, 2), what, kind, s['id'], '鋪陳音找不到 ±0.5 秒內的停頓')); continue
                        t = nt
            if t < 0 or t >= end_card - 0.2: continue
            c = {'t': round(t, 2), 'kind': kind, 'gain': gdb, 'pan': 0.5, 'params': prm, 'src': f"{s['id']} {subj or s.get('layout')}：{what}"}
            if kind in IMPACT: c['class'] = 'impact'
            if kind == 'whoosh': c['dur'] = 0.4
            # 需要 dur 的種類（keyboard 等）：沒給就補預設，且依種類設下限，避免 int(dur*SR)=0 → zero-size array
            if kind in DUR_MIN:
                dd = float(prm.get('dur') or c.get('dur') or DUR_DEFAULT.get(kind, DUR_MIN[kind]))
                dd = max(dd, DUR_MIN[kind]); dd = min(dd, end_card - 0.05 - t)
                if dd < DUR_MIN[kind]: continue    # 剩餘空間不夠就丟掉
                c['dur'] = round(dd, 2)
            cues.append(c)
            rows.append((c['t'], what, kind, gdb, s['id']))
    # 同種音效間隔 ≥ MIN_SAME_GAP：太近的後一個往後挪（挪完仍太晚或會撞進下一鏡就丟掉）
    rowd = {id(r): r for r in rows}
    cues_rows = sorted(zip(cues, rows), key=lambda x: x[0]['t'])
    last, keep = {}, []
    for c, r in cues_rows:
        p = last.get(c['kind'])
        gap_min = MIN_GAP_BY_KIND.get(c['kind'], MIN_SAME_GAP)
        if p is not None and c['t'] - p < gap_min:
            nt = round(p + gap_min, 2)
            if nt >= end_card - 0.3: continue
            c['t'] = nt; r = (nt,) + tuple(r[1:])
        last[c['kind']] = c['t']; keep.append((c, r))
    if regs is not None:   # 同種間隔挪動後再檢查一次：撞擊類碰到講話就丟；鋪陳類碰到講話就丟
        k2 = []
        for c, r in keep:
            if c['kind'] in IMPACT: k2.append((c, r)); continue
            ed = 0.0 if c['kind'] in IMPACT else (c.get('dur') or EST_DUR.get(c['kind']) or 0.3)
            if in_speech(c['t'], regs, ed):
                dropped.append((c['t'], r[1], c['kind'], r[4], '同種間隔挪動後落入講話')); continue
            k2.append((c, r))
        keep = k2
    cues = [c for c, _ in keep]; rows = [r for _, r in keep]
    cues.sort(key=lambda c: c['t'])
    out = {'total': total, 'endCardSec': round(end_card, 2), 'cues': cues}
    cp = a[a.index('--cues') + 1] if '--cues' in a else os.path.join(d, 'cues.json')
    json.dump(out, open(cp, 'w'), ensure_ascii=False, indent=1)
    tb = ['| 秒數 | 動作 | 音效 | 音量 |', '|---|---|---|---|']
    for t, what, kind, gdb, sid in sorted(rows):
        tb.append(f'| {t:.2f} 秒（{sid}） | {what} | {kind} | 比預設 {gdb:+d} dB，整體低旁白 14～18 dB |')
    for t, what, kind, sid, why in dropped:
        tb.append(f'| {t:.2f} 秒（{sid}） | {what}（講話中，依不壓旁白規則不放音效） | — | — |')
    # 片尾卡招牌音效（原片自帶，乾淨底片裡保留）：成片裡全部音效都列出
    os_ = float(a[a.index('--outro-start') + 1]) if '--outro-start' in a else end_card
    tb.append(f'| {os_:.2f} 秒（片尾卡） | 片尾卡招牌音 | video_outro_sfx.mp3 | 原片音量（底片自帶），片尾卡後不加運作音效 |')
    tp = a[a.index('--table') + 1] if '--table' in a else os.path.join(d, 'sfx_table.md')
    open(tp, 'w').write('音效清單：秒數｜動作｜音效｜音量\n\n' + '\n'.join(tb) + '\n')
    print('保留：'); [print(f"  {c['t']:.2f} {c['kind']} {c['src']}") for c in cues]
    print('拿掉：'); [print(f'  {t:.2f} {k} {sid} {w}（{why}）') for t, w, k, sid, why in sorted(dropped)]
    ni = lambda L: sum(1 for x in L if (x['kind'] if isinstance(x, dict) else x[2]) in IMPACT)
    print(f'撞擊音效：保留 {ni(cues)}、拿掉 {sum(1 for x in dropped if x[2] in IMPACT)}')
    print(f'{len(cues)} 個音效（另含片尾卡招牌音 1 筆），片尾卡 {end_card:.2f} 秒 → {cp}、{tp}')


if __name__ == '__main__':
    main()
