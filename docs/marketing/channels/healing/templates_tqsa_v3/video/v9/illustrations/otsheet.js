 otsheet:{draw(t,h){const V=+'16.2',D=+'1.5';   // 參數：V＝有加班者平均每月延長工時（小時）、D＝比前一年多幾小時（2026-11-22 新做，加班調查）
  const L=[70,46,118,62,96,52],n=L.length,x0=96,xb=520,y0=118,rh=Math.min(52,(h-250)/n),gap=(h-250-rh*n)/(n-1||1);
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="40" y="30" width="808" height="${h-60}" rx="18" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/>`;
  g+=T(76,88,'加班紀錄',34,700,TXT,'start');
  const lp=pr(t,.1,.35);g+=`<line x1="${xb}" y1="${y0-14}" x2="${xb}" y2="${(y0+n*(rh+gap)-gap+14).toFixed(1)}" stroke="${HINT}" stroke-width="4" stroke-dasharray="10 8" opacity="${lp.toFixed(3)}"/>`;
  g+=`<g opacity="${lp.toFixed(3)}">${T(812,88,'下班 18:00',30,400,SUBC,'end')}</g>`;
  let sum=0;const tot=L.reduce((a,b)=>a+b,0);
  L.forEach((ln,i)=>{const y=y0+i*(rh+gap),pb=pr(t,.05+i*.06,.35),u=t-.35-i*.2,pe=u<=0?0:Math.min(1.06,SPR(u,.45,12));
   g+=`<rect x="${x0}" y="${y.toFixed(1)}" width="${((xb-x0)*pb).toFixed(1)}" height="${rh.toFixed(1)}" rx="10" fill="#B98A6A" opacity=".55"/>`;
   if(pe>0){g+=`<rect x="${xb}" y="${y.toFixed(1)}" width="${(ln*2.2*pe).toFixed(1)}" height="${rh.toFixed(1)}" rx="10" fill="${LAMP}"/>`;sum+=ln*Math.min(1,pe)}});
  const v=V*sum/tot,last=t>.35+(n-1)*.2+.45;
  const bp=last?1+.06*DECAY(t-(.35+(n-1)*.2+.45),5,12):1,cy=h-70;
  g+=`<g transform="translate(444,${cy}) scale(${bp.toFixed(3)})"><rect x="-200" y="-34" width="400" height="68" rx="34" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(0,13,'每月 '+(last?V.toFixed(1):v.toFixed(1))+' 小時',36,700,TXT)}</g>`;
  const sp=pr(t,2.1,.3);if(sp>0)g+=`<g opacity="${sp.toFixed(3)}" transform="translate(0,${(-8*DECAY(t-2.1,5,14)).toFixed(1)})">${T(760,cy+12,'+'+D+' 小時',30,700,HINT)}</g>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i++)E(t0+.4+i*.2,'tick',{g:.42});E(t0+1.85,'pop',{g:.3})}}
