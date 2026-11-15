// 談晴說礙 數據短影音執行期 v3（2026-11-15）
// 依據：Andy 看完 v2：「影片素材需要再豐富點」「動畫、效果等等需要優化」＋ docs/marketing/channels/video_logic.md
// 每鏡兩層：量身情境插圖（illus）＋資料圖（chart）；背景三層（紙紋、淡格線、光影）緩慢視差，不留大片單色空白。
// 動畫規則：
//  - 進場一律 ease-out：cubic-bezier(.2,.8,.2,1)；標籤蓋章、數字落定用輕微過衝（back）
//  - 數字：加速減速計數（ease-in-out），停住那一格做一次 1→1.08→1 的確認放大
//  - 圖表：先後節奏 stagger 60–120ms；長條長完才出數值標籤
//  - 鏡頭：每鏡內容緩慢推近 1.04 倍＋小平移；轉場＝遮罩擦除（帶晴光橘前緣）、圓形展開、圖形延伸；
//          s1→s2 大數字「−29.4%」飛到下一鏡角落（共用元素變形）；s2→s3 同一張圖延續
//  - 強調（光暈／手繪劃線／圈選）每鏡最多一個
//  - 字幕、出處：先出後進、各自緩動，不同時疊在一起；renderAt(t) 只跟 t 有關、可重現
//  - 片尾：雲描出→太陽升起→三道光→「談晴說礙」一字一字寫上→太陽呼吸（音效在 window.sfxEvents）
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
function bez(x1,y1,x2,y2){const cx=3*x1,bx=3*(x2-x1)-cx,ax=1-cx-bx,cy=3*y1,by=3*(y2-y1)-cy,ay=1-cy-by;
 const X=t=>((ax*t+bx)*t+cx)*t,Y=t=>((ay*t+by)*t+cy)*t,DX=t=>(3*ax*t+2*bx)*t+cx;
 return x=>{x=clamp(x);if(x<=0)return 0;if(x>=1)return 1;let t=x;for(let i=0;i<8;i++){const d=DX(t);if(Math.abs(d)<1e-6)break;t-=(X(t)-x)/d;t=clamp(t)}return Y(t)}}
const EO=bez(.2,.8,.2,1);                                   // 標準進場
const BACK=x=>{x=clamp(x);const c1=1.3,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2)};   // 輕微過衝
const INOUT=x=>{x=clamp(x);return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2};
const pr=(lt,a,d,f)=>(f||EO)((lt-a)/d);
const settle=(lt,a)=>{const k=(lt-a)/.32;return k<=0||k>=1?1:1+.08*Math.sin(Math.PI*k)};   // 數字停住後確認放大一次
const fmtInt=n=>Math.round(n).toLocaleString('en-US');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LAMP='var(--lamp)',LINE='var(--line)',FACE='var(--face)',FACE3='var(--face3)',TXT='var(--text)',SUBC='var(--sub)',DARK='var(--dark)',HINT='var(--hint)';
const NIGHT='#5E5A57',NIGHT2='#4C4946',WARM='#F3DDB8';     // 夜景用暖灰（晝版線色加深，不用冷藍）
const TR=.42;                                               // 轉場長度（秒）
function T(x,y,s,fs,w,col,anchor,extra){return `<text x="${x}" y="${y}" text-anchor="${anchor||'middle'}" font-size="${fs}" font-weight="${w||400}" fill="${col||SUBC}" font-family="Noto Sans CJK TC" ${extra||''}>${esc(s)}</text>`}
const draw=(p)=>`pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="${(1-clamp(p)).toFixed(4)}"${p<=.002?' stroke-opacity="0"':''}`;   // 手繪描線
// 鏡頭：內容在框內緩慢推近 1.04 倍＋小平移（框本身不動，重疊檢查量的是框）
function cam(lt,dur,W,H,o){o=o||{};const k=INOUT(clamp(lt/Math.max(dur,.1))),z=1+(o.z==null?.04:o.z)*k,px=(o.px||0)*k,py=(o.py||0)*k;
 return `translate(${W/2+px},${H/2+py}) scale(${z.toFixed(4)}) translate(${-W/2},${-H/2})`}
function box(o,top,h,inner,lt,dur,co){return `<div data-o="${o}" class="abs" style="left:96px;top:${top}px;width:888px;height:${h}px"><svg width="888" height="${h}" viewBox="0 0 888 ${h}" overflow="hidden"><g transform="${cam(lt,dur,888,h,co)}">${inner}</g></svg></div>`}
function title(lines,lt,o){o=o||{};const fs=o.fs||92,top=o.top||170,p=o.full?1:pr(lt,.02,.38);
 return `<div data-o="title" class="abs title ${o.cls||''}" style="top:${top}px;font-size:${fs}px;line-height:${Math.round(fs*1.24)}px;opacity:${.35+.65*p};transform:translateY(${(1-p)*22}px)">${lines.map(esc).join('<br>')}</div>`}
// 狀態標籤：蓋章（1.3→1 過衝回彈、微旋轉）
function tag(s,lt,at,top){if(!s)return'';const k=clamp((lt-at)/.3);if(k<=0)return'';const sc=1.3-.3*BACK(k),rot=-4*(1-EO(k));
 return `<div data-o="tag" class="abs tag" style="top:${top}px;transform:scale(${sc.toFixed(3)}) rotate(${rot.toFixed(2)}deg);transform-origin:left center;opacity:${clamp(k*3)}">${esc(s)}</div>`}
function split2(s){const m=s.length/2;let best=-1,bd=1e9;for(let i=1;i<s.length-1;i++){if(/[，、：；？！]/.test(s[i])){const d=Math.abs(i+1-m);if(d<bd&&i+1<=16&&s.length-i-1<=16){bd=d;best=i+1}}}
 if(best<0||Math.min(best,s.length-best)<s.length/3)best=Math.ceil(m);return [s.slice(0,best),s.slice(best)]}
function capHTML(s,op,dy){if(!s||op<=0)return'';s=s.replace(/。$/,'');const one=s.length<=11;const ls=one?[s]:split2(s);const mx=Math.max(...ls.map(l=>l.length));const fs=one?76:(mx<=13?64:Math.min(64,Math.floor(880/mx)));
 const lh=Math.round(fs*1.28),h=ls.length*lh,top=1690-h;
 return `<div data-o="cap" class="abs cap" style="top:${top}px;font-size:${fs}px;line-height:${lh}px;opacity:${op.toFixed(3)};transform:translateY(${dy.toFixed(1)}px)">${ls.map(esc).join('<br>')}</div>`}
function srcHTML(s,op){return op<=0?'':`<div data-o="src" class="abs src" style="opacity:${op.toFixed(3)}">${esc(s)}</div>`}
const glow=(cx,cy,r,a)=>`<circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#gl)" opacity="${a.toFixed(3)}"/>`;
const DEFS=`<defs><radialGradient id="gl"><stop offset="0" stop-color="#F2B66B" stop-opacity=".85"/><stop offset=".55" stop-color="#F2B66B" stop-opacity=".25"/><stop offset="1" stop-color="#F2B66B" stop-opacity="0"/></radialGradient>
<radialGradient id="glw"><stop offset="0" stop-color="#FFE9B8" stop-opacity=".95"/><stop offset="1" stop-color="#FFE9B8" stop-opacity="0"/></radialGradient></defs>`;
// 手繪圈：不正圓、多繞 8%，有手感
function wobbleRing(cx,cy,rx,ry,p,seed){let d='';const n=48;for(let i=0;i<=n;i++){const a=-2.2+i/n*Math.PI*2.16,w=1+.045*Math.sin(i*.9+seed)+.03*Math.sin(i*2.3+seed*2);
 d+=(i?'L':'M')+(cx+rx*w*Math.cos(a)).toFixed(1)+' '+(cy+ry*w*Math.sin(a)).toFixed(1)}
 return `<path d="${d}" fill="none" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" ${draw(p)}/>`}
function sparkle(x,y,s,a){return a<=0?'':`<path d="M${x} ${y-s} Q${x} ${y} ${x+s} ${y} Q${x} ${y} ${x} ${y+s} Q${x} ${y} ${x-s} ${y} Q${x} ${y} ${x} ${y-s}Z" fill="#FFF4D6" opacity="${a.toFixed(2)}"/>`}
const tw=(t,ph,sp)=>.5+.5*Math.sin(t*(sp||4)+ph);   // 閃爍／呼吸

// ───────── 各鏡（每鏡回傳 HTML；o.hide 用於共用元素變形時隱藏）─────────
const SC={
 // s1 鉤子：第 0 格＝兩行標題＋完整大數字；事件：0–0.5 斜線畫出、0.45 劃線、0.5 蓋章、0.9／1.2／1.5 櫥窗燈熄三顆、1.8 戒指盒開、2.1 起戒指閃光
 hook(s,lt,d,o){
  let h=title(s.title,lt,{full:true});
  const u=pr(lt,.45,.4);   // 強調：手繪底線（本鏡唯一）
  h+=`<svg data-o="ul" class="abs" style="left:96px;top:398px" width="380" height="22"><path d="M4 12 C 90 4, 200 18, 372 8" stroke="${LAMP}" stroke-width="9" fill="none" stroke-linecap="round" ${draw(u)}/></svg>`;
  h+=tag(s.tag,lt,.5,430);
  if(!o.hideBig)h+=`<div data-o="big" class="abs bignum" style="top:500px">${esc(s.big)}</div>`;
  // 資料圖：全年結婚登記對數，2016→2025（以 0 為底的斜率線）
  const p=pr(lt,0,.5),base=170,k=120/160000,ya=base-s.trend.a*k,yb=base-s.trend.b*k,xa=480,xb=760,xe=xa+(xb-xa)*p,ye=ya+(yb-ya)*p;
  let g=T(0,62,s.label,38,700,TXT,'start')+T(0,116,'每點是一年的總數',30,400,SUBC,'start');
  g+=`<line x1="420" y1="${base}" x2="860" y2="${base}" stroke="${LINE}" stroke-width="2.5"/><line x1="${xa}" y1="${base}" x2="${xa}" y2="${ya}" stroke="${LINE}" stroke-width="2" stroke-dasharray="5 6" opacity=".6"/>`+
   `<line x1="${xa}" y1="${ya}" x2="${xe}" y2="${ye}" stroke="${LAMP}" stroke-width="7" stroke-linecap="round"/><circle cx="${xa}" cy="${ya}" r="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+
   (p>.98?`<line x1="${xb}" y1="${base}" x2="${xb}" y2="${yb}" stroke="${LINE}" stroke-width="2" stroke-dasharray="5 6" opacity=".6"/>`:'')+`<circle cx="${xe}" cy="${ye}" r="${10*settle(lt,.5)}" fill="${LAMP}"/>`;
  // 流動：線畫完後，光點沿 2016→2025 方向密集流過（拖尾 4 節），速度隨時間慢慢減下來
  if(lt>.5){const u0=lt-.5,ph=1.4/1.1*(1-Math.exp(-1.1*u0)),vel=1.4*Math.exp(-1.1*u0),fade=clamp(u0/.2);
   for(let j=0;j<12;j++){for(let k=0;k<5;k++){const u=((ph-k*.035*(.4+vel)+j/12)%1+1)%1,x=xa+(xb-xa)*u,y=ya+(yb-ya)*u;
    g+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(5.5-k).toFixed(1)}" fill="#FFF4D6" opacity="${(fade*(1-k*.2)*.9).toFixed(2)}"/>`}}}
  const lp=pr(lt,.55,.3);g+=`<g opacity="${lp}">${T(xa,ya-24,'14.8 萬對',30,700,TXT)}${T(xb,yb-22,'10.4 萬對',30,700,TXT)}${T(xa,base+36,'2016',30,400,SUBC)}${T(xb,base+36,'2025',30,400,SUBC)}</g>`;
  h+=box('chart',736,214,g,lt,d,{z:0});
  h+=box('illus',972,528,illBridal(lt),lt,d,{z:.05,px:-10});
  return h},
 // s2／s3 資料從哪來：同一張「橫條＋小人群像」；s2 只長 2016，s3 長 2025＋缺掉的 4 萬多對畫成虛線小人
 bars(s,lt,d,o){
  let h=title(s.title,lt)+tag(s.tag,lt,.12,306);
  if(!o.hideChip&&s.chip){const k=o.chipIn==null?1:o.chipIn;h+=`<div data-o="chip" class="abs chip" style="opacity:${k}">${esc(s.chip)}</div>`}
  h+=box('illus',392,348,s.stage===1?illCounter(lt):illBanquet(lt),lt,d,{z:.05,px:8});
  h+=box('chart',770,730,chartPeople(s,lt),lt,d,{z:0});
  return h},
 versus(s,lt,d){
  let h=title(s.title,lt);
  h+=box('illus',310,330,illBoard(lt),lt,d,{z:.05,px:-8});
  const pa=pr(lt,.05,.4,BACK),pb=pr(lt,.55,.42,BACK);let g='';
  [[s.a,pa,false,0],[s.b,pb,true,452]].forEach(([c,p,hi,x])=>{const dy=(1-clamp(p))*50;
   g+=`<g opacity="${clamp(p*1.6)}" transform="translate(0,${dy})"><rect x="${x+8}" y="20" width="420" height="640" rx="28" fill="${hi?FACE3:FACE}" stroke="${hi?LAMP:LINE}" stroke-width="${hi?4:3}" ${hi?'':'stroke-dasharray="12 10"'}/>`+
   T(x+218,104,c.k,38,700,hi?HINT:SUBC)+c.lines.map((l,i)=>T(x+218,300+i*100,l,70,700,TXT)).join('')+T(x+218,610,c.foot,30,400,SUBC)+`</g>`});
  // 強調：螢光筆劃過「越來越晚」（本鏡唯一）
  const m=pr(lt,1.0,.4);g=`<rect x="${452+48}" y="${336}" width="${340*m}" height="56" rx="8" fill="${LAMP}" opacity=".28"/>`+g;
  g+=`<g opacity="${pr(lt,1.35,.3)}" transform="translate(0,${(1-pr(lt,1.35,.3))*16})">${T(444,752,s.mid,40,700,TXT)}</g>`;
  h+=box('chart',668,832,g,lt,d,{z:0});
  return h},
 ruler(s,lt,d){
  let h=title(s.title,lt)+tag(s.tag,lt,.15,306);
  h+=box('illus',392,368,illCakes(lt),lt,d,{z:.05,px:10});
  const x0=70,x1=818,sx=v=>x0+(x1-x0)*(v-s.lo)/(s.hi-s.lo),ay=330;let g='';
  const rp=pr(lt,0,.45);g+=`<line x1="${x0}" y1="${ay}" x2="${x0+(x1-x0)*rp}" y2="${ay}" stroke="${LINE}" stroke-width="4"/>`;
  for(let v=s.lo;v<=s.hi;v++){const q=pr(lt,.04+(v-s.lo)*.06,.25);g+=`<g opacity="${q}"><line x1="${sx(v)}" y1="${ay-12}" x2="${sx(v)}" y2="${ay+12}" stroke="${LINE}" stroke-width="2"/>${T(sx(v),ay+56,String(v),32,400,SUBC)}</g>`}
  g+=`<g opacity="${pr(lt,.5,.3)}">${T(x1,ay+100,'歲',32,400,SUBC,'end')}</g>`;
  s.pins.forEach((m,i)=>{const a=.35+i*.5,p=pr(lt,a,.55),x=sx(s.lo+(m.v-s.lo)*p),up=i===0,lab=pr(lt,a+.55,.25,BACK),sc=settle(lt,a+.55);
   if(m.hi){const gl=pr(lt,a+.7,.4)*(0.75+.25*tw(lt,0,5));g+=glow(x,up?ay-182:ay+236,120,gl)}   // 強調：33.4 光暈（本鏡唯一）
   g+=`<g opacity="${clamp(p*4)}"><circle cx="${x}" cy="${ay}" r="16" fill="${m.hi?LAMP:FACE3}" stroke="${LINE}" stroke-width="3"/>`+
    `<line x1="${x}" y1="${ay+(up?-16:16)}" x2="${x}" y2="${up?ay-90:ay+110}" stroke="${LINE}" stroke-width="2"/></g>`+
    `<g opacity="${clamp(lab)}" transform="translate(${x},${up?ay-150:ay+216}) scale(${(sc*(.85+.15*lab)).toFixed(3)})">${T(0,up?-20:40,(m.v*INOUT((lt-a-.4)/.5)).toFixed(1)+' 歲',70,700,TXT)}${T(0,up?40:-20,m.lab,38,400,TXT)}</g>`});
  h+=box('chart',790,710,g,lt,d,{z:0});
  return h},
 card(s,lt,d){
  let h=title(s.title,lt)+tag(s.tag,lt,.15,306);
  h+=box('illus',392,368,illCradle(lt),lt,d,{z:.05,px:-10});
  const c=s.card,cp=pr(lt,0,.4,BACK),val=c.to*INOUT((lt-.15)/.75),sc=settle(lt,.9);
  let g=`<g opacity="${clamp(cp*1.5)}" transform="translate(444,250) scale(${(.92+.08*cp).toFixed(3)}) translate(-444,-250)"><rect x="64" y="20" width="760" height="460" rx="32" fill="${FACE3}" stroke="${LAMP}" stroke-width="4"/>`+T(444,120,c.lab,48,400,TXT)+`</g>`;
  const gl=pr(lt,.95,.35)*(.7+.3*tw(lt,1,4));g+=glow(444,300,250,gl);   // 強調：0.695 光暈（本鏡唯一）
  g+=`<g transform="translate(444,370) scale(${sc.toFixed(3)})">${T(0,0,(c.pre||'')+Math.max(0,val).toFixed(c.dec)+(c.unit||''),190,700,TXT)}</g>`;
  const bx=124,bw=640,by=560,bp=pr(lt,.3,.7,INOUT);
  g+=`<g opacity="${pr(lt,.2,.3)}"><rect x="${bx}" y="${by}" width="${bw}" height="44" rx="6" fill="none" stroke="${LINE}" stroke-width="2"/><rect x="${bx}" y="${by}" width="${bw*c.to*bp}" height="44" rx="6" fill="${LAMP}" opacity=".85"/>`+
   `<line x1="${bx+bw*.7}" y1="${by-14}" x2="${bx+bw*.7}" y2="${by+48}" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6"/>`+T(bx,by+96,'0',32,400,SUBC,'start')+T(bx+bw,by+96,'1',32,400,SUBC,'end')+`</g>`+
   `<g opacity="${pr(lt,1.1,.3)}">${T(bx+bw*.7,by+96,c.ref,34,700,TXT)}</g>`;
  h+=box('chart',790,710,g,lt,d,{z:0});
  return h},
 ask(s,lt,d){
  let h=title(s.title,lt,{cls:'hint'})+tag(s.tag,lt,.3,306);
  h+=box('illus',392,508,illTea(lt),lt,d,{z:.05,px:8});
  let g='';const rows=s.recap;
  rows.forEach((r,i)=>{const p=pr(lt,.15+i*.1,.4);g+=`<g opacity="${p}" transform="translate(${(1-p)*-40},0)"><rect x="20" y="${10+i*112}" width="848" height="92" rx="20" fill="${FACE}" stroke="${LINE}" stroke-width="2"/>${T(56,10+i*112+60,r[0],34,400,SUBC,'start')}${T(832,10+i*112+62,r[1],44,700,TXT,'end')}</g>`});
  const q=pr(lt,.65,.4,BACK);
  g+=`<g opacity="${clamp(q*1.5)}" transform="translate(444,440) scale(${(.9+.1*q).toFixed(3)}) translate(-444,-440)">${T(444,404,'二選一',32,700,HINT)}`+
   `<rect x="40" y="430" width="380" height="96" rx="48" fill="${FACE3}" stroke="${LAMP}" stroke-width="4"/>${T(230,492,s.opt[0],42,700,TXT)}`+
   `<rect x="468" y="430" width="380" height="96" rx="48" fill="${FACE3}" stroke="${LINE}" stroke-width="3" stroke-dasharray="10 8"/>${T(658,492,s.opt[1],42,700,TXT)}</g>`;
  h+=box('chart',930,570,g,lt,d,{z:0});
  return h},
 next(s,lt,d){
  let h=title(s.title,lt)+tag(s.tag,lt,.25,306);
  h+=box('illus',392,368,illBadge(lt),lt,d,{z:.05,px:-8});
  const p=pr(lt,.05,.45,BACK),rows=[0,1,2];
  let g=`<g opacity="${clamp(p*1.5)}" transform="translate(444,320) scale(${(.9+.1*p).toFixed(3)}) translate(-444,-320)"><rect x="104" y="40" width="680" height="440" rx="22" fill="${FACE}" stroke="${LINE}" stroke-width="3" stroke-dasharray="12 10"/>`+
   `<rect x="104" y="40" width="680" height="84" rx="22" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,96,s.slip,38,700,TXT)+`</g>`;
  rows.forEach(i=>{const q=pr(lt,.35+i*.09,.3);g+=`<g opacity="${q}">${i===0?T(160,236,s.row,36,400,TXT,'start'):''}<line x1="160" y1="${270+i*70}" x2="${160+(i?420:560)*q}" y2="${270+i*70}" stroke="${LINE}" stroke-width="2" opacity="${i?.35:.55}"/></g>`});
  const qm=.92+.08*Math.sin(lt*5);g+=`<g transform="translate(700,238) scale(${qm.toFixed(3)})">${T(0,0,'?',84,700,HINT,'end')}</g>`;
  g+=wobbleRing(668,212,70,62,pr(lt,.8,.5),3);    // 強調：圈住「?」（本鏡唯一）
  h+=box('chart',790,560,g,lt,d,{z:0});
  return h},
 // 片尾（≥3 秒，幀對齊；OF＝片尾第幾幀）：雲描出 f0–16 → 太陽升起 f14–32 → 三道光 f29／32／35 → 字 f38／43／48／53 一個個寫上
 //   → f58 落定「亮一下」（太陽光暈＋三道光變亮；招牌和弦同一幀）→ slogan f62 → 下一集 f68 →（關鍵字版）留言關鍵字 f74 → 停到片尾；太陽只輕呼吸、不轉圈
 outro(s,lt,d){
  const f=lt*30,P=(a,n,fn)=>(fn||EO)((f-a)/n),LK=58;
  const cl=P(0,16,INOUT),rise=P(14,18),sun=P(14,16,INOUT),br=f>LK+6?1+.022*Math.sin((f-LK-6)/30*4.2):1,flash=f>=LK?Math.exp(-(f-LK)/9):0;
  const C='M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z',A='M -26.3 -78.5 A 110 110 0 0 1 170.1 13.1',cx=63.9,cy=-15.5;
  let rays='';[-135,-90,-45].forEach((a,i)=>{const p=P(29+i*3,8,BACK),r0=140,r1=184,ra=a*Math.PI/180,re=r0+(r1-r0)*Math.min(p,1.06);
   if(p>.002)rays+=`<line x1="${cx+r0*Math.cos(ra)}" y1="${cy+r0*Math.sin(ra)}" x2="${cx+re*Math.cos(ra)}" y2="${cy+re*Math.sin(ra)}" stroke="#C5782B" stroke-width="${22+6*flash}" stroke-linecap="round"/>`});
  const sy=(1-rise)*80;
  let g=DEFS+glow(444+1.75*(cx-35),420+1.75*(cy-40+sy),260,.25*sun+.7*flash);
  g+=`<g transform="translate(444,420) scale(1.75) translate(-35,-40)">`+
   `<g transform="translate(${cx},${cy+sy}) scale(${br.toFixed(4)}) translate(${-cx},${-cy})"><path d="${A}" fill="none" stroke="#C5782B" stroke-width="${22+4*flash}" stroke-linecap="round" ${draw(sun)}/>${rays}</g>`+
   `<path d="${C}" fill="${FACE3}" fill-opacity="${clamp((cl-.55)/.45)}" stroke="#6E6A66" stroke-width="22" stroke-linecap="round" stroke-linejoin="round" ${draw(cl)}/></g>`;
  const chars=[['談','#2F2D2B'],['晴','#98622B'],['說','#2F2D2B'],['礙','#8A5A44']];
  chars.forEach((c,i)=>{const p=P(38+i*5,9,BACK),x=444+(i-1.5)*196,sc=f>=LK?1+.04*flash:1;
   if(p>.002)g+=`<g opacity="${clamp(p*2.5)}" transform="translate(${x},${830+(1-clamp(p))*30}) scale(${((.6+.4*p)*sc).toFixed(3)})"><text x="0" y="0" text-anchor="middle" font-family="Noto Serif CJK TC" font-weight="700" font-size="172" fill="${c[1]}">${c[0]}</text></g>`});
  const sl=P(62,10);if(sl>0)g+=`<g opacity="${sl}" transform="translate(0,${(1-sl)*14})">${T(444,940,s.slogan,42,400,SUBC)}</g>`;
  const nx=P(68,10);if(nx>0)g+=`<g opacity="${nx}" transform="translate(${(1-nx)*-24},0)"><rect x="94" y="994" width="700" height="84" rx="42" fill="${FACE}" stroke="${LINE}" stroke-width="2.5"/>${T(444,1050,s.nextLine,40,700,TXT)}</g>`;
  if(s.keyword){const kw=P(74,10,BACK);if(kw>0)g+=`<g opacity="${clamp(kw*2)}" transform="translate(444,1160) scale(${(.85+.15*kw).toFixed(3)})">${T(0,0,'留言「'+s.keyword+'」拿完整資料',46,700,HINT)}</g>`}
  return box('mark',400,s.keyword?1180:1100,g,lt,d,{z:.02})}
};

// ───────── 情境插圖（本篇量身，素材登記見 素材登記.md）─────────
function illBridal(t){   // 夜裡的婚紗店櫥窗＋窗外夜景＋戒指盒（888×552）
 let g=DEFS+`<rect x="0" y="0" width="888" height="552" rx="28" fill="${NIGHT}"/>`;
 [[60,40],[180,70],[330,30],[520,56],[700,90],[760,30]].forEach(([x,y],i)=>g+=sparkle(x,y,7,.35+.65*tw(t,i*1.7,3.2)));
 g+=`<path d="M786 58 a34 34 0 1 0 30 52 a28 28 0 1 1 -30 -52Z" fill="${WARM}" opacity=".9"/>`;
 // 遠處樓群，窗格明滅
 [[20,160,110,260],[140,120,90,300],[640,140,100,280],[748,180,120,240]].forEach(([x,y,w,hh],b)=>{g+=`<rect x="${x}" y="${y}" width="${w}" height="${hh}" fill="${NIGHT2}"/>`;
  for(let r=0;r<5;r++)for(let c=0;c<3;c++){const on=Math.sin(b*7.1+r*3.3+c*5.7)>-.2,f=on?.35+.45*tw(t,b+r*1.3+c,1.2+((b+r+c)%3)*.5):.08;g+=`<rect x="${x+10+c*(w-20)/3}" y="${y+16+r*42}" width="${(w-20)/3-10}" height="22" rx="2" fill="${WARM}" opacity="${f.toFixed(2)}"/>`}});
 // 店面
 g+=`<rect x="70" y="190" width="520" height="350" fill="${FACE}" stroke="${LINE}" stroke-width="4"/>`;
 let aw='';for(let i=0;i<8;i++){const x=70+i*65;aw+=`<path d="M${x} 190 h65 v44 a32.5 18 0 0 1 -65 0Z" fill="${i%2?FACE3:'#E9B98A'}" stroke="${LINE}" stroke-width="3"/>`}g+=aw;
 g+=`<rect x="250" y="148" width="160" height="44" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(330,182,'婚紗',32,700,TXT);
 g+=`<rect x="104" y="268" width="452" height="252" rx="6" fill="#F7E7CB" stroke="${LINE}" stroke-width="4"/>`;
 // 櫥窗燈串：10 顆，0.9／1.2／1.5 秒最後三顆熄掉
 let wire=`<path d="M118 284 Q 330 318 542 284" stroke="${LINE}" stroke-width="2" fill="none"/>`;
 for(let i=0;i<10;i++){const x=128+i*45,y=284+34*(1-Math.pow((x-330)/212,2))*0.5+4,off=i>=7?pr(t,.9+(i-7)*.3,.15):0,on=1-off;
  if(on>0)wire+=glow(x,y+6,22,on*(.55+.35*tw(t,i,6)));wire+=`<circle cx="${x}" cy="${y+6}" r="7" fill="${on>.5?'#F4B860':'#B9B2A8'}" stroke="${LINE}" stroke-width="1.5"/>`}
 g+=wire;
 // 人台＋白紗（頭紗輕擺）
 const sw=3*Math.sin(t*2.2);
 g+=`<line x1="330" y1="500" x2="330" y2="520" stroke="${LINE}" stroke-width="4"/><path d="M300 520 h60" stroke="${LINE}" stroke-width="4"/>`+
  `<path d="M312 330 q18 -12 36 0 l8 50 q-26 10 -52 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+
  `<path d="M304 380 q26 12 52 0 l46 120 q-72 16 -144 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+
  `<path d="M330 318 q${-50+sw} 40 ${-64+sw*2} 150" stroke="${LINE}" stroke-width="2" fill="none" opacity=".45"/><circle cx="330" cy="316" r="7" fill="${FACE3}" stroke="${LINE}" stroke-width="2"/>`;
 g+=`<path d="M130 496 l20 -40 l20 40Z M490 496 l20 -40 l20 40Z" fill="#E9D9BF" stroke="${LINE}" stroke-width="2"/>`;
 // 路燈（光暈呼吸）
 g+=glow(838,128,70,.5+.3*tw(t,0,2.4))+`<line x1="838" y1="140" x2="838" y2="540" stroke="${FACE3}" stroke-width="6"/><path d="M818 122 h40 l-8 18 h-24Z" fill="${WARM}" stroke="${FACE3}" stroke-width="2"/>`;
 // 戒指盒（1.8 秒開蓋），兩只戒指相扣、閃光
 const lid=pr(t,1.8,.35,BACK);
 g+=`<rect x="640" y="452" width="160" height="88" rx="6" fill="${FACE}" stroke="${LINE}" stroke-width="3"/>`+
  `<rect x="668" y="406" width="104" height="48" rx="8" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><rect x="680" y="414" width="80" height="20" rx="6" fill="#6E4636"/>`+
  `<circle cx="708" cy="414" r="15" fill="none" stroke="#F4B860" stroke-width="6"/><circle cx="730" cy="414" r="15" fill="none" stroke="#FFFDF8" stroke-width="6"/>`+
  `<g transform="translate(668,406) rotate(${(-78*lid).toFixed(1)}) translate(-668,-406)"><rect x="668" y="384" width="104" height="24" rx="8" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/></g>`;
 if(t>2.0)[[700,392],[742,396],[722,382]].forEach(([x,y],i)=>g+=sparkle(x,y,9,clamp((t-2.0)*4)*tw(t,i*2.1,7)));
 g+=`<line x1="0" y1="540" x2="888" y2="540" stroke="${FACE3}" stroke-width="3" opacity=".6"/>`;
 return g}
function illCounter(t){  // 戶政事務所櫃台：登記書滑上櫃台、0.75 秒蓋「受理」章、牆上時鐘走、盆栽輕擺（888×348）
 let g=`<rect x="0" y="0" width="888" height="348" rx="26" fill="${FACE}"/>`;
 g+=`<rect x="300" y="18" width="288" height="52" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,54,'戶政事務所',30,700,TXT);
 const sec=t*60/1.5*Math.PI/180*1.2,mn=(t*8+40)*Math.PI/180;
 g+=`<circle cx="790" cy="92" r="52" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`;for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${790+42*Math.cos(a)}" y1="${92+42*Math.sin(a)}" x2="${790+48*Math.cos(a)}" y2="${92+48*Math.sin(a)}" stroke="${LINE}" stroke-width="2"/>`}
 g+=`<line x1="790" y1="92" x2="${790+26*Math.sin(mn)}" y2="${92-26*Math.cos(mn)}" stroke="${TXT}" stroke-width="5" stroke-linecap="round"/><line x1="790" y1="92" x2="${790+40*Math.sin(sec)}" y2="${92-40*Math.cos(sec)}" stroke="${LAMP}" stroke-width="3" stroke-linecap="round"/><circle cx="790" cy="92" r="5" fill="${TXT}"/>`;
 // 盆栽
 const lw=4*Math.sin(t*2.6);g+=`<path d="M86 236 h64 l-8 -44 h-48Z" fill="#C98F5E" stroke="${LINE}" stroke-width="3"/>`+
  `<path d="M118 192 q${-30+lw} -40 ${-40+lw} -84" stroke="#7E8F6A" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M118 192 q${24+lw} -50 ${30+lw} -100" stroke="#8FA078" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M118 192 q${4+lw} -30 ${2+lw} -66" stroke="#7E8F6A" stroke-width="10" fill="none" stroke-linecap="round"/>`;
 // 櫃台
 g+=`<rect x="0" y="236" width="888" height="112" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><rect x="0" y="226" width="888" height="16" fill="${DARK}" stroke="${LINE}" stroke-width="3"/>`;
 g+=`<path d="M640 226 a26 20 0 0 1 52 0Z" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><rect x="662" y="196" width="8" height="12" fill="${LINE}"/>`;
 // 登記書
 const fp=pr(t,0,.4),fy=(1-fp)*60;
 g+=`<g transform="translate(0,${fy})" opacity="${clamp(fp*2)}"><rect x="300" y="104" width="236" height="122" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(418,140,'結婚登記書',30,700,TXT)}`+
  `<line x1="322" y1="160" x2="512" y2="160" stroke="${LINE}" stroke-width="2" opacity=".5"/><line x1="322" y1="184" x2="470" y2="184" stroke="${LINE}" stroke-width="2" opacity=".5"/><line x1="322" y1="206" x2="440" y2="206" stroke="${LINE}" stroke-width="2" opacity=".5"/>`;
 const im=pr(t,.72,.22,BACK);if(im>0)g+=`<g transform="translate(486,190) scale(${(1.3-.3*im).toFixed(3)}) rotate(-8)" opacity="${clamp(im*2)}"><circle r="36" fill="none" stroke="${LAMP}" stroke-width="4"/>${T(0,11,'受理',30,700,LAMP)}</g>`;
 g+=`</g>`;
 // 印章：落下→蓋→抬起
 const dn=pr(t,.5,.22,INOUT),up=pr(t,.86,.3),sy=-120+110*dn-120*up;
 if(t<1.3)g+=`<g transform="translate(486,${150+sy})" opacity="${t<.45?pr(t,.3,.15):1-up}"><rect x="-12" y="-70" width="24" height="44" rx="8" fill="#8A5A44"/><rect x="-26" y="-30" width="52" height="24" rx="6" fill="#6E4636"/></g>`;
 return g}
function illBanquet(t){  // 喜宴圓桌俯視：10 個座位，0.6 秒起三個變虛線空位；彩旗輕擺、氣球上下飄（888×348）
 let g=`<rect x="0" y="0" width="888" height="348" rx="26" fill="${FACE}"/>`;
 let fl=`<path d="M20 26 Q 444 ${80+6*Math.sin(t*2)} 868 26" stroke="${LINE}" stroke-width="2" fill="none"/>`;
 for(let i=0;i<13;i++){const x=50+i*64,y=26+ (80+6*Math.sin(t*2)-26)*(1-Math.pow((x-444)/424,2))*0.5,r=6*Math.sin(t*3+i);fl+=`<path d="M${x-14} ${y} h28 l-14 ${30}Z" fill="${i%3===0?'#E9B98A':i%3===1?FACE3:'#D8C3A5'}" stroke="${LINE}" stroke-width="2" transform="rotate(${r.toFixed(1)} ${x} ${y})"/>`}
 g+=fl;
 const cx=290,cy=210,R=86;g+=`<circle cx="${cx}" cy="${cy}" r="${R}" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><circle cx="${cx}" cy="${cy}" r="${R-16}" fill="none" stroke="${LINE}" stroke-width="2" stroke-dasharray="4 8" opacity=".6"/>`;
 g+=`<circle cx="${cx}" cy="${cy}" r="20" fill="#E9B98A" stroke="${LINE}" stroke-width="2"/>`;for(let i=0;i<5;i++){const a=i*72*Math.PI/180+t*.6;g+=`<circle cx="${cx+14*Math.cos(a)}" cy="${cy+14*Math.sin(a)}" r="7" fill="${FACE3}" stroke="${LINE}" stroke-width="1.5"/>`}
 for(let i=0;i<10;i++){const a=(-90+i*36)*Math.PI/180,x=cx+(R+30)*Math.cos(a),y=cy+(R+30)*Math.sin(a),p=pr(t,.02+i*.06,.25,BACK),gone=i>=7?pr(t,.6+(i-7)*.12,.25):0;
  if(y+16>346)continue;
  g+=`<g transform="translate(${x},${y}) rotate(${i*36}) scale(${(.6+.4*p).toFixed(3)})" opacity="${clamp(p*2)}"><rect x="-20" y="-14" width="40" height="28" rx="8" fill="${gone>.5?'none':FACE3}" stroke="${gone>.5?LINE:LINE}" stroke-width="3" ${gone>.5?'stroke-dasharray="6 5" opacity=".55"':''}/></g>`}
 // 氣球與禮物
 const by=8*Math.sin(t*2.4);
 g+=`<path d="M640 ${150+by} q-6 70 10 140" stroke="${LINE}" stroke-width="2" fill="none"/><path d="M700 ${140-by} q10 70 -20 150" stroke="${LINE}" stroke-width="2" fill="none"/>`+
  `<ellipse cx="640" cy="${118+by}" rx="34" ry="40" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><ellipse cx="702" cy="${108-by}" rx="34" ry="40" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
 g+=`<rect x="760" y="170" width="96" height="80" rx="6" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><rect x="802" y="170" width="12" height="80" fill="${LAMP}" opacity=".8"/><path d="M808 170 q-30 -34 -36 -6 q14 8 36 6 q30 -34 36 -6 q-14 8 -36 6" fill="none" stroke="${LAMP}" stroke-width="4"/>`;
 g+=T(884,336,'10 席空 3 席（示意）',30,400,SUBC,'end');
 return g}
// 橫條＋小人群像：每個小人（成對）＝1 萬對；長條先長，數值後出；小人 stagger 70ms
function couple(x,y,c,dash,op){const st=dash?`stroke-dasharray="4 4"`:'';const f=dash?'none':c;
 return `<g transform="translate(${x},${y})" opacity="${op.toFixed(3)}"><circle cx="11" cy="10" r="8" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/><path d="M2 46 v-18 q9 -10 18 0 v18Z" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/>`+
  `<circle cx="29" cy="12" r="7" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/><path d="M21 46 v-16 q8 -9 16 0 v16Z" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/></g>`}
function chartPeople(s,lt){
 const X0=150,L=680,k=L/s.vmax;let g=T(0,40,s.unit,32,400,SUBC,'start');
 const legend=pr(lt,.2,.3);g+=`<g opacity="${legend}">${couple(694,4,FACE3,false,1)}${T(888,40,'＝1 萬對',30,700,TXT,'end')}</g>`;
 s.bars.forEach((b,i)=>{const y=110+i*300,grow=s.stage===1?(i===0?pr(lt,.05,.6,INOUT):0):(i===0?1:pr(lt,.05,.6,INOUT));
  g+=T(0,y+44,b.lab,40,700,TXT,'start');
  if(grow<=0){g+=`<rect x="${X0}" y="${y}" width="${b.v*k}" height="60" rx="8" fill="none" stroke="${LINE}" stroke-width="2.4" stroke-dasharray="10 8" opacity=".5"/>`+T(X0+b.v*k/2,y+44,'?',44,700,SUBC);return}
  const w=b.v*k*grow;g+=`<rect x="${X0}" y="${y}" width="${w}" height="60" rx="8" fill="${b.hi?LAMP:FACE3}" stroke="${b.hi?LAMP:LINE}" stroke-width="2.4" opacity="${b.hi?.92:1}"/>`;
  const st=(s.stage===1||i===1)?.65:-1;   // 長條長完才出數值
  if(st<0)g+=T(X0+w-14,y-14,fmtInt(b.v),46,700,TXT,'end');
  else{const q=clamp((lt-st)/.35),v=b.v*INOUT(q),sc=settle(lt,st+.35);if(q>0)g+=`<g opacity="${clamp(q*3)}" transform="translate(${X0+w-14},${y-14}) scale(${sc.toFixed(3)})">${T(0,0,fmtInt(v),46,700,TXT,'end')}</g>`}
  // 小人群像：v/1 萬 個（最後一個依小數裁切）
  const n=b.v/10000,full=Math.floor(n),stA=(s.stage===1||i===1)?.3:-9;
  for(let j=0;j<Math.ceil(n);j++){const op=stA<0?1:pr(lt,stA+j*.07,.2);if(op<=0)continue;const x=X0+j*46,frac=j<full?1:n-full;
   g+=frac<1?`<clipPath id="cp${i}"><rect x="${x}" y="${y+80}" width="${40*frac}" height="60"/></clipPath><g clip-path="url(#cp${i})">${couple(x,y+84,b.hi?'#F0B87E':FACE3,false,op)}</g>`+couple(x,y+84,'',true,op*.6):couple(x,y+84,b.hi?'#F0B87E':FACE3,false,op)}
  // s3：少掉的 4.3 萬對，用虛線小人補在後面
  if(s.stage===2&&i===1){const gap=(s.bars[0].v-b.v)/10000;for(let j=Math.ceil(n);j<Math.ceil(n+gap);j++){const op=pr(lt,1.05+(j-Math.ceil(n))*.08,.2);if(op>0)g+=couple(X0+j*46,y+84,'',true,op*.7)}}});
 if(s.stage===2){const np=pr(lt,1.3,.35,BACK);if(np>0){g+=`<g opacity="${clamp(np*2)}" transform="translate(444,642) scale(${(.85+.15*np).toFixed(3)}) translate(-444,-642)">${T(444,656,s.note,48,700,TXT)}</g>`;
  g+=wobbleRing(444,640,300,58,pr(lt,1.55,.5),1)}}   // 強調：圈住差額（本鏡唯一）
 return g}
function illBoard(t){   // 翻牌告示板：「結婚 → 延後」「登記對數 → 減少」逐片翻牌；時鐘走（888×330）
 let g=`<rect x="0" y="0" width="888" height="330" rx="26" fill="${FACE}"/>`;
 g+=`<rect x="40" y="40" width="640" height="260" rx="16" fill="#3B3936" stroke="${LINE}" stroke-width="4"/>`+T(70,88,'項目',30,700,'#D8CFC0','start')+T(400,88,'狀態',30,700,'#D8CFC0','start');
 const rows=[['結婚','準時','延後',.45],['登記對數','持平','減少',.85]];
 rows.forEach(([a,from,to,at],r)=>{const y=110+r*90;g+=`<rect x="64" y="${y}" width="290" height="70" rx="8" fill="#4A4744"/>`+T(84,y+48,a,36,700,'#F6F1E8','start');
  for(let c=0;c<2;c++){const x=400+c*120,k=clamp((t-at-c*.08)/.28),showTo=k>.5,half=Math.abs(Math.cos(k*Math.PI));
   g+=`<rect x="${x}" y="${y}" width="110" height="70" rx="8" fill="#4A4744"/><g transform="translate(${x+55},${y+35}) scale(1,${(k>0&&k<1?half:1).toFixed(3)}) translate(${-x-55},${-y-35})">`+
    `<rect x="${x}" y="${y}" width="110" height="70" rx="8" fill="${showTo&&c===0||showTo&&c===1?'#5A4A3C':'#4A4744'}"/>${T(x+55,y+50,(showTo?to:from)[c],40,700,showTo?'#F4B860':'#F6F1E8')}</g><line x1="${x}" y1="${y+35}" x2="${x+110}" y2="${y+35}" stroke="#2B2927" stroke-width="2"/>`}});
 const a=(t*30+120)*Math.PI/180,b=(t*200)*Math.PI/180;
 g+=`<circle cx="784" cy="120" r="64" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/><line x1="784" y1="120" x2="${784+34*Math.sin(a)}" y2="${120-34*Math.cos(a)}" stroke="${TXT}" stroke-width="6" stroke-linecap="round"/><line x1="784" y1="120" x2="${784+50*Math.sin(b)}" y2="${120-50*Math.cos(b)}" stroke="${LAMP}" stroke-width="3" stroke-linecap="round"/><circle cx="784" cy="120" r="6" fill="${TXT}"/>`;
 g+=`<rect x="744" y="210" width="80" height="80" rx="10" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><path d="M768 210 v-16 h32 v16" fill="none" stroke="${LINE}" stroke-width="3"/><line x1="744" y1="244" x2="824" y2="244" stroke="${LINE}" stroke-width="2"/>`;
 return g}
function illCakes(t){   // 撕頁年曆 2016→2025 一頁頁翻走；兩個蛋糕插數字蠟燭 31、33，火苗晃（888×368）
 let g=`<rect x="0" y="0" width="888" height="368" rx="26" fill="${FACE}"/>`;
 const idx=Math.min(9,Math.floor(Math.max(0,t-.1)/.16)),fr=clamp((Math.max(0,t-.1)%.16)/.16);
 g+=`<rect x="44" y="36" width="250" height="300" rx="14" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><rect x="44" y="36" width="250" height="64" rx="14" fill="#C9705A"/>`+T(169,80,'年曆',30,700,'#FFFDF8');
 for(let i=0;i<5;i++)g+=`<circle cx="${80+i*45}" cy="36" r="9" fill="${FACE}" stroke="${LINE}" stroke-width="3"/>`;
 const yr=y=>T(169,230,String(y),78,700,TXT)+T(169,290,'年',30,400,SUBC);
 g+=yr(2016+Math.min(9,idx+(idx<9?1:0)));
 if(idx<9){const k=EO(fr);g+=`<g transform="translate(${169+k*40},${100}) rotate(${(-18*k).toFixed(1)}) scale(1,${(1-k*.85).toFixed(3)}) translate(-169,-100)" opacity="${(1-k).toFixed(3)}"><rect x="44" y="100" width="250" height="236" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${yr(2016+idx)}</g>`}
 const cake=(x,lab,num)=>{let c=`<ellipse cx="${x}" cy="320" rx="120" ry="16" fill="${DARK}"/><rect x="${x-96}" y="230" width="192" height="88" rx="14" fill="#F0D7B7" stroke="${LINE}" stroke-width="3"/>`+
   `<path d="M${x-96} 250 q24 20 48 0 q24 20 48 0 q24 20 48 0 q24 20 48 0 v-14 a14 14 0 0 0 -14 -14 h-164 a14 14 0 0 0 -14 14Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  [0,1].forEach(j=>{const cx=x-26+j*52,fl=1+.14*Math.sin(t*13+j*2+x),fx=2*Math.sin(t*9+j);
   c+=`<rect x="${cx-20}" y="166" width="40" height="56" rx="6" fill="${j?'#E9B98A':FACE3}" stroke="${LINE}" stroke-width="2.5"/>`+T(cx,207,num[j],38,700,TXT)+`<line x1="${cx}" y1="166" x2="${cx}" y2="152" stroke="${LINE}" stroke-width="2"/>`+
    glow(cx,138,26,.55+.25*tw(t,j,9))+`<path d="M${cx} ${150} q-10 -12 ${fx} ${-26*fl} q10 14 ${-fx} ${26*fl}Z" fill="#F4B860" stroke="#C5782B" stroke-width="1.5"/>`});
  return c+T(x,360,lab,30,700,SUBC)};
 g+=cake(470,'女性','31')+cake(726,'男性','33');
 return g}
function illCradle(t){  // 搖籃輕搖＋一雙嬰兒鞋＋小夜燈呼吸（888×368）
 let g=`<rect x="0" y="0" width="888" height="368" rx="26" fill="${FACE}"/><line x1="20" y1="330" x2="868" y2="330" stroke="${LINE}" stroke-width="3" opacity=".5"/>`;
 const r=4*Math.sin(t*2.4);
 g+=`<g transform="rotate(${r.toFixed(2)} 330 330)"><path d="M150 312 Q330 356 510 312" stroke="#8A5A44" stroke-width="10" fill="none" stroke-linecap="round"/>`+
  `<line x1="230" y1="290" x2="220" y2="326" stroke="#8A5A44" stroke-width="8"/><line x1="430" y1="290" x2="440" y2="326" stroke="#8A5A44" stroke-width="8"/>`+
  `<path d="M180 180 h300 q0 116 -150 116 q-150 0 -150 -116Z" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`+
  `<path d="M180 180 q-10 -110 110 -116 q0 60 -30 116Z" fill="#E9B98A" stroke="${LINE}" stroke-width="4"/>`;
 for(let i=0;i<6;i++)g+=`<line x1="${215+i*48}" y1="186" x2="${215+i*48}" y2="${250+10*Math.sin(i)}" stroke="${LINE}" stroke-width="2" opacity=".35"/>`;
 g+=`<path d="M300 180 q60 26 180 0" stroke="${LAMP}" stroke-width="10" fill="none" opacity=".7" stroke-linecap="round"/></g>`;
 const shoe=(x,f)=>`<g transform="translate(${x},300) scale(${f},1)"><path d="M-36 24 q-4 -30 18 -34 q14 -2 18 12 q24 6 30 22Z" fill="#F0D7B7" stroke="${LINE}" stroke-width="3"/><path d="M-14 -4 q8 8 16 0" stroke="${LAMP}" stroke-width="3" fill="none"/></g>`;
 g+=shoe(620,1)+shoe(690,1);
 const bl=.55+.35*tw(t,0,3);g+=glow(800,210,90,bl)+`<rect x="788" y="250" width="24" height="76" rx="6" fill="${LINE}"/><path d="M766 250 h68 l-14 -50 h-40Z" fill="#FFF1D2" stroke="${LINE}" stroke-width="3"/>`;
 for(let i=0;i<3;i++){const y=60+((t*30+i*40)%120);g+=sparkle(600+i*70,y,6,.3+.5*tw(t,i*2,4))}
 return g}
function illTea(t){     // 窗內：窗簾擺、窗外樓燈一盞盞亮、桌上兩杯茶＋茶壺冒蒸氣（888×508）
 let g=DEFS+`<rect x="0" y="0" width="888" height="508" rx="26" fill="${FACE}"/>`;
 const L=pr(t,.4,.6);g+=glow(444,190,330,.35*L);    // 強調：窗燈亮起（本鏡唯一）
 g+=`<rect x="190" y="30" width="508" height="300" rx="10" fill="${NIGHT}" stroke="${LINE}" stroke-width="6"/>`;
 [[200,170,90],[300,120,80],[392,190,110],[512,140,90],[612,180,80]].forEach(([x,y,w],b)=>{g+=`<rect x="${x}" y="${y}" width="${w}" height="${330-y}" fill="${NIGHT2}"/>`;
  for(let r=0;r<3;r++)for(let c=0;c<2;c++){const n=b*6+r*2+c,on=pr(t,.2+((n*7)%23)*.07,.15);g+=`<rect x="${x+12+c*(w-24)/2}" y="${y+18+r*44}" width="${(w-24)/2-10}" height="24" rx="2" fill="${WARM}" opacity="${(.12+.7*on).toFixed(2)}"/>`}});
 g+=`<line x1="444" y1="30" x2="444" y2="330" stroke="${LINE}" stroke-width="5"/><line x1="190" y1="180" x2="698" y2="180" stroke="${LINE}" stroke-width="5"/>`;
 g+=`<rect x="170" y="330" width="548" height="20" rx="4" fill="${DARK}" stroke="${LINE}" stroke-width="3"/>`;
 const cw=(side,ph)=>{const s=10*Math.sin(t*1.6+ph),x0=side<0?150:738,dir=side;let d=`M${x0} 16 h${dir*120} q${s} 120 ${-dir*10+s*1.6} 300 h${-dir*110}Z`;return `<path d="${d}" fill="#F0D7B7" stroke="${LINE}" stroke-width="3" opacity=".95"/>`};
 g+=cw(1,0)+cw(-1,1.3)+`<line x1="130" y1="16" x2="758" y2="16" stroke="${LINE}" stroke-width="6" stroke-linecap="round"/>`;
 g+=`<g transform="translate(0,46)">`;
 g+=`<rect x="60" y="420" width="768" height="22" rx="6" fill="#C98F5E" stroke="${LINE}" stroke-width="3"/>`;
 const cup=(x,c)=>`<ellipse cx="${x}" cy="418" rx="62" ry="10" fill="${DARK}" stroke="${LINE}" stroke-width="2.5"/><path d="M${x-44} 352 h88 q-4 62 -44 62 q-40 0 -44 -62Z" fill="${c}" stroke="${LINE}" stroke-width="3"/><path d="M${x+42} 366 q26 2 18 24 q-6 12 -24 10" fill="none" stroke="${LINE}" stroke-width="3"/>`+
  `<line x1="${x-14}" y1="352" x2="${x-26}" y2="388" stroke="${LINE}" stroke-width="1.5"/><rect x="${x-34}" y="386" width="14" height="16" rx="2" fill="${LAMP}" opacity=".8"/>`;
 g+=cup(300,FACE3)+cup(470,'#F0D7B7');
 g+=`<path d="M600 418 q-10 -70 70 -70 q80 0 70 70Z" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><path d="M600 382 q-34 -6 -40 -30" fill="none" stroke="${LINE}" stroke-width="4"/><path d="M740 372 q34 0 30 30 q-4 14 -30 12" fill="none" stroke="${LINE}" stroke-width="4"/><ellipse cx="670" cy="348" rx="34" ry="8" fill="${DARK}" stroke="${LINE}" stroke-width="2.5"/><circle cx="670" cy="336" r="8" fill="${LINE}"/>`;
 [[300,0],[470,1.1],[560,2.2]].forEach(([x,ph])=>{for(let k=0;k<2;k++){const u=((t*.9+ph*.3+k*.5)%1),y=340-u*80,o=Math.sin(u*Math.PI)*.6;
  g+=`<path d="M${x+k*14-6} ${y+30} q-12 -14 0 -28 q12 -14 0 -28" stroke="${SUBC}" stroke-width="3.5" fill="none" stroke-linecap="round" opacity="${o.toFixed(2)}"/>`}});
 g+=`</g>`;
 return g}
function illBadge(t){   // 牆上掛勾的識別證吊牌「新鮮人」左右擺、公事包、站牌「下一站」（888×368）
 let g=`<rect x="0" y="0" width="888" height="368" rx="26" fill="${FACE}"/><line x1="20" y1="336" x2="868" y2="336" stroke="${LINE}" stroke-width="3" opacity=".5"/>`;
 const a=7*Math.sin(t*2.2);
 g+=`<circle cx="444" cy="34" r="10" fill="${LINE}"/><g transform="rotate(${a.toFixed(2)} 444 34)"><path d="M444 34 L384 150 M444 34 L504 150" stroke="${LAMP}" stroke-width="8" fill="none"/>`+
  `<rect x="360" y="146" width="168" height="196" rx="16" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/><rect x="420" y="160" width="48" height="12" rx="6" fill="${DARK}"/>`+
  `<circle cx="444" cy="222" r="30" fill="${DARK}" stroke="${LINE}" stroke-width="3"/><path d="M406 290 q38 -42 76 0" fill="${DARK}" stroke="${LINE}" stroke-width="3"/>${T(444,330,'新鮮人',30,700,TXT)}</g>`;
 g+=`<rect x="80" y="240" width="170" height="96" rx="12" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><path d="M135 240 v-20 h60 v20" fill="none" stroke="${LINE}" stroke-width="5"/><rect x="155" y="268" width="20" height="14" rx="3" fill="#F4B860"/>`;
 const sp=pr(t,.2,.4,BACK);
 g+=`<line x1="720" y1="336" x2="720" y2="110" stroke="${LINE}" stroke-width="7"/><g transform="translate(720,100) scale(${(.6+.4*sp).toFixed(3)})" opacity="${clamp(sp*2)}"><rect x="-80" y="-40" width="160" height="70" rx="12" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/>${T(0,8,'下一站',32,700,TXT)}</g>`;
 g+=`<path d="M690 ${200} l14 0 l-4 -8 M690 ${200} l14 0 l-4 8" stroke="${LAMP}" stroke-width="3" fill="none" transform="translate(${(t*40)%60},0)" opacity="${(.3+.6*tw(t,0,5)).toFixed(2)}"/>`;
 return g}

// ───────── 背景（紙紋＋淡格線＋光影，緩慢視差；不帶 data-o）─────────
function bg(t){const px=-t*7,py=-t*4,gx=-t*16,gy=-t*9,lx=30+12*Math.sin(t*.35),ly=28+8*Math.cos(t*.27),la=.55+.12*Math.sin(t*1.1);
 return `<div class="abs bgl" style="background-image:url('${V.paper}');background-size:512px 512px;background-position:${px.toFixed(1)}px ${py.toFixed(1)}px"></div>`+
  `<div class="abs bgl grid" style="background-position:${gx.toFixed(1)}px ${gy.toFixed(1)}px"></div>`+
  `<div class="abs bgl" style="background:radial-gradient(900px 700px at ${lx.toFixed(1)}% ${ly.toFixed(1)}%,rgba(255,226,180,${la.toFixed(3)}),rgba(255,226,180,0) 70%)"></div>`+
  `<div class="abs bgl" style="background:radial-gradient(700px 600px at ${(80-lx/3).toFixed(1)}% 86%,rgba(217,130,43,.07),rgba(217,130,43,0) 70%)"></div>`}

// ───────── 轉場（遮罩擦除＋晴光橘前緣／圓形展開；新鏡自帶背景蓋住舊鏡，不淡出到空白）─────────
function trans(kind,p,t){const e=EO(p);let clip,edge='';
 if(kind==='circle'){const r=e*2300;clip=`circle(${r.toFixed(0)}px at 540px 1100px)`;edge=`<div class="abs" style="left:${540-r}px;top:${1100-r}px;width:${2*r}px;height:${2*r}px;border-radius:50%;border:${(18*(1-e)+4).toFixed(1)}px solid rgba(217,130,43,${(.5*(1-e)).toFixed(3)})"></div>`}
 else if(kind==='diag'){const f=-700+(1080+1400)*e;clip=`polygon(${f+700}px 0,1080px 0,1080px 1920px,${f}px 1920px)`;clip=`polygon(0 0,${(f+700).toFixed(0)}px 0,${f.toFixed(0)}px 1920px,0 1920px)`;
  edge=`<svg class="abs" style="left:0;top:0" width="1080" height="1920"><line x1="${f+700}" y1="0" x2="${f}" y2="1920" stroke="rgba(217,130,43,${(.55*(1-e)+.1).toFixed(3)})" stroke-width="${(26*(1-e)+6).toFixed(1)}"/></svg>`}
 else if(kind==='up'){const y=1920*(1-e);clip=`inset(${y.toFixed(0)}px 0 0 0)`;edge=`<div class="abs" style="left:0;top:${y-10}px;width:1080px;height:20px;background:rgba(217,130,43,${(.5*(1-e)+.1).toFixed(3)})"></div>`}
 else {const x=1080*(1-e);clip=`inset(0 0 0 ${x.toFixed(0)}px)`;edge=`<div class="abs" style="left:${x-12}px;top:0;width:24px;height:1920px;background:rgba(217,130,43,${(.5*(1-e)+.1).toFixed(3)})"></div>`}
 return {clip,edge}}
const strip=h=>h.replace(/data-o="/g,'data-x="');

window.renderAt=function(t){const S=V.scenes;let i=S.length-1;for(let j=0;j<S.length;j++){if(t>=S[j].t0&&t<S[j].t1){i=j;break}}
 const s=S[i],lt=t-s.t0,d=s.t1-s.t0;let html=bg(t);
 const morph=s.morphFrom&&lt<TR+.12;      // s1→s2 大數字飛進角落
 const optsNew={hideChip:morph&&lt<TR,chipIn:morph?clamp((lt-TR)/.12):1};
 const cur=SC[s.type](s,lt,d,optsNew);
 if(i>0&&lt<TR){const p=lt/TR,o=S[i-1],olt=t-o.t0,od=o.t1-o.t0,tr=trans(s.trans||'wipe',p,t);
  html+=`<div class="abs layer">${strip(SC[o.type](o,olt,od,{hideBig:!!s.morphFrom}))}</div>`;
  html+=`<div class="abs layer" style="clip-path:${tr.clip}">${bg(t)}${cur}</div>${tr.edge}`;
 }else html+=`<div class="abs layer">${cur}</div>`;
 if(morph&&lt<TR){const k=EO(lt/TR),fs=200+(40-200)*k,cx=540+(904-540)*k,cy=610+(334-610)*k;   // 從 s1 大數字中心飛到 s2 標籤列右側
  const pw=fs*3.6,ph=fs*1.2;html+=`<div class="abs" style="left:${(cx-pw/2).toFixed(1)}px;top:${(cy-ph/2).toFixed(1)}px;width:${pw.toFixed(1)}px;height:${ph.toFixed(1)}px;border-radius:${ph}px;background:rgba(217,130,43,${(.95*k).toFixed(3)});box-shadow:0 0 0 ${(6*(1-k)).toFixed(1)}px rgba(246,241,232,.9)"></div><div class="abs flyer" style="left:${(cx-500).toFixed(1)}px;top:${(cy-fs*.62).toFixed(1)}px;font-size:${fs.toFixed(1)}px;line-height:${(fs*1.24).toFixed(1)}px;color:${k>.5?'#fff':'var(--text)'}">${esc(S[i-1].big)}</div>`}
 // 字幕：舊句 0.14 秒往上淡出 → 新句 0.1–0.34 秒由下緩入；出處同理
 const prev=i>0?S[i-1]:null;
 if(prev&&lt<.14){const k=EO(lt/.14);html+=capHTML(prev.cap,1-k,-14*k)}
 else if(s.type!=='outro'){const k=prev?EO((lt-.1)/.24):1;html+=capHTML(s.cap,k,(1-k)*18)}   // 片尾卡不放字幕：念稿那句已寫在卡上（留言「結婚」拿完整資料）
 if(prev&&prev.src!==s.src&&lt<.12){html+=srcHTML(prev.src,1-EO(lt/.12))}else{html+=srcHTML(s.src,prev&&prev.src!==s.src?EO((lt-.08)/.2):1)}
 html+=`<div data-o="foot" class="abs foot"></div>`+(V.asof?`<div data-o="asof" class="abs asof">查證截至 ${esc(V.asof)}</div>`:'');
 document.getElementById('stage').innerHTML=html};
// 音效事件（render_video.js 讀取後合成）：轉場 whoosh、蓋章 pop、數字落定 chime、片尾卡林巴
window.sfxEvents=function(){const S=V.scenes,ev=[];S.forEach((s,i)=>{if(i>0&&s.type!=='outro')ev.push({t:s.t0,type:'whoosh'});
  if(s.tag)ev.push({t:s.t0+({hook:.5,bars:.12,ruler:.15,card:.15,ask:.3,next:.25}[s.type]||.2),type:'pop'});
  if(s.type==='bars'&&s.stage===1)ev.push({t:s.t0+.75,type:'pop'});
  if(s.type==='card')ev.push({t:s.t0+.9,type:'chime'});
  if(s.type==='outro'){const F=k=>s.t0+k/30;ev.push({t:F(0),type:'kal',n:[-5],g:.7});ev.push({t:F(14),type:'kal',n:[0]});[0,1,2].forEach(k=>ev.push({t:F(29+k*3),type:'kal',n:[4,7,9][k],g:.8}));
   [0,1,2,3].forEach(k=>ev.push({t:F(38+k*5),type:'kal',n:[12,14,16,19][k]}));ev.push({t:F(58),type:'bloom',n:[0,4,7,12,16]});ev.push({t:F(68),type:'kal',n:[19,24],g:.55});if(s.keyword)ev.push({t:F(74),type:'kal',n:[16],g:.5});ev.push({t:F(0),type:'pad',dur:s.t1-s.t0})}});return ev};
window.renderAt(0);
