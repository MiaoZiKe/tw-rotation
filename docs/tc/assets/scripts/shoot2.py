"""剖析圖 2D 截圖 → 1080x1350 素材。
去掉導覽列與比比；卡片裡的「台廠／台股」膠囊與文字整個拿掉（法遵：不標客戶對應）；卡片逐張拿掉到放得進 1350 為止，
被拿掉的卡片，圖上對應的編號圈一起隱藏。
用法：python shoot2.py <輸出目錄> [slot,...]"""
import io, json, os, sys, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

ROOT = os.environ.get("TC_SITE_ROOT") or "/tmp/claude-0/-home-user-tw-rotation/1662701f-8abb-57a6-b66d-4e0b4e90dd73/scratchpad/wt-sitefix"
OUT = sys.argv[1]
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
os.makedirs(OUT, exist_ok=True)


class Q(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


srv = ThreadingHTTPServer(("127.0.0.1", 8794), partial(Q, directory=ROOT + "/site"))
threading.Thread(target=srv.serve_forever, daemon=True).start()
LIST = [("ai_adv_packaging", "semiconductor", "CoWoS 先進封裝剖面"), ("foundry", "semiconductor", "晶圓代工：電晶體與製程迴圈"),
        ("hbm", "semiconductor", "HBM 堆疊記憶體"), ("silicon_wafer", "semiconductor", "矽晶圓：從熔湯到鏡面"),
        ("ai_server", "ai_server", "AI 伺服器機櫃與運算托盤"), ("pcb_rigid", "ai_server", "PCB 硬板多層剖面"),
        ("ic_substrate", "ai_server", "IC 載板 ABF 增層剖面"), ("air_cooling", "ai_server", "氣冷散熱模組"),
        ("liquid_cooling", "ai_server", "液冷：冷板與熱管"), ("server_psu", "ai_server", "伺服器電源路徑"),
        ("ai_interconnect", "ai_server", "高速互連連接器"), ("switch_wireless", "ai_server", "交換器板卡與光模組"),
        ("mlcc", "electronics", "MLCC 疊層剖析")]
PRE = ("window.TW_THEME_LEGACY=1;try{localStorage.setItem('tw.theme','light');"
       "localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'test'}));localStorage.setItem('tw.tour','*');}catch(e){}")
HIDE = "#bibi,.bibi,[id*=bibi],[class*=bibi],[class*=cservice],.csfab,#csBtn,.dgchips{display:none!important}.dim,.dgc.dim,svg.dg [data-seg].dim,svg.dgsw [data-seg].dim{opacity:1!important}"
JS = """(maxH)=>{
  const g=document.querySelector('#dgBody .dggrid'); if(!g) return {err:'nogrid'};
  // 1) 公司名／股票膠囊整個拿掉
  g.querySelectorAll('a[href^="#stock"]').forEach(a=>a.remove());
  g.querySelectorAll('.none,.stk,.stocks,.cos').forEach(e=>e.remove());
  // 卡片裡的公司膠囊列（含「台股無直接對應」那顆）整列拿掉：卡片本身保留標題與一句說明
  g.querySelectorAll('.dgchips').forEach(e=>e.remove());
  // 公司膠囊被拿掉後留下的「+2」之類的剩餘計數
  g.querySelectorAll('i,span,b,small,div,s,em').forEach(e=>{ if(e.children.length===0 && /^\s*\+\s*\d+\s*$/.test(e.textContent) && !e.classList.contains('no')) e.remove(); });
  g.querySelectorAll('.dgc').forEach(c=>{ [...c.querySelectorAll('i,span,div')].forEach(e=>{ if(/台股|台廠|台灣廠|代號|\\b\\d{4}\\b/.test(e.textContent) && e.children.length===0 && !e.classList.contains('no')) e.remove(); }); });
  g.querySelectorAll('g.dgfold').forEach(f=>f.style.display='none');
  // S3：頁首導言（標題＋說明段）整塊拿掉，只留主剖面與編號卡片；導言提到的「右欄／收在下面」在截圖裡都不存在
  g.querySelectorAll('.dghead').forEach(e=>e.style.display='none');
  const noOf=(c)=>c.querySelector('.no')?c.querySelector('.no').textContent.trim():'';
  const hidden=[];
  const hideCard=(c)=>{ hidden.push(noOf(c)); c.style.display='none'; };
  // S1／S2：含「誰做的／族群名單」「台股…」「無直接對應」或公司名的卡片，**整張卡片**隱藏（不是只清內文留一個空框）
  const CARDBAD=/為什麼點零件|外商|誰做的|族群名單|名單比這張|台股|台廠|無直接對應|台積電|日月光|聯發科|聯電|台達|廣達|緯創|緯穎|鴻海|欣興|南電|景碩|環球晶|台勝科|合晶|嘉晶|奇鋐|雙鴻|健策/;
  [...g.querySelectorAll('.dgc')].forEach(c=>{ if(c.style.display!=='none' && CARDBAD.test(c.textContent)) hideCard(c); });
  const cards=[...g.querySelectorAll('.dgc')].filter(c=>c.style.display!=='none').sort((a,b)=>(+a.style.order||0)-(+b.style.order||0));
  // 預算：主剖面「實際內容」高（canvas 上下空白之後會被裁掉）＋卡片清單高
  const sv=g.querySelector('.dgcanvas svg'), cdl=g.querySelector('.dgcards');
  const cH=()=>{ const bb=sv.getBBox(), vb=sv.viewBox.baseVal, k=sv.getBoundingClientRect().width/(vb&&vb.width||1); return bb.height*k+32; };
  const H=()=>cH()+(cdl?cdl.getBoundingClientRect().height:0)+12;
  let guard=0;
  // 保留清單：圖上有一個零件沒有別的標示（CoWoS 的 SoIC 上層晶粒），對應卡片（07）一定要留
  const KEEP=(window.__keep||[]);
  while(H()>maxH && cards.length && guard++<60){ let i=cards.length-1; while(i>=0 && KEEP.includes(noOf(cards[i]))) i--; if(i<0) break; const c=cards.splice(i,1)[0]; hideCard(c); }
  g.querySelectorAll('svg.dg g.anc').forEach(a=>{ const t=(a.textContent||'').trim(); if(hidden.includes(t)) a.style.display='none'; });
  const left=cards.map(c=>c.querySelector('.no')?c.querySelector('.no').textContent.trim():'');
  const txt=g.innerText.replace(/\\s+/g,' ');
  const CR=/台股|台廠|無直接對應|台積電|日月光|聯發科|聯電|台達|廣達|緯創|緯穎|鴻海|欣興|南電|景碩|環球晶|台勝科|合晶|嘉晶|SK ?hynix|海力士|Micron|美光|Samsung|三星|NVIDIA|輝達|Broadcom|Intel|英特爾|ASML|Amkor|力成|奇鋐|雙鴻|健策|信越|SUMCO|Shin-Etsu|GlobalWafers|TSMC|Nvidia|GB200|H100|Blackwell|Hopper/;
  const cut=[];
  g.querySelectorAll('text,tspan,span,i,b,div,p').forEach(e=>{ if(e.children.length===0 && CR.test(e.textContent) && e.getClientRects().length>0){ cut.push(e.textContent.trim().slice(0,40)); e.style.visibility='hidden'; } });
  const vis=[...g.querySelectorAll('text,span,i,b,div,p')].filter(e=>e.children.length===0&&e.getClientRects().length>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden').map(e=>e.textContent.trim()).join(' | ');
  const names=Object.values((window.Link&&window.Link.cname)||{}).filter(n=>n&&n.length>=2);
  const leaks=[...new Set(names.filter(n=>vis.includes(n)))];
  const codes=[...new Set(vis.match(/\\b[1-9]\\d{3}\\b/g)||[])];
  // 重疊檢查：可見文字（SVG text／HTML 葉節點）兩兩比外框，交集 >2px 就記一筆
  const tx=[...g.querySelectorAll('text,span,i,b,div,p,s,u')].filter(e=>e.children.length===0&&(e.textContent||'').trim()&&e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[style*="display: none"]')).map(e=>({e,r:e.getBoundingClientRect(),t:e.textContent.trim().slice(0,14)})).filter(o=>o.r.width>1&&o.r.height>1);
  const ov=[]; for(let i=0;i<tx.length;i++)for(let j=i+1;j<tx.length;j++){const a=tx[i].r,b=tx[j].r; const ox=Math.min(a.right,b.right)-Math.max(a.left,b.left), oy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top); if(ox>2&&oy>2) ov.push([tx[i].t,tx[j].t,Math.round(ox),Math.round(oy)]);}
  return {ov,h:H(),w:g.getBoundingClientRect().width,hidden,left,txt:vis,leaks,codes,cut};
}"""

summary = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    for slot, chain, title in LIST:
        if ONLY and slot not in ONLY: continue
        pg = b.new_page(viewport={"width": 820, "height": 1000}, device_scale_factor=2)
        pg.add_init_script(PRE)
        pg.goto(f"http://127.0.0.1:8794/index.html#industry/{chain}/dg/{slot}", wait_until="networkidle")
        pg.wait_for_timeout(3000)
        pg.add_style_tag(content=HIDE)
        w = pg.evaluate("document.querySelector('#dgBody .dggrid')?document.querySelector('#dgBody .dggrid').getBoundingClientRect().width:0")
        if not w:
            print(slot, "NO GRID"); pg.close(); continue
        maxH = 1180 / (1000 / w)
        pg.evaluate("k=>{window.__keep=k}", {"ai_adv_packaging": ["07"]}.get(slot, []))
        r = pg.evaluate(JS, maxH)
        pg.wait_for_timeout(400)
        # S3：主剖面（canvas）與卡片清單各截一張、直向疊起來；canvas 上下空白自動裁掉
        cv_png = pg.query_selector("#dgBody .dgcanvas").screenshot()
        cd_el = pg.query_selector("#dgBody .dgcards")
        a = Image.open(io.BytesIO(cv_png)).convert("RGB")
        bg = a.getpixel((2, 2))
        diff = ImageChops.difference(a, Image.new("RGB", a.size, bg)).convert("L").point(lambda v: 255 if v > 14 else 0)
        bb = diff.getbbox()
        if bb:
            a = a.crop((0, max(0, bb[1] - 16), a.width, min(a.height, bb[3] + 16)))
        parts_ = [a]
        if cd_el and cd_el.bounding_box() and cd_el.bounding_box()["height"] > 4:
            parts_.append(Image.open(io.BytesIO(cd_el.screenshot())).convert("RGB"))
        im = Image.new("RGB", (max(x.width for x in parts_), sum(x.height for x in parts_) + 12 * (len(parts_) - 1)), bg)
        yy = 0
        for x in parts_:
            im.paste(x, (0, yy)); yy += x.height + 12
        im.save(f"{OUT}/{slot}_raw.png")
        # 另存「只有主剖面、沒有編號圈」的版本（B2 之類只取剖面的版型用）
        pg.add_style_tag(content="g.anc{display:none!important}")
        pg.wait_for_timeout(200)
        c2 = Image.open(io.BytesIO(pg.query_selector("#dgBody .dgcanvas").screenshot())).convert("RGB")
        bg2 = c2.getpixel((2, 2))
        bb2 = ImageChops.difference(c2, Image.new("RGB", c2.size, bg2)).convert("L").point(lambda v: 255 if v > 14 else 0).getbbox()
        if bb2: c2 = c2.crop((0, max(0, bb2[1] - 16), c2.width, min(c2.height, bb2[3] + 16)))
        c2.save(f"{OUT}/{slot}_canvas.png")
        summary[slot] = dict(ov=r["ov"], cut=r["cut"], leaks=r["leaks"], codes=r["codes"], title=title, w=r["w"], h=r["h"], hidden=r["hidden"], left=r["left"], txt=r["txt"][:1500])
        print(slot, "文字重疊", len(r["ov"]), r["ov"][:4], int(r["w"]), int(r["h"]), "cards left", len(r["left"]), "hidden", len(r["hidden"]), "公司名", r["leaks"], "四位數", r["codes"])
        pg.close()
    b.close()
json.dump(summary, open(f"{OUT}/_summary.json", "w"), ensure_ascii=False, indent=1)
srv.shutdown()
