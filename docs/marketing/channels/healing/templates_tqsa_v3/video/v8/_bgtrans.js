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
// v7：片尾留言關鍵字膠囊與旁白「留言結婚」同步——旁白在片尾第 voiceAt 秒開口，「留言」約在開口後 0.85 秒；沒有旁白資料就用 OF.kw
const kwF=s=>s.voiceAt!=null?Math.round((s.voiceAt+.85)*30):OF.kw;
