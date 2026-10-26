/* 科技透明圈公司 LOGO（2026-10-26，Andy：「對應公司要附上 LOGO」）
   做法：公司名 → 官網網域，執行時向 Google favicon 服務要小圖；沒有網域或載入失敗，就退成「公司名首字＋產業色」的圓形字標。
   為什麼這樣：不把任何商標圖檔放進 repo（授權與體積），而且對照表只是網域字串，不確定的留空由字標頂上。
   ⚠ 不碰 tc/json 資料檔；名稱以 json 內的 name 欄原文為鍵。 */
(function () {
  'use strict';
  const D = {
    // 晶圓代工
    '台積電': 'tsmc.com', '聯電': 'umc.com', '世界先進': 'vis.com.tw', '力積電': 'psmc.tw', '穩懋': 'winfoundry.com',
    // 記憶體
    '南亞科': 'nanya.com', '旺宏': 'mxic.com.tw', '華邦電': 'winbond.com', '美光台灣': 'micron.com', '建興儲存': '',
    // 封測
    '日月光': 'aseglobal.com', '矽品': 'spil.com.tw', '力成': 'pti.com.tw', '京元電子': 'kyec.com.tw', '頎邦': 'chipbond.com.tw', '精材': 'xintec.com.tw',
    '穎崴': 'chpt.com.tw', '雍智': '', '漢測': '', '艾克爾（Amkor）': 'amkor.com',
    // 材料
    '欣興': 'unimicron.com', '景碩': 'kinsus.com.tw', '南電': 'npc.com.tw', '臻鼎': 'zdtco.com', '台光電': 'emctw.com', '長興材料': 'eternal-materials.com',
    '南帝化工': '', '明基材料': 'beq.com', '光洋應材': '', '英特格（Entegris）': 'entegris.com',
    // 設備
    'ASML': 'asml.com', '應用材料': 'appliedmaterials.com', 'Lam Research': 'lamresearch.com', 'KLA': 'kla.com', 'TEL': 'tel.com', 'SCREEN（DNS）': 'screen.co.jp',
    'Lasertec': 'lasertec.co.jp', '愛德萬': 'advantest.com', '泰瑞達': 'teradyne.com', 'FormFactor': 'formfactor.com', '旺矽': 'mpi.com.tw', '辛耘': 'scientech.com.tw',
    '漢磊': '', '日立先端（Hitachi High-Tech）': 'hitachi-hightech.com', 'Quest Global': 'quest-global.com',
    // IC 設計
    '聯發科': 'mediatek.com', '瑞昱': 'realtek.com', '聯詠': 'novatek.com.tw', '群聯': 'phison.com', '世芯-KY': 'alchip.com', '創意': 'gucchip.com', '信驊': 'aspeedtech.com',
    '円星': 'neuchips.ai', '力旺': 'ememory.com', '天鈺': 'fitipower.com', '奇景': 'himax.com.tw', '奕力': 'ilitek.com', '威鋒': 'via-labs.com', '愛普': 'apmemory.com',
    '慧榮': 'siliconmotion.com', '揚智': 'alisemi.com', '敦泰': 'focaltech-electronics.com', '普誠': 'princeton.com.tw', '晶相光電': 'pixart.com', '晶豪科': 'esmt.com.tw',
    '松翰': 'sonix.com.tw', '瑞鼎': 'raydium.com.tw', '祥碩': 'asmedia.com.tw', '立錡': 'richtek.com', '義隆': 'emc.com.tw', '耐能智慧': 'kneron.com', '聯陽(ITE)': 'ite.com.tw',
    '迅杰': 'o2micro.com', '達發': 'airoha.com', '鈺創': 'etron.com', '雷泰': '', '點序': '', '工研院': 'itri.org.tw', 'MPS 台灣': 'monolithicpower.com',
    '力林': '', '開酷': '',
    // ODM
    '鴻海': 'foxconn.com', '廣達': 'quantatw.com', '仁寶': 'compal.com', '緯創': 'wistron.com', '英業達': 'inventec.com', '和碩': 'pegatroncorp.com', '華碩': 'asus.com',
    '技嘉': 'gigabyte.com', '微星': 'msi.com', '明基': 'benq.com', '緯穎': 'wiwynn.com', '台達電': 'deltaww.com', '光寶': 'liteon.com', '智邦': 'accton.com', '智易': 'sercomm.com',
    '啟碁': 'wnc.com.tw', '合勤': 'zyxel.com', '群光': 'chicony.com.tw', '奇鋐': 'avc.com.tw', '瑞軒': 'amtran.com.tw', '神準': '', '系微': 'insyde.com',
    '趨勢科技': 'trendmicro.com', '元太': 'eink.com', '富智康': 'fihmobile.com', '神雲科技': 'mitac.com', '鴻運科': '', '永擎電子': '',
    // 面板／光學
    '友達': 'auo.com', '群創': 'innolux.com', '瑞儀光電': 'radiant.com.tw', '大立光': 'largan.com.tw',
    // 外商
    'AMD': 'amd.com', 'Apple': 'apple.com', 'Dell': 'dell.com', 'Garmin': 'garmin.com', 'Google': 'google.com', 'HP': 'hp.com', 'Merck': 'merck.com', 'Meta': 'meta.com',
    'NVIDIA': 'nvidia.com', 'Synopsys': 'synopsys.com', 'Wipro': 'wipro.com', '博通': 'broadcom.com', '微軟': 'microsoft.com', '高通': 'qualcomm.com', 'AMI': 'ami.com',
    'SSMC（新加坡）': 'ssmc.com',
    // 其他
    '乾坤科技': 'cyntec.com', '四零四科技（Moxa）': 'moxa.com', '新盛力科技': '', '裕隆': 'yulon-motor.com.tw', '鴻華先進': 'foxtron.com', '瑞力登 Raritan': 'raritan.com',
    '碩貝德': '', '科傳': '', '馳諾瓦': '', 'Unabiz': 'unabiz.com', '虹堡': 'castlestech.com', '雃博': 'apexmedical.com.tw', '新代': 'syntecclub.com',
    '立元科技': '', '車美仕': '', '連宇': ''
  };
  // 產業色：與圖表分類色同系，字標底色用
  const IC = { foundry: '#3ee0ff', memory: '#8b7bff', osat: '#ffb454', material: '#2ec4b6', equipment: '#ff7a45', icdesign: '#4d8dff', odm: '#c3ff5b', panel: '#e56bd0', foreign: '#9aa7b8', other: '#7c8aa0' };
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function domain(name) { return D[name] || ''; }
  /* 回傳 HTML 字串：字標先畫在底層，有網域才疊 <img>，img 失敗由下面的全域 error 監聽移除，字標自然露出 */
  function html(name, ind, size) {
    const col = IC[ind] || IC.other, ch = Array.from(String(name || '?'))[0] || '?', dm = domain(name), sz = size || 24;
    return '<span class="tc-lg" data-lg="' + (dm ? 'img' : 'txt') + '" style="--lg:' + col + ';--lz:' + sz + 'px"><i>' + esc(ch) + '</i>' +
      (dm ? '<img src="https://www.google.com/s2/favicons?domain=' + encodeURIComponent(dm) + '&sz=64" alt="' + esc(name) + '" loading="lazy" referrerpolicy="no-referrer" width="' + sz + '" height="' + sz + '">' : '') + '</span>';
  }
  // error 不冒泡，用捕獲階段接；失敗就拔掉圖，露出下面的字標
  // 圖載好才蓋上字標；Google 對查不到的網域回 16px 預設圖示（真圖是 64px），那種視同失敗，露出字標
  document.addEventListener('load', (e) => {
    const t = e.target; if (!(t && t.tagName === 'IMG' && t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('tc-lg'))) return;
    if (t.naturalWidth && t.naturalWidth < 32) { t.parentNode.dataset.lg = 'txt'; t.remove(); } else t.classList.add('ok');
  }, true);
  document.addEventListener('error', (e) => {
    const t = e.target; if (t && t.tagName === 'IMG' && t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('tc-lg')) { t.parentNode.dataset.lg = 'txt'; t.remove(); }
  }, true);
  window.TcLogo = { html, domain, color: (ind) => IC[ind] || IC.other, map: D };
})();
