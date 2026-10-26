#!/bin/bash
cd "$(dirname "$0")"
for id in Ex1 Ex2 Ex3 Demo; do
  lc=$(echo $id | tr A-Z a-z)
  npx remotion render src/index.ts $id out/$lc.mp4 --crf=16 --concurrency=2 >> render.log 2>&1
done
echo ALLDONE >> render.log
