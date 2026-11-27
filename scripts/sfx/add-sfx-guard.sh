#!/bin/bash
# ④ 版：同 add-sfx.sh，混音加 --guard（旁白講話逐框音效低旁白 ≥ GUARD_DB，預設 15 dB）
# 複製自 MiaoZiKe/AI-Mp4 分支 claude/nifty-goodall-syke8a-1548 commit 69773ad（11-27 主控複製給④用；原版有更新時以 ai-mp4 為準再同步）
# 加音效後製（Andy 2026/11/27）。不重渲畫面：影像串流 copy，只換音軌。依賴：bash、python3＋numpy、ffmpeg／ffprobe。
# 通用用法（任何頻道，不綁專案路徑）：
#   bash scripts/three/add-sfx.sh <in.mp4> <cues.json 或 sfx.wav> <out.mp4> [--end <片尾卡開始秒>]
#     cues.json＝sfx-synth.py 的 cue 表（格式見 sfx-synth.py 檔頭；可含 total／endCardSec）；給 wav 就直接當音效軌。
# 科技片用法（自動從 storyboard／script／model 排音效）：
#   bash scripts/three/add-sfx.sh --tech <slug> <in.mp4> <out.mp4>
# 流程：（科技片先排 cue 表）→ sfx-synth.py 合成 → 抽原片音軌（已含旁白與片尾招牌音）→ 旁白講話時自動壓低 sfx（−8 dB），
#       sfx 比旁白低約 10 dB（講話時 ≈ 18 dB）→ 整條兩段式 loudnorm 回 −16 LUFS（TP ≤ −1.5，再接 −4 dBFS 限幅器吃掉 AAC 編碼的過衝）→ 影像 copy 封裝。
# 片尾卡之後沒有運作音效（--end 或 cue 表的 endCardSec；片尾招牌音不動）。
set -e
D=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$D/../.." && pwd)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
END=""
if [ "$1" = "--tech" ]; then
  SLUG=$2; IN=$3; OUT=$4; [ -z "$OUT" ] && { sed -n 3,9p "$0"; exit 1; }
  python3 "$D/sfx-ops.py" "$SLUG" --out "$ROOT/out/$SLUG.sfx.wav" --cues "$ROOT/out/$SLUG/sfx-cues.json"
  SFX="$ROOT/out/$SLUG.sfx.wav"; END=$(python3 -c "import json;print(json.load(open('$ROOT/out/$SLUG/sfx-cues.json'))['endCardSec'] or '')")
  SUMMARY="$ROOT/out/$SLUG/sfx-cues.json"
else
  IN=$1; SRC=$2; OUT=$3; [ -z "$OUT" ] && { sed -n 3,9p "$0"; exit 1; }
  [ "$4" = "--end" ] && END=$5
  case "$SRC" in
    *.json) python3 -c "import json,sys;d=json.load(open('$SRC'));sys.exit(0 if not isinstance(d,dict) or 'cues' in d else 1)"
            [ -z "$END" ] && END=$(python3 -c "import json;d=json.load(open('$SRC'));print((d.get('endCardSec') or '') if isinstance(d,dict) else '')")
            DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
            python3 "$D/sfx-synth.py" render "$SRC" "$TMP/sfx.wav" --total "$DUR" ${END:+--end $END} --cues-out "${OUT%.mp4}.sfx-cues.json"
            SFX="$TMP/sfx.wav"; SUMMARY="${OUT%.mp4}.sfx-cues.json" ;;
    *) SFX="$SRC" ;;
  esac
fi
ffmpeg -loglevel error -y -i "$IN" -vn -ac 2 -ar 48000 -c:a pcm_s16le "$TMP/voice.wav"
python3 "$D/sfx-synth.py" mix "$TMP/voice.wav" "$SFX" "$TMP/mix.wav" --guard ${GUARD_DB:-15} ${END:+--end $END}
M=$(ffmpeg -nostats -i "$TMP/mix.wav" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -c "import sys,json;print(json.load(sys.stdin)['$1'])"; }
ffmpeg -loglevel error -y -i "$TMP/mix.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000,alimiter=limit=0.63:attack=3:release=60:level=disabled:latency=1" -ar 48000 -c:a pcm_s16le "$TMP/final.wav"
ffmpeg -loglevel error -y -i "$IN" -i "$TMP/final.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 "$OUT"
echo "完成：$OUT"
[ -n "$SUMMARY" ] && python3 -c "import json;d=json.load(open('$SUMMARY'));print('音效',d['count'],d.get('byType',''))"
