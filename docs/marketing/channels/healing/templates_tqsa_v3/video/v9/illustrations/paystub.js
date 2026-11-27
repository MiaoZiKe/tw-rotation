 paystub:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#C9A27A"/>`;
  // s1 薪資單：薪資單從桌下滑上來（0–0.5，過衝回停）→「+1,400」硬幣從右上落進單子（0.9，彈一下）→ 合計列由 29,500 滾到 30,900（1.1–1.9），滾完被晴光橘框起；旁邊筆筒的筆晃一下（2026-11-27 新做，最低工資）
  const up=SPR(t,.5,12),y0=60+(1-up)*(h-60);
  g+=`<rect x="700" y="${h-210}" width="110" height="130" rx="14" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  const pw=4*DECAY(t-.95,2.5,10);g+=`<g transform="rotate(${(-8+pw).toFixed(2)} 755 ${h-200})"><rect x="735" y="${h-320}" width="14" height="120" rx="5" fill="#E36B4A"/><rect x="760" y="${h-300}" width="14" height="100" rx="5" fill="#5E7A62"/></g>`;
  g+=`<g transform="translate(0,${y0.toFixed(1)})"><rect x="150" y="0" width="500" height="${h-150}" rx="14" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/>`+T(400,62,'薪資單',38,700,TXT)+T(400,104,'2027 年 1 月起',28,400,SUBC);
  g+=`<line x1="190" y1="128" x2="610" y2="128" stroke="${LINE}" stroke-width="2" opacity=".5"/>`;
  [['本薪',''],['加給',''],['合計','']].forEach(([k],i)=>{const yy=186+i*70;g+=T(200,yy,k,32,i===2?700:400,i===2?TXT:SUBC,'start');if(i<2)g+=`<line x1="330" y1="${yy-10}" x2="${590-i*60}" y2="${yy-10}" stroke="${LINE}" stroke-width="3" opacity=".3"/>`});
  const roll=clamp((t-1.1)/.8),v=Math.round((29500+1400*EO(roll))/100)*100;g+=T(600,326,F1(v),44,700,roll>=1?TXT:SUBC,'end');
  if(roll>=1){const k=clamp((t-1.9)/.3);g+=`<rect x="410" y="${280}" width="210" height="66" rx="12" fill="none" stroke="${LAMP}" stroke-width="6" ${draw(k)}/>`}
  g+=`</g>`;
  const dp=clamp((t-.6)/.3),cx=560+(1-dp)*160,cy=t<.9?(-40+(y0+250+40)*dp*dp):(y0+250-18*Math.abs(DECAY(t-.9,4,12)));
  if(t>.6&&t<1.25)g+=`<g transform="translate(${cx.toFixed(1)},${cy.toFixed(1)})" opacity="${clamp((1.25-t)*5)}"><circle r="56" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${T(0,11,'+1,400',30,700,'#FFFFFF')}</g>`;
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:420,f1:780,dur:.4,g:.06});E(t0+.9,'thump',{g:.3});for(let i=0;i<6;i++)E(t0+1.1+i*.13,'tick',{g:.3});E(t0+1.95,'bell',{n:[21],g:.3})}}
