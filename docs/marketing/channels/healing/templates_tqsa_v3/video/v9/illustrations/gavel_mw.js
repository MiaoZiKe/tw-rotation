 gavel_mw:{draw(t0_,h){const S1=4.1,t=(t0_>=S1-.55)?t0_-(S1-.55):t0_;let g=`<rect x="0" y="${h-130}" width="888" height="130" fill="#B48A60"/><rect x="0" y="${h-140}" width="888" height="14" fill="#9C7450"/>`;
  [[150,'#E9B98A'],[444,'#E0C9A6'],[738,'#E9B98A']].forEach(([x,c],i)=>{const on=clamp((t-1.0-i*.18)*6);g+=`<line x1="${x}" y1="${h-140}" x2="${x+30}" y2="${h-230}" stroke="${LINE}" stroke-width="5"/><circle cx="${x+34}" cy="${h-238}" r="12" fill="${on>.5?'#E36B4A':'#B9B2A8'}" stroke="${LINE}" stroke-width="2"/>`+(on>0?glow(x+34,h-238,30,.5*on):'')});
  const hop=t>.55?-14*Math.abs(DECAY(t-.55,5,16)):0;g+=`<g transform="translate(0,${hop.toFixed(1)})"><rect x="200" y="${h-190}" width="200" height="40" rx="4" fill="#FFFDF8" stroke="${LINE}" stroke-width="2" transform="rotate(-3 300 ${h-170})"/><rect x="230" y="${h-180}" width="190" height="34" rx="4" fill="#F3EADB" stroke="${LINE}" stroke-width="2" transform="rotate(4 320 ${h-160})"/></g>`;
  const jo=t>.55?3*DECAY(t-.55,8,30):0;g+=`<ellipse cx="560" cy="${h-150+jo}" rx="80" ry="18" fill="#6E4636" stroke="${LINE}" stroke-width="3"/>`;
  let a=t<.35?-30*EO(t/.35):t<.55?-30+30*Math.pow((t-.35)/.2,2)+0:8*DECAY(t-.55,6,18);a-=0;const ang=t<.55?(t<.35?-40*EO(t/.35):-40+40*Math.pow((t-.35)/.2,2)):6*DECAY(t-.55,6,18);
  g+=`<g transform="rotate(${ang.toFixed(1)} 700 ${h-210})"><line x1="700" y1="${h-210}" x2="590" y2="${h-180}" stroke="#8A5A44" stroke-width="16" stroke-linecap="round"/><rect x="530" y="${h-230}" width="70" height="90" rx="14" fill="#8A5A44" stroke="${LINE}" stroke-width="3" transform="rotate(-15 565 ${h-185})"/></g>`;
  if(t>.55&&t<.95){const k=(t-.55)/.4;g+=`<ellipse cx="560" cy="${h-150}" rx="${90+90*k}" ry="${20+16*k}" fill="none" stroke="${LAMP}" stroke-width="4" opacity="${(.7*(1-k)).toFixed(2)}"/>`}
  g+=`<rect x="300" y="40" width="288" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,88,'審議會',34,700,TXT);

  {const T0=t0_;
   // 日曆：9 月（九月決議 t≈2.0）→ 10/1（行政院十月一日 t≈3.5）→ 1/1（明年起 t≈4.8）
   const cp=clamp((T0-1.95)*5);if(cp>0){const lab=T0<3.5?'9月':T0<4.8?'10/1':'1/1';const fl=[3.5,4.8].map(x=>T0>x&&T0<x+.2?Math.abs(Math.cos((T0-x)/.2*Math.PI/2)):1).reduce((a,b)=>a*b,1);
    g+=`<g opacity="${cp.toFixed(2)}" transform="translate(75,${(86-(1-cp)*20).toFixed(1)}) scale(1,${fl.toFixed(2)})"><rect x="-52" y="-44" width="104" height="88" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><rect x="-52" y="-44" width="104" height="26" rx="10" fill="#E36B4A" stroke="${LINE}" stroke-width="3"/>`+T(0,28,lab,38,700,TXT)+`</g>`}
   // 核定章：t=4.1 蓋下（核 11.34）
   const sp=T0-S1;if(sp>0){const sc=1+1.2*Math.max(0,1-sp/.18)+(-.06)*DECAY(sp-.18,9,22);const rot=-10;
    g+=`<g transform="translate(830,92) rotate(${rot}) scale(${sc.toFixed(3)})"><circle r="44" fill="none" stroke="#E36B4A" stroke-width="6" opacity="${clamp(sp*8).toFixed(2)}"/>`+T(0,14,'核定',40,700,'#E36B4A')+`</g>`}
   // 金幣：從兩萬九千五起（6.2）三枚依序落到桌上，8.0 起 +1,400 箭頭（漲到三萬零九百 8.3）
   [6.2,6.8,7.4].forEach((c0,k)=>{const q=T0-c0;if(q<=0)return;const fall=clamp(q/.28);const y=300-k*18-(1-fall*fall)*130-(q>.28?10*Math.abs(DECAY(q-.28,7,16)):0);
    g+=`<ellipse cx="770" cy="${(y+8).toFixed(1)}" rx="48" ry="13" fill="#D9A441" stroke="${LINE}" stroke-width="3"/><ellipse cx="770" cy="${y.toFixed(1)}" rx="48" ry="13" fill="#F4B860" stroke="${LINE}" stroke-width="3"/>`});
   const ap=clamp((T0-7.9)*4);if(ap>0){g+=`<g opacity="${ap.toFixed(2)}" transform="translate(0,${((1-ap)*18).toFixed(1)})"><path d="M628 92 L654 56 L680 92 L664 92 L664 104 L644 104 L644 92 Z" fill="#E36B4A" stroke="${LINE}" stroke-width="3" stroke-linejoin="round"/>`+T(740,92,'+1,400',34,700,'#E36B4A')+`</g>`}
  }
  return g},
  sfx(t0,s,E){E(t0+4.1,'thump',{g:.6});E(t0+4.1,'stamp',{g:.7});E(t0+.55,'thump',{g:.6});E(t0+.55,'click');[0,1,2].forEach(i=>E(t0+1.0+i*.18,'tick'))}}
