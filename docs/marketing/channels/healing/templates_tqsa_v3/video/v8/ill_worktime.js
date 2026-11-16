// 談晴說礙 年總工時影片（talk-ep01 v8 重做）量身插圖（2026-11-16；素材登記見 素材登記.md「20261116v_worktime v8」）。
// 不沿用 ai-mp4 Remotion 版畫面；不用窗燈依序亮（結婚 v3 用過）、年曆、蛋糕、婚紗店。
const ILL={
 // s1 傍晚的辦公大樓門口：天色由暖橘轉成深暖灰（0–1.2）、門口路燈「喀」亮起（0.6）、大樓時鐘指在 7 點多（分針走）、自動門開一下
 nightoffice:{draw(t,h){const k=clamp(t/1.2);const sky=`rgb(${Math.round(243-120*k)},${Math.round(214-120*k)},${Math.round(178-100*k)})`;
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="${sky}"/><circle cx="740" cy="${(120-30*k).toFixed(1)}" r="34" fill="#FFF1D2" opacity="${(.3+.6*k).toFixed(2)}"/>`;
  for(let i=0;i<14;i++){const x=(i*137)%860+14,y=(i*71)%180+20;g+=`<circle cx="${x}" cy="${y}" r="2.5" fill="#FFF8E6" opacity="${(k*(.4+.4*tw(t,i,2))).toFixed(2)}"/>`}
  g+=`<rect x="0" y="${h-90}" width="888" height="90" fill="#8E7E6E"/><rect x="200" y="120" width="488" height="${h-210}" fill="#A99682" stroke="${LINE}" stroke-width="4"/>`;
  for(let r=0;r<5;r++)for(let c=0;c<6;c++)g+=`<rect x="${226+c*76}" y="${200+r*44}" width="52" height="26" rx="3" fill="#8E8070"/>`;
  g+=`<circle cx="444" cy="150" r="34" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`;const mn=(40+t*20)*Math.PI/30;g+=`<line x1="444" y1="150" x2="${444+24*Math.sin(mn)}" y2="${150-24*Math.cos(mn)}" stroke="${TXT}" stroke-width="4"/><line x1="444" y1="150" x2="${444+16*Math.sin(Math.PI*7/6+.1)}" y2="${150-16*Math.cos(Math.PI*7/6+.1)}" stroke="${TXT}" stroke-width="5"/>`;
  const dr=t>1.4?34*Math.sin(Math.PI*clamp((t-1.4)/1.2)):0;g+=`<rect x="384" y="${h-200}" width="120" height="110" fill="#E9D9BF"/><rect x="${384-dr}" y="${h-200}" width="60" height="110" fill="#C9D3C9" stroke="${LINE}" stroke-width="3"/><rect x="${444+dr}" y="${h-200}" width="60" height="110" fill="#C9D3C9" stroke="${LINE}" stroke-width="3"/>`;
  const on=t<.6?0:t<.66?1:t<.72?.3:1;g+=(on?glow(110,h-300,110,.6*on):'')+`<line x1="110" y1="${h-90}" x2="110" y2="${h-290}" stroke="${LINE}" stroke-width="7"/><path d="M90 ${h-300} h40 l-6 -20 h-28Z" fill="${on>.5?'#FFE9B8':'#B9B2A8'}" stroke="${LINE}" stroke-width="2"/>`;
  return g},
  sfx(t0,s,E){E(t0+.6,'click');E(t0+.66,'click');E(t0+1.4,'glide',{f0:500,f1:300,dur:.4,g:.06})}},
 // s2 碼錶：按鈕按下（0.2）指針一圈圈快轉，0.9 停住；旁邊工作日誌一頁頁翻（每頁 0.2 秒）
 stopwatch:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;const cx=300,cy=h/2+10;
  const pr2=t>.2&&t<.3?6:0;g+=`<rect x="${cx-18}" y="${cy-150+pr2}" width="36" height="26" rx="6" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><circle cx="${cx}" cy="${cy}" r="120" fill="${FACE3}" stroke="${LINE}" stroke-width="8"/>`;
  for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${cx+100*Math.sin(a)}" y1="${cy-100*Math.cos(a)}" x2="${cx+110*Math.sin(a)}" y2="${cy-110*Math.cos(a)}" stroke="${LINE}" stroke-width="3"/>`}
  const a=t<.2?0:(t<.9?(t-.2)*30:21+.3*DECAY(t-.9,4,14))+t*.15;g+=`<line x1="${cx}" y1="${cy}" x2="${(cx+92*Math.sin(a)).toFixed(1)}" y2="${(cy-92*Math.cos(a)).toFixed(1)}" stroke="${LAMP}" stroke-width="6" stroke-linecap="round"/><circle cx="${cx}" cy="${cy}" r="10" fill="${LINE}"/>`;
  g+=`<rect x="520" y="${h-260}" width="260" height="200" rx="8" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(650,h-210,'工時紀錄',32,700,TXT);
  for(let i=0;i<5;i++){const u=clamp((t-.3-i*.2)/.18);if(u>0&&u<1)g+=`<path d="M780 ${h-260} q${-130*u} -30 ${-260*u} 0 v200 q${130*u} -30 ${260*u} 0" fill="#F6EFE2" stroke="${LINE}" stroke-width="2"/>`}
  for(let i=0;i<3;i++)g+=`<line x1="548" y1="${h-170+i*36}" x2="${740-(i%2)*50}" y2="${h-170+i*36}" stroke="${LINE}" stroke-width="2" opacity=".4"/>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'click');E(t0+.9,'bell',{n:[19],g:.35});for(let i=0;i<5;i++)E(t0+.35+i*.2,'tick',{g:.4})}},
 // s3 辦公桌：辦公椅從右滑進桌下（0.2）、螢幕開機亮起（0.6）、便利貼一張張貼上螢幕邊（0.9／1.1）、咖啡蒸氣
 officedesk:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#D9C4A0"/><rect x="120" y="${h-160}" width="560" height="22" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><rect x="140" y="${h-138}" width="16" height="78" fill="${LINE}"/><rect x="644" y="${h-138}" width="16" height="78" fill="${LINE}"/>`;
  const on=clamp((t-.6)*6);g+=`<rect x="260" y="${h-330}" width="260" height="160" rx="12" fill="#4A4744" stroke="${LINE}" stroke-width="4"/><rect x="274" y="${h-316}" width="232" height="128" rx="6" fill="${on>.5?'#F7E7CB':'#3A3836'}"/><rect x="370" y="${h-170}" width="40" height="12" fill="${LINE}"/>`;
  if(on>.5)for(let i=0;i<3;i++)g+=`<rect x="292" y="${h-296+i*30}" width="${160-i*30}" height="14" rx="4" fill="#E9B98A" opacity=".8"/>`;
  [[.9,530,h-320,'#F4D27A'],[1.1,530,h-260,'#F6C0A0']].forEach(([a,x,y,c])=>{const p=SPR(t-a,.45,15);if(t>a)g+=`<rect x="${x}" y="${(y-(1-p)*30).toFixed(1)}" width="56" height="50" fill="${c}" stroke="${LINE}" stroke-width="2" transform="rotate(5 ${x} ${y})"/>`});
  g+=`<rect x="580" y="${h-210}" width="56" height="50" rx="8" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/><path d="M596 ${h-218} q8 -20 0 -40" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.2+.3*tw(t,0,2.4)).toFixed(2)}"/>`;
  const cx=740+120*(1-SPR(t-.2,.6,9));g+=`<g transform="translate(${cx.toFixed(1)},${h-60})"><rect x="-50" y="-150" width="100" height="90" rx="20" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><rect x="-50" y="-70" width="100" height="22" rx="8" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><line x1="0" y1="-48" x2="0" y2="-14" stroke="${LINE}" stroke-width="6"/><circle cx="-30" cy="-6" r="8" fill="${LINE}"/><circle cx="30" cy="-6" r="8" fill="${LINE}"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:500,f1:300,dur:.4,g:.07});E(t0+.6,'bell',{n:[24],g:.3});E(t0+.9,'tick');E(t0+1.1,'tick')}},
 // s4 通勤列車：列車從右開進月台減速停住（0.1–1.0，車廂間輕撞回彈），車門燈亮；月台時鐘秒針走
 train:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EDE2D0"/><rect x="0" y="${h-70}" width="888" height="70" fill="#C9B9A2"/><rect x="0" y="${h-80}" width="888" height="12" fill="#F4D27A"/>`;
  const p=1-Math.exp(-Math.max(0,t-.1)*3.2),x=900-760*p+(t>1.0?4*DECAY(t-1.0,5,14):0);
  for(let c=0;c<3;c++){const cx=x+c*290+(t>.9?2*c*DECAY(t-.9,5,16):0);g+=`<rect x="${cx.toFixed(1)}" y="${h-250}" width="280" height="160" rx="22" fill="#E9E4DA" stroke="${LINE}" stroke-width="4"/><rect x="${(cx).toFixed(1)}" y="${h-130}" width="280" height="14" fill="${LAMP}"/>`;
   for(let wi=0;wi<3;wi++)g+=`<rect x="${(cx+24+wi*86).toFixed(1)}" y="${h-226}" width="64" height="56" rx="8" fill="#C9D3C9" stroke="${LINE}" stroke-width="2"/>`}
  g+=`<circle cx="150" cy="80" r="44" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/>`;const sc=(Math.floor(t*2)+SPR((t*2)%1,.45,40))*Math.PI/30*6;g+=`<line x1="150" y1="80" x2="${150+36*Math.sin(sc)}" y2="${80-36*Math.cos(sc)}" stroke="${LAMP}" stroke-width="3"/><line x1="150" y1="80" x2="150" y2="52" stroke="${TXT}" stroke-width="5"/>`;
  return g},
  sfx(t0,s,E){E(t0+.1,'glide',{f0:300,f1:120,dur:.9,g:.1});E(t0+1.0,'thump',{g:.3})}},
 // s5 國定假日：一串節慶旗由左往右展開，新增的幾面「假」字旗彈出（0.6／0.8／1.0）並擺動衰減
 holiday:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E6D0"/>`;
  const sp=SPR(t-.05,.6,8);let d='M30 80';for(let x=30;x<=30+828*sp;x+=20)d+=` L${x} ${(80+40*Math.sin(Math.PI*(x-30)/828)).toFixed(1)}`;g+=`<path d="${d}" fill="none" stroke="${LINE}" stroke-width="3"/>`;
  for(let i=0;i<9;i++){const x=60+i*96;if(x>30+828*sp)continue;const y=80+40*Math.sin(Math.PI*(x-30)/828),nw=i===2||i===5||i===7,a=nw?.6+[2,5,7].indexOf(i)*.2:0,p=nw?SPR(t-a,.45,15):1;if(nw&&t<a)continue;const sw=6*DECAY(t-(nw?a:.3),2,9);
   g+=`<g transform="translate(${x},${y.toFixed(1)}) rotate(${sw.toFixed(1)}) scale(${Math.max(.01,p).toFixed(3)})" opacity="${clamp((p-.1)/.85).toFixed(3)}"><path d="M-36 0 h72 l-36 70Z" fill="${nw?LAMP:'#E9D9BF'}" stroke="${LINE}" stroke-width="2"/>${nw?T(0,36,'假',32,700,'#FFFFFF'):''}</g>`}
  g+=`<rect x="0" y="${h-90}" width="888" height="90" fill="#D9C4A0"/><rect x="560" y="${h-170}" width="240" height="90" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(680,h-112,'2025 新增',32,700,TXT);
  return g},
  sfx(t0,s,E){[.6,.8,1.0].forEach(x=>E(t0+x,'pop'))}},
 // s6 打卡卡架：一排卡片依序插進卡架（多數是全職色），只有一張是兼職色；最後一張插入時卡架輕晃
 cardrack:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EDE2D0"/><rect x="80" y="40" width="728" height="${h-90}" rx="14" fill="#B98A6A" stroke="${LINE}" stroke-width="4"/>`;
  for(let i=0;i<25;i++){const u=t-.1-i*.035,p=SPR(u,.5,15);const x=104+i*28.4,pt=i===24;if(u<=0){g+=`<rect x="${x.toFixed(1)}" y="150" width="22" height="18" fill="#8A5A44"/>`;continue}
   g+=`<rect x="${x.toFixed(1)}" y="${(70-(1-p)*60).toFixed(1)}" width="22" height="160" rx="3" fill="${pt?LAMP:'#FFFDF8'}" stroke="${LINE}" stroke-width="2"/><rect x="${x.toFixed(1)}" y="150" width="22" height="18" fill="#8A5A44"/>`}
  g+=T(400,h-74,'全職',32,700,'#FFFFFF')+T(770,h-74,'兼職',32,700,'#FFFFFF');
  return g},
  sfx(t0,s,E){for(let i=0;i<14;i+=3)E(t0+.1+i*.06+.1,'tick',{g:.5});E(t0+.9,'tick',{g:.9})}},
 // s7 加班：牆鐘指針轉過 6 點後繼續走（0.2–1.2，超過的弧段變橘），桌上馬克杯被續滿一次
 overtime:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#D9C4A0"/>`;const cx=300,cy=h/2;
  g+=`<circle cx="${cx}" cy="${cy}" r="130" fill="${FACE3}" stroke="${LINE}" stroke-width="8"/>`;for(let i=0;i<12;i++){const a=i*Math.PI/6;g+=`<line x1="${cx+110*Math.sin(a)}" y1="${cy-110*Math.cos(a)}" x2="${cx+122*Math.sin(a)}" y2="${cy-122*Math.cos(a)}" stroke="${LINE}" stroke-width="3"/>`}
  const hr=Math.PI+Math.PI/6*2*EO((t-.2)/1.0),a0=Math.PI;if(hr>a0+.01)g+=`<path d="M${cx} ${cy} L${cx+100*Math.sin(a0)} ${cy-100*Math.cos(a0)} A100 100 0 0 1 ${(cx+100*Math.sin(hr)).toFixed(1)} ${(cy-100*Math.cos(hr)).toFixed(1)}Z" fill="${LAMP}" opacity=".35"/>`;
  g+=`<line x1="${cx}" y1="${cy}" x2="${(cx+70*Math.sin(hr)).toFixed(1)}" y2="${(cy-70*Math.cos(hr)).toFixed(1)}" stroke="${TXT}" stroke-width="8" stroke-linecap="round"/><line x1="${cx}" y1="${cy}" x2="${(cx+100*Math.sin(t*4)).toFixed(1)}" y2="${(cy-100*Math.cos(t*4)).toFixed(1)}" stroke="${LAMP}" stroke-width="4"/><circle cx="${cx}" cy="${cy}" r="10" fill="${LINE}"/>`;
  const lv=t<1.0?.3:.3+.6*clamp((t-1.0)/.4);g+=`<rect x="600" y="${h-200}" width="120" height="140" rx="14" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/><rect x="606" y="${h-66-130*lv}" width="108" height="${(130*lv).toFixed(1)}" fill="#8A5A44" opacity=".85"/><path d="M720 ${h-170} q40 0 40 40 q0 30 -40 30" fill="none" stroke="${LINE}" stroke-width="6"/>`;
  if(t>1.0&&t<1.4)g+=`<rect x="652" y="${h-320}" width="14" height="${120}" fill="#8A5A44" opacity=".8"/><path d="M620 ${h-330} h80 v-30 h-80Z" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  g+=`<path d="M650 ${h-210} q8 -20 0 -40" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.2+.3*tw(t,0,2.4)).toFixed(2)}"/>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<5;i++)E(t0+.2+i*.2,'tick',{g:.5});E(t0+1.0,'glide',{f0:300,f1:500,dur:.4,g:.06})}},
 // s8 晚餐桌上的手機：碗筷擺好，手機亮起、對話泡泡一個個冒出（0.4／0.7／1.0），筷子被放下（1.3）
 chat:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#EFE3CF"/><rect x="0" y="${h-120}" width="888" height="120" fill="#C9A27A"/>`;
  g+=`<ellipse cx="220" cy="${h-120}" rx="110" ry="30" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M120 ${h-124} q100 90 200 0Z" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><path d="M180 ${h-150} q20 -20 40 0" stroke="${LINE}" stroke-width="3" fill="none" opacity="${(.2+.3*tw(t,0,2)).toFixed(2)}"/>`;
  const cd=t<1.3?0:SPR(t-1.3,.5,12);g+=`<g transform="rotate(${(-30+30*cd).toFixed(1)} 360 ${h-120})"><line x1="330" y1="${h-120}" x2="470" y2="${h-150}" stroke="#8A5A44" stroke-width="7" stroke-linecap="round"/><line x1="340" y1="${h-108}" x2="480" y2="${h-136}" stroke="#8A5A44" stroke-width="7" stroke-linecap="round"/></g>`;
  const on=clamp((t-.3)*5);g+=`<rect x="560" y="${h-150}" width="180" height="40" rx="10" fill="#4A4744" stroke="${LINE}" stroke-width="3" transform="rotate(-6 650 ${h-130})"/>`+(on?glow(650,h-140,70,.4*on):'');
  [[.4,600,h-250],[.7,640,h-320],[1.0,590,h-390]].forEach(([a,x,y],i)=>{const p=SPR(t-a,.45,16);if(t<a)return;g+=`<g transform="translate(${x},${y}) scale(${Math.max(.01,p).toFixed(3)})"><rect x="-10" y="-34" width="${150-i*10}" height="56" rx="20" fill="${i===1?LAMP:FACE3}" stroke="${LINE}" stroke-width="3"/><path d="M6 22 l-10 18 l26 -18Z" fill="${i===1?LAMP:FACE3}" stroke="${LINE}" stroke-width="2"/>${[0,1,2].map(k=>`<circle cx="${30+k*28}" cy="-6" r="6" fill="${i===1?'#FFFFFF':LINE}"/>`).join('')}</g>`});
  return g},
  sfx(t0,s,E){[.4,.7,1.0].forEach(x=>E(t0+x,'pop'));E(t0+1.3,'tick')}},
 // s9 兩杯倒成一杯：左邊大杯（全職）、右邊小杯（兼職）同時傾斜倒進中間量杯（0.3–1.2），量杯液面升起混色、刻度線
 mixing:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  const tilt=t<.3?0:-55*Math.sin(Math.PI*clamp((t-.3)/1.2)),lv=clamp((t-.5)/.9);
  g+=`<g transform="rotate(${tilt.toFixed(1)} 230 ${h-200})"><path d="M150 ${h-280} h160 l-14 220 h-132Z" fill="#FFFDF8" fill-opacity=".85" stroke="${LINE}" stroke-width="4"/><path d="M158 ${h-240} h144 l-11 178 h-122Z" fill="#B98A6A"/></g>`;
  g+=`<g transform="rotate(${(-tilt).toFixed(1)} 690 ${h-160})"><path d="M650 ${h-170} h80 l-8 110 h-64Z" fill="#FFFDF8" fill-opacity=".85" stroke="${LINE}" stroke-width="4"/><path d="M656 ${h-140} h68 l-6 78 h-56Z" fill="${LAMP}"/></g>`;
  if(t>.5&&t<1.4)g+=`<path d="M310 ${h-270} q60 0 110 60" stroke="#B98A6A" stroke-width="10" fill="none"/><path d="M650 ${h-165} q-50 0 -90 50" stroke="${LAMP}" stroke-width="5" fill="none"/>`;
  g+=`<path d="M400 ${h-230} h120 l-10 170 h-100Z" fill="#FFFDF8" fill-opacity=".7" stroke="${LINE}" stroke-width="4"/><rect x="412" y="${(h-66-150*lv).toFixed(1)}" width="96" height="${(150*lv).toFixed(1)}" fill="#C79A6B"/>`;
  for(let i=1;i<4;i++)g+=`<line x1="500" y1="${h-60-i*40}" x2="516" y2="${h-60-i*40}" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(460,h-14,'平均',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.5,'glide',{f0:400,f1:200,dur:.8,g:.07});E(t0+1.4,'tick')}},
 // s10 「注意口徑」路牌：路牌從地面彈起、牌子擺盪衰減；旁邊放大鏡掃過一行小字（掃過，不放大）
 signpost:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F1E6D3"/><rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  const p=SPR(t-.15,.45,13),sw=10*DECAY(t-.45,1.8,7);g+=`<g transform="translate(260,${(h-60+(1-p)*200).toFixed(1)})"><line x1="0" y1="0" x2="0" y2="-200" stroke="#8A5A44" stroke-width="12"/><g transform="rotate(${sw.toFixed(1)} 0 -200)"><path d="M0 -200 l-110 0 l0 -110 h220 v110Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/>${T(0,-240,'注意口徑',36,700,'#FFFFFF')}</g></g>`;
  g+=`<rect x="460" y="120" width="360" height="140" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/>`+T(640,180,'全職＋兼職',34,700,TXT)+T(640,226,'一起平均',32,400,SUBC);
  const mx=440+380*EO(clamp((t-.8)/1.2));g+=`<g transform="translate(${mx.toFixed(1)},${h-90})"><circle r="34" fill="#FFF8EA" fill-opacity=".5" stroke="${LINE}" stroke-width="6"/><line x1="24" y1="24" x2="56" y2="56" stroke="${LINE}" stroke-width="10" stroke-linecap="round"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.3,'thump',{g:.3});E(t0+.8,'glide',{f0:600,f1:900,dur:.6,g:.05})}},
 // s11 一週白板：五格工作日色塊由左往右填滿（0.2–1.2），週末兩格保持空白；白板筆滾一下
 weekboard:{draw(t,h){let g=`<rect x="60" y="30" width="768" height="${h-80}" rx="16" fill="#FFFDF8" stroke="${LINE}" stroke-width="5"/><rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  const d=['一','二','三','四','五','六','日'];d.forEach((x,i)=>{const cx=100+i*102;g+=T(cx+40,84,x,32,700,i<5?TXT:SUBC);const p=i<5?SPR(t-.2-i*.18,.55,14):0;g+=`<rect x="${cx}" y="110" width="80" height="${h-220}" rx="10" fill="${FACE}" stroke="${LINE}" stroke-width="2" ${i>4?'stroke-dasharray="8 8"':''}/>`;if(p>0)g+=`<rect x="${cx}" y="${(110+(h-220)*(1-Math.min(1,p))).toFixed(1)}" width="80" height="${((h-220)*Math.min(1.02,p)).toFixed(1)}" rx="10" fill="${LAMP}" opacity=".8"/>`});
  const rl=(1-SPR(t-1.3,.6,8))*-80;g+=`<g transform="translate(${(640+rl).toFixed(1)},${h-62}) rotate(${(rl*3).toFixed(0)})"><rect x="-60" y="-8" width="120" height="16" rx="6" fill="#4A4744"/></g>`;
  return g},
  sfx(t0,s,E){for(let i=0;i<5;i++)E(t0+.2+i*.18+.1,'tick',{g:.6});E(t0+1.3,'glide',{f0:500,f1:300,dur:.3,g:.05})}},
 // s12 風箏：風箏從右下被拉起升高（過衝回彈），尾巴蝴蝶結一個個擺；線軸轉
 kite:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F4E6D0"/><rect x="0" y="${h-60}" width="888" height="60" fill="#CDB896"/>`;
  const p=SPR(t-.15,.5,6),kx=620-140*p,ky=h-120-(h-220)*p,rot=-10+8*Math.sin(t*2.4);
  g+=`<path d="M160 ${h-80} Q ${(kx-160).toFixed(1)} ${(ky+160).toFixed(1)} ${kx.toFixed(1)} ${(ky+50).toFixed(1)}" fill="none" stroke="${LINE}" stroke-width="2"/>`;
  let tail=`M${kx} ${ky+60}`;for(let i=1;i<=4;i++)tail+=` L${(kx+18*Math.sin(t*4+i)+i*10).toFixed(1)} ${(ky+60+i*34).toFixed(1)}`;g+=`<path d="${tail}" fill="none" stroke="${LINE}" stroke-width="2"/>`;
  for(let i=1;i<=4;i++)g+=`<path d="M${(kx+18*Math.sin(t*4+i)+i*10-10).toFixed(1)} ${(ky+60+i*34-6).toFixed(1)} l20 12 l0 -12 l-20 12Z" fill="${i%2?LAMP:'#E9B98A'}"/>`;
  g+=`<g transform="rotate(${rot.toFixed(1)} ${kx.toFixed(1)} ${ky.toFixed(1)})"><path d="M${kx} ${ky-70} l50 60 l-50 70 l-50 -70Z" fill="${LAMP}" stroke="${LINE}" stroke-width="3"/><line x1="${kx}" y1="${ky-70}" x2="${kx}" y2="${ky+60}" stroke="${LINE}" stroke-width="2"/><line x1="${kx-50}" y1="${ky-10}" x2="${kx+50}" y2="${ky-10}" stroke="${LINE}" stroke-width="2"/></g>`;
  g+=`<g transform="translate(160,${h-80}) rotate(${(t*200).toFixed(0)})"><circle r="24" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/><line x1="-24" y1="0" x2="24" y2="0" stroke="${LINE}" stroke-width="3"/></g>`;
  g+=`<rect x="600" y="${h-150}" width="220" height="70" rx="12" fill="${FACE3}" stroke="${LINE}" stroke-width="3"/>`+T(710,h-104,'25–29 歲',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.15,'glide',{f0:300,f1:800,dur:.6,g:.08})}}
};
