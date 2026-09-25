"""原型其餘分段的截圖（總覽的熱力圖／題材／候選／事件、市場寬度、集中度）＋ 每一段的整頁高度
（docs/mobile_v3_spec.md §4-2 的數字來源）。用法：python docs/mobile_v3_proto/shot_extra.py"""
import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import serve  # noqa: E402

OUT = str(HERE / '_shots')
os.makedirs(OUT, exist_ok=True)
serve.PORT = serve.PORT + 1
serve.serve(block=False)
U = f'http://127.0.0.1:{serve.PORT}/proto/index.html'
H = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in [(390, 844), (360, 780)]:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        pg.goto(U + '#ov'); pg.wait_for_timeout(800); pg.evaluate('localStorage.clear()'); pg.reload(); pg.wait_for_timeout(1500)
        for step, segs in [(0, ['足跡輪盤', '資金去向', '熱力圖', '熱門題材']), (1, ['大盤', '市場寬度', '法人買超']), (2, ['今日候選']), (3, ['今日事件'])]:
            pg.locator(f'.p-steps button[data-step="{step}"]').tap(); pg.wait_for_timeout(700)
            for sname in segs:
                pg.locator(f'.p-segs button[data-seg="{sname}"]').tap(); pg.wait_for_timeout(1200)
                H[f'總覽/{sname}@{w}'] = pg.evaluate('document.documentElement.scrollHeight')
                pg.screenshot(path=f'{OUT}/ovx_{step}_{sname}_{w}.png')
        pg.locator('#pNav button[data-go="flow"]').tap(); pg.wait_for_timeout(1500)
        for sname in ['輪動', '資金去向', '法人', '集中度']:
            pg.locator(f'.p-segs button[data-seg="{sname}"]').tap(); pg.wait_for_timeout(1200)
            H[f'資金流向/{sname}@{w}'] = pg.evaluate('document.documentElement.scrollHeight')
        pg.locator('#pNav button[data-go="dg"]').tap(); pg.wait_for_timeout(2000)
        H[f'剖析圖@{w}'] = pg.evaluate('document.documentElement.scrollHeight')
        small = pg.evaluate("""(()=>{let n=0;document.querySelectorAll('body *').forEach(e=>{if(!e.childNodes.length)return;const t=[...e.childNodes].some(c=>c.nodeType===3&&c.textContent.trim());if(!t)return;if(e.closest('svg'))return;const r=e.getBoundingClientRect();if(!r.width)return;if(parseFloat(getComputedStyle(e).fontSize)<12)n++});return n})()""")
        H[f'剖析圖 HTML 字 <12px @{w}'] = small
        ctx.close()
print(json.dumps(H, ensure_ascii=False, indent=1))
json.dump(H, open(OUT + '/heights.json', 'w'), ensure_ascii=False, indent=1)
