// CaffAIne 專業版 8 方向：瀏覽器端設計庫（全部手寫 SVG 向量，無 AI 生圖、無角色）
// 由 build.js 注入頁面後呼叫 window.CF.*，回傳 SVG 字串。
(function(){
let U=0;const uid=()=>'k'+(++U)+Math.random().toString(36).slice(2,6);
const TH={
 light:{name:'light',bg:'#F6EEE3',ink:'#2B1D16',ac:'#C2652B',acHi:'#E8A066',mid:'#8A5A3C',soft:'#E9D8C2',lav:'#8676D6',paper:'#FFFBF5',cA:'#7A4B2E',cB:'#2B1D16',milk:'#EADBC6',l1:'#3A261C',l2:'#B4713F'},
 dark:{name:'dark',bg:'#2B1D16',ink:'#F6EEE3',ac:'#EB8D4E',acHi:'#F8BE8A',mid:'#C79A74',soft:'#47322A',lav:'#B6AAF2',paper:'#3A2A21',cA:'#E0A06C',cB:'#9A5A30',milk:'#F1E4D2',l1:'#6E3F24',l2:'#D88B52'}};
const ST=(col,w)=>`fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"`;
const lerp=(a,b,t)=>{const p=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));const A=p(a),B=p(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('')};
// 像素字 AI（5x7 的 A ＋ 3x7 襯線 I）
const PA=['.###.','#...#','#...#','#####','#...#','#...#','#...#'],PI=['###','.#.','.#.','.#.','.#.','.#.','###'];
function pixAI(x,y,cell,colFn,gr=.14){let o='';const g=cell*gr,r=cell*.2;
 PA.forEach((row,j)=>[...row].forEach((ch,i)=>{if(ch==='#')o+=`<rect x="${(x+i*cell+g/2).toFixed(2)}" y="${(y+j*cell+g/2).toFixed(2)}" width="${(cell-g).toFixed(2)}" height="${(cell-g).toFixed(2)}" rx="${r.toFixed(2)}" fill="${colFn(j)}"/>`}));
 PI.forEach((row,j)=>[...row].forEach((ch,i)=>{if(ch==='#')o+=`<rect x="${(x+(6+i)*cell+g/2).toFixed(2)}" y="${(y+j*cell+g/2).toFixed(2)}" width="${(cell-g).toFixed(2)}" height="${(cell-g).toFixed(2)}" rx="${r.toFixed(2)}" fill="${colFn(j)}"/>`}));
 return o;}
const spark=(cx,cy,R,fill,k=.18)=>{const r=R*k;return `<path d="M${cx} ${cy-R} Q${cx+r} ${cy-r} ${cx+R} ${cy} Q${cx+r} ${cy+r} ${cx} ${cy+R} Q${cx-r} ${cy+r} ${cx-R} ${cy} Q${cx-r} ${cy-r} ${cx} ${cy-R} Z" fill="${fill}"/>`};
const letterA=(x,y,h,col,w,k=.38)=>{const hw=h*k;return `<path d="M${x-hw} ${y+h} L${x} ${y} L${x+hw} ${y+h} M${x-hw*.6} ${y+h*.7} H${x+hw*.6}" ${ST(col,w)}/>`};

// ───────── 8 個方向 ─────────
const DIRS=[
{id:'P1',dir:'P1_手沖A',name:'手沖 A',en:'Pour-over A',ratio:[70,30],
 meaning:'手沖下壺的三角輪廓就是字母 A，木頸圈是 A 的橫槓；上方那一滴正在落下的是 I——知識一滴一滴萃取進你的杯子。',
 ai:'圖形：A＝下壺、I＝滴落的焦糖襯線；文字標：AI 改用襯線 Charter Bold 焦糖色，大寫 I 有上下襯線，不會讀成 l。',
 color:'深可可＋焦糖，壺內咖啡用可可→濃縮的柔和漸層，頸圈帶一道金屬光澤漸層。',
 type:'Inter Display Medium（Caff／ne）＋ Bitstream Charter Bold（AI）。',
 tech:'精準等腰三角與 1:2 比例網格、頸圈的金屬光澤、滴落點的等距節奏。',
 draw:(c,o)=>{const g=uid(),tri='M100 76 L156 178 L44 178 Z';
  return `<defs><clipPath id="${g}k"><path d="${tri}"/></clipPath>
  <linearGradient id="${g}c" x1="0" y1="134" x2="0" y2="182" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.cA}"/><stop offset="1" stop-color="${c.cB}"/></linearGradient>
  <linearGradient id="${g}b" x1="62" y1="0" x2="138" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.ac}"/><stop offset=".42" stop-color="${c.acHi}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient></defs>
  <rect x="30" y="134" width="140" height="52" fill="url(#${g}c)" clip-path="url(#${g}k)"/>
  <path d="${tri}" ${ST(c.ink,12)}/>
  <rect x="61" y="119" width="78" height="18" rx="9" fill="url(#${g}b)"/>
  <path d="M84 16 H116 M100 16 V36" ${ST(c.ac,10)}/>
  <path d="M100 45 C100 45 106.5 53 106.5 57.5 A6.5 6.5 0 0 1 93.5 57.5 C93.5 53 100 45 100 45 Z" fill="${c.ac}"/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Bitstream Charter',wt:700,fill:'ac',k:1.06,pre:.02,post:.03},{t:'ne',fam:'Inter Display',wt:500}]},
 cupTheme:'light'},

{id:'P2',dir:'P2_波形蒸氣',name:'波形蒸氣',en:'Steam Signal',ratio:[60,40],
 meaning:'卡布奇諾杯上升起的不是煙，是一段訊號波形——一杯咖啡的熱度，正在把新知傳給你。',
 ai:'文字標的 AI 用焦糖→薰衣草漸層＋ExtraBold＋襯線 I（Inter cv08），是整個名字裡唯一有漸層的字；圖形的蒸氣波形同一組漸層呼應。',
 color:'深可可杯身、焦糖杯緣，蒸氣由焦糖漸層到淡薰衣草（唯一點綴色，象徵 AI 的一點涼）。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）。',
 tech:'等距圓頭柱狀的音訊／資料波形、柔和雙色漸層。',
 draw:(c,o)=>{const g=uid();const xs=o.small?[64,82,100,118,136]:[58,72,86,100,114,128,142],hs=o.small?[24,48,66,40,20]:[14,28,46,66,42,24,12],sw=o.small?12:8;
  return `<defs><linearGradient id="${g}s" x1="0" y1="102" x2="0" y2="28" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.ac}"/><stop offset="1" stop-color="${c.lav}"/></linearGradient>
  <clipPath id="${g}k"><path d="M36 116 H164 C164 154 138 176 100 176 C62 176 36 154 36 116 Z"/></clipPath></defs>
  ${xs.map((x,i)=>`<path d="M${x} 102 V${102-hs[i]}" ${ST(`url(#${g}s)`,sw)}/>`).join('')}
  <path d="M158 128 C188 122 190 162 152 160" ${ST(c.ink,11)}/>
  <path d="M36 116 H164 C164 154 138 176 100 176 C62 176 36 154 36 116 Z" fill="${c.ink}"/>
  <rect x="30" y="116" width="140" height="9" fill="${c.ac}" clip-path="url(#${g}k)"/>
  <path d="M26 188 Q100 197 174 188" ${ST(c.ink,8)}/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'grad',feat:true,pre:.01,post:.02},{t:'ne',fam:'Inter Display',wt:600}]},
 cupTheme:'dark'},

{id:'P3',dir:'P3_對話杯',name:'對話杯',en:'Prompt Mug',ratio:[50,50],
 meaning:'馬克杯就是一個對話框：杯裡打下 A，焦糖色游標閃著當 I——一杯咖啡的時間，等你問一個問題。',
 ai:'圖形裡的 AI 是「A＋閃爍游標」，一看就是在跟 AI 對話；文字標的 AI 換成等寬字 JetBrains Mono ExtraBold，等寬 I 天生有上下襯線。',
 color:'深可可線條、焦糖游標，杯身內淡奶茶色填底，兩縷蒸氣用可可中間色。',
 type:'Inter SemiBold ＋ AI 用 JetBrains Mono ExtraBold。',
 tech:'對話框外形、文字游標、等寬字點綴。',
 draw:(c,o)=>{const bub='M58 48 H122 Q150 48 150 76 V126 Q150 154 122 154 H80 L50 176 L56 153 Q30 148 30 124 V76 Q30 48 58 48 Z';
  return `${o.small?'':`<path d="M72 36 C64 28 78 22 70 12 M94 36 C86 28 100 22 92 12" ${ST(c.mid,6)}/>`}
  <path d="${bub}" fill="${c.soft}"/>
  <path d="M150 80 H160 Q182 80 182 102 Q182 124 160 124 H150" ${ST(c.ink,12)}/>
  <path d="${bub}" ${ST(c.ink,12)}/>
  ${letterA(78,74,54,c.ink,12)}
  <rect x="106" y="71" width="14" height="60" rx="4" fill="${c.ac}"/>`},
 wm:{parts:[{t:'Caff',fam:'Inter',wt:600},{t:'AI',fam:'JetBrains Mono',wt:800,fill:'ac',k:1.04,pre:.04,post:.04},{t:'ne',fam:'Inter',wt:600}]},
 cupTheme:'light'},

{id:'P4',dir:'P4_分層拿鐵',name:'分層拿鐵',en:'Layered Latte',ratio:[70,30],
 meaning:'冰拿鐵的三層是 AI 新知被「分層萃取」：濃縮、焦糖、牛奶，交界是一道道波形；那根吸管就是 I，插進去一口就懂。',
 ai:'文字標的 AI 放進焦糖膠囊色塊（反白），是名字裡唯一有底色的兩個字，40px 也看得到一顆焦糖膠囊。',
 color:'濃縮→焦糖→牛奶的三層暖色層次，吸管是淡薰衣草（點綴色）。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）反白於膠囊。',
 tech:'正弦波形的分層交界、玻璃高光、精準的錐度。',
 draw:(c,o)=>{const g=uid(),inner='M50 42 H150 L141 177 Q140 182 135 182 H65 Q60 182 59 177 Z';
  const wave=(y,f)=>`<path d="M40 ${y} C70 ${y-8} 92 ${y+8} 120 ${y} S158 ${y-6} 164 ${y-2} V192 H40 Z" fill="${f}"/>`;
  return `<defs><clipPath id="${g}k"><path d="${inner}"/></clipPath></defs>
  <g clip-path="url(#${g}k)">${wave(62,c.l1)}${wave(98,c.l2)}${wave(134,c.milk)}
   <path d="M114 172 L122 64" ${ST(c.lav,9)} opacity=".55"/>
   <path d="M64 58 L71 160" ${ST('#FFFFFF',4)} opacity=".28"/></g>
  <path d="M122 64 L128 18 L150 8" ${ST(c.lav,9)}/>
  <path d="M50 42 L59 177 Q60 182 65 182 H135 Q140 182 141 177 L150 42" ${ST(c.ink,7)}/>
  <path d="M42 42 H158" ${ST(c.ink,7)}/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'bg',feat:true,pill:true,pre:.2,post:.2},{t:'ne',fam:'Inter Display',wt:600}]},
 cupTheme:'light'},

{id:'P5',dir:'P5_像素蒸氣',name:'像素蒸氣',en:'Pixel Steam',ratio:[45,55],
 meaning:'外帶杯的熱氣往上飄，在空中凝成一行點陣的「AI」——咖啡是載體，AI 是升起來的那一口新知。',
 ai:'AI 本身就是圖形的主角（點陣字，I 有襯線）；文字標的 AI 也用同一套點陣字，圖文同一套語言。',
 color:'深可可杯、焦糖杯套；點陣由焦糖（下）漸變到淡薰衣草（上），像熱氣變涼。',
 type:'Inter Display SemiBold ＋ AI 為手刻點陣字（5×7 格）。',
 tech:'點陣／像素字、由下往上的色溫漸層、逸散的小像素。',
 draw:(c,o)=>{const g=uid();
  if(o.small){const cell=14;return `<defs><clipPath id="${g}k"><path d="M50 150 H150 L142 210 H58 Z"/></clipPath></defs>
   ${pixAI(100-4.5*cell,22,cell,j=>lerp(c.lav,c.ac,j/6))}
   <rect x="40" y="134" width="120" height="14" rx="7" fill="${c.ink}"/><path d="M50 150 H150 L142 210 H58 Z" fill="${c.ink}"/>
   <rect x="40" y="164" width="120" height="30" fill="${c.ac}" clip-path="url(#${g}k)"/>`;}
  const cell=8.6;return `<defs><clipPath id="${g}k"><path d="M58 112 H142 L133 186 Q132 190 128 190 H72 Q68 190 67 186 Z"/></clipPath></defs>
  ${pixAI(100-4.5*cell,16,cell,j=>lerp(c.lav,c.ac,j/6))}
  <rect x="62" y="4" width="4.5" height="4.5" rx="1" fill="${c.lav}" opacity=".55"/><rect x="128" y="2" width="3.6" height="3.6" rx="1" fill="${c.lav}" opacity=".4"/><rect x="104" y="6" width="3" height="3" rx="1" fill="${c.lav}" opacity=".35"/>
  <path d="M62 98 Q64 88 74 88 H126 Q136 88 138 98 Z" fill="${c.ink}"/>
  <rect x="52" y="97" width="96" height="13" rx="6.5" fill="${c.ink}"/>
  <path d="M58 112 H142 L133 186 Q132 190 128 190 H72 Q68 190 67 186 Z" fill="${c.ink}"/>
  <rect x="50" y="136" width="100" height="26" fill="${c.ac}" clip-path="url(#${g}k)"/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{kind:'pixel',fill:'pix',pre:.06,post:.06},{t:'ne',fam:'Inter Display',wt:600}]},
 cupTheme:'dark'},

{id:'P6',dir:'P6_充電杯',name:'充電杯',en:'Charge Mug',ratio:[50,50],
 meaning:'杯裡的咖啡是四格電量——咖啡因替上班族充電，AI 新知替腦袋充電；喝完一杯，就充飽一格。',
 ai:'文字標的 AI 用焦糖 ExtraBold＋襯線 I，下方加一條「讀取進度條」只襯在 AI 底下，視線一定先落在 AI。',
 color:'深可可杯線、焦糖到深焙的橫向漸層電量格，第五格留空（淡色）。',
 type:'Inter Display Medium ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）。',
 tech:'電量格／讀取進度的介面語彙、水平漸層。',
 draw:(c,o)=>{const g=uid();const inner='M44 70 V138 Q44 166 72 166 H116 Q144 166 144 138 V70 Z';
  const segs=[0,1,2,3,4].map(i=>{const x=50+i*18.6;return `<rect x="${x}" y="84" width="13.6" height="92" rx="4" fill="${i<4?`url(#${g}g)`:c.ink}" ${i<4?'':'opacity=".16"'}/>`}).join('');
  return `<defs><clipPath id="${g}k"><path d="${inner}"/></clipPath>
  <linearGradient id="${g}g" x1="50" y1="0" x2="124" y2="0" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.acHi}"/><stop offset=".5" stop-color="${c.ac}"/><stop offset="1" stop-color="${c.cB}"/></linearGradient></defs>
  <g clip-path="url(#${g}k)">${segs}</g>
  <path d="M152 84 H164 Q184 84 184 106 V114 Q184 136 164 136 H152" ${ST(c.ink,13)}/>
  <path d="M36 58 V138 Q36 174 72 174 H116 Q152 174 152 138 V58" ${ST(c.ink,13)}/>
  ${o.small?'':`<path d="M84 40 C76 32 90 26 82 16 M106 40 C98 32 112 26 104 16" ${ST(c.mid,6)}/>`}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,progress:true,pre:.01,post:.02},{t:'ne',fam:'Inter Display',wt:500}]},
 cupTheme:'light'},

{id:'P7',dir:'P7_豆中靈光',name:'豆中靈光',en:'Bean Spark',ratio:[60,40],
 meaning:'咖啡豆中間那道縫，被畫成一顆四芒星的靈光——每一顆豆子裡，都藏著一個讓你「原來如此」的 AI 瞬間。',
 ai:'文字標的 AI 用焦糖 Bold＋襯線 I，I 的右上角掛一顆同款小四芒星，名字裡只有 AI 會發光。',
 color:'豆子用焦糖→深焙的光澤漸層（含一抹高光），縫隙是底色留白，外側一顆焦糖小星。',
 type:'Inter Display Medium ＋ AI 用 Inter Display Bold（cv08 襯線 I）。',
 tech:'精密的負空間星芒、光澤漸層；不靠任何電子元件就有「靈光」的科技暗示。',
 draw:(c,o)=>{const g=uid();const hi=c.name==='light'?['#A8693F','#5E3A26','#2B1D16']:['#F2B983','#D58A50','#9A5A30'];
  return `<defs><linearGradient id="${g}b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${hi[0]}"/><stop offset=".55" stop-color="${hi[1]}"/><stop offset="1" stop-color="${hi[2]}"/></linearGradient></defs>
  <g transform="rotate(-28 100 104)"><ellipse cx="100" cy="104" rx="58" ry="80" fill="url(#${g}b)"/>
  <ellipse cx="80" cy="70" rx="16" ry="30" fill="#FFFFFF" opacity=".13"/>
  <path d="M100 30 Q103.5 99 124 104 Q103.5 109 100 178 Q96.5 109 76 104 Q96.5 99 100 30 Z" fill="${c.bg}"/></g>
  ${o.small?'':spark(164,36,15,c.ac,.16)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Inter Display',wt:700,fill:'ac',feat:true,spark:true,pre:.01,post:.07},{t:'ne',fam:'Inter Display',wt:500}]},
 cupTheme:'dark'},

{id:'P8',dir:'P8_點單小票',name:'點單小票',en:'Order Ticket',ratio:[55,45],
 meaning:'咖啡館的點單小票：今天點的不是拿鐵，是一份 AI——撕下就能帶走，一杯咖啡的時間看完。',
 ai:'圖形主角就是一個大大的襯線 AI（Charter Bold），文字標用全大寫 CAFF·AI·NE，AI 換焦糖襯線字＋下方一條撕線虛線。',
 color:'奶油紙色小票、深可可字，焦糖只用在小杯印章與文字標 AI；不用橘字深底，避開 Illustrator 圖示。',
 type:'Inter Display Bold 全大寫字距 6% ＋ AI 用 Bitstream Charter Bold；票面小字用 JetBrains Mono。',
 tech:'感熱紙小票的等寬字、撕線虛線、票號 N°01——像一張系統列印出來的單據。',
 draw:(c,o)=>{const x0=44,x1=156,y0=22,y1=180,r=12;let z='';const n=7,tw=(x1-x0)/n;
  for(let i=0;i<n;i++){z+=`L${(x1-tw*i-tw/2).toFixed(1)} ${y1-7} L${(x1-tw*(i+1)).toFixed(1)} ${y1} `}
  const d=`M${x0+r} ${y0} H${x1-r} Q${x1} ${y0} ${x1} ${y0+r} V118 A9 9 0 0 0 ${x1} 136 V${y1} ${z} V136 A9 9 0 0 0 ${x0} 118 V${y0+r} Q${x0} ${y0} ${x0+r} ${y0} Z`;
  const paper=c.name==='light'?'#FFFBF5':'#F6EEE3',inkT='#2B1D16';
  return `<path d="${d}" fill="${paper}" stroke="${c.name==='light'?c.ink:'none'}" stroke-width="6" stroke-linejoin="round"/>
  ${o.small?'':`<text x="58" y="47" font-family="JetBrains Mono" font-weight="700" font-size="11" fill="${inkT}" opacity=".7">N°01</text><text x="142" y="47" text-anchor="end" font-family="JetBrains Mono" font-weight="700" font-size="11" fill="${inkT}" opacity=".7">TO GO</text>`}
  <text x="100" y="${o.small?112:106}" text-anchor="middle" font-family="Bitstream Charter" font-weight="700" font-size="${o.small?74:62}" fill="${inkT}" letter-spacing="1">AI</text>
  <path d="M60 127 H140" stroke="${inkT}" stroke-width="3" stroke-dasharray="5 5" stroke-linecap="round" opacity=".55"/>
  ${o.small?'':`<path d="M64 148 H80 L78 164 H66 Z" fill="${c.ac}"/><rect x="62" y="144" width="20" height="5" rx="2.5" fill="${c.ac}"/><text x="90" y="161" font-family="JetBrains Mono" font-weight="700" font-size="13" fill="${inkT}" opacity=".75">5 MIN</text>`}`},
 wm:{parts:[{t:'CAFF',fam:'Inter Display',wt:700,ls:.06},{t:'AI',fam:'Bitstream Charter',wt:700,fill:'ac',k:1.04,perf:true,pre:.08,post:.08},{t:'NE',fam:'Inter Display',wt:700,ls:.06}]},
 cupTheme:'light'},
];

// ───────── 量字 ─────────
const NS='http://www.w3.org/2000/svg';let MS;
function meas(t,fam,wt,size,ls=0,feat=false){if(!MS){MS=document.createElementNS(NS,'svg');MS.setAttribute('width','2000');MS.setAttribute('height','400');MS.style.cssText='position:absolute;left:-3000px;top:0';document.body.appendChild(MS);}
 const e=document.createElementNS(NS,'text');e.setAttribute('font-family',fam);e.setAttribute('font-weight',wt);e.setAttribute('font-size',size);if(ls)e.setAttribute('letter-spacing',ls);if(feat)e.setAttribute('style',"font-feature-settings:'cv08' 1");e.textContent=t;MS.appendChild(e);const w=e.getComputedTextLength();e.remove();return w;}
const FEAT=` style="font-feature-settings:'cv08' 1"`;
// 文字標：回傳 {svg, w}；基線在 y=base（呼叫者給）
function wordmark(d,c,S,x0,base){const D=DIRS.find(q=>q.id===d);let x=x0,o='',defs='';const capH=S*.727;
 for(const p of D.wm.parts){x+=(p.pre||0)*S;
  if(p.kind==='pixel'){const cell=capH/7;const pw=9*cell;o+=pixAI(x,base-capH,cell,()=>c.ac,.05);x+=pw+(p.post||0)*S;continue;}
  const fs=S*(p.k||1),ls=(p.ls||0)*fs,w=meas(p.t,p.fam,p.wt,fs,ls,p.feat)-(p.ls?ls:0);
  let fill=p.fill==='ac'?c.ac:p.fill==='bg'?c.bg:c.ink;
  if(p.fill==='grad'){const g=uid();defs+=`<linearGradient id="${g}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${c.ac}"/><stop offset="1" stop-color="${c.lav}"/></linearGradient>`;fill=`url(#${g})`;}
  if(p.pill){const px=S*.15,py=S*.13;o+=`<rect x="${(x-px).toFixed(1)}" y="${(base-capH-py).toFixed(1)}" width="${(w+2*px).toFixed(1)}" height="${(capH+2*py).toFixed(1)}" rx="${((capH+2*py)/2).toFixed(1)}" fill="${c.ac}"/>`;}
  o+=`<text x="${x.toFixed(1)}" y="${base.toFixed(1)}" font-family="${p.fam}" font-weight="${p.wt}" font-size="${fs.toFixed(1)}"${ls?` letter-spacing="${ls.toFixed(1)}"`:''} fill="${fill}"${p.feat?FEAT:''}>${p.t}</text>`;
  if(p.progress){const y=base+S*.13,h=S*.055;o+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="${(h/2).toFixed(1)}" fill="${c.ac}" opacity=".22"/><rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(w*.8).toFixed(1)}" height="${h.toFixed(1)}" rx="${(h/2).toFixed(1)}" fill="${c.ac}"/>`;}
  if(p.perf){const y=base+S*.12;o+=`<path d="M${(x+S*.02).toFixed(1)} ${y.toFixed(1)} H${(x+w-S*.02).toFixed(1)}" stroke="${c.ac}" stroke-width="${(S*.035).toFixed(1)}" stroke-dasharray="${(S*.06).toFixed(1)} ${(S*.06).toFixed(1)}" stroke-linecap="round"/>`;}
  if(p.spark){o+=spark(x+w+S*.03,base-capH-S*.13,S*.085,c.ac,.16);}
  x+=w+(p.post||0)*S;}
 return {svg:(defs?`<defs>${defs}</defs>`:'')+o,w:x-x0,capH};}
const TAG='一杯咖啡的時間，看懂一個 AI 新知';
function tagline(c,size,x,y,anchor='start',maxW){const s1='一杯咖啡的時間，看懂一個 ',s3=' 新知';
 const w=meas(s1,'WenQuanYi Zen Hei',400,size)+meas('AI','Inter',800,size)+meas(s3,'WenQuanYi Zen Hei',400,size);
 const X=anchor==='middle'?x-w/2:x;
 return {svg:`<text x="${X.toFixed(1)}" y="${y.toFixed(1)}" font-family="WenQuanYi Zen Hei" font-size="${size}" fill="${c.ink}" fill-opacity=".86">${s1}<tspan font-family="Inter" font-weight="800" fill="${c.ac}" fill-opacity="1">AI</tspan>${s3}</text>`,w};}

// ───────── 輸出元件 ─────────
const svgW=(w,h,inner)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">${inner}</svg>`;
const mark=(d,c,o={})=>DIRS.find(q=>q.id===d).draw(c,o);
function icon(d,th,o={}){const c=TH[th];return svgW(200,200,`<rect width="200" height="200" fill="${c.bg}"/>${mark(d,c,o)}`);}
function avatarInner(d,th,px){const c=TH[th],small=px<=48,s=px*(small?.74:.66)/200,off=(px-200*s)/2;
 return `<circle cx="${px/2}" cy="${px/2}" r="${px/2}" fill="${c.bg}"/><g transform="translate(${off.toFixed(2)} ${off.toFixed(2)}) scale(${s.toFixed(4)})">${mark(d,c,{small})}</g>`;}
const avatar=(d,th,px)=>svgW(px,px,avatarInner(d,th,px));
function lockup(d,th){const c=TH[th],M=320,S=148,gap=76,pad=96,tagS=40;
 const tmp=wordmark(d,c,S,0,0),tg=tagline(c,tagS,0,0);const textW=Math.max(tmp.w,tg.w);
 const blockH=tmp.capH+ (S*.2) +46+tagS;const H=Math.max(M,blockH)+pad*2,W=pad+M+gap+textW+pad;
 const top=(H-blockH)/2,base=top+tmp.capH;const wm=wordmark(d,c,S,pad+M+gap,base);
 const tl=tagline(c,tagS,pad+M+gap+(d==='P8'?0:0),base+S*.2+46+tagS*.82);
 return svgW(Math.ceil(W),Math.ceil(H),`<rect class="bgx" width="100%" height="100%" fill="${c.bg}"/><g data-el="mark" transform="translate(${pad} ${(H-M)/2}) scale(${M/200})">${mark(d,c)}</g><g data-el="word">${wm.svg}</g><g data-el="tag">${tl.svg}</g>`);}

// IG 個人頁（淺色 IG 介面，大頭貼用深底版）
function igProfile(d){const c=TH.light,W=1080,H=760;const D=DIRS.find(q=>q.id===d);
 const st=(x,n,l)=>`<text x="${x}" y="236" text-anchor="middle" font-family="Inter" font-weight="700" font-size="40" fill="#111">${n}</text><text x="${x}" y="282" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="27" fill="#333">${l}</text>`;
 const wm=wordmark(d,c,50,48,428);const tl=tagline(c,30,48,498);
 return svgW(W,H,`<rect class="bgx" width="${W}" height="${H}" fill="#FFFFFF"/>
 <g data-el="ui"><text x="48" y="76" font-family="Inter" font-weight="700" font-size="36" fill="#111">caffaine.ai</text><path d="M1012 54 H1040 M1012 66 H1040 M1012 78 H1040" stroke="#111" stroke-width="4" stroke-linecap="round"/></g>
 <g data-el="mark" transform="translate(48 140)">${avatarInner(d,'dark',200)}</g>
 <g data-el="stats">${st(460,'128','貼文')}${st(660,'5,240','粉絲')}${st(860,'36','追蹤中')}</g>
 <g data-el="word">${wm.svg}</g>
 <g data-el="tag">${tl.svg}</g>
 <g data-el="bio"><text x="48" y="560" font-family="WenQuanYi Zen Hei" font-size="28" fill="#333">上班族的 AI 使用技巧｜第一手 AI 新知</text></g>
 <g data-el="btn"><rect x="48" y="620" width="482" height="70" rx="14" fill="#0095F6"/><text x="289" y="666" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="30" fill="#fff">追蹤</text><rect x="550" y="620" width="482" height="70" rx="14" fill="#EFEFEF"/><text x="791" y="666" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="30" fill="#111">訊息</text></g>`);}

// 外帶杯杯身
function cupMock(d){const D=DIRS.find(q=>q.id===d),th=D.cupTheme,c=TH[th],W=800,H=1000;
 const body=th==='light'?'#FFFBF5':'#2B1D16',sleeve=th==='light'?'#E3C9A6':'#47322A';
 const bw=y=>400-100*(y-160)/740;const g=uid();
 const S=60;const tmp=wordmark(d,c,S,0,0);const wx=400-tmp.w/2;const wm=wordmark(d,c,S,wx,560);
 const l1=`<text x="400" y="680" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="27" fill="${c.ink}" fill-opacity=".9">一杯咖啡的時間</text><text x="400" y="722" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="27" fill="${c.ink}" fill-opacity=".9">看懂一個 <tspan font-family="Inter" font-weight="800" fill="${c.ac}">AI</tspan> 新知</text>`;
 const cupPath='M200 160 H600 L552 890 Q550 905 535 905 H265 Q250 905 248 890 Z';
 return svgW(W,H,`<defs><linearGradient id="${g}bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#EFE5D8"/><stop offset="1" stop-color="#E2D3C0"/></linearGradient>
 <linearGradient id="${g}sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".10"/><stop offset=".25" stop-color="#fff" stop-opacity=".10"/><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".16"/></linearGradient>
 <clipPath id="${g}k"><path d="${cupPath}"/></clipPath></defs>
 <rect class="bgx" width="${W}" height="${H}" fill="url(#${g}bg)"/>
 <ellipse cx="400" cy="930" rx="230" ry="26" fill="#000" opacity=".10"/>
 <path d="${cupPath}" fill="${body}"/>
 <rect x="150" y="620" width="500" height="140" fill="${sleeve}" clip-path="url(#${g}k)"/>
 <path d="${cupPath}" fill="url(#${g}sh)"/>
 <path d="M222 128 Q226 96 262 96 H538 Q574 96 578 128 Z" fill="${th==='light'?'#2B1D16':'#1C130F'}"/>
 <rect x="184" y="126" width="432" height="38" rx="19" fill="${th==='light'?'#2B1D16':'#1C130F'}"/>
 <g data-el="mark" transform="translate(${400-115} 222) scale(${230/200})">${mark(d,c)}</g>
 <g data-el="word">${wm.svg}</g>
 <g data-el="tag">${l1}</g>`);}

// 1080×1350 貼文封面（左上角放 LOGO）
function postCover(d){const c=TH.light,W=1080,H=1350;const S=46;
 const wm=wordmark(d,c,S,72+104+28,72+52+S*.727/2);const tl=tagline(c,30,72,1278);const g=uid();
 return svgW(W,H,`<defs><linearGradient id="${g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F8F1E7"/><stop offset="1" stop-color="#EFE2D0"/></linearGradient></defs>
 <rect class="bgx" width="${W}" height="${H}" fill="url(#${g})"/>
 <g data-el="mark" transform="translate(72 72) scale(${104/200})">${mark(d,c)}</g>
 <g data-el="word">${wm.svg}</g>
 <g data-el="label"><rect x="824" y="94" width="184" height="60" rx="30" fill="none" stroke="${c.ink}" stroke-width="2.5"/><text x="916" y="134" text-anchor="middle" font-family="JetBrains Mono" font-weight="700" font-size="25" fill="${c.ink}">TIPS #01</text></g>
 <g data-el="head"><text font-family="WenQuanYi Zen Hei" font-size="112" fill="${c.ink}"><tspan x="72" y="470">3 個提示詞</tspan><tspan x="72" y="620">讓週報</tspan><tspan x="72" y="770"><tspan fill="${c.ac}">5 分鐘</tspan>寫完</tspan></text></g>
 <g data-el="sub"><rect x="72" y="852" width="92" height="6" rx="3" fill="${c.ac}"/><text x="72" y="924" font-family="WenQuanYi Zen Hei" font-size="38" fill="${c.ink}" fill-opacity=".8">複製就能用，範本在第 2 頁</text></g>
 <g data-el="tag">${tl.svg}</g>
 <g data-el="ui"><text x="1008" y="1278" text-anchor="end" font-family="JetBrains Mono" font-weight="700" font-size="26" fill="${c.ink}" fill-opacity=".7">SWIPE →</text></g>`);}

window.CF={TH,DIRS:DIRS.map(({draw,...r})=>r),icon,avatar,lockup,igProfile,cupMock,postCover};
})();
