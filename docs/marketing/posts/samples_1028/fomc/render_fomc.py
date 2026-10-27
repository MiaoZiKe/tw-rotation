"""FOMC 事件前一天 IG 輪播 5 張（1080×1350）。用法：python render_fomc.py <輸出資料夾>
數字全由程式渲染；逐張重疊檢查，最後印「重疊檢查：程式 N 張 M 筆」。"""
import sys, io, os, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "scripts"))
from social_theme import logo_uri, TOKENS as T  # noqa
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;font-family:'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{T['ink']};background:{T['bg']};background-image:linear-gradient(rgba(10,106,134,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(10,106,134,.05) 1px,transparent 1px);background-size:32px 32px;padding:36px 40px 40px;display:flex;flex-direction:column;gap:16px}}
.num{{font-family:Inter,sans-serif;font-variant-numeric:tabular-nums}}
.hd{{height:88px;display:flex;align-items:center;gap:18px;border-bottom:2px solid {T['accent']};flex:none}}
.hd img{{width:72px;height:72px;border-radius:17px}}
.pill{{background:#5145C8;color:#fff;font-weight:800;font-size:28px;padding:6px 18px;border-radius:12px}}
.ht{{font-size:52px;font-weight:800}}
.hdate{{margin-left:auto;font-size:34px;font-weight:600;color:{T['ink2']}}}
.card{{flex:1;background:{T['panel']};border:1.5px solid {T['line']};border-radius:10px;padding:44px 44px;display:flex;flex-direction:column;justify-content:space-between;gap:20px;overflow:hidden}}
.blk{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:28px}}
.bibi{{align-self:center;object-fit:contain}}
.big{{font-size:104px;font-weight:800;line-height:1.25}} .mid{{font-size:60px;font-weight:800;line-height:1.3}}
.sub{{font-size:42px;font-weight:600;color:{T['ink2']};line-height:1.5}} .acc{{color:{T['accent']}}}
.unit{{font-size:32px;font-weight:600;color:{T['ink3']}}}
.tl{{display:flex;flex-direction:column;gap:0;padding-left:20px}}
.nd{{display:flex;align-items:center;gap:28px;height:170px;position:relative}}
.nd .dot{{width:44px;height:44px;border-radius:50%;background:{T['accent']};flex:none;position:relative;z-index:2}}
.nd.q .dot{{background:#fff;border:6px solid #F5B73B}}
.nd:not(:last-child)::after{{content:'';position:absolute;left:20px;top:107px;width:4px;height:156px;background:{T['line2']}}}
.nd .d{{font-size:34px;font-weight:700;color:{T['ink3']};width:210px;flex:none}}
.nd .v{{font-size:64px;font-weight:800}} .nd .n{{font-size:34px;font-weight:600;color:{T['ink2']}}}
.row{{display:flex;align-items:center;gap:22px;height:150px}}
.nm{{font-size:52px;font-weight:800;width:190px}}
.track{{flex:1;height:60px;background:{T['panel2']};border:1.5px solid {T['line']};border-radius:6px}}
.bar{{height:100%;border-radius:5px}}
.val{{font-size:64px;font-weight:800;width:170px;text-align:right}}
.li{{display:flex;align-items:center;gap:26px;min-height:128px;border-bottom:1.5px solid {T['line']}}}
.li:last-child{{border-bottom:none}}
.li .k{{font-size:52px;font-weight:800;color:{T['accent']};width:70px}}
.li .t{{font-size:46px;font-weight:800;line-height:1.3}} .li .s{{font-size:34px;font-weight:600;color:{T['ink2']};margin-top:4px}}
"""
def bibi(name,h):
    f=ROOT/'docs'/'anim'/'bibi_library'/name/'key.png'
    im=Image.open(f).convert('RGBA'); im=im.crop(im.getchannel('A').point(lambda a:255 if a>8 else 0).getbbox())
    b=io.BytesIO(); im.save(b,'PNG')
    return f'<img class="bibi" style="height:{h}px" src="data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}">'
def hd(): return f'<div class="hd"><img src="{logo_uri()}"><div class="pill">總經</div><div class="ht">FOMC 前哨</div><div class="hdate num">10/28 事件前</div></div>'
def node(d,v,n,q=False): return f'<div class="nd{" q" if q else ""}"><div class="dot"></div><div class="d num">{d}</div><div><div class="v num">{v}</div><div class="n">{n}</div></div></div>'
def row(nm,v,col,lab=None): return f'<div class="row"><div class="nm">{nm}</div><div class="track"><div class="bar" style="width:{v}%;background:{col}"></div></div><div class="val num">{lab or str(v)+"%"}</div></div>'
def li(k,t,s,w=70): return f'<div class="li"><div class="k num" style="width:{w}px;white-space:nowrap">{k}</div><div><div class="t">{t}</div><div class="s">{s}</div></div></div>'
S=[
 '<div class="mid acc">美國聯準會 FOMC 利率決議</div><div class="big">明天凌晨<br>公布</div><div class="sub">台灣 10/29（四）02:00 公布<br>02:30 記者會</div>',
 '<div class="mid">利率走到哪了？</div><div class="tl">'+node("2025/12","3.50–3.75%","降息 1 碼")+node("2026/09","3.75–4.00%","升息 1 碼（12 比 0）")+node("2026/10/28","？","明天公布",True)+'</div><div class="unit">聯邦基金利率目標區間</div>',
 '<div class="mid">市場怎麼定價？</div>'+row("持平",83,T['accent'])+row("升息",17,'#8F5600')+row("降息",1,T['flat'],"≈0%")+'<div class="unit">CME FedWatch 約 10/20 資料，隨時變動</div>',
 '<div class="mid">明天看這 4 件事</div>'+li("1","聲明措辭","對通膨與就業的描述有沒有改")+li("2","投票結果","有沒有人投反對票")+li("3","02:30 記者會","對 12 月的說法")+li("4","本次無點陣圖","不是經濟預測（SEP）會議"),
 '<div class="mid">一般來說，影響怎麼傳導？</div>'+li("美元","利率預期↑","通常偏強",190)+li("美債","殖利率","跟著利率預期走",190)+li("科技股","估值折現率","利率預期↑ 通常壓力較大",190)+'<div class="unit">只講傳導管道，不代表明天一定如此</div>',
]
B=[("calendar",470),("clock",300),("face_think",430),("magnifier",300),("globe",200)]
S2=[f'<div class="blk">{b}</div>'+bibi(n,h) for b,(n,h) in zip(S,B)]
CHECK="""()=>{const els=[...document.body.querySelectorAll('*')].filter(e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())||e.classList.contains('bar')||e.tagName==='IMG'||e.classList.contains('dot'));
const R=els.map(e=>({e,r:e.getBoundingClientRect()}));let bad=[];
for(let i=0;i<R.length;i++){const a=R[i];if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+a.e.className);
 if(a.e.scrollWidth>a.e.clientWidth+1&&a.e.clientWidth>0)bad.push('溢出:'+a.e.className);
 for(let j=i+1;j<R.length;j++){const b=R[j];if(a.e.contains(b.e)||b.e.contains(a.e))continue;
 const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);if(w>1&&h>1)bad.push('重疊:'+a.e.className+'/'+b.e.className);}}
const c=document.querySelector('.card');if(c.scrollHeight>c.clientHeight+1)bad.push('卡片內容超高');return bad;}"""
tot=0
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None); pg=b.new_page(viewport={"width":1080,"height":1350})
    for i,body in enumerate(S2,1):
        pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{hd()}<div class='card'>{body}</div></body></html>"); pg.wait_for_timeout(200)
        bad=pg.evaluate(CHECK); tot+=len(bad); print(i,"問題:",bad)
        Image.open(io.BytesIO(pg.screenshot(clip={"x":0,"y":0,"width":1080,"height":1350}))).convert("RGB").save(OUT/f"{i}.jpg",quality=92)
    b.close()
print(f"重疊檢查：程式 {len(S2)} 張 {tot} 筆")
