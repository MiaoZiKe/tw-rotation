#!/usr/bin/env python3
"""通用音效合成器（程式合成，不用任何外部音檔或版權素材）。

依賴：只用 python3＋numpy（輸出／混音另需 ffmpeg，由 add-sfx.sh 呼叫）。不依賴 storyboard／model.json／任何 3D 專案檔。
固定亂數 seed（20261127），同一份 cue 表每次產出的聲音一模一樣。

一、cue 表 → sfx.wav
    python3 sfx-synth.py render <cues.json> <out.wav> [--total 秒數] [--end 片尾卡開始秒] [--cues-out 實際排出的紀錄.json]
  cues.json 格式（陣列，或 {"total":秒,"endCardSec":秒,"cues":[…]}）：
    [{"t": 3.2, "dur": 1.5, "kind": "rain", "gain": 0, "pan": 0.5, "params": {…}, "src": "備註"}, …]
    t＝開始秒；dur＝持續秒（瞬間聲可省略）；kind＝登錄表的種類；gain＝在該種類預設音量上再加減的 dB（可省略）；
    pan＝0（左）~1（右），省略＝0.5；params＝該函式的額外參數；src＝備註（寫進紀錄）。
  輸出 48 kHz 16-bit 立體聲 wav，第 0 個樣本＝影片第 0 秒。--end 之後保證靜音。

二、混進原片音軌（旁白講話時自動壓低）
    python3 sfx-synth.py mix <原片音軌.wav 48k16bit> <sfx.wav> <輸出.wav> [--end <片尾卡開始秒>]
    python3 sfx-synth.py check <原旁白音軌.wav> <成片解碼音軌.wav> [--end 秒]   成片解碼後關卡，<14 dB 結束碼 1

三、可用的 kind（KINDS 登錄表；加新種類＝寫一個 fn(dur, **params)→單聲道 numpy 陣列，再 register("名字", fn, 預設dB)）
  機械類（科技片用）：motor 轉軸嗡聲｜servo 伺服 whir｜hiss 氣流｜liquid 液體｜plasma 電漿電流｜sputter 濺鍍劈啪｜heat 爐火｜
      chips 碎屑點擊｜clunk 金屬撞擊｜slide 滑軌｜valve 氣動 click｜whoosh 氣流掃過｜buzz 高頻震動｜thump 低頻悶響
  生活類：footstep 腳步（params: n 步數、gap 步距秒、shoe soft／hard）｜door 開關門（params: close true／false）｜
      cup 杯子放桌（clink 加一聲輕碰）｜keyboard 打字（params: rate 每秒鍵數）｜pageturn 翻書頁｜rain 雨聲（params: heavy 0~1）
"""
import sys, os, re, json, wave, math
import numpy as np

SR = 48000
rng = np.random.default_rng(20261127)

# ---------------------------------------------------------------- 參數表（改音色在這裡）
# 各類相對音量（dB，0 dB＝內部參考；進混音前整體再被 mix 子命令依旁白響度重設）
GAIN_DB = dict(motor=-2, servo=-2, hiss=-4, liquid=-3, plasma=-5, sputter=-8, heat=-6,
               chips=-9, clunk=2, valve=-4, whoosh=-8)
MOTOR_BASE_HZ = 62.0      # 轉軸嗡聲基頻；實際 = BASE * (1 + 0.9*rps)，rps 越高越尖
MOTOR_HARM = (1.0, 0.55, 0.30, 0.12)
MOTOR_AM_PER_RPS = 6.0    # 轉動造成的振幅起伏頻率 = rps * 這個倍數
SERVO_HZ = (520.0, 1250.0)   # whir 掃頻起訖
SERVO_DUR = 0.42
HISS_BAND = (1800.0, 7500.0)
HISS_VALVE_MS = 70
LIQUID_BAND = (250.0, 2600.0)
LIQUID_DRIP_PER_S = 5.0
PLASMA_HUM_HZ = 100.0
PLASMA_CRACKLE_PER_S = 22.0
SPUTTER_PER_S = 38.0
HEAT_BAND = (40.0, 260.0)
CHIPS_PER_S = 7.0
CLUNK_HZ = 88.0
CLUNK_DECAY = 0.16
SLIDE_DUR = 0.28
FADE_S = 0.12             # 每段持續音的淡入淡出秒數
LEVEL_BELOW = -10.0       # 混音：sfx（動音段平均）比旁白低 dB（未壓低時）；壓低後在講話時約低 18 dB
DUCK_DB = -8.0            # 混音：旁白講話時 sfx 再壓低
DUCK_ATTACK_S = 0.03
DUCK_RELEASE_S = 0.28



# ---------------------------------------------------------------- 基本工具
def db(x): return 10 ** (x / 20.0)

def fft_filter(x, lo=None, hi=None, slope=2.0):
    """用 FFT 做平滑的帶通（lo／hi 為 None 表示只做低通或高通）。"""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    m = np.ones_like(f)
    if lo: m *= 1.0 / (1.0 + (lo / np.maximum(f, 1e-3)) ** (2 * slope))
    if hi: m *= 1.0 / (1.0 + (f / hi) ** (2 * slope))
    return np.fft.irfft(X * m, n)

def white(n): return rng.standard_normal(n)

def pink(n):
    X = np.fft.rfft(white(n))
    f = np.fft.rfftfreq(n, 1.0 / SR); f[0] = f[1] if len(f) > 1 else 1
    return np.fft.irfft(X / np.sqrt(f), n)

def norm(x):
    p = np.max(np.abs(x)) + 1e-9
    return x / p

def env_fade(n, fade):
    a = np.ones(n)
    k = min(int(fade * SR), n // 2)
    if k > 0:
        r = np.linspace(0, 1, k) ** 2
        a[:k] = r; a[-k:] = r[::-1]
    return a

def ramp_env(n, ramp_s, fade):
    """持續音包絡：前 ramp_s 秒升（或降）速度，頭尾淡入淡出。"""
    a = env_fade(n, fade)
    return a


# ---------------------------------------------------------------- 各類聲音（回傳單聲道 float 陣列）
def s_motor(dur, rps=0.5, ramp=0.4, spin_ramp=True):
    n = int(dur * SR); t = np.arange(n) / SR
    k = np.clip(t / max(ramp, 0.05), 0, 1) if spin_ramp else np.ones(n)
    k2 = np.minimum(k, np.clip((dur - t) / max(ramp, 0.05), 0, 1)) if spin_ramp else k
    f0 = MOTOR_BASE_HZ * (1 + 0.9 * rps) * (0.55 + 0.45 * k2)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    y = sum(a * np.sin((i + 1) * ph + i) for i, a in enumerate(MOTOR_HARM))
    am = 1 + 0.18 * np.sin(2 * np.pi * rps * MOTOR_AM_PER_RPS * t)
    y = y * am + 0.12 * fft_filter(white(n), 200, 1800)
    return norm(y) * env_fade(n, FADE_S) * (0.35 + 0.65 * k2)

def s_servo(dur=SERVO_DUR):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = SERVO_HZ[0] + (SERVO_HZ[1] - SERVO_HZ[0]) * np.sin(np.pi * u) ** 1.5
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sign(np.sin(ph)) * 0.25 + np.sin(ph) * 0.6 + np.sin(2 * ph) * 0.2
    y = fft_filter(y, 300, 3500) + 0.15 * fft_filter(white(n), 1500, 5000)
    return norm(y) * np.sin(np.pi * u) ** 0.7

def s_hiss(dur):
    n = int(dur * SR)
    y = fft_filter(white(n), *HISS_BAND)
    slow = 1 + 0.15 * fft_filter(white(n), None, 3.0)   # 氣流忽大忽小
    return norm(y * np.clip(slow, 0.5, 1.5)) * env_fade(n, FADE_S + 0.05)

def s_liquid(dur):
    n = int(dur * SR)
    y = fft_filter(pink(n), *LIQUID_BAND)
    gur = 1 + 0.45 * fft_filter(white(n), None, 9.0) / (np.std(fft_filter(white(n), None, 9.0)) + 1e-9) * 0.3
    y = norm(y) * np.clip(gur, 0.4, 1.6) * 0.8
    for _ in range(int(dur * LIQUID_DRIP_PER_S)):      # 水滴：向上掃的短正弦
        t0 = rng.integers(0, max(n - 4000, 1)); L = int(rng.uniform(0.02, 0.05) * SR)
        tt = np.arange(L) / SR; f = rng.uniform(900, 2200) * (1 + 3 * tt / 0.05)
        d = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.012) * rng.uniform(0.25, 0.6)
        y[t0:t0 + L] += d[:max(0, min(L, n - t0))] if t0 + L <= n else d[:n - t0]
    return norm(y) * env_fade(n, FADE_S + 0.05)

def crackle(n, rate, lo=2500, hi=7000, decay=0.003, amp=(0.2, 1.0)):
    y = np.zeros(n)
    cnt = rng.poisson(rate * n / SR)
    for _ in range(cnt):
        t0 = rng.integers(0, n); L = int(decay * 8 * SR)
        tt = np.arange(L) / SR
        d = np.sin(2 * np.pi * rng.uniform(lo, hi) * tt) * np.exp(-tt / decay) * rng.uniform(*amp)
        e = min(L, n - t0); y[t0:t0 + e] += d[:e]
    return y

def s_plasma(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    hum = (np.sin(2 * np.pi * PLASMA_HUM_HZ * t) + 0.5 * np.sin(2 * np.pi * PLASMA_HUM_HZ * 3 * t + 1)
           + 0.25 * np.sin(2 * np.pi * PLASMA_HUM_HZ * 5 * t + 2)) * (1 + 0.12 * np.sin(2 * np.pi * 7 * t))
    y = norm(hum) * 0.7 + 0.18 * fft_filter(white(n), 3000, 9000)
    y += 0.5 * crackle(n, PLASMA_CRACKLE_PER_S)
    return norm(y) * env_fade(n, FADE_S + 0.05)

def s_sputter(dur):
    n = int(dur * SR)
    y = crackle(n, SPUTTER_PER_S, 1800, 6500, 0.0025, (0.15, 1.0)) + 0.08 * fft_filter(white(n), 2500, 8000)
    return norm(y) * env_fade(n, FADE_S)

def s_heat(dur):
    n = int(dur * SR)
    y = norm(fft_filter(pink(n), *HEAT_BAND)) * (1 + 0.2 * fft_filter(white(n), None, 1.5) * 30)
    y += 0.25 * crackle(n, 1.2, 600, 1400, 0.01)
    return norm(y) * env_fade(n, 0.3)

def s_chips(dur):
    n = int(dur * SR)
    return norm(crackle(n, CHIPS_PER_S, 3500, 6500, 0.0018, (0.4, 1.0)) + 1e-6) * env_fade(n, FADE_S)

def s_clunk(strength=1.0):
    n = int(0.55 * SR); t = np.arange(n) / SR
    low = np.sin(2 * np.pi * (CLUNK_HZ * (1 + 0.5 * np.exp(-t / 0.03))) * t) * np.exp(-t / CLUNK_DECAY)
    ns = fft_filter(white(n), 900, 4200) * np.exp(-t / 0.035)
    met = (np.sin(2 * np.pi * 743 * t) + 0.7 * np.sin(2 * np.pi * 1171 * t + 1) + 0.4 * np.sin(2 * np.pi * 1763 * t + 2)) * np.exp(-t / 0.07)
    return norm(0.9 * low + 0.45 * ns + 0.22 * met) * strength

def s_slide(dur=SLIDE_DUR):
    n = int(dur * SR); u = np.arange(n) / n
    y = fft_filter(white(n), 350, 1700) * (np.sin(np.pi * u) ** 1.3)
    return norm(y) * 0.5

def s_valve():
    n = int(0.16 * SR); t = np.arange(n) / SR
    click = fft_filter(white(n), 2200, None) * np.exp(-t / 0.006)
    psst = fft_filter(white(n), 3000, 9000) * np.exp(-t / (HISS_VALVE_MS / 1000 / 2.5)) * 0.35
    return norm(click + psst)

def s_whoosh(dur, strength=1.0):
    n = int(max(dur, 0.3) * SR); u = np.arange(n) / n
    y = fft_filter(pink(n), 180, 1700) * np.sin(np.pi * u) ** 2
    return norm(y) * min(strength, 1.0)

def s_buzz(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.4 + fft_filter(white(n), 300, 2500) * 0.3
    return norm(y) * env_fade(n, FADE_S)

def s_thump(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return norm(np.sin(2 * np.pi * 55 * t) * np.exp(-t / 0.2)) * env_fade(n, 0.01)



# ---------------------------------------------------------------- 生活類聲音
def _tick(n, t0, f, decay, amp=1.0, y=None):
    L = int(decay * 8 * SR); tt = np.arange(L) / SR
    d = np.sin(2 * np.pi * f * tt) * np.exp(-tt / decay) * amp
    e = min(L, n - t0)
    if e > 0: y[t0:t0 + e] += d[:e]

def s_footstep(dur=0.0, n=4, gap=0.5, shoe='soft'):
    tot = int((gap * (n - 1) + 0.4) * SR); y = np.zeros(tot)
    for i in range(n):
        t0 = int(i * gap * SR * rng.uniform(0.95, 1.05)); L = int(0.14 * SR); tt = np.arange(L) / SR
        thud = np.sin(2 * np.pi * 85 * tt) * np.exp(-tt / 0.03)
        sc = fft_filter(white(L), 1500 if shoe == 'hard' else 400, 5000 if shoe == 'hard' else 1800) * np.exp(-tt / (0.012 if shoe == 'hard' else 0.03))
        d = (thud * 0.8 + sc * (0.9 if shoe == 'hard' else 0.5)) * rng.uniform(0.75, 1.0)
        e = min(L, tot - t0); y[t0:t0 + e] += d[:e]
    return norm(y)

def s_door(dur=0.0, close=False):
    n = int(0.9 * SR); t = np.arange(n) / SR; y = np.zeros(n)
    y += fft_filter(white(n), 300, 1400) * 0.25 * np.sin(np.pi * np.clip(t / 0.45, 0, 1)) ** 2          # 鉸鏈摩擦
    t0 = int((0.42 if close else 0.05) * SR); L = int(0.3 * SR); tt = np.arange(L) / SR
    clk = (np.sin(2 * np.pi * 120 * tt) * np.exp(-tt / 0.06) + fft_filter(white(L), 700, 3500) * np.exp(-tt / 0.02) * 0.8)
    e = min(L, n - t0); y[t0:t0 + e] += clk[:e] * (1.0 if close else 0.5)
    return norm(y)

def s_cup(dur=0.0, clink=True):
    n = int(0.7 * SR); t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.03) + fft_filter(white(n), 600, 3000) * np.exp(-t / 0.012) * 0.6)
    if clink:
        t0 = int(0.12 * SR); tt = np.arange(n - t0) / SR
        y[t0:] += (np.sin(2 * np.pi * 2150 * tt) + 0.5 * np.sin(2 * np.pi * 3340 * tt)) * np.exp(-tt / 0.12) * 0.4
    return norm(y)

def s_keyboard(dur=2.0, rate=7.0):
    n = int(dur * SR); y = np.zeros(n); t = 0.0
    while t < dur - 0.05:
        t0 = int(t * SR); _tick(n, t0, rng.uniform(1800, 3000), 0.004, rng.uniform(0.5, 1.0), y)
        _tick(n, t0, 140, 0.012, 0.5, y)
        t += rng.exponential(1.0 / rate) * 0.6 + 0.4 / rate
    return norm(y + 1e-6) * env_fade(n, 0.05)

def s_pageturn(dur=0.0):
    n = int(0.7 * SR); u = np.arange(n) / n
    y = fft_filter(white(n), 1200, 7000) * (np.sin(np.pi * u) ** 3) * (1 + 0.5 * fft_filter(white(n), None, 40) / 0.2)
    return norm(y) * 0.8

def s_rain(dur=3.0, heavy=0.5):
    n = int(dur * SR)
    y = fft_filter(white(n), 3000, 9000) * 0.6 + fft_filter(pink(n), 400, 2500) * 0.5
    y += crackle(n, 80 + 400 * heavy, 2500, 8000, 0.0015, (0.2, 0.7)) * 0.6
    return norm(y) * env_fade(n, 0.4)


# ---------------------------------------------------------------- 登錄表
KINDS = {}   # kind -> (函式 fn(dur, **params) -> 單聲道陣列, 預設音量 dB)

def register(kind, fn, gain_db=0.0):
    KINDS[kind] = (fn, gain_db)

register('motor', lambda dur, rps=0.5, ramp=0.4, rampSpin=True, **k: s_motor(dur, rps, ramp, rampSpin), GAIN_DB['motor'])
register('servo', lambda dur, n=2, **k: _servo_seq(dur, n), GAIN_DB['servo'])
register('hiss', lambda dur, **k: s_hiss(dur), GAIN_DB['hiss'])
register('liquid', lambda dur, **k: s_liquid(dur), GAIN_DB['liquid'])
register('plasma', lambda dur, **k: s_plasma(dur), GAIN_DB['plasma'])
register('sputter', lambda dur, **k: s_sputter(dur), GAIN_DB['sputter'])
register('heat', lambda dur, **k: s_heat(dur), GAIN_DB['heat'])
register('chips', lambda dur, **k: s_chips(dur), GAIN_DB['chips'])
register('clunk', lambda dur, strength=1.0, **k: s_clunk(strength), GAIN_DB['clunk'])
register('slide', lambda dur, **k: s_slide(max(dur, 0.15)), GAIN_DB['clunk'])
register('valve', lambda dur, **k: s_valve(), GAIN_DB['valve'])
register('whoosh', lambda dur, strength=0.6, **k: s_whoosh(dur, strength) * min(strength, 1.0), GAIN_DB['whoosh'])
register('buzz', lambda dur, **k: s_buzz(dur), GAIN_DB['motor'])
register('thump', lambda dur, **k: s_thump(max(dur, 0.4)), GAIN_DB['clunk'])
register('footstep', s_footstep, -2)
register('door', s_door, 0)
register('cup', s_cup, -2)
register('keyboard', s_keyboard, -4)
register('pageturn', s_pageturn, -4)
register('rain', s_rain, -6)

def _servo_seq(dur, n):
    y = np.zeros(int(dur * SR) + int(SERVO_DUR * SR))
    for i in range(n):
        s0 = int(i * dur / n * SR); w = s_servo(SERVO_DUR * (0.8 + 0.4 * ((i * 7) % 3) / 2))
        y[s0:s0 + len(w)] += w[:len(y) - s0]
    return y


def render_cues(cues, total_sec, end_t=None):
    """cue 表 → (2, N) 立體聲 buffer 與實際排出的紀錄。"""
    buf = np.zeros((2, int(total_sec * SR)))
    out = []
    cutoff = end_t if end_t is not None else total_sec + 1
    for c in sorted(cues, key=lambda z: z['t']):
        k = c['kind']
        if k not in KINDS: raise SystemExit(f'未登錄的 kind：{k}（可用：{", ".join(KINDS)}）')
        fn, gdb = KINDS[k]
        t0 = float(c['t']); dur = float(c.get('dur') or 0)
        if t0 >= cutoff: continue
        dur = max(0.0, min(t0 + dur, cutoff - 0.05) - t0) if dur else 0.0
        y = fn(dur, **(c.get('params') or {}))
        if y is None or len(y) == 0: continue
        g = db(gdb + float(c.get('gain') or 0))
        place(buf, y, t0, float(c.get('pan', 0.5)), g)
        out.append(dict(t=round(t0, 3), t_end=round(t0 + len(y) / SR, 3), type=k, src=c.get('src', ''), gain_db=round(gdb + float(c.get('gain') or 0), 1)))
    if end_t is not None:
        i = int(end_t * SR); k = int(0.1 * SR)
        buf[:, max(0, i - k):i] *= np.linspace(1, 0, min(k, i))
        buf[:, i:] = 0
    pk = np.max(np.abs(buf)) + 1e-9
    return buf / pk * 0.5, out      # 內部參考：峰值 −6 dBFS；實際音量由 mix 依旁白決定


def pan_of(name):
    h = sum(ord(c) for c in name) % 100 / 100.0
    return 0.3 + 0.4 * h     # 0.3~0.7，偏中間，不要忽左忽右

def place(buf, y, t0, pan=0.5, gain=1.0):
    i0 = int(t0 * SR)
    if i0 >= buf.shape[1]: return
    n = min(len(y), buf.shape[1] - i0)
    if n <= 0: return
    th = pan * np.pi / 2
    buf[0, i0:i0 + n] += y[:n] * np.cos(th) * gain
    buf[1, i0:i0 + n] += y[:n] * np.sin(th) * gain



def write_wav(path, buf):
    d = (np.clip(buf, -1, 1) * 32767).astype('<i2').T.reshape(-1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())

def read_wav(path):
    with wave.open(path, 'rb') as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        assert sw == 2 and sr == SR, f'{path} 要 48k 16-bit（ffmpeg -ar 48000 -c:a pcm_s16le）'
        x = np.frombuffer(w.readframes(n), '<i2').astype(np.float64) / 32768
    return x.reshape(-1, ch).T


def frame_rms(x, hop):
    n = x.shape[1] // hop
    return np.sqrt((x[:, :n * hop].reshape(x.shape[0], n, hop) ** 2).mean(axis=(0, 2)) + 1e-12)


MIN_GAP_DB = 14.0         # 硬門檻：旁白講話的每一窗，sfx 要比旁白低至少這麼多 dB（Andy 2026/11/27：「不要影響旁白聲」）
GUARD_MARGIN_DB = 1.5     # 逐窗天花板多留的餘裕

def sp_full(speech, nf):
    # 講話窗往前後各放寬 2 窗（含壓低的 attack／release 區），這些窗也受天花板限制
    m = speech[:nf] > 0.5
    k = m.copy()
    for d in (1, 2):
        k |= np.roll(m, d) | np.roll(m, -d)
    return k


def cmd_mix(argv):
    voice, sfx, out = argv[0], argv[1], argv[2]
    end = float(argv[argv.index('--end') + 1]) if '--end' in argv else None
    v = read_wav(voice); s = read_wav(sfx)
    n = v.shape[1]
    if s.shape[1] < n: s = np.pad(s, ((0, 0), (0, n - s.shape[1])))
    s = s[:, :n]
    if v.shape[0] == 1: v = np.vstack([v, v])
    hop = int(0.02 * SR)
    ve = frame_rms(v, hop)
    lim = int((end if end is not None else n / SR) * SR) // hop
    vlim = ve[:lim]
    thr = max(np.max(vlim) * db(-26), 1e-4)         # 旁白在講話：比最大音量低 26 dB 以內
    speech = (vlim > thr).astype(float)
    speech = np.concatenate([speech, np.zeros(len(ve) - lim)])
    # 旁白講話時壓低：attack／release 一階平滑
    a_att = math.exp(-hop / SR / DUCK_ATTACK_S); a_rel = math.exp(-hop / SR / DUCK_RELEASE_S)
    sm = np.zeros(len(speech)); c = 0.0
    for i, sp in enumerate(speech):
        c = (sp + (c - sp) * a_att) if sp > c else (sp + (c - sp) * a_rel)
        sm[i] = c
    duck = db(DUCK_DB) ** sm                         # 1 → −8 dB
    duck_s = np.repeat(duck, hop)
    duck_s = np.pad(duck_s, (0, n - len(duck_s)), constant_values=1.0)[:n]
    # 音量：sfx 動音段 RMS 比旁白講話段 RMS 低 LEVEL_BELOW（壓低前）
    sm_act = frame_rms(s, hop); act = sm_act > np.max(sm_act) * db(-40)
    sfx_rms = np.sqrt((sm_act[act] ** 2).mean()) if act.any() else 1e-6
    sp_mask = speech > 0.5
    voice_rms = np.sqrt((ve[sp_mask] ** 2).mean()) if sp_mask.any() else np.sqrt((ve ** 2).mean())
    g = voice_rms * db(LEVEL_BELOW) / sfx_rms
    # 軟限幅：瞬間聲（clunk、閥門）峰值不超過 sfx 平均 RMS 的 3 倍，避免蓋過旁白字尾
    cap = 3.0 * sfx_rms
    s = np.tanh(s / cap) * cap
    sfx_rms = np.sqrt((frame_rms(s, hop)[act] ** 2).mean()) if act.any() else sfx_rms
    g = voice_rms * db(LEVEL_BELOW) / sfx_rms
    sd = s * g * duck_s[None, :]
    # 硬性保護：旁白講話的每一個 20 ms 窗，sfx RMS ≤ 該窗旁白 RMS −(MIN_GAP_DB+MARGIN_DB)；
    # 逐窗算增益上限（鄰窗取最小，再用線性內插平滑到每個樣本），撞擊聲落在講話中就被縮小。
    nf = len(ve)
    se = frame_rms(sd, hop)
    ceil_ = ve * db(-(MIN_GAP_DB + GUARD_MARGIN_DB))
    gf = np.where(sp_full(speech, nf), np.minimum(1.0, ceil_ / np.maximum(se, 1e-9)), 1.0)
    gf = np.minimum(gf, np.minimum(np.roll(gf, 1), np.roll(gf, -1)))       # 鄰窗取最小
    gf = np.minimum(gf, np.minimum(np.roll(gf, 2), np.roll(gf, -2)))
    xs = (np.arange(nf) + 0.5) * hop
    gs = np.interp(np.arange(n), xs, gf)
    sd = sd * gs[None, :]
    mix = v + sd
    # 量測：講話窗逐窗最小差距（旁白 RMS 對 sfx RMS）
    se2 = frame_rms(sd, hop); spk = speech[:nf] > 0.5
    gap = 20 * np.log10(ve[spk] / np.maximum(se2[spk], 1e-9))
    worst = float(gap.min()) if spk.any() else 99.0
    print(f'講話段逐窗最小差距 {worst:.1f} dB（門檻 {MIN_GAP_DB} dB；講話窗 {int(spk.sum())} 個）')
    if worst < MIN_GAP_DB:
        sys.exit(f'錯誤：講話段有 sfx 只比旁白低 {worst:.1f} dB（<{MIN_GAP_DB}），不輸出')
    write_wav(out, mix)
    info = dict(voice_rms_db=round(20 * math.log10(voice_rms), 1), sfx_rms_db=round(20 * math.log10(sfx_rms * g), 1),
                gain=round(g, 4), duck_db=DUCK_DB, level_below_db=LEVEL_BELOW)
    print(json.dumps(info, ensure_ascii=False))



def cmd_check(argv):
    """成片解碼後關卡：旁白原音軌 vs 成片音軌，講話窗逐窗（成片 − 旁白）殘差（＝sfx＋轉碼誤差）比旁白低 ≥ MIN_GAP_DB。"""
    v = read_wav(argv[0]); f = read_wav(argv[1])
    end = float(argv[argv.index('--end') + 1]) if '--end' in argv else None
    n = min(v.shape[1], f.shape[1]); v = v[:, :n]; f = f[:, :n]
    c = np.fft.irfft(np.fft.rfft(f[0]) * np.conj(np.fft.rfft(v[0])), n=2 * n)      # 對齊（AAC 編碼延遲）
    lag = int(np.argmax(c)); lag = lag if lag < n else lag - 2 * n
    if abs(lag) > 0: f = np.roll(f, -lag, axis=1)
    k = (f * v).sum() / (v * v).sum()
    res = f - k * v; hop = int(0.02 * SR); m = n // hop
    ve = frame_rms(k * v, hop); se = frame_rms(res, hop)
    lim = int((end if end is not None else n / SR) * SR) // hop
    spk = np.zeros(len(ve), bool); spk[:lim] = ve[:lim] > ve[:lim].max() * db(-26)
    gap = 20 * np.log10(ve[spk] / np.maximum(se[spk], 1e-9)); worst = float(gap.min())
    w = int(np.where(spk)[0][int(gap.argmin())]) * 0.02
    print(f'成片解碼後講話段逐窗最小差距 {worst:.1f} dB（在 {w:.2f} 秒；門檻 {MIN_GAP_DB} dB；<14 的窗 {(gap < MIN_GAP_DB).sum()} 個；對齊偏移 {lag} 樣本）')
    if worst < MIN_GAP_DB: sys.exit(1)


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('render', 'mix', 'check'): print(__doc__); sys.exit(1)
    if a[0] == 'mix': return cmd_mix(a[1:])
    if a[0] == 'check': return cmd_check(a[1:])
    cj = json.load(open(a[1])); cues = cj['cues'] if isinstance(cj, dict) else cj
    end = float(a[a.index('--end') + 1]) if '--end' in a else (cj.get('endCardSec') if isinstance(cj, dict) else None)
    total = float(a[a.index('--total') + 1]) if '--total' in a else (cj.get('total') if isinstance(cj, dict) and cj.get('total') else max(c['t'] + (c.get('dur') or 0) for c in cues) + 1.5)
    buf, rec = render_cues(cues, total, end)
    write_wav(a[2], buf)
    if '--cues-out' in a:
        os.makedirs(os.path.dirname(a[a.index('--cues-out') + 1]) or '.', exist_ok=True)
        json.dump(dict(count=len(rec), endCardSec=end, cues=rec), open(a[a.index('--cues-out') + 1], 'w'), ensure_ascii=False, indent=1)
    print(f'{len(rec)} 個音效 → {a[2]}')


if __name__ == '__main__':
    main()
