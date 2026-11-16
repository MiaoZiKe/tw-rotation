 nightoffice:{draw(t,h){const k=clamp(t/1.2);const sky=`rgb(${Math.round(243-120*k)},${Math.round(214-120*k)},${Math.round(178-100*k)})`;
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="${sky}"/><circle cx="740" cy="${(120-30*k).toFixed(1)}" r="34" fill="#FFF1D2" opacity="${(.3+.6*k).toFixed(2)}"/>`;
  for(let i=0;i<14;i++){const x=(i*137)%860+14,y=(i*71)%180+20;g+=`<circle cx="${x}" cy="${y}" r="2.5" fill="#FFF8E6" opacity="${(k*(.4+.4*tw(t,i,2))).toFixed(2)}"/>`}
  g+=`<rect x="0" y="${h-90}" width="888" height="90" fill="#8E7E6E"/><rect x="200" y="120" width="488" height="${h-210}" fill="#A99682" stroke="${LINE}" stroke-width="4"/>`;
  for(let r=0;r<5;r++)for(let c=0;c<6;c++)g+=`<rect x="${226+c*76}" y="${200+r*44}" width="52" height="26" rx="3" fill="#8E8070"/>`;
  g+=`<circle cx="444" cy="150" r="34" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;const mn=(40+t*20)*Math.PI/30;g+=`<line x1="444" y1="150" x2="${444+24*Math.sin(mn)}" y2="${150-24*Math.cos(mn)}" stroke="${TXT}" stroke-width="4"/><line x1="444" y1="150" x2="${444+16*Math.sin(Math.PI*7/6+.1)}" y2="${150-16*Math.cos(Math.PI*7/6+.1)}" stroke="${TXT}" stroke-width="5"/>`;
  const dr=t>1.4?34*Math.sin(Math.PI*clamp((t-1.4)/1.2)):0;g+=`<rect x="384" y="${h-200}" width="120" height="110" fill="#E9D9BF"/><rect x="${384-dr}" y="${h-200}" width="60" height="110" fill="#C9D3C9" stroke="${LINE}" stroke-width="3"/><rect x="${444+dr}" y="${h-200}" width="60" height="110" fill="#C9D3C9" stroke="${LINE}" stroke-width="3"/>`;
  const on=t<.6?0:t<.66?1:t<.72?.3:1;g+=(on?glow(110,h-300,110,.6*on):'')+`<line x1="110" y1="${h-90}" x2="110" y2="${h-290}" stroke="${LINE}" stroke-width="7"/><path d="M90 ${h-300} h40 l-6 -20 h-28Z" fill="${on>.5?'#FFE9B8':'#B9B2A8'}" stroke="${LINE}" stroke-width="2"/>`;
  return g},
  sfx(t0,s,E){E(t0+.6,'click');E(t0+.66,'click');E(t0+1.4,'glide',{f0:500,f1:300,dur:.4,g:.06})}}
