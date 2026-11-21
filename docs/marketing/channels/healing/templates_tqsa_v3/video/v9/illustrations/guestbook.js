 guestbook:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/>`;
  g+=`<path d="M120 50 q160 -20 324 10 v${h-90} q-164 -30 -324 -10Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M444 60 q160 -30 324 -10 v${h-90} q-164 -20 -324 10Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(282,110,'第一次',32,700,SUBC);for(let i=0;i<3;i++)g+=`<line x1="160" y1="${160+i*60}" x2="410" y2="${158+i*60}" stroke="${LINE}" stroke-width="2" opacity=".35"/><line x1="480" y1="${150+i*60}" x2="730" y2="${152+i*60}" stroke="${LINE}" stroke-width="2" opacity=".35"/>`;
  const w=pr(t,.3,.8);g+=`<path d="M170 150 q30 -26 50 0 t50 0 t50 -6 t50 4" fill="none" stroke="${LAMP}" stroke-width="6" stroke-linecap="round" ${draw(w)}/>`;
  const px=170+200*w,py=150-(t>1.1?40*SPR(t-1.1,.6,10):0)+(w>0&&w<1?6*Math.sin(t*30):0);g+=`<g transform="translate(${px.toFixed(1)},${py.toFixed(1)}) rotate(35)"><rect x="-8" y="-120" width="16" height="110" rx="6" fill="#8A5A44" stroke="${LINE}" stroke-width="2"/><path d="M-8 -10 l8 16 l8 -16Z" fill="${LINE}"/></g>`;
  g+=`<path d="M768 ${h-40} l-30 ${(-4-6*tw(t,0,2)).toFixed(1)} l26 -26Z" fill="#F3EADB" stroke="${LINE}" stroke-width="2"/>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'glide',{f0:900,f1:700,dur:.8,g:.04});E(t0+1.1,'tick')}}
