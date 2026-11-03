# 範例貼文 20261104 三篇：依 render_spec.json 用版型 A 出自製圖解頁（含「待 Andy 截圖」佔位頁）。
# 用法：python3 gen_samples.py && node render_samples.js
import os, re, json
LAYOUT = os.path.dirname(os.path.abspath(__file__))
SAMP = os.path.abspath(LAYOUT + '/../samples/20261104')
SITE = os.path.abspath(LAYOUT + '/../../../../../site/channels/logos/ai_intro.svg')
T = dict(bg="#0F1722", card="#182334", line="#2A3A52", ink="#F3F7FB", ink2="#B4C2D3", acc="#6FD8A0", warn="#FFC857")
FONT = "'Noto Sans TC','Noto Sans CJK TC','WenQuanYi Zen Hei',sans-serif"
MONO = "'JetBrains Mono','DejaVu Sans Mono',monospace"
_s = open(SITE).read()
_s = re.sub(r'<rect x="-999"[^>]*/>', '', _s)
_s = re.sub(r'viewBox="[^"]*"', 'viewBox="84 120 344 272"', _s)
_s = re.sub(r'width="512" height="512"', 'width="56" height="44"', _s)
LOGO = _s
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;background:%(bg)s;color:%(ink)s;font-family:FONT;position:relative;overflow:hidden}
.abs{position:absolute}
.tag{font-size:30px;font-weight:700;color:%(acc)s;letter-spacing:2px;line-height:44px;white-space:nowrap}
.date{font-size:28px;color:%(ink2)s;font-weight:500;line-height:44px;white-space:nowrap}
.hook{font-size:132px;font-weight:900;line-height:1.12;letter-spacing:-2px}
.hook em{font-style:normal;color:%(acc)s}
.sub{font-size:44px;font-weight:500;color:%(ink2)s;line-height:1.4}
.chip{font-size:30px;font-weight:700;padding:10px 24px;border-radius:999px;border:2px solid %(line)s;background:%(card)s;color:%(ink)s;line-height:1.3;white-space:nowrap}
.h2{font-size:58px;font-weight:800;line-height:1.25}
.step{font-size:30px;font-weight:800;border:3px solid %(acc)s;color:%(acc)s;padding:0 18px;border-radius:10px;line-height:38px;display:inline-block;white-space:nowrap}
.note{font-size:34px;font-weight:600;line-height:1.4}
.note b{color:%(acc)s}
.small{font-size:30px;font-weight:500;color:%(ink2)s;line-height:1.5}
.badge{font-size:28px;font-weight:800;padding:6px 18px;border-radius:8px;border:3px solid %(acc)s;color:%(acc)s;line-height:1.3;display:inline-block;white-space:nowrap}
.badge.w{border-color:%(warn)s;color:%(warn)s}
.disc{font-size:28px;color:%(ink2)s;font-weight:500;border-top:2px solid %(line)s;padding-top:12px;display:flex;justify-content:space-between;line-height:1.3}
.disc .k{color:%(ink)s;font-weight:700}
.ph{border:6px dashed %(warn)s;border-radius:22px;background:rgba(255,200,87,.08);padding:36px 40px;display:flex;flex-direction:column;gap:18px;overflow:hidden}
.ph .t{font-size:56px;font-weight:900;color:%(warn)s;line-height:1.2}
.ph .r{font-size:34px;font-weight:600;line-height:1.45;color:%(ink)s}
.ph .r b{color:%(warn)s}
table{border-collapse:collapse;width:100%%;font-size:34px;table-layout:fixed}
th{font-size:32px;font-weight:800;text-align:left;padding:0 14px;height:96px;border-bottom:3px solid %(line)s;color:%(ink2)s;line-height:1.25}
td{padding:10px 14px;border-bottom:2px solid %(line)s;font-weight:600;line-height:1.35;vertical-align:middle}
td.w{background:rgba(111,216,160,.14);color:%(acc)s;font-weight:800}
td.m{color:%(warn)s}
.item{display:flex;gap:24px;align-items:flex-start}
.item .n{flex:none;width:64px;height:64px;border-radius:50%%;border:3px solid %(acc)s;color:%(acc)s;font-weight:900;font-size:34px;display:flex;align-items:center;justify-content:center}
.item p{font-size:40px;font-weight:700;line-height:1.4}
.item small{display:block;font-size:30px;font-weight:500;color:%(ink2)s;margin-top:6px;line-height:1.45}
.col{display:flex;flex-direction:column}
.box{background:%(card)s;border:3px solid %(line)s;border-radius:22px;padding:28px 32px}
.box .lb{font-size:30px;font-weight:800;color:%(acc)s;line-height:1.3;margin-bottom:8px}
.box .tx{font-size:34px;font-weight:600;line-height:1.4}
.hi{background:rgba(111,216,160,.14);border:3px solid %(acc)s;border-radius:22px;padding:24px 32px}
.hi .tx{font-size:34px;font-weight:700;line-height:1.4}
.mono{font-family:MONO}
.info{display:flex;gap:12px}
.tile{background:%(card)s;border:3px solid %(line)s;border-radius:22px}
"""
def css(): return (CSS % dict(T)).replace('FONT', FONT).replace('MONO', MONO)
def E(name, left, top, body, width=None, right=None, extra='', cls=''):
    st = f'top:{top}px;' + (f'left:{left}px;' if left is not None else f'right:{right}px;') + (f'width:{width}px;' if width else '')
    return f'<div class="abs {cls}" data-o="{name}" style="{st}{extra}">{body}</div>'
def head(pill, pg, tag=None):
    s = E('logo', 64, 72, LOGO, extra='height:44px;width:56px')
    s += E('pill', 144, 72, f'<span class=step>{pill}</span>' if pill else f'<span class=tag>{tag}</span>')
    if pg: s += E('pg', None, 72, f'<span class=date>{pg}</span>', right=64)
    return s
def title(t, top=150): return E('title', 64, top, f'<div class=h2>{t}</div>', width=952)
def disc(left): a, b = left.split('｜'); return E('disc', 64, 1228, f'<div class=disc><span><span class=k>{a}</span>｜{b}</span><span>圖文含 AI 協助</span></div>', width=952)
def ph(top, h, what, mask, extra_title='待 Andy 截圖'):
    return E('ph', 64, top, f'<div class=t>{extra_title}</div><div class=r><b>要截：</b>{what}</div><div class=r><b>要遮：</b>{mask}</div>', width=952, extra=f'height:{h}px', cls='ph')
def pbadge(top=1120): return E('badge', 64, top, '<span class="badge w">佔位頁，非成品</span>')
def cover(tag, date, hook, sub, chips, bottom):
    s = E('logo', 64, 72, LOGO, extra='height:44px;width:56px') + E('tag', 144, 72, f'<span class=tag>{tag}</span>')
    if date: s += E('date', None, 72, f'<span class=date>{date}</span>', right=64)
    s += E('hook', 64, 162, f'<div class=hook>{hook}</div>', width=952)
    s += E('sub', 64, 674, f'<div class=sub>{sub}</div>', width=952)
    s += E('chips', 64, 766, ''.join(f'<span class=chip>{c}</span>' for c in chips), extra='display:flex;gap:16px')
    return s + bottom
def tbl(top, cols, head_, rows, name='table', wins=(), mark=(), pad=10):
    g = ''.join(f'<col style="width:{c}%">' for c in cols)
    h = ''.join(f'<th>{x}</th>' for x in head_)
    r = ''
    for i, row in enumerate(rows):
        r += '<tr>' + ''.join(f'<td class="{"w" if (i,j) in wins else ""}{" m" if (i,j) in mark else ""}">{c}</td>' for j, c in enumerate(row)) + '</tr>'
    return E(name, 64, top, f'<style>.t_{name} td{{padding:{pad}px 14px}}</style><table class=t_{name}>{g}<tr>{h}</tr>{r}</table>', width=952)
def items(top, lst, name='items', gap=34):
    b = ''.join(f'<div class=item><div class=n>{i+1}</div><p>{a}<small>{s}</small></p></div>' if s else f'<div class=item><div class=n>{i+1}</div><p>{a}</p></div>' for i, (a, s) in enumerate(lst))
    return E(name, 64, top, b, width=952, extra=f'display:flex;flex-direction:column;gap:{gap}px')
# ---- 示意圖示 ----
def ico(kind, c=T['acc'], s=84):
    p = {'person': f'<circle cx="32" cy="20" r="13" fill="none" stroke="{c}" stroke-width="6"/><path d="M8 58C8 40 18 36 32 36S56 40 56 58" fill="none" stroke="{c}" stroke-width="6" stroke-linecap="round"/>',
         'mouth': f'<path d="M8 28Q32 62 56 28" fill="none" stroke="{c}" stroke-width="6" stroke-linecap="round"/><path d="M8 28H56" stroke="{c}" stroke-width="6" stroke-linecap="round"/>',
         'lock': f'<rect x="12" y="28" width="40" height="28" rx="7" fill="none" stroke="{c}" stroke-width="6"/><path d="M20 28V20A12 12 0 0 1 44 20V28" fill="none" stroke="{c}" stroke-width="6" stroke-linecap="round"/>',
         'mark': f'<path d="M16 6H48V58L32 46L16 58Z" fill="none" stroke="{c}" stroke-width="6" stroke-linejoin="round"/>'}[kind]
    return f'<svg width="{s}" height="{s}" viewBox="0 0 64 64">{p}</svg>'
def page(body): return f'<html><head><meta charset=utf-8><style>{css()}</style></head><body>{body}</body></html>'
P = {}
# ================= post1 =================
D1 = '無業配｜截圖已遮個資'
def p1():
    s = {}
    card = E('peek', 64, 898, '<div class=t style="font-size:44px">待 Andy 截圖：第 4 張一角</div><div class=r style="font-size:30px">做好後放在這裡，罩 50% 暗度</div>', width=952, extra='height:300px', cls='ph')
    s[1] = cover('AI 實測 第 01 期', '日期待填', '答案會變成<br>「小工具」？<br>我丟 <em>10 題</em>試', 'ChatGPT 實測：出現幾次？算得對嗎？', ['10 次實測', '附算式驗算', '含翻車'], card + disc(D1))
    main = items(300, [('2026-10-07 起，ChatGPT 的「Chat」分頁，回答裡可以直接長出圖表、表單、按鈕、小計算器。', ''), ('付費方案先拿到，免費與 Go 方案 10/8 跟進。', ''), ('不用特別下指令；純文字夠用時它還是給文字。', '')], 'main', 40)
    s[2] = head('步驟 0', '2/7') + title('先搞清楚它是什麼') + main + E('small', 64, 940, '<div class=small>官方說法以 OpenAI 公告為準；細節只用兩家以上媒體一致的部分。</div>', width=952) + E('badge', 64, 1100, '<span class=badge>自製圖解（非 AI 生成）</span>') + disc(D1)
    rows = [('分帳', '4 人聚餐 1 人沒喝酒', '用 Excel 自己算', '金額差幾元'), ('比較', '三個手機方案月費', '逐格對原始數字', '有無互動元件'), ('試算', '房貸月付 800 萬、2.2%、30 年', '用 Excel 驗算', '差幾元'), ('流程', '請假流程畫成圖', '看有無漏步驟', '能不能點'), ('純知識', '特休怎麼算', '看會不會硬塞小工具', '有無引用條文')]
    s[3] = head('步驟 0', '3/7') + title('我怎麼測：5 種題目 × 2 次') + tbl(290, [14, 31, 29, 26], ['題目', '我問什麼', '我怎麼驗', '要記什麼'], rows, pad=16) + E('note', 64, 1060, '<div class=small><b style="color:#6FD8A0">測試條件：</b>日期、方案、網頁或手機、語言【待填】</div>', width=952) + disc(D1)
    s[4] = head('步驟 1', '4/7') + title('它真的變出計算器了') + ph(300, 640, '分帳題的完整回答畫面，要看得到互動元件與你的提問，從提問截到回答結束。', '左側聊天紀錄清單、帳號名稱與信箱、瀏覽器分頁與書籤列。') + E('note', 64, 980, '<div class=note><b>結果出來後填：</b>2 次裡有【__】次出現互動元件；金額與 Excel 差【__】元。</div>', width=952) + pbadge() + disc(D1)
    s[5] = head('步驟 2', '5/7') + title('房貸試算：算得和 Excel 一樣嗎') + ph(300, 640, '房貸試算題的回答畫面（含月付金額），旁邊並排你用 Excel PMT 算的同一格，兩張拼成一張。', '同第 4 張：聊天紀錄清單、帳號資訊、分頁與書籤列。') + E('note', 64, 980, '<div class=note><b>標註（最多 3 個）：</b>① ChatGPT 的數字　② Excel 的數字　③ 差額</div>', width=952) + pbadge() + disc(D1)
    rows = [('分帳', '【__】', '【__】', '【__】'), ('比較', '【__】', '【__】', '【__】'), ('試算', '【__】', '【__】', '【__】'), ('流程', '【__】', '【__】', '【__】'), ('純知識', '【__】', '【__】', '【__】')]
    s[6] = head('步驟 3', '6/7') + title('10 次的結果') + tbl(290, [18, 27, 27, 28], ['題目', '互動元件（次／2）', '數字算對（次／2）', '我的感想一句'], rows, mark={(i, j) for i in range(5) for j in (1, 2, 3)}, pad=30) + E('note', 64, 1010, '<div class=small><b style="color:#6FD8A0">怎麼比的：</b>同題問 2 次、各開新對話；樣本只有 10 次，不代表一般情況。勝出格會標 ✓。</div>', width=952) + disc(D1)
    s[7] = head('結論', '7/7') + title('結論：依實測結果寫') + items(300, [('誰適合用、誰不適合：【待填】', ''), ('哪裡會出錯：【待填，要是真的遇到的】', ''), ('下一步：先拿一題你有標準答案的題目測，再決定信不信', '')], 'items', 44) + E('small', 64, 960, '<div class=small>完整測試條件【待填】。以上為個人使用經驗，不構成任何建議。</div>', width=952) + disc(D1)
    return s
# ================= post2 =================
D2 = '無業配｜整理自新聞'
def news(n, tt, info, blocks, hi, icon=None):
    b = ''
    for lb, tx, ic in blocks:
        inner = f'<div class=box><div class=lb>{lb}</div><div class=tx>{tx}</div></div>'
        b += inner
    s = head(f'新聞 {n}', f'{n+1}/6') + title(tt)
    s += E('info', 64, 320, ''.join(f'<span class=chip>{x}</span>' for x in info), extra='display:flex;gap:12px')
    s += E('main', 64, 424, b + f'<div class=hi><div class=lb style="font-size:30px;font-weight:800;color:#6FD8A0;margin-bottom:6px">對上班族差在哪</div><div class=tx>{hi}</div></div>', width=952, extra='display:flex;flex-direction:column;gap:22px')
    return s
def p2():
    s = {}
    tiles = ''.join(f'<div class=tile style="width:300px;height:300px;padding:28px;display:flex;flex-direction:column;justify-content:space-between"><div style="font-size:72px;font-weight:900;color:#6FD8A0;line-height:1">{n}</div>{ico(k, s=88)}<div style="font-size:34px;font-weight:800;line-height:1.3">{l}</div></div>' for n, k, l in [(1, 'person', '裁員方案'), (2, 'lock', '聊天機器人新法'), (3, 'mark', 'AI 代理')])
    s[1] = cover('本週 AI 三則', '10/28～11/03', '三則 AI 新聞<br>只講跟你<br><em>上班有關</em>的', '每則附來源、日期、可信度', ['微軟 6 萬人', '紐約新法', 'Claude Duet'], E('tiles', 64, 898, tiles, extra='display:flex;gap:26px') + disc(D2))
    s[2] = news(1, '微軟提出約 6 萬人自願離職方案', ['事件日 10/26', '查證日 11/03', '信心度 中'], [('發生什麼', '向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。', 0), ('微軟怎麼說', '公司說是為員工增加彈性。把它連到 AI 投資成本，是媒體的解讀，不是公司原話。', 0)], '看到「AI 導致裁員」的標題，先分清公司說的原因和媒體猜的原因。')
    s[2] += E('ico', None, 72, ico('person', s=44), right=170) if False else ''
    s[2] += E('badge', 64, 1130, '<span class=badge>我沒親自測，整理自新聞</span>') + disc(D2)
    s[3] = news(2, '紐約簽了聊天機器人新法', ['10/28 簽署', '2027/1/1 生效', '信心度 中'], [('發生什麼', '業者沒有先確認對方不是未成年，就不能提供一批不安全的陪伴功能。違規州檢察長可提告。', 0)], '這是美國州法，台灣不適用；但做產品會跟青少年聊天的人，先看過「不准假裝是真人」。')
    s[3] = s[3].replace('data-o="main" style="top:400px', 'data-o="main" style="top:400px') + E('icons', 64, 880, ''.join(f'<div class=tile style="width:300px;padding:20px 0 16px;display:flex;flex-direction:column;align-items:center;gap:8px">{ico(k, T["warn"], 72)}<div style="font-size:30px;font-weight:700">{l}</div></div>' for k, l in [('person', '假裝成真人'), ('mouth', '一味奉承'), ('lock', '鼓勵疏遠')]), extra='display:flex;gap:26px') + E('badge', 64, 1130, '<span class=badge>我沒親自測，整理自新聞</span>') + disc(D2)
    s[4] = news(3, 'Claude Duet 開放候補', ['10/21（美西）', '查證日 11/03', '信心度 中'], [('發生什麼', 'Anthropic 推出研究預覽，會主動整理信箱與行事曆；付款、簽文件會先問你。只開美國候補，Pro、Max 先。', 0)], '台灣進不了候補，別花時間找方法；以後挑 AI 代理工具，就看「哪些動作一定先問你」。') + E('badge', 64, 1130, '<span class=badge>我沒親自測，整理自新聞</span>') + disc(D2)
    rows = [('微軟', 'AP 稿轉載（10/27）、UC Today（約 10/27，日期待核）', '中'), ('紐約', 'AP 稿轉載（10/28）、PPC Land（約 10/28，日期待核）', '中'), ('Duet', 'Inside、科技新報（10/21～22）', '中')]
    s[5] = head('來源', '5/6') + title('三則的來源（都附日期）') + tbl(290, [18, 64, 18], ['新聞', '兩個獨立來源', '信心度'], rows, pad=24) + E('small', 64, 960, '<div class=small>信心「中」＝我只讀到新聞摘要，沒讀到公司或政府一手公告。完整網址放在留言。</div>', width=952) + disc(D2)
    s[6] = head('結論', '6/6') + title('這週我的結論') + items(300, [('這三則我都沒親自測，只當資訊看。', ''), ('看到裁員標題，先查公司原話。', ''), ('看 AI 代理，先問「哪些事它會先問我」。', '')], 'items', 44) + E('small', 64, 960, '<div class=small>以上為資訊整理，不構成任何建議。提到公司名僅作新聞事實，不推薦買賣任何個股。</div>', width=952) + disc(D2)
    return s
# ================= post3 =================
D3 = '無業配｜全為假資料'
def p3():
    s = {}
    def sheet(rows, cols, hdr):
        g = ''.join(f'<div style="flex:1;border-right:2px solid #2A3A52;padding:0 16px"><div style="font-size:26px;color:#B4C2D3;line-height:56px">{h}</div>' + ''.join(f'<div class=mono style="font-size:32px;line-height:56px;white-space:nowrap">{r[i]}</div>' for r in rows) + '</div>' for i, h in enumerate(hdr))
        return g
    peek = E('peek', 64, 898, '<div class=tile style="display:flex;height:300px;overflow:hidden">' + sheet([('2026/11/03 王小明', '2026/11/03', '王小明'), ('2026/11/04 林小華', '2026/11/04', '林小華'), ('2026/11/05 陳小美', '2026/11/05', '陳小美')], 3, ['A 原始', 'B 日期', 'C 姓名']) + '</div>', width=952)
    s[1] = cover('AI 實測 第 02 期', None, '「2026/11/03<br>王小明」一欄<br><em>拆成兩欄</em>', '貼 1 段提示詞，30 秒搞定', ['假資料示範', '附公式', '附防呆'], peek + disc(D3))
    t = '<div class=tile style="padding:8px 0">' + ''.join(f'<div class=mono style="font-size:40px;line-height:96px;padding:0 32px;border-bottom:2px solid #2A3A52">{x}</div>' for x in ['2026/11/03 王小明', '2026/11/04 林小華', '2026/11/05 陳小美']).rsplit('border-bottom:2px solid #2A3A52', 1)[0] + 'border-bottom:0' + '</div></div>'
    t = '<div class=tile style="overflow:hidden">' + ''.join(f'<div class=mono style="font-size:40px;line-height:96px;padding:0 32px;{"border-bottom:2px solid #2A3A52" if i<2 else ""}">{x}</div>' for i, x in enumerate(['2026/11/03 王小明', '2026/11/04 林小華', '2026/11/05 陳小美'])) + '</div>'
    s[2] = head('情境', '2/7') + title('你是不是也有這種欄位') + E('sheet', 64, 300, '<div class=small style="margin-bottom:12px">A 欄（假資料）</div>' + t, width=952) + E('txt', 64, 700, '<div class=note style="font-size:40px">系統匯出來的表，日期和姓名黏在同一格。手動拆 200 列，拆到眼睛花。</div>', width=952) + disc(D3)
    s[3] = head('步驟 1', '3/7') + title('步驟 1：先講你用哪個版本') + E('txt', 64, 300, '<div class=note style="font-size:40px">Excel 365 有新函數，舊版沒有。<br>不講版本，它可能給你舊版打不開的公式。</div>', width=952) + E('chips', 64, 520, ''.join(f'<span class=chip style="font-size:36px;padding:14px 28px">{x}</span>' for x in ['Excel 365', 'Excel 2019', 'Excel 2016']), extra='display:flex;gap:16px') + E('small', 64, 660, '<div class=small>版本在「檔案 → 帳戶」看得到。</div>', width=952) + disc(D3)
    prm = ['你是 Excel 助手。我的 A 欄每格格式是「日期 空格 姓名」，例如「2026/11/03 王小明」。', '請給我兩條公式（從第 2 列開始）：B 欄取出日期，C 欄取出姓名。', '要求：', '1. 我的 Excel 版本是【請填：Excel 365／2019／2016】。', '2. 日期要變成真正的日期，不是文字。', '3. 姓名前後不要有多餘空格。', '4. 每條公式後面用一句話說明它在做什麼。', '5. 告訴我：如果某一格沒有空格、或是空白，公式會出現什麼結果；並給我加上防呆的版本。', '6. 不要編造不存在的函數；不確定就直接說不確定。']
    s[4] = head('步驟 2', '4/7') + title('步驟 2：貼這段') + E('prompt', 64, 300, ''.join(f'<div style="margin-bottom:8px">{x}</div>' for x in prm), width=952, extra='font-size:32px;font-weight:600;line-height:1.45;padding:28px 32px;background:#182334;border:3px solid #6FD8A0;border-radius:22px') + disc(D3)
    fm = '<div class=tile style="padding:16px 28px"><div class=mono style="font-size:30px;line-height:1.7"><span style="color:#FFC857">B2</span>　=DATEVALUE(LEFT(A2,FIND(" ",A2)-1))<br><span style="color:#FFC857">C2</span>　=TRIM(MID(A2,FIND(" ",A2)+1,100))</div></div>'
    s[5] = head('步驟 3', '5/7') + title('步驟 3：貼進去，驗 3 格') + E('fm', 64, 290, fm, width=952) + E('how', 64, 470, '<div class=note><b>驗法：</b>抽第一列、最後一列、一列故意打壞的，對照 A 欄。AI 寫法可能不同，結果要一樣。</div>', width=952) + ph(680, 400, 'B、C 欄貼上公式後的結果畫面。', '姓名以外的個資、檔案路徑、視窗標題。') + pbadge(1110) + disc(D3)
    boxes = [('坑 1：日期變成一串數字', '例如 46329。不是算錯，是格式沒設成日期。選取 B 欄 → 儲存格格式 → 日期。'), ('坑 2：姓名前是全形空格', 'FIND(" ") 找不到。叫 AI「同時處理全形空格」，或先用取代把全形空格換成半形。')]
    s[6] = head('出錯', '6/7') + title('最常見的兩個坑') + E('main', 64, 300, ''.join(f'<div class=box style="border-color:#FFC857"><div class=lb style="color:#FFC857;font-size:36px">{a}</div><div class=tx>{b}</div></div>' for a, b in boxes), width=952, extra='display:flex;flex-direction:column;gap:28px') + E('small', 64, 840, '<div class=small>【待 Andy 實測】有遇到別的坑，就換掉其中一個，寫真實遇到的。</div>', width=952) + disc(D3)
    s[7] = head('收尾', '7/7') + title('存起來，下次直接貼') + E('ico', 64, 320, ico('mark', T['acc'], 160)) + E('txt', 64, 520, '<div class=note style="font-size:40px">提示詞全文在第 4 張，截圖或複製都行。</div>', width=952) + E('small', 64, 660, '<div class=small>資料請用假資料，或先遮掉個資再貼給 AI。以上為個人使用經驗。</div>', width=952) + disc(D3)
    return s
jobs = []
for name, fn in [('post1_實測', p1), ('post2_三則', p2), ('post3_教學', p3)]:
    d = f'{SAMP}/{name}/img'; os.makedirs(d, exist_ok=True); os.makedirs(f'{LAYOUT}/html_samples', exist_ok=True)
    for n, body in fn().items():
        h = f'{LAYOUT}/html_samples/{name[:5]}_{n}.html'; open(h, 'w').write(page(body))
        jobs.append(dict(html=h, out=f'{d}/slide{n}.png', post=name))
json.dump(jobs, open(f'{LAYOUT}/html_samples/jobs.json', 'w'), ensure_ascii=False)
