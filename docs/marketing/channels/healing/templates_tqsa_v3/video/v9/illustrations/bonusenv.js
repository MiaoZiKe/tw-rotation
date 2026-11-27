 bonusenv:{draw(t,h){let g=`<rect x="0" y="${h-90}" width="888" height="90" fill="#C9A27A"/>`;
  // s1 年終紅包與預扣章：紅包「年終」從右滑進桌面（0–0.5，過衝回停）→ 上方「預扣 5%」印章壓下來（0.8），在紅包上方一點停住、碰不到就被彈回去（1.0–1.4，阻尼）→ 紅包上冒出「全額入帳」綠勾（1.5）；紅包金箔閃（2026-11-27 新做，年終）
  const sl=SPR(t,.5,11),ex=444+(1-sl)*560;
  g+=`<g transform="translate(${ex.toFixed(1)},${h-250})"><rect x="-150" y="-110" width="300" height="270" rx="18" fill="#D94F3D" stroke="${LINE}" stroke-width="4"/><path d="M-150 -110 L0 -20 L150 -110" fill="#C4402F" stroke="${LINE}" stroke-width="3"/><circle cx="0" cy="-20" r="30" fill="#F4D27A" stroke="${LINE}" stroke-width="3"/>${T(0,90,'年終',52,700,'#FFF4D6')}`;
  [[-110,30],[100,120]].forEach(([x,y],i)=>g+=sparkle(x,y,10,.3+.5*tw(t,i*2,5)));g+=`</g>`;
  const dn=SPR(t-.8,.5,14),bounce=t<1.0?0:SPR(t-1.0,.35,12),sy=40+(h-560-40)*dn*(1-.9*bounce);
  if(t>.6){g+=`<g transform="translate(444,${sy.toFixed(1)})" opacity="${clamp((t-.6)*5)}"><rect x="-26" y="-120" width="52" height="90" rx="12" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/><rect x="-100" y="-30" width="200" height="60" rx="10" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>${T(0,14,'預扣 5%',30,700,'#FFFFFF')}</g>`}
  const ok=SPR(t-1.5,.45,14);if(ok>0)g+=`<g transform="translate(690,${h-440}) scale(${ok.toFixed(3)})"><rect x="-120" y="-40" width="240" height="80" rx="40" fill="#5E7A62" stroke="${LINE}" stroke-width="3"/>${T(0,13,'全額入帳',32,700,'#FFFFFF')}</g>`;
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:800,f1:420,dur:.45,g:.07});E(t0+1.0,'thump',{g:.25});E(t0+1.55,'bell',{n:[21],g:.35})}}
