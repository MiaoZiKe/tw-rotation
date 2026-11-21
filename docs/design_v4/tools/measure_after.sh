#!/usr/bin/env bash
# 改後量測：HUD 深（九頁全量）＋ 休閒淺、專業淺（三頁）。量法與改前同一支 measure.py。
set -u
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOGDIR="${1:-/tmp}"
cd "$ROOT"
timeout 2400 flock /tmp/claude-0/browser.lock python3 docs/design_v4/tools/measure.py --site site \
  --out docs/design_v4/data/after-hud-dark.json --theme4 hud --mode dark --shots "$LOGDIR/after_hud" > "$LOGDIR/after_hud.log" 2>&1
timeout 1200 flock /tmp/claude-0/browser.lock python3 docs/design_v4/tools/measure.py --site site \
  --out docs/design_v4/data/after-casual-light.json --theme4 casual --mode light --pages overview,flow,stock/2330 > "$LOGDIR/after_casual.log" 2>&1
timeout 1200 flock /tmp/claude-0/browser.lock python3 docs/design_v4/tools/measure.py --site site \
  --out docs/design_v4/data/after-pro-light.json --theme4 pro --mode light --pages overview,flow,stock/2330 > "$LOGDIR/after_pro.log" 2>&1
echo finished
