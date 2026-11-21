 road:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/>`;
  const cl=(t*14)%1000;g+=`<g opacity=".7"><ellipse cx="${(200+cl)%1000-60}" cy="70" rx="70" ry="22" fill="#FFFDF8"/><ellipse cx="${(620+cl*.7)%1000-60}" cy="96" rx="54" ry="18" fill="#FFFDF8"/></g>`;
  g+=`<path d="M0 ${h-150} q220 -60 444 -40 q220 20 444 -30 V${h} H0Z" fill="#D9C4A0"/><path d="M380 ${h} L470 ${h-140} L520 ${h-140} L700 ${h}Z" fill="#C9B28C"/>`;
  for(let i=0;i<5;i++){const y=h-20-i*26;g+=`<rect x="${532-i*8}" y="${y}" width="${30-i*4}" height="6" fill="#FFFDF8" opacity=".8"/>`}
  // 學士帽不用（輪播已用）；改畫一雙新皮鞋在路口
  g+=`<g transform="translate(240,${h-70})"><path d="M0 0 h70 q20 0 20 18 h-90Z" fill="#6E4636" stroke="${LINE}" stroke-width="2"/><path d="M96 6 h70 q20 0 20 18 h-90Z" fill="#6E4636" stroke="${LINE}" stroke-width="2"/></g>`;
  // 路牌：0.5 往右遠處滑一格（預備往左一點→滑出→過衝回彈）
  const pre=t>.4&&t<.55?-8*Math.sin(Math.PI*(t-.4)/.15):0,mv=SPR(t-.55,.5,11),x=560+150*mv+pre,sc=1;
  g+=`<g transform="translate(${x.toFixed(1)},${(h-150-10*mv).toFixed(1)}) scale(${sc.toFixed(3)})"><line x1="0" y1="0" x2="0" y2="-150" stroke="${LINE}" stroke-width="7"/><rect x="-74" y="-206" width="148" height="66" rx="10" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>${T(0,-160,'還款',34,700,'#FFFFFF')}</g>`;
  g+=`<g transform="translate(470,${h-150})"><line x1="0" y1="0" x2="0" y2="-120" stroke="${LINE}" stroke-width="6"/><rect x="-66" y="-170" width="132" height="58" rx="10" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,-130,'寬限',32,700,'#FFFFFF')}</g>`;
  [[110,h-160],[790,h-180]].forEach(([lx,ly],i)=>{const on=clamp((t-1.2-i*.25)*5);g+=(on>0?glow(lx,ly-110,60,.55*on):'')+`<line x1="${lx}" y1="${ly}" x2="${lx}" y2="${ly-100}" stroke="${LINE}" stroke-width="5"/><circle cx="${lx}" cy="${ly-108}" r="13" fill="${on>.5?'#F4B860':'#D8C6A8'}" stroke="${LINE}" stroke-width="2"/>`});
  return g},
  sfx(t0,s,E){E(t0+.55,'glide',{f0:500,f1:260,dur:.35,g:.12});E(t0+1.0,'thump',{g:.3});E(t0+1.2,'sparkle',{n:[24]});E(t0+1.45,'sparkle',{n:[26]})}}
