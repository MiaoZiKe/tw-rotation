 govbuilding:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/><rect x="0" y="${h-60}" width="888" height="60" fill="#D9C4A0"/>`;
  g+=`<path d="M430 120 L640 60 L850 120Z" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><rect x="450" y="120" width="380" height="${h-180}" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<5;i++)g+=`<rect x="${470+i*72}" y="140" width="22" height="${h-210}" fill="#E4D8C4" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="600" y="${h-150}" width="80" height="90" rx="6" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/>`+T(640,104,'行政院',32,700,'#FFFFFF');
  const on=clamp((t-1.1)*5);g+=`<rect x="510" y="160" width="40" height="40" fill="${on>.5?'#FFE9B8':'#E4D8C4'}" stroke="${LINE}" stroke-width="2"/>`+(on>0?glow(530,180,46,.5*on):'');
  const fw=Math.sin(t*5)*8;g+=`<line x1="460" y1="120" x2="460" y2="20" stroke="${LINE}" stroke-width="4"/><path d="M462 24 q30 ${fw.toFixed(1)} 60 0 v36 q-30 ${(-fw).toFixed(1)} -60 0Z" fill="${LAMP}"/>`;
  const u=clamp((t-.2)/.7),e=EO(u),x=80+(640-80)*e,y=(h-160)-200*Math.sin(Math.PI*e),sc=1-.5*e;if(u<1)g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${(-10+20*e).toFixed(1)}) scale(${sc.toFixed(3)})"><rect x="-70" y="-46" width="140" height="92" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M-70 -46 L0 6 L70 -46" fill="none" stroke="${LINE}" stroke-width="3"/></g>`;
  for(let i=0;i<3;i++){const u2=clamp((t-.2-i*.06)/.7);if(u2<=0||u2>=1)continue;const e2=EO(u2);g+=`<circle cx="${(80+560*e2-30).toFixed(1)}" cy="${((h-160)-200*Math.sin(Math.PI*e2)+10).toFixed(1)}" r="${(6-i*1.5).toFixed(1)}" fill="${LAMP}" opacity="${(.5-i*.12).toFixed(2)}"/>`}
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:400,f1:900,dur:.6,g:.08});E(t0+.9,'thump',{g:.25});E(t0+1.1,'sparkle',{n:[24]})}}
