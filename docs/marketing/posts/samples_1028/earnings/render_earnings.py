"""公司法說解析樣張（台積電 3Q26，2026-10-15 法說）IG 輪播 6 張 1080x1350：深藍＋白底財經數據卡。
數字全部由本檔程式渲染。用法：python render_earnings.py <輸出資料夾>
輸出 JPEG 並逐張做重疊／出界／溢出檢查，最後印「重疊檢查：程式 N 張 M 筆」。"""
import sys, io
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
NAVY, BLUE, INK, GREY, LINE, PALE = "#0B2447", "#1F5FB8", "#0A1B2A", "#4A6377", "#CFDDE8", "#EEF3F9"
CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;height:1350px;font-family:'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{INK};background:#fff;display:flex;flex-direction:column}}
.num{{font-family:Inter,'DejaVu Sans',sans-serif;font-variant-numeric:tabular-nums}}
.hd{{height:150px;background:{NAVY};color:#fff;display:flex;align-items:center;gap:22px;padding:0 48px;flex:none}}
.tk{{font-size:34px;font-weight:800;background:#fff;color:{NAVY};padding:6px 20px;border-radius:10px}}
.ht{{font-size:50px;font-weight:800}}
.hd .d{{margin-left:auto;font-size:30px;font-weight:600;color:#BFD3F2}}
.main{{flex:1;padding:44px 48px 40px;display:flex;flex-direction:column;justify-content:space-between;gap:20px}}
.ft{{height:84px;background:{PALE};border-top:2px solid {LINE};display:flex;align-items:center;padding:0 48px;font-size:28px;color:{GREY};font-weight:600;flex:none}}
.lab{{font-size:40px;font-weight:700;color:{GREY}}}
.huge{{font-size:190px;font-weight:800;color:{NAVY};line-height:1.1}}
.big{{font-size:120px;font-weight:800;color:{NAVY};line-height:1.1}}
.mid{{font-size:56px;font-weight:800;color:{NAVY};line-height:1.35}}
.sub{{font-size:38px;font-weight:600;color:{GREY};line-height:1.5}}
.kpi{{border:2px solid {LINE};border-radius:14px;padding:26px 32px;background:{PALE};display:flex;flex-direction:column;gap:6px}}
.kv{{font-size:104px;font-weight:800;color:{NAVY};line-height:1.15}}
.kv small{{font-size:40px;color:{GREY};font-weight:700;margin-left:10px}}
.chg{{font-size:40px;font-weight:800;color:{BLUE}}}
.line{{display:flex;align-items:center;gap:20px;height:96px}}
.line .l{{font-size:38px;font-weight:700;color:{GREY};width:210px}}
.track{{flex:1;height:50px;background:{PALE};border:2px solid {LINE};border-radius:8px}}
.bar{{height:100%;background:{BLUE};border-radius:6px}}.bar.p{{background:#9DB8DE}}
.val{{font-size:54px;font-weight:800;width:190px;text-align:right;color:{NAVY}}}
table{{width:100%;border-collapse:collapse}}
th{{white-space:nowrap;font-size:32px;font-weight:700;color:#fff;background:{NAVY};padding:20px 20px;text-align:left}}
td{{white-space:nowrap;font-size:38px;font-weight:700;padding:30px 20px;border-bottom:2px solid {LINE};color:{INK}}}
td.n{{font-size:42px;font-weight:800;color:{NAVY}}}
.tag{{align-self:flex-start;font-size:32px;font-weight:800;background:{BLUE};color:#fff;padding:6px 22px;border-radius:10px}}
"""
def hd(tag, title): return f'<div class="hd"><div class="tk">2330 台積電</div><div class="ht">{title}</div><div class="d num">3Q26 · 10/15</div></div>'
def ft(t): return f'<div class="ft">{t}</div>'
def line(l, v, mx, txt, cls=""): return f'<div class="line"><div class="l">{l}</div><div class="track"><div class="bar {cls}" style="width:{v/mx*100:.1f}%"></div></div><div class="val num">{txt}</div></div>'
S = []
S.append(("法說解析", '<div class="tag">法說解析</div><div class="mid">台積電 2026 年第三季</div><div class="lab">每股盈餘（EPS）</div><div class="huge num">29.43</div><div class="chg">年增 68.7%（新台幣元）</div><div class="sub">毛利率 66.4%　營業利益率 58.7%<br>第四季美元營收指引 523～543 億</div>', "公司公布數字整理　資料日 2026-10-15"))
S.append(("營收與獲利", '<div class="kpi"><div class="lab">第三季營收（美元）</div><div class="kv num">467<small>億美元</small></div><div class="chg">季增 16.2%（約新台幣 1.49 兆）</div></div><div class="kpi"><div class="lab">稅後純益（歸屬母公司）</div><div class="kv num">7,631<small>億元</small></div><div class="chg">年增 68.7%</div></div><div class="kpi"><div class="lab">每股盈餘</div><div class="kv num">29.43<small>元</small></div><div class="chg">稅後純益率 51.1%</div></div>', "資料日 2026-10-15"))
S.append(("獲利率", '<div class="lab">毛利率</div>'+line("第二季",67.7,70,"67.7%","p")+line("第三季",66.4,70,"66.4%")+'<div class="lab">營業利益率</div>'+line("第三季",58.7,70,"58.7%")+'<div class="lab">稅後純益率</div>'+line("第三季",51.1,70,"51.1%")+'<div class="sub">毛利率季減 1.3 個百分點，財務長說明主因是 2 奈米量產初期的稀釋</div>', "資料日 2026-10-15"))
S.append(("第四季指引", '<div class="mid">第四季財測</div><table><tr><th>項目</th><th>公司指引</th><th>中間值</th></tr><tr><td>美元營收</td><td class="n num">523～543 億</td><td class="num">533 億</td></tr><tr><td>毛利率</td><td class="n num">65%～67%</td><td class="num">66%</td></tr><tr><td>營業利益率</td><td class="n num">56.5%～58.5%</td><td class="num">57.5%</td></tr><tr><td>匯率假設</td><td class="n num">31.8</td><td class="num">TWD/USD</td></tr></table><div class="sub">毛利率中間值較第三季再降約 0.4 個百分點，公司說明原因是 2 奈米爬坡與海外廠稀釋</div>', "資料日 2026-10-15"))
S.append(("資本支出與製程", '<div class="kpi"><div class="lab">第三季資本支出</div><div class="kv num">138<small>億美元</small></div><div class="chg">約新台幣 4,430 億元</div></div><div class="kpi"><div class="lab">2026 全年資本支出指引</div><div class="kv num">600～640<small>億美元</small></div><div class="chg">與前次法說相同</div></div><div class="kpi"><div class="lab">2 奈米占第三季晶圓營收</div><div class="kv num">8<small>%</small></div><div class="chg">2026 全年美元營收成長指引約 44%</div></div>', "資料日 2026-10-15"))
S.append(("管理層重點", '<div class="tag">管理層說法（報導摘述）</div><div class="mid" style="font-size:44px;line-height:1.6">・2026 全年美元營收成長指引上調至約 44%<br>・2026 至 2028 年資本支出，將比過去三年更顯著提高<br>・AI 相關需求仍高於供給（報導摘述）<br>・海外廠稀釋：五年期間後段約 3～4 個百分點</div><div class="sub">以上為公司說法的整理，不代表任何方向判斷</div>', "資料日 2026-10-15"))
CHECK = """() => {
 const els=[...document.body.querySelectorAll('*')].filter(e=>{
   const t=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
   return t||e.classList.contains('bar')||e.classList.contains('track');});
 const R=els.map(e=>({e,r:e.getBoundingClientRect()}));let bad=[];
 for(let i=0;i<R.length;i++){const a=R[i];
  if(a.r.left<0||a.r.top<0||a.r.right>1080||a.r.bottom>1350)bad.push('出界:'+a.e.className+a.e.tagName);
  if(a.e.scrollWidth>a.e.clientWidth+1&&a.e.clientWidth>0)bad.push('溢出:'+a.e.className+a.e.tagName);
  for(let j=i+1;j<R.length;j++){const b=R[j];
   if(a.e.contains(b.e)||b.e.contains(a.e))continue;
   const w=Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left),h=Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top);
   if(w>1&&h>1)bad.push('重疊:'+a.e.className+a.e.tagName+'/'+b.e.className+b.e.tagName);}}
 const m=document.querySelector('.main');if(m.scrollHeight>m.clientHeight+1)bad.push('main 溢出 '+m.scrollHeight+'>'+m.clientHeight);
 return bad;}"""
tot=0
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=__import__("os").environ.get("CHROMIUM") or None)
    pg=b.new_page(viewport={"width":1080,"height":1350})
    for i,(t,body,f) in enumerate(S,1):
        pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{hd(t,t)}<div class='main'>{body}</div>{ft(f)}</body></html>")
        pg.wait_for_timeout(200); bad=pg.evaluate(CHECK); tot+=len(bad); print(i,bad)
        Image.open(io.BytesIO(pg.screenshot(clip={"x":0,"y":0,"width":1080,"height":1350}))).convert("RGB").save(OUT/f"{i}.jpg",quality=92)
    b.close()
print(f"重疊檢查：程式 {len(S)} 張 {tot} 筆")
