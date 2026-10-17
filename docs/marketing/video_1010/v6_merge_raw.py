"""第 6 版新素材（檔名含 _v6）錄完後：把 capture_log_*.json 的點擊／滑過、焦點框、壞畫面時段併進剪輯端讀的檔。
  python v6_merge_raw.py
寫入（raw_v3/）：click_targets.json、focus_targets.json、bad_spans.json（spans）、clicks.json（點下當時量到的元素中心）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v3_core as K  # noqa: E402

RAW = K.RAW3


def main():
    logs = {}
    for p in sorted(RAW.glob("capture_log_*.json"), key=lambda q: q.stat().st_mtime):
        try:
            d = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        for clip, v in d.items():
            if "_v6" in clip and isinstance(v, dict) and v.get("ok"):
                logs[clip] = v          # 較新的檔蓋過較舊的（同一支重錄）
    ct = json.loads((RAW / "click_targets.json").read_text())
    ft = json.loads((RAW / "focus_targets.json").read_text())
    bs = json.loads((RAW / "bad_spans.json").read_text())
    ck = json.loads((RAW / "clicks.json").read_text()) if (RAW / "clicks.json").exists() else {}
    for clip, v in logs.items():
        tg = v.get("targets") or []
        ct[clip] = {"targets": tg}
        ft[clip] = {"focus": v.get("focus") or []}
        bs.setdefault("spans", {})[clip + ".mp4"] = [[b[0], b[1], b[2]] for b in (v.get("bad") or [])]
        if clip + ".mp4" in bs.get("unchecked", []):
            bs["unchecked"].remove(clip + ".mp4")
        rows = []
        for e in tg:
            if e.get("kind") not in ("click", "hover") or not e.get("rect_center"):
                continue
            rows.append({"t": e["t"], "kind": e["kind"], "selector": e.get("expect") or e.get("selector"), "label": e.get("label"),
                         "x": e["rect_center"][0], "y": e["rect_center"][1], "rect": e.get("block_video_rect") or e.get("video_rect"),
                         "click_point": e.get("center"), "hit_expected": e.get("hit_expected"), "source": "錄影當下 getBoundingClientRect"})
        ck[clip] = rows
        print(clip, "點擊／滑過", len(rows), "焦點框", len(v.get("focus") or []), "壞畫面", v.get("bad"))
    (RAW / "click_targets.json").write_text(json.dumps(ct, ensure_ascii=False))
    (RAW / "focus_targets.json").write_text(json.dumps(ft, ensure_ascii=False))
    (RAW / "bad_spans.json").write_text(json.dumps(bs, ensure_ascii=False, indent=1))
    (RAW / "clicks.json").write_text(json.dumps(ck, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
