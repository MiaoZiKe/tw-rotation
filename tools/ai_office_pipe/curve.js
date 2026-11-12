// 細看一個週期：node curve.js walk|run [欄位…] → 每 1/48 週期印一列（相位、是否擺動、膝角、腳掌俯仰、骨盆高、伸直比例）
const a=process.argv[2]||'walk';
process.argv[2]=`(async()=>{await stage.set({action:'${a}',t:4,route:[[0,400]]});const T=stage.loco.g.T,n=Math.round(T/48*240),o=[];for(let i=0;i<48;i++){const p=stage.step(1/240,n).pop();o.push([p.phase.toFixed(3),p.feet.L.swing?'擺':'撐',p.kneeL.toFixed(0),p.feet.L.pitch.toFixed(2),(p.pelvisY-stage.char.J.hips.y).toFixed(4),p.feet.L.reach.toFixed(3),p.feet.L.soleMinY.toFixed(3),p.armL.toFixed(0),p.elbowL.toFixed(0),p.lean.toFixed(1)].join(' '))}return o.join('\\n')})()`;
require('./dbg.js');
