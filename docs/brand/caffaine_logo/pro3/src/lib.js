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
const textT=(x,y,t,fam,wt,size,fill,extra='')=>`<text x="${x}" y="${y}" font-family="${fam}" font-weight="${wt}" font-size="${size}" fill="${fill}" ${extra}>${t}</text>`;
const serifI=(x,y,h,col,w,hw)=>`<path d="M${x-hw} ${y} H${x+hw} M${x} ${y} V${y+h} M${x-hw} ${y+h} H${x+hw}" ${ST(col,w)}/>`;
const PA2=['..#..','.#.#.','#...#','#...#','#####','#...#','#...#'];
function beanAI(x,y,cell,colFn,ghost,big){let o='';const rx=cell*(big?.5:.42),ry=cell*(big?.4:.3);const b=(cx,cy,f,op)=>`<g transform="rotate(-30 ${cx.toFixed(1)} ${cy.toFixed(1)})"><ellipse cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" rx="${rx.toFixed(2)}" ry="${ry.toFixed(2)}" fill="${f}"${op?` opacity="${op}"`:''}/>${op||big?'':`<path d="M${(cx-rx*.7).toFixed(1)} ${cy.toFixed(1)} Q${cx.toFixed(1)} ${(cy-ry*.5).toFixed(1)} ${(cx+rx*.7).toFixed(1)} ${cy.toFixed(1)}" fill="none" stroke="#FFF7EA" stroke-opacity=".55" stroke-width="${(cell*.06).toFixed(2)}" stroke-linecap="round"/>`}</g>`;
 for(let j=0;j<7;j++)for(let i=0;i<9;i++){const cx=x+i*cell+cell/2,cy=y+j*cell+cell/2;let on=false;
  if(i<5)on=PA2[j][i]==='#';else if(i>5){on=['###','.#.','.#.','.#.','.#.','.#.','###'][j][i-6]==='#';}
  if(on)o+=b(cx,cy,colFn(j));else if(ghost&&i!==5)o+=b(cx,cy,ghost,.09);}
 return o;}
const drop=(cx,cy,r,rot,fill)=>`<path transform="rotate(${rot} ${cx} ${cy})" d="M${cx} ${cy-r*2.2} C${cx+r*.35} ${cy-r*1.5} ${cx+r} ${cy-r*.8} ${cx+r} ${cy} A${r} ${r} 0 1 1 ${cx-r} ${cy} C${cx-r} ${cy-r*.8} ${cx-r*.35} ${cy-r*1.5} ${cx} ${cy-r*2.2} Z" fill="${fill}"/>`;
const PAPER=c=>c.name==='light'?'#FFFBF4':'#F6EEE3';
const DIRS=[
{id:'S1',dir:'S1_書頁杯',name:'書頁杯',en:'Book Cup',ratio:[55,45],
 meaning:'一本書翻開，兩頁彎成一只杯子，左頁是 A、右頁是 I——一杯咖啡的時間，讀懂一頁新知。',
 ai:'左右兩頁各印一個焦糖色字母，合起來是 AI；文字標的 AI 用襯線粗體並劃上一道螢光筆重點。',
 color:'奶油紙頁（右頁略深）、深可可輪廓與杯耳、焦糖字與蒸氣。',
 type:'Inter Display Medium ＋ AI 用 Bitstream Charter Bold，下半襯焦糖螢光筆色塊。',
 tech:'書頁的精準對稱曲線、螢光筆劃重點的閱讀介面語彙。',
 draw:(c,o)=>{const p=PAPER(c),p2=c.name==='light'?'#EEDFC8':'#E3CFB2',ink=c.ink;
  return `${o.small?'':`<path d="M100 72 C92 60 108 50 100 36 S106 18 100 8" ${ST(c.mid,6)}/>`}
  <path d="M158 116 C186 112 188 150 152 152" ${ST(ink,11)}/>
  <path d="M100 92 C82 80 56 78 34 84 L50 172 Q52 180 60 180 H100 Z" fill="${p}"/>
  <path d="M100 92 C118 80 144 78 166 84 L150 172 Q148 180 140 180 H100 Z" fill="${p2}"/>
  <path d="M100 92 C82 80 56 78 34 84 L50 172 Q52 180 60 180 H140 Q148 180 150 172 L166 84 C144 78 118 80 100 92 Z M100 92 V180" ${ST(ink,6)}/>
  ${letterA(70,104,52,c.ac,o.small?12:10,.33)}${serifI(132,104,52,c.ac,o.small?12:10,o.small?11:10)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Bitstream Charter',wt:700,fill:'ac',k:1.05,pre:.06,post:.07,
   under:(c,S,x,w,base,capH)=>`<rect x="${(x-S*.05).toFixed(1)}" y="${(base-capH*.42).toFixed(1)}" width="${(w+S*.1).toFixed(1)}" height="${(capH*.5).toFixed(1)}" rx="${(S*.03).toFixed(1)}" fill="${c.acHi}" opacity=".38"/>`},{t:'ne',fam:'Inter Display',wt:500}]},cupTheme:'light'},

{id:'S2',dir:'S2_時鐘杯',name:'一杯的時間',en:'Cup O\'Clock',ratio:[55,45],
 meaning:'馬克杯上的時鐘停在「一杯咖啡的時間」：時針分針合成 A、秒針是橫槓，1 點鐘的羅馬數字正好是 I。',
 ai:'時針＋分針＋秒針拼成 A，羅馬數字 I 在 1 點鐘的位置；文字標的 AI 焦糖 ExtraBold 襯線 I，旁邊不加裝飾，讓杯上的鐘說話。',
 color:'深可可杯身、奶油色指針與 I、焦糖秒針與軸心。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）。',
 tech:'錶盤的精準刻度與指針幾何，像智慧手錶的錶面。',
 draw:(c,o)=>{const cr=c.bg,ink=c.ink;return `${o.small?'':`<path d="M70 52 C62 42 78 34 70 22 M96 52 C88 42 104 34 96 22" ${ST(c.mid,6)}/>`}
  <path d="M152 86 H162 Q184 86 184 110 Q184 134 162 134 H152" ${ST(ink,12)}/>
  <path d="M34 62 H154 V138 Q154 180 114 180 H74 Q34 180 34 138 Z" fill="${ink}"/>
  <circle cx="90" cy="76" r="3.2" fill="${cr}" opacity=".7"/><circle cx="52" cy="112" r="3.2" fill="${cr}" opacity=".7"/>
  <path d="M90 108 L64 160 M90 108 L116 160" ${ST(cr,o.small?12:10)}/>
  <path d="M60 140 H122" ${ST(c.ac,o.small?6:4.5)}/>
  <circle cx="90" cy="108" r="${o.small?8:6.5}" fill="${c.ac}"/>
  ${serifI(130,72,34,cr,o.small?9:7.5,o.small?8:7)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.015,post:.025},{t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'dark'},

{id:'S3',dir:'S3_燈泡杯',name:'燈泡杯',en:'Bright Cup',ratio:[45,55],
 meaning:'外帶杯就是燈座、杯套是螺紋，上面那顆燈泡的燈絲寫著 AI——喝一口，腦袋就亮了。',
 ai:'燈絲直接彎成 AI（焦糖發光），燈泡內有柔和光暈；文字標的 AI 帶同款光暈色塊。',
 color:'深可可杯身、焦糖螺紋；燈泡奶白透光、焦糖光→焦糖燈絲。',
 type:'Inter Display Medium ＋ AI 用 Inter Display ExtraBold（cv08）焦糖，背後一團柔光。',
 tech:'燈絲的單線幾何、放射光暈（純漸層，不用模糊濾鏡）。',
 draw:(c,o)=>{const g=uid(),ink=c.ink,lt=c.name==='light';const bulb='M72 116 C72 102 46 92 46 62 C46 32 70 12 100 12 C130 12 154 32 154 62 C154 92 128 102 128 116 Z';
  return `<defs><radialGradient id="${g}r" cx=".5" cy=".55" r=".55"><stop offset="0" stop-color="${c.acHi}" stop-opacity=".75"/><stop offset="1" stop-color="${c.acHi}" stop-opacity="0"/></radialGradient></defs>
  <path d="${bulb}" fill="${lt?'#FFFBF4':'#3A2A21'}"/><path d="${bulb}" fill="url(#${g}r)"/>
  <path d="M86 116 V96 M114 116 V96" ${ST(c.mid,3)}/>
  ${letterA(84,44,52,c.ac,o.small?11:8,.3)}${serifI(116,44,52,c.ac,o.small?11:8,8)}
  <path d="${bulb}" ${ST(ink,6)}/>
  <path d="M60 122 H140 L132 182 Q131 188 125 188 H75 Q69 188 68 182 Z" fill="${ink}"/>
  <path d="M66 140 H134 M68 156 H132" ${ST(c.ac,5)}/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.05,post:.06,
   under:(c,S,x,w,base,capH)=>{const g=uid();return `<defs><radialGradient id="${g}"><stop offset="0" stop-color="${c.acHi}" stop-opacity=".55"/><stop offset="1" stop-color="${c.acHi}" stop-opacity="0"/></radialGradient></defs><ellipse cx="${(x+w/2).toFixed(1)}" cy="${(base-capH/2).toFixed(1)}" rx="${(w*.95).toFixed(1)}" ry="${(capH*.95).toFixed(1)}" fill="url(#${g})"/>`}},{t:'ne',fam:'Inter Display',wt:500}]},cupTheme:'dark'},

{id:'S4',dir:'S4_手搖磨豆',name:'手搖磨豆',en:'Hand Grinder',ratio:[70,30],
 meaning:'手搖磨豆機轉一圈，把一大堆 AI 資訊磨成剛好一杯的粉——磨豆機正面刻著 AI。',
 ai:'木盒正面是大大的奶油色 AI；文字標的 AI 上方有一道虛線旋轉弧，像搖桿轉過的軌跡。',
 color:'焦糖木紋漸層木盒、深可可金屬斗與搖桿、焦糖虛線軌跡。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08）。',
 tech:'虛線運動軌跡（像動畫路徑）、精準的機構幾何。',
 draw:(c,o)=>{const g=uid(),ink=c.ink,lt=c.name==='light';
  return `<defs><linearGradient id="${g}w" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${lt?'#B4713F':'#D98A50'}"/><stop offset="1" stop-color="${lt?'#7A4524':'#A8612F'}"/></linearGradient></defs>
  ${o.small?'':`<path d="M48 64 A54 13 0 0 1 152 58" fill="none" stroke="${c.ac}" stroke-width="3" stroke-dasharray="6 6" stroke-linecap="round"/>`}
  <path d="M100 98 V66 H148" ${ST(ink,8)}/><path d="M148 66 V50" ${ST(ink,8)}/><rect x="141" y="30" width="14" height="22" rx="7" fill="${c.ac}"/>
  <path d="M62 112 L72 92 H128 L138 112 Z" fill="${ink}"/>
  <rect x="44" y="112" width="112" height="74" rx="10" fill="url(#${g}w)"/>
  <path d="M44 124 H156" stroke="${ink}" stroke-opacity=".25" stroke-width="2"/>
  ${letterA(84,134,40,'#FFF7EA',o.small?11:9,.34)}${serifI(120,134,40,'#FFF7EA',o.small?11:9,o.small?9:8)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.015,post:.025,
   over:(c,S,x,w,base,capH)=>`<path d="M${(x-S*.04).toFixed(1)} ${(base-capH-S*.1).toFixed(1)} Q${(x+w/2).toFixed(1)} ${(base-capH-S*.28).toFixed(1)} ${(x+w+S*.04).toFixed(1)} ${(base-capH-S*.1).toFixed(1)}" fill="none" stroke="${c.ac}" stroke-width="${(S*.03).toFixed(1)}" stroke-dasharray="${(S*.05).toFixed(1)} ${(S*.05).toFixed(1)}" stroke-linecap="round"/>`},{t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'light'},

{id:'S5',dir:'S5_咖啡豆讀秒',name:'咖啡豆讀秒',en:'Bean Countdown',ratio:[50,50],
 meaning:'一顆顆咖啡豆排成點陣看板，亮起來的豆子拼出 AI，下面倒數 05:00——一杯咖啡的時間，正在讀秒。',
 ai:'亮豆拼出 AI（尖頂 A、襯線 I），暗豆是未亮的點陣；文字標的 AI 也用咖啡豆點陣。',
 color:'亮豆由焦糖（上）到深焙（下）、暗豆淡淡一層；倒數字深可可等寬字。',
 type:'Inter Display SemiBold ＋ AI 為咖啡豆點陣（5×7）；讀秒用 JetBrains Mono。',
 tech:'點陣看板、等寬讀秒字，像車站的翻牌看板。',
 draw:(c,o)=>{const cell=o.small?19:15,x=100-4.5*cell,y=o.small?34:30;const dk=c.name==='light'?'#5E3A26':'#C0753F';
  return `${beanAI(x,y,cell,j=>lerp(c.ac,dk,j/6),o.small?null:c.ink)}${o.small?'':`<text x="100" y="${y+7*cell+34}" text-anchor="middle" font-family="JetBrains Mono" font-weight="700" font-size="22" letter-spacing="3" fill="${c.ink}">05:00</text>`}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{render:(c,S,x,base)=>{const capH=S*.727,cell=capH/7;return {w:9*cell,svg:beanAI(x,base-capH,cell,()=>c.ac,null,true)}},pre:.05,post:.06},{t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'dark'},

{id:'S6',dir:'S6_濾紙A',name:'濾紙 A',en:'Filter A',ratio:[65,35],
 meaning:'一張手沖濾紙，紙形就是 A、摺線是橫槓、封邊是細細的鋸齒——濾掉雜訊，只留下一杯乾淨的 AI 新知。',
 ai:'濾紙＝A（有鋸齒封邊與摺線），右邊一個焦糖襯線 I；文字標 AI 底下是一道濾紙鋸齒線。',
 color:'奶白濾紙、摺起的下半是淡奶茶色、深可可輪廓、焦糖 I。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08）。',
 tech:'「過濾」的資訊隱喻、精準的鋸齒封邊。',
 draw:(c,o)=>{const g=uid(),ink=c.ink,p=PAPER(c);let z='M84 22';const n=36;for(let i=1;i<=n;i++){const t=(i-.5*(i%2))/n,xx=84+(142-84)*t,yy=22+(168-22)*t;z+=` L${(xx+(i%2?2.4:0)).toFixed(1)} ${(yy-(i%2?.95:0)).toFixed(1)}`;}
  const shape=`${z} Q84 182 26 168 Z`;
  return `<defs><linearGradient id="${g}c" x1="0" y1="118" x2="0" y2="176" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.name==='light'?'#EAD3B4':'#E6CBA6'}"/><stop offset="1" stop-color="${c.name==='light'?'#D9B48A':'#D3A878'}"/></linearGradient><clipPath id="${g}k"><path d="${shape}"/></clipPath></defs>
  <path d="${shape}" fill="${p}"/>
  <rect x="10" y="120" width="150" height="70" fill="url(#${g}c)" clip-path="url(#${g}k)"/>
  <path d="M68 80 L84 52 L100 80 Z" fill="${c.bg}" stroke="${ink}" stroke-width="4" stroke-linejoin="round"/>
  <path d="${shape}" fill="none" stroke="${ink}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M44 120 H126" ${ST(ink,7)}/>
  ${serifI(170,62,106,c.ac,o.small?14:11,o.small?13:12)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.015,post:.025,
   over:(c,S,x,w,base)=>{const y=base+S*.13,a=S*.03,n=7,st=w/n;let d=`M${x.toFixed(1)} ${y.toFixed(1)}`;for(let i=0;i<n;i++)d+=` l${(st/2).toFixed(1)} ${(-a).toFixed(1)} l${(st/2).toFixed(1)} ${a.toFixed(1)}`;return `<path d="${d}" ${ST(c.ac,S*.028)}/>`}},{t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'light'},

{id:'S7',dir:'S7_咖啡滴引號',name:'咖啡滴引號',en:'Quoted Drop',ratio:[45,55],
 meaning:'引號是四滴咖啡，中間引用的是「AI」——每天替你引用一則 AI 新知，像一口剛滴好的咖啡。',
 ai:'整個圖形就是被引號框起來的大字 AI；文字標的 AI 前後也加上兩組咖啡滴引號。',
 color:'咖啡滴焦糖→深焙光澤漸層加小高光；AI 深可可（深底改奶油）。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）；引號為手繪咖啡滴。',
 tech:'排版符號（引號）當圖形，像編輯器裡的引用格式。',
 draw:(c,o)=>{const g=uid(),lt=c.name==='light';const gr=`url(#${g}d)`;const r=o.small?11:9;
  return `<defs><linearGradient id="${g}d" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${lt?'#D98544':'#F2B983'}"/><stop offset="1" stop-color="${lt?'#5E3A26':'#B0652F'}"/></linearGradient></defs>
  ${drop(34,58,r,28,gr)}${drop(58,58,r,28,gr)}${drop(142,52,r,208,gr)}${drop(166,52,r,208,gr)}
  ${textT(100,o.small?150:146,'AI','Inter Display',800,o.small?92:84,c.ink,`text-anchor="middle" style="font-feature-settings:'cv08' 1"`)}`},
 wm:{parts:[{render:(c,S,x,base)=>{const r=S*.07;return {w:S*.36,svg:`${drop(x+S*.09,base-S*.62,r,28,c.ac)}${drop(x+S*.26,base-S*.62,r,28,c.ac)}`}},post:.02},
  {t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.015,post:.025},{t:'ne',fam:'Inter Display',wt:600,post:.04},
  {render:(c,S,x,base)=>{const r=S*.07;return {w:S*.36,svg:`${drop(x+S*.09,base-S*.6,r,208,c.ac)}${drop(x+S*.26,base-S*.6,r,208,c.ac)}`}}}]},cupTheme:'dark'},

{id:'S8',dir:'S8_濾掛咖啡',name:'濾掛咖啡',en:'Drip Bag',ratio:[70,30],
 meaning:'上班族的濾掛咖啡：撕開、掛上杯緣、三分鐘——濾掛包上印的是 AI，泡好的是一則新知。',
 ai:'掛在杯緣的濾掛包正面印著焦糖色大字 AI；文字標的 AI 外框一個圓角標籤框（只描邊，不填色）。',
 color:'奶白濾掛包＋撕線虛線，深可可杯身，焦糖 AI。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08），焦糖描邊標籤框。',
 tech:'撕線虛線、精準的掛耳摺紙幾何。',
 draw:(c,o)=>{const ink=c.ink,p=PAPER(c),lt=c.name==='light';const ol=lt?`stroke="${ink}" stroke-opacity=".5" stroke-width="2.5" stroke-linejoin="round"`:'';
  return `<path d="M62 30 H138 V118 H62 Z" fill="${p}" ${ol}/>
  ${o.small?'':`<path d="M68 42 H132" stroke="${ink}" stroke-opacity=".45" stroke-width="2.2" stroke-dasharray="4 4"/>`}
  <path d="M62 66 L44 104 L52 104 L66 76 Z" fill="${p}" ${ol}/><path d="M138 66 L156 104 L148 104 L134 76 Z" fill="${p}" ${ol}/>
  ${letterA(86,54,40,c.ac,o.small?11:9,.33)}${serifI(116,54,40,c.ac,o.small?11:9,o.small?9:8)}
  <path d="M152 120 C182 116 184 158 146 158" ${ST(ink,11)}/>
  <path d="M38 102 H162 L152 178 Q151 188 141 188 H59 Q49 188 48 178 Z" fill="${ink}"/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.17,post:.17,
   under:(c,S,x,w,base,capH)=>`<rect x="${(x-S*.11).toFixed(1)}" y="${(base-capH-S*.11).toFixed(1)}" width="${(w+S*.22).toFixed(1)}" height="${(capH+S*.22).toFixed(1)}" rx="${(S*.07).toFixed(1)}" fill="none" stroke="${c.ac}" stroke-width="${(S*.035).toFixed(1)}"/>`},{t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'light'},
];

// ───────── 量字 ─────────
const NS='http://www.w3.org/2000/svg';let MS;
function meas(t,fam,wt,size,ls=0,feat=false){if(!MS){MS=document.createElementNS(NS,'svg');MS.setAttribute('width','2000');MS.setAttribute('height','400');MS.style.cssText='position:absolute;left:-3000px;top:0';document.body.appendChild(MS);}
 const e=document.createElementNS(NS,'text');e.setAttribute('font-family',fam);e.setAttribute('font-weight',wt);e.setAttribute('font-size',size);if(ls)e.setAttribute('letter-spacing',ls);if(feat)e.setAttribute('style',"font-feature-settings:'cv08' 1");e.textContent=t;MS.appendChild(e);const w=e.getComputedTextLength();e.remove();return w;}
const FEAT=` style="font-feature-settings:'cv08' 1"`;
// 文字標：回傳 {svg, w}；基線在 y=base（呼叫者給）
function wordmark(d,c,S,x0,base){const D=DIRS.find(q=>q.id===d);let x=x0,o='',defs='';const capH=S*.727;
 for(const p of D.wm.parts){x+=(p.pre||0)*S;
  if(p.render){const r=p.render(c,S,x,base);o+=r.svg;x+=r.w+(p.post||0)*S;continue;}
  if(p.kind==='pixel'){const cell=capH/7;const pw=9*cell;o+=pixAI(x,base-capH,cell,()=>c.ac,.05);x+=pw+(p.post||0)*S;continue;}
  const fs=S*(p.k||1),ls=(p.ls||0)*fs,w=meas(p.t,p.fam,p.wt,fs,ls,p.feat)-(p.ls?ls:0);
  let fill=p.fill==='ac'?c.ac:p.fill==='bg'?c.bg:c.ink;
  if(p.fill==='grad'){const g=uid();defs+=`<linearGradient id="${g}" x1="0" y1="0" x2="1" y2="0"><stop offset=".08" stop-color="${c.ac}"/><stop offset=".95" stop-color="${c.lavT}"/></linearGradient>`;fill=`url(#${g})`;}
  if(p.fill==='gloss'){const g=uid(),k=glossCols(c);defs+=`<linearGradient id="${g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${k[0]}"/><stop offset=".52" stop-color="${k[0]}"/><stop offset=".52" stop-color="${k[1]}"/><stop offset="1" stop-color="${k[1]}"/></linearGradient>`;fill=`url(#${g})`;}
  if(p.fill==='facet'){const g=uid(),k=facetCols(c);defs+=`<linearGradient id="${g}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${k[0]}"/><stop offset=".5" stop-color="${k[0]}"/><stop offset=".5" stop-color="${k[1]}"/><stop offset="1" stop-color="${k[1]}"/></linearGradient>`;fill=`url(#${g})`;}
  const T=(f,dx=0,dy=0)=>`<text x="${(x+dx).toFixed(1)}" y="${(base+dy).toFixed(1)}" font-family="${p.fam}" font-weight="${p.wt}" font-size="${fs.toFixed(1)}"${ls?` letter-spacing="${ls.toFixed(1)}"`:''}${p.italic?' font-style="italic"':''} fill="${f}"${p.feat?FEAT:''}>${p.t}</text>`;
  if(p.under)o+=p.under(c,S,x,w,base,capH,T);
  if(p.pill){const px=S*.15,py=S*.13;o+=`<rect x="${(x-px).toFixed(1)}" y="${(base-capH-py).toFixed(1)}" width="${(w+2*px).toFixed(1)}" height="${(capH+2*py).toFixed(1)}" rx="${((capH+2*py)/2).toFixed(1)}" fill="${c.ac}"/>`;}
  o+=`<text x="${x.toFixed(1)}" y="${base.toFixed(1)}" font-family="${p.fam}" font-weight="${p.wt}" font-size="${fs.toFixed(1)}"${ls?` letter-spacing="${ls.toFixed(1)}"`:''} ${p.italic?' font-style="italic"':''} fill="${fill}"${p.feat?FEAT:''}>${p.t}</text>`;
  if(p.over)o+=p.over(c,S,x,w,base,capH,T);
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

function storyboard(th){const c=TH[th],W=1260,H=560;const cap=[['① 熱氣升起','0～0.6 秒'],['② 熱氣拉直','0.6～1.0 秒'],['③ 停成游標','之後每 0.5 秒閃一下']];
 let o=`<rect class="bgx" width="${W}" height="${H}" fill="${c.bg}"/>`;
 [0,1,2].forEach(i=>{const x=60+i*400;o+=`<g data-el="f${i}" transform="translate(${x} 50) scale(1.6)">${mark('Q6',c,{frame:i})}</g>`;
  if(i===2)o+=`<g transform="translate(${x} 50) scale(1.6)" opacity=".18"><rect x="110" y="10" width="13" height="50" rx="3.5" fill="${c.ac}"/></g>`;
  o+=`<g data-el="c${i}"><text x="${x+160}" y="${H-74}" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="28" fill="${c.ink}">${cap[i][0]}</text><text x="${x+160}" y="${H-36}" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="21" fill="${c.ink}" fill-opacity=".65">${cap[i][1]}</text></g>`;
  if(i<2)o+=`<path d="M${x+372} 210 h28 m-10 -10 l10 10 l-10 10" fill="none" stroke="${c.ac}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`;});
 return svgW(W,H,o);}
window.CF={TH,storyboard,DIRS:DIRS.map(({draw,wm,...r})=>r),icon,avatar,lockup,igProfile,cupMock,postCover};
})();
