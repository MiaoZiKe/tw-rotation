 outro(s,lt,d){
  const f=lt*30,KW=kwF(s),P=(a,n,fn)=>(fn||EO)((f-a)/n),SC2=2.0,MY=681,BASE=1092;
  const fin=f-OF.fin,flash=fin>=0?Math.exp(-fin/8):0;
  const rise=P(OF.cloud,OF.land-OF.cloud,x=>1-Math.pow(1-x,3)),lu=(f-OF.land)/30;
  let cy=(1-rise)*620,csy=1+.12*Math.sin(Math.PI*clamp(f/OF.land)),csx=1-.08*Math.sin(Math.PI*clamp(f/OF.land));
  if(f>=OF.land){const q=.17*DECOS(lu,9,30);csy=1-q;csx=1+.7*q;cy=-12*Math.max(0,DECAY(lu,7,20))}
  const C='M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z',A='M -26.3 -78.5 A 110 110 0 0 1 170.1 13.1',cx=63.9,cy0=-15.5;
  const su=(f-OF.sun)/30,sy=(1-SPR(su,.4,9))*90,sop=clamp((f-OF.sun)/3);
  let rays='';[-135,-90,-45].forEach((a,i)=>{const u=f-OF.ray[i];if(u<0)return;const ra=a*Math.PI/180,r0=140,r1=184,p=BACK(u/7),re=r0+(r1-r0)*Math.min(p,1.12),wd=22+10*Math.exp(-u/3)+6*flash,ex=cx+re*Math.cos(ra),ey=cy0+re*Math.sin(ra);
   rays+=`<line x1="${cx+r0*Math.cos(ra)}" y1="${cy0+r0*Math.sin(ra)}" x2="${ex}" y2="${ey}" stroke="#C5782B" stroke-width="${wd.toFixed(1)}" stroke-linecap="round"/>`;
   if(u<14){const k=u/14,s0=34*Math.sin(Math.PI*clamp(u/9));rays+=sparkle(cx+(r1+16)*Math.cos(ra),cy0+(r1+16)*Math.sin(ra),s0,1-k);
    for(let q=0;q<5;q++){const da=ra+(q-2)*.42,dist=r1+10+(18+q*5)*EO(k);rays+=`<circle cx="${(cx+dist*Math.cos(da)).toFixed(1)}" cy="${(cy0+dist*Math.sin(da)).toFixed(1)}" r="${(5*(1-k)).toFixed(1)}" fill="#F4B860" opacity="${(.9*(1-k)).toFixed(2)}"/>`}}});
  const rf=[0,1,2].reduce((a,i)=>a+(f>=OF.ray[i]?Math.exp(-(f-OF.ray[i])/5):0),0);
  const gu=(f-OF.glint)/24;      // 靜止段光掃（≤0.8 秒）：一點亮光沿太陽弧走過，四字同時被掃過一次
  const glintArc=gu>0&&gu<1?`<path d="${A}" pathLength="1" fill="none" stroke="#FFF3D0" stroke-width="14" stroke-linecap="round" stroke-dasharray="0.16 3" stroke-dashoffset="${(-(gu*.86)).toFixed(3)}" opacity="${(.95*Math.sin(Math.PI*gu)).toFixed(2)}"/>`:'';
  let shx=0,shy=0;[0,1,2,3].forEach(i=>{const u=f-(OF.ch[i]+OF.imp);if(u>=0&&u<14){const am=4.5*Math.exp(-u/3.2);shx+=am*Math.sin(u*2.2);shy+=am*.6*Math.cos(u*2.9)}});
  const sunG=`<g transform="translate(${cx},${cy0+sy}) translate(0,0)" opacity="${sop}"><g transform="translate(${-cx},${-cy0})"><path d="${A}" fill="none" stroke="#C5782B" stroke-width="${(22+4*flash+3*rf).toFixed(1)}" stroke-linecap="round"/>${glintArc}${rays}</g></g>`;
  let g=DEFS;
  g+=glow(444,760,Math.min(440,120+320*EO(fin/16)),fin<0?0:Math.min(.5,.12+.45*Math.exp(-fin/12)));
  g+=glow(444+SC2*(cx-35),MY+SC2*(cy0-40+sy),300,.2*sop*clamp((f-OF.sun)/8)+.16*rf+.45*flash);
  g+=`<g transform="translate(${shx.toFixed(1)},${shy.toFixed(1)})">`;
  g+=`<g transform="translate(444,${MY}) scale(${SC2}) translate(-35,-40)"><g data-chk="logo">${sunG}<g transform="translate(15,${120+cy/SC2}) scale(${csx.toFixed(3)},${csy.toFixed(3)}) translate(-15,-120)"><path d="${C}" fill="${FACE3}" stroke="#6E6A66" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/></g></g></g>`;
  const chars=[['談','#2F2D2B'],['晴','#98622B'],['說','#2F2D2B'],['礙','#8A5A44']];let tx='';
  chars.forEach((c,i)=>{const u=f-OF.ch[i];if(u<0)return;const x=444+(i-1.5)*196,k=clamp(u/OF.imp);let y=BASE-28*(1-k*k),ssy=1.10-.10*k,ssx=1-.05*k;
   if(u>OF.imp){const us=(u-OF.imp)/30,q=.24*DECOS(us,11,32);ssy=1-q;ssx=1+.6*q;y=BASE}
   const sc=fin>=0?1+.05*Math.exp(-fin/6):1;
   tx+=`<g transform="translate(${x},${y.toFixed(1)}) scale(${(ssx*sc).toFixed(3)},${(ssy*sc).toFixed(3)})" opacity="${clamp(u/2)}"><text x="0" y="0" text-anchor="middle" font-family="Noto Serif CJK TC" font-weight="700" font-size="172" fill="${c[1]}">${c[0]}</text><rect data-chk="char" x="-86" y="-150" width="172" height="164" fill="none"/></g>`;
   const iu=u-OF.imp;if(iu>0){const r=EO(iu/12);if(r<1){g+=`<ellipse cx="${x}" cy="${BASE+22}" rx="${(34+80*r).toFixed(1)}" ry="${(7+10*r).toFixed(1)}" fill="none" stroke="#C5782B" stroke-width="3" opacity="${(.45*(1-r)).toFixed(2)}"/>`;
    [-1,1].forEach(sg=>g+=`<circle cx="${(x+sg*(40+46*r)).toFixed(1)}" cy="${(BASE+16-14*Math.sin(Math.PI*r)).toFixed(1)}" r="${(5*(1-r)).toFixed(1)}" fill="#C5782B" opacity="${(.5*(1-r)).toFixed(2)}"/>`)}}});
  g+=tx;
  const sweep=(p0,span,t0)=>{const k=(f-t0)/span;if(k<=0||k>=1)return'';const sx=-160+1260*EO(k);return `<clipPath id="txc${t0}">${chars.map((c,i)=>`<text x="0" y="0" text-anchor="middle" transform="translate(${444+(i-1.5)*196},${BASE})" font-family="Noto Serif CJK TC" font-weight="700" font-size="172">${c[0]}</text>`).join('')}</clipPath><g clip-path="url(#txc${t0})"><path d="M${sx} ${BASE-170} l90 0 l-50 240 l-90 0Z" fill="#FFF4D6" opacity="${p0}"/></g>`};
  g+=sweep(.75,14,OF.fin)+sweep(.6,24,OF.glint);
  g+=`</g>`;
  const sl=P(OF.slog,10);if(sl>0)g+=`<g opacity="${sl}" transform="translate(${(1-sl)*-50},0)">${T(444,1180,s.slogan,44,400,SUBC)}</g>`;
  const nx=P(OF.next,12,BACK);if(nx>0)g+=`<g opacity="${clamp(nx*2)}" transform="translate(${(1-nx)*70},0)"><rect x="84" y="1214" width="720" height="88" rx="44" fill="${FACE}" stroke="${LINE}" stroke-width="2.5"/>${T(444,1274,s.nextLine,42,700,TXT)}</g>`;
  if(s.keyword){const kw=P(KW,12,BACK);if(kw>0)g+=`<g opacity="${clamp(kw*2)}" transform="translate(444,1388) scale(${(.8+.2*kw).toFixed(3)}) translate(-444,-1388)"><rect x="104" y="1342" width="680" height="92" rx="46" fill="#C5782B"/><text x="444" y="1406" text-anchor="middle" font-family="Noto Sans CJK TC" font-weight="700" font-size="46" fill="#FFFFFF">${s.keyword==='@FIXED'?'留言拿完整資料':`留言「<tspan font-size="58" font-weight="900">${esc(s.keyword)}</tspan>」拿完整資料`}</text></g>`}
  return box('mark',150,1540,g,lt,d,{})}
};

// ───────── 情境插圖（本篇量身，素材登記見 素材登記.md）─────────
// v4 動畫原則（Andy 11-15「不要出現圖片一直慢慢放大」）：插圖面板固定不縮放、不平移；只有「物件」在動——
//   預備動作（反向一點點）→ 主動作 → 過衝 → 阻尼回彈；多個物件錯開（stagger）；擺盪一律指數衰減後靜止（不一直擺、不一直閃）。
//   時間點全部放在 TM，畫面與音效（sfxEvents）讀同一份，所以聲音與動作同一幀。
