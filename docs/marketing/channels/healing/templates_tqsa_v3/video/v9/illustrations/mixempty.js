 mixempty:{draw(t,h){let g=`<rect x="0" y="${h-60}" width="888" height="60" fill="#E4D3B8"/>`;
  // 左邊大杯（高所得）傾斜倒進中間量杯；右邊小杯（最低兩成）也傾斜，但是空的：只滴下一滴就沒了
  const tilt=t<.3?0:-55*Math.sin(Math.PI*clamp((t-.3)/1.2)),lv=clamp((t-.5)/.9);
  g+=`<g transform="rotate(${tilt.toFixed(1)} 230 ${h-200})"><path d="M150 ${h-280} h160 l-14 220 h-132Z" fill="#FFFDF8" fill-opacity=".85" stroke="${LINE}" stroke-width="4"/><path d="M158 ${h-240} h144 l-11 178 h-122Z" fill="#B98A6A"/></g>`;
  g+=`<g transform="rotate(${(-tilt).toFixed(1)} 690 ${h-160})"><path d="M650 ${h-170} h80 l-8 110 h-64Z" fill="#FFFDF8" fill-opacity=".85" stroke="${LINE}" stroke-width="4"/></g>`;
  if(t>.5&&t<1.4)g+=`<path d="M310 ${h-270} q60 0 110 60" stroke="#B98A6A" stroke-width="10" fill="none"/>`;
  const dr=clamp((t-.7)/.6);if(t>.7&&t<1.3)g+=`<circle cx="${(655-30*dr).toFixed(1)}" cy="${(h-170+60*dr*dr).toFixed(1)}" r="6" fill="${LAMP}" opacity="${(1-dr).toFixed(2)}"/>`;
  // 量杯：液面被大杯一邊拉高；虛線是「如果小杯也有東西」的位置，實線是真實液面
  g+=`<path d="M400 ${h-230} h120 l-10 170 h-100Z" fill="#FFFDF8" fill-opacity=".7" stroke="${LINE}" stroke-width="4"/><rect x="412" y="${(h-66-150*lv).toFixed(1)}" width="96" height="${(150*lv).toFixed(1)}" fill="#C79A6B"/>`;
  for(let i=1;i<4;i++)g+=`<line x1="500" y1="${h-60-i*40}" x2="516" y2="${h-60-i*40}" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(460,h-14,'平均',32,700,TXT)+T(230,h-14,'高所得',32,700,TXT)+T(690,h-14,'最低20%',32,700,TXT);
  return g},
  sfx(t0,s,E){E(t0+.5,'glide',{f0:400,f1:200,dur:.8,g:.07});E(t0+.85,'tick',{g:.4});E(t0+1.4,'tick')}}
