#!/bin/bash
# 同批多支一次 TTS：bash v9/voice_batch.sh <資料夾1> <資料夾2> … [--take <已有的批次錄音 wav，離線驗證用，不送 TTS>] [--no-render] [--force]
# ①念稿檢查（整批任一支沒過就整批不送）→ ②合併稿一次 TTS（沒音訊最多重送 1 次）→ ③ASR → ④對齊切回各支 narration_take.wav／asr.json → ⑤各支接 cut_take_v8（＝make_video.sh --voice；--no-render 只做到切段＋segments）
# 上限：一批 ≤5 支且 ≤1,200 字（超過要 --force）。同音色同設定（tts_take.py 固定）。
set -e
cd "$(dirname "$0")/.."
DIRS=(); TAKE=""; NR=0; FORCE=0; args=("$@"); i=0
while [ $i -lt ${#args[@]} ]; do a=${args[$i]}
  case $a in --take) i=$((i+1)); TAKE=${args[$i]};; --no-render) NR=1;; --force) FORCE=1;; *) DIRS+=("$(cd "$a" && pwd)");; esac; i=$((i+1)); done
[ ${#DIRS[@]} -ge 2 ] || { echo "用法：bash v9/voice_batch.sh <資料夾1> <資料夾2> … [--take wav] [--no-render] [--force]（單支請用 make_video.sh --voice）"; exit 1; }
for d in "${DIRS[@]}"; do [ -f "$d/script.json" ] || { echo "$d 沒有 script.json"; exit 1; }; python3 v9/gen_v9.py "$d" --nv > /dev/null; done
python3 v9/check_narration.py "${DIRS[@]}" > /tmp/vb_check.txt || { cat /tmp/vb_check.txt | grep -E "^==|不通過"; echo "念稿檢查沒過，整批不送 TTS。"; exit 1; }
grep -E "^==|警告" /tmp/vb_check.txt
BATCH="$(dirname "${DIRS[0]}")/_batch_$(date +%m%d%H%M)"; mkdir -p "$BATCH"
CH=$(python3 v9/voice_batch.py prepare "$BATCH" "${DIRS[@]}" | tee /dev/stderr | grep -oE "[0-9]+ 字" | grep -oE "[0-9]+")
if [ $FORCE = 0 ] && { [ ${#DIRS[@]} -gt 5 ] || [ "$CH" -gt 1200 ]; }; then echo "一批 ≤5 支且 ≤1,200 字（這批 ${#DIRS[@]} 支、$CH 字），要超過請加 --force"; exit 1; fi
if [ -n "$TAKE" ]; then cp "$TAKE" "$BATCH/batch_take.wav"
else
  for try in 1 2; do python3 tts/tts_take.py "$BATCH" "$BATCH/batch_take.wav" && [ -s "$BATCH/batch_take.wav" ] && break; echo "TTS 沒拿到音訊（第 $try 次）"; [ $try = 2 ] && { echo "重送 1 次仍失敗，停止"; exit 1; }; done
fi
python3 tts/asr.py "$BATCH/batch_take.wav" "$BATCH/batch_take.asr.json"
python3 v9/voice_batch.py split "$BATCH" "${DIRS[@]}"
for d in "${DIRS[@]}"; do
  if [ $NR = 1 ]; then
    PRE_LAST=2.3 python3 tts/cut_take_v8.py "$d/narration_take.wav" "$d/narration_take.asr.json" "$d" "$d/narration.wav" 1.0 0.60 0.45 0.80 | head -3 && python3 tts/make_segments.py "$d" narration.wav
  else bash v9/make_video.sh "$d" --voice; fi
done
echo "批次完成：$BATCH"
