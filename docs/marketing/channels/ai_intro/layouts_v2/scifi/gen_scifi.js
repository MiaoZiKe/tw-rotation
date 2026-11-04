// 頻道③ 版型 v2「近未來硬科幻」三方向：S1 任務文件／S2 深空觀測／S3 軌道儀表。
// 骨架沿用 tech/gen_tech.js（同一組 4 張內容、同樣的 data-o 重疊檢查），裝飾全為 SVG／CSS，不用 AI 生圖。
const FONT="'Noto Sans TC','WenQuanYi Zen Hei','文泉驛正黑',sans-serif";
const MONO="'JetBrains Mono','DejaVu Sans Mono',monospace";
const am0='#E3A33B';
// 2b 錯高雙塊：形狀不變（與 round2/r2b 同座標），僅換配色
const logo=(s,a,b,cut)=>`<svg width="${s}" height="${s}" viewBox="60 100 390 310" style="display:block"><rect x="84" y="120" width="166" height="190" rx="36" fill="${a}"/><rect x="262" y="202" width="166" height="190" rx="36" fill="${b}"/><path d="M130 232L160 262L215 187" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M305 257L385 337M385 257L305 337" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`;
const camera=(c,s)=>`<svg width="${s}" height="${s}" viewBox="0 0 64 64" fill="none" stroke="${c}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"><rect x="6" y="14" width="52" height="38" rx="8"/><circle cx="32" cy="33" r="10"/><path d="M22 14l4-6h12l4 6"/></svg>`;
const TXT={what:'微軟向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。',say:'公司說是為員工增加彈性。媒體把它和 AI 投資成本連在一起，這是媒體的解讀，不是公司原話。',diff:'看到「AI 導致裁員」的標題時，先分清「公司說的原因」和「媒體猜的原因」。',ph1:'ChatGPT 對「分帳」題的完整回答畫面，需看得到提問與互動元件',ph2:'要遮：聊天紀錄、帳號名稱、分頁列',key:'這題 2 次裡有【__】次出現互動元件；金額與 Excel 差【__】元。',cond:'每題都記：差幾元、有無互動元件、能不能點、有無引條文。測試條件：【待填】日期、方案、網頁或手機'};
const TBL=[['題目','我問什麼','怎麼驗'],['分帳','4 人聚餐分帳','Excel 自算'],['比較','三個手機方案','逐格對數字'],['試算','房貸月付','Excel PMT'],['流程','請假流程圖','查有無漏步'],['純知識','特休怎麼算','看有沒有硬塞']];
const rows=[['微軟 6 萬人','來源 2｜信心 中'],['紐約新法','來源 2｜信心 中'],['Claude Duet','來源 2｜信心 中']];
const tbl=(w)=>`<table><colgroup>${w.map(x=>`<col style="width:${(x*100/w.reduce((a,b)=>a+b)).toFixed(2)}%">`).join('')}</colgroup>${TBL.map((r,i)=>`<tr>${r.map(c=>i?`<td>${c}</td>`:`<th>${c}</th>`).join('')}</tr>`).join('')}</table>`;
const mono=h=>h.split(/(<[^>]+>)/).map(p=>p.startsWith('<')?p:p.replace(/\d+(?:[\/.:~]\d+)*/g,'<span class="m">$&</span>')).join('');
// 種子亂數（星點位置固定、可重現）
const rng=s=>()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296};
const L=(x1,y1,x2,y2,c,w=1.5)=>`<line class="dc" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${w}"/>`;
const C=(cx,cy,r,c,w=1.5,f='none')=>`<circle class="dc" cx="${cx}" cy="${cy}" r="${r}" fill="${f}" stroke="${c}" stroke-width="${w}"/>`;
const ruler=(x1,x2,y,step,every,sh,lg,c,dir,cl,cw=1.5)=>{let s=L(x1,y,x2,y,c,cw);for(let x=x1,i=0;x<=x2;x+=step,i++){const long=i%every===0;s+=L(x,y,x,y+dir*(long?lg:sh),long&&cl?cl:c,long?2:1.5)}return s};
const vscale=(x,y1,y2,step,every,sh,lg,c,dir)=>{let s='';for(let y=y1,i=0;y<=y2;y+=step,i++){const long=i%every===0;s+=L(x,y,x+dir*(long?lg:sh),y,c,long?2:1.5)}return s};
// 任務徽記（自行設計的臂章風格小徽記：外環、傾斜軌道橢圓、中心星點、四向刻度）
const emblem=(cx,cy,r,c,a)=>C(cx,cy,r,c,2)+C(cx,cy,r*.62,c,1.5)+`<ellipse class="dc" cx="${cx}" cy="${cy}" rx="${r*.86}" ry="${r*.3}" transform="rotate(-28 ${cx} ${cy})" fill="none" stroke="${c}" stroke-width="1.5"/>`+C(cx+r*.55,cy-r*.3,r*.11,a,1.5,a)+L(cx,cy-r-6,cx,cy-r+5,c,2)+L(cx,cy+r-5,cx,cy+r+6,c,2)+L(cx-r-6,cy,cx-r+5,cy,c,2)+L(cx+r-5,cy,cx+r+6,cy,c,2)+C(cx,cy,r*.1,c,1.5,c);
// 同心圓儀表（封面右側）：圓環、刻度、十字準線、傾斜軌道、衛星點
const dial=(cx,cy,rs,c,cf,a,ex)=>{let s='';rs.forEach(r=>s+=C(cx,cy,r,c,1.5));const R=rs[rs.length-1];
 for(let d=0;d<360;d+=10){const rad=d*Math.PI/180,l=d%30===0?12:7;s+=L((cx+(R-l)*Math.cos(rad)).toFixed(1),(cy+(R-l)*Math.sin(rad)).toFixed(1),(cx+R*Math.cos(rad)).toFixed(1),(cy+R*Math.sin(rad)).toFixed(1),cf,d%30===0?2:1.5)}
 s+=L(cx-R-ex,cy,cx+R+ex,cy,cf,1.5)+L(cx,cy-R-ex,cx,cy+R+ex,cf,1.5);
 s+=`<ellipse class="dc" cx="${cx}" cy="${cy}" rx="${R*1.18}" ry="${R*.38}" transform="rotate(-24 ${cx} ${cy})" fill="none" stroke="${a}" stroke-width="1.5" stroke-dasharray="9 7"/>`;
 const m=rs[Math.floor(rs.length/2)],ang=-40*Math.PI/180;s+=C((cx+m*Math.cos(ang)).toFixed(1),(cy+m*Math.sin(ang)).toFixed(1),7,a,2,a)+C(cx,cy,5,cf,1.5,cf);return s};
const G=(n,x)=>`<g data-g="${n}">${x}</g>`;
const bars=(x1,x2,y,c,a,seed)=>{const r=rng(seed);let s=L(x1,y,x2,y,c,1.5);for(let x=x1+4,i=0;x<x2-4;x+=12,i++){const hh=Math.round(4+r()*r()*18+(i%7===0?6:0));s+=`<rect class="dc" x="${x}" y="${y-hh-2}" width="5" height="${hh}" fill="${hh>16?a:c}"/>`}return s};
const stars=(seed,n,x1,y1,x2,y2,col,bright)=>{const r=rng(seed);let s='';for(let i=0;i<n;i++){const x=(x1+r()*(x2-x1)).toFixed(1),y=(y1+r()*(y2-y1)).toFixed(1),k=r(),rad=k<.7?.9:k<.93?1.4:2;s+=`<circle class="dc st" cx="${x}" cy="${y}" r="${rad}" fill="${col}" opacity="${(.18+r()*.5).toFixed(2)}"/>`}
 for(let i=0;i<bright;i++){const x=+(x1+r()*(x2-x1)).toFixed(0),y=+(y1+r()*(y2-y1)).toFixed(0);s+=`<g class="st2">${L(x-7,y,x+7,y,col,1.2)}${L(x,y-7,x,y+7,col,1.2)}</g>`}return s};

// ---------- 三方向主題 ----------
const THEMES={
 s1:{name:'S1 任務文件',base:'#F8F3E6',vars:`--bg:#EEE6D3;--tx:#13263E;--tx2:#34475E;--hdtx:#13263E;--ms:#34475E;--cb:rgba(19,38,62,.78);--cbg:#FBF7EC;--am:#E3A33B;--amt:#7A4F05;--h3:#13263E;--pillbg:transparent;--pillbd:#13263E;--pilltx:#13263E;--tg:#7A4F05;--tgx:#7A4F05;--badgebg:#F6E3B5;--thbg:#13263E;--thtx:#F3C15C;--tdf:#EFDFB8;--tdl:rgba(19,38,62,.35);--phbd:#B97A12;--phbg:#F6E7C2;--phtx:#13263E;--phtx2:#6A4503;--r:3px;--tw:400;`,
  logo:['#13263E','#E3A33B','#EEE6D3'],bdr:'rgba(19,38,62,.5)',
  css:`body{background-image:linear-gradient(rgba(19,38,62,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(19,38,62,.055) 1px,transparent 1px),radial-gradient(ellipse 1000px 800px at 30% 20%,rgba(255,250,236,.7),rgba(255,250,236,0) 70%);background-size:40px 40px,40px 40px,100% 100%}
.card h3{border-left:8px solid var(--am);padding:0 0 0 14px;color:var(--h3)}
.th-hi{}`},
 s2:{name:'S2 深空觀測',base:'#0A1530',vars:`--bg:#060C18;--tx:#E9EFF7;--tx2:#B4C3D8;--hdtx:#EEF3FA;--ms:#AFC0D6;--cb:rgba(170,198,236,.42);--cbg:#0A1428;--am:#F0B84F;--amt:#F0B84F;--h3:#F0B84F;--pillbg:transparent;--pillbd:#F0B84F;--pilltx:#F4C568;--tg:rgba(170,198,236,.7);--tgx:#C9D8EC;--badgebg:rgba(240,184,79,.14);--thbg:rgba(240,184,79,.16);--thtx:#F4C568;--tdf:rgba(240,184,79,.08);--tdl:rgba(170,198,236,.28);--phbd:rgba(240,184,79,.85);--phbg:rgba(240,184,79,.07);--phtx:#EEF3FA;--phtx2:#C9D2E0;--r:3px;--tw:400;`,
  logo:['#EEF3FA','#F0B84F','#060C18'],bdr:'rgba(170,198,236,.42)',
  css:`body{background:radial-gradient(ellipse 1000px 440px at 50% 100%,rgba(226,148,58,.34),rgba(226,148,58,0) 72%),radial-gradient(ellipse 760px 560px at 90% 0%,rgba(80,120,190,.24),rgba(80,120,190,0) 70%),linear-gradient(180deg,#050B16 0%,#08122A 55%,#0C1B36 100%)}
.card h3{padding:0 0 4px;border-bottom:2px solid var(--am);color:var(--h3)}
.card,.tw{backdrop-filter:none}`},
 s3:{name:'S3 軌道儀表',base:'#FFFFFF',vars:`--bg:#E6ECF2;--tx:#0E2036;--tx2:#2E4259;--hdtx:#F1F5FA;--ms:#B5C6DA;--cb:rgba(14,32,54,.75);--cbg:#FFFFFF;--am:#E0A03A;--amt:#7A4F05;--h3:#F2C260;--pillbg:transparent;--pillbd:#E0A03A;--pilltx:#F2C260;--tg:#0E2036;--tgx:#0E2036;--badgebg:#F8E7BE;--thbg:#0A1626;--thtx:#F2C260;--tdf:#E6EDF4;--tdl:rgba(14,32,54,.3);--phbd:#C58718;--phbg:#FBF0D3;--phtx:#0E2036;--phtx2:#6A4503;--r:3px;--tw:700;`,
  logo:['#F1F5FA','#E0A03A','#0A1626'],bdr:'rgba(14,32,54,.5)',
  css:`body{background-image:linear-gradient(rgba(10,22,38,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(10,22,38,.05) 1px,transparent 1px);background-size:40px 40px}
.hd{background:linear-gradient(105deg,#08121F 0%,#0C1D33 62%,#12294A 100%);border-bottom:3px solid var(--am)}
.card h3{padding:0 0 4px;border-bottom:2px solid var(--am);color:#0E2036}
.g3 b.n{color:#0A1626}`}};

const BASE=`*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1350px;overflow:hidden}
body{position:relative;font-family:${FONT};color:var(--tx);background-color:var(--bg)}
.m{font-family:${MONO};font-weight:inherit;letter-spacing:-.5px}
.pg{position:absolute;left:0;top:0;z-index:0}
.hd{position:absolute;left:0;right:0;top:0;color:var(--hdtx);padding:100px 64px 40px;display:flex;flex-direction:column;gap:24px;z-index:1;overflow:hidden}
.hd>*:not(.ms):not(svg.bd){position:relative;z-index:1}.hd>svg.bd{position:absolute;z-index:0;left:0;top:0}
.ms{position:absolute;z-index:1;top:40px;left:64px;right:64px;display:flex;justify-content:space-between;font-family:${MONO};font-size:28px;line-height:36px;color:var(--ms);white-space:nowrap}
.ms span+span{border-left:1.5px solid var(--ms);padding-left:20px}.ms .m{letter-spacing:0}
.main{position:absolute;left:64px;right:64px;bottom:144px;display:flex;flex-direction:column;gap:26px;z-index:1}
.disc{position:absolute;left:64px;right:64px;bottom:72px;height:48px;border-top:1.5px solid var(--cb);padding-top:6px;display:flex;justify-content:space-between;font-size:28px;font-weight:400;line-height:36px;color:var(--tx2);z-index:1}.disc b{font-weight:700;color:var(--tx)}
.srow{display:flex;justify-content:space-between;align-items:center;gap:24px}.ser{display:flex;gap:16px;align-items:center;font-size:36px;font-weight:700;letter-spacing:1px}
.pill{background:var(--pillbg);color:var(--pilltx);border:1.5px solid var(--pillbd);border-radius:3px;padding:4px 20px;font-size:30px;font-weight:700}
.t{font-weight:var(--tw);line-height:1.12;letter-spacing:1px}
.card{border:1.5px solid var(--cb);border-radius:var(--r);background:var(--cbg);padding:22px 24px;position:relative}
.card::before,.card::after{content:'';position:absolute;width:18px;height:18px;border:0 solid var(--am)}
.card::before{left:-2px;top:-2px;border-left-width:4px;border-top-width:4px}.card::after{right:-2px;bottom:-2px;border-right-width:4px;border-bottom-width:4px}
.badge{border:1.5px solid var(--cb);background:var(--badgebg);border-radius:3px;padding:4px 24px;font-size:28px;font-weight:700;white-space:nowrap}
.brow{display:flex;justify-content:space-between;align-items:center;gap:24px}
.tag{border:1.5px solid var(--tg);color:var(--tgx);background:transparent;padding:4px 18px 4px 16px;font-family:${MONO};font-size:28px;font-weight:500;white-space:nowrap;display:flex;gap:10px;align-items:center;border-radius:3px}.tag i{display:inline-block;width:12px;height:12px;background:var(--am);flex:none}
.g3{display:flex;gap:24px;flex:1}.g3 .card{flex:1;display:flex;flex-direction:column;justify-content:space-between}.g3 b.n{font-size:150px;line-height:1;font-weight:500;font-family:${MONO}}.g3 .nm{font-size:44px;font-weight:700;line-height:1.2}.g3 .sm{font-size:28px;font-weight:500;color:var(--tx2)}
.g2{display:flex;gap:24px;flex:1}.g2 .card{flex:1}.card h3{font-size:34px;font-weight:700;margin-bottom:10px;display:inline-block;line-height:1.3}.card p{font-size:38px;font-weight:500;line-height:1.5}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}th{background:var(--thbg);color:var(--thtx);font-size:34px;font-weight:700;text-align:left;padding:0 18px;height:88px}td{font-size:36px;font-weight:600;padding:0 18px;border-bottom:1.5px solid var(--tdl);color:var(--tx)}td:first-child{background:var(--tdf);font-weight:700}
.fr{flex:1;display:flex;position:relative}
.tw{flex:1;border:1.5px solid var(--cb);border-radius:var(--r);overflow:hidden;background:var(--cbg)}
.ph{flex:1;border:5px dashed var(--phbd);border-radius:var(--r);background:var(--phbg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:0 36px;color:var(--phtx)}
.ph b{font-size:62px;font-weight:700}.ph p{font-size:32px;font-weight:600;line-height:1.45}
.bk{position:absolute;width:28px;height:28px;border:0 solid var(--am)}.bk.a{left:-9px;top:-9px;border-left-width:4px;border-top-width:4px}.bk.b{right:-9px;top:-9px;border-right-width:4px;border-top-width:4px}.bk.c{left:-9px;bottom:-9px;border-left-width:4px;border-bottom-width:4px}.bk.d{right:-9px;bottom:-9px;border-right-width:4px;border-bottom-width:4px}`;

// ---------- 裝飾（皆為背景層，class dc；星點 class st 會在版面算完後避開文字） ----------
function deco(v,h,n){
 const T=THEMES[v];let pg='',bd='';
 const bottom=(c,a,fillSeg)=>{ // 底部：徽記、基準線、頁碼節段（y>=1288，揭露列在 1230~1278 之上）
  let s=emblem(88,1307,19,c,a)+ruler(130,720,1307,12,5,6,12,c,-1,a);
  s+=C(720,1307,5,c,1.5)+L(740,1307,812,1307,c,1.5);
  for(let i=0;i<4;i++){const x=838+i*46;s+=`<rect class="dc" x="${x}" y="1302" width="38" height="10" fill="${i<n?a:'none'}" stroke="${i<n?a:c}" stroke-width="1.5"/>`}
  return G('bottom',s)};
 const sides=(c,y1)=>G('side',vscale(26,y1,1220,20,5,9,18,c,1)+vscale(1054,y1,1220,20,5,9,18,c,-1));
 if(v==='s1'){
  const c='rgba(19,38,62,.5)',cf='rgba(19,38,62,.38)',a='#B97A12';
  pg+=G('frame',`<rect class="dc" x="14" y="14" width="1052" height="1322" fill="none" stroke="${c}" stroke-width="1.5"/>`+[[14,14,1,1],[1066,14,-1,1],[14,1336,1,-1],[1066,1336,-1,-1]].map(([x,y,dx,dy])=>L(x,y,x+dx*54,y,a,4)+L(x,y,x,y+dy*54,a,4)).join(''));
  pg+=G('ruler',ruler(64,n===1?780:1016,h-8,8,5,7,15,cf,-1,a));
  pg+=sides(cf,h+40);
  if(n===1)pg+=G('dial',dial(936,526,[34,60,86,112],cf,c,a,8));
  pg+=bottom(c,a);
 }else if(v==='s2'){
  const c='rgba(170,198,236,.45)',cf='rgba(170,198,236,.3)',a='#F0B84F';
  pg+=stars(100+n,230,8,8,1072,1285,'#DDE8F8',0);
  for(const [x,y,dx,dy] of [[20,20,1,1],[1060,20,-1,1],[20,1330,1,-1],[1060,1330,-1,-1]])pg+=L(x,y,x+dx*40,y,c,2)+L(x,y,x,y+dy*40,c,2);
  pg+=G('ruler',n===1?ruler(64,780,h-8,10,5,6,14,cf,-1,a):bars(64,940,h-12,cf,a,500+n));
  pg+=sides(cf,h+40);
  if(n===1)pg+=G('dial',dial(936,526,[34,60,86,112],cf,c,a,8));
  pg+=`<path d="M0 1348 Q540 1322 1080 1348 L1080 1350 L0 1350Z" fill="#02050B"/>${G('limb','<path class="dc" d="M0 1346 Q540 1320 1080 1346" fill="none" stroke="rgba(240,184,79,.8)" stroke-width="2"/>')}`;
  pg+=bottom(c,a);
 }else{
  const c='rgba(14,32,54,.55)',cf='rgba(14,32,54,.38)',a='#B97A12',bc='rgba(181,198,218,.5)',bf='rgba(181,198,218,.32)',ba='#F2C260';
  bd+=stars(300+n,46,8,8,1072,h-14,'#CFE0F5',0);
  bd+=G('ruler',ruler(64,1016,20,12,5,7,13,bf,1,ba));
  bd+=G('band',bars(64,n===1?820:940,h-14,bf,ba,700+n));
  if(n===1)bd+=G('dial',dial(1040,470,[50,90,130,170],bf,bc,ba,16));
  else{let q='';for(const r of [36,72,108])q+=`<path class="dc" d="M${1080-r} ${h-12} A${r} ${r} 0 0 1 1080 ${h-12-r}" fill="none" stroke="${bc}" stroke-width="1.5"/>`;q+=C(1080-72*.71,h-12-72*.71,6,ba,2,ba);bd+=G('arc',q)}
  pg+=sides(cf,h+50);
  pg+=bottom(c,a);
 }
 return [`<svg class="pg" width="1080" height="1350" viewBox="0 0 1080 1350">${pg}</svg>`,`<svg class="bd" width="1080" height="${h-(v==='s3'?3:0)}" viewBox="0 0 1080 ${h-(v==='s3'?3:0)}">${bd}</svg>`];
}

function build(v){
 const T=THEMES[v],[la,lb,lc]=T.logo;
 const css=`:root{${T.vars}}`+BASE+T.css;
 const missions=['045-01','045-02','045-03','045-04'];
 const ms=(n)=>`<div class="ms" data-in="色塊" data-o="任務列"><span>任務 ${missions[n-1]}</span><span>北緯 25.03　東經 121.56</span><span>發佈日 11/03</span></div>`;
 const hdr=(l,r)=>`<div class="srow"><div class="ser" data-in="色塊" data-o="系列標">${logo(58,la,lb,lc)}<span>${l}</span></div><div class="pill" data-in="色塊" data-o="右標">${r}</div></div>`;
 const disc=l=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
 const tag=s=>`<div class="tag" data-o="資料角標"><i></i>${s}</div>`;
 const brk='<span class="bk a"></span><span class="bk b"></span><span class="bk c"></span><span class="bk d"></span>';
 const blk=(h,n,inner)=>{const [pg,bd]=deco(v,h,n);return `${pg}<div class="hd" data-o="色塊" style="height:${h}px">${bd}${ms(n)}${inner}</div>`};
 const bgs=v==='s2'?['','','']:v==='s1'?['#F3DDB0','#FBF7EC','#DCE5EC']:['#F8E7BE','#FFFFFF','#DCE7F2'];
 const pages=[
  blk(650,1,`${hdr('本週 AI 三則','10/28 ~ 11/03')}<div class="t" data-in="色塊" data-o="標題" style="font-size:122px">三則 AI 新聞<br>只講跟你上班<br>有關的</div>`)+
  `<div class="main" style="top:700px"><div class="brow"><div data-o="副標" style="font-size:44px;font-weight:700;white-space:nowrap">每則附來源、日期、可信度</div>${tag('第 45 週｜第 1 版')}</div><div class="g3">${rows.map((r,i)=>`<div class="card" data-o="卡${i}" style="${bgs[i]?'background:'+bgs[i]:''}"><b class="n">${i+1}</b><div class="nm">${r[0]}</div><div class="sm">${r[1]}</div></div>`).join('')}</div></div>${disc('自製圖文')}`,
  blk(450,2,`${hdr('本週 AI 三則','2/6')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">新聞 1／3<br>微軟提出約 6 萬人自願離職方案</div><div style="display:flex;gap:16px" data-in="色塊" data-o="資訊列"><span class="pill">事件日 10/26 美東</span><span class="pill">查證日 11/03</span><span class="pill">信心度 中</span></div>`)+
  `<div class="main" style="top:480px"><div class="g2"><div class="card" data-o="發生什麼"><h3>發生什麼</h3><p>${TXT.what}</p></div><div class="card" data-o="怎麼說"><h3>微軟怎麼說</h3><p>${TXT.say}</p></div></div><div class="card" data-o="差在哪" style="${v==='s2'?'background:#171A26':v==='s1'?'background:#F6E7C2':'background:#FBF0D3'}"><h3>對上班族差在哪</h3><p>${TXT.diff}</p></div><div class="brow"><div class="badge" data-o="標章">整理自新聞｜我沒親自測</div>${tag('查證 01｜第 1 版｜11/03')}</div></div>${disc('自製圖文')}`,
  blk(320,3,`${hdr('AI 實測 第 01 期','3/7')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">我怎麼測：5 種題目 × 2 次</div>`)+
  `<div class="main" style="top:350px"><div class="fr">${brk}<div class="tw" data-o="表">${tbl([180,380,392])}</div></div><div data-o="條件" style="font-size:32px;font-weight:500;line-height:1.45;color:var(--tx2)">${TXT.cond}</div><div class="brow"><div class="badge" data-o="標章">自製表格｜非 AI 生成</div>${tag('實測 01｜第 1 版｜11/03')}</div></div>${disc('自製圖文')}`,
  blk(320,4,`${hdr('AI 實測 第 01 期','4/7')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">步驟 1　它真的變出計算器了</div>`)+
  `<div class="main" style="top:350px"><div class="fr">${brk}<div class="ph" data-o="截圖框">${camera(v==='s2'?'#F0B84F':'#B97A12',96)}<b>待 Andy 截圖</b><p>${TXT.ph1}</p><p style="font-size:30px;color:var(--phtx2)">${TXT.ph2}</p></div></div><div class="card" data-o="重點" style="font-size:34px;font-weight:500;line-height:1.45;padding:16px 24px"><span style="background:var(--am);color:#0A1626;font-weight:700;padding:0 14px;margin-right:12px;display:inline-block">重點：</span>${TXT.key}</div><div class="brow"><div class="badge" data-o="標章">截圖為實測｜非 AI 生成</div>${tag('實測 01｜第 1 版｜11/03')}</div></div>${disc('截圖已遮個資')}`];
 const strip=(p)=>p.replace(/(<div class="(?:tag|ms)"[^>]*>)([\s\S]*?)(<\/div>)/g,(m,a,b,c)=>a+b.replace(/<span class="m">|<\/span>/g,(x)=>x==='</span>'?x:'')+c);
 // 角標與任務列整段已是等寬字：把裡面為數字加的 span.m 拿掉（保留任務列的分段 span）
 const fix=p=>p.replace(/(<div class="tag"[^>]*>)(.*?)(<\/div>)/g,(m,a,b,c)=>a+b.replace(/<span class="m">([^<]*)<\/span>/g,'$1')+c).replace(/(<div class="ms"[^>]*>)(.*?)(<\/div>)/g,(m,a,b,c)=>a+b.replace(/<span class="m">([^<]*)<\/span>/g,'$1')+c);
 return {css,pages:pages.map(mono).map(fix)};
}
module.exports={build,THEMES,MONO,FONT};
