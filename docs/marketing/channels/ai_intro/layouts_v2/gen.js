// 頻道③ 版型 v2：4 套方向 × 4 張，同一組內容。執行：node gen.js → 產 html/
const fs=require('fs');
const FONT="'Noto Sans TC','WenQuanYi Zen Hei','文泉驛正黑',sans-serif";
const logo=(s,a,b,cut)=>`<svg width="${s}" height="${s}" viewBox="60 100 390 310" style="display:block"><rect x="84" y="120" width="166" height="190" rx="36" fill="${a}"/><rect x="262" y="202" width="166" height="190" rx="36" fill="${b}"/><path d="M130 232L160 262L215 187" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M305 257L385 337M385 257L305 337" stroke="${cut}" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`;
const BASE=`*{box-sizing:border-box;margin:0;padding:0}html,body{width:1080px;height:1350px;overflow:hidden}body{position:relative;font-family:${FONT}}`;
const doc=(css,body)=>`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><style>${BASE}${css}</style><body>${body}</body></html>`;
const rows=[['微軟 6 萬人','01'],['紐約新法','02'],['Claude Duet','03']];
const TXT={
 what:'微軟向約 6 萬名員工提出自願離職方案，範圍在美國、加拿大、印度、英國，部分團隊不在內。',
 say:'公司說是為員工增加彈性。媒體把它和 AI 投資成本連在一起，這是媒體的解讀，不是公司原話。',
 diff:'看到「AI 導致裁員」的標題時，先分清「公司說的原因」和「媒體猜的原因」。',
 ph1:'ChatGPT 對「分帳」題的完整回答畫面，需看得到提問與互動元件',
 ph2:'要遮：聊天紀錄、帳號名稱、分頁列',
 key:'這題 2 次裡有【__】次出現互動元件；金額與 Excel 差【__】元。',
 cond:'測試條件：【待填】日期、方案、網頁或手機'};
const TBL=[['題目','我問什麼','怎麼驗','要記什麼'],['分帳','4 人聚餐分帳','Excel 自算','差幾元'],['比較','三個手機方案','逐格對數字','有無互動元件'],['試算','房貸月付','Excel PMT','差幾元'],['流程','請假流程圖','查有無漏步','能不能點'],['純知識','特休怎麼算','看有沒有硬塞','有無引條文']];
const tbl=(cls,w)=>`<table class="${cls}"><colgroup>${w.map(x=>`<col style="width:${x}px">`).join('')}</colgroup>${TBL.map((r,i)=>`<tr>${r.map(c=>i?`<td>${c}</td>`:`<th>${c}</th>`).join('')}</tr>`).join('')}</table>`;
const camera=(c,s)=>`<svg width="${s}" height="${s}" viewBox="0 0 64 64" fill="none" stroke="${c}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"><rect x="6" y="14" width="52" height="38" rx="8"/><circle cx="32" cy="33" r="10"/><path d="M22 14l4-6h12l4 6"/></svg>`;
const out={};

/* ========== T1 檔案櫃（亮｜左側深色書脊＋白卡列） ========== */
{const ink='#12213A',g='#137A52';
const css=out.T1css=`body{background:#E9EEF4;color:${ink}}
.rail{position:absolute;left:0;top:0;bottom:0;width:112px;background:${ink}}
.rl{position:absolute;left:24px;top:72px}
.rv{position:absolute;left:30px;top:170px;writing-mode:vertical-rl;font-size:34px;font-weight:800;color:#fff;letter-spacing:6px;height:900px;white-space:nowrap}
.rp{position:absolute;left:14px;width:84px;bottom:72px;text-align:center;font-size:30px;font-weight:700;color:#B9C6DA;height:48px;line-height:48px}
.main{position:absolute;left:152px;right:64px;top:72px;bottom:144px;display:flex;flex-direction:column;gap:28px}
.chip{align-self:flex-start;border:3px solid ${g};color:${g};border-radius:14px;padding:6px 22px;font-size:32px;font-weight:800;background:#fff}
.t{font-weight:900;line-height:1.14}.t mark{background:linear-gradient(transparent 55%,#FFD166 55%);color:inherit}
.disc{position:absolute;left:152px;right:64px;bottom:72px;height:48px;border-top:3px solid #B8C4D4;padding-top:6px;display:flex;justify-content:space-between;font-size:28px;font-weight:500;color:#33445F;line-height:40px}
.disc b{font-weight:800;color:${ink}}
.row{flex:1;background:#fff;border:3px solid #C3CEDD;border-radius:22px;display:flex;align-items:center;gap:26px;padding:0 28px}
.num{width:92px;height:92px;border-radius:18px;background:${g};color:#fff;font-size:44px;font-weight:900;display:flex;align-items:center;justify-content:center;flex:none}
.rn{font-size:46px;font-weight:800;flex:1}.rs{font-size:28px;font-weight:700;color:#3B4A63;background:#EEF2F7;border-radius:12px;padding:8px 16px;white-space:nowrap}
.meta{display:flex;gap:16px}.mb{flex:1;background:#fff;border:3px solid #C3CEDD;border-radius:18px;padding:10px 20px}.mb i{display:block;font-style:normal;font-size:28px;color:#4A5B76;font-weight:600}.mb b{font-size:36px;font-weight:800}
.blk{flex:1;background:#fff;border:3px solid #C3CEDD;border-radius:20px;border-left:18px solid var(--c);padding:18px 28px}
.blk h3{font-size:32px;font-weight:800;color:var(--c2);margin-bottom:6px}.blk p{font-size:34px;font-weight:500;line-height:1.5}
.badge{align-self:flex-start;border:3px solid ${g};color:${g};background:#fff;border-radius:999px;padding:6px 26px;font-size:28px;font-weight:800}
table{width:100%;border-collapse:collapse;background:#fff;table-layout:fixed;height:100%}th{background:${ink};color:#fff;font-size:30px;font-weight:800;text-align:left;padding:0 20px;height:84px}td{font-size:30px;font-weight:600;padding:0 20px;border-bottom:3px solid #DCE3EC}td:first-child{font-weight:900}tr:nth-child(even) td{background:#F3F6FA}
.tw{flex:1;border:3px solid #C3CEDD;border-radius:20px;overflow:hidden}
.ph{flex:1;border:7px dashed #E39A00;border-radius:24px;background:#FFF6DD;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:0 36px}
.ph b{font-size:60px;font-weight:900}.ph p{font-size:32px;font-weight:600;line-height:1.45}`;
const rail=(lab,pg)=>`<div class="rail"></div><div class="rl" data-o="LOGO">${logo(64,'#6FD8A0','#FFC857',ink)}</div><div class="rv" data-o="系列標">${lab}</div><div class="rp" data-o="頁碼">${pg}</div>`;
const disc=(l)=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
out.T1=[
`${rail('AI 實測｜本週 AI 三則','1/6')}<div class="main"><div class="chip" data-o="日期">2026/10/28 ~ 11/03</div><div class="t" data-o="標題" style="font-size:108px">三則 <mark>AI 新聞</mark>，<br>只講跟你上班<br>有關的</div><div data-o="副標" style="font-size:44px;font-weight:600;color:#3B4A63">每則附來源、日期、可信度</div>${rows.map((r,i)=>`<div class="row" data-o="列${i}"><div class="num">${r[1]}</div><div class="rn">${r[0]}</div><div class="rs">來源 2｜信心 中</div></div>`).join('')}</div>${disc('自製圖文')}`,
`${rail('AI 實測｜本週 AI 三則','2/6')}<div class="main"><div class="chip" data-o="序">新聞 1／3</div><div class="t" data-o="標題" style="font-size:58px">微軟提出約 6 萬人<br>自願離職方案</div><div class="meta" data-o="資訊列"><div class="mb"><i>事件日</i><b>10/26 美東</b></div><div class="mb"><i>查證日</i><b>11/03</b></div><div class="mb"><i>信心度</i><b>中</b></div></div><div class="blk" data-o="發生什麼" style="--c:#137A52;--c2:#137A52"><h3>發生什麼</h3><p>${TXT.what}</p></div><div class="blk" data-o="怎麼說" style="--c:#E39A00;--c2:#8A5A00"><h3>微軟怎麼說</h3><p>${TXT.say}</p></div><div class="blk" data-o="差在哪" style="--c:${ink};--c2:${ink}"><h3>對上班族差在哪</h3><p>${TXT.diff}</p></div><div class="badge" data-o="標章">整理自新聞｜我沒親自測</div></div>${disc('自製圖文')}`,
`${rail('AI 實測 第 01 期','3/7')}<div class="main"><div class="chip" data-o="序">測試方法</div><div class="t" data-o="標題" style="font-size:58px">我怎麼測：5 種題目 × 2 次</div><div class="tw" data-o="表">${tbl('',[150,240,230,244])}</div><div data-o="條件" style="font-size:32px;font-weight:600">${TXT.cond}</div><div class="badge" data-o="標章">自製表格｜非 AI 生成</div></div>${disc('自製圖文')}`,
`${rail('AI 實測 第 01 期','4/7')}<div class="main"><div class="chip" data-o="序">步驟 1</div><div class="t" data-o="標題" style="font-size:58px">它真的變出計算器了</div><div class="ph" data-o="截圖框">${camera('#B27300',96)}<b>待 Andy 截圖</b><p>${TXT.ph1}</p><p style="font-size:30px;color:#6B4A00">${TXT.ph2}</p></div><div data-o="重點" style="font-size:34px;font-weight:600;line-height:1.45"><span style="color:${g};font-weight:800">重點：</span>${TXT.key}</div><div class="badge" data-o="標章">截圖為實測｜非 AI 生成</div></div>${disc('截圖已遮個資')}`];
}

/* ========== T2 實驗筆記本（亮｜橫線紙＋打孔＋便利貼） ========== */
{const ink='#1B2A41',g='#137A52';
const css=out.T2css=`body{background-color:#FCFDFF;background-image:repeating-linear-gradient(to bottom,transparent 0,transparent 58px,#DCE8F4 58px,#DCE8F4 60px);color:${ink}}
.mg{position:absolute;left:150px;top:0;bottom:0;width:3px;background:#8FD9BA}
.hole{position:absolute;left:52px;width:44px;height:44px;border-radius:50%;background:#C9D5E3;box-shadow:inset 0 3px 6px rgba(0,0,0,.18)}
.main{position:absolute;left:184px;right:64px;top:72px;bottom:144px;display:flex;flex-direction:column;gap:26px}
.disc{position:absolute;left:184px;right:64px;bottom:72px;height:48px;border-top:3px dashed #9FB3C9;padding-top:6px;display:flex;justify-content:space-between;font-size:28px;font-weight:500;color:#33445F;line-height:40px;background:#FCFDFF}.disc b{font-weight:800;color:${ink}}
.top{display:flex;justify-content:space-between;align-items:center;gap:24px}
.ser{display:flex;gap:16px;align-items:center;font-size:34px;font-weight:800}
.tag{border:3px dashed #7A8DA6;border-radius:10px;padding:4px 20px;font-size:30px;font-weight:700;background:#fff}
.t{font-weight:900;line-height:1.14}.t mark{background:linear-gradient(transparent 50%,#B8F0D2 50%);color:inherit;padding:0 4px}
.note{background:#FFE08A;border-radius:6px;padding:22px 28px;box-shadow:6px 8px 0 rgba(27,42,65,.16);font-weight:800}
.ck{flex:1;display:flex;align-items:center;gap:26px;border-bottom:3px dashed #9FB3C9}
.box{width:64px;height:64px;border:5px solid ${ink};border-radius:12px;display:flex;align-items:center;justify-content:center;background:#fff;flex:none}
.ck b{font-size:46px;font-weight:900;flex:1}.ck span{font-size:28px;font-weight:700;color:#3B4A63}
.badge{align-self:flex-start;border:3px solid ${g};color:${g};background:#fff;border-radius:10px;padding:6px 24px;font-size:28px;font-weight:800}
.sec{background:#fff;border:3px solid #C4D3E3;border-radius:10px;padding:18px 26px;flex:1}.sec h3{font-size:34px;font-weight:900;display:inline;background:linear-gradient(transparent 55%,#B8F0D2 55%);padding:0 4px}.sec p{font-size:34px;font-weight:500;line-height:1.5;margin-top:8px}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}th{font-size:32px;font-weight:900;text-align:left;padding:0 18px;height:88px;background:linear-gradient(transparent 55%,#B8F0D2 55%);background-clip:padding-box}td{font-size:32px;font-weight:600;padding:0 18px;border-top:3px dashed #9FB3C9}td:first-child{font-weight:900}
.tw{flex:1;background:#fff;border:3px solid #C4D3E3;border-radius:10px;overflow:hidden;box-shadow:6px 8px 0 rgba(27,42,65,.1)}
.pol{flex:1;background:#fff;border:3px solid #C4D3E3;border-radius:10px;padding:26px 26px 26px;box-shadow:6px 8px 0 rgba(27,42,65,.14);display:flex}
.ph{flex:1;border:7px dashed #E39A00;border-radius:12px;background:#FFF6DD;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:0 30px}
.ph b{font-size:60px;font-weight:900}.ph p{font-size:32px;font-weight:600;line-height:1.45}`;
const deco=`<div class="mg"></div><div class="hole" style="top:200px"></div><div class="hole" style="top:640px"></div><div class="hole" style="top:1080px"></div>`;
const disc=(l)=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
const chk=`<svg width="40" height="40" viewBox="0 0 40 40"><path d="M6 21L16 31L34 9" stroke="${g}" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const top=(l,r)=>`<div class="top"><div class="ser" data-o="系列標">${logo(54,'#1E9E6A','#E39A00','#FCFDFF')}<span>${l}</span></div><div class="tag" data-o="右標">${r}</div></div>`;
out.T2=[
`${deco}<div class="main">${top('本週 AI 三則','10/28 ~ 11/03')}<div class="t" data-o="標題" style="font-size:104px">三則 <mark>AI 新聞</mark>，<br>只講跟你上班<br>有關的</div><div class="note" data-o="副標" style="font-size:44px">每則附來源、日期、可信度</div>${rows.map((r,i)=>`<div class="ck" data-o="清單${i}"><div class="box">${chk}</div><b>${r[0]}</b><span>來源 2｜信心 中</span></div>`).join('')}</div>${disc('自製圖文')}`,
`${deco}<div class="main">${top('本週 AI 三則','2/6')}<div class="tag" data-o="序" style="align-self:flex-start;font-size:32px">新聞 1／3　事件日 10/26　查證日 11/03　信心：中</div><div class="t" data-o="標題" style="font-size:58px">微軟提出約 6 萬人<br>自願離職方案</div><div class="sec" data-o="發生什麼"><h3>發生什麼</h3><p>${TXT.what}</p></div><div class="sec" data-o="怎麼說"><h3>微軟怎麼說</h3><p>${TXT.say}</p></div><div class="note" data-o="差在哪" style="flex:1"><div style="font-size:34px;font-weight:900">對上班族差在哪</div><div style="font-size:34px;font-weight:600;line-height:1.5;margin-top:6px">${TXT.diff}</div></div><div class="badge" data-o="標章">整理自新聞｜我沒親自測</div></div>${disc('自製圖文')}`,
`${deco}<div class="main">${top('AI 實測 第 01 期','3/7')}<div class="t" data-o="標題" style="font-size:58px">我怎麼測：<mark>5 種題目</mark> × 2 次</div><div class="tw" data-o="表">${tbl('',[140,230,230,260])}</div><div data-o="條件" style="font-size:32px;font-weight:600">${TXT.cond}</div><div class="badge" data-o="標章">自製表格｜非 AI 生成</div></div>${disc('自製圖文')}`,
`${deco}<div class="main">${top('AI 實測 第 01 期','4/7')}<div class="t" data-o="標題" style="font-size:58px"><mark>步驟 1</mark>　它真的變出計算器了</div><div class="pol" data-o="截圖框"><div class="ph">${camera('#B27300',96)}<b>待 Andy 截圖</b><p>${TXT.ph1}</p><p style="font-size:30px;color:#6B4A00">${TXT.ph2}</p></div></div><div class="note" data-o="重點" style="font-size:34px;line-height:1.45">重點：${TXT.key}</div><div class="badge" data-o="標章">截圖為實測｜非 AI 生成</div></div>${disc('截圖已遮個資')}`];
}

/* ========== T3 對話串（深｜聊天氣泡＋輸入列） ========== */
{const bg='#15161C',pan='#262833',g='#6FD8A0',am='#FFC857';
const css=out.T3css=`body{background:${bg};color:#F2F4F8}
.main{position:absolute;left:64px;right:64px;top:72px;bottom:156px;display:flex;flex-direction:column;gap:24px}
.bar{display:flex;align-items:center;gap:20px;background:#1F2129;border-radius:30px;padding:14px 28px}.bar b{font-size:36px;font-weight:800;flex:1}.bar span{font-size:28px;color:#B7BDCB;font-weight:600}.dot{display:inline-block;width:16px;height:16px;border-radius:50%;background:${g};margin-right:10px}
.u{align-self:flex-end;max-width:900px;background:${g};color:#0B1A12;border-radius:40px 40px 8px 40px;padding:26px 36px;font-weight:900;line-height:1.18}
.a{align-self:flex-start;max-width:930px;background:${pan};border-radius:40px 40px 40px 8px;padding:20px 32px}
.disc{position:absolute;left:64px;right:64px;bottom:72px;height:60px;background:#1F2129;border:3px solid #3A3D4D;border-radius:30px;padding:0 30px;display:flex;justify-content:space-between;align-items:center;font-size:28px;font-weight:500;color:#C4CAD8}.disc b{font-weight:800;color:#fff}
.qr{display:flex;gap:16px;align-items:center;background:#1F2129;border:3px solid #3A3D4D;border-radius:26px;padding:0 24px;flex:1}.qr i{font-style:normal;width:64px;height:64px;border-radius:50%;background:${am};color:#241800;font-size:34px;font-weight:900;display:flex;align-items:center;justify-content:center;flex:none}.qr b{font-size:44px;font-weight:800;flex:1}.qr span{font-size:28px;font-weight:700;color:${g}}
.chip{background:#343746;border-radius:16px;padding:6px 18px;font-size:30px;font-weight:700;display:inline-block;margin:0 10px 8px 0}
.a h3{font-size:32px;font-weight:900;color:${g};margin-bottom:2px}.a p{font-size:33px;font-weight:500;line-height:1.45}
.badge{align-self:flex-start;border:3px solid ${g};color:${g};border-radius:999px;padding:6px 26px;font-size:28px;font-weight:800}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}th{font-size:30px;font-weight:800;color:${g};text-align:left;padding:0 14px;height:80px;border-bottom:3px solid #4A4E62}td{font-size:31px;font-weight:600;padding:0 14px;border-bottom:2px solid #3A3D4D}td:first-child{font-weight:900;color:${am}}
.ph{flex:1;border:7px dashed ${am};border-radius:28px;background:#2A2618;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;text-align:center;padding:0 24px}
.ph b{font-size:58px;font-weight:900;color:${am}}.ph p{font-size:32px;font-weight:600;line-height:1.45}`;
const bar=(l,r)=>`<div class="bar" data-o="頂欄">${logo(60,g,am,'#1F2129')}<b>${l}</b><span><i class="dot"></i>${r}</span></div>`;
const disc=(l)=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
out.T3=[
`<div class="main">${bar('本週 AI 三則','10/28 ~ 11/03')}<div class="u" data-o="標題" style="font-size:76px">三則 AI 新聞，只講跟你上班有關的</div><div class="a" data-o="副標" style="font-size:44px;font-weight:600;padding:22px 34px">每則附來源、日期、可信度，整理好了：</div>${rows.map((r,i)=>`<div class="qr" data-o="快速${i}"><i>${i+1}</i><b>${r[0]}</b><span>來源 2｜信心 中</span></div>`).join('')}</div>${disc('自製圖文')}`,
`<div class="main">${bar('本週 AI 三則','2/6')}<div class="u" data-o="標題" style="font-size:50px;padding:20px 32px">新聞 1／3　微軟提出約 6 萬人自願離職方案</div><div class="a" data-o="資訊" style="padding-bottom:20px"><span class="chip">事件日 10/26 美東</span><span class="chip">查證日 11/03</span><span class="chip">信心度 中</span></div><div class="a" data-o="發生什麼" style="flex:1"><h3>發生什麼</h3><p>${TXT.what}</p></div><div class="a" data-o="怎麼說" style="flex:1"><h3>微軟怎麼說</h3><p>${TXT.say}</p></div><div class="a" data-o="差在哪" style="flex:1;border:3px solid ${am}"><h3 style="color:${am}">對上班族差在哪</h3><p>${TXT.diff}</p></div><div class="badge" data-o="標章">整理自新聞｜我沒親自測</div></div>${disc('自製圖文')}`,
`<div class="main">${bar('AI 實測 第 01 期','3/7')}<div class="u" data-o="標題" style="font-size:56px">我怎麼測：5 種題目 × 2 次</div><div class="a" data-o="表" style="flex:1;padding:12px 24px;width:100%;max-width:none">${tbl('',[130,262,262,226])}</div><div class="a" data-o="條件" style="font-size:32px;font-weight:600;padding:18px 30px">${TXT.cond}</div><div class="badge" data-o="標章">自製表格｜非 AI 生成</div></div>${disc('自製圖文')}`,
`<div class="main">${bar('AI 實測 第 01 期','4/7')}<div class="u" data-o="標題" style="font-size:56px">步驟 1　它真的變出計算器了</div><div class="a" data-o="截圖框" style="flex:1;display:flex;width:100%;max-width:none;padding:22px"><div class="ph">${camera(am,96)}<b>待 Andy 截圖</b><p>${TXT.ph1}</p><p style="font-size:30px;color:#D9C48A">${TXT.ph2}</p></div></div><div class="a" data-o="重點" style="font-size:34px;line-height:1.45;padding:20px 30px"><span style="color:${g};font-weight:800">重點：</span>${TXT.key}</div><div class="badge" data-o="標章">截圖為實測｜非 AI 生成</div></div>${disc('截圖已遮個資')}`];
}

/* ========== T4 色塊海報（亮｜滿版綠色塊＋粗黑框硬陰影） ========== */
{const ink='#0E1A14',gb='#0F7A55',am='#FFC857';
const css=out.T4css=`body{background:#F5F7F2;color:${ink}}
.blk0{position:absolute;left:0;right:0;top:0;background:${gb};color:#fff;padding:72px 64px 40px;display:flex;flex-direction:column;gap:24px;border-bottom:6px solid ${ink}}
.main{position:absolute;left:64px;right:64px;bottom:144px;display:flex;flex-direction:column;gap:26px}
.disc{position:absolute;left:64px;right:64px;bottom:72px;height:48px;border-top:5px solid ${ink};padding-top:6px;display:flex;justify-content:space-between;font-size:28px;font-weight:500;line-height:36px}.disc b{font-weight:900}
.srow{display:flex;justify-content:space-between;align-items:center;gap:24px}.ser{display:flex;gap:16px;align-items:center;font-size:36px;font-weight:900}
.pill{background:${am};color:${ink};border:4px solid ${ink};border-radius:12px;padding:4px 20px;font-size:30px;font-weight:900}
.t{font-weight:900;line-height:1.12}
.card{border:5px solid ${ink};border-radius:14px;box-shadow:8px 8px 0 ${ink};background:#fff;padding:22px 24px}
.badge{align-self:flex-start;border:4px solid ${ink};background:${am};border-radius:12px;padding:4px 24px;font-size:28px;font-weight:900}
.g3{display:flex;gap:24px;flex:1}.g3 .card{flex:1;display:flex;flex-direction:column;justify-content:space-between}.g3 b.n{font-size:150px;line-height:1;font-weight:900}.g3 .nm{font-size:44px;font-weight:900;line-height:1.2}.g3 .sm{font-size:28px;font-weight:700}
.g2{display:flex;gap:24px;flex:1}.g2 .card{flex:1}.card h3{font-size:34px;font-weight:900;margin-bottom:8px;background:${am};display:inline-block;padding:0 10px;border:3px solid ${ink}}.card p{font-size:33px;font-weight:600;line-height:1.5}
table{width:100%;border-collapse:collapse;table-layout:fixed;height:100%}th{background:${ink};color:${am};font-size:32px;font-weight:900;text-align:left;padding:0 18px;height:88px}td{font-size:32px;font-weight:700;padding:0 18px;border-bottom:4px solid ${ink}}td:first-child{background:${am};font-weight:900}
.tw{flex:1;border:5px solid ${ink};border-radius:14px;box-shadow:8px 8px 0 ${ink};overflow:hidden;background:#fff}
.ph{flex:1;border:8px dashed #E39A00;border-radius:14px;background:#FFF1C9;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:0 36px}
.ph b{font-size:62px;font-weight:900}.ph p{font-size:32px;font-weight:700;line-height:1.45}`;
const disc=(l)=>`<div class="disc" data-o="揭露列"><span><b>無業配</b>｜${l}</span><span>圖文含 AI 協助</span></div>`;
const hdr=(l,r)=>`<div class="srow"><div class="ser" data-in="色塊" data-o="系列標">${logo(58,'#fff',am,gb)}<span>${l}</span></div><div class="pill" data-in="色塊" data-o="右標">${r}</div></div>`;
const mainH=(h)=>`style="top:${h+30}px"`;
out.T4=[
`<div class="blk0" data-o="色塊" style="height:640px">${hdr('本週 AI 三則','10/28 ~ 11/03')}<div class="t" data-in="色塊" data-o="標題" style="font-size:122px">三則 AI 新聞，<br>只講跟你上班<br>有關的</div></div><div class="main" style="top:690px"><div data-o="副標" style="font-size:44px;font-weight:800">每則附來源、日期、可信度</div><div class="g3">${rows.map((r,i)=>`<div class="card" data-o="卡${i}" style="background:${['#FFC857','#fff','#BFEBD6'][i]}"><b class="n">${i+1}</b><div class="nm">${r[0]}</div><div class="sm">來源 2｜信心 中</div></div>`).join('')}</div></div>${disc('自製圖文')}`,
`<div class="blk0" data-o="色塊" style="height:440px">${hdr('本週 AI 三則','2/6')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">新聞 1／3<br>微軟提出約 6 萬人自願離職方案</div></div><div class="main" style="top:470px"><div style="display:flex;gap:16px" data-o="資訊列"><span class="pill">事件日 10/26 美東</span><span class="pill">查證日 11/03</span><span class="pill">信心度 中</span></div><div class="g2"><div class="card" data-o="發生什麼"><h3>發生什麼</h3><p>${TXT.what}</p></div><div class="card" data-o="怎麼說"><h3>微軟怎麼說</h3><p>${TXT.say}</p></div></div><div class="card" data-o="差在哪" style="background:${ink};color:#fff"><h3 style="color:${ink}">對上班族差在哪</h3><p>${TXT.diff}</p></div><div class="badge" data-o="標章">整理自新聞｜我沒親自測</div></div>${disc('自製圖文')}`,
`<div class="blk0" data-o="色塊" style="height:300px">${hdr('AI 實測 第 01 期','3/7')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">我怎麼測：5 種題目 × 2 次</div></div><div class="main" style="top:330px"><div class="tw" data-o="表">${tbl('',[134,262,262,294])}</div><div data-o="條件" style="font-size:32px;font-weight:700">${TXT.cond}</div><div class="badge" data-o="標章">自製表格｜非 AI 生成</div></div>${disc('自製圖文')}`,
`<div class="blk0" data-o="色塊" style="height:300px">${hdr('AI 實測 第 01 期','4/7')}<div class="t" data-in="色塊" data-o="標題" style="font-size:62px">步驟 1　它真的變出計算器了</div></div><div class="main" style="top:330px"><div class="ph" data-o="截圖框">${camera('#B27300',96)}<b>待 Andy 截圖</b><p>${TXT.ph1}</p><p style="font-size:30px;color:#6B4A00">${TXT.ph2}</p></div><div class="card" data-o="重點" style="font-size:34px;font-weight:700;line-height:1.45;padding:16px 24px"><span style="background:${am};padding:0 8px">重點：</span>${TXT.key}</div><div class="badge" data-o="標章">截圖為實測｜非 AI 生成</div></div>${disc('截圖已遮個資')}`];
}
// 組裝
function put(name,css,pages){fs.mkdirSync('html',{recursive:true});pages.forEach((b,i)=>fs.writeFileSync(`html/${name}_${i+1}.html`,doc(css,b)))}
module.exports={out,put};
