// 音效事件（v8）：換鏡 whoosh、標籤 pop、強調 pop／bell、資料圖長出 tick、插圖物件事件（ILL[名].sfx(t0, s, E)）、片尾招牌音（同 v7）
window.sfxEvents=function(){const S=V.scenes,ev=[],E=(t,type,o)=>ev.push(Object.assign({t:+t.toFixed(4),type},o||{}));
 S.forEach((s,i)=>{const t0=s.t0;
  if(i>0&&s.type!=='outro')E(t0,'whoosh');
  if(s.tag)E(t0+({hook:.5,versus:.1,ask:.3,next:.25}[s.type]||.15),'pop');
  if(s.type==='hook'){E(t0+.5,'thump',{g:.3});E(t0+.95,'tick',{g:.6})}
  if(['stack','gantt','vbars','hbars','people','lollipop','tiles','steps','lanes'].includes(s.type)){for(let k=0;k<3;k++)E(t0+.25+k*.18,'tick',{g:.55})}
  if(['card','donut','odometer','gauge','slope','dumbbell','band','split2'].includes(s.type))E(t0+1.0,'chime');
  if(!['hook','outro','ask','next'].includes(s.type))E(t0+1.5,'bell',{n:[19],g:.35});
  if(s.type==='versus'){E(t0+1.25,'glide',{f0:400,f1:900,dur:.4,g:.1});E(t0+1.95,'pop')}
  if(s.type==='ask'){E(t0+.7,'bell',{n:[24],g:.45});E(t0+1.5,'tick');E(t0+1.75,'tick')}
  if(s.type==='next'){E(t0+.6,'pop');E(t0+.72,'bell',{n:[14],g:.4})}
  if(s.ill&&ILL[s.ill]&&ILL[s.ill].sfx)ILL[s.ill].sfx(t0,s,E);
  if(s.type==='outro'){const F=k=>t0+k/30;
   E(F(OF.cloud),'kal',{n:[-17],g:.7});E(F(OF.cloud),'glide',{f0:200,f1:520,dur:.3,g:.12});
   E(F(OF.land),'thump',{g:.6});E(F(OF.land),'kal',{n:[-5],g:.45});
   E(F(OF.sun),'glide',{f0:520,f1:1900,dur:.36,g:.2});E(F(OF.apex),'bell',{n:[12],g:.65});E(F(OF.apex),'kal',{n:[19],g:.5});E(F(OF.apex+8),'kal',{n:[7],g:.3});
   OF.ray.forEach((r,k)=>{E(F(r),'click');E(F(r),'bell',{n:[[16,19,21][k]],g:.6});E(F(r),'sparkle',{n:[28+k*2],g:.5})});
   OF.ch.forEach((c,k)=>{E(F(c+OF.imp),'thump',{g:.53});E(F(c+OF.imp),'kal',{n:[[12],[14],[16],[19]][k],g:.9})});
   E(F(OF.fin),'bloom',{n:[0,4,7,12,16]});E(F(OF.fin),'bell',{n:[12,16,19,24],g:.55});E(F(OF.fin),'shimmer',{n:[12,16,19,24,28,31],g:.5});
   E(F(OF.slog),'kal',{n:[19],g:.35});E(F(OF.next),'kal',{n:[24],g:.4});if(s.keyword)E(F(kwF(s)),'kal',{n:[28],g:.5});
   E(F(OF.glint),'shimmer',{n:[24,28,31,36],g:.3});
   E(F(0),'pad',{dur:s.t1-s.t0})}});
 return ev.sort((a,b)=>a.t-b.t)};
window.renderAt(0);
