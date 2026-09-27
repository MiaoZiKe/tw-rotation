#!/usr/bin/env bash
# 設計 v4 截圖：三頁 × 四寬度 × 三主題（各主題的預設明暗）＋ 1440 的另一種明暗 ＋ 改前對照。
# 每一次開瀏覽器都包 flock（容器同時只能開一支瀏覽器）。輸出轉成 JPEG 放 docs/design_v4/shots/。
# 用法：bash docs/design_v4/tools/shots.sh [before|after|all]
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="$ROOT/docs/design_v4/shots"
TMP="${TMPDIR:-/tmp}/t4shots"
BEFORE_SITE="${BEFORE_SITE:-}"
mkdir -p "$OUT" "$TMP"
PAGES="overview flow stock/2330"
WIDTHS="1440,1100,800,390"
what="${1:-all}"

shoot() {  # $1=tag $2=view $3=widths $4=ls $5=site(可空)
  local tag="$1" view="$2" widths="$3" ls="$4" site="${5:-}"
  local d="$TMP/$tag"; rm -rf "$d"; mkdir -p "$d"
  if [ -n "$site" ]; then
    TW_SHOW_SITE="$site" TW_SHOW_OUT="$d" timeout 600 flock /tmp/claude-0/browser.lock \
      python3 "$ROOT/scripts/_show.py" --view "$view" --width "$widths" --full --wait 3500 --ls "$ls" --tag "$tag" >/dev/null 2>&1
  else
    TW_SHOW_OUT="$d" timeout 600 flock /tmp/claude-0/browser.lock \
      python3 "$ROOT/scripts/_show.py" --view "$view" --width "$widths" --full --wait 3500 --ls "$ls" --tag "$tag" >/dev/null 2>&1
  fi
  python3 - "$d" "$OUT" <<'PY'
import sys, pathlib
from PIL import Image
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for p in sorted(src.glob('*.png')):
    im = Image.open(p).convert('RGB')
    q = dst / (p.stem + '.jpg')
    im.save(q, quality=74, optimize=True)
    print(q.relative_to(dst.parent.parent.parent))
PY
}

if [ "$what" = before ] || [ "$what" = all ]; then
  for v in $PAGES; do
    shoot "before-dark" "$v" "$WIDTHS" "tw.theme=dark" "$BEFORE_SITE"
    shoot "before-light" "$v" "1440" "tw.theme=light" "$BEFORE_SITE"
  done
fi
if [ "$what" = after ] || [ "$what" = all ]; then
  for v in $PAGES; do
    shoot "casual-light" "$v" "$WIDTHS" "tw.theme4=casual,tw.theme=light"
    shoot "hud-dark" "$v" "$WIDTHS" "tw.theme4=hud,tw.theme=dark"
    shoot "pro-light" "$v" "$WIDTHS" "tw.theme4=pro,tw.theme=light"
    shoot "casual-dark" "$v" "1440" "tw.theme4=casual,tw.theme=dark"
    shoot "hud-light" "$v" "1440" "tw.theme4=hud,tw.theme=light"
    shoot "pro-dark" "$v" "1440" "tw.theme4=pro,tw.theme=dark"
  done
fi
