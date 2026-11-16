#!/bin/bash
# 配旁白＋成片＋最後驗證（一支）：bash v8/voice_pipeline.sh <名> [目標扣停頓語速，預設 5.2 字/秒]
# 1 次 Gemini 請求（tts_take.py）→ 本機 ASR → 切設定句／尾端雜訊、每鏡一段（cut_take_v8.py，不加速）→ segments.json → 成片 → 檢查 → 總覽圖
set -e
cd "$(dirname "$0")/.."
N=$1; RATE=${2:-5.2}; Q=../../queue/$N
python3 v8/gen_v8.py $N --nv > /dev/null       # 重寫 narration.txt（照最新規格）
[ -f $Q/narration_take.wav ] || python3 tts/tts_take.py $Q $Q/narration_take.wav
[ -f $Q/narration_take.asr.json ] || python3 tts/asr.py $Q/narration_take.wav $Q/narration_take.asr.json
# 2026-11-16 寫稿前必做第 6 條：寧可砍事實也不加速 → 不用 atempo（倍率 1.0），句間停頓上限 0.3 秒（換氣）
PRE_LAST=2.3 python3 tts/cut_take_v8.py $Q/narration_take.wav $Q/narration_take.asr.json $Q $Q/narration.wav 1.0 0.30
python3 tts/make_segments.py $Q narration.wav
python3 v8/gen_v8.py $N | head -1
node render_video.js $N 2>&1 | grep -v "^留白" | tail -5
python3 v8/check_v8.py $N $Q/check_v8.json
python3 v8/make_sheet.py $Q/video.mp4 $Q/overlap_report_video.json $Q/video_sheet.png
python3 v8/final_check.py $N $Q
rm -rf tmp/$N; for d in /tmp/tmp*; do [ -d "$d" ] && ls "$d" | grep -qE "sfx|v0.wav|voice.wav" && rm -rf "$d"; done
ls -la $Q/video.mp4 $Q/cover.jpg $Q/video_sheet.png
