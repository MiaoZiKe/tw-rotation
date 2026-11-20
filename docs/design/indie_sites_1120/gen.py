# 產生 6 頁設計稿原型（資料取自真實文章摘要；數字以文章 JSON 為準，示意處已標註）
import os
H=os.path.dirname(os.path.abspath(__file__))
def page(ch,name,title,body,css="../proto.css"):
    open(f"{H}/{ch}/{name}.html","w",encoding="utf-8").write(f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><link rel="stylesheet" href="{css}"></head><body data-ch="{ch}">{body}</body></html>''')
CUP='<svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7 14h20v9a9 9 0 0 1-9 9h-2a9 9 0 0 1-9-9z"/><path d="M27 17h3a4 4 0 0 1 0 8h-3"/><path d="M13 6c-1 2 1 3 0 5M19 6c-1 2 1 3 0 5"/></svg>'
CAFF_HD='<header class="hd"><img class="lg" src="logo-128.png" alt="CaffAIne"><a class="nm" href="#">Caff<i>AI</i>ne</a><span class="sp"></span><a class="btn fill" href="#">追蹤</a></header>'
HEAL_LG='<svg class="lg" viewBox="-150 -255 340 400" width="32" height="32"><path d="M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z" fill="none" stroke="#6E6A66" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/><path d="M -26.3 -78.5 A 110 110 0 0 1 170.1 13.1" fill="none" stroke="#C5782B" stroke-width="24" stroke-linecap="round"/></svg>'
HEAL_HD=f'<header class="hd">{HEAL_LG}<a class="nm" href="#">談晴說礙</a><span class="sp"></span><a class="btn fill" href="#">追蹤</a></header>'
def hd(ch): return CAFF_HD if ch=="caffaine" else HEAL_HD

# ---------- 列表 ----------
def lst_item(th,title,p,meta,lock=False):
    return f'<a class="it{" lk" if lock else ""}" href="#"><div class="th">{th}</div><div class="tx"><h3>{title}</h3><p>{p}</p><div class="m">{meta}</div></div>{"<span class=lock>🔒</span>" if lock else ""}</a>'
cth=lambda g,l:f'<div style="width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;background:{g};color:#fff">{CUP.replace("40","28")}<span style="font:700 12px/1.2 system-ui">{l}</span></div>'
page("caffaine","list","CaffAIne 列表",f'''{CAFF_HD}
<section class="hero"><h1>一杯咖啡的時間，<br>看懂一個 AI 新知 ☕</h1><p>每篇 3～6 分鐘；有影片、有可以直接照做的步驟。</p>
<div class="gate"><span>追蹤頻道，用私訊解鎖連結即可看全文</span><a class="btn fill" href="#">登入</a></div></section>
<nav class="chips"><span class="chip on">全部 3</span><span class="chip">工具實測</span><span class="chip">提示詞</span><span class="chip">影片存檔</span></nav>
<a class="feat" href="#"><div class="cv"><span class="pill">本週精選・實測</span><div style="position:absolute;right:16px;top:12px;opacity:.9;color:#fff">{CUP}</div></div><div class="tx"><h2>為什麼 AI 做的網頁，都長一個樣？</h2><div class="m">2026-11-18・閱讀 6 分鐘・含影片 54 秒</div></div></a>
<div class="lst"><h2 class="sec">更早的文章</h2>
{lst_item(cth("linear-gradient(135deg,#5b63e8,#8a63f0)","提示詞"),"同一句話問 AI 兩次，答案為什麼不一樣？","同一個問題問兩次，答案為什麼會不同？怎麼寫才穩。","2026-11-17・3 分鐘")}
{lst_item(cth("linear-gradient(135deg,#8a63f0,#c58af5)","影片"),"這支影片的動畫，是我叫 AI 做的","沒有剪輯軟體，用一段提示詞做出動畫的完整過程。","2026-11-17・3 分鐘",True)}
</div><div class="ft">文章與影片 © CaffAIne</div>''')
def num(n,l): return f'<div class="th" style="background:var(--acc2)"><div class="num" style="color:#965012">{n}<small>{l}</small></div></div>'
def hit(n,l,t,p,m,lock=False): return lst_item(num(n,l).replace('<div class="th" style="background:var(--acc2)">','').rsplit('</div>',1)[0],t,p,m,lock)
page("healing","list","談晴說礙 列表",f'''{HEAL_HD}
<section class="hero"><h1>談這一代的難，<br>也說晴天裡的光。</h1><p>用官方數字說薪水、房租、學貸、婚育；每個數字都附出處。</p>
<div class="gate"><span>追蹤頻道，用私訊解鎖連結即可看全文</span><a class="btn fill" href="#">登入</a></div></section>
<nav class="chips"><span class="chip on">全部 12</span><span class="chip">薪資</span><span class="chip">生活開銷</span><span class="chip">學貸・婚育</span><span class="chip">工作・AI</span></nav>
<a class="feat" href="#"><div class="cv" style="aspect-ratio:2/1;background:linear-gradient(135deg,#d98a3d,#c5782b);align-items:center"><div><span class="pill">數字裡的日子</span><div style="font:700 56px/1.1 var(--hf);margin-top:8px">69.74%</div><div style="font-size:15px;margin-top:2px">的員工，領不到平均月薪</div></div></div><div class="tx"><h2>近7成員工，領不到平均月薪</h2><div class="m">2026-11-12・閱讀 6 分鐘・主計總處</div></div></a>
<div class="lst"><h2 class="sec">更多數字</h2>
{hit("30,900","元/月","第一份全職工作，明年起月薪至少 30,900 元","2027/1/1 起最低工資調漲 4.75%，時薪 205 元。","2026-11-18・6 分鐘")}
{hit("0.775%","學貸利率","有學貸的人：利率降到 0.775%，寬限期變 2 年","2026/8/1 起畢業後學生負擔利率由 1.775% 降下來。","2026-11-17・6 分鐘")}
{hit("-29.4%","結婚登記","10 年，結婚登記少了近 3 成","2025 年 104,376 對，2016 年 147,861 對。","2026-11-16・5 分鐘")}
{hit("2.33%","CPI 年增","外食年漲 3%，物價連 6 月破 2%","10 月 CPI 年增 2.33%；外食費 3.01%、房租 1.70%。","2026-11-13・6 分鐘",True)}
</div><div class="ft">文章與影片 © 談晴說礙・數據以官方公布為準</div>''')

# ---------- 文章第一屏 ----------
page("caffaine","top","CaffAIne 文章第一屏",f'''{CAFF_HD}<div class="prog"><b style="width:3%"></b></div>
<main class="art"><div class="w"><a class="bk" href="#">← 全部文章</a>
<div class="tags"><span class="pill">AI 工具</span><span class="pill">提示詞</span><span class="pill">Gemini 實測</span></div>
<h1>為什麼 AI 做的網頁，都長一個樣？</h1>
<div class="meta">2026-11-18・閱讀約 6 分鐘</div>
<div class="jump"><a href="#">▶ 先看 54 秒影片</a><a href="#">📋 直接看做法</a></div>
<p class="lead">結論：叫 AI 做網頁，你沒指定風格，它就交出最常見的那一種樣子；想要自己的樣子，得先把風格講出來。</p>
<p>如果你正用 AI 幫自己的店、作品集或活動做網頁，拿到的很可能和別人的差不多。</p>
<section class="sum"><h2>3 個重點</h2><ol><li>同一句「幫我做一個咖啡店首頁」問 Gemini 兩次，配色與版型幾乎一樣。</li><li>一般認為，AI 偏向最常見的樣子；這是分析推測。</li><li>多寫一句風格，樣子明顯不同（只試 1 次，不是保證）。</li></ol></section>
</div></main>
<div class="fabs"><a class="fab" href="#toc">☰ 目錄</a></div>''')
page("healing","top","談晴說礙 文章第一屏",f'''{HEAL_HD}<div class="prog"><b style="width:3%"></b></div>
<main class="art"><div class="w"><a class="bk" href="#">← 全部文章</a>
<div class="tags"><span class="pill">薪資</span><span class="pill">主計總處</span></div>
<h1>近 7 成員工，領不到平均月薪</h1>
<div class="meta">2026-11-12・閱讀約 6 分鐘・資料：主計總處</div>
<div class="jump"><a href="#">▶ 看影片版</a><a href="#">🔎 查自己的行業</a></div>
<p class="lead">結論：2025 年平均月薪 47,884 元，但每 10 人約有 7 人領得比這個數字少；比較貼近多數人的是中位數 38,406 元。</p>
<section class="sum"><h2>3 個重點</h2><ol><li>平均經常性薪資 47,884 元，中位數 38,406 元，差 9,478 元。</li><li>69.74% 的員工領不到平均；2026 上半年升到 70.03%。</li><li>看薪水別只看平均，先看中位數，再查自己的行業。</li></ol></section>
</div></main>
<div class="fabs"><a class="fab" href="#toc">☰ 目錄</a></div>''')

# ---------- 文章中段 ----------
def sheet(items,cur):
    li="".join(f'<li class="{"on" if i==cur else ""}"><a href="#s{i+1}">{t}</a></li>' for i,t in enumerate(items))
    return f'<div class="sheet" id="toc"><div class="bd"><div class="gr"></div><div class="hh"><span>本文目錄</span><a class="btn" href="#!">關閉</a></div><ol>{li}</ol></div></div>'
def rail(items,cur): return '<aside class="rail"><b>本文目錄</b>'+"".join(f'<a class="{"on" if i==cur else ""}" href="#s{i+1}">{t}</a>' for i,t in enumerate(items))+'</aside>'
def lightbox(cap): return f'<div class="lbx" id="lb"><div class="t"><a class="btn" href="#!">← 返回</a><span class="sp"></span><a class="btn fill" href="#" style="background:#5b63e8;border-color:#5b63e8;color:#fff">下載原圖</a></div><div class="s"><div style="width:140%;aspect-ratio:4/3;background:repeating-linear-gradient(45deg,#2a2d5a,#2a2d5a 10px,#1b1e44 10px,#1b1e44 20px);display:flex;align-items:center;justify-content:center;color:#aab">原尺寸圖（雙指可放大・可左右拖）</div></div><div class="c">{cap}</div></div>'
def vid(t,dur,note): return f'<div class="vid"><div class="pv"><div class="pl"><svg width="26" height="26" viewBox="0 0 24 24"><path d="M7 4l14 8-14 8z" fill="#222"/></svg></div>{f"<span class=du>{dur}</span>" if dur else ""}</div><div class="bar"><b>{t}</b><div class="acts"><a class="btn fill" href="#">▶ 播放</a><a class="btn" href="#">⬇ 下載 MP4</a></div><div class="nt">{note}</div></div></div>'

# CaffAIne 中段
cit=["這個實測怎麼做","兩次結果像到什麼程度","影片重點","三次請求對照","自己照做：加一句風格","延伸閱讀"]
rows=[("背景色","米白底"),("區塊名稱","都叫「我們的堅持」"),("版型","左文右圖"),("卡片","三欄小卡片"),("按鈕","右上角深色")]
cs="".join(f'<g transform="translate(0,{34+i*40})"><text x="0" y="14" font-size="14" fill="#1c2052" font-weight="600">{a}</text><text x="0" y="31" font-size="12" fill="#4a4f7a">{b}</text><circle cx="262" cy="16" r="12" fill="#5b63e8"/><path d="M256 16l4 4 7-8" stroke="#fff" stroke-width="2.6" fill="none" stroke-linecap="round"/><circle cx="318" cy="16" r="12" fill="#5b63e8"/><path d="M312 16l4 4 7-8" stroke="#fff" stroke-width="2.6" fill="none" stroke-linecap="round"/></g>' for i,(a,b) in enumerate(rows))
chart_c=f'''<div class="ch" id="s2"><h3 class="ct">兩次沒指定風格，5 項全部一樣</h3><p class="cs">同一句提示詞各送一次，Gemini 的結果逐項比對</p>
<svg viewBox="0 0 354 240" role="img" aria-label="兩次請求五項逐項比對，全部相同"><text x="262" y="14" font-size="12" fill="#4a4f7a" text-anchor="middle">第 1 次</text><text x="318" y="14" font-size="12" fill="#4a4f7a" text-anchor="middle">第 2 次</text><line x1="0" x2="354" y1="26" y2="26" stroke="#dcdff5"/>{cs}</svg>
<div class="src"><span>資料：本站 2026/11/16 實測</span><span>圖表：示意，實作由文章 JSON 帶入</span></div></div>'''
body_c=f'''{CAFF_HD}<div class="prog"><b style="width:46%"></b></div>
<div class="art-wrap">{rail(cit,1)}<main class="art"><div class="w">
<h2 class="h" id="s1">這個實測怎麼做</h2>
<p>我用 Gemini API 做了三次請求，時間是 2026/11/16 下午，台北時間。前兩次是完全同一句話：「幫我做一個咖啡店首頁。」第三次在這句後面多加了風格說明。</p>
<section class="term"><h3>名詞解釋</h3><dl><dt>提示詞</dt><dd>你對 AI 下的那句話。話怎麼講，結果就怎麼不同。</dd><dt>版型</dt><dd>畫面怎麼排：文字放哪、圖放哪、卡片分幾欄。</dd><dt>單檔 HTML</dt><dd>文字和樣式都在同一個檔案，存起來點兩下就能開。</dd></dl></section>
<h2 class="h" id="s2x" style="display:none"></h2>
{chart_c}
<figure class="fig"><a class="im" href="#lb"><div class="ph">網頁截圖（第 1 次 vs 第 2 次）</div><span class="zm">🔍 點開放大</span></a><figcaption>兩份結果並排：同樣的米白底、左文右圖。點圖可看原尺寸並下載。</figcaption></figure>
<h2 class="h" id="s3">影片重點</h2>
{vid("為什麼 AI 做的網頁，都長一個樣？","0:54","想先看重點可以播這支影片；原因那一鏡的色塊是示意，不是實測比例。")}
<h2 class="h" id="s4">三次請求對照</h2>
<div class="tc"><div class="row"><b>第 1 次</b><dl><dt>提示詞</dt><dd>幫我做一個咖啡店首頁</dd><dt>風格</dt><dd>沒指定</dd><dt>結果</dt><dd>米白底、左文右圖</dd></dl></div>
<div class="row"><b>第 2 次</b><dl><dt>提示詞</dt><dd>幫我做一個咖啡店首頁</dd><dt>風格</dt><dd>沒指定</dd><dt>結果</dt><dd>與第 1 次幾乎一樣</dd></dl></div>
<div class="row hi"><b>第 3 次・加風格</b><dl><dt>提示詞</dt><dd>同上＋風格說明</dd><dt>風格</dt><dd>日本咖啡館手寫菜單</dd><dt>結果</dt><dd>明顯不同（只試 1 次）</dd></dl></div></div>
<table class="tt"><tr><th>次序</th><th>提示詞</th><th>風格</th><th>結果</th></tr><tr><td>第 1 次</td><td>幫我做一個咖啡店首頁</td><td>沒指定</td><td>米白底、左文右圖</td></tr><tr><td>第 2 次</td><td>同上</td><td>沒指定</td><td>與第 1 次幾乎一樣</td></tr><tr><td><b>第 3 次</b></td><td>同上＋風格說明</td><td>日本咖啡館手寫菜單</td><td>明顯不同（只試 1 次）</td></tr></table>
<h2 class="h" id="s5">自己照做：加一句風格</h2>
<section class="st"><h3>3 分鐘做法</h3><ol><li>先寫要做什麼：「幫我做一個咖啡店首頁。」</li><li>再補三件事：參考哪裡、要什麼、不要什麼。</li><li>複製下面的範例，換成你自己的店。</li></ol>
<div class="pr"><div class="prh"><b>範例提示詞</b><a class="btn" href="#">複製</a></div><p>幫我做一個咖啡店首頁。風格參考日本咖啡館的手寫菜單，暖木色、手繪線條；不要三欄小卡片，不要米白底配深色按鈕。</p></div></section>
<div class="cal">提醒：這次只試了 1 次，加了風格「明顯不同」不等於每次都有效，建議多試幾次。</div>
<section class="more" id="s6"><h2>延伸閱讀</h2><div class="rel"><a href="#"><span class="pill">提示詞</span><b>同一句話問 AI 兩次，答案為什麼不一樣？</b><span class="m">3 分鐘</span></a><a href="#"><span class="pill">影片存檔</span><b>這支影片的動畫，是我叫 AI 做的</b><span class="m">3 分鐘</span></a></div></section>
<details class="srcs"><summary>出處與資料說明（3）</summary><ol><li>本站 2026/11/16 Gemini 實測紀錄</li><li>Playwright 1280×800 截圖逐項量測</li><li>（其餘出處照文章 JSON 帶入）</li></ol></details>
</div></main></div>
<div class="fabs"><a class="fab" href="#toc">☰ 目錄</a><a class="fab top" href="#" aria-label="回頁首">↑</a></div>{sheet(cit,1)}{lightbox("第 1 次 vs 第 2 次：同樣的米白底、左文右圖。")}'''
page("caffaine","mid","CaffAIne 文章中段",body_c)

# 談晴說礙 中段
hit_=["平均和中位數差在哪","一眼看懂：7 成","數字對照","影片版","怎麼查自己的行業","延伸閱讀"]
bars=f'''<svg viewBox="0 0 354 150" role="img" aria-label="平均 47,884 元，中位數 38,406 元，差 9,478 元">
<text x="0" y="16" font-size="13" fill="#6e5340">平均經常性薪資</text><rect x="0" y="24" width="354" height="30" rx="3" fill="#8a6a4f"/><text x="348" y="45" font-size="16" font-weight="700" fill="#fff" text-anchor="end">47,884 元</text>
<text x="0" y="84" font-size="13" fill="#6e5340">中位數（排在正中間那個人）</text><rect x="0" y="92" width="284" height="30" rx="3" fill="#c5782b"/><text x="278" y="113" font-size="16" font-weight="700" fill="#fff" text-anchor="end">38,406 元</text>
<line x1="284" x2="354" y1="107" y2="107" stroke="#965012" stroke-width="1.5" stroke-dasharray="3 3"/><text x="354" y="140" font-size="13" fill="#965012" text-anchor="end" font-weight="700">差 9,478 元</text></svg>'''
dots="".join(f'<circle cx="{(i%20)*17.3+8}" cy="{(i//20)*17.3+8}" r="6.2" fill="{"#c5782b" if i<70 else "#e6d9c2"}"/>' for i in range(100))
waffle=f'<svg viewBox="0 0 354 94" role="img" aria-label="每100位員工約70位領不到平均">{dots}</svg>'
chart1=f'<div class="ch" id="s1c"><h3 class="ct">平均比中位數高 9,478 元</h3><p class="cs">2025 年平均經常性薪資 vs 中位數（元／月）</p>{bars}<div class="src"><span>資料：主計總處</span><span>2025 年</span></div></div>'
chart2=f'<div class="ch" id="s2"><h3 class="ct">每 100 人，約 70 人領不到平均</h3><p class="cs">69.74%（2025），2026 上半年 70.03%</p><div class="lg2"><span><i style="background:#c5782b"></i>低於平均（約 70 人）</span><span><i style="background:#e6d9c2"></i>平均以上（約 30 人）</span></div>{waffle}<div class="src"><span>資料：主計總處</span><span>圖示取整數，實際 69.74%</span></div></div>'
body_h=f'''{HEAL_HD}<div class="prog"><b style="width:46%"></b></div>
<div class="art-wrap">{rail(hit_,0)}<main class="art"><div class="w">
<h2 class="h" id="s1">平均和中位數，差在哪</h2>
<p>想像 10 個人排成一排，領最多的那位月薪特別高，把「平均」拉上去；排在正中間的那位，才是「中位數」。</p>
<section class="term"><h3>名詞解釋</h3><dl><dt>平均數</dt><dd>所有人的薪水加起來，除以人數。容易被少數高薪拉高。</dd><dt>中位數</dt><dd>把所有人由低排到高，站在正中間那位的薪水。</dd></dl></section>
{chart1}
<h2 class="h" id="s2x" style="display:none"></h2>
{chart2}
<figure class="fig"><a class="im" href="#lb"><div class="ph">貼文圖 2／3</div><span class="zm">🔍 點開放大</span></a><figcaption>IG 貼文原圖（1080×1350），點開可放大並下載。</figcaption></figure>
<h2 class="h" id="s3">數字對照</h2>
<div class="tc"><div class="row"><b>平均經常性薪資</b><dl><dt>2025 年</dt><dd>47,884 元</dd></dl></div><div class="row"><b>中位數</b><dl><dt>2025 年</dt><dd>38,406 元</dd></dl></div><div class="row hi"><b>領不到平均的比例</b><dl><dt>2025 年</dt><dd>69.74%</dd><dt>2026 上半年</dt><dd>70.03%</dd></dl></div></div>
<table class="tt"><tr><th>項目</th><th>2025 年</th><th>2026 上半年</th></tr><tr><td>平均經常性薪資</td><td class="n">47,884 元</td><td class="n">—</td></tr><tr><td>中位數</td><td class="n">38,406 元</td><td class="n">—</td></tr><tr><td><b>領不到平均的比例</b></td><td class="n">69.74%</td><td class="n">70.03%</td></tr></table>
<h2 class="h" id="s4">影片版</h2>
{vid("近 7 成員工，領不到平均月薪","","1 分鐘內看完重點；影片可下載，轉傳給朋友也行。")}
<h2 class="h" id="s5">怎麼查自己的行業</h2>
<section class="st"><h3>3 步查到自己的位置</h3><ol><li>打開主計總處的薪資統計查詢。</li><li>選你的行業，看「經常性薪資」的中位數。</li><li>和自己的薪水比：高於或低於，都只是參考位置。</li></ol></section>
<div class="cal">數字背後：中位數不是「應得的薪水」，只是多數人現在的位置。</div>
<section class="more" id="s6"><h2>延伸閱讀</h2><div class="rel"><a href="#"><span class="pill">最低工資</span><b>第一份全職工作，明年起月薪至少 30,900 元</b><span class="m">6 分鐘</span></a><a href="#"><span class="pill">學貸</span><b>有學貸的人：利率降到 0.775%，寬限期變 2 年</b><span class="m">6 分鐘</span></a></div></section>
<details class="srcs"><summary>出處與資料說明（3）</summary><ol><li>主計總處：薪資與生產力統計（2025 年）</li><li>（其餘出處照文章 JSON 帶入）</li></ol></details>
</div></main></div>
<div class="fabs"><a class="fab" href="#toc">☰ 目錄</a><a class="fab top" href="#" aria-label="回頁首">↑</a></div>{sheet(hit_,0)}{lightbox("IG 貼文圖 2／3。")}'''
page("healing","mid","談晴說礙 文章中段",body_h)
print("ok")
