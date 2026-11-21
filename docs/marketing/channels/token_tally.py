#!/usr/bin/env python3
"""在「該工作階段自己的容器」內執行：統計本機逐字稿的 token 用量。
用法：python3 tally.py [起點UTC,預設2026-11-14T16:00:00Z] > tally_<頻道>.json
依 message.id 去重；含 subagents/ 子檔；影片判定為關鍵字推估。"""
import json,glob,os,sys,re,collections
START=sys.argv[1] if len(sys.argv)>1 else "2026-11-14T16:00:00Z"
SPLIT=sys.argv[2] if len(sys.argv)>2 else "2026-11-15T16:00:00Z"
VID=re.compile(r"video|mp4|ffmpeg|render|旁白|配音|tts|storyboard|分鏡|ai-mp4|review9|remotion|hyperframes|media/.*v_",re.I)
seen=set();agg=collections.defaultdict(lambda:[0,0,0,0,0])
for f in glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"),recursive=True):
    sub="subagent" if "/subagents/" in f else "main"
    for line in open(f,errors="ignore"):
        try:e=json.loads(line)
        except:continue
        m=e.get("message") or {}
        u=m.get("usage")
        if e.get("type")!="assistant" or not u:continue
        ts=e.get("timestamp","")
        if ts<START:continue
        mid=m.get("id") or e.get("uuid")
        if mid in seen:continue
        seen.add(mid)
        txt=json.dumps(m.get("content",""),ensure_ascii=False)
        cat="video" if VID.search(txt) else "other"
        per="11-15" if ts<SPLIT else "11-16"
        k=(per,cat,sub,m.get("model","?"))
        a=agg[k];a[0]+=1;a[1]+=u.get("input_tokens",0);a[2]+=u.get("output_tokens",0)
        a[3]+=u.get("cache_creation_input_tokens",0);a[4]+=u.get("cache_read_input_tokens",0)
print(json.dumps([dict(period=k[0],cat=k[1],src=k[2],model=k[3],msgs=v[0],input=v[1],output=v[2],cache_write=v[3],cache_read=v[4]) for k,v in sorted(agg.items())],ensure_ascii=False,indent=1))
