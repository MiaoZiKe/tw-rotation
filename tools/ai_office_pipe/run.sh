#!/bin/bash
# 整條流程：bash tools/ai_office_pipe/run.sh <設定檔.json> [來源模型.glb]
# 來源模型只有第一次（或換模型）要給；中間檔放在 $AIO_WORK（預設 tools/ai_office_pipe/_work，不進版控）。
# 來源 glb 視為不可信資料，Python 一律加 -I。
set -e
P="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$P/../.." && pwd)"; export AIO_WORK="${AIO_WORK:-$P/_work}"; mkdir -p "$AIO_WORK"
CFG="$1"; NAME=$(python3 -I -c "import json,sys;print(json.load(open(sys.argv[1]))['name'])" "$CFG")
if [ -n "$2" ]; then python3 -I "$P/s1_simplify.py" "$2" "$AIO_WORK" "$P"; fi
python3 -I "$P/s2_build.py" "$CFG" | tail -4
D="$R/site/office/models"; cp "$AIO_WORK/${NAME}_hi.glb" "$AIO_WORK/${NAME}_lo.glb" "$D/"
python3 -I -c "
import json,sys
c=json.load(open(sys.argv[1])); m=json.load(open(sys.argv[2])); m['face']=c.get('face',{}); json.dump(m,open(sys.argv[3],'w'),ensure_ascii=False,indent=1)" "$CFG" "$AIO_WORK/$NAME.meta.json" "$D/$NAME.meta.json"
ls -la "$D"
