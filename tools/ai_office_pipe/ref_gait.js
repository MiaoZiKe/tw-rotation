// 參考動作量測：node ref_gait.js <參考模型.glb> <輸出.json> [動畫名,…]
// 載入別人做好的走跑動畫（例如 KayKit 的 CC0 角色），逐格量膝角、軀幹前傾、手臂擺幅、骨盆高度，當成調整自家步態的對照值。
const {chromium}=require('playwright');const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'../../site/office'),glb=process.argv[2],out=process.argv[3],names=(process.argv[4]||'Walking_A,Running_A').split(',');
const T={'.html':'text/html','.js':'text/javascript'};
const srv=http.createServer((q,s)=>{const u=q.url.split('?')[0];
 if(u==='/ref.glb'){s.writeHead(200);s.end(fs.readFileSync(glb));return}
 if(u==='/ref.html'){s.writeHead(200,{'Content-Type':'text/html'});s.end('<script type="importmap">{"imports":{"three":"./vendor/three.module.min.js"}}</script><body>');return}
 fs.readFile(path.join(root,u),(e,d)=>{if(e){s.writeHead(404);s.end();return}s.writeHead(200,{'Content-Type':T[path.extname(u)]||'application/octet-stream'});s.end(d)})}).listen(0,async()=>{
 const b=await chromium.launch();const pg=await b.newPage();pg.on('pageerror',e=>console.log('E:',e.message));
 await pg.goto(`http://localhost:${srv.address().port}/ref.html`);
 const res=await pg.evaluate(async(names)=>{
  const THREE=await import('./vendor/three.module.min.js');const {GLTFLoader}=await import('./vendor/GLTFLoader.js');
  const g=await new GLTFLoader().loadAsync('/ref.glb');const sc=g.scene;const B={};sc.traverse(o=>{if(o.isBone&&!B[o.name])B[o.name]=o});
  const P=n=>B[n.replace('.','')].getWorldPosition(new THREE.Vector3());const mix=new THREE.AnimationMixer(sc);const R={};
  const ang=(a,b,c)=>{const u=a.clone().sub(b),v=c.clone().sub(b);return u.angleTo(v)*180/Math.PI};
  for(const nm of names){const clip=g.animations.find(a=>a.name===nm);if(!clip)continue;mix.stopAllAction();const act=mix.clipAction(clip);act.play();const N=32,rows=[];
   for(let i=0;i<N;i++){mix.setTime(clip.duration*i/N);sc.updateMatrixWorld(true);
    const hip=P('upperleg.l'),kn=P('lowerleg.l'),an=P('foot.l'),toe=P('toes.l'),hp=P('hips'),ch=P('head'),sh=P('upperarm.l'),el=P('lowerarm.l'),wr=P('wrist.l');
    rows.push({knee:ang(hip,kn,an),ankleY:an.y,ankleZ:an.z-hp.z,hipY:hip.y,lean:Math.atan2(ch.z-hp.z,ch.y-hp.y)*180/Math.PI,arm:Math.atan2(el.z-sh.z,sh.y-el.y)*180/Math.PI,elbow:ang(sh,el,wr),leg:hip.distanceTo(kn)+kn.distanceTo(an)});}
   const col=k=>rows.map(r=>+r[k].toFixed(2));R[nm]={dur:clip.duration,leg:rows[0].leg,knee:col('knee'),ankleY:col('ankleY'),ankleZ:col('ankleZ'),hipY:col('hipY'),lean:col('lean'),arm:col('arm'),elbow:col('elbow')};}
  return R;},names);
 for(const k in res){const r=res[k],mm=a=>[Math.min(...a),Math.max(...a)];console.log(k,'週期',r.dur.toFixed(2),'腿長',r.leg.toFixed(2),'膝角',mm(r.knee),'前傾',mm(r.lean),'上臂擺',mm(r.arm),'肘角',mm(r.elbow),'髖高/腿長',mm(r.hipY).map(v=>+(v/r.leg).toFixed(3)),'腳踝前後/腿長',mm(r.ankleZ).map(v=>+(v/r.leg).toFixed(2)),'腳踝高/腿長',mm(r.ankleY).map(v=>+(v/r.leg).toFixed(2)));}
 fs.writeFileSync(out,JSON.stringify(res));await b.close();srv.close();});
