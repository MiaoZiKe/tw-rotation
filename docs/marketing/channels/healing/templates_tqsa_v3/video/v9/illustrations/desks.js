 desks:{draw(t,h){const N=+'10',K=+'5';   // 參數：N＝今年的基準（十張課桌）、K＝十五年後坐得滿的幾張（5）；其餘只剩空桌、椅子虛線
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-70}" width="888" height="70" fill="#CDB896"/>`;
  g+=`<rect x="244" y="30" width="400" height="90" rx="8" fill="#5E7A62" stroke="${LINE}" stroke-width="4"/>${T(444,90,'一年級',36,700,'#FFFFFF')}`;
  const cols=5,pw=150,x0=444-pw*cols/2,rows=2,rh=(h-230)/rows;let sat=0;
  for(let i=0;i<N;i++){const c=i%cols,r=Math.floor(i/cols),cx=x0+pw*(c+.5),cy=150+rh*(r+.5);
    g+=`<rect x="${(cx-50).toFixed(1)}" y="${(cy-14).toFixed(1)}" width="100" height="24" rx="5" fill="#C9A27A" stroke="${LINE}" stroke-width="3"/><line x1="${(cx-40).toFixed(1)}" y1="${(cy+10).toFixed(1)}" x2="${(cx-40).toFixed(1)}" y2="${(cy+40).toFixed(1)}" stroke="${LINE}" stroke-width="3"/><line x1="${(cx+40).toFixed(1)}" y1="${(cy+10).toFixed(1)}" x2="${(cx+40).toFixed(1)}" y2="${(cy+40).toFixed(1)}" stroke="${LINE}" stroke-width="3"/>`;
    if(i<K){const u=t-.2-i*.2,p=SPR(u,.45,12);if(u<=0)continue;sat++;const dy=(1-p)*-60;
      g+=`<g transform="translate(${cx.toFixed(1)},${(cy-40+dy).toFixed(1)})" opacity="${clamp(u*6)}"><circle cx="0" cy="-22" r="18" fill="#E9B98A" stroke="${LINE}" stroke-width="3"/><path d="M-22 18 q22 -34 44 0Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/></g>`}
    else g+=`<rect x="${(cx-22).toFixed(1)}" y="${(cy-70).toFixed(1)}" width="44" height="50" rx="10" fill="none" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6" opacity="${(.45+.2*Math.sin(t*2+i)).toFixed(2)}"/>`}
  g+=`<rect x="320" y="${(h-62).toFixed(1)}" width="248" height="52" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,h-24,`${sat} / ${N}`,38,700,TXT);
  return g},
  sfx(t0,s,E){for(let i=0;i<5;i++)E(t0+.2+i*.2+.1,'tick',{g:.45})}}
