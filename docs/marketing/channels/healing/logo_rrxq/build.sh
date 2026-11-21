#!/bin/bash
# 完整重跑：量尺寸（第一輪）→ 依尺寸自動縮放（第二輪）→ 後製與檢查
cd "$(dirname "$0")"; rm -f fit.json; python3 gen.py && node render.js >/dev/null && python3 fit.py >/dev/null && python3 gen.py && node render.js && python3 compose.py
