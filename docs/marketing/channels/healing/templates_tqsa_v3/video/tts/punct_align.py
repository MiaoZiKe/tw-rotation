#!/usr/bin/env python3
"""念稿標點 ↔ ASR 字詞對位（2026-11-21，healing-editor 規則 29）。
cut_take_v8.py（補停頓）與 v9/pace_check.py（句內斷點檢查）共用。
做法：念稿與 ASR 字串都先把中文數字換成阿拉伯數字（「二〇三一」→2031、「百分之十一」→11%、「三萬六千三百一十二」→36312、「三十三點四」→33.4），
簡轉繁、去標點，再用 difflib 逐字對；只有「標點前後兩個字都對得上、且該處是 ASR 詞與詞的交界」才算對位成功，對不上就不回傳（呼叫端不插停頓）。"""
import re, difflib

S2T = dict(zip("这买内统计负担级过体户总资贷还价来为让们说话时间开关长发动经济务观点现实后场产业对车电会发联结约论题际环项报导记错须从样别两种应该钱儿虽无节数据备选岁个万与东严张头银认龄议书",
               "這買內統計負擔級過體戶總資貸還價來為讓們說話時間開關長發動經濟務觀點現實後場產業對車電會發聯結約論題際環項報導記錯須從樣別兩種應該錢兒雖無節數據備選歲個萬與東嚴張頭銀認齡議書"))
DIG = {"零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
UNIT = {"十": 10, "百": 100, "千": 1000}
NUMCH = "零〇一二兩三四五六七八九十百千萬"
NUMRE = re.compile(r"百分之(?:[%s]+(?:點[零〇一二三四五六七八九]+)?)|(?:[%s]+(?:點[零〇一二三四五六七八九]+)?)" % (NUMCH, NUMCH))
PUNCT = "，。、；：？！,;:?!"          # 念稿標點（全形／半形）
SKIP = re.compile(r"[「」『』（）()\s]")
STRIP = re.compile(r"[，。、；：？！「」『』（）()\s,;:?!…—-]")


def _pos(s):
    """純中文整數（可含十百千萬）→ int；沒有單位字就逐位（二〇三一→2031）。"""
    if not any(c in UNIT or c == "萬" for c in s):
        return int("".join(str(DIG[c]) for c in s))
    tot = sec = cur = 0
    for c in s:
        if c in DIG: cur = DIG[c]
        elif c in UNIT: sec += (cur or 1) * UNIT[c]; cur = 0
        elif c == "萬": tot += ((sec + cur) or 1) * 10000; sec = cur = 0
    return tot + sec + cur


def _conv(m):
    s = m.group(0); pct = s.startswith("百分之")
    if pct: s = s[3:]
    ip, _, dp = s.partition("點")
    if len(ip) + len(dp) < 2: return None        # 單一個中文數字（「一個」「第三」）不轉，兩邊一律當一般字
    try: out = str(_pos(ip)) if ip else "0"
    except Exception: return None
    if dp: out += "." + "".join(str(DIG[c]) for c in dp)
    return out + ("%" if pct else "")


def canon_chars(chars):
    """chars＝[(字, 來源索引)]；回傳 [(正規化字, 來源索引)]：中文數字換阿拉伯、簡轉繁、去標點。轉換出的數字，來源索引都取原數字最後一個字的。"""
    s = "".join(c for c, _ in chars); out = []; i = 0
    for m in NUMRE.finditer(s):
        conv = _conv(m)
        if conv is None: continue
        for k in range(i, m.start()): out.append((s[k], chars[k][1]))
        for ch_ in conv: out.append((ch_, chars[m.end() - 1][1]))
        i = m.end()
    for k in range(i, len(s)): out.append((s[k], chars[k][1]))
    return [(S2T.get(c, c), ix) for c, ix in out if not STRIP.match(c)]


def punct_boundaries(text, asr_words):
    """text＝念稿一句（含標點）；asr_words＝該句範圍內的 ASR 詞（字串 list）。
    回傳 {k}：ASR 第 k 個詞「之後」是念稿的逗號／句號等，且前後字都逐字對上（對不上的不回傳＝呼叫端不插停頓）。最後一個詞之後不回傳。"""
    raw = []; idx_punct = set(); pend = False   # raw＝非標點字；idx_punct＝前面有標點的 raw 索引
    for ch_ in text:
        if ch_ in PUNCT: pend = True; continue
        if SKIP.match(ch_): continue
        if pend: idx_punct.add(len(raw)); pend = False
        raw.append((ch_, len(raw)))
    sc = canon_chars(raw); sk = [c for c, _ in sc]
    punct_after = {i for i, (_, rix) in enumerate(sc) if (rix + 1) in idx_punct}   # 正規化字 i 後面有標點
    ach = [(c, wi) for wi, w in enumerate(asr_words) for c in w.strip()]
    ac = canon_chars(ach); ak = [c for c, _ in ac]; aw = [w for _, w in ac]
    if not sk or not ak: return set()
    mp = [-1] * len(sk)
    for a, b, n in difflib.SequenceMatcher(None, sk, ak, autojunk=False).get_matching_blocks():
        for t in range(n): mp[a + t] = b + t
    res = set()
    for i in punct_after:
        if i + 1 >= len(sk): continue
        a = mp[i]
        if a < 0 or mp[i + 1] != a + 1 or a + 1 >= len(ak): continue     # 標點前後兩字都要對上、且在 ASR 緊鄰
        if aw[a + 1] != aw[a] + 1: continue                             # 必須是 ASR 詞與詞的交界
        if not ((i >= 1 and mp[i - 1] == a - 1) or (i + 2 < len(sk) and mp[i + 2] == a + 2)): continue   # 旁邊至少再多對上一個字
        res.add(aw[a])
    return res


if __name__ == "__main__":
    print("".join(c for c, _ in canon_chars([(c, i) for i, c in enumerate("二十五到二十九歲，百分之十一，三萬六千三百一十二元，二零三一，三十三點四歲，一個")])))
