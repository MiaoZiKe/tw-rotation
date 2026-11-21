"""點下那一幀的全解析度裁圖（漣漪中心 ±200px），逐一人工目視用。
  python v3_clickframes.py --fmt web --out DIR
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_1010 as B
import render_v3 as R
import v3_build as VB
import v3_core as K
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--fmt", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--only", default="")
a = ap.parse_args()
R.set_theme("cute")
S = VB.shots_for(a.fmt)
L = K.Lay(a.fmt, "cute")
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
only = set(a.only.split(",")) if a.only else None
for s in S:
    if only and s.sid not in only:
        continue
    if not s.op:
        continue
    taps = [tp for tp in s.op.taps if not tp["hover"]]
    if not taps:
        continue
    n0 = len(K.CLICKS)
    last = int(round((max(tp["t"] for tp in taps) + 0.12) * 30))
    frames = {int(round(tp["t"] * 30)) + 2: tp for tp in taps}
    for k in range(0, last + 3):
        tt = k / 30
        need = k in frames or any(abs(k - f) <= 2 for f in frames)
        if k % 6 and not need and k not in (0,):
            continue
        im = s.render(tt, L)
        if k in frames:
            # CLICKS 由 tap 當幀登記；取最近一筆對應此 tap
            ck = [c for c in K.CLICKS[n0:] if c[0] == s.sid]
            tp = frames[k]
            cxy = s.rec.map(tp["cx"], tp["cy"])
            x0, y0 = int(cxy[0]) - 200, int(cxy[1]) - 200
            crop = im.crop((x0, y0, x0 + 400, y0 + 400)).convert("RGB")
            inf = K.click_info(s.rec.clip, tp["src_t"], tp["x"], tp["y"])
            d = ImageDraw.Draw(crop)
            d.rectangle([0, 0, 399, 22], fill=(255, 255, 255))
            d.text((4, 4), f"{s.sid} {inf['label'][:22]} {inf['src'][:14]}", fill=(200, 0, 0))
            crop.save(out / f"{a.fmt}_{s.sid}_{tp['src_t']:06.2f}.png")
    for r in list(B._READERS.values()):
        r.close()
    B._READERS.clear()
print("done")
