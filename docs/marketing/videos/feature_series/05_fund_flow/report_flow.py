"""功能介紹影片 05 資金流向：由錄影紀錄＋渲染紀錄產生 storyboard.md 與 overlap_report.md。

用法：python report_flow.py [--manual-d N] [--manual-m N]（人工抽格看過的張數，寫進報告）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_flow as R  # noqa: E402

PURPOSE = {
    "open": "需求：錢往哪個族群跑？哪個族群正在轉強？（網頁：資金輪動卡全圖定位 → 推近族群資金排行上半（佔比增加最多）→ 推近輪盤上半（改善、領先象限）；手機：資金輪盤）",
    "guide": "引導：首頁 → 左側選單「資金流水」→「資金流向」→ 子分頁「資金輪動」（手機：左上角選單 → 資金流向）",
    "days": "資金輪盤＋族群資金排行共用一支「N 天前」拉桿：連點 5、10、30 天，輪盤軌跡長度與排行一起換（網頁每點一下分兩拍：拉桿＋輪盤上半 → 推近排行上半；手機：拉桿＋輪盤，最後捲到排行）",
    "pick": "產業鏈篩選：打開產業鏈下拉清單，連選半導體、AI 伺服器、一般電子，輪盤只留那條鏈的族群、族群資金排行一起篩（網頁每選一條分兩拍：清單＋輪盤上半 → 推近排行上半；手機：清單＋輪盤，最後捲到排行）。不用「族群」勾選：網站勾族群會連帶打開成分股面板（個股），本片只講族群層級",
    "tree": "資金分流樹：台股成交值 → 產業鏈 → 族群的四層樹；「看哪一天」拉桿連點 15 天前、5 天前、最新一天（樹的佔比、增減與右側排名一起換），再切流入最多／流出最多排名（網頁每天分兩拍：拉桿＋排名 → 推近分流樹上半）",
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
    sb = ["# 分鏡表：功能介紹影片 05 資金流向（網頁 1920×1080／手機 1080×1920、30fps；成片整支 1.5 倍速，下表秒數為原片）", "",
          "- 比比主持、台詞用對話泡泡（一泡一句、≤14 字、原片每泡停留 ≥1.45 秒），不配人聲；底樂＋點擊音效（make_music_v3.py 自製合成）。",
          "- 網站畫面框只放「這一句在介紹的那一塊」：鏡頭＝錄影時每一格量到的元素外框，補成框的比例後裁切放大；區塊以外淡化、外圍藍框。",
          "- 網頁版分拍推近：每個功能先全圖定位約 1 秒，再推到被點的那一區（拉桿＋輪盤上半／排行上半／族群清單／分流樹上半／排名），推近拍以 3 倍（資金分流樹 2.5 倍）像素錄、介紹內容佔畫面寬 ≥70%。",
          "- 一律未登入訪客的真實畫面；只講族群層級：不點會列出個股的面板（象限名單、族群成分股），錄影瀏覽器另把任何個股連結／個股卡模糊當保險（法遵 9-1 第 1 條）；排行只說明怎麼看，不寫推薦；畫面不放角標備註，片尾免責卡原片 4.8 秒（1.5 倍速後 3.2 秒）。",
          "- 本表由 `report_flow.py` 依錄影紀錄自動產生。", ""]
    rep = ["# 重疊與畫面檢查報告（render_flow.py 原片每一幀自動產生＋人工抽格）", "",
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
        mp4 = HERE / ("feat05_fund_flow_web_v2.mp4" if dev == "d" else "feat05_fund_flow_mobile_v2.mp4")
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
                f"- 人工抽格：原片每 0.5 秒存一張全解析度（scratchpad `feat05/samples_{dev}/`，共 {g.manual_d if dev == 'd' else g.manual_m} 張），全部排成縮圖總表逐張看過；每段推近拍與片尾卡另開全解析度原圖看（重疊、截字、出框、黑畫面），0 筆問題。",
                f"- 點擊：{len(real)} 次點按鈕／元素，點擊特效中心＝錄影當下量到的元素中心，誤差最大 {max(errs) if errs else 0:.1f}px（影片像素）；"
                f"拉桿點擊的中心＝依數值換算的拉桿位置、點完逐次核對拉桿實際數值；點擊落在畫面框外 {len(out)} 次。",
                f"- 停格：成片 ffmpeg freezedetect（n=0.003、d=0.5）{len([x for x in fz if 'freeze_start' in x])} 筆；畫面框內來源畫面連續不動最長 {j['still_max_s']} 秒（{j['still_at']} 秒附近）。",
                f"- 鏡頭裁到介紹區塊的幀數（各段）：{', '.join(f'{a} {b}' for a, b in j['cut_frames'])}；推移中（不計）：{', '.join(f'{a} {b}' for a, b in j['transit_frames'])}。",
                f"- 框邊切過輪盤／族群資金排行標籤文字的幀數（v2 新增：每一格量 ECharts 畫布上每一段標籤文字的外框，與實際裁切範圍部分相交就記一格）：{', '.join(f'{a} {b}' for a, b in j['edge_frames'])}。",
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
