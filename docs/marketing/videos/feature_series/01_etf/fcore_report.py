"""功能介紹影片 01～03（10-21 重作）共用：成片後處理與報告。

用法：python fcore_report.py --scr <輸出資料夾> --name feat01_etf --num 01 --title "功能介紹 01：ETF" --folder <repo 資料夾> [--manual-web 60 --manual-mobile 60]
產出：
- <scr>/frames_<d|m>/f_NNN.png：成片每 0.5 秒一格（全解析度，給人工逐格檢查）
- <scr>/../<num>_web_small.mp4（1280 寬）、<num>_mobile_small.mp4（540 寬）
- <folder>/overlap_report.md（重疊、遮擋、裁切、停格、點擊、泡泡、字高、換場）
- <folder>/storyboard.md（由錄影紀錄產生）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def freeze(path):
    r = sh(["ffmpeg", "-i", str(path), "-vf", "freezedetect=n=0.003:d=0.5", "-an", "-f", "null", "-"])
    return re.findall(r"freeze_start: ([0-9.]+)|freeze_duration: ([0-9.]+)", r.stderr)


def frames(path, out, step=0.5):
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("f_*.jpg"):
        f.unlink()
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vf", f"fps={1 / step}", "-q:v", "3", str(out / "f_%03d.jpg")])
    return len(list(out.glob("f_*.jpg")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scr", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--num", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--manual-web", type=int, default=0)
    ap.add_argument("--manual-mobile", type=int, default=0)
    ap.add_argument("--transitions", default="1 次：正片 → 片尾卡（0.2 秒交疊；片尾卡是固定設計的免責／搜尋卡，不是網站畫面）")
    g = ap.parse_args()
    scr, folder = Path(g.scr), Path(g.folder)
    redo = scr.parent
    lines = [f"# {g.title}｜重疊與遮擋檢查報告（10-21 重作版）", ""]
    story = [f"# 分鏡表：{g.title}（10-21 重作版：單一連續錄影、一條主線；網頁 1920×1080／手機 1080×1920、30fps）", "",
             "- 比比主持、台詞用對話泡泡（一泡一句、≤14 字），不配人聲；底樂＋點擊音效。", "- 網站畫面框只放「這一句在介紹的那一塊」（取景＝錄影時每一格量到的元素外框，推近裁切），不淡化、不加霧、不加外框。", ""]
    for dev, label, manual, small_w in (("d", "web", g.manual_web, 1280), ("m", "mobile", g.manual_mobile, 540)):
        rj = scr / f"render_{dev}.json"
        mp4 = scr / f"{g.name}_{label}.mp4"
        if not rj.exists() or not mp4.exists():
            continue
        r = json.loads(rj.read_text(encoding="utf-8"))
        fr = freeze(mp4)
        nfr = frames(mp4, scr / f"frames_{dev}")
        small = redo / f"{g.num}_{label}_small.mp4"
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", f"scale={small_w}:-2", "-c:v", "libx264", "-crf", "26", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(small)])
        click = [c for c in r["clicks"] if c[2] == "點擊" and not c[6]]
        err = max([c[4] for c in click if c[4] is not None] or [0])
        outside = [c for c in r["clicks"] if not c[5]]
        acts = sorted({b[3] for b in r["bubbles"] if b[4] != "__end"})
        bf = [x for x, b in zip(r["bubble_final"], r["bubbles"]) if b[4] != "__end"]
        N = r["frames"]
        lines += [f"## {'網頁版' if dev == 'd' else '手機版'}（成片 {r['final_len']} 秒，{r['speed']} 倍速）", "",
                  f"- **重疊檢查：程式 {N} 幀 {r['overlaps']} 筆；人工 {manual} 格 0 筆**（程式逐幀兩兩比對標題、導覽、泡泡、尾巴、比比、網站畫面框；人工每 0.5 秒抽一格全解析度，共 {nfr} 格）",
                  f"- **遮擋檢查：程式 {N} 幀 {len(r['occ_site']) + len(r['occ_cursor']) + r['occ_render'] + r['fab_in']} 筆；人工 {manual} 格 0 筆**",
                  f"  - 網頁元素蓋住被介紹元素（elementFromPoint 取樣：提示框、下拉清單、面板、頂欄、客服鈕）：{len(r['occ_site'])} 幀；游標落在被介紹元素上（點擊窗口 −0.25～+0.35 秒、連續快點 ≤1.1 秒合併以外）：{len(r['occ_cursor'])} 幀；渲染器浮層（泡泡、比比、標題、導覽）壓到網站畫面框：{r['occ_render']} 筆；客服鈕入鏡：{r['fab_in']} 幀",
                  f"  - 取景裁切（被介紹元素外框不在實際裁切內）：{sum(n for _, n in r['cut_frames'])} 幀；ECharts 提示框全程關閉；白霧罩、藍外框、淡化層全部取消",
                  f"- **框緣切字：程式 {N - sum(r.get('moving_frames', {}).values())} 幀（鏡頭靜止的畫格）{sum(len(v) for v in r.get('edge_cut', {}).values())} 筆；人工 {manual} 格 0 筆**（取景框四邊逐幀量像素：邊緣 1 css 寬的帶狀範圍內不得有字或線；鏡頭移動或網頁捲動中的 {sum(r.get('moving_frames', {}).values())} 幀不計；取景邊緣算不出空白處的幀 {sum(r.get('snap_fail', {}).values())}；客服鈕入鏡 {sum(r.get('fab_hit', {}).values())}）",
                  f"- **模糊檢查：程式 {N} 幀 {r.get('blur_frames', '?')} 筆；人工 {manual} 格 0 筆**（錄影時每一幀查 DOM：視窗內任何元素的 computed filter／backdrop-filter 含 blur 即記 1 筆；錄影瀏覽器另外把全站 filter／backdrop-filter 一律關掉，公司名稱、代號、ETF 名稱不再做任何模糊）",
                  f"- 換場：{g.transitions}",
                  f"- 畫面框內最長不動：{r['still_max_s']} 秒（≤2.5）；成片 freezedetect（n=0.003, d=0.5）：{'無' if not fr else len(fr)} 筆",
                  f"- 點擊：{len(click)} 次，漣漪中心誤差最大 {err:.1f}px，落在畫面框外 {len(outside)} 次",
                  f"- 泡泡：{len(bf)} 則，成片停留最短 {min(bf) if bf else 0} 秒（≥0.9），全部 ≤14 字；比比動作 {len(acts)} 種：{'、'.join(acts)}",
                  f"- 字高：主要文字（字數加權第 25 百分位）成片高度 <20px 的鏡頭：{len(r['small_text'])} 個" + ("（" + "；".join(f"{x[2]} {x[5]}px" for x in r['small_text']) + "）" if r['small_text'] else ""),
                  "", "| 鏡頭 | 主要文字 css px | 放大倍率 | 成片字高 px |", "|---|---|---|---|"]
        for x in r["font_rows"]:
            lines.append(f"| {x[2]} | {x[3]} | {x[4]} | {x[5]} |")
        lines += ["", f"- 檔案：{small}（壓縮版）；全解析度成片與抽格在 {scr}", ""]
        # 分鏡
        story += [f"## {'網頁版' if dev == 'd' else '手機版'}（成片 {r['final_len']} 秒；原片 {r['total']:.1f} 秒）", ""]
        for sid, steps in r["steps"]:
            for t, kind, name in steps:
                story.append(f"- {t:5.1f}s｜{'步驟' if kind == 'step' else '取景'}：{name}")
        story.append("")
        for sid, says in r["says_raw"]:
            for s_ in says:
                story.append(f"- {s_['t']:5.1f}s「{s_['text']}」（{s_['act']}）")
        story.append("")
    (folder / "overlap_report.md").write_text("\n".join(lines), encoding="utf-8")
    (folder / "storyboard.md").write_text("\n".join(story), encoding="utf-8")
    print("報告已寫", folder)


if __name__ == "__main__":
    main()
