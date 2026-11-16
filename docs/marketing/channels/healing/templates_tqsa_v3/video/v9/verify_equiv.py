#!/usr/bin/env python3
"""驗證 script.json 轉出的結果與 v8 原版一致：python3 v9/verify_equiv.py <名> [<名>…]
1. 規格逐鍵一致（reverse_spec）；2. gen_v8 與 gen_v9 的 html 內 V（規格＋時間軸）逐字一致；3. 插圖檔每個主體本文一致；
4. 三個時間點各截一張（原版／v9），差異像素數＝0，並拼成 <暫存>/equiv_<名>.png 供人看。"""
import os, sys, re, json, subprocess, shutil, tempfile
import numpy as np
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__)); VD = os.path.join(B, ".."); sys.path.insert(0, B); sys.path.insert(0, os.path.join(B, "..", "v8"))
import gen_v9, gen_v8, specs_v8, build_ill_lib as L
from reverse_spec import reverse
from build_spec import build_spec
T = tempfile.mkdtemp(prefix="equiv_")
def Vjson(h): return json.loads(re.search(r"const V=(.*?);</script>", open(h, encoding="utf-8").read(), re.S).group(1))
def ill_of(h):
    p = re.findall(r'<script src="file://([^"]+ill_[^"]+)"', open(h, encoding="utf-8").read())[0]; return p
ok_all = True
for n in sys.argv[1:]:
    orig = specs_v8.VIDEOS[n]; spec, _ = build_spec(reverse(n), n); sd = [k for k in set(orig) | set(spec) if k != "ill" and json.loads(json.dumps(orig.get(k))) != json.loads(json.dumps(spec.get(k)))]
    gen_v8.B = os.path.join(B, '..', 'v8'); h8 = gen_v8.build(n, True); i8 = ill_of(h8); a = os.path.join(T, n + "_v8.html"); shutil.copy(h8, a); shutil.copy(i8, a + ".ill.js")
    sc = os.path.join(B, "..", "..", "..", "queue", n); os.makedirs(sc, exist_ok=True)
    if not os.path.exists(os.path.join(sc, "script.json")): json.dump(reverse(n), open(os.path.join(sc, "script.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    _, h9 = gen_v9.build(sc, True); i9 = ill_of(h9); b = os.path.join(T, n + "_v9.html"); shutil.copy(h9, b); shutil.copy(i9, b + ".ill.js")
    v8, v9 = Vjson(a), Vjson(b); v8.pop("ill"); v9.pop("ill")
    e8 = {e["id"]: e["body"] for e in L.split_entries(open(i8, encoding="utf-8").read())}; e9 = {e["id"]: e["body"] for e in L.split_entries(open(i9, encoding="utf-8").read())}
    # 兩邊 html 的 script src 指到各自的 ill 檔（內容已複製），截圖時把路徑換成暫存副本
    for f in (a, b):
        s = open(f, encoding="utf-8").read(); s = re.sub(r'(<script src="file://)[^"]+ill_[^"]+"', lambda m: m.group(1) + f + '.ill.js"', s); open(f, "w", encoding="utf-8").write(s)
    d = v8["dur"]; ts = ",".join("%.2f" % x for x in (d * .12, d * .45, d * .8))
    for f, tag in ((a, "a"), (b, "b")): subprocess.run(["node", os.path.join(B, "shot3.js"), f, os.path.join(T, n + "_" + tag), ts], check=True)
    bad = []; tiles = []
    for i in range(3):
        A = Image.open(os.path.join(T, "%s_a_%d.png" % (n, i))).convert("RGB"); C = Image.open(os.path.join(T, "%s_b_%d.png" % (n, i))).convert("RGB")
        bad.append(int((np.abs(np.asarray(A, np.int16) - np.asarray(C, np.int16)).max(2) > 8).sum())); tiles += [A.resize((270, 480)), C.resize((270, 480))]
    sheet = Image.new("RGB", (270 * 6, 480)); [sheet.paste(t, (270 * i, 0)) for i, t in enumerate(tiles)]; sheet.save(os.path.join(T, "equiv_%s.png" % n))
    ok = not sd and v8 == v9 and all(e8.get(k)==v for k,v in e9.items()) and set(x['ill'] for x in orig['scenes'] if x.get('ill'))==set(e9) and not any(bad); ok_all &= ok
    print(n, "OK" if ok else "不一致", "｜規格差鍵", sd, "｜V一致", v8 == v9, "｜用到的主體本文一致", all(e8.get(k)==v for k,v in e9.items()), "｜三格差異像素", bad, "｜拼圖", os.path.join(T, "equiv_%s.png" % n))
sys.exit(0 if ok_all else 1)
