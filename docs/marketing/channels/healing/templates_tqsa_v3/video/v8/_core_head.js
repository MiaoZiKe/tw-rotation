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
function srcHTML(s,op,fs){if(op<=0)return'';const ls=String(s).split('\n'),f=fs||34,lh=44,top=1806-(ls.length-1)*lh;return `<div data-o="src" class="abs src" style="opacity:${op.toFixed(3)};top:${top}px;font-size:${f}px">${ls.map(esc).join('<br>')}</div>`}
const glow=(cx,cy,r,a)=>`<circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#gl)" opacity="${a.toFixed(3)}"/>`;
const DEFS=`<defs><radialGradient id="gl"><stop offset="0" stop-color="#F2B66B" stop-opacity=".85"/><stop offset=".55" stop-color="#F2B66B" stop-opacity=".25"/><stop offset="1" stop-color="#F2B66B" stop-opacity="0"/></radialGradient>
<radialGradient id="glw"><stop offset="0" stop-color="#FFE9B8" stop-opacity=".95"/><stop offset="1" stop-color="#FFE9B8" stop-opacity="0"/></radialGradient></defs>`;
// 手繪圈：不正圓、多繞 8%，有手感
function wobbleRing(cx,cy,rx,ry,p,seed,n){n=n||2;let d='';const N=48,e=2/n;for(let i=0;i<=N;i++){const a=-2.2+i/N*Math.PI*2.16,w=1+.045*Math.sin(i*.9+seed)+.03*Math.sin(i*2.3+seed*2),c=Math.cos(a),sn=Math.sin(a);   // n＞2＝方一點的手繪圈（把文字完整框住，不壓筆畫）
 d+=(i?'L':'M')+(cx+rx*w*Math.sign(c)*Math.pow(Math.abs(c),e)).toFixed(1)+' '+(cy+ry*w*Math.sign(sn)*Math.pow(Math.abs(sn),e)).toFixed(1)}
 return `<path d="${d}" fill="none" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" ${draw(p)}/>`}
function sparkle(x,y,s,a){return a<=0?'':`<path d="M${x} ${y-s} Q${x} ${y} ${x+s} ${y} Q${x} ${y} ${x} ${y+s} Q${x} ${y} ${x-s} ${y} Q${x} ${y} ${x} ${y-s}Z" fill="#FFF4D6" opacity="${a.toFixed(2)}"/>`}
const tw=(t,ph,sp)=>.5+.5*Math.sin(t*(sp||4)+ph);   // 閃爍／呼吸
