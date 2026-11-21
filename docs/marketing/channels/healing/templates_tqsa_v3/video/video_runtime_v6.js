// 談晴說礙 數據短影音執行期 v5（2026-11-15）＝v4＋CEO 動畫／美編兩關退件小修（見 queue/20261116_marriage/video_v4_review_*.md）
// v5 改動：片尾四字蓋在雲下淨空帶（≥24px，逐幀檢查）、留言關鍵字提前＋橘底白字膠囊、靜止段補第二拍、轉場前後文字同框 ≤4 幀、s1 黃昏暖色、資料圖重排、小字全 ≥32px
// ── 以下為 v4 原說明 ──
// 談晴說礙 數據短影音執行期 v4（2026-11-15）
// 依據：Andy 看完 v3：「不要出現圖片一直慢慢放大效果，有夠爛」「LOGO 動畫需要有吸引人的出場，配音效」＋ plan.md「2026-11-15 禁止慢慢放大」
// v4 與 v3 的差別：
//  - 拿掉所有整張圖的持續推近／放大／平移（v3 的 cam() 每鏡 1.04–1.05 倍＋平移，邊緣會露出空白）；插圖面板外框固定、內容不縮放不平移，背景紙紋／格線也不再飄移
//  - 動的是「素材本身」：翻頁年曆（陰影、加速）、蠟燭點亮、蛋糕落定回彈、椅子被抽走、燈串閃兩下熄滅、戒指盒彈開、搖籃單擺衰減、
//    窗燈依序亮起帶光暈、碰杯、吊牌擺盪衰減；動作都有預備→主動作→過衝→回彈，物件之間錯開（時間點在 TM，音效讀同一份）
//  - 資料圖：長條彈性長出＋前緣光暈拖尾＋掃光、小人蹦出、數字減速滾動後停穩；數線針頭帶軌跡走過
//  - 片尾 LOGO：雲彈入→太陽衝出過衝→三道光啪啪啪→四字蓋印落下＋震動→收束光暈→標語／下一集／關鍵字滑入（OF，每個動作配一聲，同一幀）
// 其餘（進場緩動、轉場、字幕、出處）沿用 v3。renderAt(t) 只跟 t 有關、可重現。
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
const TR=5/30;                                              // 轉場長度＝4 幀（動畫導演：前後文字同框 ≤4 幀）
// 彈簧（阻尼振盪）：x 秒後的位置 0→1，z＝阻尼比（<1 會過衝），w＝角頻率
const SPR=(x,z,w)=>{z=z==null?.45:z;w=w||16;if(x<=0)return 0;const wd=w*Math.sqrt(1-z*z);return 1-Math.exp(-z*w*x)*(Math.cos(wd*x)+z*w/wd*Math.sin(wd*x))};
const OF={cloud:0,land:8,sun:10,apex:20,ray:[30,35,40],ch:[46,51,56,61],imp:4,fin:70,slog:78,next:85,kw:91,glint:118};   // v5：字蓋印只短落 4 幀（不穿過雲）；關鍵字 f91＝片尾 +3.03 秒，之後停 ≥2 秒；f118 起一次 ≤0.8 秒光掃   // 片尾動作的幀號（片尾第幾幀）                                               // 轉場長度（秒）
function T(x,y,s,fs,w,col,anchor,extra){return `<text x="${x}" y="${y}" text-anchor="${anchor||'middle'}" font-size="${fs}" font-weight="${w||400}" fill="${col||SUBC}" font-family="Noto Sans CJK TC" ${extra||''}>${esc(s)}</text>`}
const draw=(p)=>`pathLength="1" stroke-dasharray="1 2" stroke-dashoffset="${(1-clamp(p)).toFixed(4)}"${p<=.002?' stroke-opacity="0"':''}`;   // 手繪描線
// v4：不再有鏡頭推近；box 只負責固定外框（插圖面板圓角裁切），內容不縮放、不平移（vy＝viewBox 起點，只給 s1 婚紗店用來對齊）
function box(o,top,h,inner,lt,dur,co){const vy=(co&&co.vy)||0,cid='ck'+o+top;return `<div data-o="${o}" class="abs" style="left:96px;top:${top}px;width:888px;height:${h}px"><svg width="888" height="${h}" viewBox="0 ${vy} 888 ${h}" overflow="hidden"><defs><clipPath id="${cid}"><rect x="0" y="${vy}" width="888" height="${h}" rx="${o==='illus'?26:0}"/></clipPath></defs><g clip-path="url(#${cid})">${inner}</g></svg></div>`}
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
function wobbleRing(cx,cy,rx,ry,p,seed,n){n=n||2;let d='';const N=48,e=2/n;for(let i=0;i<=N;i++){const a=-2.2+i/N*Math.PI*2.16,w=1+.045*Math.sin(i*.9+seed)+.03*Math.sin(i*2.3+seed*2),c=Math.cos(a),sn=Math.sin(a);   // n＞2＝方一點的手繪圈（把文字完整框住，不壓筆畫）
 d+=(i?'L':'M')+(cx+rx*w*Math.sign(c)*Math.pow(Math.abs(c),e)).toFixed(1)+' '+(cy+ry*w*Math.sign(sn)*Math.pow(Math.abs(sn),e)).toFixed(1)}
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
  const bu=lt-.42,bdy=bu<=0?0:bu<.08?8*Math.pow(bu/.08,2):8*(1-SPR(bu-.08,.3,22));   // 0.42 起加速下壓 8px（0.5 觸底，同幀 pop 音）→ 彈簧回位（過衝約 −3px），位移非縮放   // 重音：0.45 起整個大字往下壓 ±7px 再回彈（位移，不是縮放）
  if(!o.hideBig)h+=`<div data-o="big" class="abs bignum" style="top:${(500+bdy).toFixed(1)}px">${esc(s.big)}</div>`;
  // 資料圖：全年結婚登記對數，2016→2025（以 0 為底的斜率線）
  const p=pr(lt,0,.5),base=168,k=104/160000,ya=base-s.trend.a*k,yb=base-s.trend.b*k,xa=480,xb=760,xe=xa+(xb-xa)*p,ye=ya+(yb-ya)*p;
  let g=T(0,62,s.label,40,700,TXT,'start')+T(0,118,'每點是一年的總數',32,400,SUBC,'start');
  g+=`<line x1="420" y1="${base}" x2="860" y2="${base}" stroke="${LINE}" stroke-width="2.5"/><line x1="${xa}" y1="${base}" x2="${xa}" y2="${ya}" stroke="${LINE}" stroke-width="2" stroke-dasharray="5 6" opacity=".6"/>`+
   `<line x1="${xa}" y1="${ya}" x2="${xe}" y2="${ye}" stroke="${LAMP}" stroke-width="10" stroke-linecap="round"/><circle cx="${xa}" cy="${ya}" r="15" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+
   (p>.98?`<line x1="${xb}" y1="${base}" x2="${xb}" y2="${yb}" stroke="${LINE}" stroke-width="2" stroke-dasharray="5 6" opacity=".6"/>`:'')+`<circle cx="${xe}" cy="${ye}" r="${15*settle(lt,.5)}" fill="${LAMP}"/>`;
  // 流動：線畫完後，光點沿 2016→2025 方向密集流過（拖尾 4 節），速度隨時間慢慢減下來
  if(lt>.5){const u0=lt-.5,ph=1.4/1.1*(1-Math.exp(-1.1*u0)),vel=1.4*Math.exp(-1.1*u0),fade=clamp(u0/.2);
   for(let j=0;j<12;j++){for(let k=0;k<5;k++){const u=((ph-k*.035*(.4+vel)+j/12)%1+1)%1,x=xa+(xb-xa)*u,y=ya+(yb-ya)*u;
    g+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(5.5-k).toFixed(1)}" fill="#FFF4D6" opacity="${(fade*(1-k*.2)*.9).toFixed(2)}"/>`}}}
  const lp=pr(lt,.55,.3);g+=`<g opacity="${lp}">${T(xa,ya-26,'14.8 萬對',36,700,TXT)}${T(xb,yb-26,'10.4 萬對',36,700,TXT)}${T(xa,base+36,'2016',32,400,SUBC)}${T(xb,base+36,'2025',32,400,SUBC)}</g>`;
  h+=box('chart',734,232,g,lt,d,{z:0});
  h+=box('illus',978,528,illBridal(lt),lt,d,{vy:24});
  return h},
 // s2／s3 資料從哪來：同一張「橫條＋小人群像」；s2 只長 2016，s3 長 2025＋缺掉的 4 萬多對畫成虛線小人
 bars(s,lt,d,o){
  let h=title(s.title,lt)+tag(s.tag,lt,.12,306);
  if(!o.hideChip&&s.chip){const k=o.chipIn==null?1:o.chipIn;h+=`<div data-o="chip" class="abs chip" style="opacity:${k}">${esc(s.chip)}</div>`}
  h+=box('illus',392,348,s.stage===1?illCounter(lt):illBanquet(lt),lt,d,{z:.05,px:8});
  h+=box('chart',756,730,chartPeople(s,lt),lt,d,{z:0});
  return h},
 versus(s,lt,d){
  let h=title(s.title,lt);
  h+=box('illus',310,330,illBoard(lt),lt,d,{z:.05,px:-8});
  const pa=pr(lt,.05,.4,BACK),pb=pr(lt,.55,.42,BACK);let g='';
  [[s.a,pa,false,0],[s.b,pb,true,452]].forEach(([c,p,hi,x])=>{const dy=(1-clamp(p))*50;
   g+=`<g opacity="${clamp(p*1.6)}" transform="translate(0,${dy})"><rect x="${x+8}" y="20" width="420" height="640" rx="28" fill="${hi?FACE3:FACE}" stroke="${hi?LAMP:LINE}" stroke-width="${hi?4:3}" ${hi?'':'stroke-dasharray="12 10"'}/>`+
   T(x+218,104,c.k,38,700,hi?HINT:SUBC)+c.lines.map((l,i)=>T(x+218,300+i*100,l,70,700,TXT)).join('')+T(x+218,610,c.foot,32,400,SUBC)+`</g>`});
  // 強調：螢光筆劃過「越來越晚」（本鏡唯一）
  const m=pr(lt,1.0,.4);g=`<rect x="${452+48}" y="${336}" width="${340*m}" height="56" rx="8" fill="${LAMP}" opacity=".28"/>`+g;
  g+=`<g opacity="${pr(lt,1.35,.3)}" transform="translate(0,${(1-pr(lt,1.35,.3))*16})">${T(444,752,s.mid,40,700,TXT)}</g>`;
  // 第二拍 1.9：從「說法」卡畫一條箭頭到「統計」卡（連線長出，不是縮放）；第三拍 2.8：「?」標在說法卡右上角（沒有統計支持）
  const ar=pr(lt,1.55,.5),ah=pr(lt,1.9,.2,BACK);
  if(ar>0)g+=`<path d="M300 500 C 380 470, 520 470, 590 500" fill="none" stroke="${LAMP}" stroke-width="7" stroke-linecap="round" ${draw(ar)}/><path d="M572 478 L596 502 L566 512" fill="none" stroke="${LAMP}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="${clamp(ah*2)}"/>`;
  const qb=SPR(lt-2.3,.4,16);if(qb>0)g+=`<g transform="translate(400,46) scale(${Math.max(.01,qb).toFixed(3)})" opacity="${clamp((lt-2.3)*12)}"><circle r="28" fill="${LAMP}"/>${T(0,14,'?',40,700,'#FFFFFF')}</g>`;
  h+=box('chart',668,832,g,lt,d,{z:0});
  return h},
 ruler(s,lt,d){
  let h=title(s.title,lt)+tag(s.tag,lt,.15,306);
  h+=box('illus',392,368,illCakes(lt),lt,d,{z:.05,px:10});
  const x0=70,x1=818,sx=v=>x0+(x1-x0)*(v-s.lo)/(s.hi-s.lo),ay=330;let g='';
  const rp=pr(lt,0,.45);g+=`<line x1="${x0}" y1="${ay}" x2="${x0+(x1-x0)*rp}" y2="${ay}" stroke="${LINE}" stroke-width="4"/>`;
  for(let v=s.lo;v<=s.hi;v++){const q=pr(lt,.04+(v-s.lo)*.06,.25);g+=`<g opacity="${q}"><line x1="${sx(v)}" y1="${ay-12}" x2="${sx(v)}" y2="${ay+12}" stroke="${LINE}" stroke-width="2"/>${T(sx(v),ay+56,String(v),32,400,SUBC)}</g>`}
  g+=`<g opacity="${pr(lt,.5,.3)}">${T(x1,ay+100,'歲',32,400,SUBC,'end')}</g>`;
  s.pins.forEach((m,i)=>{const a=.35+i*.5,p=pr(lt,a,.6),x=sx(s.lo+(m.v-s.lo)*p),up=i===0,lab=pr(lt,a+.55,.25,BACK),sc=settle(lt,a+.65),dot=16+5*DECAY(lt-a-.6,9,28);
   // 軌跡：針頭走過的軸線亮起、越靠近針頭越亮（拖尾），走完慢慢淡去
   if(p>.002){const tl=Math.min(x-x0,170),fa=lt<a+.7?1:clamp(1-(lt-a-.7)/.5);g+=`<line x1="${x0}" y1="${ay}" x2="${x}" y2="${ay}" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" opacity="${(.28*fa).toFixed(2)}"/><line x1="${x-tl}" y1="${ay}" x2="${x}" y2="${ay}" stroke="${LAMP}" stroke-width="9" stroke-linecap="round" opacity="${(.55*fa).toFixed(2)}"/>`}
   if(m.hi){const gl=pr(lt,a+.7,.4);g+=glow(x,up?ay-182:ay+236,120,gl*.8)}   // 強調：33.4 光暈（本鏡唯一；落定後靜止，不呼吸）
   g+=`<g opacity="${clamp(p*4)}"><circle cx="${x}" cy="${ay}" r="${dot.toFixed(1)}" fill="${m.hi?LAMP:FACE3}" stroke="${LINE}" stroke-width="3"/>`+
    `<line x1="${x}" y1="${ay+(up?-16:16)}" x2="${x}" y2="${up?ay-90:ay+110}" stroke="${LINE}" stroke-width="2"/></g>`+
    `<g opacity="${clamp(lab)}" transform="translate(${x},${up?ay-150:ay+216}) scale(${(sc*(.85+.15*lab)).toFixed(3)})">${T(0,up?-20:64,(s.lo+(m.v-s.lo)*p).toFixed(1)+' 歲',70,700,TXT)}${T(0,up?40:-22,m.lab,38,400,TXT)}</g>`});
  h+=box('chart',790,710,g,lt,d,{z:0});
  return h},
 card(s,lt,d){
  let h=title(s.title,lt)+tag(s.tag,lt,.15,306);
  h+=box('illus',392,368,illCradle(lt),lt,d,{z:.05,px:-10});
  const c=s.card,cp=pr(lt,0,.4,BACK),val=c.to*EO((lt-.15)/.95),sc=settle(lt,.9);
  let g=`<g opacity="${clamp(cp*1.5)}" transform="translate(444,250) scale(${(.92+.08*cp).toFixed(3)}) translate(-444,-250)"><rect x="64" y="20" width="760" height="460" rx="32" fill="${FACE3}" stroke="${LAMP}" stroke-width="4"/>`+T(444,120,c.lab,48,400,TXT)+`</g>`;
  const gl=pr(lt,.95,.35)*.8;g+=glow(444,300,250,gl);   // 強調：0.695 光暈（本鏡唯一）
  g+=`<g transform="translate(444,370) scale(${sc.toFixed(3)})">${T(0,0,(c.pre||'')+Math.max(0,val).toFixed(c.dec)+(c.unit||''),190,700,TXT)}</g>`;
  const bx=124,bw=640,by=560,bp=pr(lt,.3,.9);
  g+=`<g opacity="${pr(lt,.2,.3)}"><rect x="${bx}" y="${by}" width="${bw}" height="44" rx="6" fill="none" stroke="${LINE}" stroke-width="2"/><rect x="${bx}" y="${by}" width="${bw*c.to*bp}" height="44" rx="6" fill="${LAMP}" opacity=".85"/>${bp<.999?glow(bx+bw*c.to*bp,by+22,56,.7*(1-bp)):''}`+
   `<line x1="${bx+bw*.7}" y1="${by-14}" x2="${bx+bw*.7}" y2="${by+48}" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6"/>`+T(bx,by+98,'0',36,400,SUBC,'start')+T(bx+bw,by+98,'1',36,400,SUBC,'end')+`</g>`+
   `<g opacity="${pr(lt,1.1,.3)}">${T(bx+bw*.7,by+98,c.ref,38,700,TXT)}</g>`;
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
  const p=pr(lt,.05,.45,BACK),rows=[0,1,2,3,4];
  let g=`<g opacity="${clamp(p*1.5)}" transform="translate(444,340) scale(${(.9+.1*p).toFixed(3)}) translate(-444,-340)"><rect x="104" y="40" width="680" height="560" rx="22" fill="${FACE}" stroke="${LINE}" stroke-width="3" stroke-dasharray="12 10"/>`+
   `<rect x="104" y="40" width="680" height="84" rx="22" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,96,s.slip,38,700,TXT)+`</g>`;
  rows.forEach(i=>{const q=pr(lt,.35+i*.09,.3);g+=`<g opacity="${q}">${i===0?T(160,236,s.row,36,400,TXT,'start'):''}<line x1="160" y1="${270+i*70}" x2="${160+(i===0?560:i%2?420:500)*q}" y2="${270+i*70}" stroke="${LINE}" stroke-width="2" opacity="${i?.35:.55}"/></g>`});
  const qm=.7+.3*SPR(lt-.55,.4,16);g+=`<g transform="translate(700,238) scale(${qm.toFixed(3)})">${T(0,0,'?',84,700,HINT,'end')}</g>`;
  g+=wobbleRing(668,212,70,62,pr(lt,.8,.5),3);    // 強調：圈住「?」（本鏡唯一）
  h+=box('chart',790,660,g,lt,d,{z:0});
  return h},
 // 片尾 v5（5.0 秒＝150 幀；OF＝片尾第幾幀；音效 window.sfxEvents 讀同一份 OF，聲音與動作同一幀）：
 //   版面（美編）：整組垂直置中，LOGO 放大 1.15 倍（scale 2.0）；LOGO 底 → 四字之間留 ≥24px 淨空帶（動畫導演：四字不准與雲相交，逐幀檢查 data-chk）
 //   f0 雲彈入 → f8 落地壓扁 → f10 太陽衝出、f20 過頂點 → f30／35／40 三道光「啪」→ f46／51／56／61 四字蓋印（短落 4 幀＋壓扁＋整組輕震，不穿過雲）
 //   → f70 收束光暈＋掃光＋完成音 → f78 標語、f85 下一集、f91 留言關鍵字（橘底白字膠囊）→ f118 起一次 ≤0.8 秒光掃（太陽弧與四字）→ 靜止
 outro(s,lt,d){
  const f=lt*30,P=(a,n,fn)=>(fn||EO)((f-a)/n),SC2=2.0,MY=681,BASE=1092;
  const fin=f-OF.fin,flash=fin>=0?Math.exp(-fin/8):0;
  const rise=P(OF.cloud,OF.land-OF.cloud,x=>1-Math.pow(1-x,3)),lu=(f-OF.land)/30;
  let cy=(1-rise)*620,csy=1+.12*Math.sin(Math.PI*clamp(f/OF.land)),csx=1-.08*Math.sin(Math.PI*clamp(f/OF.land));
  if(f>=OF.land){const q=.17*DECOS(lu,9,30);csy=1-q;csx=1+.7*q;cy=-12*Math.max(0,DECAY(lu,7,20))}
  const C='M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z',A='M -26.3 -78.5 A 110 110 0 0 1 170.1 13.1',cx=63.9,cy0=-15.5;
  const su=(f-OF.sun)/30,sy=(1-SPR(su,.4,9))*90,sop=clamp((f-OF.sun)/3);
  let rays='';[-135,-90,-45].forEach((a,i)=>{const u=f-OF.ray[i];if(u<0)return;const ra=a*Math.PI/180,r0=140,r1=184,p=BACK(u/7),re=r0+(r1-r0)*Math.min(p,1.12),wd=22+10*Math.exp(-u/3)+6*flash,ex=cx+re*Math.cos(ra),ey=cy0+re*Math.sin(ra);
   rays+=`<line x1="${cx+r0*Math.cos(ra)}" y1="${cy0+r0*Math.sin(ra)}" x2="${ex}" y2="${ey}" stroke="#C5782B" stroke-width="${wd.toFixed(1)}" stroke-linecap="round"/>`;
   if(u<14){const k=u/14,s0=34*Math.sin(Math.PI*clamp(u/9));rays+=sparkle(cx+(r1+16)*Math.cos(ra),cy0+(r1+16)*Math.sin(ra),s0,1-k);
    for(let q=0;q<5;q++){const da=ra+(q-2)*.42,dist=r1+10+(18+q*5)*EO(k);rays+=`<circle cx="${(cx+dist*Math.cos(da)).toFixed(1)}" cy="${(cy0+dist*Math.sin(da)).toFixed(1)}" r="${(5*(1-k)).toFixed(1)}" fill="#F4B860" opacity="${(.9*(1-k)).toFixed(2)}"/>`}}});
  const rf=[0,1,2].reduce((a,i)=>a+(f>=OF.ray[i]?Math.exp(-(f-OF.ray[i])/5):0),0);
  const gu=(f-OF.glint)/24;      // 靜止段光掃（≤0.8 秒）：一點亮光沿太陽弧走過，四字同時被掃過一次
  const glintArc=gu>0&&gu<1?`<path d="${A}" pathLength="1" fill="none" stroke="#FFF3D0" stroke-width="14" stroke-linecap="round" stroke-dasharray="0.16 3" stroke-dashoffset="${(-(gu*.86)).toFixed(3)}" opacity="${(.95*Math.sin(Math.PI*gu)).toFixed(2)}"/>`:'';
  let shx=0,shy=0;[0,1,2,3].forEach(i=>{const u=f-(OF.ch[i]+OF.imp);if(u>=0&&u<14){const am=4.5*Math.exp(-u/3.2);shx+=am*Math.sin(u*2.2);shy+=am*.6*Math.cos(u*2.9)}});
  const sunG=`<g transform="translate(${cx},${cy0+sy}) translate(0,0)" opacity="${sop}"><g transform="translate(${-cx},${-cy0})"><path d="${A}" fill="none" stroke="#C5782B" stroke-width="${(22+4*flash+3*rf).toFixed(1)}" stroke-linecap="round"/>${glintArc}${rays}</g></g>`;
  let g=DEFS;
  g+=glow(444,760,Math.min(440,120+320*EO(fin/16)),fin<0?0:Math.min(.5,.12+.45*Math.exp(-fin/12)));
  g+=glow(444+SC2*(cx-35),MY+SC2*(cy0-40+sy),300,.2*sop*clamp((f-OF.sun)/8)+.16*rf+.45*flash);
  g+=`<g transform="translate(${shx.toFixed(1)},${shy.toFixed(1)})">`;
  g+=`<g transform="translate(444,${MY}) scale(${SC2}) translate(-35,-40)"><g data-chk="logo">${sunG}<g transform="translate(15,${120+cy/SC2}) scale(${csx.toFixed(3)},${csy.toFixed(3)}) translate(-15,-120)"><path d="${C}" fill="${FACE3}" stroke="#6E6A66" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/></g></g></g>`;
  const chars=[['談','#2F2D2B'],['晴','#98622B'],['說','#2F2D2B'],['礙','#8A5A44']];let tx='';
  chars.forEach((c,i)=>{const u=f-OF.ch[i];if(u<0)return;const x=444+(i-1.5)*196,k=clamp(u/OF.imp);let y=BASE-28*(1-k*k),ssy=1.10-.10*k,ssx=1-.05*k;
   if(u>OF.imp){const us=(u-OF.imp)/30,q=.24*DECOS(us,11,32);ssy=1-q;ssx=1+.6*q;y=BASE}
   const sc=fin>=0?1+.05*Math.exp(-fin/6):1;
   tx+=`<g transform="translate(${x},${y.toFixed(1)}) scale(${(ssx*sc).toFixed(3)},${(ssy*sc).toFixed(3)})" opacity="${clamp(u/2)}"><text x="0" y="0" text-anchor="middle" font-family="Noto Serif CJK TC" font-weight="700" font-size="172" fill="${c[1]}">${c[0]}</text><rect data-chk="char" x="-86" y="-150" width="172" height="164" fill="none"/></g>`;
   const iu=u-OF.imp;if(iu>0){const r=EO(iu/12);if(r<1){g+=`<ellipse cx="${x}" cy="${BASE+22}" rx="${(34+80*r).toFixed(1)}" ry="${(7+10*r).toFixed(1)}" fill="none" stroke="#C5782B" stroke-width="3" opacity="${(.45*(1-r)).toFixed(2)}"/>`;
    [-1,1].forEach(sg=>g+=`<circle cx="${(x+sg*(40+46*r)).toFixed(1)}" cy="${(BASE+16-14*Math.sin(Math.PI*r)).toFixed(1)}" r="${(5*(1-r)).toFixed(1)}" fill="#C5782B" opacity="${(.5*(1-r)).toFixed(2)}"/>`)}}});
  g+=tx;
  const sweep=(p0,span,t0)=>{const k=(f-t0)/span;if(k<=0||k>=1)return'';const sx=-160+1260*EO(k);return `<clipPath id="txc${t0}">${chars.map((c,i)=>`<text x="0" y="0" text-anchor="middle" transform="translate(${444+(i-1.5)*196},${BASE})" font-family="Noto Serif CJK TC" font-weight="700" font-size="172">${c[0]}</text>`).join('')}</clipPath><g clip-path="url(#txc${t0})"><path d="M${sx} ${BASE-170} l90 0 l-50 240 l-90 0Z" fill="#FFF4D6" opacity="${p0}"/></g>`};
  g+=sweep(.75,14,OF.fin)+sweep(.6,24,OF.glint);
  g+=`</g>`;
  const sl=P(OF.slog,10);if(sl>0)g+=`<g opacity="${sl}" transform="translate(${(1-sl)*-50},0)">${T(444,1180,s.slogan,44,400,SUBC)}</g>`;
  const nx=P(OF.next,12,BACK);if(nx>0)g+=`<g opacity="${clamp(nx*2)}" transform="translate(${(1-nx)*70},0)"><rect x="84" y="1214" width="720" height="88" rx="44" fill="${FACE}" stroke="${LINE}" stroke-width="2.5"/>${T(444,1274,s.nextLine,42,700,TXT)}</g>`;
  if(s.keyword){const kw=P(OF.kw,12,BACK);if(kw>0)g+=`<g opacity="${clamp(kw*2)}" transform="translate(444,1388) scale(${(.8+.2*kw).toFixed(3)}) translate(-444,-1388)"><rect x="104" y="1342" width="680" height="92" rx="46" fill="#C5782B"/><text x="444" y="1406" text-anchor="middle" font-family="Noto Sans CJK TC" font-weight="700" font-size="46" fill="#FFFFFF">留言「<tspan font-size="58" font-weight="900">${esc(s.keyword)}</tspan>」拿完整資料</text></g>`}
  return box('mark',150,1540,g,lt,d,{})}
};

// ───────── 情境插圖（本篇量身，素材登記見 素材登記.md）─────────
// v4 動畫原則（Andy 11-15「不要出現圖片一直慢慢放大」）：插圖面板固定不縮放、不平移；只有「物件」在動——
//   預備動作（反向一點點）→ 主動作 → 過衝 → 阻尼回彈；多個物件錯開（stagger）；擺盪一律指數衰減後靜止（不一直擺、不一直閃）。
//   時間點全部放在 TM，畫面與音效（sfxEvents）讀同一份，所以聲音與動作同一幀。
const DECAY=(x,k,w)=>x<=0?0:Math.exp(-k*x)*Math.sin(w*x);      // 衰減擺盪（先正向）
const DECOS=(x,k,w)=>x<=0?0:Math.exp(-k*x)*Math.cos(w*x);      // 衰減擺盪（從最大振幅放手）
const FDUR=[.2,.17,.14,.12,.11,.11,.12,.14,.2],FST=[];{let a=.45;FDUR.forEach(d=>{FST.push(+a.toFixed(3));a+=d})}
const TM={
 bridal:{off:[.6,.95,1.3],box:1.55},
 counter:{stamp:.95,slide:.3},
 banquet:{pull:[.55,.83,1.11]},
 board:{flip:[[.45,.53],[.85,.93]]},
 cakes:{flip:FST,flipEnd:+(FST[8]+FDUR[8]).toFixed(3),land:[1.55,1.8],light:[2.2,2.3,2.45,2.55]},
 cradle:{push:.4,shoe:[.6,.8],lamp:1.25},
 tea:{win:b=>.45+b*.26,clink:1.0},
 badge:{case:.4,sign:.55,chev:.9,swing:.45}
};
// ── 婚紗店（s1）：燈串逐顆「閃兩下」熄滅、整間店變暗；戒指盒預備下壓→彈跳→蓋子過衝彈開→戒指升起、閃光依序爆開 ──
function bulbOn(t,toff){const u=t-toff;if(u<0)return 1;if(u<.07)return .15;if(u<.14)return 1;if(u<.2)return .1;if(u<.26)return .65;return 0}
function illBridal(t){   // v5：美編 A1——夜景改黃昏（暖米→淡桃天空、陶土棕剪影），亮度不壓過標題
 let g=DEFS+`<defs><linearGradient id="dsk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6E2C6"/><stop offset=".6" stop-color="#F3CFA6"/><stop offset="1" stop-color="#EDBE92"/></linearGradient></defs><rect x="0" y="0" width="888" height="552" rx="28" fill="url(#dsk)"/>`;
 g+=`<circle cx="800" cy="104" r="46" fill="#F4B860" opacity=".75"/><circle cx="800" cy="104" r="70" fill="#F4B860" opacity=".16"/>`;
 [[20,160,110,260],[140,120,90,300],[640,140,100,280],[748,180,120,240]].forEach(([x,y,w,hh],b)=>{g+=`<rect x="${x}" y="${y}" width="${w}" height="${hh}" fill="${b%2?'#A9785A':'#B88866'}"/>`;
  for(let r=0;r<5;r++)for(let c=0;c<3;c++){const on=Math.sin(b*7.1+r*3.3+c*5.7)>-.2;g+=`<rect x="${x+10+c*(w-20)/3}" y="${y+16+r*42}" width="${(w-20)/3-10}" height="22" rx="2" fill="${on?'#FFF1D2':'#8E6248'}" opacity="${on?.85:.5}"/>`}});
 g+=`<rect x="70" y="190" width="520" height="350" fill="${FACE}" stroke="${LINE}" stroke-width="4"/>`;
 let aw='';for(let i=0;i<8;i++){const x=70+i*65;aw+=`<path d="M${x} 190 h65 v44 a32.5 18 0 0 1 -65 0Z" fill="${i%2?FACE3:'#E9B98A'}" stroke="${LINE}" stroke-width="3"/>`}g+=aw;
 g+=`<rect x="250" y="148" width="160" height="44" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(330,182,'婚紗',32,700,TXT);
 g+=`<rect x="104" y="268" width="452" height="252" rx="6" fill="#F7E7CB" stroke="${LINE}" stroke-width="4"/>`;
 // 燈串：最後三顆各閃兩下後熄滅；每熄一顆，整間店暗一階
 const offs=TM.bridal.off;let dark=0;offs.forEach(o=>dark+=.075*(1-bulbOn(t,o)>0?clamp((t-o)/.26):0));
 let wire=`<path d="M118 284 Q 330 318 542 284" stroke="${LINE}" stroke-width="2" fill="none"/>`;
 for(let i=0;i<10;i++){const x=128+i*45,y=284+34*(1-Math.pow((x-330)/212,2))*0.5+4,on=i>=7?bulbOn(t,offs[i-7]):1;
  if(on>0)wire+=glow(x,y+6,22+14*(on>.99?0:on),on*.62);wire+=`<circle cx="${x}" cy="${y+6}" r="7" fill="${on>.5?'#F4B860':'#B9B2A8'}" stroke="${LINE}" stroke-width="1.5"/>`}
 g+=wire+`<rect x="104" y="268" width="452" height="252" fill="#6E5240" opacity="${(dark*.8).toFixed(3)}"/>`;
 // 人台＋白紗：燈熄的瞬間被風帶起，衰減擺盪
 const sw=4*DECAY(t-.1,.9,6.5)+7*DECAY(t-offs[0],1.3,7.5)+5*DECAY(t-offs[2],1.3,7.5);
 g+=`<line x1="330" y1="500" x2="330" y2="520" stroke="${LINE}" stroke-width="4"/><path d="M300 520 h60" stroke="${LINE}" stroke-width="4"/>`+
  `<path d="M312 330 q18 -12 36 0 l8 50 q-26 10 -52 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+
  `<path d="M304 380 q26 12 52 0 l46 120 q-72 16 -144 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+
  `<path d="M330 318 q${(-50+sw).toFixed(1)} 40 ${(-64+sw*2.4).toFixed(1)} 150" stroke="${LINE}" stroke-width="2" fill="none" opacity=".45"/><circle cx="330" cy="316" r="7" fill="${FACE3}" stroke="${LINE}" stroke-width="2"/>`;
 g+=`<path d="M130 496 l20 -40 l20 40Z M490 496 l20 -40 l20 40Z" fill="#E9D9BF" stroke="${LINE}" stroke-width="2"/>`;
 g+=glow(838,128,70,.7)+`<line x1="838" y1="140" x2="838" y2="540" stroke="#8A6A52" stroke-width="6"/><path d="M818 122 h40 l-8 18 h-24Z" fill="#FFF1D2" stroke="#8A6A52" stroke-width="2"/>`;
 // 戒指盒：1.45 預備下壓 → 1.55 彈跳 → 蓋子過衝彈開（−92°，最大約 −118°）→ 戒指升起（過衝回彈）→ 閃光 1.8／1.88／1.96 依序爆開後淡去
 const b0=TM.bridal.box,pre=t>b0-.12&&t<b0?Math.sin(Math.PI*clamp((t-(b0-.12))/.12))*.09:0,hop=t>=b0?-14*Math.sin(Math.PI*clamp((t-b0)/.2)):0;
 const lid=-92*SPR(t-(b0+.03),.34,17)+5*DECAY(t-2.1,6,28),ry=-30*SPR(t-(b0+.16),.45,13),rr=14*DECAY(t-(b0+.16),5,16);
 g+=`<g transform="translate(0,${hop.toFixed(1)}) translate(720,540) scale(${(1+pre*.5).toFixed(3)},${(1-pre).toFixed(3)}) translate(-720,-540)">`+
  `<rect x="640" y="452" width="160" height="88" rx="6" fill="${FACE}" stroke="${LINE}" stroke-width="3"/>`+
  `<rect x="668" y="406" width="104" height="48" rx="8" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><rect x="680" y="414" width="80" height="20" rx="6" fill="#6E4636"/>`+
  `<g transform="translate(0,${ry.toFixed(1)}) rotate(${rr.toFixed(1)} 720 414)"><circle cx="708" cy="414" r="15" fill="none" stroke="#F4B860" stroke-width="6"/><circle cx="730" cy="414" r="15" fill="none" stroke="#FFFDF8" stroke-width="6"/></g>`+
  `<g transform="translate(668,406) rotate(${lid.toFixed(1)}) translate(-668,-406)"><rect x="668" y="384" width="104" height="24" rx="8" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/></g></g>`;
 [[700,370,0],[744,376,.08],[722,352,.16]].forEach(([x,y,d])=>{const u=t-(b0+.25+d);if(u<0)return;g+=sparkle(x,y,13*Math.min(1.25,SPR(u,.5,22)),clamp(1-(u-.2)/.5))});
 g+=`<line x1="0" y1="540" x2="888" y2="540" stroke="#8A6A52" stroke-width="3" opacity=".5"/>`;
 return g}
// ── 戶政櫃台（s2）：登記書從右滑入（微過衝）、印章落下→壓扁→「受理」章過衝落定＋墨暈擴散、桌面震一下；時鐘秒針一格一格走 ──
function illCounter(t){
 let g=`<rect x="0" y="0" width="888" height="348" rx="26" fill="${FACE}"/>`;
 g+=`<rect x="300" y="18" width="288" height="52" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,54,'戶政事務所',32,700,TXT);
 const sec=(Math.floor(t)+SPR(t%1,.45,40))*6*Math.PI/180,mn=(40+t*.5)*Math.PI/180;
 g+=`<circle cx="790" cy="92" r="52" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`;for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${790+42*Math.cos(a)}" y1="${92+42*Math.sin(a)}" x2="${790+48*Math.cos(a)}" y2="${92+48*Math.sin(a)}" stroke="${LINE}" stroke-width="2"/>`}
 g+=`<line x1="790" y1="92" x2="${790+26*Math.sin(mn)}" y2="${92-26*Math.cos(mn)}" stroke="${TXT}" stroke-width="5" stroke-linecap="round"/><line x1="790" y1="92" x2="${790+40*Math.sin(sec)}" y2="${92-40*Math.cos(sec)}" stroke="${LAMP}" stroke-width="3" stroke-linecap="round"/><circle cx="790" cy="92" r="5" fill="${TXT}"/>`;
 const lw=5*DECAY(t-.5,1.4,6.5)+4*DECAY(t-2.9,1.4,6.5);g+=`<path d="M86 236 h64 l-8 -44 h-48Z" fill="#C98F5E" stroke="${LINE}" stroke-width="3"/>`+
  `<path d="M118 192 q${-30+lw} -40 ${-40+lw*1.4} -84" stroke="#7E8F6A" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M118 192 q${24+lw} -50 ${30+lw*1.4} -100" stroke="#8FA078" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M118 192 q${4+lw} -30 ${2+lw*1.4} -66" stroke="#7E8F6A" stroke-width="10" fill="none" stroke-linecap="round"/>`;
 g+=`<rect x="0" y="236" width="888" height="112" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><rect x="0" y="226" width="888" height="16" fill="${DARK}" stroke="${LINE}" stroke-width="3"/>`;
 const bh=t>2.0?-16*Math.abs(Math.sin(Math.PI*clamp((t-2.0)/.5)))*Math.exp(-(t-2.0)*2):0;   // 第二拍 2.0 秒：櫃台鈴跳一下
 g+=`<g transform="translate(0,${bh.toFixed(1)})"><path d="M640 226 a26 20 0 0 1 52 0Z" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><rect x="662" y="196" width="8" height="12" fill="${LINE}"/></g>`;
 const ts=TM.counter.stamp,fx=660*(1-SPR(t-TM.counter.slide,.8,12)),jolt=6*DECAY(t-ts,12,34),fr=3*(1-SPR(t-TM.counter.slide,.8,12));
 g+=`<g transform="translate(${fx.toFixed(1)},${jolt.toFixed(1)}) rotate(${fr.toFixed(2)} 418 226)"><rect x="300" y="104" width="236" height="122" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(418,140,'結婚登記書',32,700,TXT)}`+
  `<line x1="322" y1="160" x2="512" y2="160" stroke="${LINE}" stroke-width="2" opacity=".5"/><line x1="322" y1="184" x2="470" y2="184" stroke="${LINE}" stroke-width="2" opacity=".5"/><line x1="322" y1="206" x2="440" y2="206" stroke="${LINE}" stroke-width="2" opacity=".5"/>`;
 const mu=t-ts;if(mu>0){const sc=1+.6*(1-SPR(mu,.5,22)),rp=EO(mu/.38);
  g+=`<circle cx="486" cy="190" r="${(36+40*rp).toFixed(1)}" fill="none" stroke="${LAMP}" stroke-width="${(5*(1-rp)+1).toFixed(1)}" opacity="${(.55*(1-rp)).toFixed(2)}"/>`+
   `<g transform="translate(486,190) scale(${sc.toFixed(3)}) rotate(-8)" opacity="${clamp(mu*14)}"><circle r="36" fill="none" stroke="${LAMP}" stroke-width="4"/>${T(0,11,'受理',32,700,LAMP)}</g>`}
 g+=`</g>`;
 // 印章：0.5 起從上方加速落下（ease-in）→ 0.8 觸桌壓扁 → 0.92 彈起離開
 if(t>ts-.35&&t<ts+.5){const dn=clamp((t-(ts-.3))/.3),sy=t<ts?-130+120*dn*dn:-10-120*EO((t-(ts+.12))/.3),sq=t>=ts&&t<ts+.12?.14*Math.sin(Math.PI*(t-ts)/.12):0;
  g+=`<g transform="translate(486,${150+sy}) translate(0,-6) scale(${(1+sq*.6).toFixed(3)},${(1-sq).toFixed(3)}) translate(0,6)" opacity="${t<.5?pr(t,ts-.35,.05):1}"><rect x="-12" y="-70" width="24" height="44" rx="8" fill="#8A5A44"/><rect x="-26" y="-30" width="52" height="24" rx="6" fill="#6E4636"/></g>`}
 return g}
// ── 喜宴圓桌（s3）：十個座位，最後三張椅子被抽走——先往桌子微縮（預備）→ 加速拉出去＋旋轉、帶速度殘影 → 淡出，原位留虛線空位 ──
function illBanquet(t){
 let g=`<rect x="0" y="0" width="888" height="348" rx="26" fill="${FACE}"/>`;
 const wv=(i)=>3*DECAY(t-.08-i*.03,.9,6);
 let fl=`<path d="M20 26 Q 444 ${80+4*wv(6)} 868 26" stroke="${LINE}" stroke-width="2" fill="none"/>`;
 for(let i=0;i<13;i++){const x=50+i*64,y=26+(80-26)*(1-Math.pow((x-444)/424,2))*0.5,r=9*DECAY(t-.06-i*.035,1.0,7);fl+=`<path d="M${x-14} ${y} h28 l-14 ${30}Z" fill="${i%3===0?'#E9B98A':i%3===1?FACE3:'#D8C3A5'}" stroke="${LINE}" stroke-width="2" transform="rotate(${r.toFixed(1)} ${x} ${y})"/>`}
 g+=fl;
 const cx=290,cy=210,R=86;g+=`<circle cx="${cx}" cy="${cy}" r="${R}" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><circle cx="${cx}" cy="${cy}" r="${R-16}" fill="none" stroke="${LINE}" stroke-width="2" stroke-dasharray="4 8" opacity=".6"/>`;
 g+=`<circle cx="${cx}" cy="${cy}" r="20" fill="#E9B98A" stroke="${LINE}" stroke-width="2"/>`;for(let i=0;i<5;i++){const a=i*72*Math.PI/180+.4;g+=`<circle cx="${cx+14*Math.cos(a)}" cy="${cy+14*Math.sin(a)}" r="7" fill="${FACE3}" stroke="${LINE}" stroke-width="1.5"/>`}
 for(let i=0;i<10;i++){const a=(-90+i*36)*Math.PI/180,dx=Math.cos(a),dy=Math.sin(a),x=cx+(R+30)*dx,y=cy+(R+30)*dy,p=pr(t,.02+i*.06,.25,BACK);
  if(y+16>346)continue;
  const tp=i>=7?TM.banquet.pull[i-7]:99,u=t-tp;let off=0,rot=0,op=1,ghost=0,trail=0;
  if(i>=7&&u>0){if(u<.1)off=-6*EO(u/.1);else{const k=clamp((u-.1)/.26);off=-6+66*k*k;rot=28*k;trail=k<1?k:0;op=1-clamp((u-.26)/.22)}ghost=EO((u-.2)/.3)}
  if(trail>0){for(let s=1;s<=3;s++)g+=`<line x1="${(x+dx*off).toFixed(1)}" y1="${(y+dy*off).toFixed(1)}" x2="${(x+dx*(off-s*16)).toFixed(1)}" y2="${(y+dy*(off-s*16)).toFixed(1)}" stroke="${LINE}" stroke-width="${(5-s).toFixed(1)}" stroke-linecap="round" opacity="${(.4*trail*(1-s*.25)).toFixed(2)}" transform="translate(0,${(s-2)*8})"/>`}
  if(ghost>0)g+=`<g transform="translate(${x},${y}) rotate(${i*36})" opacity="${(.55*ghost).toFixed(2)}"><rect x="-20" y="-14" width="40" height="28" rx="8" fill="none" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 5"/></g>`;
  if(op>0.01)g+=`<g transform="translate(${(x+dx*off).toFixed(1)},${(y+dy*off).toFixed(1)}) rotate(${(i*36+rot).toFixed(1)}) scale(${(.6+.4*p).toFixed(3)})" opacity="${(clamp(p*2)*op).toFixed(3)}"><rect x="-20" y="-14" width="40" height="28" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/></g>`}
 // 氣球由下方升起（微過衝）、禮物彈出（壓扁拉長）
 const rise=(1-SPR(t,.5,10))*140,by=3*Math.sin(t*2)*clamp(t/.8);
 g+=`<path d="M640 ${150+by+rise} q-6 70 10 140" stroke="${LINE}" stroke-width="2" fill="none"/><path d="M700 ${140-by+rise} q10 70 -20 150" stroke="${LINE}" stroke-width="2" fill="none"/>`+
  `<ellipse cx="640" cy="${118+by+rise}" rx="34" ry="40" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><ellipse cx="702" cy="${108-by+rise}" rx="34" ry="40" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
 const gp=SPR(t-.3,.38,16);
 g+=`<g transform="translate(808,250) scale(${(1+(1-Math.min(1.1,gp))*.2).toFixed(3)},${(Math.max(0,gp)).toFixed(3)}) translate(-808,-250)" opacity="${clamp((t-.3)*8)}"><rect x="760" y="170" width="96" height="80" rx="6" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><rect x="802" y="170" width="12" height="80" fill="${LAMP}" opacity=".8"/><path d="M808 170 q-30 -34 -36 -6 q14 8 36 6 q30 -34 36 -6 q-14 8 -36 6" fill="none" stroke="${LAMP}" stroke-width="4"/></g>`;
 g+=T(884,336,'10 席空 3 席（示意）',32,400,SUBC,'end');
 return g}
// 橫條＋小人群像：每個小人（成對）＝1 萬對；長條帶彈性長出（微過衝）＋前緣光暈拖尾＋長完掃過一道高光；小人逐個「蹦」出（壓扁拉長）；數值減速滾動後停穩
function couple(x,y,c,dash,op,sy){const st=dash?`stroke-dasharray="4 4"`:'';const f=dash?'none':c;sy=sy==null?1:sy;const sx=1+Math.min(.12,Math.max(0,(1-sy))*.45);
 return `<g transform="translate(${x+20},${y+46}) scale(${sx.toFixed(3)},${Math.max(.01,sy).toFixed(3)}) translate(-20,-46)" opacity="${op.toFixed(3)}"><circle cx="11" cy="10" r="8" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/><path d="M2 46 v-18 q9 -10 18 0 v18Z" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/>`+
  `<circle cx="29" cy="12" r="7" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/><path d="M21 46 v-16 q8 -9 16 0 v16Z" fill="${f}" stroke="${LINE}" stroke-width="2" ${st}/></g>`}
function chartPeople(s,lt){
 const X0=150,L=680,k=L/s.vmax;let g=T(0,40,s.unit,32,400,SUBC,'start');
 const legend=pr(lt,.2,.3);g+=`<g opacity="${legend}">${couple(694,2,FACE3,false,1)}${T(888,40,'＝1 萬對',32,700,TXT,'end')}</g>`;
 const BH=72;
 s.bars.forEach((b,i)=>{const y=160+i*280,ga=s.stage===1?(i===0?.05:-1):(i===0?-1:.05),grow=ga<0?(s.stage===1?0:1):SPR(lt-ga,.78,11);
  const fillc=b.hi?LAMP:'#D2A57C',pc=b.hi?'#F0B87E':'#E6CBAA';   // 2016 實心陶土淡棕、2025 實心橘（兩條都填滿，不再是空框）
  g+=T(0,y+52,b.lab,40,700,TXT,'start');
  if(grow<=0){const gh=clamp((lt-.5)/.3);if(gh>0){for(let j=0;j<11;j++)g+=couple(X0+j*46,y+BH+24,'',true,gh*.45,1);g+=`<ellipse cx="426" cy="668" rx="330" ry="50" fill="none" stroke="${LINE}" stroke-width="3" stroke-dasharray="12 10" opacity="${(.4*gh).toFixed(2)}"/><g opacity="${(.55*gh).toFixed(2)}">${T(426,684,'還剩多少？',46,700,SUBC)}</g>`}
   const qs=lt>2.9?1+.22*Math.sin(Math.PI*clamp((lt-2.9)/.45))*Math.exp(-(lt-2.9)*1.5):1,cxq=X0+b.v*k/2;   // 第二拍：2.9 秒「?」彈一下
   g+=`<rect x="${X0}" y="${y}" width="${b.v*k}" height="${BH}" rx="8" fill="none" stroke="${LINE}" stroke-width="2.4" stroke-dasharray="10 8" opacity=".5"/><g transform="translate(${cxq},${y+36}) scale(${qs.toFixed(3)}) translate(${-cxq},${-(y+36)})">`+T(cxq,y+52,'?',48,700,SUBC)+`</g>`;return}
  const w=b.v*k*Math.max(0,grow);
  g+=`<clipPath id="bc${i}"><rect x="${X0}" y="${y}" width="${b.v*k*1.03}" height="${BH}" rx="8"/></clipPath><rect x="${X0}" y="${y}" width="${w}" height="${BH}" rx="8" fill="${fillc}" stroke="${b.hi?LAMP:LINE}" stroke-width="2.4"/>`;
  if(ga>=0){const gu=lt-ga;
   if(gu<.8)g+=glow(X0+w,y+BH/2,50,.55*(1-clamp(gu/.8)));
   [.75,2.9].forEach(t0=>{const sh=(lt-ga-t0+.05*0)/.55;if(sh>0&&sh<1){const sx=X0+(b.v*k+60)*INOUT(sh)-40;g+=`<g clip-path="url(#bc${i})"><path d="M${sx} ${y} l30 0 l-22 ${BH} l-30 0Z" fill="#FFFFFF" opacity=".34"/></g>`}})}
  const st=(s.stage===1||i===1)?.65:-1;
  if(st<0)g+=T(X0+w-14,y-18,fmtInt(b.v),46,700,TXT,'end');
  else{const q=clamp((lt-st)/.5),v=b.v*(1-Math.pow(1-q,3)),sc=settle(lt,st+.5);if(q>0)g+=`<g opacity="${clamp(q*3)}" transform="translate(${X0+w-14},${y-18}) scale(${sc.toFixed(3)})">${T(0,0,fmtInt(v),46,700,TXT,'end')}</g>`}
  const n=b.v/10000,full=Math.floor(n),stA=(s.stage===1||i===1)?.3:-9;
  for(let j=0;j<Math.ceil(n);j++){const u=stA<0?9:lt-(stA+j*.07),op=stA<0?1:clamp(u*10);let sy=stA<0?1:SPR(u,.4,22);
   // 第二拍（s2 約 2.0 秒）：2016 人像由左到右依序輕跳一次（每人差 40ms）
   let hop=0;if(s.stage===1&&i===0){const hu=lt-(2.0+j*.04);if(hu>0&&hu<.4)hop=-11*Math.sin(Math.PI*hu/.4)}
   if(op<=0)continue;const x=X0+j*46,frac=j<full?1:n-full,yy=y+BH+24+hop;
   g+=frac<1?`<clipPath id="cp${i}"><rect x="${x}" y="${y+BH+8}" width="${40*frac}" height="70"/></clipPath><g clip-path="url(#cp${i})">${couple(x,yy,pc,false,op,sy)}</g>`+couple(x,yy,'',true,op*.6,sy):couple(x,yy,pc,false,op,sy)}
  if(s.stage===2&&i===1){const gap=(s.bars[0].v-b.v)/10000;for(let j=Math.ceil(n);j<Math.ceil(n+gap);j++){const u=lt-(1.05+(j-Math.ceil(n))*.08),op=clamp(u*10);if(op>0)g+=couple(X0+j*46,y+BH+24,'',true,op*.7,SPR(u,.5,20))}}});
 if(s.stage===2){const np=pr(lt,1.3,.35,BACK);if(np>0){g+=`<g opacity="${clamp(np*2)}" transform="translate(439,676) scale(${(.85+.15*np).toFixed(3)}) translate(-439,-676)">${T(439,688,s.note,48,700,TXT)}</g>`;
  g+=wobbleRing(426,668,340,54,pr(lt,1.55,.5),1,4)}}
 return g}
// ── 翻牌告示板（s4）：真的「分翻」——舊字上半先往下翻倒（scaleY 1→0）、下半新字再翻開並回彈；兩列錯開、同列兩格錯開 80 毫秒 ──
function flapCell(x,y,w,h,from,to,k,id){const mid=y+h/2,cell=(txt,hi)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="8" fill="${hi?'#5A4A3C':'#4A4744'}"/>${T(x+w/2,y+50,txt,40,700,hi?'#F4B860':'#F6F1E8')}`;
 const ct=`<clipPath id="${id}t"><rect x="${x}" y="${y}" width="${w}" height="${h/2}"/></clipPath><clipPath id="${id}b"><rect x="${x}" y="${mid}" width="${w}" height="${h/2}"/></clipPath>`;
 let g=ct;
 if(k<=0)g+=cell(from,false);else if(k>=1)g+=cell(to,true);
 else{g+=`<g clip-path="url(#${id}t)">${cell(to,true)}</g><g clip-path="url(#${id}b)">${cell(from,false)}</g>`;
  if(k<.5){const sy=Math.cos(k*Math.PI);g+=`<g transform="translate(0,${mid}) scale(1,${sy.toFixed(3)}) translate(0,${-mid})"><g clip-path="url(#${id}t)">${cell(from,false)}</g></g>`}
  else{const q=(k-.5)/.5,s2=q<.75?Math.pow(q/.75,1.6):1;g+=`<g transform="translate(0,${mid}) scale(1,${clamp(s2).toFixed(3)}) translate(0,${-mid})"><g clip-path="url(#${id}b)">${cell(to,true)}</g></g>`}}
 return g+`<line x1="${x}" y1="${mid}" x2="${x+w}" y2="${mid}" stroke="#2B2927" stroke-width="2"/>`}
function illBoard(t){
 let g=`<rect x="0" y="0" width="888" height="330" rx="26" fill="${FACE}"/>`;
 g+=`<rect x="40" y="40" width="640" height="260" rx="16" fill="#3B3936" stroke="${LINE}" stroke-width="4"/>`+T(70,88,'項目',32,700,'#D8CFC0','start')+T(400,88,'狀態',32,700,'#D8CFC0','start');
 const rows=[['結婚','準時','延後'],['登記對數','持平','減少']];
 rows.forEach(([a,from,to],r)=>{const y=110+r*90,at=TM.board.flip[r][0];g+=`<rect x="64" y="${y}" width="290" height="70" rx="8" fill="#4A4744"/>`+T(84,y+48,a,36,700,'#F6F1E8','start');
  for(let c=0;c<2;c++){const k=clamp((t-at-c*.08)/.3);g+=flapCell(400+c*120,y,110,70,from[c],to[c],k,`fl${r}${c}`)}});
 const sec=(Math.floor(t)+SPR(t%1,.45,40))*6*Math.PI/180,mn=(120+t*.5)*Math.PI/180;
 g+=`<circle cx="784" cy="120" r="64" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/><line x1="784" y1="120" x2="${784+34*Math.sin(mn)}" y2="${120-34*Math.cos(mn)}" stroke="${TXT}" stroke-width="6" stroke-linecap="round"/><line x1="784" y1="120" x2="${784+50*Math.sin(sec)}" y2="${120-50*Math.cos(sec)}" stroke="${LAMP}" stroke-width="3" stroke-linecap="round"/><circle cx="784" cy="120" r="6" fill="${TXT}"/>`;
 const hp=SPR(t-.3,.4,15);
 const bhop=t>3.0?-16*Math.abs(Math.sin(Math.PI*clamp((t-3.0)/.45)))*Math.exp(-(t-3.0)*2):0;
 g+=`<g transform="translate(0,${bhop.toFixed(1)}) translate(784,290) scale(${(1+(1-Math.min(1.1,hp))*.15).toFixed(3)},${Math.max(0,hp).toFixed(3)}) translate(-784,-290)" opacity="${clamp((t-.3)*9)}"><rect x="744" y="210" width="80" height="80" rx="10" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><path d="M768 210 v-16 h32 v16" fill="none" stroke="${LINE}" stroke-width="3"/><line x1="744" y1="244" x2="824" y2="244" stroke="${LINE}" stroke-width="2"/></g>`;
 return g}
// ── 年曆＋蛋糕（s5）：撕頁年曆 2016→2025，每頁以「樞紐在頂」往上折起（加速、陰影掃過下一頁、頁緣亮邊），節奏先慢→快→最後一頁放慢；
//    2025 落下時整本年曆震一下、年份蓋大；兩個蛋糕由下方滑入落定回彈（壓扁）；蠟燭逐根點亮——火苗彈起、光暈擴散 ──
function illCakes(t){
 let g=`<rect x="0" y="0" width="888" height="368" rx="26" fill="${FACE}"/><defs><linearGradient id="shd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5A4632" stop-opacity=".4"/><stop offset="1" stop-color="#5A4632" stop-opacity="0"/></linearGradient></defs>`;
 const FS=TM.cakes.flip,tEnd=TM.cakes.flipEnd;let fi=-1,fu=0;for(let i=0;i<9;i++){if(t>=FS[i]&&t<FS[i]+FDUR[i]){fi=i;fu=(t-FS[i])/FDUR[i]}}
 const done=Math.min(9,FS.filter((s,i)=>t>=s+FDUR[i]).length),baseYear=2016+(fi>=0?fi+1:done),jolt=8*DECAY(t-tEnd,9,30),last=baseYear===2025&&fi<0&&done===9;
  g+=`<g transform="translate(0,${jolt.toFixed(1)})"><rect x="44" y="36" width="250" height="300" rx="14" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/>`;
 const yr=(y,col,sc)=>`<g transform="translate(169,230) scale(${(sc||1).toFixed(3)}) translate(-169,-230)">${T(169,230,String(y),78,700,col||TXT)}</g>`+T(169,290,'年',32,400,SUBC);
 g+=yr(baseYear,last?LAMP:TXT,last?1+.28*(1-SPR(t-tEnd,.4,16)):1);
 if(fi>=0){const u=fu,th=u*u*(Math.PI/2),cs=Math.cos(th),edge=100+236*cs,sh=Math.sin(th);
  g+=`<rect x="44" y="${edge.toFixed(1)}" width="250" height="${(Math.min(336-edge,52*(.4+sh))).toFixed(1)}" fill="url(#shd)" opacity="${(.5+.5*sh).toFixed(2)}"/>`;
  g+=`<g transform="translate(169,100) skewX(${(9*Math.sin(Math.PI*u)).toFixed(1)}) scale(1,${Math.max(.02,cs).toFixed(3)}) translate(-169,-100)"><rect x="44" y="100" width="250" height="236" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${yr(2016+fi)}<rect x="44" y="330" width="250" height="6" fill="#E8DCC6"/></g>`}
 g+=`<rect x="44" y="36" width="250" height="64" rx="14" fill="#C9705A"/>`+T(169,80,'年曆',32,700,'#FFFDF8');
 for(let i=0;i<5;i++)g+=`<circle cx="${80+i*45}" cy="36" r="9" fill="${FACE}" stroke="${LINE}" stroke-width="3"/>`;
 g+=`</g>`;
 const cake=(x,lab,num,li,j0)=>{const u=t-TM.cakes.land[li];let c='';
  const sp=SPR(u,.42,13),dy=(1-sp)*250,squash=u>.18?.07*DECAY(u-.18,9,30):0;
  c+=`<ellipse cx="${x}" cy="320" rx="${(120*clamp(sp)).toFixed(1)}" ry="16" fill="${DARK}" opacity="${clamp(u*5)}"/>`;
  c+=`<g transform="translate(0,${dy.toFixed(1)}) translate(${x},318) scale(${(1+squash*.8).toFixed(3)},${(1-squash).toFixed(3)}) translate(${-x},-318)"><rect x="${x-96}" y="230" width="192" height="88" rx="14" fill="#F0D7B7" stroke="${LINE}" stroke-width="3"/>`+
   `<path d="M${x-96} 250 q24 20 48 0 q24 20 48 0 q24 20 48 0 q24 20 48 0 v-14 a14 14 0 0 0 -14 -14 h-164 a14 14 0 0 0 -14 14Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  [0,1].forEach(j=>{const cx=x-26+j*52,ti=TM.cakes.light[j0+j],lu=t-ti,fsc=SPR(lu,.35,20),fl=1+.06*Math.sin(t*7+j*2+x)*clamp(lu*2);
   c+=`<rect x="${cx-20}" y="166" width="40" height="56" rx="6" fill="${j?'#E9B98A':FACE3}" stroke="${LINE}" stroke-width="2.5"/>`+T(cx,207,num[j],38,700,TXT)+`<line x1="${cx}" y1="166" x2="${cx}" y2="152" stroke="${LINE}" stroke-width="2"/>`;
   if(lu>0){const ru=clamp(lu/.3);c+=glow(cx,138,18+26*EO(lu/.5),.6*Math.min(1,fsc))+(ru<1?`<circle cx="${cx}" cy="136" r="${(6+24*ru).toFixed(1)}" fill="none" stroke="#F4B860" stroke-width="3" opacity="${(.7*(1-ru)).toFixed(2)}"/>`:'')+
    `<g transform="translate(${cx},150) scale(${(Math.max(0,fsc)*fl).toFixed(3)}) translate(${-cx},-150)"><path d="M${cx} ${150} q-10 -12 ${(1.6*Math.sin(t*5+j)).toFixed(1)} -26 q10 14 ${(-1.6*Math.sin(t*5+j)).toFixed(1)} 26Z" fill="#F4B860" stroke="#C5782B" stroke-width="1.5"/></g>`}});
  return c+`</g>`+`<g opacity="${clamp(u*5)}">${T(x,360,lab,32,700,SUBC)}</g>`};
 g+=cake(470,'女性','31',0,0)+cake(726,'男性','33',1,2);
 return g}
// ── 搖籃（s6）：先反向預備一點點 → 一推 → 依單擺物理（指數衰減）搖到停；搖籃連同弧底左右滾動；嬰兒鞋依序掉落、落地壓扁彈起；小夜燈閃兩下後亮起、光暈擴散 ──
function illCradle(t){
 let g=`<rect x="0" y="0" width="888" height="368" rx="26" fill="${FACE}"/><line x1="20" y1="330" x2="868" y2="330" stroke="${LINE}" stroke-width="3" opacity=".5"/>`;
 const p0=TM.cradle.push,ant=t>0&&t<p0?-2.2*Math.sin(Math.PI*t/p0):0,ang=ant+11*DECAY(t-p0,1.05,5.4)+6*DECAY(t-2.0,1.1,5.4),dx=ang*2.4;
 g+=`<g transform="translate(${dx.toFixed(1)},0) rotate(${ang.toFixed(2)} 330 334)"><path d="M150 312 Q330 356 510 312" stroke="#8A5A44" stroke-width="10" fill="none" stroke-linecap="round"/>`+
  `<line x1="230" y1="290" x2="220" y2="326" stroke="#8A5A44" stroke-width="8"/><line x1="430" y1="290" x2="440" y2="326" stroke="#8A5A44" stroke-width="8"/>`+
  `<path d="M180 180 h300 q0 116 -150 116 q-150 0 -150 -116Z" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`+
  `<path d="M180 180 q-10 -110 110 -116 q0 60 -30 116Z" fill="#E9B98A" stroke="${LINE}" stroke-width="4"/>`;
 for(let i=0;i<6;i++)g+=`<line x1="${215+i*48}" y1="186" x2="${215+i*48}" y2="${250+10*Math.sin(i)}" stroke="${LINE}" stroke-width="2" opacity=".35"/>`;
 g+=`<path d="M300 180 q60 26 180 0" stroke="${LAMP}" stroke-width="10" fill="none" opacity=".7" stroke-linecap="round"/></g>`;
 const shoe=(x,ts)=>{const u=t-ts,sp=SPR(u,.34,15),y=(1-sp)*-170,sq=u>.16?.12*DECAY(u-.16,9,32):0,rot=(1-sp)*-25;
  return `<g transform="translate(${x},${300+y}) rotate(${rot.toFixed(1)}) translate(0,24) scale(${(1+sq*.7).toFixed(3)},${(1-sq).toFixed(3)}) translate(0,-24)" opacity="${clamp(u*12)}"><path d="M-36 24 q-4 -30 18 -34 q14 -2 18 12 q24 6 30 22Z" fill="#F0D7B7" stroke="${LINE}" stroke-width="3"/><path d="M-14 -4 q8 8 16 0" stroke="${LAMP}" stroke-width="3" fill="none"/></g>`};
 g+=shoe(620,TM.cradle.shoe[0])+shoe(690,TM.cradle.shoe[1]);
 // 夜燈：0.95 閃兩下（亮→暗→亮）再穩定亮起，光暈由小擴大
 const lu=t-TM.cradle.lamp,lamp=lu<0?0:lu<.06?1:lu<.12?.15:lu<.18?.9:lu<.24?.25:Math.min(1,.8+.2*SPR(lu-.24,.6,12));
 g+=(lamp>0?glow(800,210,60+50*EO(lu/.6),.6*lamp):'')+`<rect x="788" y="250" width="24" height="76" rx="6" fill="${LINE}"/><path d="M766 250 h68 l-14 -50 h-40Z" fill="${lamp>.5?'#FFF1D2':'#E6DCC8'}" stroke="${LINE}" stroke-width="3"/>`;
 for(let i=0;i<3;i++){const u=((t*.35+i*.33)%1),y=250-u*190,o=Math.sin(u*Math.PI)*.55*clamp((t-.9)*2);if(o>0)g+=sparkle(600+i*70,y,6,o)}
 return g}
// ── 窗內夜景（s7）：窗外樓燈由左到右一盞盞亮起（亮度過衝再回落、帶一圈擴散光暈）、窗簾被風吹動後衰減停住、兩杯茶「碰杯」（拉開預備→撞上→彈開回位）、蒸氣向上帶密度與淡出 ──
function illTea(t){
 let g=DEFS+`<rect x="0" y="0" width="888" height="508" rx="26" fill="${FACE}"/>`;
 g+=`<rect x="190" y="30" width="508" height="300" rx="10" fill="#857C72" stroke="${LINE}" stroke-width="6"/>`;
 let halo='',lit=0;
 [[200,170,90],[300,120,80],[392,190,110],[512,140,90],[612,180,80]].forEach(([x,y,w],b)=>{g+=`<rect x="${x}" y="${y}" width="${w}" height="${330-y}" fill="#6F675F"/>`;
  for(let r=0;r<3;r++)for(let c=0;c<2;c++){const u=t-(TM.tea.win(b)+(r*2+c)*.05),wx=x+12+c*(w-24)/2,wy=y+18+r*44,ww=(w-24)/2-10,on=u<0?0:Math.min(1.35,SPR(u,.45,22));
   g+=`<rect x="${wx}" y="${wy}" width="${ww}" height="24" rx="2" fill="${WARM}" opacity="${(.12+.7*Math.min(1,on)).toFixed(2)}"/>`;
   if(u>0){lit+=on;const hr=EO(u/.5);halo+=`<circle cx="${wx+ww/2}" cy="${wy+12}" r="${(8+40*hr).toFixed(1)}" fill="${WARM}" opacity="${(.32*(1-hr)+.07*Math.min(1,on)).toFixed(3)}"/>`}}});
 g+=halo+glow(444,190,330,Math.min(.4,.4*lit/30));
 g+=`<line x1="444" y1="30" x2="444" y2="330" stroke="${LINE}" stroke-width="5"/><line x1="190" y1="180" x2="698" y2="180" stroke="${LINE}" stroke-width="5"/>`;
 g+=`<rect x="170" y="330" width="548" height="20" rx="4" fill="${DARK}" stroke="${LINE}" stroke-width="3"/>`;
 const gust=6*DECAY(t-.35,1.1,5.2),cw=(side,ph)=>{const s=gust*(1+.25*ph),x0=side<0?150:738,dir=side;return `<path d="M${x0} 16 h${dir*120} q${s.toFixed(1)} 120 ${(-dir*10+s*1.6).toFixed(1)} 300 h${-dir*110}Z" fill="#F0D7B7" stroke="${LINE}" stroke-width="3" opacity=".95"/>`};
 g+=cw(1,0)+cw(-1,1.3)+`<line x1="130" y1="16" x2="758" y2="16" stroke="${LINE}" stroke-width="6" stroke-linecap="round"/>`;
 g+=`<g transform="translate(0,46)">`;
 g+=`<rect x="60" y="420" width="768" height="22" rx="6" fill="#C98F5E" stroke="${LINE}" stroke-width="3"/>`;
 // 碰杯：兩杯各自位移＋傾斜
 const tc=TM.tea.clink,cu=t-tc;let off=0;
 if(t>tc-.25&&t<tc-.1)off=-8*EO((t-(tc-.25))/.15);else if(t>=tc-.1&&t<tc)off=-8+(38+8)*Math.pow((t-(tc-.1))/.1,2);else if(t>=tc)off=14+24*DECOS(cu,9,25)*1;
 const tilt=t>=tc?7*DECAY(cu,9,26):0;
 const cup=(x,c,sgn)=>`<g transform="translate(${(sgn*off).toFixed(1)},0) rotate(${(-sgn*tilt).toFixed(1)} ${x} 418)"><ellipse cx="${x}" cy="418" rx="62" ry="10" fill="${DARK}" stroke="${LINE}" stroke-width="2.5"/><path d="M${x-44} 352 h88 q-4 62 -44 62 q-40 0 -44 -62Z" fill="${c}" stroke="${LINE}" stroke-width="3"/><path d="M${x+42} 366 q26 2 18 24 q-6 12 -24 10" fill="none" stroke="${LINE}" stroke-width="3"/>`+
  `<line x1="${x-14}" y1="352" x2="${x-26}" y2="388" stroke="${LINE}" stroke-width="1.5"/><rect x="${x-34}" y="386" width="14" height="16" rx="2" fill="${LAMP}" opacity=".8"/></g>`;
 g+=cup(300,FACE3,1)+cup(470,'#F0D7B7',-1);
 if(cu>0&&cu<.4){const k=EO(cu/.4);g+=`<circle cx="385" cy="372" r="${(10+44*k).toFixed(1)}" fill="none" stroke="#F4B860" stroke-width="${(5*(1-k)+1).toFixed(1)}" opacity="${(.7*(1-k)).toFixed(2)}"/>`+sparkle(385,360,16*Math.min(1.2,SPR(cu,.5,26)),clamp(1-cu/.35))}
 g+=`<path d="M600 418 q-10 -70 70 -70 q80 0 70 70Z" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><path d="M600 382 q-34 -6 -40 -30" fill="none" stroke="${LINE}" stroke-width="4"/><path d="M740 372 q34 0 30 30 q-4 14 -30 12" fill="none" stroke="${LINE}" stroke-width="4"/><g transform="translate(0,${(-9*Math.abs(Math.sin(Math.PI*clamp((t-2.2)/.4)))*Math.exp(-(t-2.2)*1.5)*(t>2.2?1:0)).toFixed(1)})"><ellipse cx="670" cy="348" rx="34" ry="8" fill="${DARK}" stroke="${LINE}" stroke-width="2.5"/><circle cx="670" cy="336" r="8" fill="${LINE}"/></g>`;
 [[300,0],[470,1.1],[560,2.2]].forEach(([x,ph])=>{for(let k=0;k<3;k++){const u=((t*.8+ph*.3+k*.34)%1),y=340-u*84,o=Math.sin(u*Math.PI)*.55*clamp((t-.3)*2);
  g+=`<path d="M${x+k*12-8+u*8} ${y+30} q-12 -14 0 -28 q12 -14 0 -28" stroke="${SUBC}" stroke-width="${(3.8-2*u).toFixed(1)}" fill="none" stroke-linecap="round" opacity="${o.toFixed(2)}"/>`}});
 g+=`</g>`;
 return g}
// ── 識別證與站牌（s8）：吊牌像剛掛上去的——從大角度放手，單擺衰減擺到停；公事包從左滑入、落定壓扁；「下一站」站牌彈出並擺盪；三個箭頭依序滑向站牌、減速停住 ──
function illBadge(t){
 let g=`<rect x="0" y="0" width="888" height="368" rx="26" fill="${FACE}"/><line x1="20" y1="336" x2="868" y2="336" stroke="${LINE}" stroke-width="3" opacity=".5"/>`;
 const a=t<TM.badge.swing?22*EO((t-.2)/.25):22*DECOS(t-TM.badge.swing,1.15,5.0);
 g+=`<circle cx="444" cy="34" r="10" fill="${LINE}"/><g transform="rotate(${a.toFixed(2)} 444 34)"><path d="M444 34 L384 150 M444 34 L504 150" stroke="${LAMP}" stroke-width="8" fill="none"/>`+
  `<rect x="360" y="146" width="168" height="196" rx="16" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/><rect x="420" y="160" width="48" height="12" rx="6" fill="${DARK}"/>`+
  `<circle cx="444" cy="222" r="30" fill="${DARK}" stroke="${LINE}" stroke-width="3"/><path d="M406 290 q38 -42 76 0" fill="${DARK}" stroke="${LINE}" stroke-width="3"/>${T(444,330,'新鮮人',32,700,TXT)}</g>`;
 const cu=t-TM.badge.case,cx=-330*(1-SPR(cu,.7,11)),csq=cu>.3?.08*DECAY(cu-.3,9,30):0;
 g+=`<g transform="translate(${cx.toFixed(1)},0) translate(165,336) scale(${(1+csq*.8).toFixed(3)},${(1-csq).toFixed(3)}) translate(-165,-336)" opacity="${clamp(cu*10)}"><rect x="80" y="240" width="170" height="96" rx="12" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><path d="M135 240 v-20 h60 v20" fill="none" stroke="${LINE}" stroke-width="5"/><rect x="155" y="268" width="20" height="14" rx="3" fill="#F4B860"/></g>`;
 const su=t-TM.badge.sign,sp=SPR(su,.4,15),swing=16*DECOS(su-.12,1.5,6.2);
 g+=`<line x1="720" y1="336" x2="720" y2="${(336-226*EO(su/.3)).toFixed(1)}" stroke="${LINE}" stroke-width="7"/>`;
 if(su>0)g+=`<g transform="translate(720,100) rotate(${swing.toFixed(2)}) scale(${(Math.max(.01,sp)).toFixed(3)})" opacity="${clamp(su*8)}"><rect x="-80" y="-40" width="160" height="70" rx="12" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/>${T(0,8,'下一站',32,700,TXT)}</g>`;
 for(let i=0;i<3;i++){const u=clamp((t-TM.badge.chev-i*.12)/.7),e=1-Math.pow(1-u,3),x=560+e*(112+i*18),o=clamp(u*6)*.85;if(o>0)g+=`<path d="M${x} 214 l14 14 l-14 14" stroke="${LAMP}" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="${o.toFixed(2)}"/>`+(u<1?`<path d="M${x-26*(1-u)} 214 l14 14 l-14 14" stroke="${LAMP}" stroke-width="3" fill="none" stroke-linecap="round" opacity="${(.4*(1-u)).toFixed(2)}"/>`:'')}
 return g}

// ───────── 背景（紙紋＋淡格線＋光影，緩慢視差；不帶 data-o）─────────
function bg(t){const lx=30,ly=28,la=.55;   // v4：紙紋、格線、光影全部靜止（不飄移，避免整張圖在動）
 return `<div class="abs bgl" style="background-image:url('${V.paper}');background-size:512px 512px;background-position:0 0"></div>`+
  `<div class="abs bgl grid" style="background-position:0 0"></div>`+
  `<div class="abs bgl" style="background:radial-gradient(900px 700px at ${lx}% ${ly}%,rgba(255,226,180,${la}),rgba(255,226,180,0) 70%)"></div>`+
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

// v6：轉場＝「掃條過後硬切」，前後鏡文字任何一幀都不同時可見（0 幀同框）。
//   換鏡共 5 幀：f0／f1 掃條由左往右蓋住舊鏡（舊鏡只剩條右邊那一塊）→ f2 整幅蓋住（只有紙底與條）→ f3／f4 掃條再由左往右帶出新鏡（新鏡只有條左邊那一塊）→ f5 起新鏡完整。
//   字幕與出處屬於各自那一鏡的圖層（跟著裁切），不再單獨淡入淡出疊在一起；大數字飛進角落的共用元素變形拿掉（它會讓前鏡文字殘留在新鏡上）。
const TRF=5;
window.renderAt=function(t){const S=V.scenes;let i=S.length-1;for(let j=0;j<S.length;j++){if(t>=S[j].t0&&t<S[j].t1){i=j;break}}
 const s=S[i],lt=t-s.t0,d=s.t1-s.t0,fr=Math.floor(lt*30+1e-6),W=1080;let html=bg(t);
 const layer=(sc,tt,tin)=>{const l=tt-sc.t0,dd=sc.t1-sc.t0;let h=SC[sc.type](sc,l,dd,{});
  if(sc.type!=='outro'){const k=tin==null?1:EO((l-tin)/.24);h+=capHTML(sc.cap,k,(1-k)*18)}
  if(sc.type!=='outro')h+=srcHTML(sc.src,tin==null?1:EO((l-tin+.04)/.2));return h};
 const edge=x=>`<div class="abs" style="left:${(x-12).toFixed(0)}px;top:0;width:24px;height:1920px;background:rgba(217,130,43,.6)"></div>`;
 if(i>0&&fr<TRF){const o=S[i-1];
  if(fr<=1){const e=(fr+1)/3;html+=`<div class="abs layer" data-L="old" data-clip="${(W*e).toFixed(0)},${W}" style="clip-path:inset(0 0 0 ${(W*e).toFixed(0)}px)">${strip(layer(o,t))}</div>${edge(W*e)}`}
  else if(fr===2){html+=edge(W-12)}
  else{const e=(fr-2)/3;html+=`<div class="abs layer" data-L="new" data-clip="0,${(W*e).toFixed(0)}" style="clip-path:inset(0 ${(W*(1-e)).toFixed(0)}px 0 0)">${layer(s,t,TRF/30)}</div>${edge(W*e)}`}
 }else html+=`<div class="abs layer">${layer(s,t,i>0?TRF/30:null)}</div>`;
 html+=`<div data-o="foot" class="abs foot"></div>`+(V.asof?`<div data-o="asof" class="abs asof">截至 ${esc(V.asof)}</div>`:'');
 document.getElementById('stage').innerHTML=html};
// 音效事件（render_video.js 讀取後交給 sfx_v3.py 合成）：每個事件的時間與畫面動作讀同一份 TM／OF，所以聲音與動作落在同一幀
window.sfxEvents=function(){const S=V.scenes,ev=[],E=(t,type,o)=>ev.push(Object.assign({t:+t.toFixed(4),type},o||{}));
 S.forEach((s,i)=>{const t0=s.t0;
  if(i>0&&s.type!=='outro')E(t0,'whoosh');
  if(s.tag)E(t0+({hook:.5,bars:.12,ruler:.15,card:.15,ask:.3,next:.25}[s.type]||.2),'pop');
  if(s.type==='hook'){E(t0+.5,'thump',{g:.3});TM.bridal.off.forEach(o=>{E(t0+o,'tick');E(t0+o+.14,'tick')});E(t0+TM.bridal.box,'thump',{g:.42});E(t0+TM.bridal.box+.12,'bell',{n:[19],g:.5});[.25,.33,.41].forEach((d,k)=>E(t0+TM.bridal.box+d,'sparkle',{n:[24+k*2]}));E(t0+2.1,'tick',{g:.8})}
  if(s.type==='bars'&&s.stage===1){E(t0+TM.counter.stamp,'thump',{g:.6});E(t0+TM.counter.stamp,'bell',{n:[12],g:.35});E(t0+.75,'pop');for(let j=0;j<15;j+=3)E(t0+2.0+j*.04,'tick',{g:.5});E(t0+2.0,'bell',{n:[21],g:.3});E(t0+2.9,'sparkle',{n:[24],g:.6})}
  if(s.type==='bars'&&s.stage===2){TM.banquet.pull.forEach(p=>{E(t0+p+.1,'glide',{f0:900,f1:240,dur:.22,g:.14})})}
  if(s.type==='versus'){TM.board.flip.forEach(r=>[0,1].forEach(c=>{E(t0+r[0]+c*.08+.15,'tick');E(t0+r[0]+c*.08+.3,'tick',{g:.7})}));E(t0+1.55,'glide',{f0:400,f1:900,dur:.4,g:.1});E(t0+1.95,'tick');E(t0+2.3,'bell',{n:[17],g:.45});E(t0+3.0,'tick',{g:.8})}
  if(s.type==='ruler'){TM.cakes.flip.forEach(f=>E(t0+f+.08,'tick',{g:.8}));E(t0+TM.cakes.flipEnd,'thump',{g:.42});TM.cakes.land.forEach(l=>E(t0+l+.2,'thump',{g:.34}));TM.cakes.light.forEach((l,k)=>E(t0+l,'sparkle',{n:[24+k]}))}
  if(s.type==='card'){E(t0+.9,'chime');[0,1].forEach(k=>E(t0+TM.cradle.shoe[k]+.18,'thump',{g:.21}));E(t0+TM.cradle.lamp,'tick');E(t0+TM.cradle.lamp+.12,'tick');E(t0+TM.cradle.lamp+.24,'bell',{n:[19],g:.4});E(t0+2.0,'glide',{f0:300,f1:520,dur:.3,g:.08})}
  if(s.type==='ask'){for(let b=0;b<5;b++)E(t0+TM.tea.win(b),'sparkle',{n:[16+b*2],g:.5});E(t0+TM.tea.clink,'bell',{n:[24],g:.6});E(t0+2.2,'tick',{g:.9})}
  if(s.type==='next'){E(t0+TM.badge.case+.3,'thump',{g:.34});E(t0+TM.badge.sign+.1,'bell',{n:[14],g:.45});[0,1,2].forEach(k=>E(t0+TM.badge.chev+k*.12+.05,'tick'))}
  if(s.type==='outro'){const F=k=>t0+k/30;
   E(F(OF.cloud),'kal',{n:[-17],g:.7});E(F(OF.cloud),'glide',{f0:200,f1:520,dur:.3,g:.12});
   E(F(OF.land),'thump',{g:.6});E(F(OF.land),'kal',{n:[-5],g:.45});
   E(F(OF.sun),'glide',{f0:520,f1:1900,dur:.36,g:.2});E(F(OF.apex),'bell',{n:[12],g:.65});E(F(OF.apex),'kal',{n:[19],g:.5});E(F(OF.apex+8),'kal',{n:[7],g:.3});
   OF.ray.forEach((r,k)=>{E(F(r),'click');E(F(r),'bell',{n:[[16,19,21][k]],g:.6});E(F(r),'sparkle',{n:[28+k*2],g:.5})});
   OF.ch.forEach((c,k)=>{E(F(c+OF.imp),'thump',{g:.53});E(F(c+OF.imp),'kal',{n:[[12],[14],[16],[19]][k],g:.9})});
   E(F(OF.fin),'bloom',{n:[0,4,7,12,16]});E(F(OF.fin),'bell',{n:[12,16,19,24],g:.55});E(F(OF.fin),'shimmer',{n:[12,16,19,24,28,31],g:.5});
   E(F(OF.slog),'kal',{n:[19],g:.35});E(F(OF.next),'kal',{n:[24],g:.4});if(s.keyword)E(F(OF.kw),'kal',{n:[28],g:.5});
   E(F(OF.glint),'shimmer',{n:[24,28,31,36],g:.3});
   E(F(0),'pad',{dur:s.t1-s.t0})}});
 return ev};
window.renderAt(0);
