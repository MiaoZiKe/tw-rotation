 otrent:{draw(t,hh){const h=528,sc=Math.min(1,hh/528),ox=(888-888*sc)/2;let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E2C8"/>`;
  const cl=(t*16)%1000;g+=`<ellipse cx="${(120+cl)%1000-60}" cy="70" rx="80" ry="24" fill="#FFFDF8" opacity=".8"/><ellipse cx="${(640+cl*.6)%1000-60}" cy="110" rx="60" ry="18" fill="#FFFDF8" opacity=".7"/>`;
  g+=`<rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  g+=`<rect x="240" y="80" width="408" height="${h-140}" fill="#E9D9BF" stroke="${LINE}" stroke-width="4"/>`;
  for(let r=0;r<7;r++)for(let c=0;c<4;c++)g+=`<rect x="${270+c*94}" y="${110+r*52}" width="60" height="34" rx="3" fill="#C9D3C9" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="410" y="${h-130}" width="68" height="70" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/>`;
  [80,720].forEach((x,i)=>g+=`<rect x="${x}" y="${h-200-i*40}" width="${88}" height="${140+i*40}" fill="#D9C4A0" stroke="${LINE}" stroke-width="3"/>`);
  // （otrent＝rentbanner 等比縮進較矮的面板，2026-11-22 加班片下集預告；吊牌與窗戶不出框；吊牌字放大到縮放後 ≥30px，金額改「？」不先講下集數字）「租」字布條垂下（0.2–0.8），布條底端用細繩掛月租吊牌；吊牌像單擺：擺幅隨時間衰減（0.6 起），最後停在 0 度（價格定住）
  const un=SPR(t-.2,.6,9),L=210*un,sw=6*DECAY(t-.6,1.6,6)+3*Math.sin(t*3);
  g+=`<g transform="rotate(${sw.toFixed(2)} 600 84)"><rect x="560" y="84" width="80" height="${L.toFixed(1)}" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${L>160?T(600,160,'租',44,700,'#FFFFFF')+T(600,220,'房',44,700,'#FFFFFF'):''}`;
  if(L>120){const ang=16*DECAY(t-.9,1.3,6.5),py=84+L;
    g+=`<g transform="rotate(${ang.toFixed(2)} 600 ${py.toFixed(1)})"><line x1="600" y1="${py.toFixed(1)}" x2="600" y2="${(py+26).toFixed(1)}" stroke="${LINE}" stroke-width="3"/><rect x="510" y="${(py+26).toFixed(1)}" width="180" height="140" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><circle cx="600" cy="${(py+26).toFixed(1)}" r="5" fill="${LINE}"/>${T(600,py+80,'月租',44,700,SUBC)}${T(600,py+150,'？',56,700,HINT)}</g>`}
  g+=`</g><rect x="548" y="74" width="104" height="14" rx="4" fill="${LINE}"/>`;
  return `<rect x="0" y="0" width="888" height="${hh}" rx="26" fill="#F3E2C8"/><rect x="0" y="${(hh-60*sc).toFixed(1)}" width="888" height="${(60*sc).toFixed(1)}" fill="#CDB896"/><g transform="translate(${ox.toFixed(1)},0) scale(${sc.toFixed(4)})">`+g+'</g>'},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:900,f1:400,dur:.5,g:.08});E(t0+.7,'thump',{g:.25});E(t0+1.0,'tick',{g:.5})}}
