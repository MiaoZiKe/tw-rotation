// CaffAIne 專業版 8 方向：瀏覽器端設計庫（全部手寫 SVG 向量，無 AI 生圖、無角色）
// 由 build.js 注入頁面後呼叫 window.CF.*，回傳 SVG 字串。
(function(){
let U=0;const uid=()=>'k'+(++U)+Math.random().toString(36).slice(2,6);
const TH={
 light:{name:'light',bg:'#F6EEE3',ink:'#2B1D16',ac:'#C2652B',acHi:'#E8A066',mid:'#8A5A3C',soft:'#E9D8C2',lav:'#8676D6',lavT:'#7B69D0',paper:'#FFFBF5',cA:'#7A4B2E',cB:'#2B1D16',milk:'#EADBC6',l1:'#3A261C',l2:'#B4713F'},
 dark:{name:'dark',bg:'#2B1D16',ink:'#F6EEE3',ac:'#EB8D4E',acHi:'#F8BE8A',mid:'#C79A74',soft:'#47322A',lav:'#B6AAF2',lavT:'#BDB2F5',paper:'#3A2A21',cA:'#E0A06C',cB:'#9A5A30',milk:'#F1E4D2',l1:'#6E3F24',l2:'#D88B52'}};
const ST=(col,w)=>`fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"`;
const lerp=(a,b,t)=>{const p=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));const A=p(a),B=p(b);return '#'+A.map((v,i)=>Math.round(v+(B[i]-v)*t).toString(16).padStart(2,'0')).join('')};
// 像素字 AI（5x7 的 A ＋ 3x7 襯線 I）
const PA=['..#..','.#.#.','#...#','#...#','#####','#...#','#...#'],PI=['###','.#.','.#.','.#.','.#.','.#.','###'];
function pixAI(x,y,cell,colFn,gr=.14){let o='';const g=cell*gr,r=cell*.2;
 PA.forEach((row,j)=>[...row].forEach((ch,i)=>{if(ch==='#')o+=`<rect x="${(x+i*cell+g/2).toFixed(2)}" y="${(y+j*cell+g/2).toFixed(2)}" width="${(cell-g).toFixed(2)}" height="${(cell-g).toFixed(2)}" rx="${r.toFixed(2)}" fill="${colFn(j)}"/>`}));
 PI.forEach((row,j)=>[...row].forEach((ch,i)=>{if(ch==='#')o+=`<rect x="${(x+(6+i)*cell+g/2).toFixed(2)}" y="${(y+j*cell+g/2).toFixed(2)}" width="${(cell-g).toFixed(2)}" height="${(cell-g).toFixed(2)}" rx="${r.toFixed(2)}" fill="${colFn(j)}"/>`}));
 return o;}
const spark=(cx,cy,R,fill,k=.18)=>{const r=R*k;return `<path d="M${cx} ${cy-R} Q${cx+r} ${cy-r} ${cx+R} ${cy} Q${cx+r} ${cy+r} ${cx} ${cy+R} Q${cx-r} ${cy+r} ${cx-R} ${cy} Q${cx-r} ${cy-r} ${cx} ${cy-R} Z" fill="${fill}"/>`};
const letterA=(x,y,h,col,w,k=.38)=>{const hw=h*k;return `<path d="M${x-hw} ${y+h} L${x} ${y} L${x+hw} ${y+h} M${x-hw*.6} ${y+h*.7} H${x+hw*.6}" ${ST(col,w)}/>`};

// ───────── 8 個方向 ─────────
const P3draw=(c,o)=>{const g=uid();const bub='M58 48 H122 Q150 48 150 76 V126 Q150 154 122 154 H120 L132 171 L103 154 H58 Q30 154 30 126 V76 Q30 48 58 48 Z';
  return `<defs><linearGradient id="${g}c" x1="0" y1="71" x2="0" y2="131" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.acHi}"/><stop offset=".55" stop-color="${c.ac}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient></defs>
  ${o.small?'':`<path d="M72 36 C64 28 78 22 70 12 M94 36 C86 28 100 22 92 12" ${ST(c.mid,6)}/>`}
  <path d="${bub}" fill="${c.soft}"/>
  <path d="M150 80 H160 Q182 80 182 102 Q182 124 160 124 H150" ${ST(c.ink,12)}/>
  <path d="${bub}" ${ST(c.ink,12)}/>
  ${letterA(78,74,54,c.ink,12)}
  <rect x="106" y="71" width="14" height="60" rx="4" fill="url(#${g}c)"/>
  <rect x="108.2" y="74" width="2.4" height="46" rx="1.2" fill="#FFFFFF" opacity=".45"/>`};
const P3base={name:'對話杯',en:'Prompt Mug',ratio:[50,50],
 meaning:'馬克杯就是一個對話框：杯裡打下 A，焦糖色游標閃著當 I——一杯咖啡的時間，等你問一個問題。',
 color:'深可可線條、奶茶色杯底；游標是焦糖由亮到深的漸層加一道內光；兩縷蒸氣用可可中間色。',
 tech:'對話框外形、帶內光的文字游標（可做閃爍動畫）、文字標 AI 的焦糖→薰衣草漸層。',draw:P3draw,cupTheme:'light'};
const DIRS=[
{...P3base,id:'F1',dir:'F1_P3對話杯',sub:'主推：AI 漸層字標',
 ai:'圖形是「A＋游標 I」；文字標 AI 用 Inter Display ExtraBold＋襯線 I，填焦糖→薰衣草漸層（同 P2），名字裡唯一有漸層的兩個字。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）漸層。',
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'grad',feat:true,pre:.015,post:.025},{t:'ne',fam:'Inter Display',wt:600}]}},
{...P3base,id:'F1b',dir:'F1b_P3對話杯_等寬AI',sub:'比較版：等寬字 AI',
 ai:'圖形同 F1；文字標 AI 維持 JetBrains Mono ExtraBold 焦糖色（等寬 I 天生有上下襯線）。',
 type:'Inter SemiBold ＋ AI 用 JetBrains Mono ExtraBold。',
 wm:{parts:[{t:'Caff',fam:'Inter',wt:600},{t:'AI',fam:'JetBrains Mono',wt:800,fill:'ac',k:1.04,pre:.04,post:.04},{t:'ne',fam:'Inter',wt:600}]}},
{id:'F2',dir:'F2_P7豆中靈光',name:'豆中靈光',en:'Bean Cursor',sub:'修：拿掉星形，豆縫改成游標',ratio:[60,40],
 meaning:'咖啡豆的那道縫就是一根閃爍的游標（I），左半邊留白出一個 A——每一顆豆子裡，都在打一個 AI 的答案。',
 ai:'圖形負空間直接讀得出「A＋游標 I」（與主推 P3 同一套語言）；文字標 AI 焦糖 Bold＋襯線 I。',
 color:'豆子焦糖→深焙的光澤漸層＋右上一抹高光，A 與豆縫是底色留白；不再有任何星形。',
 type:'Inter Display Medium ＋ AI 用 Inter Display Bold（cv08 襯線 I）。',
 tech:'負空間的 A 與游標、豆縫末端收細成資料線；光澤漸層。',
 draw:(c,o)=>{const g=uid();const hi=c.name==='light'?['#A8693F','#5E3A26','#2B1D16']:['#F2B983','#D58A50','#9A5A30'];
  return `<defs><linearGradient id="${g}b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${hi[0]}"/><stop offset=".55" stop-color="${hi[1]}"/><stop offset="1" stop-color="${hi[2]}"/></linearGradient></defs>
  <g transform="rotate(-16 100 104)"><ellipse cx="100" cy="104" rx="66" ry="84" fill="url(#${g}b)"/>
  <ellipse cx="140" cy="66" rx="11" ry="22" fill="#FFFFFF" opacity=".14"/>
  ${letterA(76,76,58,c.bg,12.5,.37)}
  <rect x="111" y="70" width="13" height="70" rx="4" fill="${c.bg}"/>
  ${o.small?'':`<path d="M117.5 60 C118 46 114 36 108 28 M117.5 150 C117 164 120 174 124 180" ${ST(c.bg,4)}/>`}</g>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Inter Display',wt:700,fill:'ac',feat:true,pre:.01,post:.025},{t:'ne',fam:'Inter Display',wt:500}]},
 cupTheme:'dark'},
{id:'F3',dir:'F3_P5像素蒸氣',name:'像素蒸氣',en:'Pixel Steam',sub:'修：點陣 A 重畫（尖頂、橫槓下移），杯套加紋理',ratio:[45,55],
 meaning:'外帶杯的熱氣往上飄，在空中凝成一行點陣的「AI」——咖啡是載體，AI 是升起來的那一口新知。',
 ai:'AI 本身就是圖形主角；點陣 A 改成尖頂封口、橫槓在第 5 列，不會再讀成 H；文字標同一套點陣字。',
 color:'深可可杯、焦糖杯套（細直紋）；點陣由焦糖（下）漸變到淡薰衣草（上）。',
 type:'Inter Display SemiBold ＋ AI 為手刻點陣字（5×7 格）。',
 tech:'點陣字、由下往上的色溫漸層、逸散的小像素。',
 draw:(c,o)=>{const g=uid();const rib=(x0,x1,y0,y1,col)=>{let s='';for(let x=x0;x<=x1;x+=6)s+=`<path d="M${x} ${y0} V${y1}" stroke="${col}" stroke-width="1.6" opacity=".35"/>`;return s;};
  if(o.small){const cell=14;return `<defs><clipPath id="${g}k"><path d="M50 150 H150 L142 210 H58 Z"/></clipPath></defs>
   ${pixAI(100-4.5*cell,22,cell,j=>lerp(c.lav,c.ac,j/6),.1)}
   <rect x="40" y="134" width="120" height="14" rx="7" fill="${c.ink}"/><path d="M50 150 H150 L142 210 H58 Z" fill="${c.ink}"/>
   <rect x="40" y="164" width="120" height="30" fill="${c.ac}" clip-path="url(#${g}k)"/>`;}
  const cell=8.6,body='M58 112 H142 L133 186 Q132 190 128 190 H72 Q68 190 67 186 Z',dk=c.name==='light'?'#7A3A14':'#9A4F22';
  return `<defs><clipPath id="${g}k"><path d="${body}"/></clipPath>
  <linearGradient id="${g}s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${c.ac}"/><stop offset=".35" stop-color="${c.acHi}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient></defs>
  ${pixAI(100-4.5*cell,16,cell,j=>lerp(c.lav,c.ac,j/6),.12)}
  <rect x="62" y="4" width="4.5" height="4.5" rx="1" fill="${c.lav}" opacity=".55"/><rect x="128" y="2" width="3.6" height="3.6" rx="1" fill="${c.lav}" opacity=".4"/>
  <path d="M62 98 Q64 88 74 88 H126 Q136 88 138 98 Z" fill="${c.ink}"/>
  <rect x="112" y="91" width="12" height="3" rx="1.5" fill="${c.bg}" opacity=".55"/>
  <rect x="52" y="97" width="96" height="13" rx="6.5" fill="${c.ink}"/>
  <path d="${body}" fill="${c.ink}"/>
  <g clip-path="url(#${g}k)"><rect x="50" y="134" width="100" height="30" fill="url(#${g}s)"/>${rib(60,140,134,164,dk)}</g>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{kind:'pixel',fill:'pix',pre:.06,post:.06},{t:'ne',fam:'Inter Display',wt:600}]},
 cupTheme:'dark'},
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
  if(p.fill==='grad'){const g=uid();defs+=`<linearGradient id="${g}" x1="0" y1="0" x2="1" y2="0"><stop offset=".08" stop-color="${c.ac}"/><stop offset=".95" stop-color="${c.lavT}"/></linearGradient>`;fill=`url(#${g})`;}
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
