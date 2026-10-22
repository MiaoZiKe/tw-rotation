"""功能介紹影片 06 今日事件＋精選文章 v3 —— 成片合成（共用 render3.py）。用法：python render_ev.py --dev d|m [--frames 3.0,9.5]"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render3  # noqa: E402

SCR = os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat06")
CFG = dict(
    name="feat06", scr=SCR, out_web="feat06_events_articles_web_v3.mp4", out_mobile="feat06_events_articles_mobile_v3.mp4",
    end_sub="今日事件・精選文章・分類篩選・關鍵字搜尋",
    sec={"s1": ("需求", "新聞太多，哪些跟市場有關？", "市場有關"), "s2": ("引導", "點鈴鐺，打開今日事件", "今日事件"),
         "s3": ("分類", "選分類，只看那一類", "那一類"), "s4": ("題材", "想深入看題材", "題材"),
         "s5": ("頁籤", "點頁籤，挑文章類別", "文章類別"), "s6": ("搜尋", "搜關鍵字，快速找到", "快速找到")},
    sec_m={"s2": ("引導", "點選單，打開今日事件", "今日事件")},
    focus_el={"evbell": "evbell", "navart": "navart", "evcats": "evcats", "evlist": "evlist", "artcats": "artcats", "artq": "artq", "artlist": "artlist",
              "burger": "burger", "m4ev": "m4ev", "m4art": "m4art"},
    cut=["evbell", "navart", "artcats", "artq", "burger", "m4ev", "m4art"],
    zoom={"d": dict(stage=5, dur=0.7, tgt=(72, 0, 928, 491.8))},
)
if __name__ == "__main__":
    render3.main(CFG)
