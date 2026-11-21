// 談晴說礙 數據短影音執行期 v2（2026-11-15）
// 依據：Andy「影片步調可以再快點」＋共用內容邏輯 docs/marketing/channels/video_logic.md
//   ① 0–3 秒鉤子：第 0 格就是完整主張，1 秒內有動作（線畫出、蓋章、劃線），前 3 秒 4–5 個畫面事件
//   ② 中段一句一件事：發生什麼 → 大家以為 vs 數據 → 逐一查證（每個說法標狀態）→ 最合理的解釋
//   ③ 結尾：還不知道的事＋二選一提問＋下集預告
// 規則：硬切、不淡出到空白；每段一進來第一格就有標題與主體；數字跳動、圖表生長 0.4–0.6 秒；
//       每 0.5–1.5 秒畫面有變化；狀態標籤出現後至少停 0.8 秒；常駐「查證截至」；每段底部一行出處；
//       字幕＝該段旁白文字（大、最多 2 行）。window.renderAt(t) 只跟 t 有關、可重現。
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=clamp(x);return 1-Math.pow(1-x,3)};
const pr=(lt,a,d)=>ease((lt-a)/d);
const fmtInt=n=>Math.round(n).toLocaleString('en-US');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LAMP='var(--lamp)',LINE='var(--line)',FACE='var(--face)',FACE3='var(--face3)',TXT='var(--text)',SUBC='var(--sub)';
function T(x,y,s,fs,w,col,anchor){return `<text x="${x}" y="${y}" text-anchor="${anchor||'middle'}" font-size="${fs}" font-weight="${w||400}" fill="${col||SUBC}" font-family="Noto Sans CJK TC">${esc(s)}</text>`}
function box(o,top,h,inner){return `<div data-o="${o}" class="abs" style="left:96px;top:${top}px;width:888px;height:${h}px"><svg width="888" height="${h}" viewBox="0 0 888 ${h}">${inner}</svg></div>`}
// 版面（1080×1920）：LOGO 56–120｜標題 170 起｜狀態標籤 420｜圖 500 起｜字幕下緣 1690｜出處 1806–1850｜頁尾帶 1866–1874
function enter(lt,full){if(full)return {op:1,dy:0};const p=pr(lt,0,.22);return {op:.6+.4*p,dy:(1-p)*26}}
function title(lines,lt,o){o=o||{};const fs=o.fs||92,top=o.top||170,e=enter(lt,o.full);
 return `<div data-o="title" class="abs title ${o.cls||''}" style="top:${top}px;font-size:${fs}px;line-height:${Math.round(fs*1.24)}px;opacity:${e.op};transform:translateY(${e.dy}px)">${lines.map(esc).join('<br>')}</div>`}
// 狀態標籤（video_logic 二-2）：已確定／官方統計／常見說法／自行計算…；出現時 0.2 秒「蓋章」放大回彈
function tag(s,lt,at,top){if(!s)return'';const p=pr(lt,at||0,.2);if(p<=0)return'';const sc=1+.18*(1-p);
 return `<div data-o="tag" class="abs tag" style="top:${top||420}px;transform:scale(${sc});transform-origin:left center;opacity:${p}">${esc(s)}</div>`}
// 字幕：去掉句尾句號；≤11 字一行 76px，否則在最靠近中間的標點後斷成 2 行（64px；一行超過 13 字就縮到放得下），不留孤字
function split2(s){const m=s.length/2;let best=-1,bd=1e9;for(let i=1;i<s.length-1;i++){if(/[，、：；？！]/.test(s[i])){const d=Math.abs(i+1-m);if(d<bd&&i+1<=16&&s.length-i-1<=16){bd=d;best=i+1}}}
 if(best<0||Math.min(best,s.length-best)<s.length/3)best=Math.ceil(m);return [s.slice(0,best),s.slice(best)]}   // 標點離中間太遠（會剩 3、4 字一行）就從中間斷
function cap(s){if(!s)return'';s=s.replace(/。$/,'');const one=s.length<=11;const ls=one?[s]:split2(s);const mx=Math.max(...ls.map(l=>l.length));const fs=one?76:(mx<=13?64:Math.min(64,Math.floor(880/mx)));
 const lh=Math.round(fs*1.28),h=ls.length*lh,top=1690-h;
 return `<div data-o="cap" class="abs cap" style="top:${top}px;font-size:${fs}px;line-height:${lh}px">${ls.map(esc).join('<br>')}</div>`}
function src(s){return `<div data-o="src" class="abs src">${esc(s.src)}</div><div data-o="foot" class="abs foot"></div>`}
function asof(){return V.asof?`<div data-o="asof" class="abs asof">查證截至 ${esc(V.asof)}</div>`:''}
function ringpair(cx,cy,r,dash,k){
  if(dash)return `<g opacity="${.55*k}"><circle cx="${cx-r*.45}" cy="${cy}" r="${r}" stroke="${LINE}" stroke-width="3" stroke-dasharray="8 8" fill="none"/><circle cx="${cx+r*.45}" cy="${cy}" r="${r}" stroke="${LINE}" stroke-width="3" stroke-dasharray="8 8" fill="none"/></g>`;
  return `<g opacity="${k}"><circle cx="${cx-r*.45}" cy="${cy}" r="${r}" stroke="${LAMP}" stroke-width="7" fill="none"/><circle cx="${cx+r*.45}" cy="${cy}" r="${r}" stroke="${LINE}" stroke-width="7" fill="none"/></g>`}

const SCENES={
 // ① 鉤子：第 0 格＝完整標題＋完整大數字；0–0.5 秒折線畫出、0.5 秒蓋章、0.9 秒標籤、1.3 秒起 10 組對戒後 3 組變虛線
 hook(s,lt){
  let g=T(444,220,s.big,230,700,TXT)+T(444,310,s.label,42,400,SUBC);
  const p=pr(lt,0,.5),y0=390,y1=640,k=(y1-y0)/s.trend.vmax,a=y1-s.trend.a*k,b=y1-s.trend.b*k,xa=250,xb=250+380*p,yb=a+(b-a)*p;
  g+=`<line x1="200" y1="${y1}" x2="688" y2="${y1}" stroke="${LINE}" stroke-width="3"/><line x1="${xa}" y1="${a}" x2="${xb}" y2="${yb}" stroke="${LAMP}" stroke-width="7" stroke-linecap="round"/><circle cx="${xa}" cy="${a}" r="11" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><circle cx="${xb}" cy="${yb}" r="11" fill="${LAMP}"/>`;
  g+=`<g opacity="${pr(lt,.9,.25)}">`+T(xa,y1+52,s.trend.la,36,400,SUBC)+T(630,y1+52,s.trend.lb,36,400,SUBC)+`</g>`;
  const kr=pr(lt,1.4,.5);let rg='';for(let i=0;i<10;i++){const cx=96+i*78+(i>4?40:0);const d=i>=7;rg+=d?ringpair(cx,44,28,false,1-kr)+ringpair(cx,44,28,true,kr):ringpair(cx,44,28,false,1)}
  g+=`<g transform="translate(0,740)" opacity="${pr(lt,1.2,.2)}">${rg}</g>`;
  // 1 秒內的動作：在「近3成」下方劃一道晴光橘底線
  const u=pr(lt,.5,.35);const ul=`<div data-o="ul" class="abs" style="left:96px;top:${170+2*114+2}px;height:10px;width:${(s.ulw||360)*u}px;background:var(--lamp);border-radius:5px;opacity:.85"></div>`;
  return title(s.title,lt,{full:true})+ul+box('chart',500,880,g)+tag(s.tag,lt,.5,0)},
 // 直條：stage 1＝只長出第一根（第二根虛線待揭曉）；stage 2＝第一根已在，第二根長出＋差額
 bars(s,lt){
  const H=900,base=H-90,k=(base-110)/s.vmax,w=230,x0=120,gap=200;let g=`<line x1="30" y1="${base}" x2="858" y2="${base}" stroke="${LINE}" stroke-width="3"/>`;
  s.bars.forEach((b,i)=>{const x=x0+i*(w+gap);let p;
    if(s.stage===1)p=i===0?pr(lt,.05,.5):0;else p=i===0?1:pr(lt,.05,.5);
    if(p===0){g+=`<rect x="${x}" y="${base-200}" width="${w}" height="200" rx="6" fill="none" stroke="${LINE}" stroke-width="2.4" stroke-dasharray="10 8" opacity=".5"/>`+T(x+w/2,base-80,'?',72,700,SUBC)}
    else{const h=b.v*k*p;g+=`<rect x="${x}" y="${base-h}" width="${w}" height="${h}" rx="6" fill="${b.hi?LAMP:FACE3}" stroke="${b.hi?LAMP:LINE}" stroke-width="2.4" opacity="${b.hi?.9:1}"/>`+T(x+w/2,base-h-28,fmtInt(b.v*p),66,700,TXT)}
    g+=T(x+w/2,base+62,b.lab,42,400,SUBC)});
  if(s.stage===2){const np=pr(lt,.7,.25);if(np>0){const y1=base-s.bars[0].v*k,y2=base-s.bars[1].v*k,xm=x0+2*w+gap+40;
    g+=`<g opacity="${np}"><path d="M${x0+w+12} ${y1} H${xm} V${y2}" stroke="${LAMP}" stroke-width="3" stroke-dasharray="10 8" fill="none"/>${T(xm-14,y1-26,s.note,46,700,TXT,'end')}</g>`}}
  else{g+=`<g opacity="${pr(lt,1.1,.25)}">${T(444,44,s.unit,38,400,SUBC)}</g>`}
  return title(s.title,lt)+tag(s.tag,lt,.15)+box('chart',500,H,g)},
 // 對照：左＝常見說法（標「說法」），右＝數據（標「官方統計」）；右卡 0.6 秒滑入
 versus(s,lt){
  const pa=pr(lt,0,.3),pb=pr(lt,.6,.35);let g='';
  [[s.a,pa,false,0],[s.b,pb,true,452]].forEach(([c,p,hi,x])=>{const dx=(1-p)*40;
   g+=`<g opacity="${p}" transform="translate(${dx},0)"><rect x="${x+8}" y="20" width="420" height="700" rx="28" fill="${hi?FACE3:FACE}" stroke="${hi?LAMP:LINE}" stroke-width="${hi?4:3}" ${hi?'':'stroke-dasharray="12 10"'}/>`+
   T(x+218,110,c.k,40,700,hi?'var(--hint)':SUBC)+c.lines.map((l,i)=>T(x+218,320+i*100,l,70,700,TXT)).join('')+T(x+218,670,c.foot,32,400,SUBC)+`</g>`});
  g+=`<g opacity="${pr(lt,1.2,.25)}">${T(444,810,s.mid,42,700,TXT)}</g>`;
  return title(s.title,lt)+box('chart',500,880,g)},
 // 數線：兩個標記 0.5 秒滑到位置（數線不是長條，不從 0 起算；刻度標清楚）
 ruler(s,lt){
  const x0=80,x1=808,sx=v=>x0+(x1-x0)*(v-s.lo)/(s.hi-s.lo),ay=440;let g=`<line x1="${x0}" y1="${ay}" x2="${x1}" y2="${ay}" stroke="${LINE}" stroke-width="4"/>`;
  for(let v=s.lo;v<=s.hi;v++){g+=`<line x1="${sx(v)}" y1="${ay-12}" x2="${sx(v)}" y2="${ay+12}" stroke="${LINE}" stroke-width="2"/>`+T(sx(v),ay+60,String(v),34,400,SUBC)}
  g+=T(x1,ay+108,'歲',34,400,SUBC,'end');
  s.pins.forEach((m,i)=>{const p=pr(lt,.1+i*.6,.5),x=sx(s.lo+(m.v-s.lo)*p),up=i===0;const y=up?ay-40:ay+150;
   g+=`<g opacity="${pr(lt,.1+i*.6,.15)}"><circle cx="${x}" cy="${ay}" r="16" fill="${m.hi?LAMP:FACE3}" stroke="${LINE}" stroke-width="3"/>`+
    `<line x1="${x}" y1="${ay+(up?-16:16)}" x2="${x}" y2="${up?ay-90:ay+110}" stroke="${LINE}" stroke-width="2"/>`+
    T(x,up?ay-110:ay+176,m.lab,40,400,TXT)+T(x,up?ay-170:ay+256,m.v.toFixed(1)+' 歲',70,700,TXT)+`</g>`});
  return title(s.title,lt)+tag(s.tag,lt,.2)+box('chart',500,820,g)},
 // 數字卡：0.5 秒跳到真實值；0.8 秒出現參考說明
 card(s,lt){
  const p=pr(lt,0,.5),c=s.card;
  let g=`<rect x="64" y="20" width="760" height="520" rx="32" fill="${FACE3}" stroke="${LAMP}" stroke-width="4"/>`+T(444,140,c.lab,50,400,TXT)+T(444,390,(c.pre||'')+(c.to*p).toFixed(c.dec)+(c.unit||''),190,700,TXT);
  // 等比例小條：0～1，標 0.7 參考線
  const bx=124,bw=640,by=640;g+=`<g opacity="${pr(lt,.6,.25)}"><rect x="${bx}" y="${by}" width="${bw}" height="44" rx="6" fill="none" stroke="${LINE}" stroke-width="2"/><rect x="${bx}" y="${by}" width="${bw*c.to*p}" height="44" rx="6" fill="${LAMP}" opacity=".85"/>`+
   `<line x1="${bx+bw*.7}" y1="${by-14}" x2="${bx+bw*.7}" y2="${by+48}" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6"/>`+T(bx+bw*.7,by+100,c.ref,36,700,TXT)+T(bx,by+100,'0',34,400,SUBC,'start')+T(bx+bw,by+100,'1',34,400,SUBC,'end')+`</g>`;
  return title(s.title,lt)+tag(s.tag,lt,.2)+box('chart',500,820,g)},
 // ③ 收尾提問：第一格就有問句；小屋窗燈 0.5 秒亮起（本篇專用插圖）；1.2 秒「還不知道」標籤
 ask(s,lt){
  const L=pr(lt,.1,.5);
  let g=`<path d="M284 190 L444 60 L604 190" stroke="${LINE}" stroke-width="5" fill="none" stroke-linejoin="round"/>`+
   `<rect x="314" y="180" width="260" height="190" rx="6" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`+
   `<rect x="344" y="220" width="84" height="74" rx="4" fill="${LAMP}" opacity="${.15+.75*L}" stroke="${LINE}" stroke-width="3"/>`+
   `<rect x="470" y="252" width="74" height="118" rx="4" fill="${FACE}" stroke="${LINE}" stroke-width="3"/><circle cx="530" cy="314" r="5" fill="${LINE}"/>`+
   `<line x1="200" y1="370" x2="688" y2="370" stroke="${LINE}" stroke-width="3"/>`;
  g=`<g transform="translate(444,40) scale(1.5) translate(-444,0)">${g}</g>`;
  return title(s.title,lt,{cls:'hint'})+tag(s.tag,lt,.4)+box('chart',500,640,g)},
 // 下集預告：一張虛線的薪資條，數字位置是「?」（下集揭曉）
 next(s,lt){
  const p=pr(lt,0,.35);let g=`<g opacity="${p}"><rect x="144" y="40" width="600" height="360" rx="20" fill="${FACE}" stroke="${LINE}" stroke-width="3" stroke-dasharray="12 10"/>`+
   `<rect x="144" y="40" width="600" height="70" rx="20" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,88,s.slip,34,700,TXT)+
   T(240,200,s.row,34,400,TXT,'start')+T(650,200,'?',72,700,'var(--hint)','end')+`<line x1="240" y1="250" x2="650" y2="250" stroke="${LINE}" stroke-width="2" opacity=".5"/>`+
   `<line x1="240" y1="320" x2="560" y2="320" stroke="${LINE}" stroke-width="2" opacity=".35"/></g>`;
  g=`<g transform="translate(444,30) scale(1.3) translate(-444,0)">${g}</g>`;
  return title(s.title,lt)+tag(s.tag,lt,.3)+box('chart',500,600,g)}
};
window.renderAt=function(t){const S=V.scenes;let s=S[S.length-1];for(const x of S){if(t>=x.t0&&t<x.t1){s=x;break}}
 const lt=t-s.t0;document.getElementById('stage').innerHTML=asof()+SCENES[s.type](s,lt)+cap(s.cap)+src(s)};
window.renderAt(0);
