#!/usr/bin/env python3
"""頻道④ 影片「對應畫面動作」音效排程（規則 38）。
用法：python3 v9/make_cues.py <佇列資料夾> [--cues cues.json] [--table sfx_table.md]
讀 script.json（每鏡插圖主體 subject.id、版型 layout）＋segments.json（每鏡開始秒、字詞起點）；
依插圖動作表 ACTIONS（秒數＝動作在該鏡開始後第幾秒觸發，取自 illustrations/index.json 的 desc）排 cue：
  · 每鏡 1～3 個動作音效，換幕（第 2 鏡起）加一個很輕的 whoosh；
  · 動作若落在旁白字詞密集處，挪到 ±0.5 秒內最近的字間停頓（間距 ≥ 0.22 秒）；
  · 片尾卡（outro）之後不排；輸出 cues.json（add-sfx.sh 格式，含 endCardSec）與「音效清單」表。
"""
import json, sys, os, subprocess

# 插圖 id → [(動作開始後秒數, kind, 音量 dB 調整, params, 動作說明)]
ACTIONS = {
 'coinjar': [(0.8, 'coin', 0, {'bounces': 2}, '大硬幣落進罐子')],
 'jarpair': [(0.5, 'coin', 0, {'bounces': 1}, '硬幣落進存錢罐')],
 'scale': [(0.45, 'coin', 0, {'bounces': 1}, '硬幣落上秤盤'), (0.9, 'tick', 0, {'n': 5}, '指示數字跳動')],
 'wallet': [(0.5, 'paperslide', 0, {}, '紙鈔滑進錢包'), (1.5, 'stamp', -4, {}, '錢包扣上')],
 'envelopes': [(0.4, 'paperslide', 0, {}, '信封紙鈔探出'), (1.6, 'coin', -2, {'bounces': 1}, '硬幣倒下')],
 'tank': [(0.5, 'tick', -2, {'n': 4, 'gap': 0.12}, '水位補進')],
 'balance': [(0.45, 'coin', 0, {'bounces': 1}, '砝碼落下'), (0.9, 'tick', -2, {'n': 3, 'gap': 0.12}, '橫桿回彈')],
 'printer': [(0.2, 'tick', 0, {'n': 8, 'gap': 0.11}, '收據一格格吐出'), (1.5, 'cashier', 0, {}, '切紙刀落下')],
 'calculator': [(0.2, 'calculator', 0, {'n': 5, 'gap': 0.2}, '按鍵依序按下'), (1.3, 'cashier', -2, {}, '按下「=」')],
 'ticket': [(0.2, 'paperslide', 0, {}, '車票滑進來'), (0.85, 'stamp', 0, {}, '改期章蓋上')],
 'regdesk': [(0.3, 'tick', 0, {'n': 6}, '號碼滾動'), (1.3, 'stamp', 0, {}, '印章蓋下')],
 'calendar6': [(0.4, 'paperslide', 0, {}, '月曆落上牆'), (1.2, 'stamp', 0, {}, '蓋「>2%」章')],
 'punchclock': [(0.4, 'paperslide', -2, {}, '卡片插入'), (0.75, 'stamp', 0, {}, '打卡咔一聲')],
 'gavel_mw': [(0.55, 'thump', 0, {}, '議事槌敲下'), (3.5, 'pageturn', -6, {}, '日曆翻到 10/1'), (4.1, 'stamp', 0, {}, '核定章蓋下'), (6.2, 'coin', -2, {'bounces': 2}, '金幣落上桌面')],
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
 'signpost': [(0.2, 'stamp', -4, {}, '路牌彈起')], 'trail': [(0.3, 'stamp', -4, {}, '步道牌彈起')],
 'stepdown': [(0.4, 'stamp', -4, {}, '房子落地')], 'stepstroller': [(0.5, 'stamp', -4, {}, '推車落地')],
 'housemodel': [(0.3, 'stamp', -3, {}, '模型落下')],
 'bricks': [(0.2, 'stamp', -5, {}, '磚塊疊上'), (1.2, 'stamp', -5, {}, '磚塊疊上')],
 'mailbox': [(0.4, 'stamp', -5, {}, '信箱旗翻起')],
}
DEFAULT = [(0.3, 'paperslide', -2, {}, '主體入場')]
WHOOSH = (-0.02, 'whoosh', 0, {'strength': 0.35}, '換幕輕掃')
MAXPER = 3
MAXPER_BY_SUBJECT = {'gavel_mw': 5}   # 這鏡 8.8 秒較長：4 個動作音效＋換幕 whoosh
MIN_SAME_GAP = 0.8   # 同種音效最短間隔（秒），避免連續叮聲太密
DUR_MIN = {'keyboard': 0.3, 'whoosh': 0.15, 'pageturn': 0.15}   # 秒；依種類合理下限（全域不得 <0.15）
DUR_DEFAULT = {'keyboard': 0.8, 'whoosh': 0.4}


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
            if kind != 'whoosh': t = snap(t, g.get('words', []), t0, nxt - 0.3)
            if t < 0 or t >= end_card - 0.2: continue
            c = {'t': round(t, 2), 'kind': kind, 'gain': gdb, 'pan': 0.5, 'params': prm, 'src': f"{s['id']} {subj or s.get('layout')}：{what}"}
            if kind == 'whoosh': c['dur'] = 0.4
            # 需要 dur 的種類（keyboard 等）：沒給就補預設，且依種類設下限，避免 int(dur*SR)=0 → zero-size array
            if kind in DUR_MIN:
                d = float(prm.get('dur') or c.get('dur') or DUR_DEFAULT.get(kind, DUR_MIN[kind]))
                d = max(d, DUR_MIN[kind]); d = min(d, end_card - 0.05 - t)
                if d < DUR_MIN[kind]: continue    # 剩餘空間不夠就丟掉
                c['dur'] = round(d, 2)
            cues.append(c)
            rows.append((c['t'], what, kind, gdb, s['id']))
    # 同種音效間隔 ≥ MIN_SAME_GAP：太近的後一個往後挪（挪完仍太晚或會撞進下一鏡就丟掉）
    rowd = {id(r): r for r in rows}
    cues_rows = sorted(zip(cues, rows), key=lambda x: x[0]['t'])
    last, keep = {}, []
    for c, r in cues_rows:
        p = last.get(c['kind'])
        if p is not None and c['t'] - p < MIN_SAME_GAP:
            nt = round(p + MIN_SAME_GAP, 2)
            if nt >= end_card - 0.3: continue
            c['t'] = nt; r = (nt,) + tuple(r[1:])
        last[c['kind']] = c['t']; keep.append((c, r))
    cues = [c for c, _ in keep]; rows = [r for _, r in keep]
    cues.sort(key=lambda c: c['t'])
    out = {'total': total, 'endCardSec': round(end_card, 2), 'cues': cues}
    cp = a[a.index('--cues') + 1] if '--cues' in a else os.path.join(d, 'cues.json')
    json.dump(out, open(cp, 'w'), ensure_ascii=False, indent=1)
    tb = ['| 秒數 | 動作 | 音效 | 音量 |', '|---|---|---|---|']
    for t, what, kind, gdb, sid in sorted(rows):
        tb.append(f'| {t:.2f} 秒（{sid}） | {what} | {kind} | 比預設 {gdb:+d} dB，整體低旁白 14～18 dB |')
    # 片尾卡招牌音效（原片自帶，乾淨底片裡保留）：成片裡全部音效都列出
    os_ = float(a[a.index('--outro-start') + 1]) if '--outro-start' in a else end_card
    tb.append(f'| {os_:.2f} 秒（片尾卡） | 片尾卡招牌音 | video_outro_sfx.mp3 | 原片音量（底片自帶），片尾卡後不加運作音效 |')
    tp = a[a.index('--table') + 1] if '--table' in a else os.path.join(d, 'sfx_table.md')
    open(tp, 'w').write('音效清單：秒數｜動作｜音效｜音量\n\n' + '\n'.join(tb) + '\n')
    print(f'{len(cues)} 個音效（另含片尾卡招牌音 1 筆），片尾卡 {end_card:.2f} 秒 → {cp}、{tp}')


if __name__ == '__main__':
    main()
