// 頻道③ 版型 v2 科技感三變體（方向四色塊海報為骨架）。node render_tech.js → html/ png/
const fs=require('fs');
const FONT="'Noto Sans TC','WenQuanYi Zen Hei','文泉驛正黑',sans-serif";
const MONO="'JetBrains Mono','DejaVu Sans Mono',monospace";
const ink='#0A1B2A',am='#FFC857',tl='#0A6A86';
const logo=(s,a,b,cut)=>`<svg width="${s}" height="${s}" viewBox="60 100 390 310" style="display:block"><rect x="84" y="120" width="166" height="190" rx="36" fill="${a}"/><rect x="262" y="202" width="166" height="190" rx="36" fill="${b}"/><path d="M130 232L160 262L215 187" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M305 257L385 337M385 257L305 337" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`;
const rows=[['微軟 6 萬人','01'],['紐約新法','02'],['Claude Duet','03']];
const TXT={what:'微軟向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。',say:'公司說是為員工增加彈性。媒體把它和 AI 投資成本連在一起，這是媒體的解讀，不是公司原話。',diff:'看到「AI 導致裁員」的標題時，先分清「公司說的原因」和「媒體猜的原因」。',ph1:'ChatGPT 對「分帳」題的完整回答畫面，需看得到提問與互動元件',ph2:'要遮：聊天紀錄、帳號名稱、分頁列',key:'這題 2 次裡有【__】次出現互動元件；金額與 Excel 差【__】元。',cond:'每題都記：差幾元、有無互動元件、能不能點、有無引條文。測試條件：【待填】日期、方案、網頁或手機'};
const TBL=[['題目','我問什麼','怎麼驗'],['分帳','4 人聚餐分帳','Excel 自算'],['比較','三個手機方案','逐格對數字'],['試算','房貸月付','Excel PMT'],['流程','請假流程圖','查有無漏步'],['純知識','特休怎麼算','看有沒有硬塞']];
const tbl=(w)=>`<table><colgroup>${w.map(x=>`<col style="width:${(x*100/w.reduce((a,b)=>a+b)).toFixed(2)}%">`).join('')}</colgroup>${TBL.map((r,i)=>`<tr>${r.map(c=>i?`<td>${c}</td>`:`<th>${c}</th>`).join('')}</tr>`).join('')}</table>`;
const camera=(c,s)=>`<svg width="${s}" height="${s}" viewBox="0 0 64 64" fill="none" stroke="${c}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"><rect x="6" y="14" width="52" height="38" rx="8"/><circle cx="32" cy="33" r="10"/><path d="M22 14l4-6h12l4 6"/></svg>`;
// 數字改等寬字：只換標籤外的文字節點
const mono=h=>h.split(/(<[^>]+>)/).map(p=>p.startsWith('<')?p:p.replace(/\d+(?:[\/.:~]\d+)*/g,'<span class="m">$&</span>')).join('');

const BASE=`*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1350px;overflow:hidden}body{position:relative;font-family:${FONT};color:${ink};background-color:#EAF1F6}
.m{font-family:${MONO};font-weight:inherit;letter-spacing:-.5px}
.blk0{position:absolute;left:0;right:0;top:0;color:#fff;padding:72px 64px 40px;display:flex;flex-direction:column;gap:24px;border-bottom:6px solid ${ink};z-index:1;overflow:hidden}
.blk0>*{position:relative;z-index:1}.blk0>svg.bd{position:absolute;z-index:0;left:0;top:0}
.pg{position:absolute;left:0;top:0;z-index:0}
.main{position:absolute;left:64px;right:64px;bottom:144px;display:flex;flex-direction:column;gap:26px;z-index:1}
.disc{position:absolute;left:64px;right:64px;bottom:72px;height:48px;border-top:5px solid ${ink};padding-top:6px;display:flex;justify-content:space-between;font-size:28px;font-weight:500;line-height:36px;z-index:1}.disc b{font-weight:900}
.srow{display:flex;justify-content:space-between;align-items:center;gap:24px}.ser{display:flex;gap:16px;align-items:center;font-size:36px;font-weight:900}
.pill{background:${am};color:${ink};border:3px solid ${ink};border-radius:12px;padding:4px 20px;font-size:30px;font-weight:900}
.t{font-weight:900;line-height:1.12}
.card{border:4px solid ${ink};border-radius:14px;background:#fff;padding:22px 24px}.sh{box-shadow:6px 6px 0 ${ink}}
.badge{border:3px solid ${ink};background:${am};border-radius:12px;padding:4px 24px;font-size:28px;font-weight:900;white-space:nowrap}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.tag{border:1.5px solid ${tl};color:${tl};background:transparent;padding:4px 18px 4px 16px;font-family:${MONO};font-size:28px;font-weight:500;white-space:nowrap;display:flex;gap:10px;align-items:center;border-radius:6px}.tag i{display:inline-block;width:12px;height:12px;background:${tl};flex:none}
.g3{display:flex;gap:24px;flex:1}.g3 .card{flex:1;display:flex;flex-direction:column;justify-content:space-between}.g3 b.n{font-size:150px;line-height:1;font-weight:900;font-family:${MONO}}.g3 .nm{font-size:44px;font-weight:900;line-height:1.2}.g3 .sm{font-size:28px;font-weight:700}
.g2{display:flex;gap:24px;flex:1}.g2 .card{flex:1}.card h3{font-size:34px;font-weight:900;margin-bottom:8px;background:${am};display:inline-block;padding:0 10px;border:3px solid ${ink}}.card p{font-size:38px;font-weight:600;line-height:1.5}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}th{background:${ink};color:${am};font-size:34px;font-weight:900;text-align:left;padding:0 18px;height:88px}td{font-size:36px;font-weight:700;padding:0 18px;border-bottom:4px solid ${ink}}td:first-child{background:${am};font-weight:900}
.fr{flex:1;display:flex;position:relative}
.tw{flex:1;border:4px solid ${ink};border-radius:14px;box-shadow:6px 6px 0 ${ink};overflow:hidden;background:#fff}
.ph{flex:1;border:8px dashed #E39A00;border-radius:14px;background:#FFF1C9;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:0 36px;box-shadow:6px 6px 0 ${ink}}
.ph b{font-size:62px;font-weight:900}.ph p{font-size:32px;font-weight:700;line-height:1.45}
.bk{position:absolute;width:28px;height:28px;border:0 solid ${tl}}.bk.a{left:-9px;top:-9px;border-left-width:5px;border-top-width:5px}.bk.b{right:-9px;top:-9px;border-right-width:5px;border-top-width:5px}.bk.c{left:-9px;bottom:-9px;border-left-width:5px;border-bottom-width:5px}.bk.d{right:-9px;bottom:-9px;border-right-width:5px;border-bottom-width:5px}`;

// 各變體
const V={
 a:{name:'T4a 輕',block:`background:#0A6A86;`,grid:true,tag:false,deco:0,
    pat:'rgba(255,255,255,.10)'},
 b:{name:'T4b 中',block:`background:linear-gradient(100deg,#0B58A0 0%,#0A7C90 55%,#0AA08C 100%);`,grid:true,tag:true,deco:1,pat:'rgba(255,255,255,.10)'},
 c:{name:'T4c 強',block:`background:linear-gradient(100deg,#0B58A0 0%,#0A7C90 55%,#0AA08C 100%);`,grid:true,tag:true,deco:2,pat:'rgba(255,255,255,.14)'}};

// 背景層裝飾（class dc 供程式檢查是否穿過文字）
function pageDeco(v,h0,pgNo,pgTot){const h=h0-6;const hp=h0; // 回傳 [頁面層 svg, 色塊內 svg]
  const o=V[v].deco; if(!o) return ['',''];
  const t='rgba(10,106,134,.55)',tw='rgba(255,255,255,.55)';
  const L=(x1,y1,x2,y2,c,w=2)=>`<line class="dc" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${w}"/>`;
  const N=(x,y,c,r=6,f='none')=>`<circle class="dc" cx="${x}" cy="${y}" r="${r}" fill="${f}" stroke="${c}" stroke-width="2.5"/>`;
  let pg='',bd='';
  // 色塊內：頂邊與底邊的電路線（標題在其內側，不穿過）
  bd+=L(0,26,150,26,tw)+L(150,26,176,8,tw)+L(176,8,380,8,tw)+N(380,8,tw,5)+L(700,26,1080,26,tw)+N(700,26,tw,5)+L(790,26,816,8,tw)+L(816,8,1000,8,tw)+N(1000,8,tw,5);
  bd+=L(560,h-22,1080,h-22,tw)+N(560,h-22,tw,5)+L(660,h-22,686,h-8,tw)+L(686,h-8,860,h-8,tw)+N(860,h-8,tw,5,'rgba(255,255,255,.5)');
  if(pgNo===1&&h0>=600){ // 封面右下留白：標題第 3 行很短
    bd+=L(560,h-120,1016,h-120,tw)+N(560,h-120,tw,6)+L(820,h-120,850,h-90,tw)+L(850,h-90,1016,h-90,tw)+N(1016,h-90,tw,6,'rgba(255,255,255,.5)');
  }
  // 頁面層：左右邊距（64px）內的垂直電路線；底部 72px 安全邊距內的橫線
  for(const [x,d] of [[24,1],[1056,-1]]){
    pg+=L(x,hp+6,x,1260,t)+N(x,hp+60,t,5,'#EAF1F6')+N(x,hp+520,t,5,'#EAF1F6')+L(x,hp+520,x-d*12,hp+538,t)+L(x-d*12,hp+538,x-d*12,hp+700,t)+N(x-d*12,hp+700,t,5)+N(x,1190,t,5,t);
  }
  pg+=L(64,1318,380,1318,t)+N(380,1318,t,5)+L(380,1318,404,1334,t)+L(404,1334,700,1334,t)+N(700,1334,t,5,t)+L(760,1318,1016,1318,t)+N(760,1318,t,5);
  if(o>=2){
    // 強：標尺刻度、十字標記、節段資料條、掃描線帶
    for(let y=hp+30;y<1250;y+=24){const long=((y-hp-30)/24)%5===0;pg+=L(2,y,long?22:12,y,t,2)+L(1078-(long?20:10),y,1078,y,t,2);}
    for(const [x,y] of [[40,hp+300],[1040,hp+300],[40,hp+800],[1040,hp+800]])pg+=L(x-9,y,x+9,y,t,2)+L(x,y-9,x,y+9,t,2);
    // 底部資料條（頁碼）：7 節，目前頁亮
    for(let i=0;i<pgTot;i++){const x=730+i*40;pg+=`<rect class="dc" x="${x}" y="1290" width="30" height="8" fill="${i<pgNo?tl:'none'}" stroke="${tl}" stroke-width="2"/>`;}
    // 色塊內掃描線帶（頂部 0~44 與底部）
    for(let y=0;y<44;y+=6)bd+=L(0,y,1080,y,'rgba(255,255,255,.07)',2);
    for(let y=h-40;y<h-6;y+=6)bd+=L(0,y,520,y,'rgba(255,255,255,.07)',2);
    // 塊內節段資料條（左下，標題下方的 padding 內）
    for(let i=0;i<10;i++)bd+=`<rect class="dc" x="${64+i*22}" y="${h-20}" width="16" height="7" fill="rgba(255,255,255,${i<pgNo+3?.65:.2})"/>`;
  }
  return [`<svg class="pg" width="1080" height="1350" viewBox="0 0 1080 1350">${pg}</svg>`,`<svg class="bd" width="1080" height="${h}" viewBox="0 0 1080 ${h}">${bd}</svg>`];
}
function build(v){
  const o=V[v].deco;
  const css=BASE+`
body{${V[v].grid?`background-image:linear-gradient(rgba(10,106,134,.08) 2px,transparent 2px),linear-gradient(90deg,rgba(10,106,134,.08) 2px,transparent 2px);background-size:40px 40px`:''}}
.blk0{${V[v].block}border-bottom-color:${ink}}
${V[v].pat?`.blk0{background-image:linear-gradient(${V[v].pat} 2px,transparent 2px),linear-gradient(90deg,${V[v].pat} 2px,transparent 2px),${V[v].block.match(/background:([^;]+);/)[1]};background-size:40px 40px,40px 40px,100% 100%;background-position:-1px -1px,-1px -1px,0 0}`:''}
`;
  const logoCut=v==='a'?'#0A6A86':'#0B6AA0';
  const hdr=(l,r)=>`<div class="srow"><div class="ser" data-in="色塊" data-o="系列標">${logo(58,'#fff',am,logoCut)}<span>${l}</span></div><div class="pill" data-in="色塊" data-o="右標">${r}</div></div>`;
  const disc=(l)=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
  const tag=(s)=>V[v].tag?`<div class="tag" data-o="資料角標"><i></i>${s}</div>`:'';
  const brk=o>=2?'<span class="bk a"></span><span class="bk b"></span><span class="bk c"></span><span class="bk d"></span>':'';
  const blk=(h,n,inner)=>{const [pg,bd]=pageDeco(v,h,n,7);return `${pg}<div class="blk0" data-o="色塊" style="height:${h}px">${bd}${inner}</div>`};
  const pages=[
   blk(640,1,`${hdr('本週 AI 三則','10/28 ~ 11/03')}<div class="t" data-in="色塊" data-o="標題" style="font-size:122px">三則 AI 新聞，<br>只講跟你上班<br>有關的</div>`)+
   `<div class="main" style="top:690px"><div class="brow"><div data-o="副標" style="font-size:44px;font-weight:800;white-space:nowrap">每則附來源、日期、可信度</div>${tag('第 45 週｜第 1 版')}</div><div class="g3">${rows.map((r,i)=>`<div class="card sh" data-o="卡${i}" style="background:${['#FFC857','#fff','#CDEFF3'][i]}"><b class="n">${i+1}</b><div class="nm">${r[0]}</div><div class="sm">來源 2｜信心 中</div></div>`).join('')}</div></div>${disc('自製圖文')}`,
   blk(430,2,`${hdr('本週 AI 三則','2/6')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">新聞 1／3<br>微軟提出約 6 萬人自願離職方案</div><div style="display:flex;gap:16px" data-in="色塊" data-o="資訊列"><span class="pill">事件日 10/26 美東</span><span class="pill">查證日 11/03</span><span class="pill">信心度 中</span></div>`)+
   `<div class="main" style="top:460px"><div class="g2"><div class="card" data-o="發生什麼"><h3>發生什麼</h3><p>${TXT.what}</p></div><div class="card" data-o="怎麼說"><h3>微軟怎麼說</h3><p>${TXT.say}</p></div></div><div class="card" data-o="差在哪" style="background:#FFF1C9"><h3 style="background:#fff">對上班族差在哪</h3><p>${TXT.diff}</p></div><div class="brow"><div class="badge" data-o="標章">整理自新聞｜我沒親自測</div>${tag('查證 01｜第 1 版｜11/03')}</div></div>${disc('自製圖文')}`,
   blk(300,3,`${hdr('AI 實測 第 01 期','3/7')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">我怎麼測：5 種題目 × 2 次</div>`)+
   `<div class="main" style="top:330px"><div class="fr">${brk}<div class="tw" data-o="表">${tbl([180,380,392])}</div></div><div data-o="條件" style="font-size:32px;font-weight:700">${TXT.cond}</div><div class="brow"><div class="badge" data-o="標章">自製表格｜非 AI 生成</div>${tag('實測 01｜第 1 版｜11/03')}</div></div>${disc('自製圖文')}`,
   blk(300,4,`${hdr('AI 實測 第 01 期','4/7')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">步驟 1　它真的變出計算器了</div>`)+
   `<div class="main" style="top:330px"><div class="fr">${brk}<div class="ph" data-o="截圖框">${camera('#B27300',96)}<b>待 Andy 截圖</b><p>${TXT.ph1}</p><p style="font-size:30px;color:#6B4A00">${TXT.ph2}</p></div></div><div class="card" data-o="重點" style="font-size:34px;font-weight:700;line-height:1.45;padding:16px 24px"><span style="background:${am};padding:0 14px;margin-right:12px;display:inline-block">重點：</span>${TXT.key}</div><div class="brow"><div class="badge" data-o="標章">截圖為實測｜非 AI 生成</div>${tag('實測 01｜第 1 版｜11/03')}</div></div>${disc('截圖已遮個資')}`];
  return {css,pages:pages.map(mono).map(p=>p.replace(/(<div class="tag"[^>]*>)(.*?)(<\/div>)/g,(m,a,b,c)=>a+b.replace(/<span class="m">|<\/span>/g,'')+c))};
}
module.exports={build,V,BASE,pageDeco,logo,camera,mono,MONO,FONT,ink,am,tl};
