#!/usr/bin/env python3
"""本機語音辨識（faster-whisper small，逐字時間戳；不花 API 請求）：python3 asr.py <wav> <輸出 asr.json>
輸出 [{"w","s","e","p"}]，給 cut_take_v8.py 找設定句結尾與核對每段內容。"""
import sys, json
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(sys.argv[1], language="zh", word_timestamps=True, beam_size=5, vad_filter=False)
out = [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)} for s in segs for w in s.words]
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False); print("ASR 字詞數", len(out), "".join(x["w"] for x in out)[-120:])
