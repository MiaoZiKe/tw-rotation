 stopwatch:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;const cx=300,cy=h/2+10;
  const pr2=t>.2&&t<.3?6:0;g+=`<rect x="${cx-18}" y="${cy-150+pr2}" width="36" height="26" rx="6" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><circle cx="${cx}" cy="${cy}" r="120" fill="${FACE3}" stroke="${LINE}" stroke-width="8"/>`;
  for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${cx+100*Math.sin(a)}" y1="${cy-100*Math.cos(a)}" x2="${cx+110*Math.sin(a)}" y2="${cy-110*Math.cos(a)}" stroke="${LINE}" stroke-width="3"/>`}
  const a=t<.2?0:(t<.9?(t-.2)*30:21+.3*DECAY(t-.9,4,14))+t*.15;g+=`<line x1="${cx}" y1="${cy}" x2="${(cx+92*Math.sin(a)).toFixed(1)}" y2="${(cy-92*Math.cos(a)).toFixed(1)}" stroke="${LAMP}" stroke-width="6" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="10" fill="${LINE}"/>`;
  g+=`<rect x="520" y="${h-260}" width="260" height="200" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(650,h-210,'工時紀錄',32,700,TXT);
  for(let i=0;i<5;i++){const u=clamp((t-.3-i*.2)/.18);if(u>0&&u<1)g+=`<path d="M780 ${h-260} q${-130*u} -30 ${-260*u} 0 v200 q${130*u} -30 ${260*u} 0" fill="#F6EFE2" stroke="${LINE}" stroke-width="2"/>`}
  for(let i=0;i<3;i++)g+=`<line x1="548" y1="${h-170+i*36}" x2="${740-(i%2)*50}" y2="${h-170+i*36}" stroke="${LINE}" stroke-width="2" opacity=".4"/>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'click');E(t0+.9,'bell',{n:[19],g:.35});for(let i=0;i<5;i++)E(t0+.35+i*.2,'tick',{g:.4})}}
