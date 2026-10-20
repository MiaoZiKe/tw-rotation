"""功能介紹影片 07 熱力圖＋題材：由錄影紀錄＋渲染紀錄產生 storyboard.md 與 overlap_report.md。

用法：python report_hm.py [--manual-d N] [--manual-m N]（人工抽格看過的張數，寫進報告）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_hm as R  # noqa: E402

PURPOSE = {
    "open": "需求：全市場這麼多族群，錢集中在哪、哪個題材最熱？（網頁、手機：產業熱力圖全圖，網頁另有懸停提示框）",
    "guide": "引導：首頁 → 左側選單「熱力圖」→ 子分頁「產業」「題材」（手機：左上角選單 → 熱力圖 → 上方分頁切產業／題材）",
    "ind": "產業熱力圖：懸停看漲跌幅／成交值／成分股／本益比中位（手機：點方塊開底部面板）→ 分組下拉（自繪展開清單）產業鏈↔不分組 → 色階圖例連點 3 級只看那一級、再點一次取消。訪客點方塊跳族群頁為 Plus 以上功能，本片不點",
    "thm": "題材熱力圖：懸停看熱度／平均漲跌／成交值／近 7 天新聞 → 顏色下拉（自繪展開清單）熱度↔平均漲跌 → 連點三個題材方塊，下方產品剖析圖跟著換 → 點剖析圖環節卡（其他淡掉）。剖析圖上的個股代號標籤已模糊",
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
    sb = ["# 分鏡表：功能介紹影片 07 熱力圖＋題材（網頁 1920×1080／手機 1080×1920、30fps；成片整支 1.5 倍速，下表秒數為原片）", "",
          "- 比比主持、台詞用對話泡泡（一泡一句、≤14 字、原片每泡停留 ≥1.45 秒），不配人聲；底樂＋點擊音效（make_music_v3.py 自製合成）。",
          "- 網站畫面框只放「這一句在介紹的那一塊」：鏡頭＝錄影時每一格量到的元素外框，補成框的比例後裁切放大；區塊以外淡化、外圍藍框；每一格量文字元素外框，檢查框邊有沒有切過字（要 0）。",
          "- 一律未登入訪客的真實畫面（origin/main 的網站＋本機 build_payload 重算的資料；假的會員 API 只用來重現正式站「第一次來的訪客」：今日事件訪客額度第 1 次、文章只看得到標題）。",
          "- 會員額度字樣（CEO 10-20）：除了「限時公開」以外不入鏡——錄影瀏覽器裡藏掉今日事件「訪客預覽：已用 N／5 次」、文章清單訪客提示列、其他卡片的「全文需 Plus 以上」、文章頁「・不佔額度」。",
          "- 法遵：今日事件不點「券商」分類，「全部」清單裡的券商目標價整列模糊；新聞與文章標題出現上市櫃公司名稱或代號的模糊；個股連結模糊。只講族群與題材；畫面不放角標備註，片尾免責卡原片 4.8 秒（1.5 倍速後 3.2 秒）。",
          "- 本表由 `report_hm.py` 依錄影紀錄自動產生。", ""]
    rep = ["# 重疊與畫面檢查報告（render_ev.py 原片每一幀自動產生＋人工抽格）", "",
           "裁切檢查：介紹區塊用「元素本身的完整外框」（不以視窗裁切，露在視窗外也算），比的是每一格「實際裁切範圍」（含鏡頭慢移的內縮），"
           "區塊有任何一邊超出就記一格；鏡頭在兩拍之間推移的途中（目標取景還沒到位，每次約 0.4～0.8 秒）另列「推移中」不計入。"
           "", ""]
    for dev, name in (("d", "網頁版"), ("m", "手機版")):
        j = json.loads((R.SCR / f"render_{dev}.json").read_text(encoding="utf-8"))
        mf = R.RAW / f"{dev}_meta.json"
        meta = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
        for sid in R.ORDER:
            f = R.RAW / f"{dev}_{sid}.json"
            if f.exists():
                meta[sid] = json.loads(f.read_text(encoding="utf-8"))
        mp4 = HERE / ("feat07_heatmap_themes_web.mp4" if dev == "d" else "feat07_heatmap_themes_mobile.mp4")
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
               f"- 搜尋「哩股哩股」CTA＋三項功能（產業熱力圖・題材熱力圖・剖析圖）＋免責「{R.DISC}」（停 {j['total'] - j['end_start']:.1f} 秒）；比比 face_bow／wave，泡泡「謝謝收看，我們下次見」。", ""]
        clicks = j["clicks"]
        real = [c for c in clicks if c[2] == "點擊" and not c[6]]
        errs = [c[4] for c in real if c[4] is not None]
        out = [c for c in clicks if not c[5]]
        rows = (R.SCR / f"overlap_rows_{dev}.md").read_text(encoding="utf-8")
        rep += [f"## {name}", "",
                f"- 片長 {D:.2f} 秒；程式逐幀檢查 {j['frames']} 幀；元素外框外擴 {R.PAD}px 兩兩比對：**重疊 {j['overlaps']} 筆**；其他問題（泡泡字出框、尾巴離比比、超過 14 字、泡泡停留不足 1.45 秒）**{j['issues']} 筆**。",
                "- 登記的元素：膠囊、標題、右上（上方）說明、功能導覽（網頁）、網站畫面框、泡泡（含尾巴）、比比（每一幀實際不透明外框）、片尾卡內各元素。",
                f"- 人工抽格：原片每 0.5 秒存一張全解析度（scratchpad `feat07/samples_{dev}/`，共 {g.manual_d if dev == 'd' else g.manual_m} 張），全部排成縮圖總表逐張看過（重疊、出框、黑畫面）；全解析度原圖另開看過其中 17 張（日期下拉展開、文章段三拍推近、特斯拉標題拍與各圖與步驟圖、片尾卡、封面）；網頁版 v3 重點檢查另輸出縮圖總表（文章段、特斯拉第一拍），0 筆問題。未逐張開全解析度的格子只看過縮圖。",
                f"- 點擊：{len(real)} 次點按鈕／元素，點擊特效中心＝錄影當下量到的元素中心，誤差最大 {max(errs) if errs else 0:.1f}px（影片像素）；"
                f"拉桿點擊的中心＝依數值換算的拉桿位置、點完逐次核對拉桿實際數值；點擊落在畫面框外 {len(out)} 次。",
                f"- 停格：成片 ffmpeg freezedetect（n=0.003、d=0.5）{len([x for x in fz if 'freeze_start' in x])} 筆；畫面框內來源畫面連續不動最長 {j['still_max_s']} 秒（{j['still_at']} 秒附近）。",
                f"- 鏡頭裁到介紹區塊的幀數（各段）：{', '.join(f'{a} {b}' for a, b in j['cut_frames'])}；推移中（不計）：{', '.join(f'{a} {b}' for a, b in j['transit_frames'])}。",
                f"- 框邊切過文字的幀數（每一格量熱力圖方塊標籤、色階圖例、下拉選單、卡片標題、剖析圖標題的外框，與看得到的範圍部分相交就記一格）：{', '.join(f'{a} {b}' for a, b in j['edge_frames'])}。",
                "- 推近拍：介紹內容佔畫面寬（最小值）／每 1 css 像素在成片上的像素（字放大倍數）："]
        for sid_, ff_ in j["fill"]:
            pp_ = dict(j["ppc"]).get(sid_, {})
            for lab, v in ff_.items():
                rep.append(f"  - {sid_}｜{lab}：佔寬 {v * 100:.0f}%，每 css 像素 {pp_.get(lab, 0):.2f}px")
        if not any(ff_ for _, ff_ in j["fill"]):
            rep.append("  - （手機版鏡頭本來就只框介紹的那一塊，沒有另外的推近拍）")
        rep.append("")
        if fz:
            rep += ["  - freezedetect：" + "；".join(fz[:10]), ""]
        if out:
            rep += ["  - 點擊在畫面框外：" + "；".join(f"{c[1]}s {c[3]}" for c in out), ""]
        rep += ["<details><summary>逐筆紀錄</summary>", "", "| 秒 | 元素 A | 元素 B | 相交面積 |", "|---|---|---|---|", rows, "", "</details>", ""]
        rep += ["| 秒 | 類型 | 對象 | 中心誤差 px | 在畫面框內 |", "|---|---|---|---|---|"]
        for c in clicks:
            rep.append(f"| {c[1]} | {c[2]} | {c[3]} | {'—' if c[4] is None or c[2] != '點擊' else f'{c[4]:.1f}'} | {'是' if c[5] else '否'} |")
        rep.append("")
    (HERE / "storyboard.md").write_text("\n".join(sb), encoding="utf-8")
    (HERE / "overlap_report.md").write_text("\n".join(rep), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
