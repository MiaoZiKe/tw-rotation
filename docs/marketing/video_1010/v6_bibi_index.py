"""把動畫師第 6 版比比表情（docs/anim/bibi_library/host_v6_timing.md；逐格 512 PNG 在 scratchpad/bibi_v6/frames）登記成 index_g.json，剪輯端 bibi_index() 就讀得到。
  python v6_bibi_index.py
"""
import json
import re
from pathlib import Path

import render_1010 as B

ROOT = Path(__file__).resolve().parents[3]
MD = ROOT / "docs/anim/bibi_library/host_v6_timing.md"
FR = B.SCR / "bibi_v6" / "frames"


def main():
    out, cur, name = {}, None, None
    for ln in MD.read_text().splitlines():
        m = re.match(r"## `([\w]+)`\s*(.*)", ln)
        if m:
            name = m.group(1)
            cur = out[name] = {"name": m.group(2).strip(), "size": [512, 512], "frames": [], "durations_ms": [], "labels": [],
                               "scene": {"scale": 0.75, "center_x": 248.0, "ground_y": 482.0}}
            continue
        m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]*)\|\s*(\d+)\s*\|", ln)
        if m and cur is not None:
            i = int(m.group(1))
            cur["frames"].append(str(FR / name / f"frame_{i:02d}.png"))
            cur["durations_ms"].append(int(m.group(3)))
            cur["labels"].append(m.group(2).strip())
    for k, v in list(out.items()):
        miss = [f for f in v["frames"] if not Path(f).exists()]
        if miss or not v["frames"]:
            print("缺格，略過", k, miss[:2])
            out.pop(k)
    (B.BIBI / "index_g.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print({k: (len(v["frames"]), sum(v["durations_ms"])) for k, v in out.items()})


if __name__ == "__main__":
    main()
