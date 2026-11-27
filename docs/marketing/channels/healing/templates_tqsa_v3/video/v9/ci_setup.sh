#!/bin/bash
# healing_render.yml 各台機器共用的環境安裝（ffmpeg、中文字型、Playwright 固定裝在 /opt/node-tools、Python 套件）
# 用法：bash ci_setup.sh [--light]（--light＝只渲段的台，不裝 Python 分析套件）
set -e
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg fonts-noto-cjk
fc-list | grep -ci "Noto Sans CJK TC" || true
sudo mkdir -p /opt/node-tools && sudo chown "$USER" /opt/node-tools
cd /opt/node-tools && npm init -y >/dev/null && npm install --silent playwright@1.63.0
npx playwright install --with-deps chromium
[ "$1" = "--light" ] || pip install -q numpy scipy pillow matplotlib faster-whisper
