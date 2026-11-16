#!/usr/bin/env python3
"""插圖庫建置（v9）：把 v8/ill_*.js 拆成「一個主體一個檔」放進 v9/illustrations/<主體id>.js，並產生 index.json 與 ILLUSTRATIONS.md。
每個主體＝ILL 物件裡的一筆 `名稱:{draw(t,h,s){...},sfx(t0,s,E){...}}`（原始內文不改一個字）。
可替換的「槽」自動掃出：labels＝畫面上的中文字面值（'...' 或 <text>…</text>）、colors＝#RRGGBB 色碼；script.json 的 subject 用 labels／colors／keywords 換掉。
用法：python3 v9/build_ill_lib.py        （只在 v8 的 ill 檔有新增時重跑；已存在的主體不覆蓋，除非加 --force）"""
import os, re, json, glob, sys
B = os.path.dirname(os.path.abspath(__file__)); V8 = os.path.join(B, "..", "v8"); LIB = os.path.join(B, "illustrations")
CJK = r"[㐀-鿿]"
def split_entries(src):
    lines = src.split("\n"); ents = []; cur = None; cm = []
    for i, l in enumerate(lines):
        m = re.match(r"^ ([A-Za-z0-9_]+):\{draw", l)
        if m:
            cur = {"id": m.group(1), "comment": " ".join(c.strip()[2:].strip() for c in cm), "lines": [l]}; ents.append(cur); cm = []; continue
        if re.match(r"^ //", l) and not (cur and l.startswith("  ")): 
            cm.append(l); cur = None if cur else cur; continue
        if l.startswith("};") or l.startswith("const ILL"): cur = None; continue
        if cur is not None: cur["lines"].append(l)
    for e in ents:
        t = "\n".join(e["lines"]).rstrip()
        if t.endswith(","): t = t[:-1]
        e["body"] = t
    return ents
def slots(body):
    labs = []
    for m in re.finditer(r"'([^'\n]*%s[^'\n]*)'" % CJK, body):
        if m.group(1) not in labs: labs.append(m.group(1))
    for m in re.finditer(r"\bT\(\s*[^,()]+,\s*[^,()]+,\s*'([^'\n]+)'", body):
        if m.group(1) not in labs: labs.append(m.group(1))
    for m in re.finditer(r">([^<>`$\n]*%s[^<>`$\n]*)<" % CJK, body):
        if m.group(1) not in labs: labs.append(m.group(1))
    cols = []
    for m in re.finditer(r"#[0-9A-Fa-f]{6}\b", body):
        if m.group(0).upper() not in cols: cols.append(m.group(0).upper())
    return labs, cols
def main(force=False):
    os.makedirs(LIB, exist_ok=True); idx = {}
    ip = os.path.join(LIB, "index.json")
    if os.path.exists(ip): idx = json.load(open(ip, encoding="utf-8"))
    for f in sorted(glob.glob(os.path.join(V8, "ill_*.js"))):
        vid = os.path.basename(f)[4:-3]
        for e in split_entries(open(f, encoding="utf-8").read()):
            p = os.path.join(LIB, e["id"] + ".js")
            if e["id"] in idx and not force:
                if vid not in idx[e["id"]]["used_in"]: idx[e["id"]]["used_in"].append(vid)
                continue
            open(p, "w", encoding="utf-8").write(e["body"] + "\n")
            labs, cols = slots(e["body"])
            idx[e["id"]] = {"desc": e["comment"], "used_in": [vid], "labels": labs, "colors": cols, "has_sfx": "sfx(" in e["body"]}
    json.dump(idx, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = ["# 插圖主體庫（v9）", "", "自動產生（`python3 v9/build_ill_lib.py`）。每個主體是 `v9/illustrations/<id>.js` 一個檔；script.json 的 `subject.id` 指到這裡。",
          "換標籤與細節：`subject.labels`（原字→新字）、`subject.keywords`（依「可換標籤」順序逐一取代）、`subject.colors`（原色碼→新色碼）。",
          "守 healing-editor.md 第 20 條：主體必須貼近該篇文案，不准放無關的通用圖；沿用舊主體要用 labels／keywords 把畫面上的字換成本篇的詞，並在 素材登記.md 登記。", "",
          "| 主體 id | 動畫與用途（原作說明） | 可換標籤（依序＝keywords 順序） | 主色碼 | 原使用於 |", "|---|---|---|---|---|"]
    for k, v in sorted(idx.items()):
        md.append("| %s | %s | %s | %s | %s |" % (k, v["desc"].replace("|", "／")[:120], "、".join(v["labels"]) or "（無字）", " ".join(v["colors"][:6]), "、".join(v["used_in"])))
    md += ["", "共 %d 個主體。新增主體：在 `v9/illustrations/` 放 `<id>.js`（同樣是 `id:{draw(t,h,s){…},sfx(t0,s,E){…}}` 一筆），重跑上面指令更新索引。" % len(idx)]
    open(os.path.join(B, "ILLUSTRATIONS.md"), "w", encoding="utf-8").write("\n".join(md) + "\n"); print("主體", len(idx))
if __name__ == "__main__": main("--force" in sys.argv)
