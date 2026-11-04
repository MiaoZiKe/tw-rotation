// 以 T4b 定稿版型重出 3 篇範例貼文。node gen_posts.js
const fs=require('fs'),path=require('path');
const {build,BASE,pageDeco,logo,camera,mono,ink,am,tl}=require('./gen_tech.js');
const {chromium}=require('/opt/node-tools/node_modules/playwright');
const ROOT='/home/user/tw-rotation/docs/marketing/channels/ai_intro/samples/20261104';
const css0=build('b').css+`
.li{display:flex;gap:24px;align-items:center;border:4px solid ${ink};border-radius:14px;background:#fff;padding:0 26px;flex:1}
.li .ni{width:76px;height:76px;border-radius:12px;background:${tl};color:#fff;font-family:${require('./gen_tech.js').MONO};font-size:44px;font-weight:900;display:flex;align-items:center;justify-content:center;flex:none}
.li p{font-size:38px;font-weight:700;line-height:1.4}
.note{font-size:28px;font-weight:600;line-height:1.5;color:#2C4559}
table.sm th{font-size:30px;height:80px;padding:0 14px}table.sm td{font-size:30px;padding:6px 14px;font-weight:700;line-height:1.35}
table.sm td:first-child{font-size:32px}
.fill{color:#8A5A00;font-weight:900}
.dash{border:8px dashed #E39A00;border-radius:14px;background:#FFF1C9;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;text-align:center;padding:0 40px;box-shadow:6px 6px 0 ${ink}}
.dash b{font-size:60px;font-weight:900}.dash p{font-size:32px;font-weight:700;line-height:1.45}
.code{background:${ink};color:#E6F6F0;border-radius:14px;padding:26px 30px;font-family:${require('./gen_tech.js').MONO};font-size:30px;font-weight:500;line-height:1.5;box-shadow:6px 6px 0 #0A6A86;flex:1}
.code .k{color:${am};font-weight:900}
.cell{font-family:${require('./gen_tech.js').MONO};font-size:36px;font-weight:700}
`;
const rowsC=(items)=>`<div class="g3">${items.map((r,i)=>`<div class="card sh" data-o="卡${i}" style="background:${['#FFC857','#fff','#CDEFF3'][i]}"><b class="n">${i+1}</b><div class="nm">${r[0]}</div>${r[1]?`<div class="sm">${r[1]}</div>`:''}</div>`).join('')}</div>`;
const hdr=(l,r)=>`<div class="srow"><div class="ser" data-in="色塊" data-o="系列標">${logo(58,'#fff',am,'#0B6AA0')}<span>${l}</span></div><div class="pill" data-in="色塊" data-o="右標">${r}</div></div>`;
const disc=(l)=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
const tag=s=>`<div class="tag" data-o="資料角標"><i></i>${s}</div>`;
const brow=(badge,tg)=>`<div class="brow">${badge?`<div class="badge" data-o="標章">${badge}</div>`:'<span></span>'}${tg?tag(tg):''}</div>`;
const brk='<span class="bk a"></span><span class="bk b"></span><span class="bk c"></span><span class="bk d"></span>';
const blk=(h,n,inner)=>{const [pg,bd]=pageDeco('b',h,n,7);return `${pg}<div class="blk0" data-o="色塊" style="height:${h}px">${bd}${inner}</div>`};
const ttl=(t,sz)=>`<div class="t" data-in="色塊" data-o="標題" style="font-size:${sz}px">${t}</div>`;
const main=(top,inner)=>`<div class="main" style="top:${top}px">${inner}</div>`;
// 內頁骨架
const page=(h,n,left,right,title,sz,extra,body,d)=>blk(h,n,hdr(left,right)+ttl(title,sz)+(extra||''))+main(h+30,body)+disc(d||'自製圖文');
const cover=(left,date,title,sz,sub,tg,cards,extra)=>blk(640,1,hdr(left,date)+ttl(title,sz))+main(690,`<div class="brow"><div data-o="副標" style="font-size:44px;font-weight:800;white-space:nowrap">${sub}</div>${tag(tg)}</div>${cards}${extra||''}`)+disc('自製圖文');
const list=(arr)=>arr.map((t,i)=>`<div class="li" data-o="條${i}"><div class="ni">${i+1}</div><p>${t}</p></div>`).join('');
const tbl=(w,rows,cls='sm')=>`<table class="${cls}"><colgroup>${w.map(x=>`<col style="width:${(x*100/w.reduce((a,b)=>a+b)).toFixed(2)}%">`).join('')}</colgroup>${rows.map((r,i)=>`<tr>${r.map(c=>i?`<td>${c}</td>`:`<th>${c}</th>`).join('')}</tr>`).join('')}</table>`;
const fr=(inner)=>`<div class="fr">${brk}${inner}</div>`;
const F='<span class="fill">【__】</span>';
const P={};
/* ===== post1 實測 ===== */
const t1=d=>`實測 01｜第 1 版｜${d}`;
P.post1_實測=[
 cover('AI 實測 第 01 期','日期待填','ChatGPT 說答案會變成「小工具」，我丟 10 題去試',92,'出現幾次？算得對嗎？','實測 01｜第 1 版',rowsC([['10 次實測',''],['附算式驗算',''],['含翻車','']]).replace('class="g3"','class="g3" style="flex:1"'),`<div class="dash" data-o="截圖角" style="height:130px;flex:none;flex-direction:row;gap:20px;padding:0 24px">${camera('#B27300',64)}<b style="font-size:40px">待 Andy 截圖｜第 4 張一角</b></div>`),
 page(300,2,'AI 實測 第 01 期','2/7','先搞清楚它是什麼',62,'',list(['2026-10-07 起，ChatGPT 的「Chat」分頁，回答裡可以直接長出圖表、表單、按鈕、小計算器。','付費方案先拿到，免費與 Go 方案 10/8 跟進。','不用特別下指令；純文字夠用時它還是給文字。'])+`<div class="note" data-o="小字">官方說法以 OpenAI 公告為準；細節只用兩家以上媒體都一致的部分。</div>`+brow('自製圖解｜非 AI 生成',t1('日期待填'))),
 page(300,3,'AI 實測 第 01 期','3/7','我怎麼測：5 種題目 × 2 次',62,'',`<div class="fr">${brk}<div class="tw" data-o="表">${tbl([135,270,235,260],[['題目','我問什麼','我怎麼驗','要記什麼'],['分帳','4 人聚餐，1 人沒喝酒（假資料）','用 Excel 自己算','金額差幾元'],['比較','三個手機方案月費（假資料）','逐格對原始數字','有沒有互動元件'],['試算','房貸月付 800 萬、2.2%、30 年','用 Excel PMT 驗算','差幾元'],['流程','請假流程畫成圖','看有沒有漏步驟','能不能點'],['純知識','「特休怎麼算」','看會不會硬塞小工具','有沒有引用條文']])}</div></div><div class="note" data-o="條件">測試條件：日期、方案（Free／Plus）、網頁或手機、語言設定 ${F}</div>`+brow('自製表格｜非 AI 生成',t1('日期待填'))),
 page(300,4,'AI 實測 第 01 期','4/7','步驟 1　它真的變出計算器了',62,'',fr(`<div class="dash" data-o="截圖框" style="flex:1">${camera('#B27300',96)}<b>待 Andy 截圖</b><p>分帳題的完整回答畫面，要看得到互動元件與你的提問，從提問截到回答結束</p><p style="font-size:30px;color:#6B4A00">要遮：左側聊天紀錄清單、帳號名稱與信箱、瀏覽器分頁與書籤列</p></div>`)+`<div class="card" data-o="重點" style="font-size:34px;font-weight:700;line-height:1.45;padding:16px 24px"><span style="background:${am};padding:0 14px;margin-right:12px;display:inline-block">重點：</span>這題 2 次裡有${F}次出現互動元件；金額與我用 Excel 算的差${F}元。</div>`+brow('截圖為實測｜非 AI 生成',t1('日期待填')),'截圖已遮個資'),
 page(300,5,'AI 實測 第 01 期','5/7','房貸試算：它算得和 Excel 一樣嗎',62,'',fr(`<div class="dash" data-o="截圖框" style="flex:1">${camera('#B27300',96)}<b>待 Andy 截圖</b><p>房貸試算題的回答畫面（含月付金額），旁邊並排你用 Excel PMT 算的同一格</p><p style="font-size:30px;color:#6B4A00">要遮：同第 4 張</p></div>`)+`<div class="card" data-o="重點" style="font-size:34px;font-weight:700;line-height:1.45;padding:16px 24px">ChatGPT 算出月付${F}元，Excel 算出${F}元，差${F}元。<br>標註：①ChatGPT 的數字　②Excel 的數字　③差額</div>`+brow('截圖為實測｜非 AI 生成',t1('日期待填')),'截圖已遮個資'),
 page(300,6,'AI 實測 第 01 期','6/7','10 次的結果',62,'',`<div class="fr">${brk}<div class="tw" data-o="表">${tbl([150,230,230,260],[['題目','出現互動元件（次／2）','數字算對（次／2）','我的感想一句'],...['分帳','比較','試算','流程','純知識'].map(x=>[x,F,F,F])])}</div></div><div class="note" data-o="條件">怎麼比的：同題問 2 次，各開新對話；樣本只有 10 次，不代表一般情況。勝出格用「✓」加色。</div>`+brow('自製表格｜非 AI 生成',t1('日期待填'))),
 page(300,7,'AI 實測 第 01 期','7/7','結論：依實測結果寫',62,'',list([`誰適合用、誰不適合：${F}`,`哪裡會出錯（要是真的遇到的）：${F}`,'下一步：先拿一題你有標準答案的題目測，再決定信不信'])+`<div class="note" data-o="小字">完整測試條件 ${F}。以上為個人使用經驗，不構成任何建議。</div>`+brow('自製圖解｜非 AI 生成',t1('日期待填')))
];
/* ===== post2 三則 ===== */
const t2=(n)=>`查證 0${n}｜第 1 版｜11/03`,W='第 45 週｜第 1 版';
const pills=(a,b)=>`<div style="display:flex;gap:16px;flex-wrap:wrap" data-in="色塊" data-o="資訊列">${a.map(x=>`<span class="pill">${x}</span>`).join('')}</div>`;
const card=(h,t,bg,fl)=>`<div class="card" data-o="${h}" style="${fl?'flex:1;':''}${bg?'background:'+bg:''}"><h3${bg?' style="background:#fff"':''}>${h}</h3><p>${t}</p></div>`;
const newsBig=(a,b,c,d,e)=>`<div class="card" data-o="發生什麼" style="flex:1"><h3>發生什麼</h3><p style="font-size:34px">${a}</p></div><div class="card" data-o="差在哪" style="flex:1;background:#FFF1C9"><h3 style="background:#fff">對上班族差在哪</h3><p style="font-size:34px">${b}</p></div>`;
P.post2_三則=[
 cover('本週 AI 三則','10/28 ~ 11/03','三則 AI 新聞，<br>只講跟你上班<br>有關的',122,'每則附來源、日期、可信度',W,rowsC([['微軟 6 萬人','來源 2｜信心 中'],['紐約新法','來源 2｜信心 中'],['Claude Duet','來源 2｜信心 中']])),
 page(430,2,'本週 AI 三則','2/6','新聞 1／3<br>微軟提出約 6 萬人自願離職方案',62,pills(['事件日 10/26 美東','查證日 11/03','信心度 中']),`<div class="g2">${card('發生什麼','微軟向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。')}${card('微軟怎麼說','公司說是為員工增加彈性。媒體把它和 AI 投資成本連在一起，這是媒體的解讀，不是公司原話。')}</div>`+card('對上班族差在哪','看到「AI 導致裁員」的標題時，先分清「公司說的原因」和「媒體猜的原因」。','#FFF1C9')+brow('整理自新聞｜我沒親自測',t2(1))),
 page(502,3,'本週 AI 三則','3/6','新聞 2／3<br>紐約簽了聊天機器人新法',62,pills(['事件日 10/28 簽署，2027/1/1 生效','查證日 11/03','信心度 中']),newsBig('紐約州長簽署新法，業者若沒有先確認對方不是未成年，就不能提供一批「不安全的陪伴功能」，例如假裝成真人、一味奉承、鼓勵孩子疏遠身邊的人。違規州檢察長可以提告。','這是美國州法，台灣不適用；但如果你做的產品會跟青少年聊天，「不准假裝是真人」已經被寫成條文，值得先看一遍。')+brow('整理自新聞｜我沒親自測',t2(2))),
 page(502,4,'本週 AI 三則','4/6','新聞 3／3<br>Claude Duet 開放候補',62,pills(['事件日 10/21 美西','查證日 11/03','信心度 中']),newsBig('Anthropic 推出「Claude Duet」研究預覽，會主動整理信箱與行事曆；付款、簽文件這類動作會先問你同意。目前只開美國候補名單，Pro、Max 先。','台灣現在進不了候補名單，別花時間找方法；但要記住它的賣點是「哪些動作一定先問你」，以後挑 AI 代理工具就看這一點。')+brow('整理自新聞｜我沒親自測',t2(3))),
 page(300,5,'本週 AI 三則','5/6','三則的來源（都附日期）',62,'',`<div class="fr">${brk}<div class="tw" data-o="表">${tbl([150,520,180],[['新聞','兩個獨立來源','信心度'],['微軟','AP 稿轉載（10/27）、UC Today（10/27 前後，日期待核）','中'],['紐約','AP 稿轉載（10/28）、PPC Land（10/28 前後，日期待核）','中'],['Duet','Inside、科技新報（10/21–22）','中']])}</div></div><div class="note" data-o="小字">信心「中」＝我只讀到新聞摘要，沒讀到公司或政府一手公告。完整網址放在留言。</div>`+brow('自製表格｜非 AI 生成',W)),
 page(300,6,'本週 AI 三則','6/6','這週我的結論',62,'',list(['這三則我都沒親自測，只當資訊看。','看到裁員標題，先查公司原話。','看 AI 代理，先問「哪些事它會先問我」。'])+`<div class="note" data-o="小字">以上為資訊整理，不構成任何建議。本篇提到公司名僅作新聞事實，不推薦買賣任何個股。</div>`+brow('整理自新聞｜我沒親自測',W))
];
/* ===== post3 教學 ===== */
const t3='實測 02｜第 1 版｜11/03';
const MC=(x)=>`<span class="cell">${x}</span>`;
P.post3_教學=[
 cover('AI 實測 第 02 期','10/28 ~ 11/03'.replace('10/28 ~ 11/03','11/03'),'「2026/11/03 王小明」<br>一欄，拆成日期和姓名',80,'貼 1 段提示詞，30 秒搞定','實測 02｜第 1 版',rowsC([['假資料示範',''],['附公式',''],['附防呆','']])),
 page(300,2,'AI 實測 第 02 期','2/7','你是不是也有這種欄位',62,'',`<div class="card" data-o="內文" style="font-size:38px;font-weight:700;line-height:1.5">系統匯出來的表，日期和姓名黏在同一格。手動拆 200 列，拆到眼睛花。</div><div class="fr">${brk}<div class="tw" data-o="表">${tbl([100],[['A 欄'],['2026/11/03 王小明'],['2026/11/04 林小華'],['2026/11/05 陳小美']],'')}</div></div><div class="note" data-o="小字">全部是假資料，沒有任何真人姓名。</div>`+brow('自製圖解｜非 AI 生成',t3)),
 page(300,3,'AI 實測 第 02 期','3/7','步驟 1：先講你用哪個版本',62,'',`<div class="card sh" data-o="內文" style="flex:1;font-size:56px;font-weight:800;line-height:1.5;display:flex;align-items:center"><div>Excel 365 有新函數，舊版沒有。不講版本，它可能給你舊版打不開的公式。</div></div><div class="note" data-o="小字">版本在「檔案 → 帳戶」看得到。</div>`+brow('自製圖解｜非 AI 生成',t3)),
 page(300,4,'AI 實測 第 02 期','4/7','步驟 2：貼這段提示詞',62,'',`<div class="code" data-o="提示詞" style="font-size:35px;line-height:1.55">你是 Excel 助手。我的 A 欄每格格式是「日期 空格 姓名」，例如「2026/11/03 王小明」。請給我兩條公式（從第 2 列開始）：B 欄取出日期，C 欄取出姓名。<br><span class="k">要求：</span><br>1. 我的 Excel 版本是【請填：Excel 365／2019／2016】。<br>2. 日期要變成真正的日期，不是文字。<br>3. 姓名前後不要有多餘空格。<br>4. 每條公式後面用一句話說明它在做什麼。<br>5. 告訴我：如果某一格沒有空格、或是空白，公式會出現什麼結果；並給我加上防呆的版本。<br>6. 不要編造不存在的函數；不確定就直接說不確定。</div>`+brow('自製圖解｜非 AI 生成',t3)),
 page(300,5,'AI 實測 第 02 期','5/7','步驟 3：貼進去，驗 3 格',62,'',`<div class="code" data-o="公式" style="font-size:38px;line-height:1.7;padding-top:40px"><span class="k">B2　→ 日期</span><br>=DATEVALUE(LEFT(A2,FIND(" ",A2)-1))<br><br><span class="k">C2　→ 王小明</span><br>=TRIM(MID(A2,FIND(" ",A2)+1,100))</div><div class="card" data-o="驗法" style="font-size:36px;font-weight:700;line-height:1.5;flex:none"><span style="background:${am};padding:0 14px;margin-right:12px;display:inline-block">驗法</span>抽第一列、最後一列、一列故意打壞的，對照 A 欄。AI 的寫法可能不同，結果要一樣。</div><div class="note" data-o="待測">待實測：貼進你的 Excel 後，附 B、C 欄結果的截圖。</div>`+brow('自製圖解｜非 AI 生成',t3)),
 page(300,6,'AI 實測 第 02 期','6/7','最常見的兩個坑',62,'',list(['日期欄顯示成一串數字（例如 46329）：不是算錯，是格式沒設成日期。選取 B 欄 → 儲存格格式 → 日期。','有些姓名前面是「全形空格」，FIND(" ") 找不到。叫 AI「同時處理全形空格」，或先把全形空格取代成半形。'])+`<div class="note" data-o="小字">待實測：你自己有沒有遇到第三個坑？有就換成真實遇到的。</div>`+brow('自製圖解｜非 AI 生成',t3)),
 page(300,7,'AI 實測 第 02 期','7/7','存起來，下次直接貼',62,'',`<div class="card sh" data-o="內文" style="flex:1;font-size:56px;font-weight:800;line-height:1.5;display:flex;align-items:center"><div>資料請用假資料，或先遮掉個資再貼給 AI。以上為個人使用經驗。</div></div>`+brow('自製圖解｜非 AI 生成',t3))
];
const CHECK=fs.readFileSync(path.join(__dirname,'render_tech.js'),'utf8').match(/const CHECK=`([\s\S]*?)`;\n\(async/)[1];
(async()=>{const b=await chromium.launch();const bad=[];
for(const post of Object.keys(P)){const dir=path.join(ROOT,post,'img_t4b');fs.mkdirSync(dir,{recursive:true});fs.mkdirSync(path.join(__dirname,'html_posts'),{recursive:true});
 for(let i=0;i<P[post].length;i++){let body=mono(P[post][i]).replace(/(<div class="tag"[^>]*>)(.*?)(<\/div>)/g,(m,a,c,d)=>a+c.replace(/<span class="m">|<\/span>/g,'')+d);
  const f=path.join(__dirname,'html_posts',`${post}_${i+1}.html`);fs.writeFileSync(f,`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>${css0}</style><body>${body}</body></html>`);
  const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+f);await pg.waitForTimeout(200);
  await pg.screenshot({path:path.join(dir,`slide${i+1}.png`)});const r=await pg.evaluate(eval(CHECK));
  const probs=[...r.overlap,...r.gap24.map(x=>'間距'+x),...r.oob.map(x=>'越界'+x),...r.clip.filter(x=>x!=='高:標題'),...r.decoOnText.map(x=>'穿字'+x),...r.small.map(x=>'小字'+x)];
  console.log(post,i+1,probs.length?probs.join(' | '):'OK');await pg.close()}
 // contact
 const n=P[post].length;const pg=await b.newPage({viewport:{width:1700,height:800}});
 fs.writeFileSync('/tmp/claude-0/c.html',`<meta charset=utf-8><body style="margin:0;background:#E9EEF4;padding:20px;width:1700px;box-sizing:border-box;display:flex;flex-wrap:wrap;gap:16px">${P[post].map((_,i)=>`<img src="file://${dir}/slide${i+1}.png" style="width:395px;height:494px;border-radius:8px">`).join('')}</body>`);
 await pg.goto('file:///tmp/claude-0/c.html');await pg.waitForTimeout(400);await pg.screenshot({path:path.join(dir,'contact.png'),fullPage:true});await pg.close()}
await b.close()})()
