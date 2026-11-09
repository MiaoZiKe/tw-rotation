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
const IS=s=>`fill="none" stroke="${s}"`;
function stainArc(cx,cy,R,w,t0,t1,sd){const pts=[],inn=[];const N=s=>Math.sin(3*s+sd)*1.1+Math.sin(7*s+2*sd)*.45+Math.sin(13*s+sd*3)*.2;
 for(let t=t0;t<=t1+.01;t+=2){const a=t*Math.PI/180,tf=Math.min(1,(t-t0)/30,(t1-t)/30);const r=R+N(a),hw=w*Math.max(tf,0.05)/2;
  pts.push([cx+(r+hw)*Math.cos(a),cy+(r+hw)*Math.sin(a)]);inn.push([cx+(r-hw)*Math.cos(a),cy+(r-hw)*Math.sin(a)]);}
 const all=pts.concat(inn.reverse());return 'M'+all.map(p=>p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' L')+' Z';}
const textT=(x,y,t,fam,wt,size,fill,extra='')=>`<text x="${x}" y="${y}" font-family="${fam}" font-weight="${wt}" font-size="${size}" fill="${fill}" ${extra}>${t}</text>`;
const serifI=(x,y,h,col,w,hw)=>`<path d="M${x-hw} ${y} H${x+hw} M${x} ${y} V${y+h} M${x-hw} ${y+h} H${x+hw}" ${ST(col,w)}/>`;
const glossCols=c=>c.name==='light'?['#D27236','#A14E1E']:['#F8BE8A','#E07A3A'];
const facetCols=c=>c.name==='light'?['#D98544','#B0561F']:['#F8BE8A','#E8894A'];
const q6steam=(c,f,g)=>{if(f===0)return `<path d="M104 86 C96 72 120 64 112 48 S120 24 112 10" ${ST(`url(#${g}s)`,8)}/>`;
 if(f===1)return `<path d="M104 86 C96 72 120 66 116 52 C115 40 116 26 116 12" ${ST(`url(#${g}s)`,9)}/>`;
 return `<path d="M104 86 C96 74 118 68 116 58" ${ST(`url(#${g}s)`,8)}/><rect x="110" y="10" width="13" height="50" rx="3.5" fill="${c.ac}"/>${f===3?'':`<rect x="112.2" y="13" width="2.4" height="38" rx="1.2" fill="#FFFFFF" opacity=".4"/>`}`;};
const DIRS=[
{id:'Q1',dir:'Q1_杯漬',name:'杯漬筆記',en:'Coffee Ring',ratio:[75,25],
 meaning:'杯子放下又拿起，桌上留下兩圈沒畫完的咖啡漬——今天留下的，是一則 AI 筆記。',
 ai:'漬痕中央是一個大大的襯線 AI（Charter Bold，深可可），文字標的 AI 底下襯一塊淡淡的焦糖漬。',
 color:'焦糖漬分兩層：外緣較深、內側淡淡的水洗；濺點也是焦糖；AI 用深可可。',
 type:'Inter Display Medium ＋ AI 用 Bitstream Charter Bold。',
 tech:'精準的襯線字和隨機但可控的程式化漬痕邊緣（每一圈都是演算出來的不規則曲線）。',
 draw:(c,o)=>{const A=stainArc(96,104,68,o.small?12:8,62,300,1.3),B=stainArc(146,62,32,o.small?8:5,130,290,2.2),W=stainArc(96,104,61,9,62,300,1.3);
  return `<circle cx="96" cy="104" r="64" fill="${c.ac}" opacity=".07"/>
  <path d="${W}" fill="${c.ac}" opacity=".18"/><path d="${A}" fill="${c.ac}" opacity=".88"/><path d="${B}" fill="${c.ac}" opacity=".6"/>
  ${o.small?'':`<circle cx="172" cy="122" r="4.2" fill="${c.ac}" opacity=".8"/><circle cx="182" cy="110" r="2.2" fill="${c.ac}" opacity=".7"/><circle cx="166" cy="142" r="2" fill="${c.ac}" opacity=".6"/><circle cx="30" cy="54" r="3" fill="${c.ac}" opacity=".6"/>`}
  ${textT(96,o.small?132:128,'AI','Bitstream Charter',700,o.small?76:64,c.ink,'text-anchor="middle"')}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Bitstream Charter',wt:700,fill:'ac',k:1.05,pre:.03,post:.04,
   under:(c,S,x,w,base,capH)=>`<path d="${stainArc(0,0,1,0,0,0,0).slice(0,0)}M${(x-S*.08).toFixed(1)} ${(base-capH*.5).toFixed(1)} C${(x-S*.08).toFixed(1)} ${(base-capH*1.05).toFixed(1)} ${(x+w+S*.1).toFixed(1)} ${(base-capH*1.12).toFixed(1)} ${(x+w+S*.08).toFixed(1)} ${(base-capH*.45).toFixed(1)} C${(x+w+S*.06).toFixed(1)} ${(base+S*.06).toFixed(1)} ${(x-S*.06).toFixed(1)} ${(base+S*.1).toFixed(1)} ${(x-S*.08).toFixed(1)} ${(base-capH*.5).toFixed(1)} Z" fill="${c.ac}" opacity=".16"/>`},
  {t:'ne',fam:'Inter Display',wt:500}]},cupTheme:'light'},

{id:'Q2',dir:'Q2_一筆拉花',name:'一筆拉花',en:'Latte Line',ratio:[70,30],
 meaning:'咖啡師一筆拉出 A，最後「拉穿」的那一刀就是 I——新知像拉花，一杯一杯手作端給你。',
 ai:'A 是一筆連續的奶泡線加一道奶泡弧橫槓，I 是加粗、上下帶短橫的拉穿線；文字標 AI 下方加一道奶泡波浪線。',
 color:'咖啡面用焦糖由中心往外加深的放射漸層；奶泡奶白；杯耳深可可。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08 襯線 I）焦糖。',
 tech:'一筆連續的向量路徑（像繪圖機器手臂畫出的線）、精準的放射漸層。',
 draw:(c,o)=>{const g=uid(),milk='#FFF6E8',sw=o.small?13:9.5;const P='M42 146 L77 52 L112 146',CB='M55 114 Q77 103 100 114',PI='M127.5 54 L140.5 54 L138.6 146 L129.4 146 Z';
  return `<defs><radialGradient id="${g}r" cx=".46" cy=".44" r=".62"><stop offset="0" stop-color="${c.name==='light'?'#C77B45':'#D98E57'}"/><stop offset=".7" stop-color="${c.name==='light'?'#8E5330':'#A35F33'}"/><stop offset="1" stop-color="${c.name==='light'?'#5A321D':'#6E3C20'}"/></radialGradient></defs>
  <path d="${o.small?'M162 86 H180 Q194 86 194 100 V108 Q194 122 180 122 H162 Z':'M164 90 H178 Q190 90 190 102 V106 Q190 118 178 118 H164 Z'}" fill="${c.ink}"/>
  <circle cx="96" cy="104" r="76" fill="url(#${g}r)"/>
  <path d="${P}" ${ST(milk,sw)}/><path d="${CB}" ${ST(milk,sw*.85)}/>
  <path d="${PI}" fill="${milk}" stroke="${milk}" stroke-width="${o.small?4:1}" stroke-linejoin="round"/>
  <path d="M124 52 H144 M126 148 H142" ${ST(milk,sw*.85)}/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.015,post:.025,
   over:(c,S,x,w,base)=>{const y=base+S*.14,a=S*.035;let d=`M${x.toFixed(1)} ${y.toFixed(1)}`;const n=3,st=w/n;for(let i=0;i<n;i++)d+=` q${(st/4).toFixed(1)} ${(-a*2).toFixed(1)} ${(st/2).toFixed(1)} 0 t${(st/2).toFixed(1)} 0`;return `<path d="${d}" ${ST(c.ac,S*.04)}/>`}},
  {t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'dark'},

{id:'Q3',dir:'Q3_字母即杯',name:'字母即杯',en:'Letterform Brew',ratio:[55,45],
 meaning:'名字本身就是一杯咖啡：ff 是兩縷往上冒的熱氣、e 是俯看的杯口、AI 是從杯裡升起的那口香氣。',
 ai:'圖形是一只杯子裡升起的 AI，字腳藏在杯裡、字頂化成蒸氣；文字標的 AI 用焦糖→薰衣草漸層 ExtraBold，ff 與 e 是手刻字形。',
 color:'深可可字與杯、AI 焦糖→薰衣草漸層，e 的上半杯口填焦糖（咖啡面）。',
 type:'Inter Display SemiBold ＋ 手刻 ff（蒸氣）與 e（杯口），AI 為 Inter Display ExtraBold（cv08）。',
 tech:'字體工程式的手刻字形、漸層。',
 draw:(c,o)=>{const g=uid();return `<defs><linearGradient id="${g}g" x1="0" y1="140" x2="0" y2="16" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.ac}"/><stop offset=".55" stop-color="${c.ac}"/><stop offset="1" stop-color="${c.lav}"/></linearGradient></defs>
  <path d="M64 150 L88 46 L112 150 M73 104 H103 M132 150 V46" ${ST(`url(#${g}g)`,14)}/>
  <path d="M88 44 C88 34 97 30 93 20 S95 8 100 3 M132 44 C132 34 123 30 127 20 S125 8 120 3" ${ST(`url(#${g}g)`,o.small?0:6)}/>
  <path d="M158 128 C186 124 188 162 152 162" ${ST(c.ink,11)}/>
  <path d="M34 124 H166 C166 160 138 182 100 182 C62 182 34 160 34 124 Z" fill="${c.ink}"/>
  <rect x="34" y="124" width="132" height="8" fill="${c.ac}" opacity=".9"/>`},
 wm:{parts:[{t:'Ca',fam:'Inter Display',wt:600},
  {render:(c,S,x,base)=>{const sw=S*.1,x1=x+S*.12,x2=x+S*.43,g=uid();const st=X=>`M${X.toFixed(1)} ${base.toFixed(1)} V${(base-S*.5).toFixed(1)} C${X.toFixed(1)} ${(base-S*.66).toFixed(1)} ${(X+S*.13).toFixed(1)} ${(base-S*.66).toFixed(1)} ${(X+S*.11).toFixed(1)} ${(base-S*.82).toFixed(1)} S${(X+S*.02).toFixed(1)} ${(base-S*.96).toFixed(1)} ${(X+S*.08).toFixed(1)} ${(base-S*1.04).toFixed(1)}`;
    return {w:S*.62,svg:`<defs><linearGradient id="${g}" x1="0" y1="${base}" x2="0" y2="${base-S*1.05}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.ink}"/><stop offset=".5" stop-color="${c.ink}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient></defs><path d="${st(x1)} ${st(x2)} M${(x+S*.01).toFixed(1)} ${(base-S*.5).toFixed(1)} H${(x+S*.6).toFixed(1)}" fill="none" stroke="url(#${g})" stroke-width="${sw.toFixed(1)}" stroke-linecap="round" stroke-linejoin="round"/>`}},pre:.0,post:.03},
  {t:'AI',fam:'Inter Display',wt:800,fill:'grad',feat:true,pre:0,post:.025},
  {t:'n',fam:'Inter Display',wt:600,post:.03},
  {render:(c,S,x,base)=>{const r=S*.245,sw=S*.095,cx=x+r+sw/2,cy=base-S*.27;const a=40*Math.PI/180,ex=cx+r*Math.cos(a),ey=cy+r*Math.sin(a);
    return {w:2*r+sw,svg:`<path d="M${(cx-r+sw*.4).toFixed(1)} ${cy.toFixed(1)} A${(r-sw*.4).toFixed(1)} ${(r-sw*.4).toFixed(1)} 0 0 1 ${(cx+r-sw*.4).toFixed(1)} ${cy.toFixed(1)} Z" fill="${c.ac}"/><path d="M${(cx-r).toFixed(1)} ${cy.toFixed(1)} H${(cx+r).toFixed(1)} A${r.toFixed(1)} ${r.toFixed(1)} 0 1 0 ${ex.toFixed(1)} ${ey.toFixed(1)}" fill="none" stroke="${c.ink}" stroke-width="${sw.toFixed(1)}" stroke-linecap="round"/>`}}}]},
 cupTheme:'light'},

{id:'Q4',dir:'Q4_等角方糖',name:'等角方糖',en:'Iso Sugar Cube',ratio:[50,50],
 meaning:'AI 新知是一顆方糖：左面 A、右面 I，正落進咖啡杯裡——一杯咖啡的時間，就化開了。',
 ai:'2.5D 等角方塊的兩個側面各刻一個字母，合起來是 AI；文字標的 AI 有同角度的立體厚度。',
 color:'方糖奶白三階明暗＋頂邊高光；字母焦糖；杯子深可可、液面焦糖到深焙。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08）加等角立體厚度。',
 tech:'等角投影（30°）、精準的三面明暗、立體字。',
 draw:(c,o)=>{const g=uid(),k=46.8,h=27,e=54,T=16;const top='#FFFBF4',L='#F1E2CC',R='#DCC3A2',lc=c.name==='light'?'#B85A22':'#C2652B';
  const geoA=(col,w)=>`<path d="M12 44 L27 9 L42 44 M17.5 32 H36.5" fill="none" stroke="${col}" stroke-width="${w}" stroke-linejoin="miter" stroke-linecap="butt"/>`;
  const geoI=(col,w)=>`<path d="M27 9 V44 M18 9 H36 M18 44 H36" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="butt"/>`;
  const cubeY=T,ol=c.name==='light'?`stroke="#2B1D16" stroke-opacity=".28" stroke-width="2"`:'';
  return `<defs><linearGradient id="${g}c" x1="0" y1="118" x2="0" y2="190" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.name==='light'?'#2B1D16':'#1C130F'}"/><stop offset="1" stop-color="${c.name==='light'?'#2B1D16':'#1C130F'}"/></linearGradient>
  <radialGradient id="${g}s" cx=".5" cy=".5" r=".6"><stop offset="0" stop-color="#9A5A30"/><stop offset="1" stop-color="#5A321D"/></radialGradient></defs>
  <path d="M162 132 C190 130 192 168 156 168" ${ST(c.name==='light'?'#2B1D16':'#F6EEE3',10)}/>
  <path d="M26 122 C26 170 60 192 100 192 C140 192 174 170 174 122 Z" fill="${c.name==='light'?'#2B1D16':'#F6EEE3'}"/>
  <ellipse cx="100" cy="122" rx="74" ry="15" fill="url(#${g}s)"/>
  <g>
  <path d="M100 ${T} L${100+k} ${T+h} L100 ${T+2*h} L${100-k} ${T+h} Z" fill="${top}" ${ol} stroke-linejoin="round"/>
  <path d="M${100-k} ${T+h} L100 ${T+2*h} L100 ${T+2*h+e} L${100-k} ${T+h+e} Z" fill="${L}" ${ol} stroke-linejoin="round"/>
  <path d="M100 ${T+2*h} L${100+k} ${T+h} L${100+k} ${T+h+e} L100 ${T+2*h+e} Z" fill="${R}" ${ol} stroke-linejoin="round"/>
  <path d="M${100-k+3} ${T+h} L100 ${T+3} L${100+k-3} ${T+h}" fill="none" stroke="#FFFFFF" stroke-width="2.2" opacity=".9" stroke-linecap="round"/>
  <g transform="matrix(0.866 0.5 0 1 ${100-k} ${T+h})">${geoA(lc,o.small?8.5:6.8)}</g>
  <g transform="matrix(0.866 -0.5 0 1 100 ${T+2*h})">${geoI(lc,o.small?8.5:6.8)}</g></g>
  <path d="M26 122 A74 15 0 0 0 174 122 L174 124 A74 15 0 0 1 26 124 Z" fill="#5A321D"/>
    <path d="M28 124 A72 14 0 0 0 172 124 A72 7 0 0 0 28 124 Z" fill="url(#${g}s)"/>
  ${o.small?'':`<path d="M40 122 Q52 117 64 120 M140 120 Q150 116 162 121" ${ST('#D98E57',2.4)} opacity=".9"/>`}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'ac',feat:true,pre:.015,post:.06,
   under:(c,S,x,w,base,capH,T)=>[5,4,3,2,1].map(i=>T(c.name==='light'?'#6E3A1E':'#9A5A30',i*S*.011,i*S*.008)).join('')},
  {t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'light'},

{id:'Q5',dir:'Q5_玻璃倒影',name:'玻璃倒影',en:'Glass Reflection',ratio:[55,45],
 meaning:'一只透明玻璃杯，咖啡液面映出 AI 的倒影——把 AI 講得像玻璃一樣透明、一眼看穿。',
 ai:'液面上方是正立的 AI（焦糖→薰衣草漸層），液面下是它淡淡的倒影；文字標的 AI 用上亮下深的玻璃光澤分色。',
 color:'玻璃磨砂白＋柔和焦糖與薰衣草光暈（模糊色塊），咖啡焦糖到深焙。',
 type:'Inter Display Medium ＋ AI 用 Inter Display ExtraBold（cv08）光澤分色。',
 tech:'玻璃擬態：磨砂透明、背景光暈、鏡面倒影。',
 draw:(c,o)=>{const g=uid(),glass='M56 34 H144 L138 168 Q137 182 123 182 H77 Q63 182 62 168 Z';const lt=c.name==='light';
  const AIu=(col,w)=>`${letterA(84,46,44,col,w,.36)}${serifI(118,46,44,col,w,8)}`;
  return `<defs><filter id="${g}f" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="14"/></filter><filter id="${g}f2" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="6"/></filter>
  <clipPath id="${g}k"><path d="${glass}"/></clipPath>
  <linearGradient id="${g}c" x1="0" y1="104" x2="0" y2="182" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.ac}"/><stop offset="1" stop-color="${lt?'#5A321D':'#8A4A26'}"/></linearGradient>
  <linearGradient id="${g}a" x1="0" y1="90" x2="0" y2="46" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.ac}"/><stop offset="1" stop-color="${c.lavT}"/></linearGradient></defs>
  <g filter="url(#${g}f)" opacity="${lt?.55:.6}"><circle cx="58" cy="62" r="34" fill="${c.ac}"/><circle cx="150" cy="150" r="30" fill="${c.lav}"/></g>
  <g clip-path="url(#${g}k)"><rect x="40" y="20" width="120" height="170" fill="${lt?'#FFFFFF':'#FFF7EA'}" opacity="${lt?.55:.1}"/>
   <rect x="40" y="104" width="120" height="90" fill="url(#${g}c)"/><ellipse cx="100" cy="104" rx="44" ry="6" fill="${c.acHi}"/>
   <g transform="translate(0 208) scale(1 -1)" opacity=".38" filter="url(#${g}f2)">${AIu('#FFF7EA',9)}</g>
   <g transform="translate(0 208) scale(1 -1)" opacity=".42">${AIu('#FFF7EA',6)}</g>
   <path d="M68 44 L72 160" ${ST('#FFFFFF',4)} opacity=".6"/></g>
  ${AIu(`url(#${g}a)`,o.small?12:10)}
  <path d="${glass}" fill="none" stroke="${lt?c.ink:'#FFF7EA'}" stroke-opacity="${lt?.55:.7}" stroke-width="3" stroke-linejoin="round"/>`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:500},{t:'AI',fam:'Inter Display',wt:800,fill:'gloss',feat:true,pre:.015,post:.025},{t:'ne',fam:'Inter Display',wt:500}]},cupTheme:'dark'},

{id:'Q6',dir:'Q6_蒸氣游標',name:'蒸氣游標',en:'Steam to Cursor',ratio:[50,50],
 meaning:'馬克杯升起一縷熱氣，飄到一半停下來，變成一根閃爍的游標——咖啡在等你，AI 也在等你輸入。',
 ai:'杯身留白一個 A，熱氣變成的游標就是 I；文字標也是「A＋焦糖游標」，動起來時游標會閃。',
 color:'深可可杯身、焦糖熱氣與游標（游標帶一道內光）。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold 的 A＋手繪游標 I。',
 tech:'動態識別：蒸氣→拉直→游標閃爍（見 storyboard.png 三格分鏡）。',
 draw:(c,o)=>{const g=uid(),f=o.frame==null?2:o.frame;
  return `<defs><linearGradient id="${g}s" x1="0" y1="90" x2="0" y2="10" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.mid}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient></defs>
  ${o.small?`<rect x="108" y="16" width="16" height="58" rx="4" fill="${c.ac}"/>`:`<path d="M66 84 C60 74 74 68 68 58" ${ST(c.mid,6)} opacity=".7"/>${q6steam(c,f,g)}`}
  <path d="M150 106 H160 Q180 106 180 126 Q180 146 160 146 H150" ${ST(c.ink,12)}/>
  <path d="M40 94 H152 V138 Q152 178 112 178 H80 Q40 178 40 138 Z" fill="${c.ink}"/>
  ${letterA(96,108,54,c.bg,12.5,.37)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},
  {render:(c,S,x,base)=>{const wA=meas('A','Inter Display',800,S);const capH=S*.727,cw=S*.2;return {w:wA+S*.07+cw,svg:`<text x="${x.toFixed(1)}" y="${base.toFixed(1)}" font-family="Inter Display" font-weight="800" font-size="${S}" fill="${c.ac}">A</text><rect x="${(x+wA+S*.07).toFixed(1)}" y="${(base-capH-S*.04).toFixed(1)}" width="${cw.toFixed(1)}" height="${(capH+S*.08).toFixed(1)}" rx="${(S*.025).toFixed(1)}" fill="${c.ac}"/>`}},pre:.02,post:.06},
  {t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'dark'},

{id:'Q7',dir:'Q7_復古未來徽章',name:'復古未來徽章',en:'Retro-Future Arch',ratio:[60,40],
 meaning:'老咖啡館的單拱招牌裡升起一顆掃描線夕陽，夕陽中切出一只杯子——復古的溫度，配上未來的 AI。',
 ai:'拱門下方是大大的襯線斜體 AI；文字標全大寫，AI 換焦糖色 Charter 粗斜體。',
 color:'深可可單拱（深底改奶油）、雙線框焦糖；夕陽焦糖光→焦糖，切出掃描線與杯形缺口；40px 只留拱門、夕陽、放大的 AI。',
 type:'Inter Display Bold 全大寫字距 8% ＋ AI 用 Bitstream Charter Bold Italic；小字 JetBrains Mono。',
 tech:'合成波（synthwave）夕陽掃描線、等寬小字 EST.2026；拱門不是圓形徽章。',
 draw:(c,o)=>{const g=uid(),lt=c.name==='light',fill=lt?'#2B1D16':'#F6EEE3',fg=lt?'#F6EEE3':'#2B1D16';const arch=(i)=>`M${44+i} 188 V${92} A${56-i} ${56-i} 0 0 1 ${156-i} 92 V188 Z`;
  if(o.small)return `<defs><linearGradient id="${g}s" x1="0" y1="64" x2="0" y2="104" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.acHi}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient><clipPath id="${g}k"><rect x="40" y="50" width="120" height="54"/></clipPath></defs>
  <path d="${arch(0)}" fill="${fill}"/><g clip-path="url(#${g}k)"><circle cx="100" cy="104" r="36" fill="url(#${g}s)"/></g>
  ${textT(100,174,'AI','Bitstream Charter',700,70,fg,'font-style="italic" text-anchor="middle"')}`;
  return `<defs><linearGradient id="${g}s" x1="0" y1="74" x2="0" y2="118" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.acHi}"/><stop offset="1" stop-color="${c.ac}"/></linearGradient><clipPath id="${g}k"><rect x="40" y="60" width="120" height="58"/></clipPath>
  <mask id="${g}m"><rect x="0" y="0" width="200" height="200" fill="#fff"/><path d="M88 96 H112 L109.5 118 H90.5 Z" fill="#000"/><path d="M112 101 Q120 101 120 107.5 Q120 114 111 114" fill="none" stroke="#000" stroke-width="3.6"/><rect x="56" y="104" width="88" height="2.4" fill="#000"/><rect x="56" y="110" width="88" height="3.4" fill="#000"/></mask></defs>
  <path d="${arch(0)}" fill="${fill}"/><path d="${arch(7)}" fill="none" stroke="${c.ac}" stroke-width="2" opacity=".9"/>
  <g clip-path="url(#${g}k)"><circle cx="100" cy="118" r="40" fill="url(#${g}s)" mask="url(#${g}m)"/></g>
  <path d="M56 118.5 H144" stroke="${c.ac}" stroke-width="2"/>
  <text x="100" y="66" text-anchor="middle" font-family="JetBrains Mono" font-weight="700" font-size="9" letter-spacing="1.5" fill="${fg}" opacity=".75">EST·2026</text>
  ${textT(100,168,'AI','Bitstream Charter',700,48,fg,'font-style="italic" text-anchor="middle"')}`},
 wm:{parts:[{t:'CAFF',fam:'Inter Display',wt:700,ls:.08},{t:'AI',fam:'Bitstream Charter',wt:700,fill:'ac',k:1.05,italic:true,pre:.06,post:.08},{t:'NE',fam:'Inter Display',wt:700,ls:.08}]},cupTheme:'light'},

{id:'Q8',dir:'Q8_摺紙切面杯',name:'摺紙切面杯',en:'Faceted Cup',ratio:[55,45],
 meaning:'一只用紙摺出來的外帶杯，每個切面都是一段整理過的資訊，正面最亮的那一面，露出 AI。',
 ai:'杯身正面最亮的切面上是深可可 AI；文字標的 AI 用斜切分色（亮面／暗面），像摺紙的一道摺痕。',
 color:'焦糖到深焙的五階切面、正面奶油紙色兩階；蒸氣是一條摺紙緞帶。',
 type:'Inter Display SemiBold ＋ AI 用 Inter Display ExtraBold（cv08）斜切雙色。',
 tech:'低多邊形切面（low-poly）、精準的光影計算、摺紙幾何。',
 draw:(c,o)=>{const lt=c.name==='light';const P=lt?['#3A261C','#5E3A26','#8A5A3C','#B4713F','#D98A50','#E8A066']:['#6E3F24','#8A4F2C','#B06A3A','#D3864C','#EB9C60','#F8BE8A'];const pa=lt?['#FFF6EA','#F1DFC8']:['#FFF7EA','#EBD8BE'];
  const poly=(pts,f)=>`<path d="M${pts.join(' L')} Z" fill="${f}" stroke="${f}" stroke-width="1" stroke-linejoin="round"/>`;
  return `${''}
  ${poly(['64 50','136 50','140 60','60 60'],P[1])}${poly(['64 50','100 50','100 60','60 60'],P[2])}
  ${poly(['50 60','150 60','150 72','50 72'],P[0])}${poly(['50 60','100 60','100 72','50 72'],P[1])}
  ${poly(['56 74','72 74','82 184','72 184'],P[3])}${poly(['56 74','72 184','66 184'],P[2])}
  ${poly(['72 74','128 74','82 184'],pa[0])}${poly(['128 74','118 184','82 184'],pa[1])}
  ${poly(['128 74','144 74','134 184','118 184'],P[1])}${poly(['144 74','134 184','128 184'],P[0])}
  ${letterA(92,90,40,'#2B1D16',8,.26)}${serifI(113,90,40,'#2B1D16',8,5)}`},
 wm:{parts:[{t:'Caff',fam:'Inter Display',wt:600},{t:'AI',fam:'Inter Display',wt:800,fill:'facet',feat:true,pre:.015,post:.025},{t:'ne',fam:'Inter Display',wt:600}]},cupTheme:'light'},
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
