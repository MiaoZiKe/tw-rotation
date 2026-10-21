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
    "guide": "引導與需求：「AI 伺服器由哪些零件組成？」→ 首頁左側選單點「產業地圖」→ 上方產業鏈分頁選 AI 伺服器（手機：左上角選單 → 產業地圖 → 選 AI 伺服器）",
    "dg2d": "2D 產品剖析圖：連點編號卡 04 液冷 → 05 板上供電 → 03 電源櫃（手機點編號 05，再用面板的「‹」換到 04、03），每點一下鏡頭對到「編號卡＋圖上對應零件」，卡片展開時不蓋圖；手機視窗拉高，圖整張在底部說明面板上方，圖與面板同框、不重疊",
    "d3d": "3D 立體剖析圖（同一個零件）：切 3D → 在機櫃上方空白處拖曳旋轉 → 連點 11 後門風扇 → 13 BBU → 12 電源櫃，每點一個推到「零件標籤＋說明＋它連到的機櫃那一段」，標籤與機櫃分開在兩側、不蓋模型",
    "dg3d": "（手機）3D 立體剖析圖：切 3D → 拖曳旋轉 → 點編號 11，再用面板「›」「‹」換到 12、13、回 12 電源櫃；視窗 390×844，3D 在面板上方，面板另拍",
    "rel": "2D 供應鏈關聯圖：零件小卡「環節：電源」→ 關聯圖捲到電源 → 點上游散熱、下游系統組裝；每點一個先拍「滑到標題、說明框出現」再點下、游標移開，拍「被點環節＋上下游節點與連線」，說明框與清單卡不蓋住節點（手機取景固定中欄＋右欄）",
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
    ap.add_argument("--manual-note", default="")
    g = ap.parse_args()
    sb = ["# 分鏡表：功能介紹影片 04 產業地圖 v4（網頁 1920×1080／手機 1080×1920、30fps；成片整支 %.1f 倍速，下表秒數為原片）" % R.SPEED, "",
          "- 一條邏輯主線（Andy 10-21：不亂跳）：「AI 伺服器由哪些零件組成？」→ 選單進產業地圖 → 選 AI 伺服器鏈 → 剖析圖連點編號（結尾點 03 電源櫃）→ 切 3D 看同一個零件（結尾 12 電源櫃）→ 零件小卡「環節：電源」→ 2D 關聯圖看電源的上游（散熱）與下游（系統組裝）。鏡頭單向往下走，不在分頁間來回切、不用標題卡硬切，標題固定一個。",
          "- 比比主持、台詞用對話泡泡（一泡一句、≤14 字、原片每泡停留 ≥1.45 秒），不配人聲；底樂＋點擊音效（make_music_v3.py 自製合成）。",
          "- 不遮擋（Andy 10-21）：取消取景框外的淡化霧罩與藍框；網站提示框、說明卡、手機底部面板一律「調整取景／錄影視窗」讓卡片與介紹內容分開入鏡，或先拍圖再拍卡片分兩拍；游標點完馬上移到空白處；點擊漣漪縮小為 24px、點在字以外的空白處。",
          "- 一律未登入訪客的真實畫面；關聯圖公司卡、右側清單、剖析圖／3D 標籤的公司小籤、零件卡與手機零件抽屜的公司名稱、代號、股價、漲跌在錄影的瀏覽器裡模糊（法遵 9-1 第 1 條）；畫面不放角標備註；片尾卡原片 %.1f 秒。" % R.END_DUR,
          "- 本表由 `report_ind.py` 依錄影紀錄自動產生。", ""]
    rep = ["# 重疊／遮擋與畫面檢查報告 v4（capture_ind.py 錄影每一格＋render_ind.py 原片每一幀自動產生＋人工抽格）", "",
           "遮擋檢查（新）：錄影時每一格量「被介紹元素」（getBoundingClientRect）與所有浮層（網站提示框、零件小卡／清單卡、手機底部面板、3D 標籤、游標、點擊漣漪、客服鈕）的外框，相交面積 >0 記 1 筆；"
           "模糊塊壓到取景框內族群／環節名稱的另記。游標與漣漪只在「被點目標」上、點下前 1.0 秒到點下後 0.6 秒內可以重疊（漣漪 0.7 秒內為點擊回饋）。"
           "渲染端：霧罩／淡化層已取消（0），比比、泡泡、字卡與網站畫面框相交一律計入下方「重疊」。", ""]
    for dev, name in (("d", "網頁版"), ("m", "手機版")):
        jf = R.SCR / f"render_{dev}.json"
        if not jf.exists():
            continue
        j = json.loads(jf.read_text(encoding="utf-8"))
        meta = {}
        for sid in [s[0] for s in j["shots"]]:
            f = R.RAW / f"{dev}_{sid}.json"
            if f.exists():
                meta[sid] = json.loads(f.read_text(encoding="utf-8"))
        mp4 = Path(R.SCR / ("feat04_industry_map_web_v4_small.mp4" if dev == "d" else "feat04_industry_map_mobile_v4_small.mp4"))
        if not mp4.exists():
            mp4 = HERE / ("feat04_industry_map_web_v4.mp4" if dev == "d" else "feat04_industry_map_mobile_v4.mp4")
        fz = freeze(mp4)
        D = dur(mp4)
        sb += [f"## {name}（片長 {D:.1f} 秒）", ""]
        occ_frames = occ_rows = blur_rows = 0
        occ_detail = []
        for sid, st, du in j["shots"]:
            m = meta[sid]
            o = m.get("occ") or {}
            occ_frames += o.get("frames", 0)
            occ_rows += len(o.get("occ", []))
            blur_rows += len(o.get("blur", []))
            occ_detail += [(sid,) + tuple(r) for r in o.get("occ", [])][:20]
            sb += [f"### {R.SEC[sid][0]}｜{sid}　{st:.1f}–{st + du:.1f} 秒", "", f"- 目的：{PURPOSE.get(sid, '')}"]
            cams = [f"{st + t:.1f}s {lab}" for (t, kind, lab) in m["marks"] if kind == "cam"]
            sb.append(f"- 畫面框（鏡頭）：{'、'.join(cams)}")
            sb.append("- 操作：" + "、".join(f"{st + c['t']:.1f}s {c.get('label') or c.get('text')}" for c in m["clicks"]))
            sb.append("- 泡泡（比比動作）：")
            for b in m["says"]:
                sb.append(f"  - {st + b['t']:.1f}s「{b['text']}」（{b['act']}）")
            sb.append("")
        sb += [f"### 片尾卡　{j['end_start']:.1f}–{j['total']:.1f} 秒", "",
               f"- 搜尋「哩股哩股」CTA＋功能說明＋免責「{R.DISC}」；比比 face_bow／wave，泡泡「謝謝收看，我們下次見」。", ""]
        clicks = j["clicks"]
        real = [c for c in clicks if c[2] == "點擊" and not c[6]]
        inside = [c for c in clicks if c[5]]
        out = [c for c in clicks if not c[5]]
        rows = (R.SCR / f"overlap_rows_{dev}.md").read_text(encoding="utf-8")
        man = g.manual_d if dev == "d" else g.manual_m
        rep += [f"## {name}", "",
                f"- **遮擋檢查：程式 {occ_frames} 幀 {occ_rows} 筆；人工 {man} 格 {'0' if not g.manual_note else g.manual_note} 筆**（程式端＝錄影每一格的介紹元素×浮層；模糊塊壓文字 {blur_rows} 筆；渲染端霧罩 0）。",
                f"- 片長 {D:.2f} 秒（原片 {j['total']:.1f} 秒 ÷ {R.SPEED}）；程式逐幀檢查 {j['frames']} 幀；元素外框外擴 {R.PAD}px 兩兩比對：**重疊 {j['overlaps']} 筆**；其他問題（泡泡字出框、尾巴離比比、超過 14 字、泡泡停留不足 1.45 秒）**{j['issues']} 筆**。",
                f"- 重疊檢查：程式 {j['frames']} 幀 {j['overlaps']} 筆；人工抽 {man} 格 {'0' if not g.manual_note else g.manual_note} 筆。",
                f"- 人工抽格：每 0.5 秒一張全解析度（scratchpad `feat04/samples_v4_{dev}/`），逐張看「有沒有東西蓋住正在介紹的內容」，共 {man} 張。",
                f"- 點擊：{len(real)} 次點按鈕／元素（連動區：剖析圖 3 下、3D 3 下、關聯圖 3 下＋小卡 1 下），點擊落在被點元素內 {len(inside)} 次、畫面框外 {len(out)} 次（落點刻意取元素邊緣空白處，不壓字，所以不再以「元素中心誤差」計）。",
                f"- 停格：成片 ffmpeg freezedetect（n=0.003、d=0.5）{len([x for x in fz if 'freeze_start' in x])} 筆；畫面框內來源畫面連續不動最長 {j['still_max_s']} 秒（{j['still_at']} 秒附近）。",
                f"- 鏡頭裁到介紹區塊的幀數（各段）：{', '.join(f'{a} {b}' for a, b in j['cut_frames'])}；推移中（不計）：{', '.join(f'{a} {b}' for a, b in j['transit_frames'])}。",
                f"- 框邊切過環節卡的幀數：{', '.join(f'{a} {b}' for a, b in j['edge_frames'])}。",
                "- 推近拍：介紹內容佔畫面寬（最小值）／每 1 css 像素在成片上的像素："]
        for sid_, ff_ in j["fill"]:
            pp_ = dict(j["ppc"]).get(sid_, {})
            for lab, v in ff_.items():
                rep.append(f"  - {sid_}｜{lab}：佔寬 {v * 100:.0f}%，每 css 像素 {pp_.get(lab, 0):.2f}px")
        rep.append("")
        if occ_detail:
            rep += ["  - 遮擋檢查逐筆（前 20）：" + "；".join(str(x) for x in occ_detail), ""]
        if fz:
            rep += ["  - freezedetect：" + "；".join(fz[:10]), ""]
        rep += ["<details><summary>重疊逐筆紀錄</summary>", "", "| 秒 | 元素 A | 元素 B | 相交面積 |", "|---|---|---|---|", rows, "", "</details>", ""]
        rep += ["| 秒 | 類型 | 對象 | 落在被點元素內 | 在畫面框內 |", "|---|---|---|---|---|"]
        for c in clicks:
            rep.append(f"| {c[1]} | {'點空白處' if c[6] else c[2]} | {c[3]} | {'是' if (c[4] is not None and c[2] == '點擊') or c[2] != '點擊' else '—'} | {'是' if c[5] else '否'} |")
        rep.append("")
    (HERE / "storyboard.md").write_text("\n".join(sb), encoding="utf-8")
    (HERE / "overlap_report.md").write_text("\n".join(rep), encoding="utf-8")
    print("ok")


if __name__ == "__main__":
    main()
