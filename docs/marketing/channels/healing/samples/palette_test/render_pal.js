const {chromium}=require('/opt/node-tools/node_modules/playwright');const fs=require('fs');const path=require('path');
const P=JSON.parse(fs.readFileSync(__dirname+'/palettes.json','utf8'));
const V2=path.resolve(__dirname,'../20261104_gen2000_v2');
const pages=[['post1','threads'],['post2','01_cover'],['post3','02_inner']];
(async()=>{const b=await chromium.launch();
for(const [po,f] of pages){const src=fs.readFileSync(`${V2}/${po}/html/${f}.html`,'utf8');
 for(const p of P){const css=`body[data-palette=X]{--w-bg:${p.bg};--w-card:${p.card};--w-text:${p.text};--w-sub:${p.sub};--w-hint:${p.hint};--w-line:${p.line};--w-lamp:${p.lamp};--vig:rgba(0,0,0,${p.vig});--g-op:.10;--w-glow:${p.glow}}`;
  const h=src.replace(/data-palette="[A-Z]"/,'data-palette="X"').replace('</head>',`<style>${css}</style></head>`);
  const tmp=`${V2}/${po}/html/_pal_${p.id}.html`;fs.writeFileSync(tmp,h);
  const pg=await b.newPage({viewport:{width:1080,height:1350}});await pg.goto('file://'+tmp);await pg.waitForTimeout(300);
  await pg.screenshot({path:`${__dirname}/${po}_${p.id}.png`});await pg.close();fs.unlinkSync(tmp);}}
await b.close()})();
