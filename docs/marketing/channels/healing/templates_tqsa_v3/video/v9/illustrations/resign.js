 resign:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="0" y="${h-110}" width="888" height="110" fill="#C9A27A"/>`;
  // 辦公桌上的離職信：信封從右滑進桌面（0.2，過衝回停）→ 筆在信封上畫出一條手寫線（0.7–1.3 描線）→ 信封被輕推到桌緣又停住（1.5，晃一下）；牆上時鐘秒針走
  const ck=t*90;g+=`<circle cx="150" cy="130" r="70" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><line x1="150" y1="130" x2="${(150+52*Math.sin(ck*Math.PI/180)).toFixed(1)}" y2="${(130-52*Math.cos(ck*Math.PI/180)).toFixed(1)}" stroke="${LAMP}" stroke-width="4" stroke-linecap="round"/><line x1="150" y1="130" x2="150" y2="86" stroke="${LINE}" stroke-width="5" stroke-linecap="round"/>`;
  g+=`<rect x="560" y="${h-300}" width="220" height="190" rx="10" fill="#4A4744" stroke="${LINE}" stroke-width="3"/><rect x="578" y="${h-282}" width="184" height="130" rx="6" fill="#DCE3CF"/>`;
  const sl=SPR(t-.2,.5,11),push=12*SPR(t-1.5,.4,10)*(1+.3*Math.sin((t-1.5)*14)*DECAY(t-1.5,1,5)),ex=330+(1-sl)*600+push;
  g+=`<g transform="translate(${ex.toFixed(1)},${h-190}) rotate(${(-4+2*DECAY(t-.4,1,6)).toFixed(2)})"><rect x="-170" y="-70" width="340" height="150" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><path d="M-170 -70 L0 20 L170 -70" fill="none" stroke="${LINE}" stroke-width="3"/>${T(0,60,'離職信',34,700,TXT)}`;
  const w=clamp((t-.7)/.6);if(w>0)g+=`<path d="M-120 -10 q30 -20 60 0 t60 0 t60 0" fill="none" stroke="${LAMP}" stroke-width="5" stroke-linecap="round" stroke-dasharray="200" stroke-dashoffset="${(200*(1-w)).toFixed(1)}"/>`;
  g+=`</g>`;
  const px=ex-60+180*w,py=h-230-10*Math.sin(w*Math.PI*3);if(t>.6&&t<1.6)g+=`<g transform="translate(${px.toFixed(1)},${py.toFixed(1)}) rotate(35)"><rect x="-8" y="-90" width="16" height="90" rx="4" fill="#8A5A44"/><path d="M-8 0 L0 18 L8 0Z" fill="${LINE}"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:800,f1:420,dur:.45,g:.07});E(t0+.75,'tick',{g:.35});E(t0+1.5,'thump',{g:.18})}}
