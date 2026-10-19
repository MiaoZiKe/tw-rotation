"""功能介紹影片 04 產業地圖：由錄影紀錄＋渲染紀錄產生 storyboard.md 與 overlap_report.md。

用法：python report_cal.py [--manual-d N] [--manual-m N]（人工抽格看過的張數，寫進報告）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_ind as R  # noqa: E402

PURPOSE = {
    "open": "需求：一台 AI 伺服器從上游到下游有哪些環節？台廠在哪一段？（AI 伺服器 2D 產品剖析圖，滑過編號卡）",
    "guide": "引導：首頁 → 左側選單「族群與個股」→「產業地圖」（手機：左上角選單 → 產業地圖）",
    "chain": "選產業鏈：上方分頁連點 半導體 → 一般電子 → AI 伺服器（剖析圖跟著換），再看產品剖析圖的編號卡（網頁滑過 3 張；手機點 2 個編號開零件說明）",
    "rel": "2D 供應鏈關聯圖：連點 3 個環節（上下游連線與右側對應族群跟著換；手機為展開該環節的公司卡與連線），網頁再滑過 3 家公司看連線去向（公司名一律模糊）",
    "3d": "3D 立體剖析圖：切 3D → 拖曳旋轉兩次 → 展開／收攏（網頁游標移出移入；手機點空白處）→ 連點 3 個零件（說明與同環節零件連動；手機為下方零件抽屜）→ 網頁零件卡的進料、出貨與對應環節",
    "end": "收尾：價值總結＋CTA「搜尋「哩股哩股」」＋片尾免責",
}


def freeze(mp4):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-vf", "freezedetect=n=0.003:d=0.5", "-map", "0:v", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [ln.split("]")[-1].strip() for ln in r.stderr.splitlines() if "freeze_" in ln]


def dur(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manual-d", type=int, default=0)
    ap.add_argument("--manual-m", type=int, default=0)
    g = ap.parse_args()
    sb = ["# 分鏡表：功能介紹影片 04 產業地圖（網頁 1920×1080／手機 1080×1920、30fps；成片整支 1.5 倍速，下表秒數為原片）", "",
          "- 比比主持、台詞用對話泡泡（一泡一句、≤14 字、原片每泡停留 ≥1.45 秒），不配人聲；底樂＋點擊音效（make_music_v3.py 自製合成）。",
          "- 網站畫面框只放「這一句在介紹的那一塊」：鏡頭＝錄影時每一格量到的元素外框，補成框的比例後裁切放大；區塊以外淡化、外圍藍框。",
          "- 一律未登入訪客的真實畫面；關聯圖公司卡、右側清單、剖析圖／3D 標籤的公司小籤、零件卡與手機零件抽屜的公司名稱、代號、股價、漲跌在錄影的瀏覽器裡模糊（法遵 9-1 第 1 條：不放大、不標色單一家）；畫面不放角標備註，片尾免責卡原片 4.8 秒（1.5 倍速後 3.2 秒）。",
          "- 本表由 `report_ind.py` 依錄影紀錄自動產生。", ""]
    rep = ["# 重疊與畫面檢查報告（render_ind.py 原片每一幀自動產生＋人工抽格）", ""]
    for dev, name in (("d", "網頁版"), ("m", "手機版")):
        j = json.loads((R.SCR / f"render_{dev}.json").read_text(encoding="utf-8"))
        mf = R.RAW / f"{dev}_meta.json"
        meta = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
        for sid in R.ORDER:
            f = R.RAW / f"{dev}_{sid}.json"
            if f.exists():
                meta[sid] = json.loads(f.read_text(encoding="utf-8"))
        mp4 = HERE / ("feat04_industry_map_web.mp4" if dev == "d" else "feat04_industry_map_mobile.mp4")
        fz = freeze(mp4)
        D = dur(mp4)
        sb += [f"## {name}（片長 {D:.1f} 秒）", ""]
        for sid, st, du in j["shots"]:
            m = meta[sid]
            sb += [f"### {R.SEC[sid][0]}｜{R.SEC[sid][1]}　{st:.1f}–{st + du:.1f} 秒", "", f"- 目的：{PURPOSE[sid]}"]
            cams = [f"{st + t:.1f}s {lab}" for (t, kind, lab) in m["marks"] if kind == "cam"]
            sb.append(f"- 畫面框（鏡頭）：{'、'.join(cams)}")
            sb.append("- 操作：" + "、".join(f"{st + c['t']:.1f}s {c.get('label') or c.get('text')}" for c in m["clicks"]))
            sb.append("- 泡泡（比比動作）：")
            for b in m["says"]:
                sb.append(f"  - {st + b['t']:.1f}s「{b['text']}」（{b['act']}）")
            sb.append("")
        sb += [f"### 片尾卡　{j['end_start']:.1f}–{j['total']:.1f} 秒", "",
               f"- 搜尋「哩股哩股」CTA＋三項功能＋免責「{R.DISC}」（停 {j['total'] - j['end_start']:.1f} 秒）；比比 face_bow／wave，泡泡「謝謝收看，我們下次見」。", ""]
        clicks = j["clicks"]
        real = [c for c in clicks if c[2] == "點擊" and not c[6]]
        errs = [c[4] for c in real if c[4] is not None]
        out = [c for c in clicks if not c[5]]
        rows = (R.SCR / f"overlap_rows_{dev}.md").read_text(encoding="utf-8")
        rep += [f"## {name}", "",
                f"- 片長 {D:.2f} 秒；程式逐幀檢查 {j['frames']} 幀；元素外框外擴 {R.PAD}px 兩兩比對：**重疊 {j['overlaps']} 筆**；其他問題（泡泡字出框、尾巴離比比、超過 14 字、泡泡停留不足 1.45 秒）**{j['issues']} 筆**。",
                "- 登記的元素：膠囊、標題、右上（上方）說明、功能導覽（網頁）、網站畫面框、泡泡（含尾巴）、比比（每一幀實際不透明外框）、片尾卡內各元素。",
                f"- 人工抽格：每 0.5 秒一張全解析度（scratchpad `feat04/samples_{dev}/`），看過 {g.manual_d if dev == 'd' else g.manual_m} 張。",
                f"- 點擊：{len(real)} 次點按鈕／元素，點擊特效中心＝錄影當下量到的元素中心，誤差最大 {max(errs) if errs else 0:.1f}px（影片像素）；"
                f"另有 {len([c for c in clicks if c[6]])} 次點 3D 空白處（展開／收攏，不以元素中心計誤差）、{len([c for c in clicks if c[2] != '點擊'])} 次拖曳起點；點擊落在畫面框外 {len(out)} 次。",
                f"- 停格：成片 ffmpeg freezedetect（n=0.003、d=0.5）{len([x for x in fz if 'freeze_start' in x])} 筆；畫面框內來源畫面連續不動最長 {j['still_max_s']} 秒（{j['still_at']} 秒附近）。",
                f"- 鏡頭裁到介紹區塊的幀數（區塊比畫面框大、只能裁一部分）：{', '.join(f'{a} {b}' for a, b in j['cut_frames'])}。", ""]
        if fz:
            rep += ["  - freezedetect：" + "；".join(fz[:10]), ""]
        if out:
            rep += ["  - 點擊在畫面框外：" + "；".join(f"{c[1]}s {c[3]}" for c in out), ""]
        rep += ["<details><summary>逐筆紀錄</summary>", "", "| 秒 | 元素 A | 元素 B | 相交面積 |", "|---|---|---|---|", rows, "", "</details>", ""]
        rep += ["| 秒 | 類型 | 對象 | 中心誤差 px | 在畫面框內 |", "|---|---|---|---|---|"]
        for c in clicks:
            rep.append(f"| {c[1]} | {'點空白處' if c[6] else c[2]} | {c[3]} | {'—' if c[4] is None or c[6] or c[2] != '點擊' else f'{c[4]:.1f}'} | {'是' if c[5] else '否'} |")
        rep.append("")
    (HERE / "storyboard.md").write_text("\n".join(sb), encoding="utf-8")
    (HERE / "overlap_report.md").write_text("\n".join(rep), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
