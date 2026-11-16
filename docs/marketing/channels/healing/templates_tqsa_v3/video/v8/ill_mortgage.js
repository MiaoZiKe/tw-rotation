// 談晴說礙 11/20 房貸負擔率影片 量身插圖（2026-11-16；素材登記見 素材登記.md「20261120v_mortgage」）。輪播用過的圓環小屋、鑰匙門牌不再用。
const ILL={
 // s1 公寓大樓＋「售」字布條：布條從頂樓垂下展開（0.2–0.8）、在風裡擺動衰減；陽台盆栽葉子晃、雲飄
 forsale:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E2C8"/>`;
  const cl=(t*16)%1000;g+=`<ellipse cx="${(120+cl)%1000-60}" cy="70" rx="80" ry="24" fill="#FFFDF8" opacity=".8"/><ellipse cx="${(640+cl*.6)%1000-60}" cy="110" rx="60" ry="18" fill="#FFFDF8" opacity=".7"/>`;
  g+=`<rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  g+=`<rect x="240" y="80" width="408" height="${h-140}" fill="#E9D9BF" stroke="${LINE}" stroke-width="4"/>`;
  for(let r=0;r<7;r++)for(let c=0;c<4;c++)g+=`<rect x="${270+c*94}" y="${110+r*52}" width="60" height="34" rx="3" fill="#C9D3C9" stroke="${LINE}" stroke-width="2"/>`;
  g+=`<rect x="410" y="${h-130}" width="68" height="70" fill="#8A5A44" stroke="${LINE}" stroke-width="3"/>`;
  [80,720].forEach((x,i)=>g+=`<rect x="${x}" y="${h-200-i*40}" width="${88}" height="${140+i*40}" fill="#D9C4A0" stroke="${LINE}" stroke-width="3"/>`);
  const un=SPR(t-.2,.6,9),L=260*un,sw=6*DECAY(t-.6,1.6,6)+3*Math.sin(t*3);g+=`<g transform="rotate(${sw.toFixed(2)} 600 84)"><rect x="560" y="84" width="80" height="${L.toFixed(1)}" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/>${L>200?T(600,170,'售',44,700,'#FFFFFF')+T(600,240,'屋',44,700,'#FFFFFF'):''}</g><rect x="548" y="74" width="104" height="14" rx="4" fill="${LINE}"/>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:900,f1:400,dur:.5,g:.08});E(t0+.7,'thump',{g:.25})}},
 // s2 冰箱門：磁鐵把「房貸」帳單貼上（0.3，彈一下）、其他便條依序貼上；冰箱壓縮機燈呼吸、便條角輕翹
 fridge:{draw(t,h){let g=`<rect x="0" y="${h-40}" width="888" height="40" fill="#E4D3B8"/><rect x="250" y="16" width="388" height="${h-56}" rx="24" fill="#E8ECE6" stroke="${LINE}" stroke-width="4"/><line x1="250" y1="130" x2="638" y2="130" stroke="${LINE}" stroke-width="3"/><rect x="600" y="50" width="14" height="60" rx="6" fill="${LINE}"/><rect x="600" y="160" width="14" height="100" rx="6" fill="${LINE}"/>`;
  const notes=[[300,150,'房貸',LAMP,.3,1],[450,170,'水電','#FFFDF8',.7,0],[310,40,'菜錢','#FFFDF8',.9,0],[460,40,'交通','#FFFDF8',1.1,0]];
  notes.forEach(([x,y,l,c,a,hi])=>{const u=t-a,p=SPR(u,.45,15);if(u<=0)return;const fl=4*Math.sin(t*2.5+x);g+=`<g transform="translate(${x},${(y-(1-p)*40).toFixed(1)}) rotate(${(hi?-4:3)})" opacity="${clamp(u*6)}"><rect x="0" y="0" width="${hi?150:120}" height="${hi?110:76}" fill="${c}" stroke="${LINE}" stroke-width="3"/>${T(hi?75:60,hi?66:48,l,32,700,hi?'#FFFFFF':TXT)}<path d="M${hi?150:120} ${hi?110:76} l-18 ${(-4+fl*.4).toFixed(1)} l2 -16Z" fill="#F3EADB"/><circle cx="${hi?75:60}" cy="2" r="10" fill="#B98A6A" stroke="${LINE}" stroke-width="2"/></g>`});
  const ld=.5+.5*tw(t,0,2);g+=`<circle cx="290" cy="${h-70}" r="8" fill="#9CC08A" opacity="${ld.toFixed(2)}"/>`;
  return g},
  sfx(t0,s,E){E(t0+.35,'thump',{g:.3});[.75,.95,1.15].forEach(x=>E(t0+x,'tick',{g:.6}))}},
 // s3 紅綠燈（暖色版）：綠→黃→橘依序切換（0.3／0.7／1.1），停在橘燈，燈罩光暈；旁邊路牌擺一下
 traffic:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-50}" width="888" height="50" fill="#CDB896"/>`;
  g+=`<line x1="660" y1="${h-50}" x2="660" y2="115" stroke="${LINE}" stroke-width="12"/><line x1="636" y1="115" x2="666" y2="115" stroke="${LINE}" stroke-width="12"/><rect x="250" y="40" width="388" height="150" rx="40" fill="#4A4744" stroke="${LINE}" stroke-width="4"/>`;
  const st=t<.3?-1:t<.7?0:t<1.1?1:2,cols=['#9CC08A','#F2D16B',LAMP];[0,1,2].forEach(i=>{const on=i===st;g+=(on?glow(320+i*124,115,90,.55):'')+`<circle cx="${320+i*124}" cy="115" r="46" fill="${on?cols[i]:'#6A6662'}" stroke="${LINE}" stroke-width="3"/>`});
  g+=T(320,236,'可合理',32,700,SUBC)+T(444,236,'略低',32,700,SUBC)+T(568,236,'偏低',32,700,st===2?HINT:SUBC);
  const sw=8*DECAY(t-1.1,2,8);g+=`<g transform="rotate(${sw.toFixed(1)} 780 ${h-180})"><line x1="780" y1="${h-50}" x2="780" y2="${h-180}" stroke="${LINE}" stroke-width="6"/><rect x="706" y="${h-240}" width="148" height="70" rx="10" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>${T(780,h-193,'41.46%',32,700,TXT)}</g>`;
  return g},
  sfx(t0,s,E){[.3,.7,1.1].forEach(x=>E(t0+x,'click'));E(t0+1.1,'bell',{n:[17],g:.35})}},
 // s4 玄關鞋櫃：一家人的鞋（大中小三雙）先排好，再「啪」放進一雙新的布鞋（1.0），布鞋鞋帶甩動衰減
 shoerack:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="0" y="${h-60}" width="888" height="60" fill="#C9A27A"/>`;
  g+=`<rect x="80" y="40" width="728" height="${h-110}" rx="12" fill="#D9B48C" stroke="${LINE}" stroke-width="4"/><line x1="80" y1="${(h-70)/2+20}" x2="808" y2="${(h-70)/2+20}" stroke="${LINE}" stroke-width="4"/>`;
  const shoe=(x,y,w,c)=>`<path d="M${x} ${y} h${w*.65} q${w*.35} 0 ${w*.35} ${w*.4} h-${w}Z" fill="${c}" stroke="${LINE}" stroke-width="2"/>`;
  [[130,170,'#6E4636'],[330,140,'#9C6A50'],[510,100,'#E9B98A']].forEach(([x,w,c],i)=>{const u=t-.1-i*.18,p=SPR(u,.5,14);if(u<=0)return;const y=(h-70)/2+20-(1-p)*30;g+=`<g opacity="${clamp(u*6)}">${shoe(x,y,w*.5,c)}${shoe(x+w*.55,y,w*.5,c)}</g>`});
  const u=t-1.0,p=SPR(u,.4,16);if(u>0){const y=(h-60)-(1-p)*80,lc=14*DECAY(u,2.2,9);g+=`<g>${shoe(560,y,120,'#FFFDF8')}${shoe(690,y,120,'#FFFDF8')}<path d="M600 ${y-14} q20 ${(-20+lc).toFixed(1)} 40 0" stroke="${LAMP}" stroke-width="5" fill="none"/></g>`}
  g+=T(340,90,'家戶',32,700,SUBC)+T(680,(h-70)/2+80,'剛出社會',32,700,HINT);
  return g},
  sfx(t0,s,E){[.1,.28,.46].forEach(x=>E(t0+x+.12,'tick',{g:.5}));E(t0+1.1,'thump',{g:.3})}},
 // s5 計算機：按鍵依序被按下（0.2–1.2，按下＝位移不縮放）、螢幕數字跳、最後一下「=」亮橘；紙捲尾端輕擺
 calculator:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/><rect x="270" y="20" width="348" height="${h-70}" rx="28" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/><rect x="300" y="44" width="288" height="70" rx="10" fill="#DCE3CF" stroke="${LINE}" stroke-width="3"/>`;
  const seq=[0,5,10,3,7,15],at=k=>.2+k*.2;let pressed=-1;seq.forEach((k,i)=>{if(t>=at(i)&&t<at(i)+.14)pressed=k});
  const shown=['7','70%','20','20 年','×','='][Math.min(5,Math.max(0,Math.floor((t-.2)/.2)))]||'';g+=T(570,96,t<.2?'0':shown,36,700,TXT,'end');
  for(let r=0;r<4;r++)for(let c=0;c<4;c++){const k=r*4+c,dn=k===pressed?5:0,eq=k===15&&t>1.2;g+=`<rect x="${300+c*74}" y="${(134+r*(h-210)/4+dn).toFixed(1)}" width="62" height="${((h-210)/4-12).toFixed(1)}" rx="10" fill="${eq?LAMP:'#F3EADB'}" stroke="${LINE}" stroke-width="2"/>`}
  const rl=10*Math.sin(t*2);g+=`<path d="M630 ${h-50} q60 ${-30-rl} 120 -40 v-120 q-60 10 -120 40Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><line x1="650" y1="${h-140}" x2="730" y2="${h-170}" stroke="${LINE}" stroke-width="2" opacity=".4"/>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<6;i++)E(t0+.2+i*.2,'tick',{g:.7});E(t0+1.25,'bell',{n:[19],g:.35})}},
 // s6 疊磚：九塊半磚一塊塊疊上（每塊＝一年所得，示意 9.47 年），最後那塊只有一半、落下時晃一下
 bricks:{draw(t,h){let g=`<rect x="0" y="${h-40}" width="888" height="40" fill="#E4D3B8"/>`;
  for(let i=0;i<10;i++){const u=t-.1-i*.11,p=SPR(u,.5,16);if(u<=0)continue;const half=i===9,w=half?110*.47*2:220,row=Math.floor(i/2),col=i%2,x=(row%2?260:240)+col*230,y=h-40-38*(row+1)-(1-p)*60;
   g+=`<rect x="${x}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="34" rx="4" fill="${half?LAMP:'#B98A6A'}" stroke="${LINE}" stroke-width="2" opacity="${clamp(u*8)}" ${half?`transform="rotate(${(4*DECAY(u-.15,4,14)).toFixed(1)} ${x} ${y})"`:''}/>`}
  g+=`<rect x="640" y="50" width="200" height="80" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(740,104,'約 9.47 年',32,700,TXT);
  g+=T(150,104,'1 塊＝1 年',32,400,SUBC);
  return g},
  sfx(t0,s,E){for(let i=0;i<10;i+=2)E(t0+.1+i*.11+.1,'tick',{g:.6});E(t0+1.2,'thump',{g:.25})}},
 // s7 信箱：信箱小旗由下往上翻起（0.4，過衝回彈）、信箱門打開一點、裡面空空的；樹影晃
 mailbox:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-70}" width="888" height="70" fill="#CDB896"/>`;
  g+=`<line x1="444" y1="${h-70}" x2="444" y2="250" stroke="${LINE}" stroke-width="12"/><path d="M300 250 v-120 q0 -90 144 -90 q144 0 144 90 v120Z" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  const dr=-35*SPR(t-.9,.5,10);g+=`<g transform="rotate(${dr.toFixed(1)} 300 250)"><path d="M300 250 v-120 q0 -90 30 -90 v210Z" fill="#9C6A50" stroke="${LINE}" stroke-width="3"/></g>`;
  const fa=-90*SPR(t-.4,.38,13);g+=`<g transform="rotate(${fa.toFixed(1)} 600 200)"><rect x="596" y="196" width="140" height="12" fill="${LINE}"/><rect x="700" y="170" width="50" height="40" fill="${LAMP}" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<rect x="380" y="270" width="128" height="50" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(444,306,'號 ?',32,700,TXT);
  const sw=6*Math.sin(t*1.6);g+=`<path d="M60 ${h-70} v-200" stroke="#8A6A52" stroke-width="14"/><circle cx="${60+sw}" cy="${h-300}" r="70" fill="#9CB38A" opacity=".85"/><circle cx="${110+sw*1.2}" cy="${h-260}" r="50" fill="#8FA078" opacity=".85"/>`;
  return g},
  sfx(t0,s,E){E(t0+.4,'click');E(t0+.9,'glide',{f0:400,f1:250,dur:.3,g:.07})}},
 // s8 里程碑：一條長路通往遠方，路邊里程碑一個個彈出（2026 → 2031 的方向），最後一個寫「?」；路上光點往前流
 milestone:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/><path d="M0 ${h} L380 120 L508 120 L888 ${h}Z" fill="#D9C4A0"/><path d="M444 ${h} L444 120" stroke="#FFFDF8" stroke-width="6" stroke-dasharray="24 22"/>`;
  [[180,h-90,1],[290,h-190,.8],[360,h-250,.62],[400,h-290,.5]].forEach(([x,y,sc],i)=>{const u=t-.2-i*.22,p=SPR(u,.45,16);if(u<=0)return;g+=`<g transform="translate(${x},${y}) scale(${(sc*Math.max(.01,p)).toFixed(3)})"><path d="M-40 0 v-70 q0 -30 40 -30 q40 0 40 30 v70Z" fill="${i===3?LAMP:FACE3}" stroke="${LINE}" stroke-width="4"/></g>`});
  for(let k=0;k<6;k++){const u=((t*.5+k/6)%1);g+=`<circle cx="444" cy="${(h-u*(h-140)).toFixed(1)}" r="${(8-6*u).toFixed(1)}" fill="#FFF4D6" opacity="${(.8*(1-u)).toFixed(2)}"/>`}
  g+=`<rect x="600" y="40" width="220" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(710,88,'退休那天',32,700,TXT);
  return g},
  sfx(t0,s,E){[0,1,2,3].forEach(i=>E(t0+.2+i*.22+.08,'tick',{g:.6}));E(t0+.95,'pop')}}
};
