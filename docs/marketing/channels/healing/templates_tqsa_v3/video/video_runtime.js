// 談晴說礙 數據短影音執行期：window.renderAt(t) 依時間 t（秒）重畫整個畫面（逐幀截圖用，結果只跟 t 有關、可重現）。
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const ease=x=>{x=clamp(x);return 1-Math.pow(1-x,3)};          // easeOutCubic
const prog=(t,a,b)=>ease((t-a)/(b-a));
const fmtInt=n=>Math.round(n).toLocaleString('en-US');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LAMP='var(--lamp)',LINE='var(--line)',FACE='var(--face)',FACE3='var(--face3)',TXT='var(--text)',SUBC='var(--sub)';
function T(x,y,s,fs,w,col,anchor){return `<text x="${x}" y="${y}" text-anchor="${anchor||'middle'}" font-size="${fs}" font-weight="${w||400}" fill="${col||SUBC}" font-family="Noto Sans CJK TC">${esc(s)}</text>`}
function svgBox(top,h,inner){return `<div data-o="chart" class="abs" style="left:96px;top:${top}px;width:888px;height:${h}px"><svg width="888" height="${h}" viewBox="0 0 888 ${h}">${inner}</svg></div>`}
function title(lines,top,fs,op,dy){return `<div data-o="title" class="abs title" style="top:${top+(dy||0)}px;font-size:${fs}px;line-height:${Math.round(fs*1.22)}px;opacity:${op}">${lines.map(esc).join('<br>')}</div>`}
function sceneAlpha(t,s){const fi=s.t0===0?1:prog(t,s.t0,s.t0+.45),fo=1-prog(t,s.t1-.35,s.t1);return Math.min(fi,fo)}
function sub(s,t,a){if(!s.sub)return'';const o=a*prog(t,s.t0+.6,s.t0+1.2);return `<div data-o="sub" class="abs sub" style="opacity:${o}">${esc(s.sub)}</div>`}
function src(s,a){return `<div data-o="src" class="abs src" style="opacity:${a}">${esc(s.src)}</div>`}

function ringpair(cx,cy,r,dashed,a){
  const st=dashed?`stroke="${LINE}" stroke-width="3" stroke-dasharray="8 8" fill="none" opacity="${.55*a}"`:'';
  if(dashed)return `<circle cx="${cx-r*.45}" cy="${cy}" r="${r}" ${st}/><circle cx="${cx+r*.45}" cy="${cy}" r="${r}" ${st}/>`;
  return `<circle cx="${cx-r*.45}" cy="${cy}" r="${r}" stroke="${LAMP}" stroke-width="8" fill="none" opacity="${a}"/><circle cx="${cx+r*.45}" cy="${cy}" r="${r}" stroke="${LINE}" stroke-width="8" fill="none" opacity="${a}"/>`}

const SCENES={
 title_rings(s,t,a){
  let o=title(s.title,360,88,a*prog(t,s.t0,s.t0+.7),(1-prog(t,s.t0,s.t0+.7))*30);
  let g='';const r=48;
  for(let i=0;i<s.n;i++){const rr=Math.floor(i/5),c=i%5,cx=104+c*170,cy=90+rr*200;
    const ap=prog(t,s.t0+.8+i*.18,s.t0+1.1+i*.18);
    const dashedNow=i>=s.n-s.fade && t>s.t0+3.3;
    const k=i>=s.n-s.fade?prog(t,s.t0+3.0,s.t0+3.6):0;     // 3 組由實線淡成虛線
    g+= dashedNow?ringpair(cx,cy,r,true,ap):ringpair(cx,cy,r,false,ap*(1-k))+ (k>0?ringpair(cx,cy,r,true,ap*k):'');
  }
  const bp=prog(t,s.t0+3.8,s.t0+5.2);
  g+=`<g opacity="${prog(t,s.t0+3.7,s.t0+4.0)}">`+T(444,560,s.big.fmt.replace('{:.1f}',(s.big.from+(s.big.to-s.big.from)*bp).toFixed(1)),120,700,TXT)+T(444,630,s.big.label,34,400,SUBC)+`</g>`;
  g=`<g opacity="${prog(t,s.t0+.6,s.t0+1)}">${g}</g>`;
  return o+`<div style="opacity:${a}">${svgBox(640,680,g)}</div>`+sub(s,t,a)+src(s,a)},
 bars(s,t,a){
  let o=title(s.title,360,80,a,0)+`<div data-o="lead" class="abs" style="left:96px;top:470px;font-size:40px;line-height:56px;opacity:${a};color:var(--sub)">${esc(s.lead)}</div>`;
  const H=720,base=H-90,k=(base-110)/s.vmax,w=210,x0=140,gap=300;let g=`<line x1="40" y1="${base}" x2="848" y2="${base}" stroke="${LINE}" stroke-width="3"/>`;
  s.bars.forEach((b,i)=>{const p=prog(t,s.t0+.7+i*1.6,s.t0+2.1+i*1.6),h=b.v*k*p,x=x0+i*(w+gap);
    g+=`<rect x="${x}" y="${base-h}" width="${w}" height="${h}" rx="6" fill="${b.hi?LAMP:FACE3}" stroke="${b.hi?LAMP:LINE}" stroke-width="2.4" opacity="${b.hi?.9:1}"/>`;
    if(p>0)g+=T(x+w/2,base-h-24,fmtInt(b.v*p),54,700,TXT);
    g+=T(x+w/2,base+56,b.lab,36,400,SUBC)});
  const np=prog(t,s.t0+4.4,s.t0+5.2);
  if(np>0){const y1=base-s.bars[0].v*k,y2=base-s.bars[1].v*k,xm=x0+w+gap+w+28;
    g+=`<g opacity="${np}"><path d="M${x0+w+12} ${y1} H${xm} V${y2}" stroke="${LAMP}" stroke-width="3" stroke-dasharray="10 8" fill="none"/>${T(xm-10,y1-20,s.note,38,700,TXT,'end')}</g>`}
  return o+`<div style="opacity:${a}">${svgBox(570,H,g)}</div>`+sub(s,t,a)+src(s,a)},
 numbers(s,t,a){
  let o=title(s.title,360,80,a,0);let g='';
  s.cards.forEach((c,i)=>{const y=40+i*380,p=prog(t,s.t0+.5+i*1.8,s.t0+1.9+i*1.8),ap=prog(t,s.t0+.3+i*1.8,s.t0+.7+i*1.8);
    g+=`<g opacity="${ap}"><rect x="64" y="${y}" width="760" height="320" rx="28" fill="${i?FACE:FACE3}" stroke="${i?LINE:LAMP}" stroke-width="3"/>`+T(444,y+80,c.lab,40,400,TXT)+T(444,y+230,(c.pre||'')+(c.to*p).toFixed(c.dec)+(c.unit||''),120,700,TXT)+`</g>`});
  return o+`<div style="opacity:${a}">${svgBox(500,760,g)}</div>`+sub(s,t,a)+src(s,a)},
 ask(s,t,a){
  const p=prog(t,s.t0+.2,s.t0+1.0);
  // 收尾插圖：一間小屋（成家），窗戶的燈由暗慢慢亮起；只在本篇使用（素材不跨篇重複）
  const L=prog(t,s.t0+.8,s.t0+2.2);
  let g=`<g opacity="${p}"><path d="M284 200 L444 70 L604 200" stroke="${LINE}" stroke-width="5" fill="none" stroke-linejoin="round"/>`+
   `<rect x="314" y="190" width="260" height="190" rx="6" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`+
   `<rect x="344" y="230" width="84" height="74" rx="4" fill="${LAMP}" opacity="${.15+.75*L}" stroke="${LINE}" stroke-width="3"/>`+
   `<rect x="470" y="262" width="74" height="118" rx="4" fill="${FACE}" stroke="${LINE}" stroke-width="3"/><circle cx="530" cy="324" r="5" fill="${LINE}"/>`+
   `<line x1="200" y1="380" x2="688" y2="380" stroke="${LINE}" stroke-width="3"/></g>`;
  return `<div style="opacity:${a}">${svgBox(560,400,g)}</div>`+`<div data-o="title" class="abs title" style="top:1010px;font-size:80px;line-height:100px;text-align:center;color:var(--hint);opacity:${a*prog(t,s.t0+.6,s.t0+1.3)}">${esc(s.ask)}<br>${esc(s.ask2)}</div>`+src(s,a)}
};
window.renderAt=function(t){let o='';for(const s of V.scenes){if(t<s.t0||t>=s.t1+(s===V.scenes[V.scenes.length-1]?1:0))continue;o+=SCENES[s.type](s,t,sceneAlpha(t,s))}
 document.getElementById('stage').innerHTML=o};
window.renderAt(0);
