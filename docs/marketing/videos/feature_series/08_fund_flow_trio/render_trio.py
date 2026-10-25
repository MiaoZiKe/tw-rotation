"""功能介紹影片 08 資金流向三合一 —— 成片合成（共用 render8.py；1.0 倍速、片尾卡 4 秒）。
用法：python render_trio.py --dev d|m [--frames 3.0,9.5]"""
import os
import sys
from pathlib import Path

os.environ.setdefault("FEAT_SPEED", "1.0")
os.environ.setdefault("FEAT_END_FINAL", "4.0")
os.environ.setdefault("FEAT_MIN_BUB", "1.4")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render8  # noqa: E402

SCR = os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat08")
SEC = {
    "s1": ("需求", "錢往哪個族群跑？", "哪個族群"),
    "s2": ("需求", "三頁接著看，答案就出來", "答案"),
    "s3": ("導覽", "先看資金輪動", "資金輪動"),
    "s4": ("資金輪動", "輪盤看強弱，排行看流入", "流入"),
    "s5": ("資金輪動", "滑過長條，兩圖連動", "兩圖連動"),
    "s6": ("資金輪動", "換條產業鏈，兩圖同步變", "同步變"),
    "s7": ("資金輪動", "只看半導體，記下晶圓代工", "晶圓代工"),
    "s8": ("導覽", "接著看，錢怎麼分下去", "分下去"),
    "s9": ("資金分流樹", "一條主幹，分到各產業", "主幹"),
    "s10": ("資金分流樹", "點半導體，看它分給誰", "分給誰"),
    "s11": ("資金分流樹", "晶圓代工，占這條鏈最大", "最大"),
    "s12": ("導覽", "最後看法人動向", "法人動向"),
    "s13": ("族群×法人", "三種法人，三種顏色", "三種顏色"),
    "s14": ("族群×法人", "同樣只看半導體", "半導體"),
    "s15": ("族群×法人", "滑過長條，看三種法人", "三種法人"),
    "s16": ("族群×法人", "點圖例，單獨看某一方", "單獨"),
    "s17": ("收尾", "輪動、分流、法人，串成一線", "串成一線"),
}
CFG = dict(
    name="feat08", scr=SCR, out_web="feat08_fund_flow_trio_web.mp4", out_mobile="feat08_fund_flow_trio_mobile.mp4",
    end_sub="資金輪動・資金分流樹・族群×法人",
    sec=SEC, sec_m={},
    focus_el={"navflow": "navflow", "subsankey": "subsankey", "subinst": "subinst", "clock": "clock", "rank": "rank", "chainr": "chainr", "sk": "sk",
              "sklist": "sklist", "inst": "inst", "instleg": "instleg", "instchain": "instchain", "hov": "hov", "burger": "burger", "m4flow": "m4flow",
              "tabsk": "tabsk", "tabinst": "tabinst", "tabrot": "tabrot", "skchain": "skchain"},
    cut=["navflow", "subsankey", "subinst", "chainr", "instleg", "instchain", "burger", "m4flow", "tabsk", "tabinst", "tabrot"],
    occ_skip=["clock", "rank", "inst", "sk", "sklist"],
    zoom={"d": dict(stage=3, at_click=0, dur=0.5, tgt=(0, 75, 1100, 627), auto_pan=(60, 100), from_t=6.0)},
)
if __name__ == "__main__":
    render8.main(CFG)
