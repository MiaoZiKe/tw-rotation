import os, glob, sys
sys.path.insert(0, os.path.dirname(__file__))
from marks import DIRS
from playwright.sync_api import sync_playwright
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
FONT=f"""@font-face{{font-family:T;font-weight:900;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
@font-face{{font-family:T;font-weight:700;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-700-normal.woff2')}}
*{{box-sizing:border-box}}body{{margin:0;font-family:T,Inter,sans-serif;color:#1F2A44;background:#fff}}"""
def img(f,w=None,h=None,extra=''): return f'<img src="file://{OUT}/{f}" {"width=%d"%w if w else ""} {"height=%d"%h if h else ""} style="display:block;{extra}">'
def overview():
    rows=''
    for did,name,idea,font,art,hz,keys in DIRS:
        rows+=f'''<div class="r"><div class="lab"><b>{did}　{name}</b><span>{idea}</span><i>字型：{font}</i></div>
        <div class="c">{img(f"{did}_icon512.png",132)}</div><div class="c ig">{img(f"{did}_ig110.png")}</div><div class="c ig">{img(f"{did}_ig40.png")}</div>
        <div class="c hz">{img(f"{did}_horizontal.png",330,110,"border:1px solid #eee;border-radius:8px")}</div></div>'''
    return f'''<html><style>{FONT}
    .h{{padding:26px 34px 8px}} h1{{margin:0;font-size:30px;font-weight:900}} .h p{{margin:6px 0 0;color:#666;font-size:14px}}
    .th{{display:flex;padding:14px 34px 6px;border-bottom:2px solid #1F2A44;font-size:13px;font-weight:700;color:#555}}
    .th div,.r div{{flex:none}} .lab{{width:340px;padding-right:20px}} .c{{width:150px;display:flex;align-items:center;justify-content:center}} .c.hz{{width:370px}}
    .r{{display:flex;padding:14px 34px;border-bottom:1px solid #e6e6e6;align-items:center;min-height:164px}}
    .lab b{{display:block;font-size:20px;font-weight:900}} .lab span{{display:block;font-size:14px;margin-top:6px;line-height:1.5;color:#333}} .lab i{{display:block;font-size:12px;margin-top:6px;color:#888;font-style:normal}}
    </style><body><div class="h"><h1>哩股哩股 LOGO 第六輪：10 種新風格（F01～F10）</h1><p>每列由左至右：方形圖示（縮到 132px 顯示）、IG 圓形 110px、IG 圓形 40px（皆為實際像素、白底、未放大）、橫式 LOGO。</p></div>
    <div class="th"><div class="lab">風格與理念</div><div class="c">方形</div><div class="c">IG 110</div><div class="c">IG 40</div><div class="c hz">橫式</div></div>{rows}</body></html>'''
def shot(html,path,w):
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0],args=['--allow-file-access-from-files'])
        pg=b.new_page(viewport={'width':w,'height':800})
        open('/tmp/claude-0/w/tmp.html','w').write(html); pg.goto('file:///tmp/claude-0/w/tmp.html'); pg.wait_for_timeout(800)
        pg.screenshot(path=path,full_page=True); b.close()
if __name__=='__main__': shot(overview(),OUT+'/overview.png',1290)
