import sys; sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102b/src')
from marks import *
CORAL='#FF5B4A';YEL='#FFC83D';MINT='#19C6A7';SKY='#3FA9FF';CREAM='#FFF6E6';INK='#232733';WHITE='#FFFFFF'
cfg={
 'A':[(CORAL,{'main':WHITE,'accent':YEL}),(CREAM,{'main':INK,'accent':CORAL})],
 'B':[(SKY,{'c1':WHITE,'c2':YEL,'c3':'#BFE3FF','accent':CORAL}),(CREAM,{'c1':SKY,'c2':YEL,'c3':MINT,'accent':CORAL})],
 'C':[(YEL,{'c1':WHITE,'c2':INK,'accent':CORAL}),(CREAM,{'c1':MINT,'c2':SKY,'accent':CORAL})],
 'D':[(INK,{'main':WHITE,'accent':CORAL}),(CREAM,{'main':INK,'accent':CORAL})],
}
h='<html><body style="margin:0;background:#ddd;display:flex;flex-wrap:wrap;gap:20px;padding:20px">'
for k,v in cfg.items():
    for bg,p in v:
        h+=f'<svg width="320" height="320" viewBox="0 0 100 100"><rect width="100" height="100" rx="22" fill="{bg}"/>{MARKS[k](p)}</svg>'
open('/tmp/fp/proto.html','w').write(h)
