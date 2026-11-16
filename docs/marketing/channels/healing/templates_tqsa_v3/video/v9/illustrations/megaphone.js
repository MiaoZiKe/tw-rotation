 megaphone:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  const kick=-8*DECAY(t-.2,4,14);g+=`<g transform="rotate(${kick.toFixed(1)} 150 ${h/2})"><path d="M90 ${h/2-30} h50 l140 -80 v220 l-140 -80 h-50Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><rect x="110" y="${h/2+30}" width="30" height="60" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/></g>`;
  for(let k=0;k<4;k++){const u=((t*.9+k/4)%1);if(t<.2)break;g+=`<path d="M${300+u*220} ${h/2-60-u*30} q${30+u*20} ${60+u*30} 0 ${120+u*60}" fill="none" stroke="${LAMP}" stroke-width="${(6*(1-u)).toFixed(1)}" opacity="${(.8*(1-u)).toFixed(2)}"/>`}
  g+=`<rect x="600" y="${h/2-100}" width="200" height="230" rx="8" fill="#F3EADB" stroke="${LINE}" stroke-width="3"/><rect x="590" y="${h/2-110}" width="200" height="230" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(690,h/2-56,'精算報告',32,700,TXT);
  for(let i=0;i<4;i++)g+=`<line x1="612" y1="${h/2-10+i*30}" x2="${770-(i%2)*40}" y2="${h/2-10+i*30}" stroke="${LINE}" stroke-width="2" opacity=".45"/>`;
  const pg=clamp((t-1.0)/.5);if(pg>0&&pg<1){const x=790-200*pg;g+=`<path d="M790 ${h/2-110} L${x} ${h/2-110-30*Math.sin(Math.PI*pg)} L${x} ${h/2+120-30*Math.sin(Math.PI*pg)} L790 ${h/2+120}Z" fill="#F7F0E4" stroke="${LINE}" stroke-width="2"/>`}
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:500,f1:300,dur:.3,g:.08});E(t0+1.0,'glide',{f0:900,f1:500,dur:.4,g:.06})}}
