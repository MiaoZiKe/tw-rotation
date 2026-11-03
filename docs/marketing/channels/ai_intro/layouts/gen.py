# 版型範例產生器：3 方向 × (封面 1080x1350 / 截圖頁 1080x1350)，推薦方向另出 Reels 封面 1080x1920；並做重疊檢查
import json, sys
T = {
 "A": dict(name="實測終端", bg="#0F1722", card="#182334", line="#2A3A52", ink="#F3F7FB", ink2="#B4C2D3", acc="#7CF29A", acc2="#5AB0FF", warn="#FFC857", on="#0B1A12", font="'Noto Sans TC','WenQuanYi Zen Hei',sans-serif", ui_bg="#F6F7F9", ui_ink="#1D2530"),
 "B": dict(name="紙本實驗報告", bg="#F6EFE2", card="#FFFBF3", line="#D9CBB2", ink="#2A2118", ink2="#6B5B49", acc="#D4401F", acc2="#1F6F6B", warn="#B7791F", on="#FFFFFF", font="'Noto Serif TC','WenQuanYi Zen Hei',serif", ui_bg="#FFFFFF", ui_ink="#222"),
 "C": dict(name="清晨薄荷儀表", bg="#EAF7F3", card="#FFFFFF", line="#BFE3D8", ink="#0C2B2A", ink2="#3F6361", acc="#0E9F8A", acc2="#6D5BD0", warn="#C26A00", on="#FFFFFF", font="'Noto Sans TC','WenQuanYi Zen Hei',sans-serif", ui_bg="#F7FAFA", ui_ink="#1D2530"),
}
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:%(W)dpx;height:%(H)dpx;background:%(bg)s;color:%(ink)s;font-family:%(font)s;position:relative;overflow:hidden}
.abs{position:absolute}
.tag{font-size:30px;font-weight:700;color:%(acc)s;letter-spacing:2px}
.date{font-size:28px;color:%(ink2)s;font-weight:500}
.hook{font-size:132px;font-weight:900;line-height:1.12;letter-spacing:-2px}
.hook em{font-style:normal;color:%(acc)s}
.sub{font-size:44px;font-weight:500;color:%(ink2)s;line-height:1.4}
.chip{font-size:30px;font-weight:700;padding:10px 24px;border-radius:999px;border:2px solid %(line)s;background:%(card)s;color:%(ink)s}
.h2{font-size:58px;font-weight:800;line-height:1.25}
.step{font-size:30px;font-weight:800;background:%(acc)s;color:%(on)s;padding:6px 20px;border-radius:10px}
.shot{background:%(card)s;border:3px solid %(line)s;border-radius:22px;overflow:hidden;box-shadow:0 18px 40px -24px rgba(0,0,0,.45)}
.bar{height:56px;background:%(card)s;border-bottom:2px solid %(line)s;display:flex;align-items:center;gap:10px;padding-left:20px;font-size:24px;color:%(ink2)s}
.dot{width:16px;height:16px;border-radius:50%%;background:%(line)s}
.ui{background:%(ui_bg)s;color:%(ui_ink)s;height:calc(100%% - 56px);padding:28px;font-family:sans-serif}
.ui .l{height:22px;border-radius:6px;background:#D7DCE3;margin-bottom:16px}
.ui .b{border-radius:12px;background:#fff;border:2px solid #DDE2E8;padding:20px;margin-bottom:16px;font-size:30px}
.hl{border:6px solid %(warn)s;border-radius:16px;background:rgba(255,200,87,.14)}
.num{width:64px;height:64px;border-radius:50%%;background:%(warn)s;color:#1b1300;font-weight:900;font-size:36px;display:flex;align-items:center;justify-content:center}
.note{font-size:34px;font-weight:600;line-height:1.4;color:%(ink)s}
.note b{color:%(acc)s}
.disc{font-size:26px;color:%(ink2)s;font-weight:500;border-top:2px solid %(line)s;padding-top:14px;display:flex;justify-content:space-between}
.disc span.k{color:%(ink)s;font-weight:700}
.badge{font-size:28px;font-weight:800;padding:6px 18px;border-radius:8px;border:3px solid %(acc2)s;color:%(acc2)s}
"""
def cover(t, W, H, reels=False):
    top = 250 if reels else 72; bot = 230 if reels else 72
    return f"""<div class=abs data-o=tag style="left:64px;top:{top}px"><span class=tag>AI 實測 NO.07</span></div>
<div class=abs data-o=date style="right:64px;top:{top+2}px"><span class=date>2026/11/03</span></div>
<div class=abs data-o=hook style="left:64px;top:{top+90}px;width:952px"><div class=hook>我用 <em>AI</em><br>一天寫完<br>一個月的報表</div></div>
<div class=abs data-o=sub style="left:64px;top:{top+90+480 if not reels else top+90+480}px;width:952px"><div class=sub>實測 3 款工具，第 2 款最意外</div></div>
<div class=abs data-o=chips style="left:64px;top:{top+90+480+130}px;display:flex;gap:16px"><span class=chip>省 6 小時</span><span class=chip>免費可用</span><span class=chip>附實測截圖</span></div>
<div class="abs shot" data-o=peek style="left:64px;top:{H-bot-(300 if not reels else 330)-70}px;width:952px;height:{300 if not reels else 330}px"><div class=bar><i class=dot></i><i class=dot></i><i class=dot></i></div><div class=ui><div class=l style="width:60%"></div><div class=l style="width:85%"></div><div class=l style="width:40%"></div></div></div>
<div class=abs data-o=disc style="left:64px;right:64px;top:{H-bot-50}px;width:952px"><div class=disc><span><span class=k>無業配</span>｜截圖為本人實測</span><span>圖文含 AI 協助</span></div></div>"""
def shot(t, W, H):
    return f"""<div class=abs data-o=step style="left:64px;top:72px"><span class=step>STEP 2</span></div>
<div class=abs data-o=date style="right:64px;top:76px"><span class=date>2/6</span></div>
<div class=abs data-o=title style="left:64px;top:150px;width:952px"><div class=h2>貼上原始資料，一鍵出圖表</div></div>
<div class="abs shot" data-o=shot id=shot style="left:64px;top:300px;width:952px;height:640px"><div class=bar><i class=dot></i><i class=dot></i><i class=dot></i><span>某某工具 · 範例畫面</span></div><div class=ui><div class=b>輸入：2025 Q3 銷售表（已遮個資）</div><div class=b style="height:90px"></div><div class=b>輸出：長條圖＋摘要</div></div></div>
<div class="abs hl" data-o=hl data-in=shot style="left:92px;top:590px;width:896px;height:96px"></div>
<div class="abs num" data-o=n1 data-in=shot style="left:900px;top:512px">1</div>
<div class=abs data-o=arrow data-in=shot style="left:760px;top:700px"><svg width=210 height=170 viewBox="0 0 210 170"><path d="M200 160 C170 90 110 60 40 30" stroke="{t['warn']}" stroke-width="9" fill="none" stroke-linecap="round"/><path d="M40 30 L82 28 M40 30 L56 68" stroke="{t['warn']}" stroke-width="9" stroke-linecap="round"/></svg></div>
<div class=abs data-o=note style="left:64px;top:980px;width:952px"><div class=note><b>重點：</b>它自動辨識欄位，不用先整理表格。實測 120 列資料，約 8 秒完成。</div></div>
<div class=abs data-o=source style="left:64px;top:1130px"><span class=badge>實測｜非 AI 生成</span></div>
<div class=abs data-o=disc style="left:64px;top:{H-72-50}px;width:952px"><div class=disc><span><span class=k>無業配</span>｜截圖本人實測，個資已遮</span><span>測試日 11/03</span></div></div>"""
def page(t, body, W, H):
    return f"<html><head><meta charset=utf-8><style>{CSS % dict(t, W=W, H=H)}</style></head><body>{body}</body></html>"
CHECK = """()=>{const els=[...document.querySelectorAll('[data-o]')].map(e=>{const r=e.getBoundingClientRect();return {o:e.dataset.o,inn:e.dataset.in||'',x:r.left,y:r.top,w:r.right,h:r.bottom}});
const bad=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],b=els[j];
if(a.inn===b.o||b.inn===a.o)continue; const ix=Math.min(a.w,b.w)-Math.max(a.x,b.x), iy=Math.min(a.h,b.h)-Math.max(a.y,b.y);
if(ix>0&&iy>0)bad.push(a.o+'×'+b.o+' '+Math.round(ix)+'x'+Math.round(iy))}
const oob=els.filter(e=>e.x<0||e.y<0||e.w>document.body.clientWidth||e.h>document.body.clientHeight).map(e=>e.o);
return {n:els.length,bad,oob}}"""
import os
os.makedirs("html",exist_ok=True)
for k,t in T.items():
    for kind,W,H,fn in [("cover",1080,1350,lambda t:cover(t,1080,1350)),("shot",1080,1350,lambda t:shot(t,1080,1350))]+([("reels",1080,1920,lambda t:cover(t,1080,1920,True))] if k=="A" else []):
        open(f"html/{k}_{kind}.html","w").write(page(t,fn(t),W,H))
open("check.js.txt","w").write(CHECK)
