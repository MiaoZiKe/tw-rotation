# A 方向（實測終端）第 2 版：依美術總監審查修正。只產 A，不動 B、C。
import os
t = dict(bg="#0F1722", card="#182334", line="#2A3A52", ink="#F3F7FB", ink2="#B4C2D3",
         acc="#6FD8A0", warn="#FFC857", on="#0B1A12", ui_bg="#F6F7F9", ui_ink="#1D2530",
         font="'Noto Sans TC','WenQuanYi Zen Hei',sans-serif")
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:%(W)dpx;height:%(H)dpx;background:%(bg)s;color:%(ink)s;font-family:%(font)s;position:relative;overflow:hidden}
.abs{position:absolute}
.tag{font-size:30px;font-weight:700;color:%(acc)s;letter-spacing:2px;line-height:1.3}
.date{font-size:28px;color:%(ink2)s;font-weight:500;line-height:1.3}
.hook{font-size:132px;font-weight:900;line-height:1.12;letter-spacing:-2px}
.hook em{font-style:normal;color:%(acc)s}
.sub{font-size:44px;font-weight:500;color:%(ink2)s;line-height:1.4}
.chip{font-size:30px;font-weight:700;padding:10px 24px;border-radius:999px;border:2px solid %(line)s;background:%(card)s;color:%(ink)s;line-height:1.3}
.h2{font-size:58px;font-weight:800;line-height:1.25}
.step{font-size:30px;font-weight:800;border:3px solid %(acc)s;color:%(acc)s;padding:4px 18px;border-radius:10px;line-height:1.3}
.shot{background:%(card)s;border:3px solid %(line)s;border-radius:22px;overflow:hidden}
.bar{height:56px;background:%(card)s;border-bottom:2px solid %(line)s;display:flex;align-items:center;gap:10px;padding-left:20px;font-size:24px;color:%(ink2)s}
.dot{width:16px;height:16px;border-radius:50%%;background:%(line)s}
.ui{background:%(ui_bg)s;color:%(ui_ink)s;height:calc(100%% - 56px);padding:28px;font-family:sans-serif}
.dim .ui{filter:brightness(.5)}
.ui .l{height:22px;border-radius:6px;background:#D7DCE3;margin-bottom:16px}
.ui .b{border-radius:12px;background:#fff;border:2px solid #DDE2E8;padding:20px;margin-bottom:16px;font-size:30px;height:84px}
.hl{position:absolute;border:6px solid %(warn)s;border-radius:16px;background:rgba(255,200,87,.14)}
.num{position:absolute;width:64px;height:64px;border-radius:50%%;background:%(warn)s;color:#1b1300;font-weight:900;font-size:36px;display:flex;align-items:center;justify-content:center}
.note{font-size:34px;font-weight:600;line-height:1.4}
.note b{color:%(acc)s}
.badge{font-size:28px;font-weight:800;padding:6px 18px;border-radius:8px;border:3px solid %(acc)s;color:%(acc)s;line-height:1.3}
.disc{font-size:28px;color:%(ink2)s;font-weight:500;border-top:2px solid %(line)s;padding-top:12px;display:flex;justify-content:space-between;line-height:1.3}
.disc .k{color:%(ink)s;font-weight:700}
table{border-collapse:collapse;width:100%%;font-size:34px;table-layout:fixed}
col.c0{width:28%%}col.c1{width:24%%}
th{font-size:32px;font-weight:800;text-align:left;padding:0 20px;height:96px;border-bottom:3px solid %(line)s;color:%(ink2)s}
td{padding:0 20px;height:124px;border-bottom:2px solid %(line)s;font-weight:600}
td.w{background:rgba(111,216,160,.14);color:%(acc)s;font-weight:800}
.item{display:flex;gap:24px;align-items:flex-start}
.item .n{flex:none;width:64px;height:64px;border-radius:50%%;border:3px solid %(acc)s;color:%(acc)s;font-weight:900;font-size:34px;display:flex;align-items:center;justify-content:center}
.item p{font-size:44px;font-weight:700;line-height:1.35}
.item small{display:block;font-size:30px;font-weight:500;color:%(ink2)s;margin-top:6px}
"""
def disc(bot, left="無業配｜截圖已遮個資"):
    return f'<div class=abs data-o=disc style="left:64px;width:952px;bottom:{bot}px"><div class=disc><span><span class=k>{left.split("｜")[0]}</span>｜{left.split("｜")[1]}</span><span>圖文含 AI 協助</span></div></div>'
def cover(reels):
    H = 1920 if reels else 1350; top = 250 if reels else 72; bot = 230 if reels else 72
    hk = top + (130 if reels else 90)
    sub = hk + 480; chips = sub + (110 if reels else 100)
    ch = 466 if reels else 300
    cardtop = (H - bot - 56 - 24 - ch) if True else 0   # 揭露列約 56px 高，再留 24px
    dimcls = "shot dim"
    return f"""<div class=abs data-o=tag style="left:64px;top:{top}px"><span class=tag>AI 實測 第 07 期</span></div>
<div class=abs data-o=date style="right:64px;top:{top}px"><span class=date>2026/11/03</span></div>
<div class=abs data-o=hook style="left:64px;top:{hk}px;width:952px"><div class=hook>我用 <em>AI</em><br>一天寫完<br>一個月的報表</div></div>
<div class=abs data-o=sub style="left:64px;top:{sub}px;width:952px"><div class=sub>實測 3 款工具，第 2 款最意外</div></div>
<div class=abs data-o=chips style="left:64px;top:{chips}px;display:flex;gap:16px"><span class=chip>省 6 小時</span><span class=chip>免費可用</span><span class=chip>附測試條件</span></div>
<div class="abs {dimcls}" data-o=peek style="left:64px;top:{cardtop}px;width:952px;height:{ch}px"><div class=bar><i class=dot></i><i class=dot></i><i class=dot></i></div><div class=ui><div class=l style="width:60%"></div><div class=l style="width:85%"></div><div class=l style="width:40%"></div></div></div>
{disc(bot)}"""
def head(n, tot, title):
    return f"""<div class=abs data-o=step style="left:64px;top:72px"><span class=step>{n}</span></div>
<div class=abs data-o=date style="right:64px;top:76px"><span class=date>{tot}</span></div>
<div class=abs data-o=title style="left:64px;top:150px;width:952px"><div class=h2>{title}</div></div>"""
def shot():
    return head("步驟 2","2/6","貼上原始資料，一鍵出圖表") + f"""
<div class="abs shot" data-o=shot id=shot style="left:64px;top:300px;width:952px;height:640px"><div class=bar><i class=dot></i><i class=dot></i><i class=dot></i><span>某某工具 · 範例畫面</span></div><div class=ui><div class=b>輸入：2025 Q3 銷售表（已遮個資）</div><div class=b style="height:100px;color:#888">資料已貼上，共 120 列</div><div class=b>輸出：長條圖＋摘要</div></div></div>
<div class=abs data-o=anno data-in=shot style="left:92px;top:590px;width:868px;height:96px">
 <div class=hl style="left:0;top:0;width:700px;height:96px"></div>
 <svg class=abs style="left:708px;top:30px" width=84 height=36 viewBox="0 0 84 36"><path d="M80 18 H14" stroke="{t['warn']}" stroke-width="9" stroke-linecap="round"/><path d="M30 4 L12 18 L30 32" stroke="{t['warn']}" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>
 <div class=num style="left:804px;top:16px">1</div></div>
<div class=abs data-o=note style="left:64px;top:980px;width:952px"><div class=note><b>重點：</b>它自動辨識欄位，不用先整理表格。實測 120 列資料，約 8 秒完成。</div></div>
<div class=abs data-o=badge style="left:64px;top:1120px"><span class=badge>截圖為實測｜非 AI 生成</span></div>
<div class=abs data-o=tdate style="right:64px;top:1124px"><span class=date>測試日 11/03</span></div>
{disc(72)}"""
def table():
    return head("步驟 4","4/6","三款工具實測比較") + """
<div class=abs data-o=table style="left:64px;top:300px;width:952px"><table><col class=c0><col class=c1><col class=c1><col class=c1>
<tr><th>項目</th><th>工具 A</th><th>工具 B</th><th>工具 C</th></tr>
<tr><td>120 列耗時</td><td>21 秒</td><td class=w>8 秒 ✓</td><td>35 秒</td></tr>
<tr><td>欄位辨識</td><td>手動</td><td class=w>自動 ✓</td><td>自動</td></tr>
<tr><td>每日免費次數</td><td class=w>20 次 ✓</td><td>5 次</td><td>無</td></tr>
<tr><td>輸出圖表</td><td>3 種</td><td class=w>9 種 ✓</td><td>5 種</td></tr></table></div>
<div class=abs data-o=note style="left:64px;top:930px;width:952px"><div class=note><b>怎麼比的：</b>同一份 120 列銷售表、同一台電腦、各測 3 次取中位數，11/03 測試。</div></div>
<div class=abs data-o=first style="left:64px;top:1070px;width:952px"><div class=note><b>結論先看：</b>工具 B 三項勝出，但免費次數只有 A 的四分之一。</div></div>
""" + disc(72)
def end():
    items = [("誰適合、誰不適合","適合常整理表格的人；資料本來就整齊的人省不了多少"),("結果要人工抽查","AI 出的圖表數字，交出去前至少核對 3 處"),("行動：先用免費版測 1 週","不用先付費，確認資料格式對得上再決定")]
    s = head("結論","6/6","結論：值得試，但要抽查")
    for i,(a,b) in enumerate(items):
        s += f'<div class=abs data-o=i{i+1} style="left:64px;top:{340+i*230}px;width:952px"><div class=item><div class=n>{i+1}</div><p>{a}<small>{b}</small></p></div></div>'
    s += '<div class=abs data-o=cta style="left:64px;top:1060px;width:952px"><div class=note><b>完整測試條件</b>放在留言第一則。追蹤看下一款實測。</div></div>'
    return s + disc(72)
CHECK = """()=>{const els=[...document.querySelectorAll('[data-o]')].map(e=>{const r=e.getBoundingClientRect();return {o:e.dataset.o,inn:e.dataset.in||'',x:r.left,y:r.top,w:r.right,h:r.bottom}});
const ov=[],gap=[];for(let i=0;i<els.length;i++)for(let j=i+1;j<els.length;j++){const a=els[i],b=els[j];
if(a.inn===b.o||b.inn===a.o)continue;
const gx=Math.max(a.x-b.w,b.x-a.w),gy=Math.max(a.y-b.h,b.y-a.h),g=Math.max(gx,gy);
if(g<0)ov.push(a.o+'×'+b.o);else if(g<24)gap.push(a.o+'×'+b.o+' '+Math.round(g)+'px')}
const W=document.body.clientWidth,H=document.body.clientHeight;
const oob=els.filter(e=>e.x<0||e.y<0||e.w>W||e.h>H).map(e=>e.o);
const minDisc=Math.min(...[...document.querySelectorAll('.disc')].map(e=>parseFloat(getComputedStyle(e).fontSize)));
return {n:els.length,overlap:ov,gap24:gap,oob,discFont:minDisc}}"""
def page(body,W,H): return f"<html><head><meta charset=utf-8><style>{CSS%dict(t,W=W,H=H)}</style></head><body>{body}</body></html>"
os.makedirs("html",exist_ok=True)
for n,W,H,b in [("A_cover",1080,1350,cover(False)),("A_reels",1080,1920,cover(True)),("A_shot",1080,1350,shot()),("A_table",1080,1350,table()),("A_end",1080,1350,end())]:
    open(f"html/{n}.html","w").write(page(b,W,H))
open("check_a.js.txt","w").write(CHECK)
