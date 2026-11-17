 trees:{draw(t,h){let g=`<rect x="0" y="${h-80}" width="888" height="80" fill="#CDB896"/>`;
  const grow=(x,H,a,lv)=>{const p=SPR(t-a,.6,9),hh=H*p;let s=`<rect x="${x-10}" y="${h-80-hh}" width="20" height="${hh.toFixed(1)}" rx="6" fill="#8A5A44"/>`;
   for(let i=0;i<lv;i++){const u=t-a-.3-i*.07,q=SPR(u,.45,16);if(u<=0)continue;const ang=i/lv*Math.PI*2,r=H*.28,cx=x+r*Math.cos(ang)*.9,cy=h-80-hh-10+r*Math.sin(ang)*.6;s+=`<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${(H*.16*Math.max(.01,q)).toFixed(1)}" fill="${i%2?'#9CB38A':'#8FA078'}"/>`}return s};
  g+=grow(250,120,.1,5)+grow(620,190,.4,9);
  const lf=t-1.6;if(lf>0){const y=h-330+lf*90,x=660+30*Math.sin(lf*4);if(y<h-90)g+=`<ellipse cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" rx="12" ry="7" fill="#E9B98A" transform="rotate(${(lf*120).toFixed(0)} ${x.toFixed(1)} ${y.toFixed(1)})"/>`}
  g+=`<rect x="150" y="${h-74}" width="200" height="62" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="2"/>`+T(250,h-29,'25 歲前',44,700,TXT)+`<rect x="530" y="${h-74}" width="180" height="62" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="2"/>`+T(620,h-29,'50 後',44,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:200,f1:500,dur:.4,g:.08});E(t0+.4,'glide',{f0:200,f1:600,dur:.5,g:.1});[0,1,2].forEach(i=>E(t0+.75+i*.14,'sparkle',{n:[22+i*2],g:.5}))}}
