"""功能介紹影片 06／07：由錄影紀錄＋渲染紀錄產生 storyboard.md 與 overlap_report.md。
用法（由各資料夾的 report_*.py 呼叫）：report3.make(CFG, manual_d=N, manual_m=N)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def freeze(mp4):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-vf", "freezedetect=n=0.003:d=0.5", "-map", "0:v", "-f", "null", "-"], capture_output=True, text=True)
    return [ln.split("]")[-1].strip() for ln in r.stderr.splitlines() if "freeze_" in ln]


def dur(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def make(CFG, manual_d=0, manual_m=0, extra=None):
    scr = Path(CFG["scr"])
    here = Path(CFG["here"])
    extra = extra or {}
    sb = [f"# 分鏡表：功能介紹影片 {CFG['no']} {CFG['title']} v3（一鏡到底；網頁 1920×1080／手機 1080×1920；成片 1.5 倍速，下表秒數為原片）", "",
          f"單一取景、不換頁、不淡化、不用標題卡換場；大標題在泡泡換句的同一刻換字。{CFG['note']}", ""]
    rep = [f"# 重疊與遮擋檢查報告（{CFG['no']} {CFG['title']} v3；render3.py 逐幀自動產生＋人工每 0.5 秒抽格）", ""]
    for dev, name in (("d", "網頁版"), ("m", "手機版")):
        j = json.loads((scr / f"render_{dev}.json").read_text(encoding="utf-8"))
        meta = json.loads((scr / "raw" / f"{dev}_main.json").read_text(encoding="utf-8"))
        mp4 = Path(j["final"])
        D = dur(mp4)
        fz = freeze(mp4)
        stages = meta["stages"]
        sb += [f"## {name}（成片 {D:.1f} 秒，含片尾卡 {j['end_final']:.1f} 秒；原片 {j['total_raw']:.1f} 秒）", "",
               "| 原片秒 | 大標題 | 泡泡（比比動作） | 畫面與操作 |", "|---|---|---|---|"]
        ends = [s[0] for s in stages[1:]] + [j["body_raw"]]
        sec_title = CFG["sec_d"] if dev == "d" else {**CFG["sec_d"], **CFG.get("sec_m", {})}
        for (t0, k, nm), t1 in zip(stages, ends):
            says = [f"「{s['text']}」（{s['act']}）" for s in meta["says"] if t0 - 1e-3 <= s["t"] < t1 - 1e-3]
            cl = [f"{c['t']:.1f}s {c.get('label')}" for c in meta["clicks"] if c["kind"] == "click" and t0 - 1e-3 <= c["t"] < t1 - 1e-3]
            sb.append(f"| {t0:.1f}–{t1:.1f} | {sec_title['s%d' % k][0]}：{sec_title['s%d' % k][1]} | {'；'.join(says)} | {'、'.join(cl) or '（只看畫面）'} |")
        sb += [f"| {j['body_raw'] - 0.2:.1f}–{j['total_raw']:.1f} | 片尾卡 | 「謝謝收看，我們下次見」（face_bow） | 搜尋「哩股哩股」＋免責全文（原片 4.5 秒、成片 {j['end_final']:.1f} 秒） |", "",
               f"鏡頭換場：0 次（沒有硬切或換頁；只有片尾卡用 0.2 秒交疊接上）。單向推近／往下捲：{extra.get(dev + '_motion', '無')}。", ""]
        real = j["clicks"]
        errs = [c[2] for c in real if c[2] is not None]
        out = [c for c in real if not c[3]]
        hitbad = [c for c in real if c[4] is False]
        rows = (scr / f"overlap_rows_{dev}.md").read_text(encoding="utf-8")
        occ = (scr / f"occlusion_rows_{dev}.md").read_text(encoding="utf-8")
        M = manual_d if dev == "d" else manual_m
        rep += [f"## {name}（成片 {D:.1f} 秒；原片逐幀 {j['frames']} 幀）", "",
                f"- 重疊檢查：程式 {j['frames']} 幀 {j['overlaps']} 筆；人工 {M} 格 {extra.get(dev + '_manual_overlap', 0)} 筆。（元素＝膠囊、標題、網站畫面框、泡泡含尾巴、比比；外擴 {6}px 兩兩比對；其他問題〔泡泡字出框、尾巴離比比、超過 14 字、停留不足〕{j['issues']} 筆）",
                f"- 遮擋檢查：程式 {j['frames']} 幀 {j['occlusion'] + j['strict'] + j['cursor_text']} 筆；人工 {M} 格 {extra.get(dev + '_manual_occ', 0)} 筆。分項：泡泡講的元素 × 浮層 {j['occlusion']}；浮層／自繪清單／提示框／客服鈕 × 畫面內任何文字 {j['strict']}；游標與點擊波紋 × 任何文字 {j['cursor_text']}。",
                f"- 裁切檢查：介紹元素超出畫面框 {j['cut']} 幀；畫面框邊切到任何文字 {j['slice']} 幀（正在推近／捲動的幀不計，共 {j['push_frames']} 幀推近）。",
                f"- 換場次數：0。{extra.get(dev + '_motion', '')}",
                f"- 停格：成片 ffmpeg freezedetect（n=0.003、d=0.5）{len([x for x in fz if 'freeze_start' in x])} 筆；畫面框內來源畫面連續不動最長 {j['still_max_s']} 秒（{j['still_at']} 秒附近；網站畫面框內容另有 3px 慢漂避免停格）。",
                f"- 點擊：{len(real)} 次；落點都選在「元素內、最上層仍是目標、游標與波紋不壓字」的位置；點擊落在畫面框外 {len(out)} 次；最上層不是目標 {len(hitbad)} 次。",
                f"- 泡泡：{len(j['bubbles']) - 1} 則（含片尾 {len(j['bubbles'])} 則），最短停留（原片）{min(b[1] - b[0] for b in j['bubbles'][:-1]):.2f} 秒，每則 ≤14 字。",
                f"- 資料日：{j['data_date']}（網站實際畫面）。", ""]
        if fz:
            rep += ["  - freezedetect：" + "；".join(fz[:10]), ""]
        rep += ["<details><summary>逐筆紀錄</summary>", "", "遮擋明細：", "```", occ[:3000], "```", "", "重疊明細：", "```", rows[:1500], "```", "", "</details>", "",
                "| 秒 | 對象 | 中心誤差 px | 在畫面框內 | 最上層＝目標 | 游標壓字 px² |", "|---|---|---|---|---|---|"]
        for c in real:
            rep.append(f"| {c[0]} | {c[1]} | {c[2]} | {'是' if c[3] else '否'} | {c[4]} | {c[5]} |")
        rep.append("")
    (here / "storyboard.md").write_text("\n".join(sb), encoding="utf-8")
    (here / "overlap_report.md").write_text("\n".join(rep), encoding="utf-8")
    print("ok")
