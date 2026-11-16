#!/bin/bash
# 一支指令（v9）：bash v9/make_video.sh <佇列資料夾> [--voice]
# 讀 <資料夾>/script.json → build_spec 驗證 → 無旁白渲染＋check_v8＋autofix（最多 3 輪）。
# 加 --voice：先念稿檢查（欸／英文字母開頭／阿拉伯數字，沒過就不送 TTS）→ 沒有 narration_take.wav 才送 1 次 TTS → ASR → 切段（不加速、段間停頓）→ segments → 成片＋final_check＋autofix → 總覽圖。
# 已有 narration_take.wav（含 voice_batch.sh 切回來的）就不再送 TTS。
set -e
cd "$(dirname "$0")/.."
[ -n "$1" ] && [ -f "$1/script.json" ] || { echo "用法：bash v9/make_video.sh <佇列資料夾（要有 script.json）> [--voice]"; exit 1; }
Q=$(cd "$1" && pwd); N=$(basename "$Q"); VOICE=0; for a in "${@:2}"; do [ "$a" = "--voice" ] && VOICE=1; done
python3 v9/build_spec.py "$Q" > /dev/null || { echo "script.json 轉規格失敗"; exit 1; }
python3 v9/gen_v9.py "$Q" --nv > /dev/null          # 重寫 narration.txt、順便確認整條路徑能產 html
if [ $VOICE = 1 ]; then
  python3 v9/check_narration.py "$Q" || { echo "念稿檢查沒過，不送 TTS。改 script.json 的 say 再跑。"; exit 1; }
  [ -f "$Q/narration_take.wav" ] || python3 tts/tts_take.py "$Q" "$Q/narration_take.wav"
  [ -f "$Q/narration_take.asr.json" ] || python3 tts/asr.py "$Q/narration_take.wav" "$Q/narration_take.asr.json"
  PRE_LAST=2.3 python3 tts/cut_take_v8.py "$Q/narration_take.wav" "$Q/narration_take.asr.json" "$Q" "$Q/narration.wav" 1.0 0.45 0.30 0.70
  python3 tts/make_segments.py "$Q" narration.wav
  python3 v9/autofix.py "$Q" --voice || echo "（autofix 後仍有要人看的項目，見上方與 $Q/autofix_log.json）"
  python3 v8/make_sheet.py "$Q/video.mp4" "$Q/overlap_report_video.json" "$Q/video_sheet.png"
  ls -la "$Q/video.mp4" "$Q/cover.jpg" "$Q/video_sheet.png"
else
  python3 v9/autofix.py "$Q" || echo "（autofix 後仍有要人看的項目，見上方與 $Q/autofix_log.json）"
  ls -la "$Q/video_nv.mp4"
fi
