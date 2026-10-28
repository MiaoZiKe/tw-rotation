/* 科技透明圈公司 LOGO（2026-10-26，Andy：「對應公司要附上 LOGO」）
   做法：公司名 → 官網網域，執行時向 Google favicon 服務要小圖；沒有網域或載入失敗，就退成「公司名首字＋產業色」的圓形字標。
   為什麼這樣：不把任何商標圖檔放進 repo（授權與體積），而且對照表只是網域字串，不確定的留空由字標頂上。
   ⚠ 不碰 tc/json 資料檔；名稱以 json 內的 name 欄原文為鍵。 ｜2026-10-29 補：華通 compeq.com.tw（technews 公司資料／MONEY LINK）｜南茂 chipmos.com（MoneyDJ／StockAnalysis）｜合晶 waferworks.com（histock 6182 公司資料／Craft）｜聯穎光電 查不到官網，不補 ｜明泰 alphanetworks.com（technews 公司資料／goodinfo／年報封面） ｜譜瑞 paradetech.com（histock／MONEY LINK／wantgoo 公司資料、年報） */
/* 2026-10-28 補：鴻勁 honprec.com（鉅亨／technews 公司資料）｜德律 tri.com.tw（technews／Statementdog）｜Cadence cadence.com、Siemens EDA siemens.com、HPE hpe.com（原廠主網域）｜環球晶 sas-globalwafers.com（goodinfo／MONEY LINK）｜中美晶 saswafer.com（technews 公司資料）｜宸曜科技 neousys-tech.com（官網公司介紹）｜研華 advantech.com（財報與 Statementdog）｜多方科技 查不到官網，不補｜台星科 winstek.com.tw（MONEY LINK 公司基本資料）｜海華 azurewave.com（商工登記／玩股網）｜超豐 greatek.com.tw（technews 公司資料）｜弘塑 gptc.com.tw（twincn 公司登記資料）｜久元 ytec.com.tw（technews／鉅亨公司資料）｜台灣光罩 tmcnet.com.tw（technews／wantgoo 公司資料）｜台灣荏原 ebara.com（母公司荏原製作所主網域，台灣分公司無獨立網域可查）｜祥茂光電 ao-inc.com（新北市就業平台企業資料，Applied Optoelectronics） */
/* 2026-10-26 逐家查證（WebSearch，關鍵字「<公司> 官網／網址」「<英文名> official website」）：
   改正：力積電 psmc.tw→powerchip.com（technews 公司資料、維基）｜旺宏 mxic.com.tw→macronix.com（technews）｜穎崴 chpt.com.tw→winwayglobal.com（MONEY LINK）
   南電 npc.com.tw→nanyapcb.com.tw（technews）｜長興 eternal-materials.com→eternal-group.com（法說簡報網域）｜明基材 beq.com→benqmaterials.com（年報）
   旺矽 mpi.com.tw→mpi-corporation.com（SEMI 會員頁）｜創意 gucchip.com→guc-asic.com（維基、TSMC OIP）｜円星 neuchips.ai→m31tech.com（官網）
   力旺 ememory.com→ememory.com.tw（technews）｜揚智 alisemi.com→ali.com.tw（官網新聞稿）｜晶相光電 pixart.com→soinc.com.tw（technews；原值是原相）
   瑞鼎 raydium.com.tw→rad-ic.com（MONEY LINK、Google Finance）｜迅杰 o2micro.com→ene.com.tw（technews、財報狗；原值是凹凸科技）
   智易 sercomm.com→arcadyan.com（twincn；原值是中磊）｜群光 chicony.com.tw→chicony.com（2024 年報）｜奇鋐 avc.com.tw→avc.co（technews 登記）
   神雲 mitac.com→mitaccomputing.com（維基、工商時報）｜鴻華先進 foxtron.com→foxtronev.com（technews、MONEY LINK）｜雃博 apexmedical.com.tw→wellell.com（twincn 登記）
   新增：神基 getac.com（CSR 報告網域）｜鴻佰 ingrasys.com（人才招募資料）｜漢測（漢民測試）hermes-testing.com.tw（漢民官網英文頁）
   雷泰＝雷泰光電（光罩檢測、EUV，即 Lasertec 台灣）→ lasertec.co.jp；⚠ json 的 code 6164 實為華興電子（LEDTECH），代號有誤，未改 json
   車美仕 carmax.com.tw（TVBS 報導）｜連宇（2482 UIC）uicpaymentsinc.com（technews 登記）
   其餘已核對一致：台積電 聯電 世界先進 穩懋 南亞科 華邦 建興 日月光 矽品 力成 京元 頎邦 精材 雍智 欣興 臻鼎 台光電 光洋科 漢磊 辛耘 天鈺 奕力 威鋒 愛普 慧榮 敦泰 普誠
     晶豪科 松翰 祥碩 義隆 聯陽 達發 鈺創 點序 奇景 神準 瑞軒 啟碁 瑞儀 大立光 富智康 永擎 新盛力 乾坤 虹堡 新代 SSMC
   國際大廠（ASML、NVIDIA、Apple…）與知名品牌網域未逐家另搜。
   仍無網域：鴻運科（只查到新加坡商專利資料）、立元科技、科傳、碩貝德（查到 speed-hz.com 僅為信箱網域，未證實）、馳諾瓦、開酷（kaikutek，查無官網）、力林 */
/* 2026-10-27 第二輪查證（國際大廠／大型品牌逐家 WebSearch；台灣子公司一律以集團主網域為 favicon 來源）：
   改正：Quest Global quest-global.com→questglobal.com（多數頁面在無連字號網域）｜Merck merck.com→merckgroup.com（台灣默克＝德國 Merck KGaA 電子材料；merck.com 是美國 MSD）
   Garmin garmin.com→garmin.com.tw（台灣國際航電官網，實習公告）｜合勤 zyxel.com→zyxelgroup.com（3704 合勤控登記網址）
   台灣子公司用主網域：ASML（asml.com/zh-tw）、應材（appliedmaterials.com/tw）、Lam、KLA（台灣分公司無獨立網域）、TEL、美光（micron.com）、愛德萬（advantest.com/tw）、
     泰瑞達、AMD／NVIDIA（/zh-tw）、Dell（/zh-tw）、HP（/tw-zh）、Synopsys（/zh-tw）、高通、AMI、Moxa（moxa.com/tw）、Raritan（raritan.com/ap/tw）
   一手或登記資料核對一致：台積電 聯電 南亞科 華邦 日月光 Amkor 欣興 聯發科 瑞昱 聯詠 群聯 世芯 信驊 立錡 耐能 智原 新唐 MPS 工研院 SCREEN FormFactor 日立先端
     鴻海 廣達 仁寶 緯創 英業達 和碩 華碩 技嘉 微星 緯穎 台達電 光寶 智邦 系微 趨勢 元太 友達 群創 裕隆 Wipro 博通 Meta UnaBiz
   明基：json 代號 2352 實為佳世達（qisda.com.tw），名稱寫明基故仍用品牌 benq.com。Google／微軟搜尋摘要未直接列網址，網域即品牌主網域。
   查無補上（換 3 組關鍵字）：鴻運科→foxconn.com（新加坡商，鴻海 100% 持有的 Foxconn Singapore 體系；集團主網域，中信心）
     碩貝德→speed-hz.com（母公司惠州碩貝德 300322 登記網站，台灣子公司信箱同網域）｜馳諾瓦→phihongtech.com（飛宏子公司，母公司登記網址）｜開酷→kaikutek.com（科技新報等報導）
   仍無：立元科技（立元科技 官網／統一編號／Liyuan Technology／薪水 面試，皆只撈到立端、立銜等）、科傳（官網／統編 英文名／Cotron 推測未證實）、
     力林（官網／統一編號 網址／Li Lin 電子 半導體，只撈到力領、力智） */
(function () {
  'use strict';
  const D = {
    // 晶圓代工
    '台積電': 'tsmc.com', '聯電': 'umc.com', '世界先進': 'vis.com.tw', '力積電': 'powerchip.com', '穩懋': 'winfoundry.com',
    // 記憶體
    '南亞科': 'nanya.com', '旺宏': 'macronix.com', '華邦電': 'winbond.com', '美光台灣': 'micron.com', '建興儲存': 'ssstc.com',
    // 封測
    '日月光': 'aseglobal.com', '矽品': 'spil.com.tw', '力成': 'pti.com.tw', '京元電子': 'kyec.com.tw', '頎邦': 'chipbond.com.tw', '南茂': 'chipmos.com', '精材': 'xintec.com.tw',
    '穎崴': 'winwayglobal.com', '雍智': 'ksmt.com.tw', '漢測': 'hermes-testing.com.tw', '台星科': 'winstek.com.tw', '超豐': 'greatek.com.tw', '久元': 'ytec.com.tw', '艾克爾（Amkor）': 'amkor.com',
    // 材料
    '欣興': 'unimicron.com', '景碩': 'kinsus.com.tw', '南電': 'nanyapcb.com.tw', '臻鼎': 'zdtco.com', '台光電': 'emctw.com', '長興材料': 'eternal-group.com',
    '南帝化工': 'nantex.com.tw', '環球晶': 'sas-globalwafers.com', '中美晶': 'saswafer.com', '華通': 'compeq.com.tw', '合晶': 'waferworks.com', '台灣光罩': 'tmcnet.com.tw', '明基材料': 'benqmaterials.com', '光洋應材': 'solartech.com.tw', '英特格（Entegris）': 'entegris.com',
    // 設備
    'ASML': 'asml.com', '應用材料': 'appliedmaterials.com', 'Lam Research': 'lamresearch.com', 'KLA': 'kla.com', 'TEL': 'tel.com', 'SCREEN（DNS）': 'screen.co.jp',
    'Lasertec': 'lasertec.co.jp', '愛德萬': 'advantest.com', '泰瑞達': 'teradyne.com', 'FormFactor': 'formfactor.com', '旺矽': 'mpi-corporation.com', '辛耘': 'scientech.com.tw',
    '漢磊': 'episil.com', '日立先端（Hitachi High-Tech）': 'hitachi-hightech.com', 'Quest Global': 'questglobal.com', '鴻勁': 'honprec.com', '德律': 'tri.com.tw', '弘塑': 'gptc.com.tw', '台灣荏原': 'ebara.com',
    // IC 設計
    '聯發科': 'mediatek.com', '瑞昱': 'realtek.com', '聯詠': 'novatek.com.tw', '群聯': 'phison.com', '世芯-KY': 'alchip.com', '創意': 'guc-asic.com', '信驊': 'aspeedtech.com',
    '円星': 'm31tech.com', '力旺': 'ememory.com.tw', '天鈺': 'fitipower.com', '奇景': 'himax.com.tw', '奕力': 'ilitek.com', '威鋒': 'via-labs.com', '愛普': 'apmemory.com',
    '慧榮': 'siliconmotion.com', '揚智': 'ali.com.tw', '敦泰': 'focaltech-electronics.com', '普誠': 'princeton.com.tw', '晶相光電': 'soinc.com.tw', '晶豪科': 'esmt.com.tw',
    '松翰': 'sonix.com.tw', '瑞鼎': 'rad-ic.com', '祥碩': 'asmedia.com.tw', '譜瑞': 'paradetech.com', '立錡': 'richtek.com', '義隆': 'emc.com.tw', '耐能智慧': 'kneron.com', '聯陽(ITE)': 'ite.com.tw',
    '迅杰': 'ene.com.tw', '達發': 'airoha.com', '鈺創': 'etron.com', '點序': 'asolid-tek.com', '工研院': 'itri.org.tw', 'MPS 台灣': 'monolithicpower.com',
    '力林': '', '開酷': 'kaikutek.com',
    // ODM
    '鴻海': 'foxconn.com', '廣達': 'quantatw.com', '仁寶': 'compal.com', '緯創': 'wistron.com', '英業達': 'inventec.com', '和碩': 'pegatroncorp.com', '華碩': 'asus.com',
    '技嘉': 'gigabyte.com', '微星': 'msi.com', '明基': 'benq.com', '緯穎': 'wiwynn.com', '台達電': 'deltaww.com', '光寶': 'liteon.com', '智邦': 'accton.com', '智易': 'arcadyan.com',
    '啟碁': 'wnc.com.tw', '合勤': 'zyxelgroup.com', '群光': 'chicony.com', '奇鋐': 'avc.co', '瑞軒': 'amtran.com.tw', '神準': 'senaonetworks.com', '系微': 'insyde.com',
    '趨勢科技': 'trendmicro.com', '元太': 'eink.com', '富智康': 'fihmobile.com', '明泰': 'alphanetworks.com', '神雲科技': 'mitaccomputing.com', '鴻運科': 'foxconn.com', '神基': 'getac.com', '鴻佰': 'ingrasys.com', '永擎電子': 'asrockrack.com', '宸曜科技': 'neousys-tech.com', '研華': 'advantech.com', '海華': 'azurewave.com', '祥茂光電': 'ao-inc.com',
    // 面板／光學
    '友達': 'auo.com', '群創': 'innolux.com', '瑞儀光電': 'radiant.com.tw', '大立光': 'largan.com.tw',
    // 外商
    'AMD': 'amd.com', 'Apple': 'apple.com', 'Dell': 'dell.com', 'Garmin': 'garmin.com.tw', 'Google': 'google.com', 'HP': 'hp.com', 'Merck': 'merckgroup.com', 'Meta': 'meta.com',
    'NVIDIA': 'nvidia.com', 'Synopsys': 'synopsys.com', 'Cadence': 'cadence.com', 'Siemens EDA': 'siemens.com', 'HPE': 'hpe.com', 'Wipro': 'wipro.com', '博通': 'broadcom.com', '微軟': 'microsoft.com', '高通': 'qualcomm.com', 'AMI': 'ami.com',
    'SSMC（新加坡）': 'ssmc.com',
    // 其他
    '乾坤科技': 'cyntec.com', '四零四科技（Moxa）': 'moxa.com', '新盛力科技': 'stl-tech.com', '裕隆': 'yulon-motor.com.tw', '鴻華先進': 'foxtronev.com', '瑞力登 Raritan': 'raritan.com',
    '碩貝德': 'speed-hz.com', '科傳': '', '馳諾瓦': 'phihongtech.com', 'Unabiz': 'unabiz.com', '虹堡': 'castlestech.com', '雃博': 'wellell.com', '新代': 'syntecclub.com',
    '立元科技': '', '車美仕': 'carmax.com.tw', '連宇': 'uicpaymentsinc.com'
  };
  Object.assign(D, { '智原': 'faraday-tech.com', '新唐': 'nuvoton.com' });
  // 產業色：與圖表分類色同系，字標底色用
  const IC = { foundry: '#3ee0ff', memory: '#8b7bff', osat: '#ffb454', material: '#2ec4b6', equipment: '#ff7a45', icdesign: '#4d8dff', odm: '#c3ff5b', panel: '#e56bd0', foreign: '#9aa7b8', other: '#7c8aa0' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  /* 2026-10-27 Andy：「之前建立搜尋功能、個股資訊時做過查找 LOGO 功能」→ 優先用站內個股 Logo（DECISIONS #264、#267）。
     來源順序：① 公司在 tc/json 有數字代號（4～6 碼）且 data/logos.json 有該代號 → 站內 data/logos/<代號>.png（管線抓的官網圖，與個股頁同一份）；
     ② 沒代號／站內沒圖（外商、未上市、外商台灣子公司）→ gstatic faviconV2 256 → Google s2 256（#267 決議不用 DuckDuckGo，已移除）；
     ③ 都不夠清楚 → 字標。外部來源載入後 naturalWidth < 64 一律換下一個、不放大糊圖。
     站內圖不放大：原圖 < 容器內徑×2 時以原尺寸（≤ 內徑）置中顯示；原圖 < 16px 才退字標。
     不改 app.js：app.js 的 logoSrc 沒掛在 window，這裡讀同一支 data/logos.json（同一個檔、同一個版本）；預覽版由 preview_boot.js 把 data/ 改寫到正式站，路徑一併改寫。 */
  const SRC = [
    (dm) => 'https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=' + encodeURIComponent('https://' + dm) + '&size=256',
    (dm) => 'https://www.google.com/s2/favicons?domain=' + encodeURIComponent(dm) + '&sz=256'
  ];
  const MINW = 64, STMIN_S = 48, STMIN_D = 32, LSK = 'tc.lgsrc2';
  let MEM = {};
  try { MEM = JSON.parse(localStorage.getItem(LSK) || '{}') || {}; } catch (e) { MEM = {}; }
  function remember(dm, i) { MEM[dm] = i; try { localStorage.setItem(LSK, JSON.stringify(MEM)); } catch (e) { /* 私密視窗等：不記也照常運作 */ } }
  // 站內 Logo 對照（與 app.js 同一支 logos.json）；名稱→代號由 tc.js 載完 json 後登記
  let LG = null; const CODE = {};
  const okPath = (s) => typeof s === 'string' && /^[\w./:-]+\.(png|webp|jpg|jpeg|svg)$/i.test(s) && !s.includes('..');
  const LGP = fetch('data/logos.json', { cache: 'no-cache' }).then(async (r) => { const t = await r.text(); if (!r.ok) return {}; try { return JSON.parse(t); } catch (e) { return {}; } }).catch(() => ({}))
    .then((m) => { LG = m && typeof m === 'object' ? m : {}; upgrade(document); return LG; });
  const isCode = (c) => /^\d{4,6}$/.test(String(c || ''));
  /* 第二層：站內網域圖 data/tc_logos.json（{網域: 路徑}，資料同事抓進資料湖）；檔案不存在或 404 就是空物件，晚到也自動生效。
     預覽版 preview_boot 只改寫 logos.json 的路徑，這支檔名不同，所以路徑在這裡自己改到正式站的 data/ */
  let TLG = {}, TDONE = false;
  const prevRoot = (location.pathname.match(/^(.*?\/)preview\/[^/]+\//) || [])[1];
  const fixP = (p) => (prevRoot && /^data\//.test(p) ? prevRoot + p : p);
  const TLP = fetch('data/tc_logos.json', { cache: 'no-cache' }).then(async (r) => { const t = await r.text(); if (!r.ok) return {}; try { return JSON.parse(t); } catch (e) { return {}; } }).catch(() => ({}))
    .then((m) => { TLG = m && typeof m === 'object' ? m : {}; TDONE = true; upgrade(document); return TLG; });
  function dstation(name) { const dm = domain(name), p = dm && TLG[dm]; return okPath(p) ? fixP(p) : ''; }
  /* 2026-10-27 站內代號圖不是 LOGO（例如 2385 群光是一張鍵盤照片）的代號：不用站內代號圖，直接往下一來源（網域圖→s2→字標） */
  const NOSTATION = new Set(['2385']);
  function station(name) { const c = CODE[name]; return (LG && isCode(c) && !NOSTATION.has(String(c)) && okPath(LG[c])) ? LG[c] : ''; }
  function reg(name, code) { if (name && isCode(code)) CODE[name] = String(code); }
  function toTxt(t) { if (t.parentNode) { t.parentNode.dataset.lg = 'txt'; t.parentNode.classList.remove('has'); } t.remove(); }
  function cand(t) { const L = []; if (t.dataset.s) t.dataset.s.split('|').forEach((x) => L.push(x)); if (t.dataset.dm) SRC.forEach((f) => L.push(f(t.dataset.dm))); return L; }
  function nextImg(t) {
    const n = +t.dataset.st + 1, L = cand(t);
    if (n < L.length) { t.dataset.st = String(n); t.classList.remove('sm', 'lc'); t.style.width = t.style.height = ''; t.src = L[n]; return; }
    if (t.dataset.dm && !t.dataset.s) remember(t.dataset.dm, -1);
    toTxt(t);
  }
  function domain(name) { return D[name] || ''; }
  // 未具名／類別名：不是一家可查官網的公司，字標改中性建築圖示
  const GEN = new Set(['設備商', '外商（台灣據點）', 'IC 晶圓代工', 'IC 設計', '記憶體', '封測', '材料／PCB', '系統廠 ODM/OEM', '其他科技', '面板／光學']);
  const unnamed = (n) => GEN.has(n) || /未具名|派遣 [A-Z]/.test(String(n || ''));
  const BLD = '<svg viewBox="0 0 24 24" width="62%" height="62%" fill="currentColor" aria-hidden="true"><path d="M4 21V5l8-3v6l8 3v10h-6v-4h-4v4zm3-13h2V6H7zm0 4h2v-2H7zm0 4h2v-2H7zm8 0h2v-2h-2zm0-4h2v-2h-2z"/></svg>';
  // 站內圖：st=0 用站內路徑；沒站內圖時從外部來源開始（記住的來源索引用 MEM）
  function imgTag(name, dm, sz, st) {
    const L2 = [['s', station(name)], ['d', dstation(name)]].filter((x) => x[1]), loc = L2.map((x) => x[1]), s = loc.join('|'), kd = L2.map((x) => x[0]).join('|');
    const i = loc.length ? 0 : (dm && MEM[dm] > 0 ? Math.min(MEM[dm], SRC.length - 1) : 0);
    const src = loc.length ? loc[0] : SRC[i](dm);
    return '<img src="' + esc(src) + '" data-dm="' + esc(dm) + '" data-s="' + esc(s) + '" data-k="' + kd + '" data-st="' + i + '" alt="' + esc(name) + '" loading="lazy" referrerpolicy="no-referrer" width="' + sz + '" height="' + sz + '">';
  }
  /* 回傳 HTML 字串：字標先畫在底層，有圖來源才疊 <img>；LG 還沒載好的短暫空檔，data-pend 標起來，載好後 upgrade() 補圖 */
  function html(name, ind, size) {
    const col = IC[ind] || IC.other, un = unnamed(name), ch = Array.from(String(name || '?'))[0] || '?', dm = un ? '' : domain(name), sz = size || 24;
    const hasSt = !un && !!(station(name) || dstation(name)), pend = !un && (!LG || !TDONE) && !!(isCode(CODE[name]) || dm);
    const useExt = !!dm && MEM[dm] !== -1 && !hasSt;
    const img = hasSt ? imgTag(name, dm, sz, true) : (useExt && !pend ? imgTag(name, dm, sz, false) : '');
    return '<span class="tc-lg" data-co="' + esc(name) + '" data-lg="' + (img ? 'img' : 'txt') + '"' + (pend ? ' data-pend="1"' : '') + ' style="--lg:' + col + ';--lz:' + sz + 'px"' + (un ? ' data-un="1" title="未具名公司"' : '') + '><i>' + (un ? BLD : esc(ch)) + '</i>' + img + '</span>';
  }
  // LG 晚到：把已畫好的字標補上圖
  function upgrade(root) {
    Array.from(root.querySelectorAll('.tc-lg[data-pend]')).forEach((el) => {
      if (!LG || !TDONE) return;
      el.removeAttribute('data-pend');
      const name = el.dataset.co, dm = domain(name), sz = parseInt(el.style.getPropertyValue('--lz'), 10) || 24;
      const hasSt = !!(station(name) || dstation(name));
      if (!hasSt && !(dm && MEM[dm] !== -1)) return;
      el.dataset.lg = 'img'; el.insertAdjacentHTML('beforeend', imgTag(name, dm, sz, hasSt));
    });
  }
  // error 不冒泡，用捕獲階段接。站內圖 ≥16px 收；外部圖 ≥64px 才收（16／32px 的小 favicon 放大會糊）；收下後依容器尺寸決定要不要縮小置中
  const isLg = (t) => t && t.tagName === 'IMG' && t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('tc-lg');
  document.addEventListener('load', (e) => {
    const t = e.target; if (!isLg(t)) return;
    const nloc = t.dataset.s ? t.dataset.s.split('|').length : 0, st = +t.dataset.st < nloc, nw = t.naturalWidth;
    // 2026-10-27 Andy：站內代號圖 < 48px（如聯電 16px）視為低解析 → 換網域圖（< 32px 同理）→ Google（≥64）→ 字標
    const kind = st ? (t.dataset.k || '').split('|')[+t.dataset.st] : '', need = st ? (kind === 's' ? STMIN_S : STMIN_D) : MINW;
    if (!nw || nw < need) { nextImg(t); return; }
    if (st) {   // 站內圖一律 contain＋10% 邊距，不裁切；橫幅也完整縮進白圓內
      t.classList.add('lc'); t.parentNode.classList.add('has'); t.classList.add('ok'); return;
    }
    const box = t.parentNode.clientWidth || parseInt(t.parentNode.style.getPropertyValue('--lz'), 10) || 24, inner = Math.max(8, box - 8);
    if (nw < inner * 2) { const z = Math.min(nw, inner); t.classList.add('sm'); t.style.width = t.style.height = z + 'px'; }   // 解析不夠 ×2：不放大，原尺寸（不超過內徑）置中
    if (!st) remember(t.dataset.dm, +t.dataset.st);
    t.parentNode.classList.add('has'); t.classList.add('ok');
  }, true);
  document.addEventListener('error', (e) => { const t = e.target; if (isLg(t)) nextImg(t); }, true);
  // 統計用：每家預定來源（station＝站內、ext＝Google s2/gstatic、txt＝字標）
  function plan(name) { if (unnamed(name)) return 'txt'; if (station(name)) return 'station'; if (dstation(name)) return 'domain'; return domain(name) ? 'ext' : 'txt'; }
  window.TcLogo = { html, domain, unnamed, reg, plan, ready: Promise.all([LGP, TLP]), station, upgrade, sources: SRC, MINW, color: (ind) => IC[ind] || IC.other, map: D };
})();
