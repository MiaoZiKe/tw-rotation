#!/bin/bash
# 依序產生並渲染無旁白版，每支跑完接 check_v8（靜止段、強調淨空），之後刪掉逐幀 PNG（磁碟有限）。用法：bash v8/render_nv_all.sh <名>...
cd "$(dirname "$0")/.."
for n in "$@"; do
  python3 v8/gen_v8.py "$n" --nv > /dev/null && node render_video.js "$n" 2>&1 | grep -v "^留白" | tail -4
  python3 v8/check_v8.py "$n" ../../queue/"${n}"/check_v8_nv.json
  rm -rf tmp/"$n"; for d in /tmp/tmp*; do [ -d "$d" ] && ls "$d" | grep -qE "sfx|v0.wav|voice.wav" && rm -rf "$d"; done
  echo "== $n 完成 $(TZ=Asia/Taipei date +%H:%M)"
done
