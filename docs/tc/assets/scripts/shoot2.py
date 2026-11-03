"""剖析圖 2D 截圖 → 1080x1350 素材。
去掉導覽列與比比；卡片裡的「台廠／台股」膠囊與文字整個拿掉（法遵：不標客戶對應）；卡片逐張拿掉到放得進 1350 為止，
被拿掉的卡片，圖上對應的編號圈一起隱藏。
用法：python shoot2.py <輸出目錄> [slot,...]"""
import io, json, os, sys, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = "/home/user/tw-rotation/.claude/worktrees/agent-a269082c5aeb4fe8e"
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
HIDE = "#bibi,.bibi,[id*=bibi],[class*=bibi],[class*=cservice],.csfab,#csBtn{display:none!important}"
JS = """(maxH)=>{
  const g=document.querySelector('#dgBody .dggrid'); if(!g) return {err:'nogrid'};
  // 1) 公司名／股票膠囊整個拿掉
  g.querySelectorAll('a[href^="#stock"]').forEach(a=>a.remove());
  g.querySelectorAll('.none,.stk,.stocks,.cos').forEach(e=>e.remove());
  g.querySelectorAll('.dgc').forEach(c=>{ [...c.querySelectorAll('i,span,div')].forEach(e=>{ if(/台股|台廠|台灣廠|代號|\\b\\d{4}\\b/.test(e.textContent) && e.children.length===0 && !e.classList.contains('no')) e.remove(); }); });
  g.querySelectorAll('g.dgfold').forEach(f=>f.style.display='none');
  const cards=[...g.querySelectorAll('.dgc')].sort((a,b)=>(+a.style.order||0)-(+b.style.order||0));
  const hidden=[];
  const H=()=>g.getBoundingClientRect().height;
  let guard=0;
  while(H()>maxH && cards.length && guard++<60){ const c=cards.pop(); hidden.push(c.querySelector('.no')?c.querySelector('.no').textContent.trim():''); c.style.display='none'; }
  g.querySelectorAll('svg.dg g.anc').forEach(a=>{ const t=(a.textContent||'').trim(); if(hidden.includes(t)) a.style.display='none'; });
  const left=cards.map(c=>c.querySelector('.no')?c.querySelector('.no').textContent.trim():'');
  const txt=g.innerText.replace(/\\s+/g,' ');
  const CR=/台股|台廠|台積電|日月光|聯發科|聯電|台達|廣達|緯創|緯穎|鴻海|欣興|南電|景碩|環球晶|台勝科|合晶|嘉晶|SK ?hynix|海力士|Micron|美光|Samsung|三星|NVIDIA|輝達|Broadcom|Intel|英特爾|ASML|Amkor|力成|奇鋐|雙鴻|健策|信越|SUMCO|Shin-Etsu|GlobalWafers|TSMC|Nvidia|GB200|H100|Blackwell|Hopper/;
  const cut=[];
  g.querySelectorAll('text,tspan,span,i,b,div,p').forEach(e=>{ if(e.children.length===0 && CR.test(e.textContent) && e.getClientRects().length>0){ cut.push(e.textContent.trim().slice(0,40)); e.style.visibility='hidden'; } });
  const vis=[...g.querySelectorAll('text,span,i,b,div,p')].filter(e=>e.children.length===0&&e.getClientRects().length>0&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden').map(e=>e.textContent.trim()).join(' | ');
  const names=Object.values((window.Link&&window.Link.cname)||{}).filter(n=>n&&n.length>=2);
  const leaks=[...new Set(names.filter(n=>vis.includes(n)))];
  const codes=[...new Set(vis.match(/\\b[1-9]\\d{3}\\b/g)||[])];
  return {h:H(),w:g.getBoundingClientRect().width,hidden,left,txt:vis,leaks,codes,cut};
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
        r = pg.evaluate(JS, maxH)
        pg.wait_for_timeout(400)
        png = pg.query_selector("#dgBody .dggrid").screenshot()
        im = Image.open(io.BytesIO(png)).convert("RGB")
        im.save(f"{OUT}/{slot}_raw.png")
        summary[slot] = dict(cut=r["cut"], leaks=r["leaks"], codes=r["codes"], title=title, w=r["w"], h=r["h"], hidden=r["hidden"], left=r["left"], txt=r["txt"][:1500])
        print(slot, int(r["w"]), int(r["h"]), "cards left", len(r["left"]), "hidden", len(r["hidden"]), "公司名", r["leaks"], "四位數", r["codes"])
        pg.close()
    b.close()
json.dump(summary, open(f"{OUT}/_summary.json", "w"), ensure_ascii=False, indent=1)
srv.shutdown()
