#!/usr/bin/env python3
"""④ 旁白保護檢查（Andy 11-27：「音效不要影響旁白聲」）。
用法：python3 healing_guard.py <原片.mp4> <cues.json> [--end 片尾卡秒] [--min 14] [--fix <修正後 cues 輸出.json>]
重現 add-sfx.sh 的混音（sfx-synth.py mix），旁白講話的每個 20 毫秒框，音效 RMS 都要比旁白 RMS 低 ≥ --min dB；
任一框不合格就印出時間並以結束碼 1 離開（workflow 據此不輸出成品）。最後一行印「最差一段差 X dB」。
--fix：不合格的 cue 自動降 gain（每次 −3 dB，最多 6 輪）後寫新 cues；仍不合格就結束碼 1。
"""
import sys, os, json, math, subprocess, tempfile, importlib.util
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('sfxsynth', os.path.join(D, 'sfx-synth.py'))
S = importlib.util.module_from_spec(sp); sys.modules['sfxsynth'] = S; sp.loader.exec_module(S)


def measure(inp, cues, end, total, tmp):
    voice = os.path.join(tmp, 'v.wav'); sfxw = os.path.join(tmp, 's.wav'); mixw = os.path.join(tmp, 'm.wav')
    subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-i', inp, '-vn', '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s16le', voice])
    buf, _ = S.render_cues(cues, total, end); S.write_wav(sfxw, buf)
    S.cmd_mix([voice, sfxw, mixw, '--guard', '15'] + (['--end', str(end)] if end else []))
    v = S.read_wav(voice); m = S.read_wav(mixw); n = min(v.shape[1], m.shape[1])
    s = (m[:, :n] - v[:, :n]); v = v[:, :n]
    hop = int(0.02 * S.SR); ve = S.frame_rms(v, hop); se = S.frame_rms(s, hop)
    lim = int((end if end else n / S.SR) * S.SR) // hop
    thr = max(ve[:lim].max() * 10 ** (-26 / 20), 1e-4)
    worst = 99.0; bad = []
    for i in range(min(lim, len(ve))):
        if ve[i] > thr and se[i] > 1e-5:                   # 旁白講話中、且有音效能量
            d = 20 * math.log10(ve[i] / se[i])
            worst = min(worst, d)
            if d < MIN: bad.append((i * 0.02, d))
    return worst, bad


MIN = 14.0
def main():
    global MIN
    a = sys.argv[1:]
    inp, cj = a[0], a[1]
    end = float(a[a.index('--end') + 1]) if '--end' in a else None
    MIN = float(a[a.index('--min') + 1]) if '--min' in a else 14.0
    c = json.load(open(cj)); cues = c['cues'] if isinstance(c, dict) else c
    if end is None and isinstance(c, dict): end = c.get('endCardSec')
    total = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', inp]).decode())
    fix = a[a.index('--fix') + 1] if '--fix' in a else None
    with tempfile.TemporaryDirectory() as tmp:
        for rnd in range(7 if fix else 1):
            worst, bad = measure(inp, cues, end, total, tmp)
            if not bad: break
            if not fix: break
            for t, _ in bad:                               # 降低涵蓋該框的 cue
                for q in cues:
                    if q['t'] - 0.02 <= t <= q['t'] + (q.get('dur') or 1.0) + 0.6: q['gain'] = q.get('gain', 0) - 3
        if fix: json.dump({'total': total, 'endCardSec': end, 'cues': cues}, open(fix, 'w'), ensure_ascii=False, indent=1)
    for t, d in bad[:10]: print(f'不合格：{t:.2f} 秒 音效只低旁白 {d:.1f} dB（要求 ≥ {MIN:.0f}）')
    print(f'旁白保護：最差一段差 {worst:.1f} dB（要求 ≥ {MIN:.0f} dB）→ ' + ('不合格' if bad else '合格'))
    sys.exit(1 if bad else 0)

main()
