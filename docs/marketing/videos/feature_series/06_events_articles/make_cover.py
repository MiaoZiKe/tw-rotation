"""功能介紹影片 06 封面（共用 make_cover3.py）。"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_cover3 as M  # noqa: E402

CFG = dict(pill="哩股哩股・功能介紹 06", words=("事件", "文章"), sub="新聞太多？分類、搜尋一次找到",
           raw=os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat06") + "/raw",
           t=21.5, crop=(72, 0, 928, 491.8), bibi="news", out=str(HERE))
if __name__ == "__main__":
    M.make("16x9", CFG)
    M.make("9x16", CFG)
