import os, glob, sys
sys.path.insert(0, os.path.dirname(__file__))
from marks import DIRS
from playwright.sync_api import sync_playwright
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
FONT=f"""@font-face{{font-family:T;font-weight:900;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
@font-face{{font-family:T;font-weight:700;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-700-normal.woff2')}}
@font-face{{font-family:T;font-weight:500;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-500-normal.woff2')}}
*{{box-sizing:border-box}}body{{margin:0;font-family:T,Inter,sans-serif;color:#1F2A44;background:#fff}}"""
def img(f,w=None,h=None,extra=''): 
    return f'<img src="file://{OUT}/{f}" {"width=%d"%w if w else ""} {"height=%d"%h if h else ""} style="display:block;{extra}">'
def overview():
    rows=''
    for did,name,idea,art,hz,pal,font in DIRS:
        rows+=f'''<div class="r"><div class="lab"><b>{did[1]}　{name}</b><span>{idea}</span><i>字型：{font}</i></div>
        <div class="c">{img(f"{did}_A_icon512.png",128)}</div><div class="c">{img(f"{did}_B_icon512.png",128)}</div>
        <div class="c ig">{img(f"{did}_A_ig110.png")}</div><div class="c ig">{img(f"{did}_B_ig110.png")}</div>
        <div class="c ig">{img(f"{did}_A_ig40.png")}</div><div class="c ig">{img(f"{did}_B_ig40.png")}</div></div>'''
    return f'''<html><style>{FONT}
    .h{{padding:26px 34px 8px}} h1{{margin:0;font-size:30px;font-weight:900}} .h p{{margin:6px 0 0;color:#666;font-size:14px}}
    .th{{display:flex;padding:14px 34px 6px;border-bottom:2px solid #1F2A44;font-size:13px;font-weight:700;color:#555}}
    .th div,.r div{{flex:none}} .lab{{width:330px;padding-right:20px}} .c{{width:150px;display:flex;align-items:center;justify-content:center}}
    .r{{display:flex;padding:14px 34px;border-bottom:1px solid #e6e6e6;align-items:center;min-height:164px}}
    .lab b{{display:block;font-size:20px;font-weight:900}} .lab span{{display:block;font-size:14px;margin-top:6px;line-height:1.5;color:#333}} .lab i{{display:block;font-size:12px;margin-top:6px;color:#888;font-style:normal}}
    </style><body><div class="h"><h1>哩股哩股 LOGO 第五輪：8 種風格 × 2 套配色（16 組）</h1><p>每列由左至右：方形圖示 A／B（縮到 128px 顯示）、IG 圓形 110px A／B、IG 圓形 40px A／B。110／40 皆為實際像素、白底、未放大。A＝陽光糖果主色，B＝反相／異色方案。</p></div>
    <div class="th"><div class="lab">風格與理念</div><div class="c">方形 A</div><div class="c">方形 B</div><div class="c">IG 110 A</div><div class="c">IG 110 B</div><div class="c">IG 40 A</div><div class="c">IG 40 B</div></div>{rows}</body></html>'''
def profile(did,k,dark):
    bg='#101010' if dark else '#fff'; fg='#f3f5f7' if dark else '#101010'; mu='#777' if dark else '#999'; ln='#2a2a2a' if dark else '#e6e6e6'
    btn=('#f3f5f7','#101010') if dark else ('#101010','#fff')
    return f'''<div class="p" style="background:{bg};color:{fg};border-color:{ln}">
      <div class="top"><div><div class="nm">哩股哩股</div><div class="hd">ligu.ligu <span>threads.com</span></div></div>{img(f"{did}_{k}_ig110.png",72,72)}</div>
      <div class="bio">每天盤後 3 分鐘，看懂錢往哪個族群跑｜ETF 存股・資金輪動</div>
      <div class="fo" style="color:{mu}">1,284 位粉絲 · liguligu-puipui.com</div>
      <div class="bt"><div style="background:{btn[0]};color:{btn[1]}">追蹤</div><div style="border:1px solid {ln};color:{fg}">提及</div></div>
      <div class="tb" style="border-color:{ln}"><b style="border-bottom:2px solid {fg}">串文</b><span style="color:{mu}">回覆</span><span style="color:{mu}">轉發</span></div>
      <div class="post" style="border-color:{ln}">{img(f"{did}_{k}_ig40.png",36,36)}<div><b>哩股哩股</b> <small style="color:{mu}">2 小時</small><div style="font-size:14px;margin-top:3px">今天資金往 AI 伺服器族群集中，ETF 存股要看的三個數字 👇</div></div></div></div>'''
def detail():
    rows=''
    for did,name,idea,art,hz,pal,font in DIRS:
        rows+=f'<div class="r"><div class="lab"><b>{did[1]}　{name}</b><span>{idea}</span></div>'
        rows+=f'<div class="hz">{img(f"{did}_A_horizontal.png",440)}<div style="height:10px"></div>{img(f"{did}_B_horizontal.png",440)}</div>'
        rows+=f'<div class="pw">{profile(did,"A",False)}</div><div class="pw">{profile(did,"B",True)}</div></div>'
    return f'''<html><style>{FONT}
    .h{{padding:26px 34px 10px}} h1{{margin:0;font-size:30px;font-weight:900}} .h p{{margin:6px 0 0;color:#666;font-size:14px}}
    .r{{display:flex;padding:20px 34px;border-top:1px solid #ddd;align-items:center;gap:24px}} .lab{{width:150px;flex:none}} .lab b{{display:block;font-size:19px;font-weight:900}} .lab span{{display:block;font-size:13px;margin-top:6px;line-height:1.5;color:#444}}
    .hz{{flex:none}} .hz img{{border-radius:10px;border:1px solid #eee}} .pw{{flex:none}}
    .p{{width:350px;border:1px solid;border-radius:20px;padding:18px 18px 8px}} .top{{display:flex;justify-content:space-between;align-items:flex-start}}
    .top img{{border-radius:50%}} .nm{{font-size:23px;font-weight:900}} .hd{{font-size:14px;margin-top:4px}} .hd span{{font-size:11px;background:#8883;padding:2px 7px;border-radius:10px;margin-left:4px;color:#888}}
    .bio{{font-size:14px;line-height:1.5;margin-top:12px}} .fo{{font-size:13px;margin-top:8px}}
    .bt{{display:flex;gap:8px;margin-top:12px}} .bt div{{flex:1;text-align:center;padding:8px 0;border-radius:10px;font-size:14px;font-weight:700}}
    .tb{{display:flex;margin-top:12px;border-bottom:1px solid;font-size:14px}} .tb *{{flex:1;text-align:center;padding:9px 0}}
    .post{{display:flex;gap:10px;padding:12px 0;font-size:14px}} .post img{{border-radius:50%;flex:none}}
    </style><body><div class="h"><h1>哩股哩股 LOGO 第五輪：橫式 LOGO 與 Threads 個人頁模擬</h1><p>每列：橫式 LOGO（A 上、B 下）、Threads 個人頁（A 淺色模式、B 深色模式；頭像用 IG 110px 圓形、貼文頭像 36px）。</p></div>{rows}</body></html>'''
def shot(html,path,w):
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0],args=['--allow-file-access-from-files'])
        pg=b.new_page(viewport={'width':w,'height':800}); 
        open('/tmp/claude-0/w/tmp.html','w').write(html); pg.goto('file:///tmp/claude-0/w/tmp.html'); pg.wait_for_timeout(800)
        pg.screenshot(path=path,full_page=True); b.close()
if __name__=='__main__':
    shot(overview(),OUT+'/overview.png',1290)
    shot(detail(),OUT+'/overview_detail.png',1480)
