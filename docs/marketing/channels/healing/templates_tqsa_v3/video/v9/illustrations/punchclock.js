 punchclock:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  g+=`<rect x="300" y="60" width="288" height="${h-120}" rx="24" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><circle cx="444" cy="150" r="70" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${444+56*Math.cos(a)}" y1="${150+56*Math.sin(a)}" x2="${444+64*Math.cos(a)}" y2="${150+64*Math.sin(a)}" stroke="${LINE}" stroke-width="3"/>`}
  const mn=(2+(t>.6?1:0)*SPR(t-.6,.4,30))*6*Math.PI/180,sec=(Math.floor(t*2)+SPR((t*2)%1,.45,40))*12*Math.PI/180;
  g+=`<line x1="444" y1="150" x2="${444+46*Math.sin(mn)}" y2="${150-46*Math.cos(mn)}" stroke="${TXT}" stroke-width="6" stroke-linecap="round"/><line x1="444" y1="150" x2="${444+30*Math.sin(Math.PI*5/6)}" y2="${150-30*Math.cos(Math.PI*5/6)}" stroke="${TXT}" stroke-width="8" stroke-linecap="round"/><line x1="444" y1="150" x2="${444+58*Math.sin(sec)}" y2="${150-58*Math.cos(sec)}" stroke="${LAMP}" stroke-width="3"/>`;
  g+=`<rect x="360" y="250" width="168" height="16" rx="6" fill="#4A4744"/>`;
  const ins=SPR(t-.2,.6,12),pop=t>.75?-18*DECAY(t-.75,3,9):0,cy=40+200*ins+pop;g+=`<g transform="translate(0,${cy.toFixed(1)})"><rect x="384" y="-40" width="120" height="180" rx="6" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>${T(444,10,'時薪',32,700,TXT)}<line x1="400" y1="40" x2="488" y2="40" stroke="${LINE}" stroke-width="2" opacity=".5"/></g>`;
  g+=`<rect x="300" y="250" width="288" height="${h-310}" rx="0" fill="#B98A6A"/><rect x="300" y="250" width="288" height="4" fill="${LINE}"/>`;
  if(t>.6&&t<.9)g+=glow(444,262,70,.6*(1-(t-.6)/.3));
  g+=`<rect x="640" y="${h-170}" width="160" height="110" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(720,h-104,'2027',34,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.6,'thump',{g:.4});E(t0+.6,'click');E(t0+.75,'tick')}}
