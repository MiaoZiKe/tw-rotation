// v8.2（CEO／美術 11-16：孤字、行首標點、關鍵詞拆行、字級 ≥64px）：字幕排版統一在這裡——
//   旁白依標點切成片語 → 每行 ≤13 字（64px 放得下）→ 每兩行一個畫面；一鏡裡有好幾個畫面時，依字數比例跟著旁白時間換。
//   標點只會在行尾；超過 13 字的單一片語才在中間切（不切數字念法）；單行 ≤11 字用 76px。
function capLines(c){const ps=c.replace(/。$/,'').match(/[^，。、；：？！]+[，。、；：？！]?/g)||[];const L=[];
 const NUM=/[零〇一二兩三四五六七八九十百千萬點]/;
 ps.forEach(p0=>{let p=p0;while(p.length>13){let k=13;while(k>6&&NUM.test(p[k-1])&&NUM.test(p[k]))k--;L.push({t:p.slice(0,k),glue:true});p=p.slice(k)}L.push({t:p})});
 const lines=[];L.forEach(x=>{const last=lines[lines.length-1];if(last&&!last.full&&(last.t+x.t).length<=13&&!x.glue)last.t+=x.t;else lines.push({t:x.t});if(x.glue)lines[lines.length-1].full=true});
 return lines.map(x=>x.t)}
function capChunks(c){const L=capLines(c),ch=[];for(let i=0;i<L.length;i+=2){let a=L.slice(i,i+2);ch.push(a)}
 if(ch.length>1&&ch[ch.length-1].length===1&&ch[ch.length-1][0].replace(/[，。、；：？！]/g,'').length<=2&&ch[ch.length-2].length===2){}   // 單獨一行的短句自成一個畫面（單行不算孤字）
 return ch}
function capAt(sc,l){const c=sc.cap||'';if(!c)return '';const ch=capChunks(c);if(ch.length===1)return ch[0].join('\n');
 const n=x=>x.join('').replace(/[，。、；：？！「」（）\s]/g,'').length,a=sc.voiceAt!=null?sc.voiceAt:.25,b=Math.max(a+.5,(sc.t1-sc.t0)-.15),tot=ch.reduce((s,x)=>s+n(x),0);let acc=0;
 for(let i=0;i<ch.length;i++){acc+=n(ch[i]);if(l<a+(b-a)*acc/tot||i===ch.length-1)return ch[i].join('\n')}return ''}
function capV8(s,op,dy){if(!s||op<=0)return'';const ls=s.split('\n').map(x=>x.replace(/[。；]$/,'')),one=ls.length===1&&ls[0].length<=11,fs=one?76:64,lh=Math.round(fs*1.28),h=ls.length*lh,top=1690-h;
 return `<div data-o="cap" class="abs cap" style="top:${top}px;font-size:${fs}px;line-height:${lh}px;opacity:${op.toFixed(3)};transform:translateY(${dy.toFixed(1)}px)">${ls.map(esc).join('<br>')}</div>`}
window.renderAt=function(t){const S=V.scenes;let i=S.length-1;for(let j=0;j<S.length;j++){if(t>=S[j].t0&&t<S[j].t1){i=j;break}}
 const s=S[i],lt=t-s.t0,d=s.t1-s.t0,fr=Math.floor(lt*30+1e-6),W=1080;let html=bg(t);
 const layer=(sc,tt,tin)=>{const l=tt-sc.t0,dd=sc.t1-sc.t0;_LT=l;_BEATS=sc.beats||null;let h=SC[sc.type](sc,l,dd,{});
  if(sc.type!=='outro'){const k=tin==null?1:EO((l-tin)/.12);/* v7：有旁白，字幕在開口前 0.25 秒內就要進好 */h+=capV8(capAt(sc,l),k,(1-k)*18)}
  if(sc.type!=='outro')h+=srcHTML(sc.src,tin==null?1:EO((l-tin+.04)/.2));return h};
 const edge=x=>`<div class="abs" style="left:${(x-12).toFixed(0)}px;top:0;width:24px;height:1920px;background:rgba(217,130,43,.6)"></div>`;
 if(i>0&&fr<TRF){const o=S[i-1];
  if(fr<=1){const e=(fr+1)/3;html+=`<div class="abs layer" data-L="old" data-clip="${(W*e).toFixed(0)},${W}" style="clip-path:inset(0 0 0 ${(W*e).toFixed(0)}px)">${strip(layer(o,t))}</div>${edge(W*e)}`}
  else if(fr===2){html+=edge(W-12)}
  else{const e=(fr-2)/3;html+=`<div class="abs layer" data-L="new" data-clip="0,${(W*e).toFixed(0)}" style="clip-path:inset(0 ${(W*(1-e)).toFixed(0)}px 0 0)">${layer(s,t,TRF/30)}</div>${edge(W*e)}`}
 }else html+=`<div class="abs layer">${layer(s,t,i>0?TRF/30:null)}</div>`;
 html+=`<div data-o="foot" class="abs foot"></div>`+(V.asof?`<div data-o="asof" class="abs asof">截至 ${esc(V.asof)}</div>`:'');
 document.getElementById('stage').innerHTML=html};
// 音效事件（render_video.js 讀取後交給 sfx_v3.py 合成）：每個事件的時間與畫面動作讀同一份 TM／OF，所以聲音與動作落在同一幀
