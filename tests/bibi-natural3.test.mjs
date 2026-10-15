import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

// 正式程式在虛擬時鐘與最小DOM內執行；只於VM注入接點，網站不增加測試API。
function harness(width=1440,optional=true) {
  let now=0,next=0; const queue=new Map(),images=[],elements=[];
  function element() {
    const classes=new Set();
    const el={style:{setProperty(k,v){this[k]=v;}},dataset:{},children:[],isConnected:true,complete:true,naturalWidth:160,
      classList:{add(...xs){xs.forEach(x=>classes.add(x));},remove(...xs){xs.forEach(x=>classes.delete(x));},contains:x=>classes.has(x),toggle(x,on){on?classes.add(x):classes.delete(x);}},
      setAttribute(k,v){this[k]=v;if(k==='src'&&this.onload)this.onload();},getAttribute(k){return this[k]||'';},
      appendChild(x){this.children.push(x);return x;},remove(){this.isConnected=false;this.removed=true;},querySelector(){return this.path||=element();},querySelectorAll(){return [];},addEventListener(){},
      getBoundingClientRect(){return {left:width-88,top:720,width:64,height:64,bottom:784,right:width-24};}};
    Object.defineProperty(el,'innerHTML',{get(){return this._html||'';},set(v){this._html=v;this.children=[];}}); elements.push(el);return el;
  }
  const document={readyState:'loading',hidden:false,documentElement:{clientWidth:width,classList:{contains:()=>false}},createElement:element,body:element(),addEventListener(){},getElementById:()=>null,querySelector:()=>null,
    querySelectorAll(s){return s==='.bibi-back-thread'?elements.filter(x=>x.classList.contains('bibi-back-thread')&&!x.removed):[];}};
  const context=vm.createContext({console,document,matchMedia:()=>({matches:false}),window:{innerWidth:width,innerHeight:900,matchMedia:()=>({matches:false}),addEventListener(){}},location:{hash:''},localStorage:{getItem:()=>null,setItem(){}},performance:{now:()=>now},
    Image:class{constructor(){images.push(this);}},setTimeout:(fn,ms=0)=>{const id=++next;queue.set(id,{fn,at:now+ms});return id;},clearTimeout:id=>queue.delete(id),
    requestAnimationFrame:fn=>{const id=++next;queue.set(id,{fn:()=>fn(now),at:now+8});return id;},cancelAnimationFrame:id=>queue.delete(id),MutationObserver:class{observe(){}disconnect(){}},fetch:async()=>({json:async()=>[]})});
  let source=fs.readFileSync(new URL('../site/bibi.js',import.meta.url),'utf8');
  source=source.replace('  window.Bibi = {',`
  window._engine={init:(f,im,w,b,h,t)=>{fab=f;imgs=im;wrapEl=w;bodyEl=b;hopEl=h;tip=t;shown=want=IDLE_HOP;},begin:id=>{mode='act';startRun(id,true);},ready:names=>names.forEach(x=>readyParts.add(x)),reactionAnchor,reactionBody,reactionFrame,reactionDuration,atTip,runTo,spinScript,bubbleScript,leafScript,planeScript,yarnScript,tween,loopBg,geo};
  window.Bibi = {`);
  vm.runInContext(source,context); const f=element(),im=[element(),element()],engine=context.window._engine,api=context.window.Bibi;
  engine.init(f,im,element(),element(),element(),element()); if(optional)engine.ready(['leaf_bite','bubble_react','plane_react','yarn_tumble']);
  async function advance(ms) {
    const target=now+ms;
    while(true){const due=[...queue].filter(([,v])=>v.at<=target).sort((a,b)=>a[1].at-b[1].at)[0];if(!due)break;now=due[1].at;queue.delete(due[0]);due[1].fn();await Promise.resolve();await Promise.resolve();}
    now=target;await Promise.resolve();await Promise.resolve();
  }
  return {api,engine,advance,images,im,f,elements,resolveImages(){images.forEach(i=>i.onload?.());}};
}

test('觸發同步停待機，預載取消後不能偷偷啟動',async()=>{
  const h=harness(),pending=h.api.act('leaf'); assert.equal(h.api.state().mode,'loading');assert.equal(h.api.state().file,'idle_hop_still');assert.ok(h.f.classList.contains('bibiinteracting'));assert.ok(h.im.every(i=>i.src.includes('idle_hop_still')));
  h.api.stop('esc');h.resolveImages();await pending;await h.advance(1000);const s=h.api.state();assert.equal(s.mode,'idle');assert.equal(s.tweens,0);assert.equal(s.props,0);assert.equal(s.off.x,0);assert.equal(s.off.y,0);assert.equal(s.tip,'');
});
for(const width of [390,1440]) {
  test(`${width}：跑步當下固定速度起步且無外加跳躍`,async()=>{
    const h=harness(width);h.engine.begin('run');const p=h.engine.runTo(h.engine.geo(),0,-100,200);await h.advance(80);const a=h.api.state().off.x;await h.advance(80);const b=h.api.state().off.x;
    assert.equal(a,-16);assert.equal(b-a,-16);assert.equal(h.api.state().off.y,0);await h.advance(400);await p;assert.equal(h.api.state().off.x,-100);
  });
  test(`${width}：地面一圈弧長等速，垂直不超過6px`,async()=>{
    const h=harness(width);h.engine.begin('spin');const p=h.engine.spinScript(h.engine.geo());let prev={x:0,y:0},speeds=[],minX=0;
    while(h.api.state().phase==='lap'){await h.advance(8);const s=h.api.state(),c=s.off;if(s.phase==='lap'){speeds.push(Math.hypot(c.x-prev.x,c.y-prev.y));assert.ok(Math.abs(c.y)<=6.001);minX=Math.min(minX,c.x);}prev=c;}
    assert.ok(minX < -80);const sorted=speeds.slice(2,-2).sort((a,b)=>a-b),median=sorted[Math.floor(sorted.length/2)];assert.ok(sorted[0]/median>.88);assert.ok(sorted.at(-1)/median<1.02);await h.advance(800);await p;assert.equal(h.api.state().off.x,0);assert.equal(h.api.state().off.y,0);
  });
  for(const name of ['leaf','bubble','plane','yarn']) test(`${width}：${name}取消清掉前後道具及所有補間`,async()=>{
    const h=harness(width);h.engine.begin(name);const p=h.engine[name+'Script'](h.engine.geo()).catch(()=>{});await h.advance(name==='yarn'?1300:900);h.api.stop('esc');await p;const s=h.api.state();
    assert.equal(s.mode,'idle');assert.equal(s.tweens,0);assert.equal(s.props,0);assert.equal(s.off.x,0);assert.equal(s.off.y,0);assert.ok(!h.elements.some(e=>e.classList.contains('bibi-back-thread')&&!e.removed));await h.advance(10000);assert.equal(h.api.state().run,'');assert.equal(h.api.state().tweens,0);
  });
  test(`${width}：並行背景補間取消後全部settle`,async()=>{
    const h=harness(width);h.engine.begin('test');const p=h.engine.tween(60000,()=>{}).catch(e=>e),q=h.engine.tween(60000,()=>{}).catch(e=>e);assert.equal(h.api.state().tweens,2);h.api.stop('esc');await Promise.all([p,q]);assert.equal(h.api.state().tweens,0);
  });
  for(const [name,phase] of [['leaf','leaf-chew'],['bubble','bubble-startle'],['plane','plane-recoil'],['yarn','yarn-struggle']]) test(`${width}：${name}專屬反應接觸後取消無殘留`,async()=>{
    const h=harness(width);h.engine.begin(name);const p=h.engine[name+'Script'](h.engine.geo()).catch(()=>{});for(let elapsed=0;h.api.state().phase!==phase&&elapsed<10000;elapsed+=8)await h.advance(8);
    assert.equal(h.api.state().phase,phase);assert.equal(h.api.state().file,{leaf:'leaf_bite',bubble:'bubble_react',plane:'plane_react',yarn:'yarn_tumble'}[name]);h.api.stop('page');await p;await h.advance(5000);const s=h.api.state();assert.equal(s.tweens,0);assert.equal(s.props,0);assert.equal(s.off.x,0);assert.equal(s.off.y,0);
  });
}
test('缺專屬圖時只用四腳fallback，不冒稱新素材已載入',async()=>{
  const h=harness(390,false);h.engine.begin('leaf');const p=h.engine.leafScript(h.engine.geo()).catch(()=>{});await h.advance(1200);assert.equal(h.api.state().file,'receive');assert.deepEqual(Array.from(h.api.state().readyParts),[]);h.api.stop('esc');await p;
});
test('逐格時間與口鼻接點換格同步，鏡像同軸',()=>{
  const h=harness(),g=h.engine.geo(),m=h.api.MAP.REACTIONS.leaf_bite;m.durations=[100,200];m.mouth=[[110,90],[125,95]];m.nose=[[115,85],[130,90]];assert.equal(h.engine.reactionDuration('leaf_bite'),300);
  const a=h.engine.reactionAnchor(g,'leaf_bite','mouth',99,1),b=h.engine.reactionAnchor(g,'leaf_bite','mouth',100,1),c=h.engine.reactionAnchor(g,'leaf_bite','mouth',100,-1);assert.equal(b.dx-a.dx,15*g.s/160);assert.equal(b.dx,-c.dx);assert.equal(b.y,c.y);
});
test('旋轉後葉尖精準貼口緣，非圖片中心貼臉',()=>{
  const h=harness(),el={_w:20,_h:30,style:{}},tip=[.72,.03],angle=70;h.engine.atTip(el,200,300,tip,angle);const [left,top]=el.style.transform.match(/translate\(([-\d.]+)px,([-\d.]+)px\)/).slice(1).map(Number),rad=angle*Math.PI/180,dx=(tip[0]-.5)*20,dy=(tip[1]-.5)*30;
  assert.ok(Math.abs(left+10+dx*Math.cos(rad)-dy*Math.sin(rad)-200)<.06);assert.ok(Math.abs(top+15+dx*Math.sin(rad)+dy*Math.cos(rad)-300)<.06);assert.ok(Math.abs(left+10-200)>5);
});
test('逐格肩腹臀角度驅動毛線，解纏有效長度縮至零且不淡出',async()=>{
  const h=harness(),g=h.engine.geo(),m=h.api.MAP.REACTIONS.yarn_tumble;m.durations=[1300,1300];m.body=[{cx:80,cy:103,angle:0,shoulder:[75,90],belly:[80,103],hip:[85,115]},{cx:83,cy:110,angle:60,shoulder:[70,103],belly:[83,110],hip:[95,116]}];
  const a=h.engine.reactionBody(g,'yarn_tumble',0,-1),b=h.engine.reactionBody(g,'yarn_tumble',1300,-1);assert.equal(b.angle,-Math.PI/3);assert.notEqual(a.anchors[0].x,b.anchors[0].x);assert.notEqual(a.anchors[0].y,b.anchors[0].y);
  h.engine.begin('yarn');const p=h.engine.yarnScript(g).catch(()=>{});let elapsed=0;while(h.api.state().phase!=='yarn-release'&&elapsed<6000){await h.advance(8);elapsed+=8;}
  const f=h.elements.find(e=>e.className==='bp bp-thread-front'),r=h.elements.find(e=>e.className==='bp bp-thread-back');assert.ok(f.path.d.length>100);assert.ok(r.path.d.length>100);const start=f.path.d.length+r.path.d.length;await h.advance(560);assert.ok(f.path.d.length+r.path.d.length<start/2);assert.equal(f.style.opacity,'1');assert.equal(r.style.opacity,'1');h.api.stop('esc');await p;
});
