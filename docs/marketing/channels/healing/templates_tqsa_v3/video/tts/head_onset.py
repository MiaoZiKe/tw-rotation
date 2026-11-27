#!/usr/bin/env python3
"""找「念稿第一個字」在原始錄音裡的真正起音。
歷史：2026-11-27 avgwage／quit 審片殘留設定句尾巴「直接說」→ 改成「找『直接』後第一段 ≥0.15 秒安靜」；
2026-12-03～05 minwage／bonus 又踩到：「直接」與「說」之間剛好有 ≥0.15 秒安靜時，停在「說」前面，成品開頭多一個「說」（bonus 要人工重裁，首字 46.77 秒）。
穩健做法（2026-11-27 改）：
  主：念稿第一句前 4 個字（中文數字先轉阿拉伯數字再比，沿用 punct_align.canon_chars）在 ASR 字詞時間戳裡對位（≤1 字同音誤辨）→ 得到粗略位置 t_a；
      ASR 的字詞時間常比真正起音早 0.2～0.6 秒，所以在 t_a 附近找「≥0.15 秒安靜之後、接著持續有聲」的起點＝念稿首字起音；回傳的 "cut_at" 再往前退 0.05 秒。
  輔：ASR 有「直接說」就必須取「說」字結束之後（起音不得早於「說」結束 −0.1 秒，對位位置也要落在「說」結束附近）；兩者對不起來就報錯，不輸出。
回傳 {"sil_start","onset","cut_at","anchor"}（原始錄音秒數）；對不上、找不到起音一律丟 OnsetError（命令列版結束碼 1），不再默默退回舊法。
用法（單獨看）：python3 head_onset.py <原始 wav> <asr.json> <念稿 narration.txt 或第一句文字>"""
import json, os, re, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from punct_align import canon_chars

NCH = 4          # 比對念稿前幾個字
MAXMIS = 1       # 容許幾個字對不上（同音誤辨，例：領／靈、年終／年中）

class OnsetError(RuntimeError): pass

def first_line(src):
    """narration.txt 路徑（取 s1｜ 那行）或直接給文字。"""
    if os.path.exists(src):
        for ln in open(src, encoding="utf-8"):
            m = re.match(r"\s*s1\s*[｜|]\s*(.+)", ln)
            if m: return m.group(1).strip()
        raise OnsetError("narration.txt 找不到 s1｜ 那行：%s" % src)
    return src.split("｜", 1)[-1].strip()

def _find_anchor(text, asr, after):
    sk = [c for c, _ in canon_chars([(c, i) for i, c in enumerate(text) if not c.isspace()])][:NCH]
    if len(sk) < 4: raise OnsetError("念稿第一句太短，無法對位")
    ach = [(c, wi) for wi, a in enumerate(asr) for c in a["w"].strip()]
    ac = canon_chars(ach); ak = [c for c, _ in ac]; aw = [w for _, w in ac]
    n = len(sk)
    for i in range(len(ak) - n + 1):
        if asr[aw[i]]["s"] < after: continue
        mis = sum(1 for a, b in zip(sk, ak[i:i + n]) if a != b)
        if mis <= MAXMIS:
            return asr[aw[i]]["s"], mis, i
    raise OnsetError("ASR 找不到念稿開頭「%s」（容許 %d 字誤辨）" % ("".join(sk), MAXMIS))

def script_onset(x, SR, asr, text, thr_db=-38.0, min_sil=.15):
    hop = int(SR * .01); n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(1)) + 1e-9)
    quiet = db < thr_db
    # 輔助：最後一個「直接」＋其後的「說」
    ks = [i for i, a in enumerate(asr) if "直接" in a["w"]]
    shuo_e = None
    if ks:
        k = ks[-1]; j = k if asr[k]["w"].strip().endswith("說") else k + 1
        if j < len(asr) and asr[j]["w"].strip().startswith("說"): shuo_e = asr[j]["e"]
        else: raise OnsetError("ASR 有「直接」但其後沒有「說」，設定句結尾不明")
    t_a, mis, _ = _find_anchor(text, asr, (shuo_e - .6) if shuo_e is not None else 0.0)
    if shuo_e is not None and not (shuo_e - .6 <= t_a <= shuo_e + 2.0):
        raise OnsetError("念稿開頭對位在 %.2f 秒，離「直接說」結束 %.2f 秒太遠，兩者對不起來" % (t_a, shuo_e))
    lo = max(t_a - .1, (shuo_e - .1) if shuo_e is not None else 0.0)
    cand = None; i = int(lo * 100); end = min(n - 1, int((t_a + .9) * 100))
    while i < end:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if j - i >= int(min_sil * 100) and j + 20 <= n and (~quiet[j:j + 20]).mean() >= .7 and j / 100 >= lo:
                cand = (i / 100, j / 100); break
            i = j
        else: i += 1
    if cand is None: raise OnsetError("對位位置 %.2f 秒附近找不到「≥%.2f 秒安靜＋接著持續有聲」的念稿起音" % (t_a, min_sil))
    return {"sil_start": cand[0], "onset": cand[1], "cut_at": round(cand[1] - .05, 3), "anchor": round(t_a, 3), "mismatch": mis}

if __name__ == "__main__":
    w = wave.open(sys.argv[1]); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
    try: print(script_onset(x, SR, json.load(open(sys.argv[2])), first_line(sys.argv[3])))
    except OnsetError as e: print("錯誤：%s" % e, file=sys.stderr); sys.exit(1)
