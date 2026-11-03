# 範例貼文成圖（企劃 11-04 三份文字；色票用 visual.md 的 A 暖霧紙本，邊距 88）。在 layouts/ 執行：python3 samples.py
import os, json
from gen import tex, BASE, FONT, FONT_S, FONT_W
S = '../samples/20261104'; ACCT = '把燈留著'   # 頻道名稱候選主推，Andy 未定名前僅為暫用
V = {'light': dict(bg='#FBF4EA', card='#FFFFFF', ink='#3B2F2A', ink2='#6E5A4E', acc='#A34A30', glow='#F3D9C2'),
     'dark':  dict(bg='#2B2622', card='#3A322D', ink='#F6EBDD', ink2='#C8A58E', acc='#C8A58E', glow='#4A3A30')}
def css(m):
    v = V[m]
    return f"""body{{background:var(--hl-bg);background-image:{tex};color:var(--hl-text);font-family:{FONT_S}}}
:root{{--hl-bg:{v['bg']};--hl-card:{v['card']};--hl-text:{v['ink']};--hl-sub:{v['ink2']};--hl-accent:{v['acc']};--hl-glow:{v['glow']}}}
.glow{{position:absolute;border-radius:50%;background:radial-gradient(closest-side,var(--hl-glow),transparent);opacity:.6}}
.ser{{font-family:{FONT}}}
.wk{{font-family:{FONT_W};font-weight:400}}
.s30{{font-size:30px;line-height:1.4;letter-spacing:4px;color:var(--hl-sub)}}
.s28{{font-size:28px;line-height:1.4;letter-spacing:2px;color:var(--hl-sub)}}
.main{{font-size:72px;font-weight:700;line-height:1.6;letter-spacing:.04em}}
.main64{{font-size:64px;font-weight:700;line-height:1.7;letter-spacing:.04em}}
.hook{{font-size:96px;font-weight:700;line-height:1.45;letter-spacing:.04em}}
.sub38{{font-size:38px;font-weight:500;line-height:1.75;color:var(--hl-sub)}}
.em{{color:var(--hl-accent);font-style:normal}}
.note{{background:var(--hl-glow);box-shadow:0 10px 0 rgba(59,47,42,.10)}}"""
def w(post, name, m, body, H=1350):
    d = f'{S}/{post}/html'; os.makedirs(d, exist_ok=True)
    open(f'{d}/{name}.html', 'w', encoding='utf-8').write(f'<!doctype html><meta charset=utf-8><style>{BASE % (1080,H)}{css(m)}</style><body>{body}</body>')
    p = f'{S}/{post}/manifest.json'; mf = json.load(open(p)) if os.path.exists(p) else {}
    mf[name] = H; json.dump(mf, open(p, 'w'))
foot = '<div class=abs data-o=acct style="right:88px;top:1214px;width:300px"><div class=s28 style="text-align:right">' + ACCT + '</div></div>'
def head(lab, no): return f'<div class=abs data-o=lab style="left:88px;top:96px;width:500px"><div class=s30>{lab}</div></div><div class=abs data-o=no style="right:88px;top:96px;width:240px"><div class=s30 style="text-align:right">{no}</div></div>'
def line(y, m='light'): return f'<div class=abs style="left:88px;top:{y}px;width:904px;height:2px;background:{V[m]["ink2"]};opacity:.35"></div>'
# 手繪感底線（不規則 SVG 路徑，不構成封閉圈）
def ul(x, y, wd, m='light'): return f'<svg class=abs style="left:{x}px;top:{y}px" width={wd} height=18 viewBox="0 0 {wd} 18"><path d="M3 11 C{wd*.25} 4, {wd*.5} 16, {wd-4} 7" stroke="{V[m]["acc"]}" stroke-width="5" fill="none" stroke-linecap="round"/></svg>'

# post1 範例1：Threads 單圖，便利貼版型（A 色票）
P = 'post1'
w(P, 'threads', 'light', head('週日晚上', '') .replace('<div class=abs data-o=no style="right:88px;top:96px;width:240px"><div class=s30 style="text-align:right"></div></div>','') +
 '<div class="abs glow" style="left:190px;top:300px;width:700px;height:700px"></div>'
 '<div class="abs note" data-o=note1 style="left:104px;top:340px;width:872px;height:280px;transform:rotate(-0.8deg);padding:52px 56px;background:var(--hl-card)"><div class="s30 wk" style="color:var(--hl-accent)">今晚只做一件事</div><div class="wk" style="font-size:60px;font-weight:400;line-height:1.5;margin-top:10px">把明天最小的那件事<br>寫在紙上。</div></div>'
 '<div class="abs note" data-o=note2 style="left:104px;top:700px;width:872px;height:200px;transform:rotate(0.6deg);padding:46px 56px"><div class="wk" style="font-size:56px;font-weight:400;line-height:1.5">其他的，留給明天的你。</div></div>'
 + foot)
# post2 範例2：IG 輪播 5 張，深色底
P = 'post2'
dark_glow = '<div class="abs glow" style="left:140px;top:360px;width:800px;height:800px"></div>'
w(P, '01_cover', 'dark', head('睡前一段', '1 / 5') + dark_glow +
 '<div class=abs data-o=hook style="left:88px;top:300px;width:904px"><div class="hook ser">今天先<br>到這裡。</div></div>'
 '<div class=abs data-o=sub style="left:88px;top:690px;width:700px"><div class=sub38>給還沒睡的你</div></div>'
 '<svg class=abs data-o=deco style="left:760px;top:830px" width=232 height=232 viewBox="0 0 232 232"><circle cx="116" cy="116" r="84" fill="#C8A58E"/><circle cx="152" cy="92" r="72" fill="#2B2622"/></svg>'
 '<div class=abs data-o=swipe style="left:760px;top:1110px;width:232px"><div class=s30 style="text-align:right">往右滑 →</div></div>' + foot)
def inner(n, t, extra=''):
    w('post2', f'0{n}_inner', 'dark', head('睡前一段', f'{n} / 5') + dark_glow + f'<div class=abs data-o=main style="left:88px;top:380px;width:904px"><div class="main64 ser">{t}</div></div>' + extra + foot)
inner(2, '沒做完的事，<br>放在桌上就好。<br>它不會跑掉。')
inner(3, '今天說了很多次「沒事」，<br>現在可以對自己<br>說一次實話：<br><span class=em>我有點累。</span>')
inner(4, '不用逼自己馬上睡著。<br>躺著、呼吸、什麼都不想，<br>也算休息。')
inner(5, '辛苦了。<br>明天的事，明天再說。<br>晚安。',
 '<div class=abs data-o=help style="left:88px;top:940px;width:904px"><div class=s28 style="line-height:1.6">如果你最近很辛苦，不用一個人撐：<br>・安心專線 1925（24 小時、免付費）<br>・生命線 1995<br>・張老師 1980（非 24 小時）<br>有立即危險請撥 119 或 110。</div></div>')
# post3 範例3：語錄卡，淺色底
P = 'post3'
w(P, '01_quote', 'light', head('給累了的你', '') .replace('<div class=abs data-o=no style="right:88px;top:96px;width:240px"><div class=s30 style="text-align:right"></div></div>','') +
 '<div class="abs glow" style="left:80px;top:280px;width:920px;height:560px"></div>'
 '<div class=abs data-o=main style="left:88px;top:430px;width:904px"><div class="main ser">回訊息慢了，<br>不代表你<span class=em>不在乎</span>。</div></div>'
 + ul(388, 648, 226) +
 '<div class=abs data-o=sub style="left:88px;top:720px;width:904px"><div class=sub38 style="font-size:44px">你只是電量剩 3%。</div></div>' + foot)
