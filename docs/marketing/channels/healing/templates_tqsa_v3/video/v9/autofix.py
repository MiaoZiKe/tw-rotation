#!/usr/bin/env python3
"""v9 自動修正迴圈：渲染 → 檢查 → 依錯誤類型改 script.json 的旗標 → 重渲染，最多 3 輪；仍不過就印出「要人看的項目」。
用法：python3 v9/autofix.py <佇列資料夾> [--voice] [--rounds 3] [--dry]（--dry＝只讀現有報告、印出會加什麼旗標，不渲染）
--voice：有旁白版（要先有 segments.json）；預設無旁白版。每輪渲染完刪 tmp/ 與暫存。
錯誤 → 旗標（每鏡 script.json scenes[].opts）：
  靜止段 >1.2 秒（check_v8）            → tagAll:true（狀態標籤跟著節拍跳）
  標籤×標題重疊（overlap：tag×title）    → tagAt +0.27（標籤晚點進，上限 0.9）
  字幕碰撞／字幕下緣超界（overlap／oob／edge 含 cap）→ capDy 8 → 0
  強調淨空不足（emphasis_fail）／光點亮帶閃爍 → once:true → 再不行 noglide:true
  字幕斷行不良（caption_bad：孤字、行首標點）→ capBal:true
其餘（同步、起音、響度、換鏡同框、插圖面板變動、片尾 LOGO）無自動旗標，直接列給人看。"""
import os, sys, re, json, shutil, subprocess, glob
B = os.path.dirname(os.path.abspath(__file__)); VD = os.path.join(B, ".."); sys.path.insert(0, B)
TAGAT_DEF = {"versus": .1, "next": .25}
def run(cmd, **k): return subprocess.run(cmd, cwd=VD, capture_output=True, text=True, **k)
def pipeline(folder, name, voice):
    cmd = ["python3", os.path.join(B, "gen_v9.py"), folder] + ([] if voice else ["--nv"]); r = run(cmd)
    if r.returncode: raise SystemExit("gen_v9 失敗：" + (r.stderr or r.stdout)[-600:])
    r = run(["node", "render_video.js", name]); print("\n".join(l for l in r.stdout.splitlines() if not l.startswith("留白"))[-400:])
    if r.returncode: raise SystemExit("render 失敗：" + r.stderr[-600:])
    ck = os.path.join(folder, "check_v8.json" if voice else "check_v8_nv.json"); r = run(["python3", "v8/check_v8.py", name, ck]); print(r.stdout[-300:])
    if r.returncode: raise SystemExit("check_v8 失敗：" + r.stderr[-600:])
    if voice:
        r = run(["python3", "v8/final_check.py", name, folder]); print(r.stdout[:400])
        if r.returncode: raise SystemExit("final_check 失敗：" + r.stderr[-600:])
    shutil.rmtree(os.path.join(VD, "tmp", name), ignore_errors=True)
    for d in glob.glob("/tmp/tmp*"):
        if os.path.isdir(d) and any(re.search(r"sfx|v0.wav|voice.wav", x) for x in os.listdir(d)): shutil.rmtree(d, ignore_errors=True)
def scene_at(rep, t):
    for s in rep.get("scenes", []):
        if s["t0"] - 1e-6 <= t < s["t1"]: return s["id"]
def collect(folder, voice):
    ck = json.load(open(os.path.join(folder, "check_v8.json" if voice else "check_v8_nv.json")))
    rep = json.load(open(os.path.join(folder, "overlap_report_video.json" if voice else "overlap_report_nv.json")))
    fc = json.load(open(os.path.join(folder, "final_check.json"))) if voice and os.path.exists(os.path.join(folder, "final_check.json")) else {}
    I = []   # (類型, 鏡 id 或 None, 說明)
    for t0, d in ck.get("static_runs_gt_1_2s", []): I.append(("static", scene_at(rep, t0 + .05), "靜止 %.2f 秒（%.2f 秒起）" % (d, t0)))
    for e in ck.get("emphasis_fail", []): I.append(("emphasis", e["id"], "強調淨空 %.1fpx <16" % e["min_px"]))
    for kind in ("overlap", "oob", "edge"):
        for x in rep.get(kind, []):
            m = re.match(r"([\d.]+)s (.*)", x)
            if not m: I.append(("other", None, "%s：%s" % (kind, x))); continue
            sid = scene_at(rep, float(m.group(1))); body = m.group(2); names = set(re.split(r"×| ", body))
            if {"tag", "title"} <= names: I.append(("tagtitle", sid, x))
            elif "cap" in names: I.append(("cap", sid, x))
            else: I.append(("other", sid, "%s：%s" % (kind, x)))
    for x in rep.get("coText", []): I.append(("other", None, "換鏡文字同框 " + str(x)))
    if rep.get("panelChangedScenes"): I.append(("other", None, "插圖面板變動：%s" % rep["panelChangedScenes"]))
    for c in fc.get("caption_bad", []): I.append(("capbad", c.get("id") if isinstance(c, dict) else None, "字幕斷行：%s" % c))
    if voice and fc:
        if fc.get("start_ok") is not True: I.append(("other", None, "起音檢查沒過"))
        if not fc.get("sync_ok"): I.append(("other", None, "字幕同步抽查沒過"))
        if fc.get("true_peak_dbtp_max", -9) > -1.0: I.append(("other", None, "true peak %s dBTP > -1" % fc.get("true_peak_dbtp_max")))
    seen = set(); out = []
    for i in I:
        if i not in seen: seen.add(i); out.append(i)
    return out
def fix(sc, issues):
    """改 script 內存內容；回傳 (已套用 [說明], 沒辦法 [說明])。"""
    sm = {s["id"]: s for s in sc["scenes"]}; done, left = [], []
    hit = set()
    for kind, sid, d in issues:
        if (kind, sid) in hit: continue      # 同一鏡同一類一輪只加一次
        hit.add((kind, sid)); s = sm.get(sid)
        if kind == "other" or s is None: left.append("%s %s" % (sid or "", d)); continue
        o = s.setdefault("opts", {})
        if kind == "static":
            if not o.get("tagAll"): o["tagAll"] = True; done.append("%s tagAll（%s）" % (sid, d))
            else: left.append("%s %s（tagAll 已開，仍靜止）" % (sid, d))
        elif kind == "tagtitle":
            cur = o.get("tagAt", TAGAT_DEF.get(s["layout"], .15))
            if cur < .89: o["tagAt"] = round(min(.9, cur + .27), 2); done.append("%s tagAt %.2f→%.2f（%s）" % (sid, cur, o["tagAt"], d))
            else: left.append("%s %s（tagAt 已到上限）" % (sid, d))
        elif kind == "cap":
            cur = o.get("capDy", 18)
            if cur > 0: o["capDy"] = 8 if cur > 8 else 0; done.append("%s capDy %s→%s（%s）" % (sid, cur, o["capDy"], d))
            else: left.append("%s %s（capDy 已 0）" % (sid, d))
        elif kind == "emphasis":
            if not o.get("once"): o["once"] = True; done.append("%s once（%s）" % (sid, d))
            elif not o.get("noglide"): o["noglide"] = True; done.append("%s noglide（%s）" % (sid, d))
            else: left.append("%s %s（once／noglide 都已開）" % (sid, d))
        elif kind == "capbad":
            if not o.get("capBal"): o["capBal"] = True; done.append("%s capBal（%s）" % (sid, d))
            else: left.append("%s %s（capBal 已開）" % (sid, d))
    return done, left
def main():
    a = sys.argv[1:]; voice = "--voice" in a; dry = "--dry" in a; R = int(a[a.index("--rounds") + 1]) if "--rounds" in a else 3
    folder = os.path.abspath([x for x in a if not x.startswith("--") and not x.isdigit()][0]); name = os.path.basename(folder); sp = os.path.join(folder, "script.json"); log = []
    for rnd in range(R + 1):
        if not dry: pipeline(folder, name, voice)
        issues = collect(folder, voice)
        if not issues: print("第 %d 輪：檢查全過" % rnd); log.append({"round": rnd, "issues": []}); break
        sc = json.load(open(sp, encoding="utf-8")); done, left = fix(sc, issues); log.append({"round": rnd, "issues": [list(i) for i in issues], "fixed": done, "manual": left})
        print("第 %d 輪：%d 項問題；自動加旗標：%s" % (rnd, len(issues), done or "（無）"))
        if dry or not done or rnd == R:
            print("要人看的項目：" if left else "（沒有要人看的項目）"); [print("  -", x) for x in left]
            if rnd == R and done: print("  - 已達 %d 輪上限，最後一輪的旗標已寫入 script.json 但尚未重渲染；請再跑一次確認" % R)
            break
        json.dump(sc, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(log, open(os.path.join(folder, "autofix_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(0 if log and not log[-1]["issues"] else 2)
if __name__ == "__main__": main()
