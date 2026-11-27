 taxreturn:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  // s5 預扣再結算：左邊年終袋上方一枚「5%」硬幣沿弧線飛進右邊「報稅單」（0.2–0.8），報稅單頁角翻起、月曆翻到「隔年 5 月」（1.0）→ 一枚較小的硬幣沿下方弧線飛回年終袋（1.3–1.8，多退），袋子彈一下（2026-11-27 新做，年終）
  g+=`<rect x="110" y="${h-200}" width="200" height="150" rx="14" fill="#D94F3D" stroke="${LINE}" stroke-width="4"/>`+T(210,h-110,'年終',36,700,'#FFF4D6');
  const fp=10*DECAY(t-1.0,2,9);g+=`<rect x="560" y="${h-250}" width="220" height="200" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="4"/>`+T(670,h-200,'報稅單',32,700,TXT)+`<path d="M780 ${h-250} l${(-30-fp).toFixed(1)} 0 l${(30+fp).toFixed(1)} ${(30+fp).toFixed(1)}Z" fill="#EFE3CF" stroke="${LINE}" stroke-width="2"/>`;
  for(let i=0;i<3;i++)g+=`<line x1="590" y1="${h-160+i*30}" x2="${750-i*30}" y2="${h-160+i*30}" stroke="${LINE}" stroke-width="2" opacity=".4"/>`;
  const cal=clamp((t-1.0)/.25);g+=`<rect x="380" y="30" width="130" height="110" rx="10" fill="#FFFDF8" stroke="${LINE}" stroke-width="3"/><rect x="380" y="30" width="130" height="32" rx="10" fill="#E36B4A"/>`+T(445,120,cal>=1?'5月':'1月',40,700,TXT)+T(445,56,cal>=1?'隔年':'今年',22,700,'#FFFFFF');
  const arc=(p,x0,y0,x1,y1,hh)=>[x0+(x1-x0)*p,y0+(y1-y0)*p-hh*4*p*(1-p)];
  const p1=clamp((t-.2)/.6);if(t>.2&&t<.85){const [x,y]=arc(EO(p1),330,h-110,670,h-100,10);const fo=clamp((.85-t)/.15);g+=`<g opacity="${fo.toFixed(2)}" transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><circle r="40" fill="#E0B070" stroke="${LINE}" stroke-width="3"/>${T(0,10,'5%',28,700,TXT)}</g>`}
  const p2=clamp((t-1.3)/.5);if(t>1.3&&t<1.85){const [x,y]=arc(EO(p2),640,h-120,210,h-235,-90);g+=`<g transform="translate(${x.toFixed(1)},${y.toFixed(1)})"><circle r="28" fill="#E0B070" stroke="${LINE}" stroke-width="3"/>${T(0,9,'退',24,700,TXT)}</g>`}
  return g},
  sfx(t0,s,E){E(t0+.2,'glide',{f0:500,f1:900,dur:.5,g:.06});E(t0+.85,'tick',{g:.4});E(t0+1.3,'glide',{f0:900,f1:500,dur:.45,g:.06});E(t0+1.85,'bell',{n:[19],g:.3})}}
