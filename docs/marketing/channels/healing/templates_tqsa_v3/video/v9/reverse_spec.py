#!/usr/bin/env python3
"""把 v8/specs_v8.py 既有的一支規格反向產成 script.json（驗證用／既有片搬家用）：python3 v9/reverse_spec.py <名> [輸出資料夾]
產完立刻用 build_spec 轉回去，與原規格逐鍵比對（== 才算一致）。"""
import os, sys, json
B = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, B); sys.path.insert(0, os.path.join(B, "..", "v8"))
from specs_v8 import VIDEOS
from build_spec import build_spec, PAYLOAD, SLOGAN
RES = {"id", "type", "ill", "title", "tag", "say", "src", "capText"}
def reverse(name):
    v = VIDEOS[name]; sc = {"id": name, "asof": v["asof"], "cover_t": v["cover_t"], "queue": v["queue"], "scenes": []}
    if v.get("narr_para"): sc["narr_para"] = True
    for s in v["scenes"]:
        if s["type"] == "outro":
            o = {"id": s["id"], "keyword": s["keyword"], "next": s["nextLine"].replace("下一集 ▸ ", "", 1), "dur": s["dur"]}
            if s["say"] != "想看完整資料，留言%s。" % s["keyword"]: o["say"] = s["say"]
            if s["slogan"] != SLOGAN: o["slogan"] = s["slogan"]
            if s["nextLine"] != "下一集 ▸ " + o["next"]: o["nextLine"] = s["nextLine"]
            if s.get("src"): o["src"] = s["src"]
            sc["outro"] = o; continue
        k = PAYLOAD.get(s["type"]); o = {"id": s["id"], "layout": s["type"], "say": s.get("say", "")}
        if "title" in s: o["title"] = s["title"]
        if "tag" in s: o["tag"] = s["tag"]
        if "src" in s: o["source"] = s["src"]
        if "capText" in s: o["caption"] = s["capText"]
        if s.get("ill"): o["subject"] = {"id": s["ill"]}
        if k: o["data"] = s[k]; rest = {a: b for a, b in s.items() if a not in RES and a != k}
        else:
            keys = {"hook": ("ulw", "big", "mini"), "versus": ("a", "b", "mid", "em", "emw"), "ask": ("recap", "opt"), "next": ("slip", "row")}[s["type"]]
            o["data"] = {a: s[a] for a in keys if a in s}; rest = {a: b for a, b in s.items() if a not in RES and a not in keys}
        if rest: o["opts"] = rest
        sc["scenes"].append(o)
    return sc
if __name__ == "__main__":
    n = sys.argv[1]; sc = reverse(n); spec, _ = build_spec(sc, n)
    orig = json.loads(json.dumps(VIDEOS[n])); got = json.loads(json.dumps(spec))
    diff = [k for k in set(orig) | set(got) if k != "ill" and orig.get(k) != got.get(k)]   # 影片層的 ill＝ill 檔名（v9 改為每篇組裝，不比）
    print(n, "規格一致" if not diff else "不一致：%s" % diff, "；鏡數", len(spec["scenes"]))
    if len(sys.argv) > 2:
        os.makedirs(sys.argv[2], exist_ok=True); json.dump(sc, open(os.path.join(sys.argv[2], "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(1 if diff else 0)
