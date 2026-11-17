 tank:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EEE5D6"/><rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  const x0=280,w=330,top=80,bot=h-120;g+=`<rect x="${x0}" y="${top}" width="${w}" height="${bot-top}" rx="18" fill="#F7F2E8" stroke="${LINE}" stroke-width="5"/>`;
  const lv=.62+.08*SPR(t-.5,.6,6)*Math.exp(-Math.max(0,t-1.2)*.6)-.03*Math.max(0,t-.2),wy=bot-(bot-top)*lv;
  let d=`M${x0+4} ${wy}`;for(let x=0;x<=w-8;x+=16)d+=` L${x0+4+x} ${(wy+4*Math.sin(x/30+t*4)).toFixed(1)}`;g+=`<path d="${d} L${x0+w-4} ${bot-4} L${x0+4} ${bot-4}Z" fill="#B9CFC8" opacity=".9"/>`;
  for(let i=1;i<5;i++)g+=`<line x1="${x0+w-40}" y1="${top+i*(bot-top)/5}" x2="${x0+w-6}" y2="${top+i*(bot-top)/5}" stroke="${LINE}" stroke-width="3"/>`;
  g+=`<rect x="${x0+w}" y="${bot-40}" width="90" height="24" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  for(let k=0;k<3;k++){const u=((t*1.6+k/3)%1);g+=`<ellipse cx="${x0+w+84}" cy="${(bot-10+u*80).toFixed(1)}" rx="7" ry="10" fill="#9CB8AE" opacity="${(1-u).toFixed(2)}"/>`}
  const fl=t>.5&&t<1.3;g+=`<path d="M120 ${top+20} h200 v30" fill="none" stroke="#B98A6A" stroke-width="22" stroke-linejoin="round"/>`;if(fl)g+=`<rect x="306" y="${top+50}" width="12" height="${(wy-top-50).toFixed(1)}" fill="#9CB8AE" opacity=".8"/>`;
  const vr=fl?0:-90*SPR(t-1.3,.5,12);g+=`<g transform="rotate(${(t<.5?-90*(1-SPR(t-.2,.5,12)):vr).toFixed(1)} 180 ${top+20})"><rect x="150" y="${top+12}" width="60" height="16" rx="6" fill="${LAMP}" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=T(445,bot+40,'勞保基金',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.5,'glide',{f0:300,f1:600,dur:.6,g:.08});E(t0+1.3,'click')}}
