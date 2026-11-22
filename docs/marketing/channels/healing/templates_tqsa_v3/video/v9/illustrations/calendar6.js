 calendar6:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/>`;
  // 六張月曆：5～10 月六張月曆依序翻上牆（每 0.18 秒一張，落下彈一下），每張落定後蓋上「>2%」章（章壓下回彈、橘光一閃）；最後一張（10 月）框起
  const M=['5月','6月','7月','8月','9月','10月'],cw=124,gap=14,x0=(888-(cw*6+gap*5))/2,y0=h/2-90;
  g+=`<line x1="40" y1="${y0-24}" x2="848" y2="${y0-24}" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 8" opacity=".5"/>`;
  for(let i=0;i<6;i++){const u=t-.15-i*.18,p=SPR(u,.45,12),x=x0+i*(cw+gap);
    if(u<=0){g+=`<rect x="${x}" y="${y0}" width="${cw}" height="170" rx="10" fill="none" stroke="${LINE}" stroke-width="2" stroke-dasharray="5 6" opacity=".35"/>`;continue}
    const dy=(1-p)*-120;g+=`<g transform="translate(0,${dy.toFixed(1)})" opacity="${clamp(u*8)}"><rect x="${x}" y="${y0}" width="${cw}" height="170" rx="10" fill="#FFFDF8" stroke="${i==5?LAMP:LINE}" stroke-width="${i==5?6:3}"/><rect x="${x}" y="${y0}" width="${cw}" height="44" rx="10" fill="#D9C4A0"/>${T(x+cw/2,y0+34,M[i],30,700,TXT)}`;
    const st=SPR(u-.35,.35,10);if(st>0){const sc=1+.4*(1-st);g+=`<g transform="translate(${x+cw/2},${y0+112}) scale(${sc.toFixed(3)})" opacity="${clamp(st*3)}"><circle r="56" fill="none" stroke="${LAMP}" stroke-width="5"/>${T(0,12,'>2%',34,700,LAMP)}</g>`}
    g+=`</g>`}
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i++)E(t0+.5+i*.18,'tick',{g:.4})}}
