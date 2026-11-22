 bento:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E2C8"/><rect x="0" y="${h-80}" width="888" height="80" fill="#CDB896"/>`;
  // 外食便當：便當盒滑上桌（0.2，過衝回停）→ 蓋子掀開（0.6，翻起回彈）→ 熱氣上升 → 價格標籤從右邊彈出、標「外食費」，箭頭往上長（漲幅），標籤輕晃衰減
  const sl=SPR(t-.2,.5,11),bx=444-(1-sl)*520,by=h-80-150;
  g+=`<g transform="translate(${bx.toFixed(1)},0)"><rect x="-210" y="${by}" width="420" height="150" rx="18" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><rect x="-190" y="${by+18}" width="190" height="114" rx="10" fill="#F4D0A0" stroke="${LINE}" stroke-width="2.5"/><rect x="12" y="${by+18}" width="178" height="52" rx="10" fill="#9CB38A" stroke="${LINE}" stroke-width="2.5"/><rect x="12" y="${by+80}" width="178" height="52" rx="10" fill="#E9B98A" stroke="${LINE}" stroke-width="2.5"/><circle cx="-95" cy="${by+75}" r="34" fill="#FFFFFF" stroke="${LINE}" stroke-width="2"/>`;
  const op=SPR(t-.6,.5,9),ang=-68*op;
  g+=`<g transform="rotate(${ang.toFixed(1)} -210 ${by})"><rect x="-216" y="${by-26}" width="432" height="30" rx="12" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/></g>`;
  if(op>.5)for(let i=0;i<3;i++){const p=((t*0.7+i/3)%1),x=-120+i*120,y=by-20-p*150;g+=`<path d="M${x} ${y.toFixed(1)} q12 -18 0 -36 q-12 -18 0 -36" fill="none" stroke="#FFFDF8" stroke-width="5" stroke-linecap="round" opacity="${(1-p).toFixed(2)}"/>`}
  g+=`</g>`;
  const tg=SPR(t-1.0,.5,10),sw=8*DECAY(t-1.2,1.4,6);
  if(tg>0){g+=`<g opacity="${clamp(tg*2)}" transform="translate(${(1-tg)*200},0) rotate(${sw.toFixed(2)} 700 110)"><line x1="700" y1="60" x2="700" y2="110" stroke="${LINE}" stroke-width="3"/><rect x="590" y="110" width="220" height="130" rx="14" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/>${T(700,160,'外食費',34,700,SUBC)}${T(700,214,'年增',34,700,TXT)}</g>`;
   const ar=clamp((t-1.3)*1.6);g+=`<g opacity="${clamp(ar*3)}"><line x1="150" y1="${h-260}" x2="150" y2="${(h-260-150*ar).toFixed(1)}" stroke="${LAMP}" stroke-width="12" stroke-linecap="round"/><path d="M120 ${(h-240-150*ar).toFixed(1)} l30 -40 l30 40Z" fill="${LAMP}"/></g>`}
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:500,f1:900,dur:.4,g:.07});E(t0+.65,'thump',{g:.22});E(t0+1.05,'tick',{g:.45})}}
