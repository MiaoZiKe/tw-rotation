#!/usr/bin/env python3
"""流暢度檢查（2026-11-27；Andy：「影片很棒，但是看起來感覺卡卡的 幫我避免」）。v9/verify4.py 會自動呼叫，也可單獨跑：
    python3 v9/smooth_check.py <video.mp4> [--chunk 60]
抓三類卡頓：
 A. 時間戳：播放器照 PTS 排順序。PTS 倒退／重複（B 幀沒正確封裝）、幀距 ≠ 1/fps（掉幀或重複時間）、幀數 ≠ 片長×fps → 不合格。
    11-27 事故：分段渲染把裸 h264（含 B 幀）cat 起來再 -c:v copy 封裝，外食片 1530 幀有 673 幀 PTS 倒退，畫面前後跳格。
 B. 畫面變化量（270×480 灰階逐幀平均絕對差 m[i]＝幀 i 與 i+1）：
    · 動態中孤立停格：m[i]<0.05 但前後兩個變化量都 >0.6（畫面在動卻卡一格）
    · 顯示順序倒退：幀 i-1 與 i+1 的差 < 0.5×min(m[i-1], m[i])，且都在動（中間那格是從後面或前面插進來的）
 C. 段接縫（每 chunk 幀，即分段渲染的第 k×chunk 幀）：接縫前 3 個與後 3 個變化量的中位數都 >0.3（正在動）時，接縫變化量 > 中位數×3＋1.0（跳格）或 <0.05（停格）。
    靜止畫面中的單次變化（字幕換句、元素出現）不算 —— 那是內容本身。
門檻：A 全部要 0；B 停格 ≤2、倒退 ≤2（呼吸、閃爍類來回動畫會有 1～2 格 A-B-A）；C 0。"""
import json, subprocess, sys
import numpy as np
W, H = 270, 480
def smooth_check(vid, chunk=60):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate:format=duration", "-show_entries", "frame=pts_time", "-of", "json", vid], capture_output=True, text=True).stdout)
    a_, b_ = pr["streams"][0]["r_frame_rate"].split("/"); fps = float(a_) / float(b_); dur = float(pr["format"]["duration"])
    pts = np.array([float(f["pts_time"]) for f in pr.get("frames", []) if f.get("pts_time") not in (None, "N/A")])
    d = np.diff(pts); back = int((d <= 1e-6).sum()); gap = int((np.abs(d - 1 / fps) > .25 / fps).sum())
    expect = int(round(dur * fps)); nfr = len(pts)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", vid, "-vf", "scale=%d:%d,format=gray" % (W, H), "-f", "rawvideo", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    m = np.abs(np.diff(fr, axis=0)).mean((1, 2))
    stall = [i + 1 for i in range(1, len(m) - 1) if m[i] < .05 and m[i - 1] > .6 and m[i + 1] > .6]
    rev = []
    for i in range(1, len(m)):
        if m[i - 1] > .6 and m[i] > .6:
            skip = np.abs(fr[i + 1] - fr[i - 1]).mean()
            if skip < .5 * min(m[i - 1], m[i]): rev.append(i)
    seam = []
    for s in range(chunk, len(fr), chunk):
        i = s - 1   # m[i]＝幀 s-1 → s
        nb = np.r_[m[max(0, i - 3):i], m[i + 1:i + 4]]
        if not len(nb): continue
        med = float(np.median(nb))
        pre, post = m[max(0, i - 3):i], m[i + 1:i + 4]
        moving = len(pre) and len(post) and float(np.median(pre)) > .3 and float(np.median(post)) > .3   # 接縫前後都在動（排除換鏡起訖）
        jump = moving and m[i] > med * 3 + 1.0              # 動態中接縫突然大跳（時間不連續）
        freeze = moving and m[i] < .05                      # 動態中接縫停一格
        if jump or freeze: seam.append({"frame": s, "t": round(s / fps, 3), "m": round(float(m[i]), 2), "nb_med": round(med, 2), "kind": "跳格" if jump else "停格"})
    bad = []
    if back: bad.append("流暢度：PTS 倒退／重複 %d 幀（播放會前後跳格）" % back)
    if gap: bad.append("流暢度：幀距不是 1/%g 秒的有 %d 處（掉幀／重複時間）" % (fps, gap))
    if abs(nfr - expect) > 1: bad.append("流暢度：幀數 %d ≠ 片長×fps %d" % (nfr, expect))
    if len(stall) > 2: bad.append("流暢度：動態中孤立停格 %d 格（%s）" % (len(stall), "、".join("%.2fs" % (x / fps) for x in stall[:8])))
    if len(rev) > 2: bad.append("流暢度：顯示順序倒退 %d 格（%s）" % (len(rev), "、".join("%.2fs" % (x / fps) for x in rev[:8])))
    if seam: bad.append("流暢度：段接縫變化量異常 %d 處（%s）" % (len(seam), "、".join("%.2fs" % x["t"] for x in seam[:8])))
    seam_m = [float(m[s - 1]) for s in range(chunk, len(fr), chunk)]
    return {"fps": fps, "frames": nfr, "expect": expect, "pts_back": back, "pts_gap": gap, "dup_ratio": round(float((m < .05).mean()), 3),
            "stall": len(stall), "stall_t": [round(x / fps, 2) for x in stall], "reverse": len(rev), "reverse_t": [round(x / fps, 2) for x in rev],
            "seam_mean": round(float(np.mean(seam_m)), 3) if seam_m else None, "nonseam_mean": round(float(np.delete(m, [s - 1 for s in range(chunk, len(fr), chunk)]).mean()), 3),
            "seam_bad": seam, "chunk": chunk, "bad": bad, "pass": not bad}
if __name__ == "__main__":
    a = sys.argv[1:]; c = int(a[a.index("--chunk") + 1]) if "--chunk" in a else 60
    r = smooth_check(a[0], c); print(json.dumps({k: v for k, v in r.items() if k not in ("stall_t", "reverse_t")}, ensure_ascii=False))
    sys.exit(0 if r["pass"] else 1)
