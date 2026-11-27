#!/usr/bin/env python3
"""比對兩支成片（容器渲的 vs Actions 分段渲的）：python3 v9/compare_render.py <甲.mp4> <乙.mp4> [--out DIR]
片長差（秒）＋逐秒抽格（每 1 秒取 0.5、1.5、…秒那一格）同秒兩張的像素平均絕對差（佔 255 的 %）。
判準（2026-11-27 Andy 指示、render_check_20261127.md）：片長差 ≤0.05 秒；逐秒抽格平均差 ≤2%（取全部秒數的最大值與平均）。
抽格不是渲染，可以在容器做。輸出 JSON 到 stdout，並把最差的 3 秒並排圖存到 --out。"""
import sys, os, json, subprocess, tempfile
import numpy as np
from PIL import Image
a = sys.argv[1:]; A, B = a[0], a[1]; OUT = a[a.index("--out") + 1] if "--out" in a else None
def dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout)
def frames(p, d, n):
    # 每秒取該秒中點一格；縮到 270x480 比（不影響平均差判斷、省時間）
    for i in range(n):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(i + .5), "-i", p, "-frames:v", "1", "-vf", "scale=270:480", os.path.join(d, "f%03d.png" % i)], check=True)
da, db = dur(A), dur(B); n = int(min(da, db))
with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
    frames(A, ta, n); frames(B, tb, n); diffs = []
    for i in range(n):
        x = np.asarray(Image.open(os.path.join(ta, "f%03d.png" % i)).convert("RGB"), dtype=np.float32); y = np.asarray(Image.open(os.path.join(tb, "f%03d.png" % i)).convert("RGB"), dtype=np.float32)
        diffs.append(float(np.abs(x - y).mean() / 255 * 100))
    if OUT:
        os.makedirs(OUT, exist_ok=True)
        for i in sorted(range(n), key=lambda k: -diffs[k])[:3]:
            im = Image.new("RGB", (540, 480)); im.paste(Image.open(os.path.join(ta, "f%03d.png" % i)), (0, 0)); im.paste(Image.open(os.path.join(tb, "f%03d.png" % i)), (270, 0)); im.save(os.path.join(OUT, "worst_%02ds.png" % i))
r = {"dur_a": round(da, 3), "dur_b": round(db, 3), "dur_diff": round(abs(da - db), 3), "seconds_compared": n,
     "diff_pct_mean": round(float(np.mean(diffs)), 3), "diff_pct_max": round(max(diffs), 3), "worst_seconds": sorted(range(n), key=lambda k: -diffs[k])[:3], "per_second_pct": [round(d, 3) for d in diffs]}
r["pass"] = bool(r["dur_diff"] <= 0.05 and r["diff_pct_max"] <= 2.0)
print(json.dumps(r, ensure_ascii=False))
