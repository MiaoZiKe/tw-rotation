# 範例貼文成圖產生器（套 A／B／C 版型）。在 layouts/ 目錄下執行：python3 samples.py
import os, json, gen
from gen import cssA, cssB, cssC, A, B, C, ACCT, BASE
S = '../samples/20261104'
def w(post, name, css, body, H=1350):
    d = f'{S}/{post}/html'; os.makedirs(d, exist_ok=True)
    open(f'{d}/{name}.html', 'w', encoding='utf-8').write(f'<!doctype html><meta charset=utf-8><style>{BASE % (1080, H)}{css}</style><body>{body}</body>')
    m = f'{S}/{post}/manifest.json'
    mf = json.load(open(m)) if os.path.exists(m) else {}
    mf[name] = H; json.dump(mf, open(m, 'w'))
acct = lambda: f'<div class=abs data-o=acct style="right:96px;top:1236px;width:400px"><div class=acct>{ACCT}</div></div>'
def a_head(lab, no): return f'<div class=abs data-o=lab style="left:96px;top:96px;width:600px"><div class=lab>{lab}</div></div><div class=abs data-o=no style="right:96px;top:100px;width:240px"><div class=no style="text-align:right">{no}</div></div><div class="abs rule" style="left:96px;top:176px;width:888px"></div>'
def a_card(post, name, lab, no, q, sub):
    w(post, name, cssA, a_head(lab, no) + f'<div class=abs data-o=quote style="left:96px;top:300px;width:888px"><div class=q>{q}</div></div><div class=abs data-o=sub style="left:96px;top:1000px;width:888px"><div class=sub>{sub}</div></div><div class="abs rule" style="left:96px;top:1200px;width:888px"></div>' + acct())
def a_inner(post, name, lab, no, title, body, seal=None):
    s = f'<div class=abs data-o=seal style="left:96px;top:1180px"><div class=seal>{seal}</div></div>' if seal else ''
    w(post, name, cssA, a_head(lab, no) + f'<div class=abs data-o=title style="left:96px;top:250px;width:888px"><div class=h>{title}</div></div><div class=abs data-o=body style="left:96px;top:520px;width:888px"><div class=p>{body}</div></div>' + s + acct())
def b_card(post, name, lab, txt):
    w(post, name, cssB(1350), f'<div class=abs data-o=moon style="left:96px;top:96px"><div class=moon></div></div><div class=abs data-o=lab style="left:210px;top:118px;width:600px"><div class=lab>{lab}</div></div><div class=abs data-o=txt style="left:96px;top:300px;width:888px"><div class=txt>{txt}</div></div>' + acct())
def c_list(post, name, title, tsub, items, foot):
    rots = [-1.2, 1.0, -0.8, 1.2, -1.0]
    b = f'<div class=abs data-o=title style="left:96px;top:72px;width:888px;height:190px;background:#FFE98A;transform:rotate(-1deg);padding:34px 40px;box-shadow:0 8px 0 rgba(60,45,20,.12)"><div class=title>{title}</div><div class=tsub>{tsub}</div></div>'
    for i, t in enumerate(items):
        b += f'<div class="abs note" data-o=n{i+1} style="left:96px;top:{310+i*160}px;height:128px;background:{C["notes"][i]};transform:rotate({rots[i]}deg)"><i class=box></i><div class=t>{t}</div></div>'
    b += f'<div class=abs data-o=foot style="left:96px;top:1180px;width:560px"><div class=foot>{foot}</div></div>' + acct().replace('1236', '1260')
    w(post, name, cssC, b)
def c_note(post, name, color, big, label=None):
    extra = f'.big{{font-size:84px;font-weight:900;line-height:1.5;letter-spacing:4px}}.big em{{font-style:normal;text-decoration:underline;text-decoration-thickness:6px;text-underline-offset:10px}}'
    b = (f'<div class=abs data-o=lab style="left:96px;top:140px;width:420px;height:96px;background:#FFD3D9;transform:rotate(1.5deg);padding:24px 28px;box-shadow:0 8px 0 rgba(60,45,20,.12)"><div class=t style="font-size:40px">給自己的便條</div></div>' if label else '')
    b += f'<div class=abs data-o=note style="left:96px;top:380px;width:888px;height:640px;background:{color};transform:rotate(-1.5deg);padding:72px 64px;box-shadow:0 10px 0 rgba(60,45,20,.12)"><div class=big>{big}</div></div>'
    b += f'<div class=abs data-o=foot style="left:96px;top:1150px;width:560px"><div class=foot>撕下來，貼在心裡。</div></div>' + acct().replace('1236', '1260')
    w(post, name, cssC + extra, b)

P = 'post1'
a_card(P, '01_cover', '今晚的一句話', 'No.002', '不用每天都<br>閃閃發亮。<br><em>安靜的日子</em>，<br>也算數。', '把肩膀放鬆，今晚不用再證明什麼。')
a_inner(P, '02_inner', '寫給累了的你', '2 / 3', '給今天很累的你', '有些日子，<br>什麼都沒做成，<br>只是<b>把自己帶回家</b>。<br><br>那也是一件，<br>需要力氣的事。')
a_inner(P, '03_inner', '寫給累了的你', '3 / 3', '今晚，<br>慢慢來。', '<b>喝杯溫的</b>，<br>把螢幕調暗一點，<br>剩下的，交給明天。', '存起來，睡前看')
a_card(P, 'threads', '今晚的一句話', 'No.003', '今天做到的，<br>已經<em>夠了</em>。', '不必和任何人比較。')
P = 'post2'
b_card(P, '01_cover', '睡前一分鐘　1/3', '你今天，<br>說了很多話，<br>也忍住了很多話。<br><b>辛苦了。</b>')
b_card(P, '02_inner', '睡前一分鐘　2/3', '心裡的事，<br>不必今晚想完。<br><b>寫在明天的清單上，</b><br>它會在那裡等你。')
b_card(P, '03_inner', '睡前一分鐘　3/3', '深呼吸，<br>慢慢吐氣。<br>被子蓋好。<br><b>晚安。</b>')
b_card(P, 'threads', '睡前一分鐘', '有些煩惱，<br>在天亮以後<br>會變得小一點。<br><b>先睡吧。</b>')
P = 'post3'
c_list(P, '01_cover', '下班前小喘息', '做一個就算贏', ['站起來伸個懶腰', '把桌面清出一個角落', '傳訊息給讓你安心的人', '把明天最重要的事寫下來', '關掉電腦，說聲辛苦了'], '存起來，下班前看一眼。')
c_list(P, '02_inner', '週日晚上小喘息', '給週一的自己一點緩衝', ['洗個熱水澡', '把明天要穿的衣服拿出來', '聽一首喜歡的歌', '十點前躺上床'], '週一，也會過去的。')
c_note(P, '03_inner', '#FFE98A', '今天不用<br>做到完美。<br>做到<em>完成</em><br>就好。', label=True)
c_note(P, 'threads', '#CFE6F5', '喝口水，<br>深呼吸，<br>再繼續。')
