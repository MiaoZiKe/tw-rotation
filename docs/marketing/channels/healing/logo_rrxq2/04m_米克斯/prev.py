import sys, json; sys.argv
from mix import *
S=sys.argv[1]; jobs=[]
for v,fo,fn in VAR:
    for tag in ('奶油晨光','深色模式','單色黑'):
        P=TONES[tag]; sv=gen.avatar_svg(P,fn(P),1.0); p=f'{S}/{v}_{tag}'; open(p+'.svg','w').write(sv)
        jobs.append(dict(svg=p+'.svg',png=p+'.png',w=1080,h=1080))
    P=TONES['奶油晨光']; sv=gen.avatar_svg(P,fn(P),1.0,bg=False); p=f'{S}/{v}_T'; open(p+'.svg','w').write(sv)
    jobs.append(dict(svg=p+'.svg',png=p+'.png',w=1080,h=1080,transparent=True))
json.dump(dict(jobs=jobs),open(f'{S}/jobs.json','w'))
