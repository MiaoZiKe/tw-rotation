// 產出：每個方向的 SVG／PNG、大頭貼、橫式、三個應用情境、重疊量測報告、總覽
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
const FINAL = !!process.env.FINAL, HANKO = !!process.env.HANKO;
const { DARK_BG } = require('./marks');
const { dirs } = FINAL ? require('./final_marks') : HANKO ? require('./hanko_marks') : require('./marks');
const OUT = FINAL ? path.resolve(__dirname, '..', 'final') : HANKO ? path.resolve(__dirname, '..', 'hanko') : path.resolve(__dirname, '..');
const AIPX = ['.###..###', '#...#..#.', '#####..#.', '#...#..#.', '#...#.###'];
const TAG = '一杯咖啡的時間，看懂一個 AI 新知';
const CJK = "'WenQuanYi Zen Hei'";
const report = [];

// ---------- 瀏覽器端的排版工具（注入到頁面） ----------
const LIB = `
const AIPX=${JSON.stringify(['.####..######', '##..##...##..', '##..##...##..', '######...##..', '##..##...##..', '##..##...##..', '##..##.######'])};
const NS='http://www.w3.org/2000/svg';
function el(p,tag,attrs,txt){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(txt!=null)e.textContent=txt;p.appendChild(e);return e;}
function capH(font,w,size,ch){const c=document.createElement('canvas').getContext('2d');c.font=w+' '+size+'px "'+font+'"';return c.measureText(ch||'I').actualBoundingBoxAscent;}
// 文字標 CaffAIne：x 為左緣、base 為基線；回傳寬度
function word(svg,cfg,col,size,x,base){
  const g=el(svg,'g',{'data-role':'word'});
  const f=cfg.font, st=(w,fill)=>({x:0,y:base,'font-family':f,'font-weight':w,'font-size':size,fill});
  let cx=x; const t1=el(g,'text',{...st(cfg.w,col.ink),x:cx},'Caff'); cx+=t1.getComputedTextLength();
  const ch=capH(f,cfg.aiW,size,'I');
  if(cfg.ai==='pixelAI'||cfg.ai==='inlineSeal'){
    const px=(rows,cs,x0,y0)=>{let d='';rows.forEach((r,y)=>[...r].forEach((c,x)=>{if(c==='#')d+='M'+(x0+x*cs)+' '+(y0+y*cs)+'h'+cs+'v'+cs+'h-'+cs+'z';}));return d;};
    if(cfg.ai==='pixelAI'){const cs=ch/7;cx+=size*0.06;el(g,'path',{d:px(AIPX,cs,cx,base-ch),fill:col.aiText||col[cfg.aiColor]||col.accent});cx+=13*cs+size*0.07;}
    else{const cs=ch*0.11,pw=13*cs+cs*4,ph=7*cs+cs*4,y0=base-ch/2-ph/2;cx+=size*0.06;el(g,'rect',{x:cx+cs*0.35,y:y0+cs*0.35,width:pw-cs*0.7,height:ph-cs*0.7,rx:cs*0.15,fill:'none',stroke:col.accent,'stroke-width':cs*0.7});el(g,'path',{d:px(AIPX,cs,cx+cs*2,y0+cs*2),fill:col.accent});cx+=pw+size*0.06;}
    const t3=el(g,'text',{...st(cfg.w,col.ink),x:cx},'ne'); cx+=t3.getComputedTextLength(); return {g,w:cx-x};
  }
  const aiFill = cfg.ai==='pill'?col.paperText||'#FBF4EA': cfg.ai==='text'?col.text: cfg.ai==='rakkan'?col.accent: cfg.ai==='underline'?col.accent: col.accent;
  const padX=size*0.16, gapI=cfg.iBars?size*0.07:size*0.02;
  if(cfg.ai==='pill'){cx+=size*0.05+padX;}
  const pillStart=cx-padX;
  const tA=el(g,'text',{...st(cfg.aiW,aiFill),x:cx},'A'); const xA=cx; cx+=tA.getComputedTextLength()+gapI;
  const tI=el(g,'text',{...st(cfg.aiW,aiFill),x:cx},'I'); const eI=tI.getExtentOfChar(0); cx+=tI.getComputedTextLength();
  if(cfg.iBars){ // 無襯線字體的 I 加上下橫筆，避免被讀成小寫 l
    const icx=eI.x+eI.width/2, bw=size*0.34, th=size*0.115;
    el(g,'rect',{x:icx-bw/2,y:base-ch,width:bw,height:th,rx:th*0.25,fill:aiFill});
    el(g,'rect',{x:icx-bw/2,y:base-th,width:bw,height:th,rx:th*0.25,fill:aiFill});
    cx+=size*0.10;
  }
  if(cfg.ai==='pill'){const pr=el(g,'rect',{x:pillStart,y:base-ch-size*0.17,width:cx+padX-pillStart,height:ch+size*0.34,rx:size*0.16,fill:col.accent});g.insertBefore(pr,tA);cx+=padX+size*0.05;}
  if(cfg.ai==='underline'){el(g,'rect',{x:xA,y:base+size*0.11,width:cx-xA,height:size*0.075,rx:size*0.03,fill:col.accent});}
  cx+= cfg.iBars? size*0.0 : size*0.02;
  const t3=el(g,'text',{...st(cfg.w,col.ink),x:cx},'ne'); cx+=t3.getComputedTextLength();
  if(cfg.ai==='rakkan'){const cs=size*0.05,w=7*cs,h=13*cs,x0=cx+size*0.10,y0=base-ch-size*0.04;el(g,'rect',{x:x0,y:y0,width:w,height:h,rx:cs*0.3,fill:col.accent});let d='';const A=['.###.','#...#','#####','#...#','#...#','.....','.###.','..#..','..#..','..#..','.###.'];A.forEach((r,yy)=>[...r].forEach((c,xx)=>{if(c==='#')d+='M'+(x0+(xx+1)*cs)+' '+(y0+(yy+1)*cs)+'h'+cs+'v'+cs+'h-'+cs+'z';}));el(g,'path',{d,fill:col.paperText||'#FBF4EA'});cx=x0+w;}
  return {g,w:cx-x};
}
function mark(svg,inner,x,y,s,role){const g=el(svg,'g',{transform:'translate('+x+' '+y+') scale('+(s/200)+')'});if(role)g.setAttribute('data-role',role);g.innerHTML=inner;return g;}
function tag(svg,col,size,x,base,anchor,lines){const g=el(svg,'g',{'data-role':'tag'});(lines||[${JSON.stringify(TAG)}]).forEach((l,i)=>el(g,'text',{x,y:base+i*size*1.45,'font-family':${JSON.stringify(CJK)},'font-size':size,fill:col.ink,opacity:0.78,'text-anchor':anchor||'start'},l));return g;}
// 量測：各 data-role 的外框（文字用字身框，比實際筆畫保守），兩兩算最短距離
function measure(svg,padMark){
  const sr=svg.getBoundingClientRect(); const rs=[...svg.querySelectorAll('[data-role]')].map(e=>{const r=e.getBoundingClientRect();let p=e.getAttribute('data-role')==='mark'?padMark:0;return {role:e.getAttribute('data-role'),l:r.left-sr.left-p,t:r.top-sr.top-p,r:r.right-sr.left+p,b:r.bottom-sr.top+p};});
  const pairs=[];for(let i=0;i<rs.length;i++)for(let j=i+1;j<rs.length;j++){const a=rs[i],b=rs[j];const dx=Math.max(0,Math.max(a.l,b.l)-Math.min(a.r,b.r)),dy=Math.max(0,Math.max(a.t,b.t)-Math.min(a.b,b.b));const gap=(dx>0&&dy>0)?Math.hypot(dx,dy):Math.max(dx,dy);pairs.push({pair:a.role+'–'+b.role,gap:+gap.toFixed(1),overlap:dx===0&&dy===0});}
  const W=svg.viewBox.baseVal.width, H=svg.viewBox.baseVal.height; const outOf=rs.filter(r=>r.l<0||r.t<0||r.r>W||r.b>H).map(r=>r.role);
  return {boxes:rs.map(r=>({role:r.role,l:Math.round(r.l),t:Math.round(r.t),r:Math.round(r.r),b:Math.round(r.b)})),pairs,outOfCanvas:outOf};
}
`;

async function shot(page, html, file, w, h, transparent) {
  await page.setViewportSize({ width: w, height: h });
  await page.setContent(`<html><head><style>html,body{margin:0;background:transparent}</style></head><body>${html}</body></html>`);
  await page.screenshot({ path: file, omitBackground: !!transparent, clip: { x: 0, y: 0, width: w, height: h } });
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const d of dirs) {
    const dir = path.join(OUT, d.id); fs.mkdirSync(dir, { recursive: true });
    const L = d.light, D = d.dark;
    // 1. 圖形 深淺底 SVG＋1024 PNG
    for (const [v, c] of [['light', L], ['dark', D]]) {
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="1024" height="1024"><rect width="200" height="200" fill="${c.bg}"/><g transform="translate(14 14) scale(.86)">${d.mark(c)}</g></svg>`;
      fs.writeFileSync(path.join(dir, `mark_${v}.svg`), svg);
      await shot(page, svg, path.join(dir, `mark_${v}.png`), 1024, 1024);
    }
    // 2. 圓形大頭貼 110／40
    for (const [s, av, sfx] of (HANKO ? [[110, L, ''], [40, L, ''], [110, D, '_dark'], [40, D, '_dark']] : [[110, L, ''], [40, L, '']])) {
      const k = HANKO ? (s === 40 ? .78 : .74) : s === 40 ? (d.markSmall ? .8 : .84) : (d.markSmall ? .78 : .76);
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="${s}" height="${s}"><clipPath id="c"><circle cx="100" cy="100" r="100"/></clipPath><g clip-path="url(#c)"><rect width="200" height="200" fill="${av.bg}"/><g transform="translate(${100 - 100 * k} ${100 - 100 * k}) scale(${k})">${(d.markSmall || d.mark)(av)}</g></g></svg>`;
      fs.writeFileSync(path.join(dir, `avatar_${s}${sfx}.svg`), svg);
      await shot(page, svg, path.join(dir, `avatar_${s}${sfx}.png`), s, s, true);
    }
    // 3. 橫式完整版（深淺各一）＋ 4. 三個應用情境：在瀏覽器裡排版、量測、序列化
    await page.setViewportSize({ width: 2400, height: 1600 });
    await page.setContent(`<html><body style="margin:0"><script>${LIB}</script></body></html>`);
    const res = await page.evaluate(({ d, L, D, mk, mkD, mkS, mkSD, TAG, CJK, DARK_BG, HK }) => {
      const out = {};
      const newSvg = (w, h) => { document.body.innerHTML = ''; const s = el(document.body, 'svg', { xmlns: NS, viewBox: `0 0 ${w} ${h}`, width: w, height: h }); return s; };
      // 橫式
      for (const [v, c, inner] of [['light', L, mk], ['dark', D, mkD]]) {
        const H = 460, ms = 300, pad = 80, gap = 72;
        let s = newSvg(3000, H); const bg = el(s, 'rect', { width: 3000, height: H, fill: c.bg });
        mark(s, inner, pad, (H - ms) / 2, ms, 'mark');
        const tx = pad + ms + gap; const wsz = 124, tsz = 40;
        const wd = word(s, d.word, c, wsz, tx, 0); const wb = wd.g.getBBox();
        const tg = tag(s, c, tsz, tx, 0); const tb = tg.getBBox();
        const blockH = wb.height + 30 + tb.height; const top = (H - blockH) / 2;
        wd.g.setAttribute('transform', `translate(0 ${top - wb.y})`);
        tg.setAttribute('transform', `translate(${wb.x - tb.x + 4} ${top + wb.height + 30 - tb.y})`);
        const W = Math.ceil(tx + Math.max(wd.w, tb.width) + pad);
        s.setAttribute('viewBox', `0 0 ${W} ${H}`); s.setAttribute('width', W); bg.setAttribute('width', W);
        out['h_' + v] = { svg: s.outerHTML, w: W, h: H, m: measure(s, 6) };
      }
      // IG 個人頁
      {
        const W = 1080, H = 1320, c = L; const s = newSvg(W, H);
        el(s, 'rect', { width: W, height: H, fill: '#FFFFFF' });
        el(s, 'text', { x: 40, y: 86, 'font-family': 'Inter', 'font-weight': 700, 'font-size': 40, fill: '#111' }, 'caffaine.ai');
        el(s, 'path', { d: 'M290 70 l12 12 l12 -12', fill: 'none', stroke: '#111', 'stroke-width': 4, 'stroke-linecap': 'round' });
        const ag = el(s, 'g', { 'data-role': 'mark' });
        el(ag, 'circle', { cx: 160, cy: 270, r: 120, fill: c.bg, stroke: '#E6E0D8', 'stroke-width': 2 });
        const cl = el(s, 'clipPath', { id: 'av' }); el(cl, 'circle', { cx: 160, cy: 270, r: 120 });
        const inner = el(ag, 'g', { 'clip-path': 'url(#av)' }); mark(inner, mk, 160 - 120 * .76, 270 - 120 * .76, 240 * .76);
        [['86', '貼文'], ['1.2萬', '粉絲'], ['128', '追蹤中']].forEach(([n, t], i) => { const x = 450 + i * 210;
          el(s, 'text', { x, y: 262, 'text-anchor': 'middle', 'font-family': 'Inter', 'font-weight': 700, 'font-size': 44, fill: '#111' }, n);
          el(s, 'text', { x, y: 312, 'text-anchor': 'middle', 'font-family': CJK, 'font-size': 30, fill: '#333' }, t); });
        word(s, d.word, c, 56, 40, 500);
        el(s, 'text', { x: 40, y: 556, 'font-family': CJK, 'font-size': 28, fill: '#8A8A8A' }, '教育網站');
        tag(s, { ink: '#111' }, 32, 40, 620, 'start', [TAG, '上班族的 AI 技巧｜每天一則第一手新知']);
        [[40, '追蹤', c.accent, '#fff'], [380, '傳送訊息', '#EFEFEF', '#111'], [720, '電子郵件', '#EFEFEF', '#111']].forEach(([x, t, bgc, fc]) => {
          el(s, 'rect', { x, y: 730, width: 320, height: 72, rx: 16, fill: bgc });
          el(s, 'text', { x: x + 160, y: 777, 'text-anchor': 'middle', 'font-family': CJK, 'font-size': 30, fill: fc }, t); });
        for (let i = 0; i < 3; i++) { const x = i * 361, y = 846, w = 358, h = 448; const tc = (HK ? [c.bg, '#E6D6BF', '#2E2621'] : [c.bg, c.accent, '#2E2621'])[i];
          el(s, 'rect', { x, y, width: w, height: h, fill: tc });
          const fg = (i === 0 || (HK && i === 1)) ? c.ink : '#FFF8EE';
          const mg = el(s, 'g', { transform: `translate(${x + 22} ${y + 22}) scale(${56 / 200})` }); mg.innerHTML = i === 0 ? (mkS||mk) : (mkSD||mkD);
          ['3 個 AI 指令', '會議紀錄', '自己寫完'].forEach((t, k) => el(s, 'text', { x: x + 26, y: y + 210 + k * 58, 'font-family': CJK, 'font-size': 44, fill: fg }, [['3 個 AI 指令', '會議紀錄', '自己寫完'], ['Excel 公式', '交給 AI', '一句話生成'], ['本週 AI', '新知 5 則', '一次看懂']][i][k])); }
        out.ig = { svg: s.outerHTML, w: W, h: H, m: measure(s, 0) };
      }
      // 外帶杯杯身
      {
        const W = 1080, H = 1080, c = L; const s = newSvg(W, H);
        el(s, 'rect', { width: W, height: H, fill: c.bg });
        el(s, 'ellipse', { cx: 540, cy: 985, rx: 250, ry: 26, fill: '#000', opacity: .08 });
        const lx = y => 340 + (y - 210) * 60 / 760, rx = y => 740 - (y - 210) * 60 / 760;
        el(s, 'path', { d: `M${lx(210)} 210 L${lx(970)} 970 H${rx(970)} L${rx(210)} 210 Z`, fill: '#FFFDF8', stroke: '#E2D6C6', 'stroke-width': 3 });
        el(s, 'path', { d: `M${lx(690)} 690 L${lx(860)} 860 H${rx(860)} L${rx(690)} 690 Z`, fill: '#C9A27A' });
        el(s, 'rect', { x: 316, y: 168, width: 448, height: 52, rx: 18, fill: '#3A2E28' });
        el(s, 'path', { d: 'M372 168 Q378 120 430 120 H650 Q702 120 708 168 Z', fill: '#4A3D36' });
        mark(s, mk, 540 - 125, 262, 250, 'mark');
        const wd = word(s, d.word, c, 58, 0, 0); const wb = wd.g.getBBox();
        wd.g.setAttribute('transform', `translate(${540 - wd.w / 2} ${262 + 250 + 34 - wb.y})`);
        const tg = tag(s, { ink: '#3A2A21' }, 32, 540, 0, 'middle', ['一杯咖啡的時間，', '看懂一個 AI 新知']); const tb = tg.getBBox();
        tg.setAttribute('transform', `translate(0 ${775 - (tb.y + tb.height / 2)})`);
        out.cup = { svg: s.outerHTML, w: W, h: H, m: measure(s, 6) };
      }
      // 1080×1350 貼文封面（左上角落識別）
      {
        const W = 1080, H = 1350, c = L; const s = newSvg(W, H);
        el(s, 'rect', { width: W, height: H, fill: c.bg });
        el(s, 'rect', { x: 48, y: 48, width: 0, height: 128, rx: 64, fill: '#FFFFFF', opacity: .75, id: 'badge' });
        mark(s, mk, 64, 56, 112, 'mark');
        const wd = word(s, d.word, c, 46, 0, 0); const wb = wd.g.getBBox();
        wd.g.setAttribute('transform', `translate(${64 + 112 + 28} ${112 - (wb.y + wb.height / 2)})`);
        s.querySelector('#badge').setAttribute('width', 64 + 112 + 28 + wd.w + 40 - 48);
        const hg = el(s, 'g', { 'data-role': 'headline' });
        el(hg, 'text', { x: 72, y: 470, 'font-family': CJK, 'font-size': 40, fill: c.accent }, '上班族 AI 技巧 #07');
        ['3 個 AI 指令', '讓會議紀錄', '自己寫完'].forEach((t, k) => el(hg, 'text', { x: 68, y: 600 + k * 132, 'font-family': CJK, 'font-size': 112, fill: c.ink }, t));
        el(hg, 'text', { x: 72, y: 950, 'font-family': CJK, 'font-size': 38, fill: c.ink, opacity: .7 }, '複製貼上就能用，附完整提示詞 →');
        el(s, 'rect', { x: 72, y: 1150, width: 936, height: 2, fill: c.ink, opacity: .2 });
        tag(s, c, 32, 72, 1236);
        el(s, 'text', { x: 1008, y: 1236, 'text-anchor': 'end', 'font-family': 'Inter', 'font-weight': 600, 'font-size': 30, fill: c.ink, opacity: .6 }, '@caffaine.ai');
        out.cover = { svg: s.outerHTML, w: W, h: H, m: measure(s, 4) };
      }
      return out;
    }, { d: { word: d.word }, L, D, mk: d.mark(L), mkD: d.mark(D), mkS: d.markSmall ? d.markSmall(L) : null, mkSD: d.markSmall ? d.markSmall(D) : null, TAG, CJK, DARK_BG, HK: HANKO });
    const files = { h_light: 'horizontal_light', h_dark: 'horizontal_dark', ig: 'mock_ig_profile', cup: 'mock_takeaway_cup', cover: 'mock_post_cover' };
    if (HANKO) delete files.cover;
    for (const k in files) {
      const r = res[k]; fs.writeFileSync(path.join(dir, files[k] + '.svg'), r.svg);
      await shot(page, r.svg, path.join(dir, files[k] + '.png'), r.w, r.h);
      const minGap = Math.min(...r.m.pairs.map(p => p.gap));
      report.push({ dir: d.id, file: files[k] + '.png', minGap, overlaps: r.m.pairs.filter(p => p.overlap).length, below24: r.m.pairs.filter(p => p.gap < 24).map(p => p.pair + ' ' + p.gap), outOfCanvas: r.m.outOfCanvas, pairs: r.m.pairs });
    }
    console.log(d.id, 'ok');
  }
  fs.mkdirSync(OUT,{recursive:true});fs.writeFileSync(path.join(OUT, 'overlap_report.json'), JSON.stringify(report, null, 1));
  const bad = report.filter(r => r.minGap < 24 || r.overlaps || r.outOfCanvas.length);
  console.log('量測張數', report.length, '不合格', bad.length); bad.forEach(b => console.log(JSON.stringify(b)));
  report.forEach(r => console.log(r.dir, r.file, '最小間距', r.minGap));
  await browser.close();
})();
