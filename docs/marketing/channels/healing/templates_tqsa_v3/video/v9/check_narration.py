#!/usr/bin/env python3
"""送 TTS 前的念稿檢查（healing-editor 第 17 條）：python3 v9/check_narration.py <資料夾>…（讀各資料夾 script.json 的每鏡 say；片尾也讀）
不過就 exit 1（voice_batch／make_video --voice 會因此不送）。每鏡全文逐句印出供人讀一遍，並寫 <資料夾>/tts_check.txt。
擋：①「欸」「嗯」「喔」「哦」「呃」等語助詞（句末的「喔／哦」也擋）②句子以英文字母開頭 ③「A I」「A.I.」拆開 ④阿拉伯數字或 % . 符號（數字要寫成中文念法，例 0.775% → 零點七七五、2027 → 二〇二七）⑤空稿。
警告（不擋）：全篇字數不在 180～260（對應 45～60 秒）、其他英文字母（確認念法）。"""
import os, re, sys, json
FILL = re.compile(r"[欸嗯呃唉]|[喔哦]。?$|^(那個|就是)")
def check(folder):
    sc = json.load(open(os.path.join(folder, "script.json"), encoding="utf-8")); lines = [(s["id"], s.get("say", "")) for s in sc["scenes"] if s.get("say")]
    ou = sc.get("outro")
    if ou: lines.append((ou.get("id", "s9"), ou.get("say", "想看完整資料，留言%s。" % ou["keyword"])))
    err, warn, out = [], [], []
    for sid, t in lines:
        out.append("%s｜%s" % (sid, t))
        if not t.strip(): err.append("%s 念稿是空的" % sid)
        for sen in [x for x in re.split(r"(?<=[。！？])", t) if x.strip()]:
            if FILL.search(sen): err.append("%s 有多餘語助詞：「%s」" % (sid, sen))
            if re.match(r"\s*[A-Za-z]", sen): err.append("%s 句子以英文字母開頭：「%s」" % (sid, sen))
        if re.search(r"\bA[\s.]+I\b", t): err.append("%s「AI」被拆開（要寫 AI）" % sid)
        if re.search(r"[0-9％%]|(?<=\w)\.(?=\w)", t): err.append("%s 有阿拉伯數字或 % . 符號，要寫成中文念法：「%s」" % (sid, t))
        lat = [w for w in re.findall(r"[A-Za-z]+", t) if w != "AI"]
        if lat: warn.append("%s 有英文字「%s」，確認念法" % (sid, "、".join(lat)))
    n = sum(len(re.sub(r"[，。、；：？！「」（）\s]", "", t)) for _, t in lines)
    if not 180 <= n <= 260: warn.append("全篇 %d 字（60 秒片建議 180～260 字）" % n)
    return lines, err, warn, out, n
if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        lines, err, warn, out, n = check(f); print("== %s（%d 鏡、%d 字）" % (os.path.basename(os.path.abspath(f)), len(lines), n)); print("\n".join(out))
        for w in warn: print("警告：", w)
        for e in err: print("不通過：", e)
        open(os.path.join(f, "tts_check.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n\n" + ("不通過：\n" + "\n".join(err) if err else "念稿檢查通過") + ("\n警告：\n" + "\n".join(warn) if warn else "") + "\n"); bad += bool(err)
    sys.exit(1 if bad else 0)
