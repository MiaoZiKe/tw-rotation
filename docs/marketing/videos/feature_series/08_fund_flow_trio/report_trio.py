"""08 資金流向三合一：產生 storyboard_final.md、overlap_report.md。用法：python report_trio.py --manual-d N --manual-m N"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_trio  # noqa: E402
import report8  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--manual-d", type=int, default=0)
ap.add_argument("--manual-m", type=int, default=0)
g = ap.parse_args()
C = render_trio.CFG
cfg = dict(scr=C["scr"], here=str(HERE), no="08", title="資金流向三合一", sec_d=C["sec"], sec_m=C.get("sec_m", {}),
           note="訪客的時間列（拉桿、回放）在正式站是反灰的（要升級會員才能調），所以影片照原樣入鏡、不示範；用「換產業鏈」示範兩圖同步變。不勾族群（族群清單錄影端隱藏）。手機點長條會跳去別頁，所以手機不點長條、不按長條，只看圖與圖例。")
report8.make(cfg, g.manual_d, g.manual_m, extra={"d_manual_overlap": 0, "d_manual_occ": 0, "d_manual_blur": 0, "m_manual_overlap": 0, "m_manual_occ": 0, "m_manual_blur": 0, "d_motion": "只有 1 次：點選單進資金輪動時單向推近約 0.5 秒（頂欄已在框外）＋進分流樹後往下捲 1 次", "m_motion": "進各頁後各往下捲 1 次（單向）"})
