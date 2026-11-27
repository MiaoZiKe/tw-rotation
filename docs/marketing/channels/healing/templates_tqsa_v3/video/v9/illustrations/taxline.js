 taxline:{draw(t,h){let g=`<rect x="0" y="${h-50}" width="888" height="50" fill="#E4D3B8"/>`;
  // s4 起扣線：一條「起扣 90,501」虛線橫在半空（0.1 描出）；左邊「月薪 4 萬」年終鈔票堆長到 64,400 停在線下（0.3–1.0），右邊「月薪 5.6 萬以上」那堆長過虛線（0.6–1.4），跨線瞬間線閃一下、堆頂蓋上「先扣 5%」章（1.5，壓下回彈）（2026-11-27 新做，年終）
  const base=h-60,top=70,sc=v=>(base-top)*v/110000,ly=base-sc(90501);
  const lp=clamp((t-.1)/.4),fl=t>1.25&&t<1.5?1:0;
  const st=(x,v,p,lab)=>{const hh=sc(v)*EO(p);let s='';for(let y=0;y<hh;y+=26){const q=Math.min(26,hh-y);s+=`<rect x="${x-90}" y="${(base-y-q).toFixed(1)}" width="180" height="${(q-3).toFixed(1)}" rx="5" fill="#9CB38A" stroke="${LINE}" stroke-width="2"/>`}return s+T(x,base+40,lab,28,700,TXT)};
  g+=st(260,64400,clamp((t-.3)/.7),'月薪 4 萬')+st(628,96600,clamp((t-.6)/.8),'月薪 5.6 萬以上');
  g+=`<line x1="80" y1="${ly.toFixed(1)}" x2="808" y2="${ly.toFixed(1)}" stroke="${fl?'#E36B4A':HINT}" stroke-width="${fl?8:5}" stroke-dasharray="16 10" ${draw(lp)}/>`+`<g opacity="${lp}">${T(90,ly-16,'起扣 90,501 元',30,700,HINT,'start')}</g>`;
  const sp=SPR(t-1.5,.45,15);if(sp>0){const s1=1.4-.4*sp;g+=`<g transform="translate(628,${(base-sc(96600)-40).toFixed(1)}) scale(${s1.toFixed(3)}) rotate(-6)" opacity="${clamp(sp*2)}"><rect x="-90" y="-30" width="180" height="60" rx="10" fill="none" stroke="#E36B4A" stroke-width="5"/>${T(0,12,'先扣 5%',32,700,'#E36B4A')}</g>`}
  return g},
  sfx(t0,s,E){E(t0+1.3,'tick',{g:.4});E(t0+1.5,'thump',{g:.3})}}
