# 頻道④療癒系版型樣張（純排版：不用 AI 圖、照片、比比）。產出 html/*.html，再由 render.js 截圖＋重疊檢查。
import os, json
FONT = "'Noto Serif TC','Source Han Serif TC','Songti TC','WenQuanYi Zen Hei',serif"   # 容器僅有文泉驛正黑，正式上線請換思源宋體
FONT_S = "'Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
ACCT = "頻道名稱待定"
BASE = "*{box-sizing:border-box;margin:0;padding:0}body{width:%dpx;height:%dpx;position:relative;overflow:hidden}.abs{position:absolute}"

def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]
    return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return round((la+.05)/(lb+.05), 2)

def page(name, W, H, css, body):
    html = f'<!doctype html><meta charset=utf-8><style>{BASE % (W,H)}{css}</style><body>{body}</body>'
    open(f'html/{name}.html', 'w', encoding='utf-8').write(html)

# ---------- A 紙與墨 ----------
A = dict(bg="#F4EEE2", ink="#2B2622", ink2="#5C544A", acc="#A23E2B", line="#CFC4B0")
tex = "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' seed='4'/><feColorMatrix values='0 0 0 0 .35  0 0 0 0 .28  0 0 0 0 .2  0 0 0 .09 0'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>\")"
cssA = f"""body{{background:{A['bg']} {tex};color:{A['ink']};font-family:{FONT}}}
.lab{{font-size:34px;font-weight:700;color:{A['acc']};letter-spacing:10px;line-height:1.4}}
.rule{{height:3px;background:{A['line']}}}
.q{{font-size:100px;font-weight:900;line-height:1.5;letter-spacing:4px}}
.q em{{font-style:normal;color:{A['acc']}}}
.sub{{font-size:42px;color:{A['ink2']};line-height:1.7;letter-spacing:2px}}
.no{{font-size:30px;color:{A['ink2']};letter-spacing:4px;line-height:1.4}}
.acct{{font-size:28px;color:{A['ink2']};text-align:right;letter-spacing:2px;line-height:1.4}}
.h{{font-size:62px;font-weight:900;line-height:1.4;letter-spacing:3px}}
.p{{font-size:44px;line-height:1.85;letter-spacing:2px}}.p b{{color:{A['acc']}}}
.seal{{border:4px solid {A['acc']};color:{A['acc']};font-size:34px;font-weight:900;padding:6px 14px;line-height:1.3;letter-spacing:2px}}"""
page('A_quote', 1080, 1350, cssA, f"""
<div class=abs data-o=lab style="left:96px;top:96px;width:600px"><div class=lab>今晚的一句話</div></div>
<div class=abs data-o=no style="right:96px;top:100px;width:240px;text-align:right"><div class=no style="text-align:right">No.001</div></div>
<div class="abs rule" style="left:96px;top:176px;width:888px"></div>
<div class=abs data-o=quote style="left:96px;top:300px;width:888px"><div class=q>今天沒有很好，<br>也<em>沒關係</em>。<br>你已經撐到<br>晚上了。</div></div>
<div class=abs data-o=sub style="left:96px;top:1000px;width:888px"><div class=sub>先放下手機，喝口水。<br>明天的事，明天再說。</div></div>
<div class="abs rule" style="left:96px;top:1200px;width:888px"></div>
<div class=abs data-o=acct style="right:96px;top:1236px;width:400px"><div class=acct>{ACCT}</div></div>
""")
page('A_inner', 1080, 1350, cssA, f"""
<div class=abs data-o=lab style="left:96px;top:96px;width:600px"><div class=lab>寫給累了的你</div></div>
<div class=abs data-o=no style="right:96px;top:100px;width:240px"><div class=no style="text-align:right">2 / 4</div></div>
<div class="abs rule" style="left:96px;top:176px;width:888px"></div>
<div class=abs data-o=title style="left:96px;top:250px;width:888px"><div class=h>撐著的時候，<br>也算在努力。</div></div>
<div class=abs data-o=body style="left:96px;top:520px;width:888px"><div class=p>不是每天都要<b>很有精神</b>。<br>有些日子，只是把該做的做完，<br>就已經用掉了全部力氣。<br><br>這樣的你，<b>不需要再道歉</b>。</div></div>
<div class=abs data-o=seal style="left:96px;top:1180px"><div class=seal>存起來，睡前看</div></div>
<div class=abs data-o=acct style="right:96px;top:1236px;width:400px"><div class=acct>{ACCT}</div></div>
""")

# ---------- B 暮色 ----------
B = dict(g1="#1E2444", g2="#3A3563", g3="#4B3F72", ink="#F4F1FB", ink2="#D5CEE8")
def cssB(H):
    return f"""body{{background:linear-gradient(170deg,{B['g1']} 0%,{B['g2']} 55%,{B['g3']} 100%);color:{B['ink']};font-family:{FONT_S}}}
.lab{{font-size:34px;font-weight:700;color:{B['ink2']};letter-spacing:8px;line-height:1.4}}
.txt{{font-size:52px;font-weight:500;line-height:2.0;letter-spacing:3px}}
.txt b{{font-weight:800}}
.big{{font-size:132px;font-weight:900;line-height:1.35;letter-spacing:6px}}
.sub{{font-size:46px;font-weight:500;color:{B['ink2']};line-height:1.8;letter-spacing:3px}}
.acct{{font-size:28px;color:{B['ink2']};text-align:right;letter-spacing:2px;line-height:1.4}}
.moon{{border-radius:50%;box-shadow:inset -26px -8px 0 0 {B['ink2']};width:84px;height:84px}}"""
page('B_post', 1080, 1350, cssB(1350), f"""
<div class=abs data-o=moon style="left:96px;top:96px"><div class=moon></div></div>
<div class=abs data-o=lab style="left:210px;top:118px;width:500px"><div class=lab>睡前一分鐘</div></div>
<div class=abs data-o=txt style="left:96px;top:300px;width:888px"><div class=txt>今天辛苦了。<br>那些沒做完的事，<br>不會在夜裡長腳跑掉。<br><b>先睡吧，</b><br><b>明天的你會接手。</b></div></div>
<div class=abs data-o=acct style="right:96px;top:1236px;width:400px"><div class=acct>{ACCT}</div></div>
""")
# Reels：上方 250、下方 340 為平台介面安全區，所有元素落在 250～1580
page('B_reels', 1080, 1920, cssB(1920), f"""
<div class=abs data-o=lab style="left:96px;top:300px;width:700px"><div class=lab>睡前一分鐘</div></div>
<div class=abs data-o=big style="left:96px;top:640px;width:888px"><div class=big>把今天<br>放下吧。</div></div>
<div class=abs data-o=sub style="left:96px;top:1100px;width:888px"><div class=sub>你已經做得<br>夠多了。</div></div>
<div class=abs data-o=acct style="right:96px;top:1480px;width:400px"><div class=acct>{ACCT}</div></div>
""")

# ---------- C 便利貼 ----------
C = dict(bg="#EFE7D8", ink="#2E2A22", ink2="#5A5346", notes=["#FFE98A", "#FFD3D9", "#D4EDC4", "#CFE6F5", "#FFE98A"])
items = ["喝一杯水，慢慢喝完", "肩膀放下來，深呼吸三次", "看窗外十秒鐘", "回訊息前，先停三秒", "準時下班，也是一種努力"]
rots = [-1.2, 1.0, -0.8, 1.2, -1.0]
cssC = f"""body{{background:{C['bg']};color:{C['ink']};font-family:{FONT_S}}}
.note{{width:888px;padding:0 40px;display:flex;align-items:center;gap:32px;box-shadow:0 8px 0 rgba(60,45,20,.12);}}
.box{{flex:none;width:52px;height:52px;border:5px solid {C['ink']};border-radius:8px}}
.t{{font-size:50px;font-weight:700;line-height:1.3;letter-spacing:2px}}
.title{{font-size:68px;font-weight:900;line-height:1.3;letter-spacing:3px}}
.tsub{{font-size:34px;font-weight:500;color:{C['ink2']};line-height:1.4;margin-top:8px;letter-spacing:2px}}
.foot{{font-size:36px;font-weight:600;color:{C['ink2']};line-height:1.5;letter-spacing:2px}}
.acct{{font-size:28px;color:{C['ink2']};text-align:right;letter-spacing:2px;line-height:1.4}}"""
body = f"""<div class=abs data-o=title style="left:96px;top:72px;width:888px;height:190px;background:#FFE98A;transform:rotate(-1deg);padding:34px 40px;box-shadow:0 8px 0 rgba(60,45,20,.12)"><div class=title>上班族小喘息清單</div><div class=tsub>每一格，三十秒就做得到</div></div>"""
for i, (t, r) in enumerate(zip(items, rots)):
    y = 310 + i*160
    body += f'<div class="abs note" data-o=n{i+1} style="left:96px;top:{y}px;height:128px;background:{C["notes"][i]};transform:rotate({r}deg)"><i class=box></i><div class=t>{t}</div></div>'
body += f"""<div class=abs data-o=foot style="left:96px;top:1180px;width:560px"><div class=foot>存起來，下班前看一眼。</div></div>
<div class=abs data-o=acct style="right:96px;top:1260px;width:400px"><div class=acct>{ACCT}</div></div>"""
page('C_list', 1080, 1350, cssC, body)

# ---------- 對比計算 ----------
pairs = {
 "A 內文 墨色/紙": (A['ink'], A['bg']), "A 次要字/紙": (A['ink2'], A['bg']), "A 朱紅強調/紙": (A['acc'], A['bg']),
 "B 主文/漸層最亮端": (B['ink'], B['g3']), "B 次要字/漸層最亮端": (B['ink2'], B['g3']),
 "C 墨色/黃貼": (C['ink'], C['notes'][0]), "C 墨色/粉貼": (C['ink'], C['notes'][1]), "C 墨色/綠貼": (C['ink'], C['notes'][2]), "C 墨色/藍貼": (C['ink'], C['notes'][3]),
 "C 次要字/米底": (C['ink2'], C['bg']),
}
res = {k: cr(*v) for k, v in pairs.items()}
json.dump(res, open('contrast.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
