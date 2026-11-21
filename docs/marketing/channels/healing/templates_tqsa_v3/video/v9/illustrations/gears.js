 gears:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EDE4D4"/>`;
  const gear=(cx,cy,R,n,a,c,lab)=>{let d='';for(let i=0;i<n*2;i++){const r=i%2?R:R+16,aa=a+i*Math.PI/n;d+=(i?'L':'M')+(cx+r*Math.cos(aa)).toFixed(1)+' '+(cy+r*Math.sin(aa)).toFixed(1)}return `<path d="${d}Z" fill="${c}" stroke="${LINE}" stroke-width="3"/><circle cx="${cx}" cy="${cy}" r="${R*.55}" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(cx,cy+12,lab,32,700,TXT)}`};
  const sp=t*.8+1.2*(1-Math.exp(-Math.max(0,t-.6)*3))*(t>.6?1:0);
  g+=gear(220,h/2+20,100,12,sp,'#B98A6A','報酬')+gear(444,h/2-30,80,10,-sp*1.25+.2,LAMP,'人數')+gear(650,h/2+30,95,12,sp*1.05+.1,'#C9A27A','物價');
  return g},
  sfx(t0,s,E){E(t0+.6,'click');E(t0+.62,'glide',{f0:300,f1:700,dur:.4,g:.08})}}
