#!/bin/bash
# 截全部動作並拼成三張總表：bash acts.sh <輪次標籤>
W=/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad; cd $W/glb_work
node ../glb_pipe/shots.js ../glb_stage/acts.json ../glb_stage 2>&1 | grep -v ReadPixels; cd $W/glb_stage
f(){ for a in "$@"; do echo ${a}_1_front.png ${a}_1_side.png ${a}_2_front.png ${a}_2_side.png; done; }
python3 ../glb_pipe/sheet.py $1_A.png 4 1 $(f idle walk run sit)
python3 ../glb_pipe/sheet.py $1_B.png 4 1 $(f talk argue note raise)
python3 ../glb_pipe/sheet.py $1_C.png 4 1 $(f clap cheer hit)
