// 頻道③ 版型 v3：依網路受歡迎風格做的六種（A 白紙大字／B 手繪筆記／C 便當格／D 新粗獷／E 對話氣泡／F 日系排版）。
// 同一組 4 張內容（封面、新聞卡、比較表、待截圖頁），1080×1350；裝飾全為 SVG／CSS，不用 AI 生圖，不放比比。
// 字體：容器只有文泉驛正黑（單一字重）＋ Inter（拉丁與數字）。中文「粗」靠 -webkit-text-stroke 補，見 .W/.w。
const FONT="'Inter','WenQuanYi Zen Hei','文泉驛正黑',sans-serif";
const logo=(s,a,b,cut)=>`<svg width="${s}" height="${s}" viewBox="60 100 390 310" style="display:block;flex:none"><rect x="84" y="120" width="166" height="190" rx="36" fill="${a}"/><rect x="262" y="202" width="166" height="190" rx="36" fill="${b}"/><path d="M130 232L160 262L215 187" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M305 257L385 337M385 257L305 337" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`;
const T={what:'微軟向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。',say:'公司說是為員工增加彈性。媒體把它和 AI 投資成本連在一起，這是媒體的解讀，不是公司原話。',diff:'看到「AI 導致裁員」的標題時，先分清「公司說的原因」和「媒體猜的原因」。',ph1:'ChatGPT 對「分帳」題的完整回答畫面，需看得到提問與互動元件',ph2:'要遮：聊天紀錄、帳號名稱、分頁列',key:'這題 2 次裡有【__】次出現互動元件；金額與 Excel 差【__】元。',cond:'每題都記：差幾元、有無互動元件、能不能點、有無引條文。測試條件：【待填】日期、方案、網頁或手機'};
const TBL=[['題目','我問什麼','怎麼驗'],['分帳','4 人聚餐分帳','Excel 自算'],['比較','三個手機方案','逐格對數字'],['試算','房貸月付','Excel PMT'],['流程','請假流程圖','查有無漏步'],['純知識','特休怎麼算','看有沒有硬塞']];
const CHIPS=['微軟 6 萬人','紐約新法','Claude Duet'];
const TAGS=['第 45 週｜第 1 版','查證 01｜第 1 版｜11/03','實測 01｜第 1 版｜11/03','實測 01｜第 1 版｜11/03'];
const RIGHT=['10/28 ~ 11/03','2/6','3/7','4/7'];
const disc=()=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜自製圖文</span><span>圖文含 AI 協助</span></div>`;
const camera=(c,s,sw=4)=>`<svg width="${s}" height="${s}" viewBox="0 0 64 64" fill="none" stroke="${c}" stroke-width="${sw}" stroke-linejoin="round" stroke-linecap="round" style="display:block"><rect x="6" y="14" width="52" height="38" rx="8"/><circle cx="32" cy="33" r="10"/><path d="M22 14l4-6h12l4 6"/></svg>`;
const rng=s=>()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
const tbl=(w,cls='')=>`<table class="${cls}"><colgroup>${w.map(x=>`<col style="width:${(x*100/w.reduce((a,b)=>a+b)).toFixed(2)}%">`).join('')}</colgroup>${TBL.map((r,i)=>`<tr>${r.map(c=>i?`<td>${c}</td>`:`<th>${c}</th>`).join('')}</tr>`).join('')}</table>`;

const BASE=`*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1350px;overflow:hidden}
body{position:relative;font-family:${FONT};color:var(--tx);background-color:var(--bg);-webkit-font-smoothing:antialiased}
.col{position:absolute;left:64px;right:64px;top:64px;bottom:136px;display:flex;flex-direction:column;gap:28px}.fx{flex:1;min-height:0}
.disc{position:absolute;left:64px;right:64px;bottom:60px;height:44px;display:flex;justify-content:space-between;align-items:center;font-size:30px;line-height:40px;white-space:nowrap;color:var(--tx2);z-index:2}
.W{font-weight:700;-webkit-text-stroke:.03em currentColor;line-height:1.2;letter-spacing:.02em}.w{font-weight:700;-webkit-text-stroke:.012em currentColor}
.disc b{font-weight:700;-webkit-text-stroke:.012em currentColor;color:var(--tx)}
.ni{font-family:'Inter';font-weight:800;letter-spacing:-.02em}
.top{display:flex;justify-content:space-between;align-items:center;gap:24px}.ser{display:flex;align-items:center;gap:16px;font-size:36px;line-height:1.2;white-space:nowrap}
.abs{position:absolute}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}th{font-weight:700;-webkit-text-stroke:.012em currentColor}
.dcw{position:absolute;left:0;top:0;pointer-events:none}`;

// ============ A 白紙大字 ============
const A=(()=>{
 const css=`:root{--bg:#FAF8F3;--tx:#1B1B1B;--tx2:#3F3D39;--ac:#C63D12;--ln:#1B1B1B}`+BASE+`
.rt{font-size:30px;line-height:1.2;color:var(--tx2);white-space:nowrap}
.cat{font-size:36px;color:var(--ac);letter-spacing:.12em}
.big{font-size:128px;line-height:1.18}.big em{font-style:normal;color:var(--ac)}
.sub{font-size:46px;line-height:1.4}.chips{font-size:36px;line-height:1.4;color:var(--tx2)}.chips i{font-style:normal;color:var(--ac);padding:0 .35em}
.swp{display:flex;justify-content:space-between;align-items:center;gap:24px;border-top:3px solid var(--ln);padding-top:24px}
.swp .go{font-size:40px;color:var(--ac);white-space:nowrap}
.tag{border:2.5px solid var(--ln);padding:4px 18px;font-size:30px;line-height:1.3;white-space:nowrap}
.badge{border:2.5px solid var(--ac);color:var(--ac);padding:4px 18px;font-size:30px;line-height:1.3;white-space:nowrap}
.num{font-size:140px;line-height:1.2;color:var(--ac)}
.ttl{font-size:60px;line-height:1.2;white-space:nowrap}.ttl2{font-size:62px;line-height:1.2}
.meta{font-size:32px;line-height:1.4;color:var(--tx2)}.meta i{font-style:normal;padding:0 .5em;color:var(--ac)}
.blk{border-top:2.5px solid var(--ln);padding-top:16px}.blk h3{font-size:34px;line-height:1.3;color:var(--ac);margin-bottom:6px}.blk p{font-size:40px;line-height:1.5}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
th{font-size:34px;text-align:left;padding:0 18px;border-bottom:4px solid var(--ln);height:84px}td{font-size:38px;padding:0 18px;border-bottom:1.5px solid rgba(27,27,27,.35)}td:first-child{color:var(--ac);font-weight:700;-webkit-text-stroke:.012em currentColor}
.note{font-size:32px;line-height:1.5;color:var(--tx2)}
.ph{border:4px dashed var(--ln);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;text-align:center;padding:0 40px}.ph b{font-size:64px;line-height:1.2}.ph p{font-size:34px;line-height:1.5}.ph p.s{font-size:32px;color:var(--tx2)}
.key{font-size:36px;line-height:1.5}.key b{color:var(--ac)}`;
 const top=n=>`<div class="top"><div class="ser" data-o="系列標">${logo(56,'#1B1B1B','#C63D12','#FAF8F3')}<span class="w">本週 AI 三則</span></div><div class="rt" data-o="右標">${RIGHT[n]}${n?' &gt;':''}</div></div>`;
 const brow=(n,b)=>`<div class="brow"><div class="badge w" data-o="標章">${b}</div><div class="tag" data-o="角標">${TAGS[n]}</div></div>`;
 const pages=[
 `<div class="col">${top(0)}<div class="fx"></div><div class="cat w" data-o="分類">AI 週報</div><div class="big W" data-o="主標">三則 AI 新聞<br>只講跟<em>上班有關</em></div><div class="sub w" data-o="副標">每則附來源、日期、可信度</div><div class="chips" data-o="膠囊">微軟 6 萬人<i>／</i>紐約新法<i>／</i>Claude Duet</div><div class="fx"></div><div class="swp" data-o="滑動列"><span class="go w">滑動看 3 則 &gt;</span><span class="tag">${TAGS[0]}</span></div></div>${disc()}`,
 `<div class="col">${top(1)}<div class="num ni" data-o="序號" style="font-size:118px">01</div><div class="ttl W" data-o="標題">微軟提出約 6 萬人自願離職方案</div><div class="meta" data-o="資訊">事件日 10/26 美東<i>｜</i>查證日 11/03<i>｜</i>信心度 中</div><div class="blk" data-o="b1"><h3 class="w">發生什麼</h3><p>${T.what}</p></div><div class="blk" data-o="b2"><h3 class="w">微軟怎麼說</h3><p>${T.say}</p></div><div class="blk" data-o="b3"><h3 class="w">對上班族差在哪</h3><p>${T.diff}</p></div><div class="fx"></div>${brow(1,'整理自新聞｜我沒親自測')}</div>${disc()}`,
 `<div class="col">${top(2)}<div class="num ni" data-o="序號" style="font-size:110px">02</div><div class="ttl2 W" data-o="標題">我怎麼測：5 種題目 × 2 次</div><div class="fx" data-o="表">${tbl([180,380,392])}</div><div class="note" data-o="條件">${T.cond}</div>${brow(2,'自製表格｜非 AI 生成')}</div>${disc()}`,
 `<div class="col">${top(3)}<div class="num ni" data-o="序號" style="font-size:110px">03</div><div class="ttl2 W" data-o="標題">步驟 1　它真的變出計算器了</div><div class="ph fx" data-o="截圖框">${camera('#1B1B1B',92,3.5)}<b class="W">待 Andy 截圖</b><p>${T.ph1}</p><p class="s">${T.ph2}</p></div><div class="key" data-o="重點"><b class="w">重點：</b>${T.key}</div>${brow(3,'截圖為實測｜非 AI 生成')}</div>${disc()}`];
 return {css,pages,base:'#FAF8F3'};
})();

// ============ B 手繪筆記 ============
const B=(()=>{
 const css=`:root{--bg:#FBF9F1;--tx:#222222;--tx2:#3A3A36;--hl:#FFE45C;--pk:#C93560;--bl:#2459B5}`+BASE+`
body{background-image:linear-gradient(rgba(70,110,180,.13) 1.5px,transparent 1.5px),linear-gradient(90deg,rgba(70,110,180,.13) 1.5px,transparent 1.5px);background-size:36px 36px}
.rt{font-size:30px;line-height:1.2;white-space:nowrap;border:3px solid var(--tx);border-radius:255px 15px 225px 15px/15px 225px 15px 255px;padding:4px 20px}
.hl{background:linear-gradient(transparent 52%,var(--hl) 52%,var(--hl) 92%,transparent 92%);padding:0 .12em;-webkit-box-decoration-break:clone;box-decoration-break:clone}
.hlp{background:linear-gradient(transparent 52%,#FFC2D1 52%,#FFC2D1 92%,transparent 92%);padding:0 .12em}
.rough{border:3.5px solid var(--tx);border-radius:255px 15px 225px 15px/15px 225px 15px 255px}
.rough2{border:3.5px solid var(--tx);border-radius:15px 225px 15px 255px/255px 15px 225px 15px}
.big{margin:52px 0 0 8px;font-size:124px;line-height:1.2;transform:rotate(-1.8deg);transform-origin:left center;filter:url(#wob)}
.sub{font-size:46px;line-height:1.4;text-decoration:underline wavy var(--pk);text-decoration-thickness:3px;text-underline-offset:10px}
.notes{display:flex;gap:44px;padding:8px 0}.sn{flex:1;font-size:38px;line-height:1.3;padding:24px 20px;text-align:center;border:3px solid var(--tx);box-shadow:5px 6px 0 rgba(34,34,34,.18)}
.tag{font-size:30px;line-height:1.3;white-space:nowrap;border:3px dashed var(--tx);padding:4px 18px;border-radius:12px;background:#FFFFFF}
.badge{font-size:30px;line-height:1.3;white-space:nowrap;background:var(--hl);padding:4px 20px;border:3px solid var(--tx)}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.ttl{font-size:58px;line-height:1.25;transform:rotate(-1deg);transform-origin:left;filter:url(#wob)}
.chip{font-size:32px;line-height:1.3;white-space:nowrap;padding:4px 18px;border:3px solid var(--tx);border-radius:255px 15px 225px 15px/15px 225px 15px 255px;background:#fff}
.nb{padding:16px 28px 18px;background:#FFFFFF;box-shadow:5px 6px 0 rgba(34,34,34,.15)}.nb h3{font-size:34px;line-height:1.3;margin-bottom:4px;color:var(--bl)}.nb p{font-size:36px;line-height:1.5}
.nb.y{background:#FFF4B8}.nb.y h3{color:var(--pk)}
th{font-size:34px;text-align:left;padding:0 18px;background:var(--hl);height:84px;border-bottom:3.5px solid var(--tx)}td{font-size:38px;padding:0 18px;border-bottom:2.5px dashed rgba(34,34,34,.5)}td:first-child{color:var(--bl);font-weight:700;-webkit-text-stroke:.012em currentColor}
.tw{overflow:hidden;background:#fff;box-shadow:5px 6px 0 rgba(34,34,34,.15)}
.note{font-size:32px;line-height:1.5;color:var(--tx2)}
.ph{background:#fff;border:5px dashed var(--tx);border-radius:30px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;text-align:center;padding:0 40px}.ph b{font-size:62px;line-height:1.2}.ph p{font-size:34px;line-height:1.5}.ph p.s{font-size:32px;color:var(--tx2)}
.key{font-size:36px;line-height:1.5;padding:14px 22px;background:#FFF4B8;border:3px solid var(--tx)}`;
 const defs=`<svg width="0" height="0" style="position:absolute"><filter id="wob" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="3" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.2"/></filter></svg>`;
 const top=n=>`<div class="top"><div class="ser" data-o="系列標">${logo(56,'#222222','#FFC800','#FBF9F1')}<span class="w">本週 AI 三則</span></div><div class="rt w" data-o="右標">${RIGHT[n]}</div></div>`;
 const brow=(n,b)=>`<div class="brow"><div class="badge w" data-o="標章">${b}</div><div class="tag" data-o="角標">${TAGS[n]}</div></div>`;
 const P=(d,x,y,w=3.5,c='#222')=>`<path class="dc" d="${d}" transform="translate(${x} ${y})" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
 const svg=(x,y,w,h,inner,rot=0)=>`<svg class="abs" style="left:${x}px;top:${y}px;transform:rotate(${rot}deg)" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${inner}</svg>`;
 const star=(c)=>P('M30 4 L37 22 L56 23 L41 35 L46 54 L30 43 L14 54 L19 35 L4 23 L23 22 Z',0,0,3.5,c);
 const bulb=P('M32 6 C16 6 8 20 14 32 C18 40 22 42 22 50 L42 50 C42 42 46 40 50 32 C56 20 48 6 32 6 Z M24 58 L40 58 M27 64 L37 64',0,0,3.5)+P('M32 -4 V-12 M6 8 L-1 2 M58 8 L65 2',0,8,3.5,'#C93560');
 const arrow=P('M4 44 C30 50 60 40 84 14 M84 14 L62 16 M84 14 L80 36',0,0,4,'#C93560');
 const check=P('M6 30 L26 50 L64 6',0,0,7,'#2E9E5B');
 const tape=(x,y,w,rot,c='rgba(255,214,102,.85)')=>`<div class="abs" style="left:${x}px;top:${y}px;width:${w}px;height:44px;background:${c};transform:rotate(${rot}deg);clip-path:polygon(0 8%,4% 0,8% 10%,12% 0,100% 0,96% 25%,100% 50%,96% 75%,100% 100%,12% 100%,8% 88%,4% 100%,0 92%,3% 50%)"></div>`;
 const pages=[
 `${defs}${svg(560,176,70,70,star('#E8A400'),10)}${svg(350,926,100,60,P('M4 30 C30 24 60 34 90 30 M90 30 L70 14 M90 30 L70 46',0,0,4,'#C93560'),0)}<div class="col">${top(0)}<div class="fx"></div><div class="abs w" data-o="懶人包" style="left:672px;top:150px;width:300px;height:78px;font-size:42px;line-height:72px;text-align:center;background:rgba(255,214,102,.9);transform:rotate(4deg);clip-path:polygon(0 8%,3% 0,6% 10%,9% 0,100% 0,97% 25%,100% 50%,97% 75%,100% 100%,9% 100%,6% 88%,3% 100%,0 92%,2.5% 50%)">懶人包</div><div class="big W" data-o="主標">三則 AI 新聞<br>只講跟<span class="hl">上班有關</span></div><div class="sub w" data-o="副標">每則附來源、日期、可信度</div><div class="notes" data-o="便利貼"><div class="sn w" style="background:#FFF0A3;transform:rotate(-2deg)">微軟 6 萬人</div><div class="sn w" style="background:#FFD1DC;transform:rotate(1.5deg)">紐約新法</div><div class="sn w" style="background:#CFE6FF;transform:rotate(-1deg)">Claude Duet</div></div><div class="go2 w" data-o="滑動" style="font-size:42px;line-height:1.3;color:var(--pk)">滑動看 3 則 &gt;</div><div class="fx"></div>${brow(0,'整理自新聞｜附來源')}</div>${disc()}`,
 `${defs}${svg(920,920,64,70,bulb,0)}<div class="col">${top(1)}<div class="ttl W" data-o="標題" style="margin:18px 0"><span class="hl">新聞 1／3</span>　微軟提出約 6 萬人<br>自願離職方案</div><div class="brow" style="justify-content:flex-start;gap:26px"><div class="chip" data-o="日">事件日 10/26 美東</div><div class="chip" data-o="查證">查證日 11/03</div><div class="chip" data-o="信心">信心度 中</div></div><div class="nb rough" data-o="n1"><h3 class="w">發生什麼</h3><p>${T.what}</p></div><div class="nb rough2" data-o="n2"><h3 class="w">微軟怎麼說</h3><p>${T.say}</p></div><div class="nb y rough" data-o="n3" style="padding-right:96px"><h3 class="w">對上班族差在哪</h3><p>${T.diff}</p></div><div class="fx"></div>${brow(1,'整理自新聞｜我沒親自測')}</div>${disc()}`,
 `${defs}<div class="col">${top(2)}<div class="ttl W" data-o="標題" style="margin-top:22px"><span class="hl">我怎麼測</span>：5 種題目 × 2 次</div><div class="fx rough tw" data-o="表">${tbl([180,380,392])}</div><div class="note" data-o="條件">${T.cond}</div>${brow(2,'自製表格｜非 AI 生成')}</div>${disc()}`,
 `${defs}${tape(40,236,150,-8)}${tape(890,236,150,8)}<div class="col">${top(3)}<div class="ttl W" data-o="標題" style="margin-top:22px"><span class="hl">步驟 1</span>　它真的變出計算器了</div><div class="ph fx" data-o="截圖框">${camera('#222',92,3.5)}<b class="W">待 Andy 截圖</b><p>${T.ph1}</p><p class="s">${T.ph2}</p></div><div class="key" data-o="重點"><span class="w">重點：</span>${T.key}</div>${brow(3,'截圖為實測｜非 AI 生成')}</div>${disc()}`];
 return {css,pages,base:'#FBF9F1'};
})();

// ============ C 便當格資訊卡 ============
const C=(()=>{
 const css=`:root{--bg:#F3F4F6;--tx:#14171C;--tx2:#3B424D}`+BASE+`
.cell{background:#fff;border-radius:24px;padding:24px 28px;position:relative;box-shadow:0 2px 0 rgba(20,23,28,.06)}
.mint{background:#CDEFE0}.lav{background:#DDD3F7}.cream{background:#FFEDB3}
.row{display:flex;gap:24px}.row>*{flex:1;min-width:0}
.rt{font-size:30px;line-height:1.2;white-space:nowrap;background:#fff;border-radius:999px;padding:6px 22px}
.big{font-size:104px;line-height:1.2}.big2{font-size:48px;line-height:1.3}
.stat{font-size:110px;line-height:1;font-family:'Inter';font-weight:800;letter-spacing:-.03em}.lbl{font-size:34px;line-height:1.35;color:var(--tx2);margin-top:10px}
.ic{display:block;margin-bottom:12px}
.tag{font-size:30px;line-height:1.3;white-space:nowrap;background:#fff;border-radius:999px;padding:6px 22px}
.badge{font-size:30px;line-height:1.3;white-space:nowrap;background:#14171C;color:#fff;border-radius:999px;padding:6px 24px}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.cell h3{font-size:34px;line-height:1.3;margin-bottom:8px;display:flex;align-items:center;gap:12px}.cell h3 svg{margin:0;width:44px;height:44px}.cell p{font-size:38px;line-height:1.5}
.ttl{font-size:58px;line-height:1.25}
.mrow{display:flex;gap:16px}.mrow>*{flex:1}.m1{font-size:34px;line-height:1.35;white-space:nowrap}.m1 b{display:block;font-size:30px;color:var(--tx2);font-weight:400;-webkit-text-stroke:0}
th{font-size:34px;text-align:left;padding:0 20px;height:84px;color:#fff;background:#14171C}td{font-size:38px;padding:0 20px;border-bottom:2px solid #E5E7EB}td:first-child{background:#DDD3F7;font-weight:700;-webkit-text-stroke:.012em currentColor}
.tw{padding:0;overflow:hidden}
.note{font-size:32px;line-height:1.5;color:var(--tx2)}
.ph{border:5px dashed #8A93A3;border-radius:24px;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;text-align:center;padding:0 40px}.ph b{font-size:62px;line-height:1.2}.ph p{font-size:34px;line-height:1.5}.ph p.s{font-size:32px;color:var(--tx2)}
.key{font-size:36px;line-height:1.5}`;
 const top=n=>`<div class="top"><div class="ser" data-o="系列標">${logo(56,'#14171C','#2FB583','#F3F4F6')}<span class="w">本週 AI 三則</span></div><div class="rt w" data-o="右標">${RIGHT[n]}</div></div>`;
 const brow=(n,b)=>`<div class="brow"><div class="badge w" data-o="標章">${b}</div><div class="tag" data-o="角標">${TAGS[n]}</div></div>`;
 const I=(d,c='#14171C')=>`<svg class="ic" width="52" height="52" viewBox="0 0 52 52" fill="none" stroke="${c}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
 const iDoc='<path class="dc" d="M12 6h20l10 10v30H12z M32 6v10h10 M19 26h16 M19 34h16"/>';
 const iSrc='<path class="dc" d="M8 26a18 18 0 1 0 36 0a18 18 0 1 0-36 0 M8 26h36 M26 8c-8 8-8 28 0 36 M26 8c8 8 8 28 0 36"/>';
 const iLvl='<path class="dc" d="M8 40h8V28H8z M22 40h8V16h-8z M36 40h8V8h-8z"/>';
 const iTalk='<path class="dc" d="M8 10h36v26H24l-10 8v-8H8z"/>';
 const iBulb='<path class="dc" d="M26 6a14 14 0 0 0-8 25c2 2 2 4 2 7h12c0-3 0-5 2-7a14 14 0 0 0-8-25z M20 46h12"/>';
 const iCal='<path class="dc" d="M8 12h36v32H8z M8 22h36 M17 6v10 M35 6v10"/>';
 const pages=[
 `<div class="col">${top(0)}<div class="cell lav" data-o="主標格" style="height:430px;display:flex;flex-direction:column;justify-content:center"><div class="big W">三則 AI 新聞<br>只講跟上班有關</div></div><div class="row" data-o="三格" style="height:300px"><div class="cell"><div class="stat">3</div><div class="lbl">則新聞<br>本週整理</div></div><div class="cell mint"><div class="stat">6</div><div class="lbl">筆來源<br>每則附 2 筆</div></div><div class="cell cream"><div class="stat">中</div><div class="lbl">信心度<br>三則皆是</div></div></div><div class="cell" data-o="副標格" style="flex:1"><div class="big2 w">每則附來源、日期、可信度</div><div class="mrow" style="margin-top:18px">${CHIPS.map((c,i)=>`<div class="m1 w"><b>0${i+1}</b>${c}</div>`).join('')}</div></div>${brow(0,'整理自新聞｜附來源')}</div>${disc()}`,
 `<div class="col">${top(1)}<div class="ttl W" data-o="標題" style="font-size:52px;white-space:nowrap">微軟提出約 6 萬人自願離職方案</div><div class="row" style="align-items:stretch"><div class="cell" data-o="c1" style="flex:1.3"><h3 class="w">${I(iDoc)}發生什麼</h3><p style="font-size:38px">${T.what}</p></div><div class="cell cream" data-o="c2" style="flex:.8"><h3 class="w">${I(iCal)}新聞 1／3</h3><p style="font-size:36px;line-height:1.5">事件日 10/26 美東<br>查證日 11/03<br>信心度 中</p></div></div><div class="cell" data-o="c3"><h3 class="w">${I(iTalk)}微軟怎麼說</h3><p style="font-size:38px">${T.say}</p></div><div class="cell mint" data-o="c4"><h3 class="w">${I(iBulb)}對上班族差在哪</h3><p style="font-size:38px">${T.diff}</p></div><div class="fx"></div>${brow(1,'整理自新聞｜我沒親自測')}</div>${disc()}`,
 `<div class="col">${top(2)}<div class="ttl W" data-o="標題">我怎麼測：5 種題目 × 2 次</div><div class="cell tw fx" data-o="表">${tbl([180,380,392])}</div><div class="cell" data-o="條件" style="padding:20px 28px"><div class="note">${T.cond}</div></div>${brow(2,'自製表格｜非 AI 生成')}</div>${disc()}`,
 `<div class="col">${top(3)}<div class="ttl W" data-o="標題">步驟 1　它真的變出計算器了</div><div class="cell fx" data-o="截圖框" style="display:flex;padding:20px"><div class="ph" style="flex:1">${camera('#14171C',92,3.5)}<b class="W">待 Andy 截圖</b><p>${T.ph1}</p><p class="s">${T.ph2}</p></div></div><div class="cell cream" data-o="重點" style="padding:20px 28px"><div class="key"><span class="w">重點：</span>${T.key}</div></div>${brow(3,'截圖為實測｜非 AI 生成')}</div>${disc()}`];
 return {css,pages,base:'#F3F4F6'};
})();

// ============ D 新粗獷 ============
const D=(()=>{
 const css=`:root{--bg:#FFF8E7;--tx:#000000;--tx2:#222222}`+BASE+`
.bx{border:4px solid #000;box-shadow:8px 8px 0 #000;position:relative}
.y{background:#FFD84D}.p{background:#FF8FB1}.s{background:#6EC6FF}.wh{background:#fff}
.rt{font-size:30px;line-height:1.2;white-space:nowrap;padding:6px 20px;background:#fff}
.disc{color:#000}
.big{font-size:118px;line-height:1.25;white-space:nowrap}
.sticker{position:absolute;right:56px;top:210px;width:210px;height:210px;border-radius:50%;background:#FF8FB1;border:4px solid #000;box-shadow:6px 6px 0 #000;display:flex;align-items:center;justify-content:center;text-align:center;font-size:44px;line-height:1.2;transform:rotate(10deg);z-index:3}
.sub{font-size:48px;line-height:1.35;padding:22px 28px}
.lab{display:flex;gap:20px}.lab>*{font-size:38px;line-height:1.3;white-space:nowrap;padding:18px 22px;flex:1;text-align:center}
.tag{font-size:30px;line-height:1.3;white-space:nowrap;padding:4px 18px;background:#fff;border:3.5px solid #000}
.badge{font-size:30px;line-height:1.3;white-space:nowrap;padding:4px 20px;background:#FFD84D;border:3.5px solid #000}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.ttl{font-size:50px;line-height:1.25;padding:18px 24px 18px 132px;white-space:nowrap}
.stamp{position:absolute;left:-22px;top:50%;margin-top:-52px;width:104px;height:104px;border-radius:50%;background:#000;color:#FFD84D;border:4px solid #000;display:flex;align-items:center;justify-content:center;font-size:48px;line-height:1.1;font-family:'Inter';font-weight:800;text-align:center}
.c{padding:22px 26px}.c h3{display:inline-block;font-size:34px;line-height:1.3;background:#000;color:#fff;padding:2px 16px;margin-bottom:8px}.c p{font-size:38px;line-height:1.5}
.chip{font-size:32px;line-height:1.3;white-space:nowrap;padding:4px 18px;background:#fff;border:3.5px solid #000}
th{font-size:34px;text-align:left;padding:0 18px;height:84px;background:#000;color:#FFD84D}td{font-size:38px;padding:0 18px;border-bottom:3px solid #000}td:first-child{background:#FFD84D;font-weight:700;-webkit-text-stroke:.012em currentColor;border-right:3px solid #000}
.tw{overflow:hidden;background:#fff}
.note{font-size:32px;line-height:1.5;color:#000;padding:16px 24px}
.ph{border:5px dashed #000;background:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;text-align:center;padding:0 40px}.ph b{font-size:62px;line-height:1.2}.ph p{font-size:34px;line-height:1.5}.ph p.s2{font-size:32px}
.key{font-size:36px;line-height:1.5;padding:14px 24px}`;
 const top=n=>`<div class="top"><div class="ser" data-o="系列標">${logo(56,'#000','#FF8FB1','#FFF8E7')}<span class="w">本週 AI 三則</span></div><div class="rt w bx" data-o="右標" style="box-shadow:4px 4px 0 #000;border-width:3.5px">${RIGHT[n]}</div></div>`;
 const brow=(n,b)=>`<div class="brow"><div class="badge w" data-o="標章">${b}</div><div class="tag" data-o="角標">${TAGS[n]}</div></div>`;
 const pages=[
 `<div class="sticker w" data-o="貼紙" data-in="主卡">懶人包</div><div class="col">${top(0)}<div class="fx"></div><div class="bx y" data-o="主卡" style="padding:64px 36px 64px"><div class="big W">三則 AI 新聞<br>只講跟上班有關</div></div><div class="bx wh sub w" data-o="副標">每則附來源、日期、可信度</div><div class="lab" data-o="標籤列"><div class="bx p w">微軟 6 萬人</div><div class="bx s w">紐約新法</div><div class="bx y w">Claude Duet</div></div><div class="fx"></div>${brow(0,'整理自新聞｜附來源')}</div>${disc()}`,
 `<div class="col">${top(1)}<div class="bx s ttl W" data-o="標題"><span class="stamp" style="font-size:30px;font-family:inherit;font-weight:700;color:#FFD84D">新聞<br>1／3</span>微軟提出約 6 萬人自願離職方案</div><div class="brow" style="justify-content:flex-start;gap:26px"><div class="chip w" data-o="日">事件日 10/26 美東</div><div class="chip w" data-o="查證">查證日 11/03</div><div class="chip w" data-o="信心">信心度 中</div></div><div class="bx wh c" data-o="c1"><h3 class="w">發生什麼</h3><p>${T.what}</p></div><div class="bx wh c" data-o="c2"><h3 class="w">微軟怎麼說</h3><p>${T.say}</p></div><div class="bx y c" data-o="c3"><h3 class="w">對上班族差在哪</h3><p>${T.diff}</p></div><div class="fx"></div>${brow(1,'整理自新聞｜我沒親自測')}</div>${disc()}`,
 `<div class="col">${top(2)}<div class="bx p ttl W" data-o="標題" style="font-size:50px"><span class="stamp">02</span>我怎麼測：5 種題目 × 2 次</div><div class="bx tw fx" data-o="表">${tbl([180,380,392])}</div><div class="bx wh note" data-o="條件">${T.cond}</div>${brow(2,'自製表格｜非 AI 生成')}</div>${disc()}`,
 `<div class="col">${top(3)}<div class="bx y ttl W" data-o="標題" style="font-size:50px"><span class="stamp" style="background:#FF8FB1;color:#000">03</span>步驟 1　它真的變出計算器了</div><div class="bx wh fx" data-o="截圖框" style="display:flex;padding:20px"><div class="ph" style="flex:1">${camera('#000',92,4)}<b class="W">待 Andy 截圖</b><p>${T.ph1}</p><p class="s2">${T.ph2}</p></div></div><div class="bx s key" data-o="重點"><span class="w">重點：</span>${T.key}</div>${brow(3,'截圖為實測｜非 AI 生成')}</div>${disc()}`];
 return {css,pages,base:'#FFF8E7'};
})();

// ============ E 對話氣泡 ============
const E=(()=>{
 const css=`:root{--bg:#EEF2F7;--tx:#111827;--tx2:#364152}`+BASE+`
.hdr{display:flex;justify-content:space-between;align-items:center;gap:24px;background:#fff;border-radius:28px;padding:14px 24px}
.ser b{font-weight:700}.rt{font-size:30px;line-height:1.2;color:var(--tx2);white-space:nowrap}
.msg{display:flex;gap:18px;align-items:flex-end}.msg.u{flex-direction:row-reverse}
.av{width:68px;height:68px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center}
.bub{position:relative;border-radius:36px;padding:24px 32px;font-size:36px;line-height:1.5;max-width:866px}
.u .bub{background:#2563EB;color:#fff;border-bottom-right-radius:10px}.a .bub{background:#fff;color:var(--tx);border-bottom-left-radius:10px}
.bub b{font-weight:700;-webkit-text-stroke:.012em currentColor}.a .bub b{background:#FFE9A8;padding:0 .15em}
.q{font-size:84px;line-height:1.3}
.who{font-size:30px;line-height:1.2;color:var(--tx2);margin:0 0 8px 86px}.u .who{text-align:right;margin:0 86px 8px 0}
.tag{font-size:30px;line-height:1.3;white-space:nowrap;background:#fff;border-radius:999px;padding:6px 22px}
.badge{font-size:30px;line-height:1.3;white-space:nowrap;background:#DCEAFE;color:#12326B;border-radius:999px;padding:6px 24px}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.chips{display:flex;gap:14px;flex-wrap:wrap;margin-top:18px}.chips span{font-size:32px;margin-top:0;line-height:1.3;background:#EEF2F7;border-radius:999px;padding:4px 20px;white-space:nowrap}
th{font-size:34px;text-align:left;padding:0 16px;height:84px;color:#12326B;background:#DCEAFE}td{font-size:36px;padding:0 16px;border-bottom:2px solid #E3E8EF}td:first-child{font-weight:700;-webkit-text-stroke:.012em currentColor}
.tw{overflow:hidden;background:#fff;border-radius:28px;border-bottom-left-radius:10px}
.note{font-size:32px;line-height:1.5;color:var(--tx2)}
.ph{border:5px dashed #94A3B8;border-radius:24px;background:#F8FAFC;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;text-align:center;padding:0 36px}.ph b{font-size:60px;line-height:1.2}.ph p{font-size:34px;line-height:1.5}.ph p.s{font-size:32px;color:var(--tx2)}
.a .bub .ph b{background:none;padding:0}.day{align-self:center;font-size:30px;line-height:1.3;color:var(--tx2);background:#DDE4EE;border-radius:999px;padding:2px 22px}`;
 const user=`<svg width="68" height="68" viewBox="0 0 68 68" style="display:block"><circle cx="34" cy="34" r="34" fill="#C7D2E3"/><circle cx="34" cy="27" r="11" fill="#fff"/><path d="M12 58c3-13 11-17 22-17s19 4 22 17a34 34 0 0 1-44 0z" fill="#fff"/></svg>`;
 const ai=`<div class="av" style="background:#fff">${logo(44,'#111827','#2563EB','#fff')}</div>`;
 const hdr=n=>`<div class="hdr" data-o="頂列"><div class="ser">${logo(56,'#111827','#2563EB','#fff')}<span class="w">本週 AI 三則</span></div><div class="rt">${RIGHT[n]}</div></div>`;
 const brow=(n,b)=>`<div class="brow"><div class="badge w" data-o="標章">${b}</div><div class="tag" data-o="角標">${TAGS[n]}</div></div>`;
 const U=(t,cls='',o='問')=>`<div class="msg u" data-o="${o}"><div class="av">${user}</div><div class="bub ${cls}">${t}</div></div>`;
 const Aa=(t,o,cls='')=>`<div class="msg a" data-o="${o}"><div class="av" style="background:#fff">${logo(44,'#111827','#2563EB','#fff')}</div><div class="bub ${cls}">${t}</div></div>`;
 const pages=[
 `<div class="col">${hdr(0)}<div class="fx"></div>${U('這週 AI 有哪<b>三則</b><br>跟上班有關？','q W','問')}${Aa(`<span class="w">三則，每則附來源、日期、可信度：</span><div class="chips">${CHIPS.map(c=>`<span>${c}</span>`).join('')}</div>`,'答')}${Aa('<span class="w">往右滑，先看第 1 則 &gt;</span>','滑')}<div class="fx"></div>${brow(0,'整理自新聞｜附來源')}</div>${disc()}`,
 `<div class="col">${hdr(1)}${U('<b>新聞 1／3</b>　微軟提出約 6 萬人自願離職方案','','問')}${Aa(`<b>發生什麼</b><br>${T.what}<br><b style="display:inline-block;margin-top:12px">微軟怎麼說</b><br>${T.say}`,'答1')}${Aa(`<b>對上班族差在哪</b><br>${T.diff}<div class="chips"><span>事件日 10/26 美東</span><span>查證日 11/03</span><span>信心度 中</span></div>`,'答2')}<div class="fx"></div>${brow(1,'整理自新聞｜我沒親自測')}</div>${disc()}`,
 `<div class="col">${hdr(2)}${U('你怎麼測？<b>5 種題目 × 2 次</b>','','問')}<div class="msg a fx" data-o="答" style="align-items:stretch;min-height:0"><div class="av" style="background:#fff;align-self:flex-end">${logo(44,'#111827','#2563EB','#fff')}</div><div class="tw" style="flex:1">${tbl([180,380,392])}</div></div><div class="note" data-o="條件">${T.cond}</div>${brow(2,'自製表格｜非 AI 生成')}</div>${disc()}`,
 `<div class="col">${hdr(3)}${U('步驟 1　它真的變出<b>計算器</b>了？','','問')}<div class="msg a fx" data-o="答" style="align-items:stretch;min-height:0"><div class="av" style="background:#fff;align-self:flex-end">${logo(44,'#111827','#2563EB','#fff')}</div><div class="bub" style="flex:1;max-width:none;display:flex;padding:20px"><div class="ph" style="flex:1">${camera('#475569',92,3.5)}<b class="W">待 Andy 截圖</b><p>${T.ph1}</p><p class="s">${T.ph2}</p></div></div></div>${Aa(`<b>重點</b>　${T.key}`,'重點')}${brow(3,'截圖為實測｜非 AI 生成')}</div>${disc()}`];
 return {css,pages,base:'#EEF2F7'};
})();

// ============ F 日系排版海報 ============
const F=(()=>{
 const css=`@font-face{font-family:'InstSerif';src:url('file:///mnt/skills/examples/canvas-design/canvas-fonts/InstrumentSerif-Regular.ttf')}
:root{--bg:#F4EFE6;--tx:#1F3A3D;--tx2:#34504F;--rd:#BC3420}`+BASE+`
.sf{font-family:'InstSerif','Inter',serif;letter-spacing:.02em}
.rt{font-size:30px;line-height:1.2;white-space:nowrap;color:var(--tx2)}
.ln{border-top:2px solid var(--tx)}
.giant{font-size:390px;line-height:1.2;letter-spacing:-.02em;font-weight:700;color:var(--tx)}
.giant2{font-size:200px;line-height:1.2;letter-spacing:0;font-weight:700;color:var(--tx)}.gi{-webkit-text-stroke:.012em currentColor}
.dot{color:var(--rd)}
.cap{font-size:54px;line-height:1.35;letter-spacing:.06em}
.vt{color:var(--tx)}
.tag{font-size:30px;line-height:1.3;white-space:nowrap;border:2px solid var(--tx);padding:4px 18px}
.badge{font-size:30px;line-height:1.3;white-space:nowrap;background:var(--rd);color:#fff;padding:4px 20px}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.chips{font-size:36px;line-height:1.5;letter-spacing:.08em}.chips i{font-style:normal;color:var(--rd);padding:0 .4em}
.sd{display:flex;gap:28px}.sd .k{flex:none;width:200px;font-size:34px;line-height:1.4;color:var(--rd);border-top:2px solid var(--tx);padding-top:14px}.sd .v{flex:1;font-size:36px;line-height:1.55;border-top:2px solid var(--tx);padding-top:14px}
.ttl{font-size:46px;line-height:1.35;letter-spacing:.04em}
.meta{font-size:32px;line-height:1.5;letter-spacing:.06em;color:var(--tx2)}.meta i{font-style:normal;color:var(--rd);padding:0 .5em}
th{font-size:34px;text-align:left;padding:0 14px;height:84px;color:var(--rd);border-top:3px solid var(--tx);border-bottom:2px solid var(--tx);letter-spacing:.06em}td{font-size:38px;padding:0 14px;border-bottom:1.5px solid rgba(31,58,61,.4)}td:first-child{color:var(--rd)}
.note{font-size:32px;line-height:1.5;color:var(--tx2)}
.ph{border:3px dashed var(--tx);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:20px;text-align:center;padding:0 40px}.ph b{font-size:60px;line-height:1.2;letter-spacing:.08em}.ph p{font-size:34px;line-height:1.5}.ph p.s{font-size:32px;color:var(--tx2)}
.key{font-size:36px;line-height:1.5}.key b{color:var(--rd)}`;
 const top=n=>`<div class="top"><div class="ser" data-o="系列標">${logo(52,'#1F3A3D','#BC3420','#F4EFE6')}<span style="letter-spacing:.12em">本週 AI 三則</span></div><div class="rt sf" data-o="右標">${RIGHT[n]}</div></div>`;
 const brow=(n,b)=>`<div class="brow"><div class="badge" data-o="標章">${b}</div><div class="tag" data-o="角標">${TAGS[n]}</div></div>`;
 const pages=[
 `<div class="col">${top(0)}<div class="ln"></div><div class="fx" style="position:relative;display:flex;flex-direction:column;justify-content:flex-end;gap:36px;min-height:0"><svg class="abs" style="left:2px;top:30px" width="60" height="60" viewBox="0 0 60 60"><circle class="dc" cx="30" cy="30" r="24" fill="#BC3420"/></svg><div class="vt abs" data-o="副標" style="right:6px;top:0;font-size:46px;line-height:1.32;text-align:center;display:flex;flex-direction:column;gap:30px;font-weight:700;-webkit-text-stroke:.012em currentColor"><div>每<br>則<br>附<br>來<br>源</div><div>日<br>期</div><div>可<br>信<br>度</div></div><div class="giant gi" data-o="巨字" style="align-self:flex-start">三則</div><div class="cap" data-o="主標" style="font-weight:700;-webkit-text-stroke:.02em currentColor">AI 新聞<span class="dot">，</span>只講跟上班有關的</div></div><div class="ln"></div><div class="chips" data-o="膠囊">微軟 6 萬人<i>／</i>紐約新法<i>／</i>Claude Duet</div>${brow(0,'整理自新聞｜附來源')}</div>${disc()}`,
 `<div class="col">${top(1)}<div class="ln"></div><div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px"><div class="giant2 gi" data-o="巨字" style="font-size:168px">離職</div><div class="meta" data-o="資訊" style="padding-bottom:16px;text-align:right">事件日 10/26 美東<br>查證日 11/03<br>信心度 中</div></div><div class="ttl w" data-o="標題">新聞 1／3<br>微軟提出約 6 萬人自願離職方案</div><div class="sd" data-o="s1"><div class="k w">發生什麼</div><div class="v">${T.what}</div></div><div class="sd" data-o="s2"><div class="k w">微軟怎麼說</div><div class="v">${T.say}</div></div><div class="sd" data-o="s3"><div class="k w">對上班族差在哪</div><div class="v">${T.diff}</div></div><div class="fx"></div>${brow(1,'整理自新聞｜我沒親自測')}</div>${disc()}`,
 `<div class="col">${top(2)}<div class="ln"></div><div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px"><div class="giant2 gi" data-o="巨字" style="font-size:230px">實測</div><div class="ttl w" data-o="標題" style="font-size:46px;width:440px;padding-bottom:20px">我怎麼測：<br>5 種題目 × 2 次</div></div><div class="fx" data-o="表">${tbl([180,380,392])}</div><div class="note" data-o="條件">${T.cond}</div>${brow(2,'自製表格｜非 AI 生成')}</div>${disc()}`,
 `<div class="col">${top(3)}<div class="ln"></div><div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px"><div class="giant2 gi" data-o="巨字" style="font-size:230px">截圖</div><div class="ttl w" data-o="標題" style="font-size:46px;width:440px;padding-bottom:20px">步驟 1<br>它真的變出計算器了</div></div><div class="ph fx" data-o="截圖框">${camera('#1F3A3D',92,3)}<b>待 Andy 截圖</b><p>${T.ph1}</p><p class="s">${T.ph2}</p></div><div class="key" data-o="重點"><b class="w">重點：</b>${T.key}</div>${brow(3,'截圖為實測｜非 AI 生成')}</div>${disc()}`];
 return {css,pages,base:'#F4EFE6'};
})();

module.exports={STY:{A,B,C,D,E,F},NAMES:{A:'A 白紙大字',B:'B 手繪筆記',C:'C 便當格資訊卡',D:'D 新粗獷',E:'E 對話氣泡',F:'F 日系排版海報'}};
