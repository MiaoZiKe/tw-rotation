 tape:{draw(t,h){let g=`<rect x="0" y="${h-90}" width="888" height="90" fill="#E4D3B8"/>`;
  const ext=600*SPR(t-.2,.55,10)+(t>1.4?6*Math.sin((t-1.4)*5):0),y=h-170;   // 尺帶在手上輕輕來回（環境動作）g+=`<rect x="140" y="${y}" width="${ext.toFixed(1)}" height="50" fill="#F4D27A" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i*30<ext;i++)g+=`<line x1="${140+i*30}" y1="${y}" x2="${140+i*30}" y2="${y+(i%5?16:28)}" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="${136+ext}" y="${y-12}" width="14" height="74" rx="3" fill="${LINE}"/>`;
  const rb=-6*DECAY(t-.9,4,14);g+=`<g transform="translate(${rb.toFixed(1)},0)"><rect x="40" y="${y-90}" width="180" height="180" rx="40" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><circle cx="130" cy="${y}" r="34" fill="#F3DDB8" stroke="${LINE}" stroke-width="3"/></g>`;
  const q=SPR(t-1.1,.45,16);if(t>1.1)g+=`<g transform="translate(560,${y-90}) scale(${Math.max(.01,q).toFixed(3)})" opacity="${clamp((q-.1)/.85).toFixed(3)}"><rect x="-50" y="-40" width="100" height="70" rx="14" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(0,14,'?',44,700,HINT)}<path d="M-10 30 l10 16 l10 -16" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<rect x="300" y="40" width="288" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,88,'25 歲以前',34,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:900,f1:500,dur:.5,g:.07});E(t0+.9,'click');E(t0+1.15,'pop')}}
