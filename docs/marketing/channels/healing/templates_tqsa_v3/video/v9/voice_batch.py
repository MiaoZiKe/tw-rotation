#!/usr/bin/env python3
"""同批多支一次 TTS（v9）：prepare 合併稿；split 用強制對齊把一份錄音切回各支。由 voice_batch.sh 呼叫。
  python3 v9/voice_batch.py prepare <批次資料夾> <資料夾1> <資料夾2> …   → 批次資料夾/narration.txt（行 id＝「序號:鏡id」，支與支之間空行）
  python3 v9/voice_batch.py split <批次資料夾> <資料夾1> …              → 各資料夾 narration_take.wav／narration_take.asr.json（各自接 cut_take_v8）
切法：先用 cut_take_v8.py 對整批做逐行對齊（ASR 逐字時間戳＋靜音動態規劃＋下一行開頭比對），取每支「第一行起點～最後一行終點」，
再把「設定句那一段（原錄音開頭到念稿起點）」接在每支前面，讓每支都長得像單支錄音（cut_take_v8 找『直接』與靜音的邏輯照舊可用）；ASR 字詞時間依切點平移，不必重跑。"""
import os, sys, re, json, wave, subprocess, difflib
import numpy as np
B = os.path.dirname(os.path.abspath(__file__)); VD = os.path.join(B, "..")
sys.path.insert(0, B)
S2T = dict(zip("这买内统计负担级过体户总资贷还价来为让们说话时间开关长发动经济务观点现实后场产业对车电会发联结约论题际环项报导记错须从样别两种应该钱让儿虽无节数据备选", "這買內統計負擔級過體戶總資貸還價來為讓們說話時間開關長發動經濟務觀點現實後場產業對車電會發聯結約論題際環項報導記錯須從樣別兩種應該錢讓兒雖無節數據備選"))
def norm(t): return "".join(S2T.get(c, c) for c in re.sub(r"[，。、；：？！「」（）\s\d%.零〇一二三四五六七八九十點百千萬]", "", t))
def scenes_of(folder):
    sc = json.load(open(os.path.join(folder, "script.json"), encoding="utf-8")); L = [(s["id"], s["say"]) for s in sc["scenes"] if s.get("say")]
    ou = sc.get("outro")
    if ou and ou.get("say", "想看完整資料，留言%s。" % ou["keyword"]): L.append((ou.get("id", "s9"), ou.get("say", "想看完整資料，留言%s。" % ou["keyword"])))   # 2026-11-22：片尾無旁白（say=""，規則 28）就不放空行，否則對齊信心被空行拉成 0
    return L
def prepare(batch, dirs):
    os.makedirs(batch, exist_ok=True); out = ["# 批次旁白稿（%d 支）；行 id＝序號:鏡 id" % len(dirs)]; n = 0
    for k, d in enumerate(dirs):
        for sid, t in scenes_of(d): out.append("%d:%s｜%s" % (k, sid, t)); n += len(re.sub(r"[，。、；：？！「」（）\s]", "", t))
        out.append("")
    open(os.path.join(batch, "narration.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("合併 %d 支、%d 字" % (len(dirs), n)); return n
def split(batch, dirs):
    take = os.path.join(batch, "batch_take.wav"); asr = os.path.join(batch, "batch_take.asr.json"); cut = os.path.join(batch, "batch_aligned.wav")
    env = dict(os.environ, PRE_LAST="0"); r = subprocess.run(["python3", os.path.join(VD, "tts", "cut_take_v8.py"), take, asr, batch, cut, "1.0", "0.45", "0.30", "0.70"], capture_output=True, text=True, env=env)
    print(r.stdout[-1500:]); print(r.stderr[-800:], file=sys.stderr)
    if r.returncode: sys.exit("批次對齊失敗（cut_take_v8）")
    cj = json.load(open(cut + ".cut.json")); segs = cj["segments"]; on0 = cj["narration_onset_in_raw"]
    conf = {s["id"]: round(difflib.SequenceMatcher(None, norm(s["text"]), norm(s["heard"])).ratio(), 3) for s in segs}
    mean = sum(conf.values()) / len(conf)
    # 只有「支與支之間」的分界會影響切回（支內各行的分界，每支會用自己的錄音與 ASR 在 cut_take_v8 重做）：看每支第一行與前一支最後一行
    edge = {}
    for k in range(len(dirs)):
        ids = [s["id"] for s in segs if s["id"].split(":")[0] == str(k)]; edge[ids[0]] = conf[ids[0]]; edge[ids[-1]] = conf[ids[-1]]
    weak = {k: v for k, v in edge.items() if v < .6}
    print("對齊信心：全批平均 %.3f、最低 %.3f（%s）；支與支分界旁的行（首／尾行）<0.6：%s（ASR 簡體且常漏字，支內單行偏低不影響切回）" % (mean, min(conf.values()), min(conf, key=conf.get), weak or "無"))
    json.dump({"mean": round(mean, 3), "per_line": conf, "boundary_lines": edge}, open(os.path.join(batch, "align_confidence.json"), "w"), indent=1)
    if mean < .7 or weak: sys.exit("對齊信心不足（全批平均 <0.7 或分界旁的行 <0.6），不切；請人工聽 %s 或用 BOUNDS 指定分界" % take)
    w = wave.open(take); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2"); w.close()
    words = json.load(open(asr)); req = {}
    if os.path.exists(take + ".request.json"): req = json.load(open(take + ".request.json"))
    for k, d in enumerate(dirs):
        mine = [s for s in segs if s["id"].split(":")[0] == str(k)]; assert mine, "批次裡找不到第 %d 支的行" % k
        a = mine[0]["src"][0]; b = mine[-1]["src"][1] + min(mine[-1]["gap_after"] + .09, .4)
        s0 = on0 if k == 0 else max(a - .15, on0); e0 = b
        y = np.concatenate([x[:int(on0 * SR)], x[int(s0 * SR):int(e0 * SR)]]) if k else x[:int(e0 * SR)]
        with wave.open(os.path.join(d, "narration_take.wav"), "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes(y.astype("<i2").tobytes())
        nw = [dict(v) for v in words if v["e"] <= on0 + .05]
        for v in words:
            if v["s"] >= s0 - .05 and v["e"] <= e0 + .1 and v["e"] > on0 + .05: nw.append(dict(v, s=round(v["s"] - s0 + on0, 2), e=round(v["e"] - s0 + on0, 2)))
        json.dump(nw, open(os.path.join(d, "narration_take.asr.json"), "w"), ensure_ascii=False)
        json.dump(dict(req, batch=os.path.relpath(batch, d), split_index=k, split_range_in_batch=[round(s0, 2), round(e0, 2)], align_confidence_mean=round(mean, 3), note="同批一次 TTS，v9/voice_batch.py 依行切回"), open(os.path.join(d, "narration_take.wav.request.json"), "w"), ensure_ascii=False, indent=1)
        print("第 %d 支 %s：原錄音 %.2f–%.2f 秒 → narration_take.wav（%.1f 秒）" % (k, os.path.basename(d), s0, e0, len(y) / SR))
if __name__ == "__main__":
    c, batch, dirs = sys.argv[1], sys.argv[2], [os.path.abspath(x) for x in sys.argv[3:]]
    prepare(batch, dirs) if c == "prepare" else split(batch, dirs)
