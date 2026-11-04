const {chromium}=require('/opt/node-tools/node_modules/playwright');
const rows=[['A','A 白紙大字','暖白底、近黑大字、單一珊瑚紅強調，靠留白與字級取勝。','依據：白紙類被點名最受歡迎的輪播型之一（Matt Gray 分類，recapio；contentstudio、postnitro 的大字高對比原則）。信心：中'],
['B','B 手繪筆記','方格紙、螢光筆、便利貼、膠帶，像一頁讀書筆記。','依據：Notion 手繪／馬克筆風（Claude 技能範例）、Substack 柔和手繪款。信心：低，沒有互動數據'],
['C','C 便當格資訊卡','淺灰底配白色圓角卡，每頁一格上主題色，格內全是真資訊。','依據：蘋果發表會摘要帶起的 bento（saasframe、contra、usevisuals）。信心：中到低'],
['D','D 新粗獷','奶油底、黑粗邊、硬陰影、亮黃粉藍，對比強、一眼停下。','依據：新粗獷特徵描述（asiadesignprize、pixso）。信心：低到中，趨勢多在網頁'],
['E','E 對話氣泡','自創通用對話框，使用者提問、AI 回答，像一段聊天紀錄。','依據：科技與財經精選帳號的對話截圖做法（twittershots、brandghost）。信心：低到中'],
['F','F 日系排版海報','象牙底、墨綠巨字、朱紅小點，字體當主視覺，像展覽海報。','依據：數位時代整理的 Threads 爆紅風格（日系排版海報、字體主導）。信心：中到低']];
rows.splice(0,rows.length,rows[0],rows[2]);
const html=`<meta charset=utf-8><style>*{box-sizing:border-box;margin:0;padding:0}body{width:1760px;background:#fff;font-family:'Inter','WenQuanYi Zen Hei',sans-serif;color:#111;padding:40px}
h1{font-size:44px;margin-bottom:8px}p.s{font-size:26px;color:#444;margin-bottom:28px}
.r{display:flex;gap:28px;align-items:center;border-top:3px solid #111;padding:22px 0}.lb{width:560px;flex:none}.lb b{display:block;font-size:44px;margin-bottom:10px}.lb span{display:block;font-size:28px;line-height:1.5;margin-bottom:10px}.lb i{display:block;font-style:normal;font-size:24px;line-height:1.5;color:#555}
img{width:270px;height:337px;border:1.5px solid #cfd3d9;display:block}</style>
<h1>頻道③ AI 介紹　版型 v3　六種受歡迎風格</h1><p class=s>同一組四張：封面、新聞卡、比較表、待截圖頁（1080×1350，此圖為縮圖）</p>
${rows.map(r=>`<div class=r><div class=lb><b>${r[1]}</b><span>${r[2]}</span><i>${r[3]}</i></div>${[1,2,3,4].map(i=>`<img src="png/${r[0]}_${i}.png">`).join('')}</div>`).join('')}`;
require('fs').writeFileSync('overview_r2.html',html);
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1760,height:800}});await p.goto('file://'+process.cwd()+'/overview_r2.html');await p.waitForTimeout(400);await p.screenshot({path:'overview_r2.png',fullPage:true});await b.close()})()
