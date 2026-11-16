#!/usr/bin/env python3
"""v8 補充檢查（render_video.js 之後跑）：
1. 靜止段（v8.1）：關掉光點與亮帶（static_pass.js）逐幀 1/4 解析度截圖，與前一幀比較，差 >10 灰階的像素少於 150 個＝主體靜止；列出 >1.2 秒的段（標準：靜止段 ≤1.2 秒）。
2. 強調淨空：em_shots.js 三張圖 → 強調像素＝A 與 B 不同；其他內容＝B 與 C 不同（排除強調本身）；量強調與其他文字／線稿的最短距離（標準 ≥16px）。
用法：python3 v8/check_v8.py <名> <報告 json>"""
import sys, os, glob, json, subprocess
import numpy as np
from PIL import Image
from scipy import ndimage
B = os.path.dirname(os.path.abspath(__file__)); VD = os.path.dirname(B)
name, outp = sys.argv[1:3]
SP = os.path.join("/tmp/claude-0/-home-user/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad", "static_" + name)
subprocess.run(["node", os.path.join(B, "static_pass.js"), name, SP], check=True)   # v8.1：關掉光點／亮帶後再判靜止（主體有沒有動）
fr = sorted(glob.glob(os.path.join(SP, "*.png")))
prev = None; still = []
for f in fr:
    a = np.asarray(Image.open(f).convert("L").resize((270, 480)), np.int16)
    still.append(prev is not None and int((np.abs(a - prev) > 10).sum()) < 150); prev = a   # 差 >10 灰階的像素 <150（約 0.12%）＝主體沒動
runs = []; i = 0
while i < len(still):
    if still[i]:
        j = i
        while j < len(still) and still[j]: j += 1
        runs.append((round((i - 1) / 30, 2), round((j - i + 1) / 30, 2))); i = j
    else: i += 1
long = [r for r in runs if r[1] > 1.2]
sd = os.path.join("/tmp/claude-0/-home-user/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad", "em_" + name)
subprocess.run(["node", os.path.join(B, "em_shots.js"), name, sd], check=True)
em = []
for s in json.load(open(os.path.join(sd, "shots.json"))):
    A, Bm, C = [np.asarray(Image.open(os.path.join(sd, "%s_%s.png" % (s["id"], k))).convert("RGB"), np.int16) for k in "ABC"]
    emm = np.abs(A - Bm).max(2) > 30; oth = (np.abs(Bm - C).max(2) > 40) & ~ndimage.binary_dilation(emm, iterations=2)
    oth[:140, :] = False; oth[1760:, :] = False   # LOGO／頁首與出處列不算
    if not emm.any(): continue
    dist = ndimage.distance_transform_edt(~oth); d = float(dist[emm].min())
    em.append({"id": s["id"], "t": s["t"], "min_px": round(d, 1), "ok": d >= 16})
rep = {"frames": len(fr), "static_runs_gt_1_2s": long, "static_max_s": max([r[1] for r in runs] or [0]), "emphasis": em, "emphasis_fail": [e for e in em if not e["ok"]]}
json.dump(rep, open(outp, "w"), ensure_ascii=False, indent=1)
print("靜止段最長 %.2f 秒；>1.2 秒：%s" % (rep["static_max_s"], long)); print("強調淨空：", [(e["id"], e["min_px"]) for e in em])

import shutil; shutil.rmtree(SP, ignore_errors=True)
