 regdesk:{draw(t,h){const dy=h-84;let g=`<rect x="0" y="${dy}" width="888" height="84" fill="#C9A27A"/><line x1="0" y1="${dy}" x2="888" y2="${dy}" stroke="${LINE}" stroke-width="4"/>`;
  g+=`<rect x="214" y="150" width="460" height="${dy-150}" fill="#F3E6D0" stroke="${LINE}" stroke-width="4"/><rect x="236" y="168" width="416" height="${dy-190}" fill="#FFFDF8" stroke="${LINE}" stroke-width="2"/>`;
  const p=clamp((t-.2)/1.2),v=Math.round(104376*(1-Math.pow(1-p,3))),num=v.toString().replace(/\B(?=(\d{3})+(?!\d))/g,',');
  g+=`<rect x="194" y="22" width="500" height="106" rx="16" fill="#3A3836" stroke="${LINE}" stroke-width="4"/>`+T(444,98,num+' 對',62,700,'#F4B860');
  const sy=214+48*SPR(t-1.3,.45,14),pr=t>1.3;if(t>1.0)g+=`<g transform="translate(444 ${sy.toFixed(1)})"><rect x="-8" y="-60" width="16" height="50" rx="6" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><circle cx="0" cy="-66" r="18" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><rect x="-36" y="-10" width="72" height="22" rx="6" fill="#E36B4A" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<rect x="334" y="${dy-26}" width="220" height="26" rx="4" fill="#FFFFFF" stroke="${LINE}" stroke-width="3"/><rect x="344" y="${dy-48}" width="200" height="24" rx="4" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`;
  if(pr)g+=glow(444,dy-40,70,.45*(1-clamp(t-1.6)))+`<circle cx="444" cy="${dy-36}" r="${(16*Math.min(1,(t-1.3)*6)).toFixed(1)}" fill="#E36B4A" opacity=".85"/>`;
  g+=`<rect x="40" y="${dy+14}" width="190" height="52" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(135,dy+52,'結婚登記',32,700,TXT);
  const tp=SPR(t-.5,.5,12);g+=`<rect x="742" y="170" width="96" height="${dy-170}" rx="12" fill="#E4D3B8" stroke="${LINE}" stroke-width="3"/><rect x="760" y="200" width="60" height="14" rx="4" fill="${LINE}"/>`;
  if(t>.5)g+=`<g transform="translate(790 ${(206+70*tp).toFixed(1)})"><rect x="-26" y="-6" width="52" height="76" rx="4" fill="#FFFFFF" stroke="${LINE}" stroke-width="3"/><line x1="-14" y1="14" x2="14" y2="14" stroke="${LINE}" stroke-width="3"/><line x1="-14" y1="28" x2="14" y2="28" stroke="${LINE}" stroke-width="3"/></g>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i++)E(t0+.3+i*.16,'tick',{g:.4});E(t0+1.3,'thump',{g:.35});E(t0+1.35,'sparkle',{n:[24]})}}
