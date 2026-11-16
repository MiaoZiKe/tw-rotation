#!/usr/bin/env python3
"""v9 稿件驅動：script.json → v8 規格（specs_v8.VIDEOS[名] 同格式），免手寫 specs。
用法：python3 v9/build_spec.py <佇列資料夾>        → 印出轉出的規格 JSON
      from build_spec import build_spec, compose_ill   （gen_v9.py 用）
script.json 格式見 v9/SCRIPT_FORMAT.md。"""
import os, re, sys, json, hashlib
B = os.path.dirname(os.path.abspath(__file__)); LIB = os.path.join(B, "illustrations")
SLOGAN = "談著這一代的難，也說著晴天裡的光"
# 版型 → 資料放在規格的哪個鍵（None＝資料欄位直接攤平到鏡上）
PAYLOAD = {"gantt": "gantt", "stack": "stack", "vbars": "vbars", "slope": "slope", "dumbbell": "dumbbell", "people": "people", "steps": "steps", "donut": "donut",
           "band": "band", "split2": "split2", "hbars": "hbars", "lollipop": "lollipop", "tiles": "tiles", "lanes": "lanes", "odometer": "odo"}
FLAT = {"hook", "versus", "ask", "next"}
LAYOUTS = sorted(set(PAYLOAD) | FLAT | {"outro"})
TOP = ("id", "layout", "say", "caption", "title", "tag", "source", "subject", "data", "opts")

def _load_index(): return json.load(open(os.path.join(LIB, "index.json"), encoding="utf-8"))
def _alias(sid, sub):
    ov = {k: sub[k] for k in ("labels", "keywords", "colors") if sub.get(k)}
    return sid if not ov else "%s__%s" % (sid, hashlib.sha1(json.dumps(ov, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:6])

def build_spec(sc, name=None):
    """sc＝script.json 內容；回傳 (規格 dict, 主體清單 {鍵: subject})。"""
    name = name or sc["id"]; scenes = []; subs = {}
    for s in sc["scenes"]:
        assert s["layout"] in LAYOUTS, "不認得的版型 %s（可用：%s）" % (s["layout"], "、".join(LAYOUTS))
        o = {"id": s["id"], "type": "outro" if s["layout"] == "outro" else s["layout"]}
        if s.get("subject"):
            k = _alias(s["subject"]["id"], s["subject"]); o["ill"] = k; subs[k] = s["subject"]
        for a, b in (("title", "title"), ("tag", "tag"), ("say", "say"), ("source", "src")):
            if a in s: o[b] = s[a]
        if s.get("caption"): o["capText"] = s["caption"]
        o.update(s.get("opts", {}))
        d = s.get("data", {})
        if s["layout"] in PAYLOAD: o[PAYLOAD[s["layout"]]] = d
        else: o.update(d)
        scenes.append(o)
    ou = sc.get("outro")
    if ou:   # 片尾：keyword＋next 就夠；其餘可覆寫
        scenes.append({"id": ou.get("id", "s9"), "type": "outro", "dur": ou.get("dur", 5.6), "say": ou.get("say", "想看完整資料，留言%s。" % ou["keyword"]), "keyword": ou["keyword"],
                       "slogan": ou.get("slogan", SLOGAN), "nextLine": ou.get("nextLine", "下一集 ▸ " + ou["next"]), "src": ou.get("src", "")})
    spec = {"queue": sc.get("queue", name), "ill": sc.get("ill_file", name), "out": "video.mp4", "cover": "cover.jpg", "report": "overlap_report_video.json",
            "cover_t": sc.get("cover_t", 1.9), "asof": sc["asof"], "scenes": scenes}
    if sc.get("narr_para"): spec["narr_para"] = True
    return spec, subs

def _sub(body, sub, entry):
    labs = entry["labels"]; rep = dict(sub.get("labels") or {})
    for i, kw in enumerate(sub.get("keywords") or []):
        if kw: assert i < len(labs), "主體 %s 只有 %d 個可換標籤，keywords 太多" % (sub["id"], len(labs)); rep[labs[i]] = kw
    for old, new in rep.items():
        assert old in labs, "主體 %s 沒有標籤「%s」（可換：%s）" % (sub["id"], old, "、".join(labs))
        assert not re.search(r"['<>`$\\]", new), "標籤「%s」不可含 ' < > ` $ \\" % new
        body = body.replace("'%s'" % old, "'%s'" % new).replace(">%s<" % old, ">%s<" % new)
    for old, new in (sub.get("colors") or {}).items():
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", new); body = re.sub(re.escape(old), new, body, flags=re.I)
    return body

def compose_ill(subs):
    """依 subjects 從 v9/illustrations/ 組出這支片的 ill 檔（const ILL={…}）。"""
    idx = _load_index(); parts = []
    for k, sub in subs.items():
        assert sub["id"] in idx, "插圖庫沒有主體「%s」（見 v9/ILLUSTRATIONS.md）" % sub["id"]
        body = open(os.path.join(LIB, sub["id"] + ".js"), encoding="utf-8").read().rstrip()
        body = _sub(body, sub, idx[sub["id"]])
        if k != sub["id"]: body = re.sub(r"^ ([A-Za-z0-9_]+):\{draw", " %s:{draw" % k, body, count=1)
        parts.append(body)
    return "const ILL={\n" + ",\n".join(parts) + "\n};\n"

if __name__ == "__main__":
    f = sys.argv[1]; f = os.path.join(f, "script.json") if os.path.isdir(f) else f
    sc = json.load(open(f, encoding="utf-8")); sp, _ = build_spec(sc, sc.get("id") or os.path.basename(os.path.dirname(os.path.abspath(f))))
    print(json.dumps(sp, ensure_ascii=False, indent=1))
