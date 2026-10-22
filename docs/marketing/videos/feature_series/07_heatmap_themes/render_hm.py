"""功能介紹影片 07 熱力圖＋題材 v3 —— 成片合成（共用 06_events_articles/render3.py）。用法：python render_hm.py --dev d|m [--frames 3.0,9.5]"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "06_events_articles"))
import render3  # noqa: E402

SCR = os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat07")
CFG = dict(
    name="feat07", scr=SCR, out_web="feat07_heatmap_themes_web_v3.mp4", out_mobile="feat07_heatmap_themes_mobile_v3.mp4",
    end_sub="產業熱力圖・題材熱度・剖析圖",
    sec={"s1": ("需求", "錢集中在哪個族群？", "哪個族群"), "s2": ("引導", "點熱力圖，看產業分布", "熱力圖"),
         "s3": ("看圖", "大小看成交，顏色看漲跌", "漲跌"), "s4": ("篩選", "分組、色階，一鍵篩選", "一鍵篩選"),
         "s5": ("題材", "想看題材？點題材", "題材"), "s6": ("剖析", "點方塊，再點環節看細節", "看細節")},
    sec_m={"s2": ("引導", "點選單，進熱力圖", "熱力圖"), "s5": ("題材", "想看題材？切到題材", "題材")},
    focus_el={**{k: k for k in ("navheat", "navthm", "themecard", "dg", "burger", "m4heat", "mtabs")}, "indcard": ["indcard", "indtree"]},
    cut=["navheat", "navthm", "indcard", "burger", "m4heat", "mtabs"],
    occ_skip=["indcard", "themecard"],
    bub_cap=11.0,
    zoom={"d": dict(stage=6, dur=0.7, tgt=(72, 44, 978, 518.4))},
)
if __name__ == "__main__":
    render3.main(CFG)
