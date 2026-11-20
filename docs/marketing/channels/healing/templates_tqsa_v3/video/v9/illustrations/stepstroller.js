 stepstroller:{draw(t,h){const DROP=+'20'*4;   // 參數：減少的百分比 × 4 ＝ 台階落差（px）；這裡 20％＝80px
  let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E2C8"/>`;
  const cl=(t*14)%1000;g+=`<ellipse cx="${(520+cl)%1000-60}" cy="60" rx="80" ry="24" fill="#FFFDF8" opacity=".8"/>`;
  const yB=170+DROP;
  g+=`<rect x="60" y="170" width="380" height="${h-170}" fill="#CDB896" stroke="${LINE}" stroke-width="3"/><rect x="440" y="${yB}" width="388" height="${h-yB}" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(250,336,'2024',44,700,TXT)+T(634,336,'2025',44,700,TXT);
  g+=`<rect x="670" y="${yB-40}" width="158" height="40" fill="#A67A5C" stroke="${LINE}" stroke-width="3"/>`;
  const pr0=(x,y,a)=>`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)})" opacity="${a}"><path d="M-50 -66 h96 v14 q0 40 -48 40 q-48 0 -48 -40Z" fill="#FFF4D6" stroke="${LINE}" stroke-width="4"/><path d="M-50 -66 q50 -64 96 0Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><path d="M46 -66 l30 -34" stroke="${LINE}" stroke-width="5" stroke-linecap="round"/><circle cx="-26" cy="-14" r="14" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/><circle cx="22" cy="-14" r="14" fill="${FACE3}" stroke="${LINE}" stroke-width="4"/></g>`;
  // 虛線影子留在 2024 高台（原本的位置）；嬰兒推車從高台滾下一階、落地彈一下就停
  g+=`<g opacity=".35"><g transform="translate(250,170)"><path d="M-50 -66 h96 v14 q0 40 -48 40 q-48 0 -48 -40Z" fill="none" stroke="${LINE}" stroke-width="3" stroke-dasharray="6 6"/></g></g>`;
  const u=clamp((t-.5)/.9),e=u*u*(3-2*u),u2=clamp((t-1.9)/.5,0,1),e2=u2*u2*(3-2*u2),x=250+(640-250)*e+110*e2,by=170+DROP*e-70*Math.sin(Math.PI*e)-40*e2-30*Math.sin(Math.PI*e2),lt=t-1.4,bn=lt>0&&t<1.9?16*Math.exp(-lt*7)*Math.sin(lt*28):0,lt2=t-2.4,bn2=lt2>0?8*Math.exp(-lt2*8)*Math.sin(lt2*28):0,y=by+bn+bn2;
  g+=pr0(x,y,1);
  return g},
  sfx(t0,s,E){E(t0+.5,'glide',{f0:700,f1:350,dur:.8,g:.08});E(t0+1.4,'thump',{g:.3});E(t0+1.9,'glide',{f0:350,f1:520,dur:.3,g:.06});E(t0+2.4,'thump',{g:.2})}}
