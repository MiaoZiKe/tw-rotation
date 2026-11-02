import sys; sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102c/src')
from marks_c import *
P={'main':'#fff','acc':'#FFC83D','sec':'#FFE3DE'}
h='<html><body style="margin:0;background:#ddd;display:flex;flex-wrap:wrap;gap:16px;padding:16px">'
for k,n,f in VARS:
    h+=f'<svg width="300" height="300" viewBox="0 0 100 100"><rect width="100" height="100" rx="22.5" fill="#FF5B4A"/>{render(f(P),60)}</svg>'
open('/tmp/fp/pc.html','w').write(h)
