 birthcards:{draw(t,h){const N=+'10',K=+'8';   // 參數：N＝前一年的基準數（十張卡）、K＝今年剩下幾張（8）；缺的 N-K 張只留虛線空位
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-70}" width="888" height="70" fill="#CDB896"/>`;
  const pitch=828/N,cw=Math.min(66,pitch-10),ch=cw*1.38,y0=h/2-ch/2-10;let landed=0;
  for(let i=0;i<N;i++){const cx=30+pitch*(i+.5);
    if(i<K){const u=t-.15-i*.17,p=SPR(u,.5,13);if(u<=0){g+=`<rect x="${(cx-cw/2).toFixed(1)}" y="${y0.toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" rx="8" fill="none" stroke="${LINE}" stroke-width="2" stroke-dasharray="5 6" opacity=".35"/>`;continue}
      landed++;const dy=(1-p)*-150,x=cx,y=y0+dy;
      g+=`<g transform="translate(${x.toFixed(1)},${(y+ch/2).toFixed(1)})" opacity="${clamp(u*8)}"><rect x="${(-cw/2).toFixed(1)}" y="${(-ch/2).toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><circle cx="0" cy="${(-ch*.12).toFixed(1)}" r="${(cw*.2).toFixed(1)}" fill="${LAMP}"/><path d="M${(-cw*.3).toFixed(1)} ${(ch*.34).toFixed(1)} q${(cw*.3).toFixed(1)} ${(-ch*.34).toFixed(1)} ${(cw*.6).toFixed(1)} 0Z" fill="${LAMP}" opacity=".8"/></g>`}
    else{g+=`<rect x="${(cx-cw/2).toFixed(1)}" y="${y0.toFixed(1)}" width="${cw.toFixed(1)}" height="${ch.toFixed(1)}" rx="8" fill="none" stroke="${LINE}" stroke-width="3" stroke-dasharray="7 7" opacity="${(.5+.2*Math.sin(t*2+i)).toFixed(2)}"/>`}}
  // 計數牌：卡一張張落下就一張張加，最後停在 K / N
  g+=`<rect x="320" y="${(h-62).toFixed(1)}" width="248" height="52" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,h-24,`${landed} / ${N}`,38,700,TXT);
  return g},
  sfx(t0,s,E){for(let i=0;i<8;i++)E(t0+.15+i*.17+.1,'tick',{g:.45})}}
