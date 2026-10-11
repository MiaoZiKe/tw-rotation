"""每鏡抽一格（0.8 倍鏡長處，全解析度）存檔，供「主圖入鏡檢查表」人工目視。
  python v3_shotstills.py --fmt web --out DIR [--only 04,05]
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_v3 as R
import v3_build as VB
import v3_core as K
import v3_check as C

ap = argparse.ArgumentParser()
ap.add_argument("--fmt", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--only", default="")
ap.add_argument("--frac", type=float, default=0.8)
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
    t = min(s.dur - 0.05, s.dur * a.frac)
    for k in range(0, int(t * 30) + 1, 6):
        s.render(k / 30, L)
    im = s.render(t, L)
    C.end(s.sid, t, L.W, L.H)
    im.save(out / f"{a.fmt}_{s.sid}.png")
    print(s.sid, "ok", flush=True)
