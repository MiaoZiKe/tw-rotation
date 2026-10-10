"""第 3 版正式合成命令列。

  python v3_build.py --fmt web --theme cute --stills 12.0,20.5 --still-dir <dir>
  python v3_build.py --fmt web --theme cute --cues <json>
  python v3_build.py --fmt web --theme cute --out <mp4> --audio <wav> [--only 04,05] [--jobs 4] [--work <dir>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_1010 as B  # noqa: E402
import render_v3 as R  # noqa: E402
from v3_core import FPS, Lay  # noqa: E402

FMT = THEME = None


def shots_for(fmt):
    if fmt == "web":
        import v3_web
        return v3_web.build()
    import v3_mobile
    return v3_mobile.build()


def timeline(S):
    t, out = 0.0, []
    for s in S:
        out.append((s.sid, t, s.dur))
        t += s.dur
    return out


def render_seg(args):
    fmt, theme, sid, path = args
    R.set_theme(theme)
    S = shots_for(fmt)
    L = Lay(fmt)
    s = next(x for x in S if x.sid == sid)
    n = int(round(s.dur * FPS))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.W}x{L.H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        p.stdin.write(s.render(k / FPS, L).tobytes())
    p.stdin.close()
    p.wait()
    for r in list(B._READERS.values()):
        r.close()
    B._READERS.clear()
    return sid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmt", choices=["web", "mobile"], required=True)
    ap.add_argument("--theme", choices=["cute", "pro"], default="cute")
    ap.add_argument("--out", default="")
    ap.add_argument("--audio", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--work", default="")
    ap.add_argument("--stills", default="")
    ap.add_argument("--still-dir", default=".")
    ap.add_argument("--cues", default="")
    a = ap.parse_args()
    R.set_theme(a.theme)
    S = shots_for(a.fmt)
    L = Lay(a.fmt)
    tl = timeline(S)
    total = sum(d for _, _, d in tl)

    if a.cues:
        cues = []
        for s, (_, t0, _) in zip(S, tl):
            for ct, kind in s.auto_cues():
                cues.append([round(t0 + ct, 3), kind])
        Path(a.cues).write_text(json.dumps({"total": round(total, 3), "cues": sorted(cues), "shots": [[s, round(t, 3), d] for s, t, d in tl]}, ensure_ascii=False))
        print("cues", a.cues, "total", total, "n", len(cues))
        return

    if a.stills:
        od = Path(a.still_dir); od.mkdir(parents=True, exist_ok=True)
        for T in [float(x) for x in a.stills.split(",")]:
            for s, (sid, t0, d) in zip(S, tl):
                if t0 <= T < t0 + d:
                    im = s.render(T - t0, L)
                    p = od / f"{a.fmt}_{a.theme}_{T:07.2f}_{sid}.png"
                    im.save(p); print(p)
                    break
        return

    work = Path(a.work or (B.SCR / "v10" / "work3" / f"{a.fmt}_{a.theme}"))
    work.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    jobs = [(a.fmt, a.theme, s.sid, work / f"seg_{s.sid}.mp4") for s in S if (only is None or s.sid in only)]
    jobs.sort(key=lambda j: -next(x.dur for x in S if x.sid == j[2]))
    with Pool(a.jobs) as pool:
        for sid in pool.imap_unordered(render_seg, jobs):
            print("完成鏡", sid, flush=True)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{work / ('seg_' + s.sid + '.mp4')}'\n" for s in S))
    if a.out:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
        if a.audio:
            cmd += ["-i", a.audio]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high", "-movflags", "+faststart"]
        if a.audio:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest"]
        cmd += [a.out]
        subprocess.check_call(cmd)
        print("輸出", a.out)


if __name__ == "__main__":
    main()
