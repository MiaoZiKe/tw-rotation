"""功能介紹影片 07 封面（共用 06_events_articles/make_cover3.py）。"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "06_events_articles"))
import make_cover3 as M  # noqa: E402

CFG = dict(pill="哩股哩股・功能介紹 07", words=("熱力", "題材"), sub="錢集中在哪？一張圖看懂",
           raw=os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat07") + "/raw",
           t=4.6, crop=(88, 22, 936, 540), bibi="spotlight", out=str(HERE))
if __name__ == "__main__":
    M.make("16x9", CFG)
    M.make("9x16", CFG)
