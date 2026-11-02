# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
OUT='/home/user/tw-rotation/docs/brand/logo_1102'
D=[('d1_wordmark','① 純字標「哩」','只放一個「哩」字加一道紅色上漲短線；最簡、最好套進各種版面。','依據：金融 LOGO 通則「簡約、可縮放、單色可用」。弱點：筆畫多，40px 偏糊，沒有人味。'),
('d2_rotation','② 輪動環','三段箭頭繞成圓＝資金在族群間輪動，紅色那段向上＝領漲。','依據：金融標誌常用「流動、平衡」的抽象幾何；直接對應本站「資金輪動」。弱點：像回收／重新整理圖示。'),
('d3_li_rising','③ 「哩」＋上漲線','哩字下方接一條紅色上漲折線與箭頭，一眼是「股票」。','依據：上升曲線是金融通用符號；紅色＝台灣漲。弱點：折線與字兩件事，小尺寸線條變細。'),
('d4_bibi_mono','④ 比比單色幾何頭','比比簡化成圓＋橢圓＋三個點，幾乎一筆畫；淺底版加深藍描邊。','依據：Robinhood 式幾何極簡；臉在小尺寸比字好認（美術總監實測）。弱點：像小熊，少了毛球感。'),
('d5_seal','⑤ 圓章「哩股」','紅色印章、「哩股」直排、米白陰刻，台灣人對印章與紅色有親切感。','依據：我的判斷（搜尋未找到印章風格金融 LOGO 的資料）。弱點：像農民曆／店家章；40px 字糊但紅圓章辨識度高。'),
('d6_bibi_color','⑥ 彩色比比＋紅K棒（推薦）','毛球比比頭，頭頂一根紅 K 棒當呆毛；可愛、有人味、一個重點色。','依據：口袋證券有吉祥物「牛牛」、Webull 用牛（WebSearch 摘要，信心中）；Threads 靠人味。弱點：K 棒在 40px 只剩一小點。')]
def card(k,t,why,ev):
    return f'''<div class="card"><h2>{t}</h2><p class="why">{why}</p><p class="ev">{ev}</p>
<div class="row"><div class="big"><img src="{k}_dark.png" width="170"><span>深底</span></div><div class="big"><img src="{k}_light.png" width="170"><span>淺底</span></div>
<div class="sm"><img src="{k}_dark_circle110.png" width="110"><span>圓形 110px</span><img src="{k}_dark_circle40.png" width="40"><span>圓形 40px</span></div></div>
<div class="mocks">
<div class="mock l"><div class="top"><img src="{k}_dark_circle110.png" width="110"><div><b>哩股哩股</b><i>@liguligu0818</i><em>每天盤後 3 分鐘，看懂錢往哪個族群跑</em></div></div><div class="cm"><img src="{k}_dark_circle40.png" width="40"><span><b>哩股哩股</b> 今天錢往半導體跑</span></div></div>
<div class="mock d"><div class="top"><img src="{k}_dark_circle110.png" width="110"><div><b>哩股哩股</b><i>@liguligu0818</i><em>每天盤後 3 分鐘，看懂錢往哪個族群跑</em></div></div><div class="cm"><img src="{k}_dark_circle40.png" width="40"><span><b>哩股哩股</b> 今天錢往半導體跑</span></div></div>
</div></div>'''
strip=''.join(f'<div class="sc"><img src="{k}_dark_circle110.png" width="110"><img src="{k}_dark_circle40.png" width="40"><img src="{k}_light_circle110.png" width="110"><img src="{k}_light_circle40.png" width="40"></div>' for k,*_ in D)
html=f'''<!doctype html><meta charset="utf-8"><style>
*{{box-sizing:border-box}}body{{margin:0;background:#E9ECF2;font-family:"WenQuanYi Zen Hei","Inter",sans-serif;color:#14213D;padding:32px;width:2040px}}
h1{{font-size:30px;margin:0 0 6px}}.sub{{font-size:16px;margin:0 0 22px;color:#4a5568}}
.grid{{display:grid;grid-template-columns:repeat(3,640px);gap:24px}}
.card{{background:#fff;border-radius:16px;padding:20px;width:640px}}
h2{{font-size:22px;margin:0 0 6px}}.why{{font-size:15px;margin:0 0 4px;line-height:1.5}}.ev{{font-size:13px;color:#5a6577;margin:0 0 12px;line-height:1.5;min-height:40px}}
.row{{display:flex;gap:16px;align-items:flex-start}}.big,.sm{{display:flex;flex-direction:column;gap:4px;font-size:13px;color:#5a6577}}.sm img{{margin-bottom:2px}}
.mocks{{display:flex;gap:12px;margin-top:14px}}.mock{{width:290px;border-radius:12px;padding:14px;border:1px solid #d8dde6}}
.mock.l{{background:#fff}}.mock.d{{background:#101010;color:#f3f3f3;border-color:#101010}}
.top{{display:flex;gap:12px;align-items:center}}.top div{{display:flex;flex-direction:column;gap:2px;font-size:13px}}.top b{{font-size:17px}}.top i{{font-style:normal;color:#8a93a3}}.top em{{font-style:normal;font-size:13px;line-height:1.4;margin-top:3px}}
.cm{{display:flex;gap:8px;align-items:center;margin-top:10px;font-size:13px}}
.strip{{margin-top:24px;background:#fff;border-radius:16px;padding:20px}}.strip h2{{margin-bottom:12px}}.sr{{display:flex;gap:18px}}.sc{{display:grid;grid-template-columns:110px 40px;gap:10px;align-items:center;padding:12px;border-radius:12px;background:#f2f3f6;width:300px}}
.sc img:nth-child(3),.sc img:nth-child(4){{}}
</style><body><h1>哩股哩股 LOGO 六個方向（2026-11-02 設計美編）</h1><p class="sub">全部 SVG 手刻向量；每格含：深底／淺底大圖、IG 圓形 110px 與 40px、模擬 Threads／IG 個人頁（左淺色頁、右深色頁）與留言列。大頭貼一律以深底版為主版。</p>
<div class="grid">{''.join(card(*d) for d in D)}</div>
<div class="strip"><h2>六個方向並排：110px／40px，深底版與淺底版（實際像素，不放大）</h2><div class="sr">{strip}</div></div></body>'''
open(OUT+'/_overview.html','w',encoding='utf-8').write(html)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg=b.new_page(viewport={'width':2104,'height':1200})
    pg.goto('file://'+OUT+'/_overview.html'); pg.wait_for_timeout(500)
    pg.screenshot(path=OUT+'/overview.png',full_page=True); b.close()
