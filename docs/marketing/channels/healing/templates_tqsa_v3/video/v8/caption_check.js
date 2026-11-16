// 字幕逐句檢查（CEO 11-16）：每鏡每 0.1 秒讀一次字幕，列出所有出現過的字幕畫面，檢查四項：孤字（多行時某行 ≤2 字）、行首標點、關鍵詞被拆行、字級 <64px
// 用法：node v8/caption_check.js <名>  → stdout JSON
const {chromium}=require('/opt/node-tools/node_modules/playwright');const path=require('path');
const name=process.argv[2];
const KW=['全職','兼職','中位數','寬限期','百分點','最低工資','經常性薪資','加班費','房貸','負擔能力','首購族','費率','平衡費率','初婚','年齡','行政院','勞動部','主計總處','內政部','臺銀','教育部','工作天','年總工時','時薪','月薪','精算','撥補','第一份','學貸','舊貸','二〇二七','二〇三一','二零二五','二零二三'];
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+path.join(__dirname,'..','html',name+'.html'));await pg.waitForTimeout(400);
 const V=await pg.evaluate(()=>V);const seen={};const bad=[];
 const numRe=/[零〇一二兩三四五六七八九十百千萬點]{2,}/g;
 for(const s of V.scenes){if(s.type==='outro')continue;for(let t=s.t0+.2;t<s.t1-.05;t+=.1){await pg.evaluate(t=>window.renderAt(t),t);
  const c=await pg.evaluate(()=>{const e=[...document.querySelectorAll('#stage [data-o=cap]')].pop();if(!e||parseFloat(getComputedStyle(e).opacity)<.9)return null;return {fs:parseFloat(getComputedStyle(e).fontSize),lines:e.innerHTML.split('<br>').map(x=>x.replace(/&amp;/g,'&'))}});
  if(!c)continue;const key=c.lines.join('|');if(seen[key])continue;seen[key]=1;
  const issues=[];const L=c.lines;
  if(L.length>1)L.forEach(l=>{if(l.replace(/[，。、；：？！「」]/g,'').length<=2)issues.push('孤字「'+l+'」')});
  L.forEach((l,i)=>{if(i>0&&/^[，。、；：？！」）]/.test(l))issues.push('行首標點「'+l[0]+'」')});
  const kws=KW.concat((s.cap.match(numRe)||[]));for(let i=0;i<L.length-1;i++){const a=L[i],bb=L[i+1];kws.forEach(k=>{for(let j=1;j<k.length;j++){if(a.endsWith(k.slice(0,j))&&bb.startsWith(k.slice(j)))issues.push('關鍵詞拆行「'+k+'」')}})}
  if(c.fs<63.5)issues.push('字級 '+c.fs+'px');
  const row={id:s.id,t:+t.toFixed(2),fs:c.fs,lines:L,issues:[...new Set(issues)]};if(row.issues.length)bad.push(row);(seen.rows=seen.rows||[]).push(row)}}
 console.log(JSON.stringify({captions:seen.rows,bad},null,0));await b.close()})();
