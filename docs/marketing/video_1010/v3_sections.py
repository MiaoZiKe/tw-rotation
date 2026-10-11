"""分頁段落輸出：每段獨立 mp4（含該段配樂切片）＋四項檢查報告。
  python v3_sections.py --fmt web --music wav --sections 01,02 [--jobs 4]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_1010 as B  # noqa: E402
import render_v3 as R  # noqa: E402
import v3_build as VB  # noqa: E402
import v3_core as K  # noqa: E402

SECTIONS = {
    "web": [
        ("01", "開場與比比自我介紹", ["01a", "01b", "01c", "02", "03"]),
        ("02", "總覽_今日事件_搜尋", ["04", "05", "06", "07"]),
        ("03", "財經日曆", ["03a", "03b", "03c", "03d", "03e", "03f"]),
        ("04", "資金流向", ["09", "09b", "10", "10b", "11"]),
        ("05", "熱力圖", ["12", "13a", "13b", "13c", "13d", "13e", "13f", "14"]),
        ("06", "產業地圖_2D到3D到四宮格", ["15", "16", "17", "18", "19", "20", "21"]),
        ("07", "個股", ["22a", "22b", "22c", "22d", "23a", "23b", "23c", "23d", "23e", "24a", "24a3", "24b1", "24b2", "24c1", "24c2"]),
        ("08", "市場明細_選股策略_週期統計", ["25", "26", "27"]),
        ("09", "ETF", ["28", "29", "30", "31a", "31b", "31c", "31d", "32"]),
        ("10", "自選_導覽_許願_片尾_警語", ["33", "34", "35", "36", "37", "38"]),
    ],
    "mobile": [
        ("01", "開場與比比自我介紹", ["01a", "01b", "01c", "02", "03"]),
        ("02", "總覽_今日事件_搜尋", ["04a", "04b", "04c", "04d", "04e", "05", "06", "07"]),
        ("03", "財經日曆", ["03a", "03b", "03c", "03d", "03e", "03f", "03g"]),
        ("04", "資金流向", ["09", "09b", "10", "10b", "11"]),
        ("05", "熱力圖", ["12", "13a", "13b", "13c", "13d", "13e", "13f"]),
        ("06", "產業地圖_2D到3D到四宮格", ["14", "15", "16", "17", "18"]),
        ("07", "個股", ["19a", "19b", "19c", "19d", "19e", "19e2", "19e3", "19e4", "19e5", "19f", "19g1", "19g2", "19h1", "19h2"]),
        ("08", "市場明細_選股策略_週期統計", ["22", "23", "24"]),
        ("09", "ETF", ["25", "26", "27", "28a", "28b", "28c", "28d", "29"]),
        ("10", "自選_導覽_許願_片尾_警語", ["30", "31", "32", "33", "34", "35"]),
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmt", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--sections", default="")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--reuse", action="store_true")
    a = ap.parse_args()
    theme = "cute"
    R.set_theme(theme)
    S = VB.shots_for(a.fmt)
    tl = {sid: (t, d) for sid, t, d in VB.timeline(S)}
    work = B.SCR / "v10" / "work4" / f"{a.fmt}_{theme}"
    work.mkdir(parents=True, exist_ok=True)
    out = B.SCR / "v10" / "sections" / a.fmt
    out.mkdir(parents=True, exist_ok=True)
    want = set(a.sections.split(",")) if a.sections else None
    for no, name, ids in SECTIONS[a.fmt]:
        if want and no not in want:
            continue
        miss = [i for i in ids if i not in tl]
        if miss:
            print("段", no, "鏡不存在", miss)
            continue
        jobs = [(a.fmt, theme, sid, work / f"seg_{sid}.mp4", 1, False) for sid in ids]
        if a.reuse:
            jobs = [j for j in jobs if not (j[3].exists() and Path(str(j[3]) + ".chk.json").exists())]
        else:
            for j in jobs:
                for f in (j[3], Path(str(j[3]) + ".chk.json")):
                    if f.exists():
                        f.unlink()
        if jobs:
            with Pool(a.jobs) as pool:
                list(pool.imap_unordered(VB.run_seg, jobs))
        sub = [s for s in S if s.sid in ids]
        stage = out / f"{no}_{name}_checks"
        stage.mkdir(exist_ok=True)
        bad, tot = VB.write_reports(work, sub, f"{a.fmt}／{theme}／{name}")
        for f in ("overlap_report.md", "click_check.md", "focus_check.md", "crop_check.md", "main_check.md", "dwell_check.md", "content_check.md"):
            shutil.copy(work / f, stage / f)
        t0 = tl[ids[0]][0]
        dur = sum(tl[i][1] for i in ids)
        lst = work / f"list_{no}.txt"
        lst.write_text("".join(f"file '{work / ('seg_' + i + '.mp4')}'\n" for i in ids))
        mp4 = out / f"{no}_{name}.mp4"
        w = 1280 if a.fmt == "web" else 720
        vf = f"scale={w}:-2:flags=lanczos"
        af = f"afade=t=in:st=0:d=0.05,afade=t=out:st={dur - 0.5:.2f}:d=0.5"
        subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", a.music,
                               "-vf", vf, "-af", af, "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                               "-shortest", "-movflags", "+faststart", str(mp4)])
        cl = tot["CLICKS"]; fo = tot["FOCUSES"]; cr = tot["CROPS"]
        res = (f"重疊 {len(tot['LOG'])} 筆（{tot['frames']} 幀逐幀）；例外 {len(tot['EXC'])} 幀；點擊 {len(cl)} 次落點正確 {sum(1 for c in cl if c[6])}；"
               f"焦點框 {len(fo)} 個誤差≤12px {sum(1 for f in fo if f[5])}；裁切 {len(cr)} 鏡通過 {sum(1 for c in cr if c[5])}")
        size = mp4.stat().st_size / 1e6
        from datetime import datetime, timedelta, timezone
        ts = datetime.now(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
        line = f"- {a.fmt} {no} {name}｜{ts}（台北）｜{dur:.1f}s {size:.1f}MB｜{res}｜{'通過' if not bad else '未通過'}｜{mp4}"
        print(line, flush=True)
        with open(B.SCR / "v10" / "sections" / "READY.md", "a") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    main()
