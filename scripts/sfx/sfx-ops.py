#!/usr/bin/env python3
"""【科技片轉接層】運作音效（Andy 2026/11/27：「以後產出所有內容，Claude 這邊都需要在影片上配對應運作上的音效」）。

分層：通用合成器在 scripts/three/sfx-synth.py（只吃 cue 表 JSON，不依賴專案檔，別的頻道可單獨用）；
本檔只負責「從 storyboard／script／model 自動產 cue 表」再呼叫合成器。依賴：python3＋numpy（混音由 add-sfx.sh 用 ffmpeg）。

用法：
  python3 scripts/three/sfx-ops.py <slug> [--out out/<slug>.sfx.wav] [--cues out/<slug>/sfx-cues.json]
      讀 videos/<slug>/storyboard.json、script.json、model.json，依動作類型排出音效時間軸，全部用 numpy 合成
      （固定 seed、不用外部音檔、不用版權素材），輸出 48 kHz 立體聲 wav（第 0 個樣本＝影片第 0 幀）與 sfx-cues.json。
  python3 scripts/three/sfx-ops.py <slug> --cues-table-only  只輸出 cue 表（out/<slug>/sfx-table.json），不合成
  混音用 sfx-synth.py mix（add-sfx.sh 會呼叫）。

排音規則（來源＝script.json 各幕 props.run／motion／shift／explode／shot，與 model.json 的 actions）：
  cue 寫法跟引擎一樣：「cue±幀」「sN:cue±幀」，cue 可以是該幕的 cue id 或 start／voice／end／exit；負的時間夾到 0。
  同一類聲音、時間重疊的動作合併成一段（例如 atom0~atom20 只出一段濺鍍聲，不疊 21 層）。
  片尾卡（最後一幕 silent 或有 endCard）整段不加運作音效；標籤出現、字卡、2D 疊層一律不加（避免太吵）。

| 類型 key | 聲音                         | 觸發的動作                                                              |
|----------|------------------------------|-------------------------------------------------------------------------|
| motor    | 低頻嗡聲，音高與音量隨轉速   | rotate 動作（轉軸、輥輪、轉盤）；rps 越高越尖；rampSpin 起轉／停轉有升降頻 |
| servo    | 短促 whir（伺服馬達）        | motion：pick-place／arm-transfer／arm-reach／scan／advance               |
| hiss     | 濾波白噪（氣流、吹淨、噴氣） | flow 動作顏色 argonC／名稱含 gas、spray、air、blow；開頭結尾各一個閥門 click |
| liquid   | 粉紅噪＋水滴（噴灑、流動）   | flow 動作顏色 waterD、cuBright（電解液）；名稱含 water、cool                |
| plasma   | 電流嗡（100 Hz 與泛音）＋細微劈啪 | flow 動作在 plasma 層（ion／elec／field）、pulse 顏色 plasmaC           |
| sputter  | 細碎撞擊劈啪（原子被打出）   | flow 動作在 hitL 層（atom*）、pulse 顏色 hitC                            |
| heat     | 很低的爐火轟聲＋偶爾金屬熱脹 tick | pulse 顏色 hotC／moltenC（加熱、熔融）                              |
| chips    | 稀疏的細小碎屑點擊           | flow 顏色 chipFlake（碎屑）                                              |
| clunk    | 金屬 clunk＋滑軌聲           | props.explode／assemble／reexplode（每層一下）、shift 有位移（dx／dy／dz）、press-bond、stack-up 每層 |
| valve    | 氣動 click（短噪音＋極短 psst） | hiss 類開始與結束、press-bond 壓下與放開、pick-place 吸附與破真空      |
| whoosh   | 很輕的氣流掃過               | props.shot 鏡頭大移動（位移量超過 SHOT_MIN 才加，距離越大越大聲）         |
| （不加） | 標籤出現、字卡、overlay、reveal、片尾卡 | —                                                              |

沒對到規則的 actions（wave／vibrate／trace／sum／meter 等）：vibrate＝buzz（motor 的高頻版）、wave＝低頻 thump 環，其餘不發聲。
"""

import sys, os, re, json, importlib.util
from collections import Counter

_sp = importlib.util.spec_from_file_location('sfx_synth', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sfx-synth.py'))
syn = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(syn)

SHOT_MIN = 6.0            # 鏡頭位移量（x+y+0.5d）超過才加 whoosh
SHOT_MIN_DUR = 5          # 鏡頭過渡短於這個幀數＝硬切，不加

# ---------------------------------------------------------------- 時間軸解析
TOK = re.compile(r'^(?:(s\d+):)?([A-Za-z_][A-Za-z0-9_]*)([+-]\d+(?:\.\d+)?)?$')

class Timeline:
    def __init__(self, sb):
        self.fps = sb.get('fps', 30)
        self.scenes = {s['id']: s for s in sb['scenes']}
        self.total = sb['totalFrames']

    def frame(self, tok, cur):
        if tok is None: return None
        if isinstance(tok, (int, float)): return float(tok)
        m = TOK.match(str(tok).strip())
        if not m: return None
        sid, name, off = m.group(1), m.group(2), float(m.group(3) or 0)
        sc = self.scenes.get(sid or cur)
        if not sc: return None
        base = sc['startFrame']
        if name == 'start': f = base
        elif name == 'voice': f = (sc.get('voice') or {}).get('startFrame', base)
        elif name in ('end', 'exit'): f = base + sc['durationFrames']
        else:
            c = next((c for c in sc['cues'] if c['id'] == name), None)
            if not c: return None
            f = c['frame']
        return f + off

    def sec(self, tok, cur):
        f = self.frame(tok, cur)
        if f is None: return None
        return max(0.0, f / self.fps)


# ---------------------------------------------------------------- 分類
def classify_action(aid, a):
    """回傳 (類型 key, family key)；family 相同的重疊區段會合併。"""
    typ = a.get('type'); col = str(a.get('color', '')); lay = str(a.get('layer', '')); name = aid.lower()
    if typ == 'rotate':
        fam = re.sub(r'\d+$', '', aid)
        fam = re.sub(r'(Spin|U|L|BU|BL)$', '', fam) if False else fam
        return 'motor', ('roll' if aid.startswith('roll') else 'spin')
    if typ == 'flow':
        if col == 'waterD' or 'water' in name or col == 'cuBright' or lay in ('rfElyt',): return 'liquid', 'liquid'
        if col == 'chipFlake': return 'chips', 'chips'
        if lay == 'hitL' or col == 'tgtFaceC': return 'sputter', 'sputter'
        if lay == 'plasma' or col in ('ionC', 'eleC', 'fieldC'): return 'plasma', 'plasma'
        if col == 'argonC' or re.search(r'gas|spray|air|blow|cool', name): return 'hiss', 'hiss:' + lay
        return 'hiss', 'hiss:' + lay
    if typ == 'pulse':
        if col in ('plasmaC',): return 'plasma', 'plasma'
        if col in ('hitC',): return 'sputter', 'sputter'
        if col in ('hotC', 'moltenC'): return 'heat', 'heat'
        return None, None
    if typ == 'vibrate': return 'buzz', 'buzz'
    if typ == 'wave': return 'thump', 'thump'
    return None, None


def collect(slug, root):
    vd = os.path.join(root, 'videos', slug)
    sb = json.load(open(os.path.join(vd, 'storyboard.json')))
    sc = json.load(open(os.path.join(vd, 'script.json')))
    md = json.load(open(os.path.join(vd, 'model.json')))
    tl = Timeline(sb)
    actions = md.get('actions', {})
    ev = []   # {kind, t0, t1, rps, fam, src, strength}
    end_t = None
    last = sc['scenes'][-1]
    if last.get('silent') or (last.get('props') or {}).get('endCard'):
        end_t = tl.scenes[last['id']]['startFrame'] / tl.fps
    shots = []

    def add_run(r, sid, scene_end_t):
        aid = r.get('id'); a = actions.get(aid)
        if not a: return
        kind, fam = classify_action(aid, a)
        if not kind: return
        t0 = tl.sec(r.get('at'), sid)
        t1 = tl.sec(r.get('until'), sid) if r.get('until') else None
        if t0 is None: return
        if t1 is None: t1 = t0 + 1.0
        ev.append(dict(kind=kind, fam=fam, t0=t0, t1=t1, rps=a.get('rps', 0.5) or 0.5, ramp=(r.get('ramp') or 8) / tl.fps,
                       rampSpin=a.get('rampSpin', False), src=f'{sid}:{aid}'))

    for s in sc['scenes']:
        sid = s['id']; p = s.get('props') or {}
        for r in p.get('run') or []: add_run(r, sid, None)
        for m in p.get('motion') or []:
            pr = m.get('preset'); t0 = tl.sec(m.get('at'), sid)
            if pr == 'run':
                for i in m.get('ids', []):
                    add_run(dict(id=i, at=m.get('at'), until=m.get('until'), ramp=m.get('ramp')), sid, None)
            elif t0 is None: continue
            elif pr in ('pick-place', 'arm-transfer', 'arm-reach'):
                ln = {'pick-place': 126, 'arm-transfer': 108, 'arm-reach': 70}[pr] / tl.fps
                ev.append(dict(kind='servo', t0=t0, t1=t0 + ln, src=f'{sid}:{pr}', n=3 if pr != 'arm-reach' else 2))
                if pr == 'pick-place':
                    ev.append(dict(kind='valve', t0=t0 + 0.35 * 1.0 + 0.2, t1=0, src=f'{sid}:{pr}:吸附'))
                    ev.append(dict(kind='valve', t0=t0 + 3.2, t1=0, src=f'{sid}:{pr}:破真空'))
                    ev.append(dict(kind='clunk', t0=t0 + 3.3, t1=0, src=f'{sid}:{pr}:放下', strength=0.5))
                if pr == 'arm-transfer':
                    ev.append(dict(kind='valve', t0=t0 + 0.9, t1=0, src=f'{sid}:{pr}:夾緊'))
                    ev.append(dict(kind='clunk', t0=t0 + 2.9, t1=0, src=f'{sid}:{pr}:放下', strength=0.5))
            elif pr == 'scan':
                ev.append(dict(kind='servo', t0=t0, t1=t0 + m.get('len', 90) / tl.fps, src=f'{sid}:scan', n=4))
            elif pr == 'advance':
                ev.append(dict(kind='slide', t0=t0, t1=t0 + m.get('dur', 30) / tl.fps, src=f'{sid}:advance'))
            elif pr == 'press-bond':
                ev.append(dict(kind='valve', t0=t0 + 0.2, t1=0, src=f'{sid}:press-bond:下壓'))
                ev.append(dict(kind='clunk', t0=t0 + 1.1, t1=0, src=f'{sid}:press-bond:接觸', strength=0.8))
                ev.append(dict(kind='valve', t0=t0 + 3.3, t1=0, src=f'{sid}:press-bond:放開'))
            elif pr == 'stack-up':
                for i, _ in enumerate(m.get('layers', [])):
                    ev.append(dict(kind='clunk', t0=t0 + (i * m.get('gap', 16) + 12) / tl.fps, t1=0, src=f'{sid}:stack-up:層{i+1}', strength=0.6))
            elif pr == 'cut':
                ev.append(dict(kind='motor', fam='blade', t0=t0, t1=t0 + (m.get('len', 60) + 40) / tl.fps, rps=6.0, ramp=0.5, rampSpin=True, src=f'{sid}:cut'))
        for k in ('explode', 'assemble', 'reexplode'):
            if p.get(k):
                t0 = tl.sec(p[k].get('at'), sid)
                if t0 is None: continue
                for i in range(4):
                    ev.append(dict(kind='slide', t0=t0 + i * 0.22, t1=t0 + i * 0.22 + 0.25, src=f'{sid}:{k}'))
                    ev.append(dict(kind='clunk', t0=t0 + i * 0.22 + (0.2 if k != 'explode' else 0.0), t1=0, src=f'{sid}:{k}:層{i+1}', strength=0.55 if k == 'explode' else 0.7))
        for sh in p.get('shift') or []:
            if not any(sh.get(k) for k in ('dx', 'dy', 'dz')): continue
            f0 = tl.frame(sh.get('at'), sid)
            if f0 is None or f0 < 0: continue      # 影片開始前就已就位的擺放，不發聲
            t0 = f0 / tl.fps
            d = (sh.get('dur') or 20) / tl.fps
            ev.append(dict(kind='slide', t0=t0, t1=t0 + d, src=f'{sid}:shift:{sh.get("layer")}'))
            ev.append(dict(kind='clunk', t0=t0 + d, t1=0, src=f'{sid}:shift:{sh.get("layer")}', strength=0.45))
        for sh in p.get('shot') or []:
            t0 = tl.sec(sh.get('at'), sid)
            if t0 is None: continue
            shots.append(dict(t0=t0, dur=sh.get('dur', 20), x=sh.get('x', 0), y=sh.get('y', 0), d=sh.get('d', 30), sid=sid))
    shots.sort(key=lambda z: z['t0'])
    for a, b in zip(shots, shots[1:]):
        mv = abs(b['x'] - a['x']) + abs(b['y'] - a['y']) + 0.5 * abs(b['d'] - a['d'])
        if mv >= SHOT_MIN and b['dur'] >= SHOT_MIN_DUR:
            ev.append(dict(kind='whoosh', t0=b['t0'], t1=b['t0'] + b['dur'] / tl.fps, strength=min(1.0, 0.35 + mv / 40.0), src=f'{b["sid"]}:shot'))
    return ev, end_t, tl


def merge(ev):
    """同 kind+fam 的持續音，間隔 < 0.35 s 合併；合併後在 hiss 的頭尾加閥門 click。"""
    cont = [e for e in ev if e['kind'] in ('motor', 'hiss', 'liquid', 'plasma', 'sputter', 'heat', 'chips', 'buzz', 'thump')]
    rest = [e for e in ev if e not in cont]
    out = []
    groups = {}
    for e in cont: groups.setdefault((e['kind'], e.get('fam')), []).append(e)
    for key, lst in groups.items():
        lst.sort(key=lambda z: z['t0'])
        cur = None
        for e in lst:
            if cur and e['t0'] <= cur['t1'] + 0.35:
                cur['t1'] = max(cur['t1'], e['t1'])
                if e['src'] not in cur['src']: cur['src'] += '+' + e['src'].split(':', 1)[-1]
                cur['rps'] = max(cur.get('rps', 0), e.get('rps', 0))
            else:
                if cur: out.append(cur)
                cur = dict(e)
        if cur: out.append(cur)
    for e in out:
        if e['kind'] == 'hiss':
            rest.append(dict(kind='valve', t0=e['t0'], t1=0, src=e['src'] + ':開閥'))
            rest.append(dict(kind='valve', t0=e['t1'], t1=0, src=e['src'] + ':關閥'))
    # 同一類瞬間聲（clunk／slide／valve）0.25 s 內只留一個（多層同時動＝一聲）
    rest.sort(key=lambda z: (z['kind'], z['t0']))
    keep = []
    for e in rest:
        if keep and e['kind'] in ('clunk', 'slide', 'valve') and keep[-1]['kind'] == e['kind'] and e['t0'] - keep[-1]['t0'] < 0.25:
            keep[-1]['src'] += '+' + e['src'].split(':', 1)[-1]
            keep[-1]['strength'] = min(1.0, keep[-1].get('strength', 1.0) + 0.1)
            continue
        keep.append(e)
    return out + keep


def pan_of(name):
    h = sum(ord(c) for c in name) % 100 / 100.0
    return 0.3 + 0.4 * h     # 0.3~0.7，偏中間，不要忽左忽右


def to_cues(ev, end_t):
    """合併後的事件 → cue 表（給 sfx-synth.py）。"""
    cues = []
    for e in sorted(ev, key=lambda z: z['t0']):
        k = e['kind']; dur = max((e.get('t1') or e['t0']) - e['t0'], 0.0)
        p = {}
        if k == 'motor': p = dict(rps=e.get('rps', 0.5), ramp=e.get('ramp', 0.4), rampSpin=e.get('rampSpin', True))
        elif k == 'servo': p = dict(n=e.get('n', 2))
        elif k in ('clunk', 'whoosh'): p = dict(strength=e.get('strength', 1.0 if k == 'clunk' else 0.6))
        if k in ('motor', 'hiss', 'liquid', 'plasma', 'sputter', 'chips', 'buzz') and dur < 0.3: continue
        if k == 'heat' and dur < 0.3: continue
        cues.append(dict(t=round(e['t0'], 3), dur=round(dur, 3), kind=k, pan=round(pan_of(e['src']), 2), params=p, src=e['src']))
    return cues


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(1)
    slug = a[0]
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(root, 'out', f'{slug}.sfx.wav')
    cues_path = a[a.index('--cues') + 1] if '--cues' in a else os.path.join(root, 'out', slug, 'sfx-cues.json')
    ev, end_t, tl = collect(slug, root)
    ev = merge(ev)
    total = tl.total / tl.fps + 0.5
    table = to_cues(ev, end_t)
    tpath = os.path.join(os.path.dirname(cues_path), 'sfx-table.json')
    os.makedirs(os.path.dirname(cues_path) or '.', exist_ok=True)
    json.dump(dict(total=total, endCardSec=end_t, cues=table), open(tpath, 'w'), ensure_ascii=False, indent=1)
    if '--cues-table-only' in a: print(f'{len(table)} 個 cue → {tpath}'); return
    buf, rec = syn.render_cues(table, total, end_t)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    syn.write_wav(out, buf)
    syn.write_wav(out + '.impact.wav', syn.LAST_IMPACT)   # 撞擊類分軌（2026-11-27），add-sfx 的 mix 自動讀
    summary = dict(Counter(c['type'] for c in rec))
    json.dump(dict(slug=slug, endCardSec=end_t, count=len(rec), byType=summary, cues=rec), open(cues_path, 'w'), ensure_ascii=False, indent=1)
    print(f'{slug}: {len(rec)} 個音效 {summary}；片尾卡 {end_t}s 起靜音 → {out}')


if __name__ == '__main__':
    main()
