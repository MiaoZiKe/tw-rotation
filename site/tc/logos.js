/* 科技透明圈公司 LOGO（2026-10-26，Andy：「對應公司要附上 LOGO」）
   做法：公司名 → 官網網域，執行時向 Google favicon 服務要小圖；沒有網域或載入失敗，就退成「公司名首字＋產業色」的圓形字標。
   為什麼這樣：不把任何商標圖檔放進 repo（授權與體積），而且對照表只是網域字串，不確定的留空由字標頂上。
   ⚠ 不碰 tc/json 資料檔；名稱以 json 內的 name 欄原文為鍵。 */
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
(function () {
  'use strict';
  const D = {
    // 晶圓代工
    '台積電': 'tsmc.com', '聯電': 'umc.com', '世界先進': 'vis.com.tw', '力積電': 'powerchip.com', '穩懋': 'winfoundry.com',
    // 記憶體
    '南亞科': 'nanya.com', '旺宏': 'macronix.com', '華邦電': 'winbond.com', '美光台灣': 'micron.com', '建興儲存': 'ssstc.com',
    // 封測
    '日月光': 'aseglobal.com', '矽品': 'spil.com.tw', '力成': 'pti.com.tw', '京元電子': 'kyec.com.tw', '頎邦': 'chipbond.com.tw', '精材': 'xintec.com.tw',
    '穎崴': 'winwayglobal.com', '雍智': 'ksmt.com.tw', '漢測': 'hermes-testing.com.tw', '艾克爾（Amkor）': 'amkor.com',
    // 材料
    '欣興': 'unimicron.com', '景碩': 'kinsus.com.tw', '南電': 'nanyapcb.com.tw', '臻鼎': 'zdtco.com', '台光電': 'emctw.com', '長興材料': 'eternal-group.com',
    '南帝化工': 'nantex.com.tw', '明基材料': 'benqmaterials.com', '光洋應材': 'solartech.com.tw', '英特格（Entegris）': 'entegris.com',
    // 設備
    'ASML': 'asml.com', '應用材料': 'appliedmaterials.com', 'Lam Research': 'lamresearch.com', 'KLA': 'kla.com', 'TEL': 'tel.com', 'SCREEN（DNS）': 'screen.co.jp',
    'Lasertec': 'lasertec.co.jp', '愛德萬': 'advantest.com', '泰瑞達': 'teradyne.com', 'FormFactor': 'formfactor.com', '旺矽': 'mpi-corporation.com', '辛耘': 'scientech.com.tw',
    '漢磊': 'episil.com', '日立先端（Hitachi High-Tech）': 'hitachi-hightech.com', 'Quest Global': 'quest-global.com',
    // IC 設計
    '聯發科': 'mediatek.com', '瑞昱': 'realtek.com', '聯詠': 'novatek.com.tw', '群聯': 'phison.com', '世芯-KY': 'alchip.com', '創意': 'guc-asic.com', '信驊': 'aspeedtech.com',
    '円星': 'm31tech.com', '力旺': 'ememory.com.tw', '天鈺': 'fitipower.com', '奇景': 'himax.com.tw', '奕力': 'ilitek.com', '威鋒': 'via-labs.com', '愛普': 'apmemory.com',
    '慧榮': 'siliconmotion.com', '揚智': 'ali.com.tw', '敦泰': 'focaltech-electronics.com', '普誠': 'princeton.com.tw', '晶相光電': 'soinc.com.tw', '晶豪科': 'esmt.com.tw',
    '松翰': 'sonix.com.tw', '瑞鼎': 'rad-ic.com', '祥碩': 'asmedia.com.tw', '立錡': 'richtek.com', '義隆': 'emc.com.tw', '耐能智慧': 'kneron.com', '聯陽(ITE)': 'ite.com.tw',
    '迅杰': 'ene.com.tw', '達發': 'airoha.com', '鈺創': 'etron.com', '點序': 'asolid-tek.com', '工研院': 'itri.org.tw', 'MPS 台灣': 'monolithicpower.com',
    '力林': '', '開酷': '',
    // ODM
    '鴻海': 'foxconn.com', '廣達': 'quantatw.com', '仁寶': 'compal.com', '緯創': 'wistron.com', '英業達': 'inventec.com', '和碩': 'pegatroncorp.com', '華碩': 'asus.com',
    '技嘉': 'gigabyte.com', '微星': 'msi.com', '明基': 'benq.com', '緯穎': 'wiwynn.com', '台達電': 'deltaww.com', '光寶': 'liteon.com', '智邦': 'accton.com', '智易': 'arcadyan.com',
    '啟碁': 'wnc.com.tw', '合勤': 'zyxel.com', '群光': 'chicony.com', '奇鋐': 'avc.co', '瑞軒': 'amtran.com.tw', '神準': 'senaonetworks.com', '系微': 'insyde.com',
    '趨勢科技': 'trendmicro.com', '元太': 'eink.com', '富智康': 'fihmobile.com', '神雲科技': 'mitaccomputing.com', '鴻運科': '', '神基': 'getac.com', '鴻佰': 'ingrasys.com', '永擎電子': 'asrockrack.com',
    // 面板／光學
    '友達': 'auo.com', '群創': 'innolux.com', '瑞儀光電': 'radiant.com.tw', '大立光': 'largan.com.tw',
    // 外商
    'AMD': 'amd.com', 'Apple': 'apple.com', 'Dell': 'dell.com', 'Garmin': 'garmin.com', 'Google': 'google.com', 'HP': 'hp.com', 'Merck': 'merck.com', 'Meta': 'meta.com',
    'NVIDIA': 'nvidia.com', 'Synopsys': 'synopsys.com', 'Wipro': 'wipro.com', '博通': 'broadcom.com', '微軟': 'microsoft.com', '高通': 'qualcomm.com', 'AMI': 'ami.com',
    'SSMC（新加坡）': 'ssmc.com',
    // 其他
    '乾坤科技': 'cyntec.com', '四零四科技（Moxa）': 'moxa.com', '新盛力科技': 'stl-tech.com', '裕隆': 'yulon-motor.com.tw', '鴻華先進': 'foxtronev.com', '瑞力登 Raritan': 'raritan.com',
    '碩貝德': '', '科傳': '', '馳諾瓦': '', 'Unabiz': 'unabiz.com', '虹堡': 'castlestech.com', '雃博': 'wellell.com', '新代': 'syntecclub.com',
    '立元科技': '', '車美仕': 'carmax.com.tw', '連宇': 'uicpaymentsinc.com'
  };
  Object.assign(D, { '智原': 'faraday-tech.com', '新唐': 'nuvoton.com' });
  // 產業色：與圖表分類色同系，字標底色用
  const IC = { foundry: '#3ee0ff', memory: '#8b7bff', osat: '#ffb454', material: '#2ec4b6', equipment: '#ff7a45', icdesign: '#4d8dff', odm: '#c3ff5b', panel: '#e56bd0', foreign: '#9aa7b8', other: '#7c8aa0' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // 圖源三段：gstatic faviconV2 256px → 失敗或 <32px 退 DuckDuckGo ip3 → 再失敗退字標（未具名公司直接畫中性建築圖示）；2x 以上來源，顯示尺寸不變
  const src1 = (dm) => 'https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=' + encodeURIComponent('https://' + dm) + '&size=256';
  const src2 = (dm) => 'https://icons.duckduckgo.com/ip3/' + encodeURIComponent(dm) + '.ico';
  function failImg(t) {
    if (t.dataset.st === '0') { t.dataset.st = '1'; t.src = src2(t.dataset.dm); return; }
    if (t.parentNode) t.parentNode.dataset.lg = 'txt'; t.remove();
  }
  function domain(name) { return D[name] || ''; }
  // 未具名／類別名：不是一家可查官網的公司，字標改中性建築圖示
  const GEN = new Set(['設備商', '外商（台灣據點）', 'IC 晶圓代工', 'IC 設計', '記憶體', '封測', '材料／PCB', '系統廠 ODM/OEM', '其他科技', '面板／光學']);
  const unnamed = (n) => GEN.has(n) || /未具名|派遣 [A-Z]/.test(String(n || ''));
  const BLD = '<svg viewBox="0 0 24 24" width="62%" height="62%" fill="currentColor" aria-hidden="true"><path d="M4 21V5l8-3v6l8 3v10h-6v-4h-4v4zm3-13h2V6H7zm0 4h2v-2H7zm0 4h2v-2H7zm8 0h2v-2h-2zm0-4h2v-2h-2z"/></svg>';
  /* 回傳 HTML 字串：字標先畫在底層，有網域才疊 <img>，img 失敗由下面的全域 error 監聽移除，字標自然露出 */
  function html(name, ind, size) {
    const col = IC[ind] || IC.other, un = unnamed(name), ch = Array.from(String(name || '?'))[0] || '?', dm = un ? '' : domain(name), sz = size || 24;
    return '<span class="tc-lg" data-lg="' + (dm ? 'img' : 'txt') + '" style="--lg:' + col + ';--lz:' + sz + 'px"' + (un ? ' data-un="1" title="未具名公司"' : '') + '><i>' + (un ? BLD : esc(ch)) + '</i>' +
      (dm ? '<img src="' + src1(dm) + '" data-dm="' + esc(dm) + '" data-st="0" alt="' + esc(name) + '" loading="lazy" referrerpolicy="no-referrer" width="' + sz + '" height="' + sz + '">' : '') + '</span>';
  }
  // error 不冒泡，用捕獲階段接；失敗就拔掉圖，露出下面的字標
  // 圖載好才蓋上字標；naturalWidth<32（含 16×16 預設地球）視同失敗；error 不冒泡所以用捕獲階段
  const isLg = (t) => t && t.tagName === 'IMG' && t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('tc-lg');
  document.addEventListener('load', (e) => { const t = e.target; if (!isLg(t)) return; if (t.dataset.st === '0' && t.naturalWidth && t.naturalWidth < 32) failImg(t); else t.classList.add('ok'); }, true);
  document.addEventListener('error', (e) => { const t = e.target; if (isLg(t)) failImg(t); }, true);
  window.TcLogo = { html, domain, unnamed, color: (ind) => IC[ind] || IC.other, map: D };
})();
