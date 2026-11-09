// 頻道③ CaffAIne IG 版型（LOGO「07 八位元衝框」視覺語言）。
// 用法：node gen.js samples   → 4 張樣張＋深色封面到 png/
//       node gen.js posts     → 3 篇範例全部張數到各 post 的 img_caffaine/
const fs=require('fs'),path=require('path');
const {chromium}=require('/opt/node-tools/node_modules/playwright');
const HERE=__dirname;
const ROOT='/home/user/tw-rotation/docs/marketing/channels/ai_intro/samples/20261104';
const LG='/home/user/tw-rotation/docs/brand/caffaine_logo/nordic/hanko/final/f07_八位元衝框_主款/';
// ---- LOGO 零件（直接取自 LOGO 的 SVG，不重畫）
function parts(file){const s=fs.readFileSync(LG+file,'utf8');
 const mark=s.match(/data-role="mark">([\s\S]*?)<\/g><g data-role="word"/)[1];
 const word=s.match(/data-role="word"[^>]*>([\s\S]*?)<\/g><g data-role="tag"/)[1];
 return {mark:`<svg width="88" height="92" viewBox="14 6 172 182" style="display:block;flex:none">${mark}</svg>`,
  word:`<svg width="340" height="61" viewBox="446 -104 656 118" style="display:block;flex:none">${word}</svg>`}}
const LOGOS={light:parts('horizontal_light.svg'),dark:parts('horizontal_dark.svg')};
// ---- 像素階梯角框（與 LOGO 外框同語言：每階 s、共兩階）
const poly=s=>{const a=s,b=2*s,R=x=>`calc(100% - ${x}px)`;
 return `polygon(0 ${b}px,${a}px ${b}px,${a}px ${a}px,${b}px ${a}px,${b}px 0,${R(b)} 0,${R(b)} ${a}px,${R(a)} ${a}px,${R(a)} ${b}px,100% ${b}px,100% ${R(b)},${R(a)} ${R(b)},${R(a)} ${R(a)},${R(b)} ${R(a)},${R(b)} 100%,${b}px 100%,${b}px ${R(a)},${a}px ${R(a)},${a}px ${R(b)},0 ${R(b)})`};
const FONT="'WenQuanYi Zen Hei','文泉驛正黑',sans-serif";
const PIX="'Unifont','Unifont-JP',monospace";
const MONO="'JetBrains Mono','DejaVu Sans Mono',monospace";
const CSS=`
:root{--bg:#F4ECDF;--cd:#FFF8EC;--ln:#3B281F;--tx:#3B281F;--ac:#C77A3A;--ac2:#8F4E18;--st:#E9A25D;--stx:#3B281F;--hl:#F6DDB8;--sh:#C77A3A;--ph:#FCE9CC;--code:#3B281F;--codetx:#F5EBDC;--hd:#3B281F;--hdtx:#F5EBDC;--rule:rgba(59,40,31,.22);--nbtx:#FFF8EC;--c0:#FFF8EC}
.dark{--bg:#231A15;--cd:#33251C;--ln:#E9D6BC;--tx:#F5EBDC;--ac:#D08643;--ac2:#F0B572;--st:#F0B572;--stx:#231A15;--hl:#4A3324;--sh:#0F0A07;--ph:#3A2A1E;--code:#17100C;--codetx:#F5EBDC;--hd:#D08643;--hdtx:#231A15;--rule:rgba(233,214,188,.22);--nbtx:#231A15;--c0:#33251C}
*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1350px;overflow:hidden}
body{position:relative;font-family:${FONT};color:var(--tx);background-color:var(--bg);
 background-image:radial-gradient(circle,transparent 0,transparent 0),linear-gradient(var(--dot),var(--dot));background-size:48px 48px,6px 6px;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48'><rect x='21' y='21' width='6' height='6' fill='%23C77A3A' fill-opacity='.28'/></svg>");background-size:48px 48px;background-repeat:repeat}
.pix{font-family:${PIX};font-weight:400}
.ai{font-family:${PIX};font-weight:400;color:var(--ac)}
/* 像素階梯角框：大（階 8、線 6）與小（階 4、線 4） */
.pc{position:relative;isolation:isolate;filter:drop-shadow(8px 8px 0 var(--sh))}
.pc::before{content:"";position:absolute;inset:0;background:var(--ln);clip-path:${poly(8)};z-index:-1}
.pc::after{content:"";position:absolute;inset:6px;background:var(--cd);clip-path:${poly(8)};z-index:-1}
.pcs{position:relative;isolation:isolate}
.pcs::before{content:"";position:absolute;inset:0;background:var(--ln);clip-path:${poly(4)};z-index:-1}
.pcs::after{content:"";position:absolute;inset:4px;background:var(--cd);clip-path:${poly(4)};z-index:-1}
.hd{position:absolute;left:64px;right:64px;top:52px;height:92px;display:flex;justify-content:space-between;align-items:center}
.lock{display:flex;gap:20px;align-items:center}
.pg{font-family:${PIX};font-size:32px;line-height:1;padding:14px 20px;color:var(--tx);white-space:nowrap}
.steam{position:absolute;z-index:0}
.main{position:absolute;left:64px;right:64px;top:176px;bottom:154px;display:flex;flex-direction:column;gap:28px;z-index:1}
.row{display:flex;align-items:center;gap:24px}
.chip{--cd:var(--st);font-family:${PIX};font-size:32px;line-height:1;padding:12px 20px;color:var(--stx);white-space:nowrap}
.tag{font-family:${PIX};font-size:32px;line-height:1;color:var(--ac2);white-space:nowrap;margin-left:auto;display:flex;gap:12px;align-items:center}
.tag i{display:inline-block;width:16px;height:16px;background:var(--ac);flex:none}
.pill{--cd:var(--hl);font-size:30px;font-weight:700;line-height:1;padding:12px 20px;white-space:nowrap}
.t{font-weight:700;line-height:1.2;letter-spacing:.5px;-webkit-text-stroke:.022em var(--tx)}
.t .kick{-webkit-text-stroke:0}
.t .ai{-webkit-text-stroke:0;line-height:.5}
.chip .ai,.badge .ai{color:var(--stx)}
.kick{display:block;font-family:${PIX};font-weight:400;font-size:48px;line-height:1.1;color:var(--ac2);margin-bottom:8px}
.disc{position:absolute;left:64px;right:64px;bottom:72px;height:56px;padding-top:16px;font-size:32px;font-weight:700;line-height:38px;white-space:nowrap;z-index:1}
.disc::before{content:"";position:absolute;left:0;right:0;top:0;height:8px;background:repeating-linear-gradient(90deg,var(--ac) 0 8px,transparent 8px 16px)}
.badge{--cd:var(--st);font-size:28px;font-weight:700;line-height:1;padding:11px 22px;color:var(--stx);white-space:nowrap;align-self:flex-start}
.c{padding:24px 28px}
.c h3{display:inline-block;align-self:flex-start;font-size:32px;font-weight:700;line-height:1.2;background:var(--st);color:var(--stx);padding:2px 14px;margin-bottom:12px}
.c p{font-size:38px;font-weight:500;line-height:1.5}
.g2{display:flex;gap:28px;flex:1}.g2>.c{flex:1}
.stk{display:flex;flex-direction:column;gap:28px;flex:1}.stk>.c{flex:1;display:flex;flex-direction:column;justify-content:center}
.tiles{display:flex;gap:24px;flex:none}
.tile{flex:1;padding:22px 24px;display:flex;flex-direction:column;gap:6px}
.tile .nn{font-family:${PIX};font-size:96px;line-height:1;color:var(--nn,var(--ac2))}
.tile .nm{font-size:42px;font-weight:700;line-height:1.2}
.tile .sm{font-size:30px;font-weight:600;line-height:1.3}
.onst{color:var(--stx)}
.li{display:flex;gap:24px;align-items:center;padding:0 28px 0 22px;flex:1;--sh:var(--sh)}
.li .nb{--cd:var(--ac);width:76px;height:76px;flex:none;display:flex;align-items:center;justify-content:center;font-family:${PIX};font-size:48px;color:var(--nbtx)}
.li p{font-size:38px;font-weight:600;line-height:1.4}
.note{font-size:30px;font-weight:600;line-height:1.5}
.fill{color:var(--ac2);font-weight:700}
.hlm{display:inline-block;background:var(--st);color:var(--stx);padding:0 14px;margin-right:10px;font-weight:700}
.tw{flex:1;padding:18px;display:flex}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}
th{background:var(--hd);color:var(--hdtx);font-size:34px;font-weight:700;text-align:left;padding:8px 16px;line-height:1.3;height:92px}
td{font-size:34px;font-weight:600;padding:6px 16px;line-height:1.35;border-bottom:3px solid var(--rule)}
tr:last-child td{border-bottom:0}
td:first-child{background:var(--hl);font-weight:700}
td .cell{font-family:${PIX};font-size:48px;font-weight:400}
.ph{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;text-align:center;padding:0 36px}
.ph .box{flex:1;width:100%;border:6px dashed var(--ac);background:var(--ph);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:20px 32px}
.ph b{font-size:64px;font-weight:700;line-height:1.2}
.ph p{font-size:34px;font-weight:600;line-height:1.45}
.ph p.s{font-size:30px;color:var(--ac2)}
.code{--cd:var(--code);color:var(--codetx);padding:30px 34px;flex:1;font-size:34px;font-weight:500;line-height:1.55}
.code .k{color:var(--st);font-weight:700}
.code .f{font-family:${MONO};font-size:38px;font-weight:700;line-height:1.7}
.dark .code{--ln:#E9D6BC}
`;
const steam=(x,y)=>{const z=[0,12,12,0];let r='';const cols=[[9,'--st'],[7,'--ac'],[8,'--st']];
 cols.forEach(([h,col],c)=>{for(let i=0;i<h;i++)r+=`<rect x="${c*48+z[i%4]}" y="${(h-1-i)*12+(c===1?24:0)}" width="12" height="12" fill="var(${col})"/>`});
 return `<svg class="steam dc" data-o="蒸氣" style="left:${x}px;top:${y}px" width="132" height="132" viewBox="0 0 132 132">${r}</svg>`};
const camera=(s=10)=>{const g=["...XXXX.....","XXXXXXXXXXXX","X..........X","X...XXXX...X","X..X....X..X","X..X....X..X","X...XXXX...X","X..........X","XXXXXXXXXXXX"];let r='';g.forEach((row,y)=>[...row].forEach((c,x)=>{if(c==='X')r+=`<rect x="${x*s}" y="${y*s}" width="${s}" height="${s}"/>`}));
 return `<svg width="${12*s}" height="${9*s}" viewBox="0 0 ${12*s} ${9*s}" fill="var(--ac)" style="flex:none">${r}</svg>`};
const AI=s=>s.replace(/\bAI\b/g,'<span class="ai">AI</span>');
const pcs=(c,i,st='',o='')=>`<div class="${c}" ${o?`data-o="${o}" `:''}style="${st}">${i}</div>`;
// ---- 版面零件
const header=(n,tot,L)=>`<div class="hd"><div class="lock" data-o="LOGO">${L.mark}${L.word}</div><div class="pg pcs" data-o="頁碼">${String(n).padStart(2,'0')}/${String(tot).padStart(2,'0')}</div></div>${steam(640,16)}`;
const disc=d=>`<div class="disc" data-o="揭露列"><b>無業配</b>｜${d}｜圖文含 ${'AI'} 協助</div>`;
const tagH=s=>s?`<div class="tag" data-o="資料角標"><i></i>${s}</div>`:'';
const chipRow=(series,tag)=>`<div class="row"><div class="chip pcs" data-o="標籤">${AI(series)}</div>${tagH(tag)}</div>`;
const title=(t,sz,kick)=>`<div class="t" data-o="標題" style="font-size:${sz}px">${kick?`<span class="kick">${kick}</span>`:''}${AI(t)}</div>`;
const badge=b=>`<div class="badge pcs" data-o="標章">${AI(b)}</div>`;
const pills=a=>`<div class="row" data-o="資訊列" style="flex-wrap:wrap">${a.map(x=>`<span class="pill pcs">${x}</span>`).join('')}</div>`;
const card=(h,t,st='',fl=1)=>`<div class="pc c" data-o="${h}" style="${fl?'flex:1;':''}${st}"><h3>${h}</h3><p>${t}</p></div>`;
const list=(arr,sz)=>arr.map((t,i)=>`<div class="pc li" data-o="條${i}"><div class="nb pcs">${i+1}</div><p${sz?` style="font-size:${sz}px"`:''}>${t}</p></div>`).join('');
const note=(t,o='小字')=>`<div class="note" data-o="${o}">${t}</div>`;
const F='<span class="fill">【__】</span>';
const tbl=(w,rows)=>{const s=w.reduce((a,b)=>a+b);return `<div class="pc tw" data-o="表"><table><colgroup>${w.map(x=>`<col style="width:${(x*100/s).toFixed(2)}%">`).join('')}</colgroup>${rows.map((r,i)=>`<tr>${r.map(c=>i?`<td>${c}</td>`:`<th>${c}</th>`).join('')}</tr>`).join('')}</table></div>`};
const page=(o,{series,tag,t,sz=64,kick,top='',body,bd,d='自製圖文'})=>`${header(o.n,o.tot,o.L)}<div class="main">${chipRow(series,tag)}${title(t,sz,kick)}${top}${body}${bd?badge(bd):''}</div>${disc(d)}`;
const tiles=a=>`<div class="tiles">${a.map((r,i)=>`<div class="pc tile ${i===0?'onst':''}" data-o="卡${i}" style="--cd:${['var(--st)','var(--c0)','var(--hl)'][i]};${i===0?'--nn:var(--stx)':''}"><b class="nn">${String(i+1).padStart(2,'0')}</b><div class="nm">${r[0]}</div>${r[1]?`<div class="sm">${r[1]}</div>`:''}</div>`).join('')}</div>`;
const cover=(o,{series,date,tag,t,sz,sub,cards,extra=''})=>`${header(o.n,o.tot,o.L)}<div class="main"><div class="pc c" data-o="封面卡" style="flex:1;display:flex;flex-direction:column;justify-content:space-between;padding:30px 34px"><div class="row" style="flex-wrap:nowrap"><div class="chip pcs" data-in="封面卡" data-o="標籤">${AI(series)}</div>${date?`<span class="pill pcs" data-in="封面卡" data-o="日期">${date}</span>`:''}${tag?`<div class="tag" data-in="封面卡" data-o="資料角標"><i></i>${tag}</div>`:''}</div><div class="t" data-in="封面卡" data-o="標題" style="font-size:${sz}px;line-height:1.22">${AI(t)}</div><div data-in="封面卡" data-o="副標" style="font-size:44px;font-weight:700;line-height:1.3"><span class="hlm">${AI(sub)}</span></div></div>${tiles(cards)}${extra}</div>${disc('自製圖文')}`;
const dashStrip=txt=>`<div class="pc" data-o="截圖角" style="flex:none;padding:16px 24px;--cd:var(--ph)"><div class="row" style="gap:20px">${camera(6)}<b style="font-size:38px">${txt}</b></div></div>`;
const phBox=(a,b,c)=>`<div class="pc ph" data-o="截圖框" style="padding:18px"><div class="box">${camera(12)}<b>待 Andy 截圖</b><p>${a}</p>${c?`<p class="s">${c}</p>`:''}</div></div>`;
// ---- 內容
const CONTENT={};
const t1=d=>`實測 01｜第 1 版｜${d}`;
CONTENT.post1_實測=[
 o=>cover(o,{series:'AI 實測 第 01 期',date:'日期待填',tag:'',t:'ChatGPT 說答案會變成「小工具」，我丟 10 題去試',sz:96,sub:'出現幾次？算得對嗎？',cards:[['10 次實測',''],['附算式驗算',''],['含翻車','']],extra:dashStrip('待 Andy 截圖｜第 4 張一角')}),
 o=>page(o,{series:'AI 實測 第 01 期',tag:t1('日期待填'),t:'先搞清楚它是什麼',body:`<div class="stk" style="flex:1">${list(['2026-10-07 起，ChatGPT 的「Chat」分頁，回答裡可以直接長出圖表、表單、按鈕、小計算器。','付費方案先拿到，免費與 Go 方案 10/8 跟進。','不用特別下指令；純文字夠用時它還是給文字。'])}</div>${note('官方說法以 OpenAI 公告為準；細節只用兩家以上媒體都一致的部分。')}`,bd:'自製圖解｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 01 期',tag:t1('日期待填'),t:'我怎麼測：5 種題目 × 2 次',body:tbl([150,440,362],[['題目','我問什麼','我怎麼驗'],['分帳','4 人聚餐，1 人沒喝酒（假資料）','用 Excel 自己算'],['比較','三個手機方案月費（假資料）','逐格對原始數字'],['試算','房貸月付 800 萬、2.2%、30 年','用 Excel PMT 驗算'],['流程','請假流程畫成圖','看有沒有漏步驟'],['純知識','「特休怎麼算」','看會不會硬塞小工具']])+note(`每題都記：差幾元、有無互動元件、能不能點、有無引條文。測試條件：日期、方案、網頁或手機 ${F}`,'條件'),bd:'自製表格｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 01 期',tag:t1('日期待填'),kick:'步驟 1',t:'它真的變出計算器了',body:phBox('分帳題的完整回答畫面，要看得到互動元件與你的提問，從提問截到回答結束','','要遮：左側聊天紀錄清單、帳號名稱與信箱、瀏覽器分頁與書籤列')+`<div class="pc c" data-o="重點" style="flex:none;padding:18px 28px"><p style="font-size:34px;line-height:1.45"><span class="hlm">重點：</span>這題 2 次裡有${F}次出現互動元件；金額與我用 Excel 算的差${F}元。</p></div>`,bd:'截圖為實測｜非 AI 生成',d:'截圖已遮個資'}),
 o=>page(o,{series:'AI 實測 第 01 期',tag:t1('日期待填'),kick:'步驟 2',t:'房貸試算：和 Excel 一樣嗎',body:phBox('房貸試算題的回答畫面（含月付金額），旁邊並排你用 Excel PMT 算的同一格','','要遮：同第 4 張')+`<div class="pc c" data-o="重點" style="flex:none;padding:18px 28px"><p style="font-size:34px;line-height:1.45">ChatGPT 算出月付${F}元，Excel 算出${F}元，差${F}元。標註：①ChatGPT 的數字　②Excel 的數字　③差額</p></div>`,bd:'截圖為實測｜非 AI 生成',d:'截圖已遮個資'}),
 o=>page(o,{series:'AI 實測 第 01 期',tag:t1('日期待填'),t:'10 次的結果',body:tbl([220,320,320],[['題目','互動元件<br>次數／2','數字算對<br>次數／2'],...['分帳','比較','試算','流程','純知識'].map(x=>[x,F,F])])+note(`我的感想（每題一句）：${F}。同題問 2 次、各開新對話；樣本只有 10 次，不代表一般情況。`,'條件'),bd:'自製表格｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 01 期',tag:t1('日期待填'),t:'結論：依實測結果寫',body:`<div class="stk" style="flex:1">${list([`誰適合用、誰不適合：${F}`,`哪裡會出錯（要是真的遇到的）：${F}`,'下一步：先拿一題你有標準答案的題目測，再決定信不信'])}</div>`+note(`完整測試條件 ${F}。以上為個人使用經驗，不構成任何建議。`),bd:'自製圖解｜非 AI 生成'})
];
const t2=n=>`查證 0${n}｜第 1 版｜11/03`,W='第 45 週｜第 1 版';
const newsBig=(a,b)=>`<div class="stk">${card('發生什麼',a,'',1).replace('<p>','<p style="font-size:36px">')}${card('對上班族差在哪',b,'--cd:var(--hl)',1).replace('<p>','<p style="font-size:36px">')}</div>`;
CONTENT.post2_三則=[
 o=>cover(o,{series:'本週 AI 三則',date:'10/28 ~ 11/03',tag:W,t:'三則 AI 新聞，<br>只講跟你上班<br>有關的',sz:128,sub:'每則附來源、日期、可信度',cards:[['微軟 6 萬人','來源 2｜信心 中'],['紐約新法','來源 2｜信心 中'],['Claude Duet','來源 2｜信心 中']]}),
 o=>page(o,{series:'本週 AI 三則',tag:t2(1),kick:'新聞 1／3',t:'微軟提出約 6 萬人自願離職方案',top:pills(['事件日 10/26 美東','查證日 11/03','信心度 中']),body:`<div class="g2">${card('發生什麼','微軟向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。','',1).replace('<p>','<p style="font-size:36px">')}${card('微軟怎麼說','公司說是為員工增加彈性。媒體把它和 AI 投資成本連在一起，這是媒體的解讀，不是公司原話。','',1).replace('<p>','<p style="font-size:36px">')}</div>`+card('對上班族差在哪','看到「AI 導致裁員」的標題時，先分清「公司說的原因」和「媒體猜的原因」。','--cd:var(--hl);flex:none',0).replace('<p>','<p style="font-size:36px">'),bd:'整理自新聞｜我沒親自測'}),
 o=>page(o,{series:'本週 AI 三則',tag:t2(2),kick:'新聞 2／3',t:'紐約簽了聊天機器人新法',top:pills(['10/28 簽署，2027/1/1 生效','查證日 11/03','信心度 中']),body:newsBig('紐約州長簽署新法，業者若沒有先確認對方不是未成年，就不能提供一批「不安全的陪伴功能」，例如假裝成真人、一味奉承、鼓勵孩子疏遠身邊的人。違規州檢察長可以提告。','這是美國州法，台灣不適用；但如果你做的產品會跟青少年聊天，「不准假裝是真人」已經被寫成條文，值得先看一遍。'),bd:'整理自新聞｜我沒親自測'}),
 o=>page(o,{series:'本週 AI 三則',tag:t2(3),kick:'新聞 3／3',t:'Claude Duet 開放候補',top:pills(['事件日 10/21 美西','查證日 11/03','信心度 中']),body:newsBig('Anthropic 推出「Claude Duet」研究預覽，會主動整理信箱與行事曆；付款、簽文件這類動作會先問你同意。目前只開美國候補名單，Pro、Max 先。','台灣現在進不了候補名單，別花時間找方法；但要記住它的賣點是「哪些動作一定先問你」，以後挑 AI 代理工具就看這一點。'),bd:'整理自新聞｜我沒親自測'}),
 o=>page(o,{series:'本週 AI 三則',tag:W,t:'三則的來源（都附日期）',body:tbl([150,560,180],[['新聞','兩個獨立來源','信心度'],['微軟','AP 稿轉載（10/27）、UC Today（10/27 前後，日期待核）','中'],['紐約','AP 稿轉載（10/28）、PPC Land（10/28 前後，日期待核）','中'],['Duet','Inside、科技新報（10/21–22）','中']])+note('信心「中」＝我只讀到新聞摘要，沒讀到公司或政府一手公告。完整網址放在留言。'),bd:'自製表格｜非 AI 生成'}),
 o=>page(o,{series:'本週 AI 三則',tag:W,t:'這週我的結論',body:`<div class="stk" style="flex:1">${list(['這三則我都沒親自測，只當資訊看。','看到裁員標題，先查公司原話。','看 AI 代理，先問「哪些事它會先問我」。'])}</div>`+note('以上為資訊整理，不構成任何建議。本篇提到公司名僅作新聞事實，不推薦買賣任何個股。'),bd:'整理自新聞｜我沒親自測'})
];
const t3='實測 02｜第 1 版｜11/03';
CONTENT.post3_教學=[
 o=>cover(o,{series:'AI 實測 第 02 期',date:'11/03',tag:'',t:'「2026/11/03 王小明」<br>一欄，拆成日期和姓名',sz:76,sub:'貼 1 段提示詞，30 秒搞定',cards:[['假資料示範','不放真人姓名'],['附公式','日期、姓名各一條'],['附防呆','空白也不出錯']]}),
 o=>page(o,{series:'AI 實測 第 02 期',tag:t3,t:'你是不是也有這種欄位',body:`<div class="pc c" data-o="內文" style="flex:none"><p style="font-size:38px;font-weight:700">系統匯出來的表，日期和姓名黏在同一格。手動拆 200 列，拆到眼睛花。</p></div>`+tbl([100],[['A 欄'],['2026/11/03 王小明'],['2026/11/04 林小華'],['2026/11/05 陳小美']])+note('全部是假資料，沒有任何真人姓名。'),bd:'自製圖解｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 02 期',tag:t3,kick:'步驟 1',t:'先講你用哪個版本',body:`<div class="pc c" data-o="內文" style="flex:none;--cd:var(--hl)"><p style="font-size:38px;font-weight:700">Excel 365 有新函數，舊版沒有。不講版本，它可能給你舊版打不開的公式。</p></div><div class="stk" style="flex:1">${list(['打開 Excel，點左上角「檔案」','點左下角「帳戶」','看右側的版本資訊，記下是 365、2019 或 2016，填進提示詞'])}</div>`+note('版本在「檔案 → 帳戶」看得到。'),bd:'自製圖解｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 02 期',tag:t3,kick:'步驟 2',t:'貼這段提示詞',body:`<div class="pc code" data-o="提示詞">你是 Excel 助手。我的 A 欄每格格式是「日期 空格 姓名」，例如「2026/11/03 王小明」。請給我兩條公式（從第 2 列開始）：B 欄取出日期，C 欄取出姓名。<br><span class="k">要求：</span><br>1. 我的 Excel 版本是【請填：Excel 365／2019／2016】。<br>2. 日期要變成真正的日期，不是文字。<br>3. 姓名前後不要有多餘空格。<br>4. 每條公式後面用一句話說明它在做什麼。<br>5. 告訴我：如果某一格沒有空格、或是空白，公式會出現什麼結果；並給我加上防呆的版本。<br>6. 不要編造不存在的函數；不確定就直接說不確定。</div>`,bd:'自製圖解｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 02 期',tag:t3,kick:'步驟 3',t:'貼進去，驗 3 格',body:`<div class="pc code" data-o="公式" style="flex:1;display:flex;flex-direction:column;justify-content:center"><span class="k">B2　→ 日期</span><div class="f">=DATEVALUE(LEFT(A2,FIND(" ",A2)-1))</div><br><span class="k">C2　→ 王小明</span><div class="f">=TRIM(MID(A2,FIND(" ",A2)+1,100))</div></div><div class="pc c" data-o="驗法" style="flex:none;padding:20px 28px"><p style="font-size:34px;line-height:1.5"><span class="hlm">驗法</span>抽第一列、最後一列、一列故意打壞的，對照 A 欄。AI 的寫法可能不同，結果要一樣。</p></div>`+note('待實測：貼進你的 Excel 後，附 B、C 欄結果的截圖。','待測'),bd:'自製圖解｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 02 期',tag:t3,t:'最常見的兩個坑',body:`<div class="stk" style="flex:1">${list(['日期欄顯示成一串數字（例如 46329）：不是算錯，是格式沒設成日期。選取 B 欄 → 儲存格格式 → 日期。','有些姓名前面是「全形空格」，FIND(" ") 找不到。叫 AI「同時處理全形空格」，或先把全形空格取代成半形。'],36)}</div>`+note('待實測：你自己有沒有遇到第三個坑？有就換成真實遇到的。'),bd:'自製圖解｜非 AI 生成'}),
 o=>page(o,{series:'AI 實測 第 02 期',tag:t3,t:'存起來，下次直接貼',body:`<div class="stk" style="flex:1">${list(['把提示詞存成備忘錄或文字檔，取名「Excel 拆欄提示詞」','每次只改【請填】那格的 Excel 版本','貼給 AI 前，用假資料或先遮掉個資'])}</div>`+note('以上為個人使用經驗。'),bd:'自製圖解｜非 AI 生成'})
];
// ---- 輸出
const CHECK=fs.readFileSync(path.join(HERE,'../layouts_v2/tech/render_tech.js'),'utf8').match(/const CHECK=`([\s\S]*?)`;\n\(async/)[1];
const doc=(body,dark)=>`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>${CSS}</style><body class="${dark?'dark':''}">${body}</body></html>`;
async function shot(b,html,htmlFile,png){fs.writeFileSync(htmlFile,html);const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+htmlFile);await pg.waitForTimeout(250);
 await pg.screenshot({path:png});const r=await pg.evaluate(eval(CHECK));
 const tb=await pg.evaluate(()=>[...document.querySelectorAll('td,th')].filter(e=>parseFloat(getComputedStyle(e).fontSize)<34).map(e=>e.textContent.slice(0,6)));
 const disc=await pg.evaluate(()=>{const e=document.querySelector('.disc');return parseFloat(getComputedStyle(e).fontSize)});
 const en=await pg.evaluate(()=>{const cl=document.body.cloneNode(true);cl.querySelectorAll('svg,style').forEach(e=>e.remove());const t=cl.innerText.replace(/CaffAIne|AI|ChatGPT|Excel|PMT|Free|Plus|Pro|Max|OpenAI|Claude|Duet|Anthropic|Go|AP|UC Today|PPC Land|Inside|FIND|LEFT|MID|TRIM|DATEVALUE|Andy|B2|C2|A2|A|B|C/g,'');return (t.match(/[A-Za-z]{3,}(?:\s+[A-Za-z]{2,})+/g)||[]).join('/')});
 const probs=[...r.overlap,...r.gap24.map(x=>'間距'+x),...r.oob.map(x=>'越界'+x),...r.clip.map(x=>'溢出'+x),...r.decoOnText.map(x=>'穿字'+x),...r.small.map(x=>'小字'+x),...tb.map(x=>'表字<34 '+x),...(disc<28?['揭露<28']:[]),...(en?['英文句 '+en]:[])];
 await pg.close();return probs}
(async()=>{const b=await chromium.launch();const mode=process.argv[2]||'samples';const all=[];
 const mk=(post,i,dark)=>{const n=CONTENT[post].length;return CONTENT[post][i]({n:i+1,tot:n,L:LOGOS[dark?'dark':'light']})};
 if(mode==='samples'){
  const S=[['s1_post2_封面','post2_三則',0,0],['s2_post2_新聞卡','post2_三則',1,0],['s3_post1_比較表','post1_實測',2,0],['s4_post1_待截圖頁','post1_實測',3,0],['s5_深色變體_post2封面','post2_三則',0,1]];
  for(const [nm,post,i,dk] of S){const p=await shot(b,doc(mk(post,i,dk),dk),`${HERE}/html/${nm}.html`,`${HERE}/png/${nm}.png`);console.log(nm,p.length?p.join(' | '):'OK');all.push(...p)}}
 else{for(const post of Object.keys(CONTENT)){const dir=`${ROOT}/${post}/img_caffaine`;fs.mkdirSync(dir,{recursive:true});const n=CONTENT[post].length;
   for(let i=0;i<n;i++){const p=await shot(b,doc(mk(post,i,0),0),`${HERE}/html/${post}_${i+1}.html`,`${dir}/slide${i+1}.png`);console.log(post,i+1,p.length?p.join(' | '):'OK');all.push(...p)}
   const pg=await b.newPage({viewport:{width:1760,height:800}});
   const f=`${HERE}/html/contact_${post}.html`;fs.writeFileSync(f,`<meta charset=utf-8><body style="margin:0;background:#E6DAC6;padding:20px;width:1760px;box-sizing:border-box;display:flex;flex-wrap:wrap;gap:16px">${Array.from({length:n},(_,i)=>`<img src="file://${dir}/slide${i+1}.png" style="width:410px;height:512px;border-radius:6px">`).join('')}</body>`);
   await pg.goto('file://'+f);await pg.waitForTimeout(400);await pg.screenshot({path:`${dir}/contact.png`,fullPage:true});await pg.close()}}
 await b.close();console.log('總問題數',all.length)})();
