#!/usr/bin/env python3
"""v9 產生器：queue/<名>/script.json → html/<名>.html（沿用 v8/gen_v8.py 的全部邏輯，只是規格來自稿件、插圖來自插圖庫）。
用法：python3 v9/gen_v9.py <佇列資料夾> [--nv]   （--nv＝無旁白版，同 gen_v8）"""
import os, sys, json
B = os.path.dirname(os.path.abspath(__file__)); V8 = os.path.join(B, "..", "v8"); GEN = os.path.join(B, "_gen")
sys.path.insert(0, B); sys.path.insert(0, V8)
import specs_v8, gen_v8
from build_spec import build_spec, compose_ill
def load(folder):
    folder = os.path.abspath(folder); sc = json.load(open(os.path.join(folder, "script.json"), encoding="utf-8")); name = sc.get("id") or os.path.basename(folder)
    assert os.path.basename(folder) == sc.get("queue", name), "script.json 的 queue／id 要等於資料夾名（%s）" % os.path.basename(folder)
    return name, sc
def build(folder, nv=False):
    name, sc = load(folder); spec, subs = build_spec(sc, name); os.makedirs(GEN, exist_ok=True)
    open(os.path.join(GEN, "ill_%s.js" % spec["ill"]), "w", encoding="utf-8").write(compose_ill(subs))
    specs_v8.VIDEOS[name] = spec; gen_v8.B = GEN      # gen_v8 從 B 目錄讀 ill_<ill>.js
    return name, gen_v8.build(name, nv)
if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--nv"]; n, p = build(a[0], "--nv" in sys.argv); print(p)
