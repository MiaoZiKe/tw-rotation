// final3_compare.png：最終三選一（P3 對話杯精修、01 蒸氣寫字、S1 書頁杯精修）
// 用法：node final3.js <蒸氣寫字資料夾> <註記文字>
const { chromium } = require('playwright');const fs=require('fs'),path=require('path');
const B=path.resolve(__dirname,'..','..','..');
const N=path.resolve(process.argv[2]),note=process.argv[3]||'';
const pick=(dir,cands)=>{const fs_=fs.readdirSync(dir);for(const c of cands){const re=new RegExp(c);const f=fs_.find(x=>re.test(x)&&x.endsWith('.png'));if(f)return 'file://'+path.join(dir,f);}return null;};
const A=JSON.parse(fs.readFileSync(path.join(B,'pro/final/src/dirs.json'))).find(d=>d.id==='F1');
const S=JSON.parse(fs.readFileSync(path.join(__dirname,'dirs.json'))).find(d=>d.id==='S1');
const nmd=fs.readFileSync(path.join(B,'nordic/README.md'),'utf8').match(/\| 01 \| [^|]+\| ([^|]+)\|/);
const cols=[
 {name:'P3 對話杯',sub:'實心杯（第一批精修）',dir:path.join(B,'pro/final',A.dir),m:A.meaning},
 {name:'01 蒸氣寫字',sub:'線畫（日系北歐）'+(note?`｜${note}`:''),dir:N,m:nmd?nmd[1].trim():''},
 {name:'S1 書頁杯',sub:'書頁（第三批精修）',dir:path.join(B,'pro3/final/S1'),m:S.meaning}];
const col=c=>{const d=c.dir,P=a=>pick(d,a);
 const av=['avatar_110_light','avatar_110_dark','avatar_110$|avatar_110\\.','avatar_110'].map(x=>x);
 const imgs={a110:[P(['avatar_110_light','avatar_110']),P(['avatar_110_dark'])],a40:[P(['avatar_40_light','avatar_40']),P(['avatar_40_dark'])],
  ll:P(['lockup_light','horizontal_light']),ld:P(['lockup_dark','horizontal_dark']),ig:P(['app_ig_profile','mock_ig_profile','ig']),cup:P(['app_cup','mock_takeaway_cup','cup'])};
 const im=(s,cls,w)=>s?`<img class="${cls}" src="${s}"${w?` width="${w}"`:''}>`:'';
 return `<div class="col"><div class="hd"><b>${c.name}</b><span>${c.sub}</span></div>
 <div class="av">${im(imgs.a110[0],'',110)}${im(imgs.a110[1],'',110)}${im(imgs.a40[0],'',40)}${im(imgs.a40[1],'',40)}<em>110／40px 實寸</em></div>
 ${im(imgs.ll,'lk')}${im(imgs.ld,'lk')}<div class="row">${im(imgs.ig,'ig')}${im(imgs.cup,'cup')}</div><p>${c.m}</p></div>`};
const html=`<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#EFE6DA;color:#2B1D16;padding:44px;width:2712px;font-family:Inter,'WenQuanYi Zen Hei'}
h1{font:600 46px Inter,'WenQuanYi Zen Hei';margin:0 0 6px}.s{font:22px 'WenQuanYi Zen Hei';opacity:.7;margin:0 0 28px}
.g{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}.col{background:#FFFBF5;border-radius:26px;padding:28px;display:flex;flex-direction:column;gap:16px}
.hd b{font:700 38px Inter,'WenQuanYi Zen Hei';margin-right:14px}.hd span{font:21px 'WenQuanYi Zen Hei';opacity:.65}
.av{display:flex;gap:14px;align-items:center}.av em{font:17px 'WenQuanYi Zen Hei';opacity:.55;font-style:normal}
.lk{width:100%;border-radius:12px;object-fit:contain;background:transparent}.row{display:flex;gap:14px;align-items:flex-start}.ig{width:540px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08)}.cup{width:270px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08)}
p{font:23px/1.6 'WenQuanYi Zen Hei';margin:4px 0 0}</style>
<h1>CaffAIne 最終三選一</h1><p class="s">每欄：大頭貼 110／40px、淺底橫式、深底橫式、IG 個人頁、外帶杯、一句含義</p><div class="g">${cols.map(col).join('')}</div>`;
(async()=>{const f=path.join(__dirname,'_f3.html');fs.writeFileSync(f,html);const br=await chromium.launch();const pg=await br.newPage({viewport:{width:2800,height:900}});
 await pg.goto('file://'+f);await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(400);await pg.screenshot({path:path.join(B,'final3_compare.png'),fullPage:true});await br.close();fs.unlinkSync(f);console.log('ok');})();
