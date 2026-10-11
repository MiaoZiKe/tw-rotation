"""第 3 版正式合成命令列（含逐幀重疊／點擊／焦點框／裁切檢查，未通過不出片）。

  python v3_build.py --fmt web --theme cute --check            # 每 3 幀檢查一次，只寫報告不出片（快）
  python v3_build.py --fmt web --theme cute --out x.mp4 --audio y.wav [--only 04,05] [--jobs 4] [--allow]
  python v3_build.py --fmt web --theme cute --stills 12.0,20.5 --still-dir DIR
  python v3_build.py --fmt web --theme cute --cues cues.json
報告：<work>/overlap_report.md、click_check.md、focus_check.md、crop_check.md
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
import v3_check as C  # noqa: E402
import v3_core as K  # noqa: E402
from render_1010 import FPS  # noqa: E402


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


def run_seg(args):
    fmt, theme, sid, path, step, only_check = args
    C.LOG.clear(); C.EXC.clear(); K.CLICKS.clear(); K.FOCUSES.clear(); K.CROPS.clear()
    R.set_theme(theme)
    S = shots_for(fmt)
    L = K.Lay(fmt, theme)
    s = next(x for x in S if x.sid == sid)
    n = int(round(s.dur * FPS))
    p = None
    if not only_check:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.W}x{L.H}", "-r", str(FPS), "-i", "-",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", str(path)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = 0
    for k in range(n):
        t = k / FPS
        if only_check and k % step:
            continue
        im = s.render(t, L)
        C.end(sid, t, L.W, L.H)
        frames += 1
        if p:
            p.stdin.write(im.tobytes())
    if p:
        p.stdin.close()
        p.wait()
    for r in list(B._READERS.values()):
        r.close()
    B._READERS.clear()
    chk = {"frames": frames, "LOG": C.LOG, "EXC": C.EXC, "CLICKS": K.CLICKS, "FOCUSES": K.FOCUSES, "CROPS": K.CROPS}
    Path(str(path) + ".chk.json").write_text(json.dumps(chk, ensure_ascii=False))
    return sid


def write_reports(work, S, label):
    tot = {"frames": 0, "LOG": [], "EXC": [], "CLICKS": [], "FOCUSES": [], "CROPS": []}
    for s in S:
        f = Path(work) / f"seg_{s.sid}.mp4.chk.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for k in tot:
            tot[k] = tot[k] + d[k] if isinstance(tot[k], list) else tot[k] + d[k]
    work = Path(work)
    log = tot["LOG"]
    lines = [f"# 重疊檢查報告（{label}）", "", f"- 檢查幀數：{tot['frames']}　違規筆數：{len(log)}　例外（比比踩按鈕整段與網站畫面）：{len(tot['EXC'])} 幀", ""]
    if log:
        lines += ["| 鏡 | 秒 | 元素 A | 元素 B | 相交面積 px² |", "|---|---|---|---|---|"]
        lines += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in log[:400]]
        if len(log) > 400:
            lines.append(f"…另有 {len(log) - 400} 筆")
    else:
        lines.append("全部通過，0 筆。")
    if tot["EXC"]:
        sh = sorted({e[0] for e in tot["EXC"]})
        lines += ["", "## 例外清單（比比跳進框內踩按鈕，整段 ≤0.9 秒）", f"出現在鏡：{', '.join(sh)}；共 {len(tot['EXC'])} 幀"]
    (work / "overlap_report.md").write_text("\n".join(lines))
    cl = tot["CLICKS"]
    ok = sum(1 for c in cl if c[6])
    L2 = [f"# 點擊檢查（{label}）", "", f"點擊 {len(cl)} 次，落點在目標元素 rect 內 {ok} 次", "", "| 鏡 | 秒 | 素材 | 目標 | 漣漪中心 | 目標 rect（框內座標） | 通過 | 來源 |", "|---|---|---|---|---|---|---|---|"]
    L2 += [f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {'✓' if c[6] else '✗'} | {c[7]} |" for c in cl]
    (work / "click_check.md").write_text("\n".join(L2))
    fo = tot["FOCUSES"]
    fok = sum(1 for f in fo if f[5])
    L3 = [f"# 焦點框檢查（{label}）", "", f"焦點框 {len(fo)} 個，四邊誤差 ≤12px 且完整在畫面框內 {fok} 個", "", "| 鏡 | 秒 | 目標 | 四邊誤差(左上右下) | 完整在框內 | 通過 | rect 來源 |", "|---|---|---|---|---|---|---|"]
    L3 += [f"| {f[0]} | {f[1]} | {f[2]} | {f[3]} | {'是' if f[4] else '否'} | {'✓' if f[5] else '✗'} | {f[6]} |" for f in fo]
    (work / "focus_check.md").write_text("\n".join(L3))
    cr = tot["CROPS"]
    cok = sum(1 for c in cr if c[5])
    L4 = [f"# 裁切／置中檢查（{label}）", "", f"{len(cr)} 鏡，網站畫面完整且左右空白差 <20px：{cok} 鏡", "", "| 鏡 | 素材 | 左空白 | 右空白 | 內容完整 | 通過 |", "|---|---|---|---|---|---|"]
    L4 += [f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} | {'是' if c[4] else '否'} | {'✓' if c[5] else '✗'} |" for c in cr]
    (work / "crop_check.md").write_text("\n".join(L4))
    bad = len(log) + (len(cl) - ok) + (len(fo) - fok) + (len(cr) - cok)
    print(f"重疊 {len(log)} 筆（檢查 {tot['frames']} 幀）；點擊 {len(cl)} 次通過 {ok}；焦點框 {len(fo)} 個通過 {fok}；裁切 {len(cr)} 鏡通過 {cok}；例外 {len(tot['EXC'])} 幀")
    return bad, tot


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
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--allow", action="store_true")
    a = ap.parse_args()
    R.set_theme(a.theme)
    S = shots_for(a.fmt)
    L = K.Lay(a.fmt, a.theme)
    tl = timeline(S)
    total = sum(d for _, _, d in tl)
    label = f"{a.fmt}／{a.theme}"

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
                    C.LOG.clear()
                    for k in range(0, int((T - t0) * FPS) + 1, 4):
                        s.render(k / FPS, L)
                    im = s.render(T - t0, L)
                    C.end(sid, T - t0, L.W, L.H)
                    p = od / f"{a.fmt}_{a.theme}_{T:07.2f}_{sid}.png"
                    im.save(p)
                    print(p, "重疊:", [x for x in C.LOG if x[1] == round(T - t0, 3)])
                    break
        return

    work = Path(a.work or (B.SCR / "v10" / "work4" / f"{a.fmt}_{a.theme}"))
    work.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    jobs = [(a.fmt, a.theme, s.sid, work / f"seg_{s.sid}.mp4", a.step, a.check) for s in S if (only is None or s.sid in only)]
    jobs.sort(key=lambda j: -next(x.dur for x in S if x.sid == j[2]))
    with Pool(a.jobs) as pool:
        for sid in pool.imap_unordered(run_seg, jobs):
            print("完成鏡", sid, flush=True)
    bad, tot = write_reports(work, S, label)
    if a.check:
        print("總長", round(total, 1), "秒；報告在", work)
        return
    if bad and not a.allow:
        print("★ 檢查未通過，不出片。報告：", work)
        sys.exit(2)
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
        print("輸出", a.out, "總長", round(total, 1))


if __name__ == "__main__":
    main()
