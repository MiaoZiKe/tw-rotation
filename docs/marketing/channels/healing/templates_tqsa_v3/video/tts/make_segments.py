#!/usr/bin/env python3
"""cut_take.py 的結果 → segments.json（產生器讀它對齊每鏡長度與字幕）＋ .srt。
每鏡起點＝該句第一個字前 0.25 秒（讓 5 幀換鏡＋字幕進場在開口前完成）；第一鏡從 0 開始（旁白 voiceLeadIn 0.2 秒）。
用法：python3 make_segments.py <佇列資料夾> <旁白 wav 檔名>"""
import json, sys, os
q, wn = sys.argv[1:3]; c = json.load(open(os.path.join(q, wn + ".cut.json")))
segs = []
for i, s in enumerate(c["segments"]):
    prev = c["segments"][i - 1] if i else None
    st = 0.0 if i == 0 else (round(prev["end"] + .12, 3) if s["speech_start"] - prev["end"] > 1.0 else round(s["speech_start"] - .25, 3))   # 前面有長停頓（片尾）：鏡頭在上一句一結束就換，開口晚一點
    segs.append({"id": s["id"], "text": s["text"], "start": st, "end": s["end"], "speech_start": s["speech_start"], "words": s.get("words", []), "audio": wn})
json.dump({"audio": wn, "voiceLeadIn": c["voiceLeadIn"], "model": "gemini-3.8-flash-tts", "voice": "Sulafat", "atempo": c["atempo"], "rate_incl_pauses": c["rate_incl_pauses"], "rate_speech_only": c["rate_speech_only"], "preamble_cut_sec": c["preamble_cut_sec"], "segments": segs},
          open(os.path.join(q, "segments.json"), "w"), ensure_ascii=False, indent=1)
f = lambda t: "%02d:%02d:%02d,%03d" % (t // 3600, t % 3600 // 60, int(t % 60), round((t % 1) * 1000) % 1000)
open(os.path.join(q, wn.replace(".wav", ".srt")), "w", encoding="utf-8").write("\n".join("%d\n%s --> %s\n%s\n" % (i + 1, f(s["speech_start"]), f(s["end"]), s["text"].rstrip("。")) for i, s in enumerate(segs)))
print("segments.json、%s 完成" % wn.replace(".wav", ".srt"))
