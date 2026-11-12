#!/bin/bash
# 重跑整條流程並發佈到網站資料夾：bash publish.sh <config.json>
set -e
W=/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad
python3 -I $W/glb_pipe/s2_build.py $1 | tail -3
D=/home/user/tw-rotation/site/office/models
cp $W/glb_out/boy_hi.glb $W/glb_out/boy_lo.glb $W/glb_out/boy.meta.json $D/
python3 -I -c "
import json,sys
from PIL import Image
c=json.load(open('$1')); Image.open(c['image']).convert('RGB').save('$D/'+c['name']+'_ref.png')
m=json.load(open('$D/'+c['name']+'.meta.json')); m['face']=c.get('face',{}); json.dump(m,open('$D/'+c['name']+'.meta.json','w'),ensure_ascii=False,indent=1)"
ls -la $D
