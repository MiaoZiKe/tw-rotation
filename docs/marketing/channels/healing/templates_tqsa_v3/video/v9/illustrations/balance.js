 balance:{draw(t,h){let g=`<rect x="0" y="${h-40}" width="888" height="40" fill="#E4D3B8"/><path d="M400 ${h-40} h88 l-24 -30 h-40Z" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><line x1="444" y1="${h-70}" x2="444" y2="110" stroke="${LINE}" stroke-width="10"/>`;
  const ang=8*SPR(t-.55,.35,8),r=ang*Math.PI/180,L=300,lx=444-L*Math.cos(r),ly=70-L*Math.sin(r)*-1*-1,rx=444+L*Math.cos(r);const yl=110-L*Math.sin(r),yr=110+L*Math.sin(r);
  g+=`<line x1="${lx.toFixed(1)}" y1="${yl.toFixed(1)}" x2="${rx.toFixed(1)}" y2="${yr.toFixed(1)}" stroke="#B98A6A" stroke-width="12" stroke-linecap="round"/><circle cx="444" cy="110" r="14" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>`;
  const pan=(x,y,w2,lab,c,drop)=>`<line x1="${x}" y1="${y}" x2="${x-70}" y2="${y+110}" stroke="${LINE}" stroke-width="2"/><line x1="${x}" y1="${y}" x2="${x+70}" y2="${y+110}" stroke="${LINE}" stroke-width="2"/><path d="M${x-90} ${y+110} h180 q-10 24 -90 24 q-80 0 -90 -24Z" fill="#DADCD6" stroke="${LINE}" stroke-width="3"/><g transform="translate(0,${drop.toFixed(1)})"><rect x="${x-w2/2}" y="${y+110-w2*.7}" width="${w2}" height="${w2*.7}" rx="10" fill="${c}" stroke="${LINE}" stroke-width="3"/>${T(x,y+110-w2*.35+12,lab,32,700,'#FFFFFF')}</g>`;
  const dr=t<.4?-200:-200*(1-Math.min(1,(t-.4)/.15)**2)+(t>.55?-6*Math.abs(DECAY(t-.55,6,14)):0);
  g+=pan(lx,yl,80,'11%','#B98A6A',0)+(t>.4?pan(rx,yr,150,'31.42%',LAMP,dr):pan(rx,yr,0.01,'',LAMP,0));
  return g},
  sfx(t0,s,E){E(t0+.55,'thump',{g:.45});E(t0+.8,'tick')}}
