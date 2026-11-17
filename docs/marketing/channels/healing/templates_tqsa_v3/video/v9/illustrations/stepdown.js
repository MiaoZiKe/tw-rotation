 stepdown:{draw(t,h){let g=`<rect x="0" y="0" width="888" height="${h}" rx="26" fill="#F3E2C8"/>`;
  const cl=(t*14)%1000;g+=`<ellipse cx="${(520+cl)%1000-60}" cy="60" rx="80" ry="24" fill="#FFFDF8" opacity=".8"/>`;
  g+=`<rect x="60" y="170" width="380" height="${h-170}" fill="#CDB896" stroke="${LINE}" stroke-width="3"/><rect x="440" y="250" width="388" height="${h-250}" fill="#B98A6A" stroke="${LINE}" stroke-width="3"/>`;
  g+=T(250,336,'去年同期',44,700,TXT)+T(634,336,'今年',44,700,TXT);
  g+=`<rect x="670" y="210" width="158" height="40" fill="#A67A5C" stroke="${LINE}" stroke-width="3"/>`;
  const u=clamp((t-.5)/.9,0,1),e=u*u*(3-2*u),u2=clamp((t-1.9)/.5,0,1),e2=u2*u2*(3-2*u2),x=250+(640-250)*e+110*e2,by=170+80*e-70*Math.sin(Math.PI*e)-40*e2-30*Math.sin(Math.PI*e2),lt=t-1.4,bn=lt>0&&t<1.9?16*Math.exp(-lt*7)*Math.sin(lt*28):0,lt2=t-2.4,bn2=lt2>0?8*Math.exp(-lt2*8)*Math.sin(lt2*28):0,y=by+bn+bn2;
  g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><rect x="-45" y="-62" width="90" height="62" fill="#FFF4D6" stroke="${LINE}" stroke-width="4"/><path d="M-58 -62 L0 -108 L58 -62Z" fill="${LAMP}" stroke="${LINE}" stroke-width="4"/><rect x="-12" y="-36" width="24" height="36" fill="${LINE}" opacity=".8"/></g>`;
  return g},
  sfx(t0,s,E){E(t0+.5,'glide',{f0:700,f1:350,dur:.8,g:.08});E(t0+1.4,'thump',{g:.3});E(t0+1.9,'glide',{f0:350,f1:520,dur:.3,g:.06});E(t0+2.4,'thump',{g:.2})}}
