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
    import os
    if os.environ.get("VIDEO_V") == "6":
        if fmt == "web":
            import v6_web
            return v6_web.build()
        import v6_mobile
        return v6_mobile.build()
    if os.environ.get("VIDEO_V") == "4":
        if fmt == "web":
            import v4_web
            return v4_web.build()
        import v4_mobile
        return v4_mobile.build()
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
    C.LOG.clear(); C.EXC.clear(); K.CLICKS.clear(); K.FOCUSES.clear(); K.CROPS.clear(); K.MAINCHK.clear(); K.DWELLCHK.clear(); K.CONTENTCHK.clear(); K.ZOOMCHK.clear(); K.SITEOV.clear(); K.BUSYCHK.clear(); K.TAPNOPOSE.clear()
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
    chk = {"frames": frames, "LOG": C.LOG, "EXC": C.EXC, "CLICKS": K.CLICKS, "FOCUSES": K.FOCUSES, "CROPS": K.CROPS, "MAIN": K.MAINCHK, "DWELL": K.DWELLCHK, "CONTENT": K.CONTENTCHK, "ZOOM": K.ZOOMCHK, "SITEOV": K.SITEOV, "BUSY": K.BUSYCHK, "TAPNOPOSE": K.TAPNOPOSE}
    Path(str(path) + ".chk.json").write_text(json.dumps(chk, ensure_ascii=False))
    return sid


def write_reports(work, S, label):
    tot = {"frames": 0, "LOG": [], "EXC": [], "CLICKS": [], "FOCUSES": [], "CROPS": [], "MAIN": [], "DWELL": [], "CONTENT": [], "ZOOM": [], "SITEOV": [], "BUSY": [], "TAPNOPOSE": []}
    for s in S:
        f = Path(work) / f"seg_{s.sid}.mp4.chk.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        for k in tot:
            if k in d:
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
    L2 = [f"# 點擊檢查（{label}）", "", f"點擊 {len(cl)} 次，落點在目標元素 rect 內（離邊緣 ≥6px）{ok} 次", "", "| 鏡 | 秒 | 素材 | 目標標籤 | 漣漪中心（畫面座標） | 目標 rect（畫面座標） | 錄影端中心（src px） | 離邊緣 px | 通過 | 來源 |", "|---|---|---|---|---|---|---|---|---|---|"]
    L2 += [f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {c[8] if len(c) > 8 else ''} | {c[9] if len(c) > 9 else ''} | {'✓' if c[6] else '✗'} | {c[7]} |" for c in cl]
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
    mn = tot["MAIN"]
    mbad = [m for m in mn if (0 <= m[2] < 99.9) or (m[5] == 'web' and m[3] < 35)]
    L5 = [f"# 主圖入鏡檢查（{label}）", "", f"{len(mn)} 鏡；主圖 100% 入框：{sum(1 for m in mn if m[2] >= 99.9)} 鏡；主圖佔視窗 ≥60%：{sum(1 for m in mn if m[3] >= 60)} 鏡；未達 35%（視為不合格）：{len([m for m in mn if m[5] == 'web' and m[3] < 35])} 鏡", "",
          "| 鏡 | 主圖標籤 | 入鏡% | 主圖佔視窗% | 視窗 src px (x0,y0,x1,y1) |", "|---|---|---|---|---|"]
    L5 += [f"| {m[0]} | {m[1]} | {m[2]} | {m[3]} | {m[4]} |" for m in mn]
    (work / "main_check.md").write_text("\n".join(L5))
    dw = tot["DWELL"]
    dbad = [d for d in dw if (not d[4]) or (d[3] + 1e-6 < d[2] and "快節奏" not in d[6] and "播放" not in d[6])]
    L6 = [f"# 每鏡停留表（{label}）", "", "規則：最短＝2.0＋0.35×區塊數（≤7s）、字卡讀完（6.5 字／秒）；長頁必須滑到內容底部並停 ≥1.2 秒；點擊後內容區完整入窗停 ≥1.5 秒。", "",
          "| 鏡 | 內容量(區塊) | 規定最短秒 | 實際秒 | 看完（底部入窗停≥1.2s） | 備註 |", "|---|---|---|---|---|---|"]
    L6 += [f"| {d[0]} | {d[1]} | {d[2]} | {d[3]} | {'是' if d[4] else '否'} | {d[6]} |" for d in dw]
    (work / "dwell_check.md").write_text("\n".join(L6))
    ct = tot["CONTENT"]
    cbad = [c for c in ct if c[3] < 99.9]
    L7 = [f"# 點擊後內容入框檢查（{label}）", "", f"{len(ct)} 筆；點擊後 1.5 秒內內容區完整入窗：{sum(1 for c in ct if c[3] >= 99.9)} 筆", "",
          "| 鏡 | 點擊目標 | 內容區標籤 | 入框% | 停留秒 | 內容區來源 | 備註 |", "|---|---|---|---|---|---|---|"]
    L7 += [f"| {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {c[6]} |" for c in ct]
    (work / "content_check.md").write_text("\n".join(L7))
    zm = tot["ZOOM"]
    zbad = [z for z in zm if z[2] > 1.001]
    L8 = [f"# 畫質／推近倍率檢查（{label}）", "", f"{len(zm)} 筆；輸出像素／來源像素 >1（放大超過素材原解析度）：{len(zbad)} 筆。成片＝原生解析度、H.264 CRF 17、30fps（見 v3_sections --final）。", "", "| 鏡 | 素材 | 倍率 | 通過 |", "|---|---|---|---|"]
    L8 += [f"| {z[0]} | {z[1]} | {z[2]} | {'✓' if z[2] <= 1.001 else '✗'} |" for z in zm]
    (work / "zoom_check.md").write_text("\n".join(L8))
    so = tot["SITEOV"]
    L9 = [f"# site_overlay_check（{label}）", "", "規則（CEO 10-12，layout_rules 例外 5）：比比、泡泡、字卡、小字、道具可以疊在網站框上，但與該鏡的重點框（focus_targets）、點擊後內容框（content_rect）、點擊目標相交面積必須是 0；踩按鈕時只准腳碰到按鈕邊緣（重疊高度 ≤8px），按鈕文字要露出。",
          "", f"檢查幀數：{tot['frames']}　違規：{len(so)} 筆", ""]
    if so:
        L9 += ["| 鏡 | 秒 | 疊加元素 | 被壓到的重點 | 相交面積 px² |", "|---|---|---|---|---|"] + [f"| {a} | {b_} | {c} | {d} | {e} |" for a, b_, c, d, e in so[:400]]
    else:
        L9.append("全部通過，0 筆。")
    (work / "site_overlay_check.md").write_text("\n".join(L9))
    bz = tot["BUSY"]
    L10 = [f"# 忙碌圖檢查 busy_check（{label}）", "",
           "規則（CEO 10-12）：每一鏡每一幀，在網站框內用邊緣密度算出受保護像素（有字、有線、有圖），比比、泡泡、字卡、小字、道具與受保護像素的相交 ≤ 該元素面積 1%；受保護區 0 個直接判失敗；比比踩按鈕那一下只准碰被點的按鈕、按鈕露出 ≥80%。",
           "", f"檢查幀數：{tot['frames']}　違規：{len(bz)} 筆", ""]
    if bz:
        L10 += ["| 鏡 | 秒 | 元素 | 相交% | 說明 |", "|---|---|---|---|---|"] + [f"| {a} | {b_} | {c} | {d} | {e} |" for a, b_, c, d, e in bz[:600]]
        if len(bz) > 600:
            L10.append(f"…另有 {len(bz) - 600} 筆")
    else:
        L10.append("全部通過，0 筆。")
    tn = tot["TAPNOPOSE"]
    L10 += ["", f"## 找不到合格站位的點擊（比比留待機位、只有漣漪）：{len(tn)} 個", "（按鈕旁 160px 內沒有主角資料 0%、其他文字 ≤8% 的位置；依規則 2-1 請內容剪輯換時段或換點擊對象）", ""]
    L10 += [f"- {a} {b_} 秒「{c}」" for a, b_, c in tn]
    (work / "busy_check.md").write_text("\n".join(L10))
    bad = len(bz) + len(so) + len(zbad) + len(dbad) + len(cbad) + len(log) + (len(cl) - ok) + (len(fo) - fok) + (len(cr) - cok) + len(mbad)
    print(f"重疊 {len(log)} 筆（檢查 {tot['frames']} 幀）；busy_check {len(tot['BUSY'])} 筆；客服鈕檢查 {len(tot['SITEOV'])} 筆；點擊 {len(cl)} 次通過 {ok}；焦點框 {len(fo)} 個通過 {fok}；裁切 {len(cr)} 鏡通過 {cok}；例外 {len(tot['EXC'])} 幀；找不到站位的點擊 {len(tot['TAPNOPOSE'])} 個")
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
    ap.add_argument("--final", action="store_true", help="成片：bad_spans.json 必須存在、守門不可放行")
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
    import v3_guard as G
    gbad = G.guard(S, work, label, strict=a.final)
    if gbad:
        print(f"★ 來回切換／錯誤畫面檢查未通過（{gbad} 筆），不出片。報告：{work}/flow_check.md、bad_span_check.md")
        sys.exit(3)
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
    if bad:
        # CEO 10-12：任何檢查失敗都不准輸出 mp4（預覽也一樣），舊檔刪掉免得誤導
        if a.out and Path(a.out).exists():
            Path(a.out).unlink()
            print("已刪除舊檔：", a.out)
        print("★ 檢查未通過，不出片。報告：", work)
        sys.exit(2)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{work / ('seg_' + s.sid + '.mp4')}'\n" for s in S))
    if a.out:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
        if a.audio:
            cmd += ["-i", a.audio]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-profile:v", "high", "-movflags", "+faststart"]
        if a.audio:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest"]
        cmd += [a.out]
        subprocess.check_call(cmd)
        # 停格檢查改在成片上跑（CEO 10-12）：ffmpeg freezedetect n=0.003 d=0.5，開場、字卡、四宮格、片尾都算
        fz = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.out, "-vf", "freezedetect=n=0.003:d=0.5", "-map", "0:v:0", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        import re as _re
        starts = [float(x) for x in _re.findall(r"freeze_start: ([0-9.]+)", fz)]
        durs = [float(x) for x in _re.findall(r"freeze_duration: ([0-9.]+)", fz)]
        lines_ = [f"# 停格檢查（成片 freezedetect n=0.003 d=0.5）（{label}）", "", f"停格 {len(starts)} 筆", ""]
        lines_ += [f"- {s0:.2f} 秒起停 {d0:.2f} 秒" for s0, d0 in zip(starts, durs + [0] * (len(starts) - len(durs)))] or ["全部通過，0 筆。"]
        (work / "freeze_check.md").write_text("\n".join(lines_))
        if starts:
            Path(a.out).unlink()
            print(f"★ 成片停格 {len(starts)} 筆（{', '.join(f'{s0:.2f}s' for s0 in starts[:12])}），刪除成片、不交件。報告：{work}/freeze_check.md")
            sys.exit(4)
        print("輸出", a.out, "總長", round(total, 1), "；停格 0 筆")


if __name__ == "__main__":
    main()
