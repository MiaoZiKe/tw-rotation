// node v9/shot3.js <html> <輸出前綴> <t1,t2,...>：開頁面、renderAt(t) 後逐張截圖（驗證用，不渲染整支）
const {chromium}=require('/opt/node-tools/node_modules/playwright');
(async()=>{const [html,pre,ts]=process.argv.slice(2);const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1080,height:1920}});
 await pg.goto('file://'+html);await pg.waitForTimeout(400);let i=0;
 for(const t of ts.split(',').map(Number)){await pg.evaluate(t=>window.renderAt(t),t);await pg.screenshot({path:pre+'_'+(i++)+'.png'})}
 await b.close()})();
