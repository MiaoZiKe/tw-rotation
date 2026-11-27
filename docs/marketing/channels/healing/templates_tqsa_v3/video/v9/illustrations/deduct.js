 deduct:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  // s6 薪資袋被抽出兩張單：牛皮紙薪資袋立在桌上，「勞保」「健保」兩張小單從袋口依序被抽出、往左上和右上飄開（0.4／0.75，過衝回停、輕晃），袋子每抽一張就變扁一點；右邊「入帳」箭頭跟著變短（2026-11-27 新做，最低工資）
  const a=SPR(t-.4,.45,13),b=SPR(t-.75,.45,13),sq=8*(clamp((t-.4)/.3)+clamp((t-.75)/.3));
  [[a,330,170,'勞保',-8,.4],[b,430,560,'健保',8,.75]].forEach(([p,x0,x1,lab,r,t1])=>{const x=x0+(x1-x0)*p,yy=(h-130)-(h-210)*p,sw=3*DECAY(t-t1-.3,2,9);if(p>0)g+=`<g transform="translate(${x.toFixed(1)},${yy.toFixed(1)}) rotate(${(r*p+sw).toFixed(2)})"><rect x="-62" y="-38" width="124" height="76" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(0,12,lab,32,700,TXT)}</g>`});
  g+=`<rect x="260" y="${(h-180+sq).toFixed(1)}" width="240" height="${(130-sq).toFixed(1)}" rx="12" fill="#D9B48C" stroke="${LINE}" stroke-width="4"/><rect x="260" y="${(h-182+sq).toFixed(1)}" width="240" height="30" rx="10" fill="#C9A27A" stroke="${LINE}" stroke-width="3"/>`+T(380,h-80,'薪資',40,700,TXT);
  const al=140-50*clamp((t-.4)/.8);g+=`<path d="M640 ${h-110} h${al.toFixed(1)}" stroke="${LAMP}" stroke-width="10" stroke-linecap="round"/><path d="M${(640+al).toFixed(1)} ${h-130} l26 20 l-26 20Z" fill="${LAMP}"/>`+T(700,h-140,'入帳',30,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.4,'glide',{f0:500,f1:900,dur:.3,g:.06});E(t0+.75,'glide',{f0:520,f1:940,dur:.3,g:.06})}}
