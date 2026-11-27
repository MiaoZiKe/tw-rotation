#!/usr/bin/env python3
"""頻道④ 乾淨底片重建（規則 38 修正，2026-11-27）。
渲染時 sfx_v3 已把物件音效烤進 video_nosfx.mp4 的音軌；若直接在上面疊 healing 音效就是兩層。
本程式只用：資料夾的 narration.wav（旁白原音）＋ video_outro_sfx.mp3（片尾卡音效），
依 video_nosfx 音軌用互相關找出兩者實際起點，重組音軌，影像串流 -c:v copy 封回 → 乾淨底片。
用法：rebuild_clean.py <佇列資料夾> <video_nosfx.mp4> <輸出乾淨.mp4> <對齊後旁白.wav 輸出> [--secs N]
（--secs 只做前 N 秒，供試混）。"""
import sys, os, json, subprocess, tempfile
import numpy as np
from numpy.fft import rfft, irfft
SR = 48000

def dec(path, ss=None, t=None):
    cmd = ['ffmpeg', '-v', 'error', '-i', path] + (['-t', str(t)] if t else []) + ['-vn', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.check_output(cmd), dtype=np.float32).astype(np.float64)

def xcorr_offset(ref, seg, lo=0, hi=None):
    """seg 在 ref 中的起點（樣本）。用 sign-envelope 較穩的相位相關：直接 FFT 互相關＋能量正規化。"""
    n = 1 << int(np.ceil(np.log2(len(ref) + len(seg))))
    c = irfft(rfft(ref, n) * np.conj(rfft(seg, n)), n)[:len(ref) - len(seg) + 1]
    # 滑動能量正規化
    e = np.concatenate([[0], np.cumsum(ref ** 2)]); w = e[len(seg):len(seg) + len(c)] - e[:len(c)]
    sc = c / np.sqrt(np.maximum(w, 1e-9) * np.sum(seg ** 2))
    hi = hi if hi is not None else len(sc)
    k = lo + int(np.argmax(sc[lo:hi])); return k, float(sc[k])

def main():
    a = sys.argv[1:]; d, nos, out, nw = a[:4]
    secs = float(a[a.index('--secs') + 1]) if '--secs' in a else None
    sc = json.load(open(os.path.join(d, 'script.json'))); outro_dur = float((sc.get('outro') or {}).get('dur') or 6.2)
    tot = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', nos]).decode())
    ref = dec(nos); nar = dec(os.path.join(d, 'narration.wav')); om = dec(os.path.join(d, 'video_outro_sfx.mp3'))
    # 旁白起點：用旁白前 12 秒（含最多字）在原片音軌前 20 秒內找
    L = min(len(nar), 12 * SR)
    k, sc1 = xcorr_offset(ref[:20 * SR + L], nar[:L]); 
    # 增益：對 narration 全長以最小平方估計（物件音效是額外加成，估值略偏高故取各 1 秒窗比值中位數）
    # 一致性：再用旁白最後 12 秒獨立找一次起點，兩處差 >10 ms 就報錯（防漂移／剪接位移）
    tail0 = max(0, len(nar) - 12 * SR); k2, sc3 = xcorr_offset(ref, nar[tail0:], lo=max(0, k + tail0 - SR), hi=k + tail0 + SR)
    drift_ms = (k2 - tail0 - k) / SR * 1000
    print(f'旁白起點交叉驗證：前段 {k / SR:.4f} 秒、後段推回起點 {(k2 - tail0) / SR:.4f} 秒（差 {drift_ms:+.2f} ms，相關 {sc3:.3f}）')
    if abs(drift_ms) > 10 or sc1 < 0.9 or sc3 < 0.9: sys.exit('錯誤：旁白對齊誤差 >10 ms 或相關太低')
    seg = ref[k:k + len(nar)]; m = min(len(seg), len(nar))
    rs = []
    for i in range(0, m - SR, SR):
        x, y = nar[i:i + SR], seg[i:i + SR]
        if np.sum(x ** 2) > 1e-4: rs.append(np.dot(x, y) / np.dot(x, x))
    g_nar = float(np.median(rs))
    # 片尾卡音效：在原片音軌最後 outro_dur+2 秒內找 mp3 前 3 秒
    lo = max(0, len(ref) - int((outro_dur + 2.5) * SR)); Lm = min(len(om), 3 * SR)
    ko, sc2 = xcorr_offset(ref[lo:], om[:Lm]); ko += lo
    segm = ref[ko:ko + len(om)]; mm = min(len(segm), len(om)); g_om = float(np.dot(om[:mm], segm[:mm]) / np.dot(om[:mm], om[:mm]))
    print(f'對齊：旁白起點 {k / SR:.4f} 秒（相關 {sc1:.3f}、增益 {g_nar:.3f}）；片尾卡音效起點 {ko / SR:.4f} 秒（相關 {sc2:.3f}、增益 {g_om:.3f}）；原片 {tot:.3f} 秒')
    # 取立體聲重組
    n = len(ref); buf = np.zeros(n)
    nn = min(len(nar), n - k); buf[k:k + nn] += g_nar * nar[:nn]
    mo = min(len(om), n - ko); buf[ko:ko + mo] += g_om * om[:mo]
    pk = float(np.max(np.abs(buf))); sc_ = min(1.0, 0.9 / pk); buf *= sc_   # 整體等比縮放避免削波（後面 add-sfx 會 loudnorm 回 -16 LUFS，不影響相對關係）
    print(f'重組音軌峰值 {pk:.3f}（整體縮放 {sc_:.3f}）')
    open(nw, 'wb').write(b'')  # 先建檔
    import wave
    def wr(p, x, s=None):
        x = x if s is None else x[:int(s * SR)]
        with wave.open(p, 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            y = (np.clip(x, -1, 1) * 32767).astype('<i2'); w.writeframes(np.repeat(y, 2).tobytes())
    base = os.path.splitext(out)[0] + '.base.wav'
    wr(base, buf, secs)
    # 對齊後旁白（供出片檢查當人聲基準；長度同底音軌）
    nb = np.zeros(n); nb[k:k + nn] = nar[:nn]; wr(nw, nb, secs)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', nos, '-i', base, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-ar', '48000'] + (['-t', str(secs)] if secs else []) + [out]
    subprocess.check_call(cmd); os.remove(base)
    json.dump({'narr_start': k / SR, 'narr_corr': sc1, 'narr_gain': g_nar, 'drift_ms': drift_ms, 'outro_start': ko / SR, 'outro_corr': sc2, 'outro_gain': g_om}, open(os.path.splitext(out)[0] + '.align.json', 'w'))
main()
