/* ============================================================================
   法律頁、同意橫幅、平台導覽、頁尾免責聲明（設計系統 v2 第 6 批）
   規格：docs/design_system_v2.md ④（4.1 橫幅、4.2 導覽、4.3 法律頁）
   文字：docs/compliance_and_tiers.md ③ 的草稿（3-1 版本 A／B、3-2、3-3）—— **一個字都不從別的網站抄**。

   為什麼整塊放在一支新檔：
     同一時間有別的 agent 在改 app.js／industry.js 的結構與 index.html 的淺色主題 CSS。
     這裡的 CSS 由本檔自己注入、DOM 由本檔自己建，對既有檔的改動只剩
     index.html 兩行 <script>、app.js route() 裡一段掛勾。撞檔的面積降到最小。

   開關在 site/legal_config.js（window.TW_LEGAL）：
     · 頁尾那一行短版免責聲明 —— **永遠開著**（版本 A 沒有空格，規格說可以先上）。
       2026-09-24 第二版：上面多一行「© 年 站名 · 保留所有權利」，右邊一顆「顯示詳細規範」膠囊鈕，
       展開是 8 格詳細規範（預設收起；2026-10-06 起重新整理、換頁一律回收起，不再記 tw.footDetail）。
     · 三個法律頁 —— 永遠打得開；條款還有空格時，服務條款與隱私權政策頂端掛「草稿，尚未生效」。
     · 同意橫幅、平台導覽自動彈出 —— 只有「必填全部填好、條款全文掃不到【】、enabled:true」才啟用。
   ========================================================================== */
(function () {
  'use strict';

  /* ★ 2026-10-07：名稱與客服信箱還沒定 —— 定了只改這兩行。*/
  const SITE_NAME = '本網站';
  const CONTACT_EMAIL = 'kcq01010909@gmail.com';
  const UPDATED = '2026-10-07';

  /* 驗收腳本用 add_init_script 注入 window.TW_LEGAL_OVERRIDE 來模擬「已經填好」的狀態。
     這不是後門：同意狀態本來就只存在使用者自己的瀏覽器，他要偽造也只是騙他自己。*/
  const CFG = Object.assign({}, window.TW_LEGAL || {}, window.TW_LEGAL_OVERRIDE || {});
  const REQUIRED = ['operator', 'email', 'effective_date', 'tax_id', 'court'];
  const LABEL = {
    operator: '營業人名稱／個人姓名', email: '聯絡 email', effective_date: 'YYYY-MM-DD',
    updated_date: 'YYYY-MM-DD', tax_id: '統編，未辦稅籍登記者填「尚未辦理」', court: '○○地方法院',
    copyright_holder: '著作權人', site_name: '網站名稱', repo_url: 'repo 網址', hosting: '雲端服務提供者',
  };
  const TOUR_V = '2026-09-24';           // 導覽內容改版就改這個字串，所有人會再自動看到一次
  const K_CONSENT = 'tw.consent', K_TOUR = 'tw.tour';

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  /* 「空」的定義：沒填、只有空白、或還留著【】（有人把草稿的空格原樣貼進設定檔）。*/
  const isBlank = (v) => v == null || !String(v).trim() || /[【】]/.test(String(v));
  const fallback = { updated_date: () => CFG.effective_date, copyright_holder: () => CFG.operator };
  function val(k) {
    if (!isBlank(CFG[k])) return String(CFG[k]).trim();
    if (fallback[k] && !isBlank(fallback[k]())) return String(fallback[k]()).trim();
    return null;
  }
  /* 把 {key} 換成設定值；沒填的換成醒目的【】空格 —— 草稿狀態下讀者一眼看得出哪裡還沒定。*/
  function fill(s) {
    return s.replace(/\{(\w+)\}/g, (m, k) => {
      const v = val(k);
      if (v == null) return '<mark class="lgblank">【' + esc(LABEL[k] || k) + '】</mark>';
      if (k === 'email') return '<a href="mailto:' + esc(v) + '">' + esc(v) + '</a>';
      if (k === 'repo_url' || k === 'license_url') return '<a href="' + esc(v) + '" target="_blank" rel="noopener">' + esc(v) + '</a>';
      return esc(v);
    });
  }
  const ol = (items) => '<ol>' + items.filter(Boolean).map((x) => '<li>' + x + '</li>').join('') + '</ol>';
  const ul = (items) => '<ul>' + items.filter(Boolean).map((x) => '<li>' + x + '</li>').join('') + '</ul>';
  const CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二'];

  // ------------------------------------------------------------------ 條款內容
  /* ★ 2026-10-07 Andy：「依據參考網站撰寫對應基本事項，盡量屬於通用行文案，因為我還沒想好名稱」。
     · 章節結構參考台灣同類網站常見的涵蓋事項；**文字全部本站自寫，沒有逐字取自任何網站**。
     · 名稱一律走 SITE_NAME（預設「本網站」），聯絡信箱走 CONTACT_EMAIL —— 定了名稱／客服信箱只改檔頭這兩行。
     · 隱私權政策每一項都對到實際做法：workers/account-api/worker.js 檔頭「蒐集與保存」、sub-v1 區塊、admin-v3 區塊、
       site/account.js 的告知文字。改那邊要一起改這裡（DECISIONS #270-7 三處同步）。
     · 這不是律師擬的定稿：退款、試用、管轄法院、責任上限等標了「以購買頁所示為準」或待專業人士確認。*/
  const SN = SITE_NAME;
  const MAIL = '<a href="mailto:' + esc(CONTACT_EMAIL) + '">' + esc(CONTACT_EMAIL) + '</a>';
  const OP = SN + '營運者';

  function disclaimerDoc() {
    return {
      id: 'disclaimer', title: '免責聲明', short: '免責聲明', dated: true, lead:
        '<p>使用' + esc(SN) + '前，請詳細閱讀本聲明。您開始瀏覽或使用' + esc(SN) + '，即表示您已閱讀並瞭解本聲明之內容。</p>',
      secs: [
        { h: '網站性質', b: ol([
          esc(SN) + '是<b>公開資料之整理、計算與視覺化工具</b>，提供族群資金流向、估值、技術指標、事件與產業鏈等資訊之呈現。',
          '<b>' + esc(OP) + '不是證券投資顧問事業、證券投資信託事業或證券商</b>，未取得金融監督管理委員會之相關許可。',
          esc(SN) + '<b>不提供投資建議、不推介任何有價證券、不代客操作、不代為保管資金或有價證券、不招攬投資</b>。',
          '付費方案所提供者為<b>工具與功能之使用權</b>，<b>不是投資建議或個股推介之對價</b>。',
        ]) },
        { h: '資料來源與正確性', b: ol([
          '站內資料主要取自臺灣證券交易所、證券櫃檯買賣中心、臺灣集中保管結算所之公開資料，以及其他公開或第三方資料來源。原始資料之權利屬於各來源機構。',
          '資料可能因來源更正、傳輸、轉換或計算而<b>有錯誤、遺漏或延遲</b>。盤中數字為估算或代理值，<b>以各交易所與發行公司之正式公告為準</b>。',
          '<b>' + esc(OP) + '不擔保資料之正確性、完整性、即時性或適用於特定目的。</b>',
        ]) },
        { h: '不構成投資建議', b: ol([
          '站內之數值、評分、排行、條件篩選結果、圖表、文字說明與自動產生之摘要，均為<b>依公開資料與預先設定之方法計算之結果</b>，僅供研究與參考。',
          '這些內容<b>不構成任何買賣要約、要約之引誘、推介或獲利保證</b>。條件篩選清單不是推薦名單；圖上之價位參數是計算條件，不是建議之買進、賣出或停損價位。',
          '您在做任何投資決定前，應自行查證並審慎評估，必要時諮詢合格之專業人士。',
        ]) },
        { h: '計算方法與回測限制', b: ol([
          '各項指標之計算方法可能隨資料來源或設計調整而變更，恕不另行個別通知。',
          '任何歷史統計、季節性或回測結果皆<b>不代表未來表現</b>；回測可能受資料期間、存活者偏差、交易成本與滑價等因素影響，未必能於實際交易中重現。',
        ]) },
        { h: '第三方連結與內容', b: '<p>' + esc(SN) + '可能包含第三方網站之連結，或引述第三方公開發布之新聞、公告與資料。該等內容由第三方負責，'
          + '<b>' + esc(OP) + '不保證其正確性，亦不代表同意或推薦其觀點</b>。您前往第三方網站時，應適用該網站之條款與政策。</p>' },
        { h: '投資風險自負', b: '<p>投資有風險，市場價格可能劇烈波動，您可能損失部分或全部本金。<b>任何投資決策由您自行判斷，其結果與風險由您自行承擔。</b>'
          + '在法律允許之範圍內，' + esc(OP) + '對您因使用或信賴本網站資訊所生之任何直接或間接損失，不負賠償責任；但因故意或重大過失所致者，不在此限。</p>' },
        { h: '法規變動', b: '<p>' + esc(SN) + '之服務內容將隨相關法令及主管機關之規定調整。若法令變更致部分功能不得提供或須改變提供方式，'
          + esc(OP) + '得逕行調整、暫停或終止該功能，並於網站公告。</p>' },
        { h: '聯絡方式', b: '<p>對本聲明有任何疑問，請來信 ' + MAIL + '。</p>' },
      ],
    };
  }

  function termsDoc() {
    return {
      id: 'terms', title: '使用條款', short: '使用條款', dated: true,
      lead: '<p>歡迎使用' + esc(SN) + '（以下稱「本服務」）。本條款是您與' + esc(OP) + '之間關於使用本服務之約定。'
        + '<b>您開始使用本服務，即表示您已閱讀、瞭解並同意本條款、<a href="#privacy">隱私權政策</a>及<a href="#disclaimer">免責聲明</a>之全部內容。</b>如您不同意，請停止使用。</p>',
      secs: [
        { h: '服務內容', b: ol([
          '本服務提供台股公開資料之整理、計算與視覺化工具，包含但不限於族群資金流向、估值、技術指標、事件、產業鏈、自選清單等功能。',
          '本服務為資訊與工具，<b>不構成投資建議、不推介個股、不代客操作</b>；詳見<a href="#disclaimer">免責聲明</a>。',
          '各功能之內容、開放範圍與每日使用次數，依您所屬之方案（訪客、免費會員、付費會員）而有不同，以網站所示為準。',
        ]) },
        { h: '帳號註冊與登入', b: ol([
          '本服務以 <b>Google 帳號登入</b>建立會員帳號。本服務不取得、不保存您的 Google 密碼。',
          '您應妥善保管您的 Google 帳號與裝置；以您帳號進行之一切行為，推定為您本人所為。發現帳號遭冒用時，請立即來信通知。',
          '您得隨時停止使用並申請刪除帳號（見<a href="#privacy">隱私權政策</a>「您的權利」）。',
        ]) },
        { h: '會員方案、試用與付費', b: ol([
          '本服務得提供<b>免費試用（目前規劃為 1 個月）</b>；試用之資格、期間、次數與結束後之處理，<b>以購買頁所示為準</b>。',
          '付費方案之價格、計費週期、付款方式與包含之功能，<b>以購買頁所示為準</b>。付費取得者為<b>本服務工具與功能之使用權</b>，不是投資建議或個股推介之對價。',
          '<b>續訂</b>：若方案為自動續訂，將於每一計費週期屆滿時依原方案續扣；購買頁另有說明者，從其說明。',
          '<b>取消</b>：您得隨時取消續訂；取消後，已付費之期間仍可使用至期滿。',
          '<b>退款</b>：退款條件與計算方式<b>以購買頁所示為準</b>；購買頁未載明者，依消費者保護法及相關法令辦理。',
          '方案到期未續訂者，帳號自動回到免費會員，您的自選清單等資料不因此刪除。',
        ]) },
        { h: '禁止行為', b: '<p>使用本服務時，您不得有下列行為：</p>' + ol([
          '以程式、爬蟲或其他自動化方式大量擷取本服務之內容或資料。',
          '未經書面授權，將本服務之資料、圖表或內容<b>轉售、出租、再散布或作為商業用途</b>。',
          '<b>將帳號提供他人共用</b>、轉讓或出借。',
          '對本服務進行<b>逆向工程</b>、反編譯，或嘗試取得原始碼與未公開之介面。',
          '<b>以任何方式繞過付費機制</b>、使用次數限制或存取控制。',
          '干擾或破壞本服務之正常運作，或利用本服務從事違法行為（例如操縱市場、散布不實資訊、未經許可經營證券投資顧問業務）。',
        ]) },
        { h: '裝置數上限與異常使用', b: ol([
          '為防止帳號共用，本服務得限制<b>每一帳號可使用之裝置數</b>；上限以網站公告為準。',
          '本服務偵測到異常使用（例如短時間大量存取、多處同時使用、自動化擷取）時，得先行限制存取或<b>暫停帳號</b>。',
          '經查證確有違反本條款者，' + esc(OP) + '得終止您的帳號；您如認為有誤，得來信說明，' + esc(OP) + '將重新審視。',
        ]) },
        { h: '智慧財產權', b: ol([
          '本服務之原創圖形、族群與供應鏈分類、版面設計、文字與程式，其權利屬於' + esc(OP) + '或其授權人。',
          '原始資料之權利屬於各原始來源機構，本服務僅為整理與呈現。',
          '您得為個人非商業目的閱覽、截圖與引用本服務內容，並應標註來源；其他利用須事先取得書面授權。',
        ]) },
        { h: '服務變更與中斷', b: ol([
          esc(OP) + '得因維護、資料來源變更、法令調整或第三方服務（例如雲端主機、資料來源）中斷等原因，變更、暫停或終止部分或全部服務。',
          '本服務不保證不中斷或無錯誤。涉及付費會員權益之重大變更，將事先於網站公告或以電子郵件通知。',
        ]) },
        { h: '責任限制', b: ol([
          '在法律允許之最大範圍內，' + esc(OP) + '對您因使用或無法使用本服務所生之任何損失（包括投資損失、利潤損失、資料損失）不負賠償責任。',
          '本條不免除' + esc(OP) + '因故意或重大過失所應負之責任。',
          '依法仍應負賠償責任者，賠償總額以您於事由發生前十二個月內實際支付予本服務之費用為上限。',
        ]) },
        { h: '條款修改', b: '<p>' + esc(OP) + '得修改本條款，修改後於本頁公告並更新「最後更新日期」。您於修改後繼續使用本服務，視為同意修改後之條款；'
          + '如不同意，請停止使用並得依第三條取消續訂。</p>' },
        { h: '準據法與管轄法院', b: '<p>本條款以<b>中華民國法律</b>為準據法。因本條款所生之爭議，雙方同意以<b>臺灣臺北地方法院</b>為第一審管轄法院；'
          + '但不影響您依消費者保護法所得主張之權利。</p>' },
        { h: '聯絡方式', b: '<p>客服與各項申請，請來信 ' + MAIL + '。</p>' },
      ],
    };
  }

  function privacyDoc() {
    const rows = [
      ['瀏覽本網站（未登入）', '不蒐集可識別您身分之資料。僅計入不具名之使用統計與線上人數（見下列）', '—', '—'],
      ['Google 帳號登入', '<b>Google 帳號之顯示名稱、電子郵件地址、大頭貼網址</b>；Google 帳號識別碼僅保存其雜湊值；帳號建立與最後使用時間。不取得密碼，不讀取 Gmail、雲端硬碟或聯絡人',
        '身分識別、提供會員功能與自選清單同步、客服聯繫', '至您申請刪除為止；<b>連續 24 個月未使用自動刪除</b>'],
      ['自選清單', '您自行建立之清單名稱與股票代號（<b>不含張數、成本、損益</b>）', '跨裝置同步', '至您刪除清單或帳號為止'],
      ['方案與到期日', '管理者為您的電子郵件地址設定之<b>方案、功能開關與到期日</b>', '決定帳號可使用之功能', '至管理者移除設定或您刪除帳號為止'],
      ['使用紀錄（登入者）', '每日造訪次數、在線時間、各頁面瀏覽與各功能使用次數、所看之股票代號與族群名稱；每日各功能瀏覽次數。<b>不含您輸入之文字、不記錄 IP</b>',
        '計算每日使用次數上限、改善服務與方案設計；管理者得檢視', '明細 <b>90 天</b>；每日瀏覽次數 3 天；造訪與在線時間 13 個月；刪除帳號時一併刪除'],
      ['使用統計（所有訪客）', '<b>不含身分</b>之彙總次數：每日各頁面、各功能、各選項之使用次數。不記錄 IP、不含識別碼；瀏覽器開啟「請勿追蹤」（DNT）或「全球隱私控制」（GPC）時不傳送',
        '瞭解功能使用情形以改善服務', '<b>13 個月</b>'],
      ['在線狀態（所有訪客）', '每次開啟頁面產生之<b>隨機代碼</b>與目前所在頁面；登入者另關聯其帳號', '計算線上人數；管理者得檢視目前在線之登入者名稱與所在頁面',
        '關閉分頁即刪除；<b>無訊號最遲 7 分鐘刪除</b>'],
      ['意見反饋與訂閱申請', '您主動填寫之聯絡電子郵件、類別、內容，以及當時網址與瀏覽器資訊；登入者另關聯其帳號', '回覆與處理您的意見或申請', '<b>13 個月</b>；刪除帳號時一併刪除'],
      ['公告已讀紀錄', '登入者讀過哪幾則公告', '跨裝置顯示未讀公告', '公告刪除或帳號刪除時一併刪除'],
    ];
    const table = '<div class="lgtbl"><table><thead><tr><th>情境</th><th>蒐集之資料</th><th>目的</th><th>保存期間</th></tr></thead><tbody>'
      + rows.map((r) => '<tr>' + r.map((c) => '<td>' + c + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
    return {
      id: 'privacy', title: '隱私權政策', short: '隱私權政策', dated: true,
      lead: '<p>' + esc(OP) + '重視您的隱私。本政策說明' + esc(SN) + '蒐集哪些資料、如何利用與保護，以及您依個人資料保護法享有之權利。</p>',
      secs: [
        { h: '蒐集之資料、目的與保存期間', b: table
          + '<p>為防止濫用，伺服器會暫時於記憶體中依連線 IP 計算請求次數，<b>不寫入資料庫</b>。</p>'
          + '<p><b>本網站不蒐集</b>：身分證字號、電話、地址、出生日期、<b>您的實際持股、成本價、損益或券商帳號</b>，也請您不要提供。</p>' },
        { h: '資料之利用與分享對象', b: ul([
          '僅於上表所列目的範圍內利用。<b>不販售、不出租、不交換您的個人資料，也不用於廣告追蹤。</b>',
          '為提供服務所必要，資料由下列服務供應商代為處理或傳輸：<b>Google</b>（驗證登入身分；會員大頭貼由 Google 伺服器提供）、'
            + '<b>Cloudflare</b>（會員資料、自選清單、使用統計與線上狀態之儲存與運算；盤中報價轉送）、<b>GitHub</b>（網站主機）。日後新增金流等服務商時，將於本頁更新。',
          '法令要求或司法、主管機關依法調取時，依法提供。',
          '利用地區：中華民國及上述服務供應商之伺服器所在地（可能位於境外）。',
        ]) },
        { h: 'Cookie 與本機儲存', b: ul([
          '本網站<b>不使用 Cookie 進行追蹤</b>，不裝設廣告追蹤器。僅在 Google 登入過程中，登入伺服器會設定一個<b>有效 10 分鐘</b>、用於防止偽造登入之暫時 Cookie。',
          '您的介面偏好（版面、主題、圖表設定等）存於瀏覽器之 <code>localStorage</code>，只存在您的裝置，不傳回伺服器。',
          '登入後，登入憑證與自選清單之本機副本亦存於 <code>localStorage</code>；自選清單會同步至伺服器。',
          '「每個分頁只計一次造訪」之標記存於 <code>sessionStorage</code>，關閉分頁即清除。',
          '您可隨時於瀏覽器清除上述資料；清除後需重新登入。',
        ]) },
        { h: '您的權利', b: '<p>依個人資料保護法第 3 條，您得就您的個人資料請求：<b>查詢或請求閱覽、製給複製本、補充或更正、停止蒐集處理或利用、刪除</b>。</p>'
          + '<p>請以您登入所用之電子郵件來信 ' + MAIL + ' 提出，' + esc(OP) + '將於收到後<b>十五日內</b>處理並回覆；刪除範圍包含會員資料、雲端自選清單、使用紀錄、反饋與申請紀錄、線上狀態。'
          + '不具名之彙總使用統計無從對應至個人，故無個人部分可刪除。</p>'
          + '<p>您得自由選擇是否提供個人資料；不登入者仍可使用開放給訪客之功能，但無法使用自選清單同步等會員功能。</p>' },
        { h: '資料安全', b: '<p>' + esc(SN) + '採取合理之技術與管理措施保護您的資料，包括：HTTPS 加密傳輸、Google 登入採 OAuth 2.0 授權碼與 PKCE 機制、'
          + 'Google 帳號識別碼僅存雜湊值、登入權杖經簽章並設有效期限（刪除帳號後立即失效）、管理功能僅限經驗證之管理者存取、過期資料定時自動刪除。</p>'
          + '<p>惟網際網路傳輸無法保證絕對安全。如發生個人資料外洩，將依個人資料保護法第 12 條，查明後以適當方式通知您。</p>' },
        { h: '未成年人', b: '<p>未滿十八歲者，應於法定代理人閱讀、瞭解並同意本政策及<a href="#terms">使用條款</a>後，方得使用本服務；購買付費方案應經法定代理人同意。</p>' },
        { h: '政策修改', b: '<p>本政策修改時，將於本頁公告並更新「最後更新日期」；涉及蒐集目的變更者，將另行取得您的同意。</p>' },
        { h: '聯絡方式', b: '<p>隱私相關問題與權利行使，請來信 ' + MAIL + '。</p>' },
      ],
    };
  }

  const DOCS = { terms: termsDoc, privacy: privacyDoc, disclaimer: disclaimerDoc };

  /* 草稿有沒有填完：必填全部有值，**而且**畫出來的兩份條款全文找不到任何【】。
     第二道是保險 —— 旗標打開（付費、電子報…）會帶出新的空格，那些不在 REQUIRED 裡。*/
  function missing() {
    const miss = REQUIRED.filter((k) => val(k) == null).map((k) => k);
    const txt = [termsDoc(), privacyDoc()].map((d) => d.title + d.lead + d.secs.map((s) => s.b).join('')).join('');
    const holes = (txt.match(/【[^】]*】/g) || []).filter((x, i, a) => a.indexOf(x) === i);
    return { fields: miss, holes };
  }
  function filled() { const m = missing(); return !m.fields.length && !m.holes.length; }
  /* 正式啟用＝草稿填完 ＋ 總開關打開。兩個條件缺一不可：填完了但 Andy 還沒說要上，也不啟用。*/
  function active() { return CFG.enabled === true && filled(); }
  const version = () => val('effective_date') || '';

  // ------------------------------------------------------------------ 同意狀態
  /* 規格 4.1：
     · 讀的時候丟錯 → 當作沒同意過（顯示橫幅）。
     · 寫的時候丟錯 → 記在記憶體，這次瀏覽不再出現；重新整理會再出現一次（這樣是對的）。
     · **不記住「不同意」**：什麼都不寫。記住的唯一效果是讓按錯的人回不來，而且那本身就是一筆蒐集。
     · 不用 cookie 補位：隱私權政策寫著「不使用 Cookie 進行追蹤」，用 cookie 會讓那句話需要解釋。*/
  let memConsent = false, declined = false, storeOK = true;
  function readConsent() {
    if (memConsent) return true;
    try {
      const raw = localStorage.getItem(K_CONSENT);
      if (!raw) return false;
      const o = JSON.parse(raw);
      /* `v:'*'` 是驗收腳本預寫的（_uitest／_preview／_show 的 add_init_script），
         意思是「這個瀏覽器不必再看到橫幅」。不這樣做，一旦啟用，所有關卡會被橫幅擋住點擊而一起紅。*/
      return !!o && (o.v === '*' || o.v === version());
    } catch (e) { return false; }
  }
  function writeConsent() {
    memConsent = true;
    try { localStorage.setItem(K_CONSENT, JSON.stringify({ v: version(), at: new Date().toISOString() })); storeOK = true; }
    catch (e) { storeOK = false; }
  }
  function tourSeen() {
    try { return localStorage.getItem(K_TOUR) != null; } catch (e) { return null; }   // null＝讀不到
  }
  function markTour() { try { localStorage.setItem(K_TOUR, TOUR_V); } catch (e) { /* 忽略 */ } }

  // ------------------------------------------------------------------ 樣式
  /* 全部用站上既有的 token（--panel／--ink／--cyan…），深淺兩主題自動跟著換。
     字級下限 12px（全站硬規矩）。*/
  const CSS = `
/* ★ 2026-09-26（Andy：「下面填滿版面 需要調整適當大小」）：改前 max-width:1200px＋margin auto 置中，
   1440 寬時兩側各空 100 多 px、跟上面全寬的內容卡左右對不齊。改後不設上限、左右邊界＝main 的內距
   （跟每一頁 .view 裡的卡片同一條線）；八格依 footer 自己的寬度 4／2／1 欄（下面的 @container sfoot）。*/
.sitefoot{max-width:none;margin:32px 0 0;padding:24px 0;border-top:1px solid var(--line);
  font-size:12px;line-height:1.7;color:var(--ink-3);container:sfoot/inline-size}
.sitefoot p{margin:0}
.sitefoot b{color:var(--ink-2);font-weight:600}
/* 上半部：左邊是版權＋短版免責＋連結列（寬度收在約 2/3，長句才不會拉成一整條難讀的線），右邊是「詳細規範」開關 */
.sitefoot .sf-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px 24px}
/* 左欄文字上限跟著變寬（760 → 1040）：footer 全寬之後 760 會在中間留一大塊空白；1040 在 12px 下約 85 字一行，還讀得動。*/
.sitefoot .sf-main{flex:1 1 auto;min-width:0;max-width:1040px}
.sitefoot .sf-copy{color:var(--ink-2);margin-bottom:4px}
.sitefoot .sf-links{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:8px}
.sitefoot .sf-links a,.sitefoot .sf-links button{font:inherit;font-size:12px;color:var(--cyan);background:none;border:0;padding:0;
  cursor:pointer;text-decoration:none}
.sitefoot .sf-links a:hover,.sitefoot .sf-links button:hover{text-decoration:underline}
.sitefoot .sf-links em{font-style:normal;color:var(--ink-3)}
.sf-more{flex:none;display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 12px 0 14px;border-radius:999px;
  border:1px solid var(--line-2);background:var(--panel);color:var(--ink-2);font:inherit;font-size:12px;font-weight:600;
  cursor:pointer;white-space:nowrap}
.sf-more:hover{border-color:var(--cyan);color:var(--ink)}
.sf-more:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.sf-more svg{width:12px;height:12px;transition:transform .18s}
.sf-more[aria-expanded="true"] svg{transform:rotate(180deg)}
/* ⚠ 一定要寫 [hidden] 規則：下面 .sf-detail 有自己的 display，權重會蓋過瀏覽器內建的 [hidden]{display:none}
   （2026-09-24 手機分段列「hidden 完全沒生效」就是這樣踩到的）。*/
.sf-detail[hidden]{display:none!important}
.sf-detail{display:block;margin-top:16px;background:var(--panel-2);border:1px solid var(--line);border-radius:16px;padding:20px 24px}
.sf-grid{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px 24px}
.sf-item{display:grid;grid-template-columns:18px minmax(0,1fr);gap:10px;align-items:start}
.sf-item svg{width:18px;height:18px;color:var(--cyan);margin-top:1px}
.sf-item b{display:block;font-size:13px;font-weight:700;color:var(--ink);line-height:1.5}
.sf-item p{font-size:12px;line-height:1.6;color:var(--ink-3);margin-top:2px}
@container sfoot (max-width:900px){ .sf-grid{grid-template-columns:repeat(2,minmax(0,1fr))} }
@container sfoot (max-width:560px){
  .sitefoot .sf-top{flex-direction:column}
  .sf-grid{grid-template-columns:minmax(0,1fr);gap:14px}
  .sf-detail{padding:16px}
}
@media (prefers-reduced-motion:reduce){ .sf-more svg{transition:none} }

#v-legal{container-type:inline-size}
/* 法律頁上方三顆膠囊分頁：目前頁實心主色、其他描邊。高 38、全圓角、間距 8；
   手機 390 三顆要一列放得下（13px 字：4＋5＋4 個字 ≈ 170px ＋ 內距 84 ＋ 間距 16 ≈ 270px < 358）。*/
.lgtabs{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 20px}
.lgtabs a{display:inline-flex;align-items:center;justify-content:center;height:38px;padding:0 18px;border-radius:999px;
  border:1px solid var(--line-2);background:var(--panel);color:var(--ink-2);font-size:14px;font-weight:500;
  text-decoration:none;white-space:nowrap;transition:border-color .15s,color .15s}
.lgtabs a:hover{border-color:var(--cyan);color:var(--ink)}
.lgtabs a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.lgtabs a.on{background:var(--cyan);color:var(--ontop);border-color:var(--cyan);font-weight:700}
@container (min-width:1000px){ .lgtabs{margin-left:244px} }   /* 跟右邊文件卡的左緣對齊（目錄 220 ＋ 間距 24）*/
@media (max-width:560px){
  .lgtabs{flex-wrap:nowrap;gap:8px}
  .lgtabs a{flex:1 1 auto;padding:0 12px;font-size:13px;height:36px}
}
.lgwrap{display:block}
.lgtoc{display:none}
.lgtocm{margin:0 0 16px;font-size:13px}
.lgtocm summary{cursor:pointer;color:var(--ink-2)}
.lgtocm ol,.lgtoc ol{list-style:none;margin:8px 0 0;padding:0}
.lgtocm a,.lgtoc a{display:block;padding:4px 10px;color:var(--ink-3);text-decoration:none;border-left:2px solid transparent;font-size:13px}
.lgtoc a.on{color:var(--cyan);border-left-color:var(--cyan)}
@container (min-width:1000px){
  .lgwrap{display:grid;grid-template-columns:220px minmax(0,760px);gap:24px;align-items:start}
  .lgtoc{display:block;position:sticky;top:80px;font-size:13px}
  .lgtocm{display:none}
}
.lgdoc{width:min(760px,100%);background:var(--panel);border:1px solid var(--line);border-radius:24px;padding:40px;
  font-size:14px;line-height:1.8;color:var(--ink-2)}
.lgdoc h1{font-size:22px;font-weight:700;color:var(--ink);margin:0 0 6px;line-height:1.4}
.lgdoc .lgmeta{font-size:13px;color:var(--ink-3);margin:0 0 4px}
.lgdoc h2{font-size:17px;font-weight:700;color:var(--ink);margin:32px 0 8px;scroll-margin-top:80px}
.lgdoc p,.lgdoc ol,.lgdoc ul{margin:8px 0;max-width:68ch}
.lgdoc ol,.lgdoc ul{padding-left:1.6em}
.lgdoc li{margin:4px 0}
.lgdoc b{color:var(--ink);font-weight:700}
.lgdoc a{color:var(--cyan)}
.lgdoc code{font-family:var(--mono);font-size:13px}
.lgblank{background:color-mix(in srgb,var(--amber) 22%,transparent);color:var(--ink);border-radius:4px;padding:0 3px}
.lgdraft{border:1px solid var(--amber);background:color-mix(in srgb,var(--amber) 12%,var(--panel));color:var(--ink);
  border-radius:16px;padding:12px 16px;margin:0 0 20px;font-size:13px;line-height:1.7}
.lgdraft b{color:var(--amber)}
.lgtbl{overflow-x:auto;margin:8px 0}
.lgtbl table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.6}
.lgtbl th,.lgtbl td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top;white-space:normal;word-break:break-word}
.lgtbl td:first-child,.lgtbl th:first-child{width:7em}
.lgtbl th{background:var(--panel-3);color:var(--ink);font-weight:700}

.lgleave{width:min(560px,100%);margin:48px auto;background:var(--panel);border:1px solid var(--line);border-radius:24px;
  padding:32px;font-size:14px;line-height:1.8;color:var(--ink-2)}
.lgleave h1{font-size:18px;color:var(--ink);margin:0 0 8px}
.lgleave .lgbtns{margin-top:24px}

.lgbtns{display:flex;gap:12px;flex-wrap:wrap}
.lgb1,.lgb2{height:44px;padding:0 20px;border-radius:999px;font:inherit;font-size:14px;font-weight:600;cursor:pointer}
.lgb1{background:var(--cyan);color:var(--ontop);border:0}
.lgb2{background:var(--panel);color:var(--ink);border:1px solid var(--line-2)}
.lgb1:focus-visible,.lgb2:focus-visible,.lgx:focus-visible,.lgtx:focus-visible{outline:2px solid var(--focus);outline-offset:2px}

.lgban{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);width:min(1024px,calc(100vw - 48px));z-index:90;
  display:flex;align-items:center;gap:24px;padding:24px 32px;border-radius:24px;border:1px solid var(--line);
  background:rgba(20,30,54,.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  box-shadow:0 12px 32px -12px rgba(0,0,0,.25);font-size:13px;line-height:1.6;color:var(--ink-3);
  animation:lgUp .24s var(--ease,ease) both}
:root[data-theme="light"] .lgban{background:rgba(250,249,246,.92)}
.lgban p{margin:0;flex:1}
.lgban a{color:var(--cyan);text-decoration:none}
.lgban a:hover{text-decoration:underline}
.lgban .lgbtns{flex:none;flex-wrap:nowrap}
.lgban.out{animation:lgDown .18s ease both}
@keyframes lgUp{from{transform:translate(-50%,24px);opacity:0}to{transform:translate(-50%,0);opacity:1}}
@keyframes lgDown{to{transform:translate(-50%,24px);opacity:0}}
@media (max-width:820px){
  .lgban{left:12px;right:12px;width:auto;transform:none;bottom:calc(var(--mnav-h,102px) + 12px);border-radius:20px;
    padding:20px;flex-direction:column;align-items:stretch;gap:14px;animation-name:lgUpM}
  .lgban.out{animation-name:lgDownM}
  .lgban .lgbtns{flex-direction:column-reverse}
  .lgban .lgb1,.lgban .lgb2{width:100%}
  .lgdoc{padding:20px;border-radius:20px}
}
@keyframes lgUpM{from{transform:translateY(24px);opacity:0}to{transform:none;opacity:1}}
@keyframes lgDownM{to{transform:translateY(24px);opacity:0}}

.lgmask{position:fixed;inset:0;z-index:95;background:rgba(7,11,22,.45);backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
  display:flex;align-items:center;justify-content:center;padding:24px}
.lgtour{width:min(600px,100%);max-height:calc(100vh - 48px);overflow:auto;background:var(--panel);border:1px solid var(--line);
  border-radius:24px;padding:32px;box-shadow:0 24px 64px -16px rgba(0,0,0,.35);color:var(--ink-2);font-size:14px;line-height:1.7;
  animation:lgIn .18s var(--ease,ease) both}
@keyframes lgIn{from{transform:translateY(8px);opacity:0}to{transform:none;opacity:1}}
.lgth{display:flex;align-items:center;gap:12px}
.lgic{width:44px;height:44px;border-radius:50%;flex:none;display:grid;place-items:center;font-size:18px;color:var(--cyan);
  background:color-mix(in srgb,var(--cyan) 12%,transparent)}
.lgth h2{margin:0;font-size:13px;font-weight:600;color:var(--cyan);outline:none}
.lgth small{display:block;font-size:13px;color:var(--ink-3)}
.lgx{margin-left:auto;align-self:flex-start;background:none;border:0;color:var(--ink-3);font-size:20px;line-height:1;cursor:pointer;
  width:32px;height:32px;border-radius:50%}
.lgx:hover{background:var(--panel-3);color:var(--ink)}
.lgtour h3{font-size:18px;font-weight:700;color:var(--ink);margin:24px 0 6px}
.lgtour p{margin:0}
.lgcards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:24px}
.lgcard{background:var(--panel-3);border:1px solid var(--line);border-radius:16px;padding:16px;font-size:13px;line-height:20px;color:var(--ink-3)}
.lgcard b{display:block;font-size:13px;font-weight:700;color:var(--ink);margin-bottom:4px}
.lgstep{background:var(--panel-3);border-radius:20px;padding:16px;margin-top:24px;animation:lgFade .12s ease both}
@keyframes lgFade{from{opacity:0}to{opacity:1}}
.lgstep .lgsn{font-size:13px;color:var(--ink-3)}
.lgstep .lgst{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600;color:var(--ink);margin-top:6px}
.lgstep .lgst i{width:16px;height:16px;border-radius:50%;background:var(--cyan);color:var(--ontop);font-style:normal;font-size:12px;
  display:grid;place-items:center;flex:none}
.lgstep .lgsd{font-size:13px;line-height:20px;color:var(--ink-2);margin-top:4px;padding-left:24px}
.lggo{display:inline-block;margin-top:8px;font-size:13px;color:var(--cyan);background:none;border:0;padding:0;cursor:pointer;font:inherit;font-size:13px}
.lggo:hover{text-decoration:underline}
.lgdots{display:flex;gap:8px;margin-top:20px}
.lgdots i{width:6px;height:6px;border-radius:999px;background:var(--line-2);transition:width .18s}
.lgdots i.on{width:32px;background:var(--cyan)}
.lgtf{display:flex;align-items:center;justify-content:space-between;margin-top:32px}
.lgtx{background:none;border:0;color:var(--ink-3);font:inherit;font-size:13px;font-weight:600;cursor:pointer;padding:6px 0}
.lgtour .lgb1{height:40px;font-size:13px;font-weight:700}
.lgflash{outline:2px solid var(--focus)!important;outline-offset:3px;transition:outline-color .3s}
@media (max-width:600px){
  .lgmask{align-items:flex-end;padding:0}
  .lgtour{width:100%;border-radius:24px 24px 0 0;max-height:90vh;padding:24px 20px calc(20px + env(safe-area-inset-bottom))}
  .lgcards{grid-template-columns:1fr}
}
@media (prefers-reduced-motion:reduce){
  .lgban,.lgban.out,.lgtour,.lgstep{animation:none!important}
  .lgdots i{transition:none}
}`;
  function injectCSS() {
    if (document.getElementById('legalCss')) return;
    const st = document.createElement('style'); st.id = 'legalCss'; st.textContent = CSS;
    document.head.appendChild(st);
  }

  // ------------------------------------------------------------------ 頁尾
  /* 版本 A 的**短版**：意思一個不少（不是投顧、不建議不推介、僅供參考、可能有誤、風險自負），
     全文在 #disclaimer。這一行**預設開啟**，不看開關。*/
  /* 「詳細規範」八格：版面參考別的台股站的頁尾（小標＋一兩句），**文字全部是本站自己的事實**，沒有一句照抄。
     刻意不做的兩格（參考站有）：
       · 「上鏈績效認可」—— 本站沒有任何績效上鏈或第三方認證機制，寫了就是不實陳述。
       · 「最終解釋權歸本站所有」—— 對消費者不利的單方解釋條款，在消保法第 11、12 條下效力有疑義，
         而且跟服務條款第十條「不影響消費者依消保法所得主張之權利」自相矛盾。
     每格 ≤ 60 字；這裡**不准**出現【】空格（營業人名稱等還沒填，頁尾是永遠開著的）。*/
  const FOOT_ITEMS = [
    ['重要聲明', '本站不是證券投資顧問事業、證券經紀商或自營商，不提供投資顧問服務。'],
    ['非投資建議', '所有數值、排行、條件篩選結果僅供研究參考，不構成買賣建議或推介。'],
    ['投資風險警告', '投資有風險，市場價格可能劇烈波動，過去表現不代表未來結果。'],
    ['不代操／不託管／不招攬', '不代客操作、不代收代付、不保管資金或證券、不招攬投資。'],
    ['數據來源', '臺灣證券交易所、櫃買中心、集保結算所、FinMind 等公開資料；可能延遲、遺漏或錯誤。'],
    ['即時資料說明', '盤中數字為估算與代理值（例如成交值權重、代理大盤），以交易所正式公告為準。'],
    ['專業諮詢', '做投資決定前，建議諮詢合格的證券投資顧問或財務顧問。'],
    ['責任限制', '在法律允許的範圍內，使用本站資訊所生之任何損失，本站不負賠償責任。'],
  ];
  const K_FOOT = 'tw.footDetail';
  /* ⓘ：內嵌 SVG，顏色吃 currentColor（跟著主題 token 走），不用圖片也不用圖示庫。*/
  const ICON_I = '<svg viewBox="0 0 18 18" aria-hidden="true" focusable="false"><circle cx="9" cy="9" r="7.6" fill="none" '
    + 'stroke="currentColor" stroke-width="1.4"/><circle cx="9" cy="5.6" r="1" fill="currentColor"/>'
    + '<path d="M9 8.2v4.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  const CHEV = '<svg viewBox="0 0 12 12" aria-hidden="true" focusable="false"><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" '
    + 'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  /* ★ 2026-10-06 Andy：「每次重新整理、換頁面後 Default 都會是收合狀態」—— 詳細規範不再記住展開。
     以前寫 tw.footDetail 讓下次進來維持展開；現在一律收起，舊瀏覽器留下的值由 viewreset.js 清掉。*/
  function footOpenPref() { return false; }
  function setFootOpen(f, open, save) {
    const btn = f.querySelector('#sfMore'), box = f.querySelector('#sfDetail');
    box.hidden = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.querySelector('span').textContent = open ? '隱藏詳細規範' : '顯示詳細規範';
    void save; void K_FOOT;   // 不再寫入（見 footOpenPref 的說明）
  }

  function buildFooter() {
    const main = document.querySelector('main');
    if (!main || document.getElementById('siteFoot')) return;
    const year = isBlank(CFG.copyright_year) ? '2026' : String(CFG.copyright_year).trim();
    const f = document.createElement('footer');
    f.className = 'sitefoot'; f.id = 'siteFoot';
    f.innerHTML = '<div class="sf-top"><div class="sf-main">'
      + '<p class="sf-copy" id="sfCopy">© ' + esc(year) + ' ' + esc(SITE_NAME) + ' · 保留所有權利</p>'
      + '<p class="sf-dis"><b>免責聲明</b>　本站為公開資料之整理、計算與視覺化工具，不是證券投資顧問事業，'
      + '不提供投資建議、不推介任何有價證券；所有數值僅供研究參考，資料可能有誤、遺漏或延遲，'
      + '投資決策與風險由使用者自行判斷並承擔。</p>'
      + '<nav class="sf-links" aria-label="法律與說明">'
      + '<a href="#disclaimer" id="sfDis">免責聲明</a><em aria-hidden="true">｜</em>'
      + '<a href="#terms" id="sfTerms">使用條款</a><em aria-hidden="true">｜</em>'
      + '<a href="#privacy" id="sfPriv">隱私權政策</a>'
      + '<button type="button" id="sfTour">平台導覽</button>'
      /* 2026-10-07：「交付清單」資料已不發佈，入口從頁尾拿掉（#delivery 路由照舊）。*/
      + '</nav></div>'   // ★ 2026-09-24 Andy：原始碼不能公開 ——「原始碼與演算法」連結已拿掉
      + '<button type="button" class="sf-more" id="sfMore" aria-expanded="false" aria-controls="sfDetail">'
      + '<span>顯示詳細規範</span>' + CHEV + '</button></div>'
      + '<div class="sf-detail" id="sfDetail" role="region" aria-label="詳細規範" hidden><ul class="sf-grid">'
      + FOOT_ITEMS.map((x) => '<li class="sf-item">' + ICON_I + '<div><b>' + esc(x[0]) + '：</b><p>' + esc(x[1]) + '</p></div></li>').join('')
      + '</ul></div>';
    main.appendChild(f);
    f.querySelector('#sfTour').addEventListener('click', (e) => openTour(e.currentTarget));
    /* 預設收起；頁尾是整站共用、換頁不會重畫，所以要自己在換頁時收回去（2026-10-06）。*/
    setFootOpen(f, footOpenPref(), false);
    window.addEventListener('hashchange', () => setFootOpen(f, false, false));
    f.querySelector('#sfMore').addEventListener('click', () => {
      setFootOpen(f, f.querySelector('#sfDetail').hidden, true);
    });
  }

  // ------------------------------------------------------------------ 法律頁 view
  function ensureView() {
    let v = document.getElementById('v-legal');
    if (v) return v;
    const main = document.querySelector('main');
    if (!main) return null;
    v = document.createElement('section');
    v.className = 'view'; v.id = 'v-legal';
    const foot = document.getElementById('siteFoot');
    main.insertBefore(v, foot || null);
    return v;
  }
  let tocSync = null;
  function renderDoc(id) {
    const v = ensureView(); if (!v) return;
    const d = DOCS[id]();
    const m = missing();
    const ready = !m.fields.length && !m.holes.length;
    const on = active();
    const tabs = '<nav class="lgtabs" aria-label="法律文件">'
      + ['terms', 'privacy', 'disclaimer'].map((k) => '<a href="#' + k + '"' + (k === id ? ' class="on" aria-current="page"' : '') + '>'
        + DOCS[k]().short + '</a>').join('') + '</nav>';
    const toc = d.secs.map((s, i) => '<li><a href="#" data-sec="' + i + '">' + CN[i] + '、' + esc(s.h) + '</a></li>').join('');
    const draft = '';   // 2026-10-07：三份文件已是正式文字，不再掛草稿標示
    const meta = d.dated ? '<p class="lgmeta">最後更新日期：' + UPDATED + '</p>' : '';
    void ready; void on;
    v.innerHTML = tabs + '<div class="lgwrap"><nav class="lgtoc" aria-label="目錄"><ol>' + toc + '</ol></nav>'
      + '<article class="lgdoc" id="lgDoc" data-doc="' + id + '">' + draft
      + '<details class="lgtocm"><summary>目錄</summary><ol>' + toc + '</ol></details>'
      + '<h1>' + d.title + '</h1>' + meta + (d.lead || '')
      + d.secs.map((s, i) => '<h2 id="lg-' + id + '-' + i + '">' + CN[i] + '、' + esc(s.h) + '</h2>' + s.b).join('')
      + '</article></div>';
    /* 目錄連結不能用 href="#lg-…"：那會改掉 hash、觸發路由，整頁被當成未知路由導回總覽。*/
    v.querySelectorAll('a[data-sec]').forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      const h = document.getElementById('lg-' + id + '-' + a.dataset.sec);
      if (h) window.scrollTo({ top: h.getBoundingClientRect().top + window.scrollY - 76 });
      const dt = a.closest('details'); if (dt) dt.open = false;
    }));
    const links = [...v.querySelectorAll('.lgtoc a')];
    const heads = d.secs.map((s, i) => document.getElementById('lg-' + id + '-' + i));
    if (tocSync) window.removeEventListener('scroll', tocSync);
    tocSync = () => {
      if (!v.classList.contains('on')) return;
      let k = 0;
      heads.forEach((h, i) => { if (h && h.getBoundingClientRect().top < 120) k = i; });
      links.forEach((a, i) => a.classList.toggle('on', i === k));
    };
    window.addEventListener('scroll', tocSync, { passive: true });
    tocSync();
  }

  function renderLeave() {
    const v = ensureView(); if (!v) return;
    let back = '';
    try {
      const ref = document.referrer ? new URL(document.referrer) : null;
      if (ref && ref.origin !== location.origin && history.length > 1)
        back = '<button type="button" class="lgb2" id="lgBack">回到上一頁</button>';
    } catch (e) { /* 忽略 */ }
    v.innerHTML = '<div class="lgleave" id="lgLeave" role="region" aria-label="未同意使用條款">'
      + '<h1>你沒有同意使用條款，所以本站不顯示內容。</h1>'
      + '<p>重新整理就能再選一次。<a href="#terms">使用條款</a>、<a href="#privacy">隱私權政策</a>、<a href="#disclaimer">免責聲明</a></p>'
      + '<div class="lgbtns">' + back
      + '<a class="lgb2" href="#terms" id="lgRead" style="display:inline-flex;align-items:center;text-decoration:none">閱讀條款</a>'
      + '<button type="button" class="lgb1" id="lgReAccept">我重新考慮，同意並繼續</button></div></div>';
    const b = v.querySelector('#lgBack'); if (b) b.addEventListener('click', () => history.back());
    v.querySelector('#lgReAccept').addEventListener('click', () => { accept(); location.hash = '#overview'; });
  }

  // ------------------------------------------------------------------ 同意橫幅
  function bannerEl() { return document.getElementById('lgBanner'); }
  function hideBanner(anim) {
    const b = bannerEl(); if (!b) return;
    if (!anim || matchMedia('(prefers-reduced-motion: reduce)').matches) { b.remove(); return; }
    b.classList.add('out');
    setTimeout(() => b.remove(), 190);
  }
  function syncBanner() {
    const h = (location.hash.replace('#', '').split('/')[0]) || '';
    const want = active() && !readConsent() && h !== 'leave';
    const b = bannerEl();
    if (!want) { if (b && !b.classList.contains('out')) b.remove(); return; }
    if (b) return;
    const el = document.createElement('div');
    el.className = 'lgban'; el.id = 'lgBanner';
    el.setAttribute('role', 'region'); el.setAttribute('aria-label', '使用條款同意');
    el.innerHTML = '<p>本站整理公開資料供研究參考，不是投資建議。繼續使用前，請先閱讀'
      + '<a href="#terms">使用條款</a>、<a href="#privacy">隱私權政策</a>與<a href="#disclaimer">免責聲明</a>。</p>'
      + '<div class="lgbtns"><button type="button" class="lgb2" id="lgDecline">不同意</button>'
      + '<button type="button" class="lgb1" id="lgAccept">同意並繼續</button></div>';
    document.body.appendChild(el);          // 出現時**不搶焦點**：這不是強制彈窗
    el.querySelector('#lgAccept').addEventListener('click', () => {
      accept(true);
    });
    el.querySelector('#lgDecline').addEventListener('click', () => {
      declined = true;                       // 只記在記憶體：重新整理就忘掉（規格 4.1 第 2 點）
      hideBanner(false);
      location.hash = '#leave';
    });
  }
  function accept(fromBanner) {
    writeConsent();
    declined = false;
    hideBanner(!!fromBanner);
    /* 導覽只在「第一次同意」之後自動開一次；讀寫不到 localStorage 就不自動開
       （否則每次重新整理都會跳出來），只留頁尾的入口。*/
    const seen = tourSeen();
    if (storeOK && seen === false) setTimeout(() => openTour(null), fromBanner ? 200 : 400);
  }

  // ------------------------------------------------------------------ 平台導覽
  /* 對到首頁的四步決策動線；標題與 app.js 的 MIA_STEPS 同一套字。*/
  const STEPS = [
    { t: '① 錢往哪跑', d: '先看輪動時鐘：哪些族群正從「改善」走進「領先」，再看熱力圖今天的錢集中在哪幾塊。', sel: '#ovRotCard' },
    { t: '② 貴不貴', d: '看大盤與族群的體質：漲的是不是只有權值股、法人有沒有一起進來。', sel: '#hero' },
    { t: '③ 何時進場', d: '看大盤三張圖的走勢與 K 線，判斷現在是回檔還是突破。', sel: '#m3' },
    { t: '④ 別進的理由', d: '最後看新聞、法說與事件面消息。', sel: '#ovEvents' },
  ];
  let tourState = null;
  function closeTour(restore) {
    if (!tourState) return;
    const { mask, opener, onKey } = tourState;
    document.removeEventListener('keydown', onKey, true);
    mask.remove();
    markTour();
    tourState = null;
    if (restore && opener && opener.isConnected) { try { opener.focus(); } catch (e) { /* 忽略 */ } }
  }
  function openTour(opener) {
    if (tourState) return;
    const mask = document.createElement('div');
    mask.className = 'lgmask'; mask.id = 'lgTourMask';
    mask.innerHTML = '<div class="lgtour" id="lgTour" role="dialog" aria-modal="true" aria-labelledby="lgTourH">'
      + '<div class="lgth"><span class="lgic" aria-hidden="true">◎</span><div><h2 id="lgTourH" tabindex="-1">平台導覽</h2>'
      + '<small>四步看懂今天的資金</small></div><button type="button" class="lgx" id="lgTourX" aria-label="關閉導覽">✕</button></div>'
      + '<h3>先看錢，再看價，最後才看時機</h3>'
      + '<p>這個網站把公開的成交、法人、營收與新聞資料，照「錢往哪跑 → 貴不貴 → 何時進場 → 別進的理由」排成一條路徑。</p>'
      + '<div class="lgcards">'
      + '<div class="lgcard"><b>⤢ 紅漲綠跌</b>跟台股看盤軟體一樣。</div>'
      + '<div class="lgcard"><b>◷ 每天盤後更新</b>盤中的數字另外標「即時」。</div>'
      + '<div class="lgcard"><b>⛉ 不是投資建議</b>所有數字都是公開資料算出來的結果。</div></div>'
      + '<div id="lgStepBox"></div>'
      + '<div class="lgdots" id="lgDots" aria-hidden="true">' + STEPS.map(() => '<i></i>').join('') + '</div>'
      + '<div class="lgtf"><button type="button" class="lgtx" id="lgSkip">先跳過</button>'
      + '<button type="button" class="lgb1" id="lgNext">下一步 →</button></div></div>';
    document.body.appendChild(mask);
    let i = 0;
    const paint = () => {
      const s = STEPS[i];
      mask.querySelector('#lgStepBox').innerHTML = '<div class="lgstep" id="lgStep" data-i="' + i + '">'
        + '<div class="lgsn">四個步驟 ' + (i + 1) + '/' + STEPS.length + '</div>'
        + '<div class="lgst"><i aria-hidden="true">✓</i><span id="lgStepT">' + s.t + '</span></div>'
        + '<div class="lgsd">' + s.d + '</div></div>'
        + '<button type="button" class="lggo" id="lgGo">到總覽看這一步 →</button>';
      mask.querySelector('#lgGo').addEventListener('click', () => goStep(i));
      [...mask.querySelectorAll('#lgDots i')].forEach((d, k) => d.classList.toggle('on', k === i));
      mask.querySelector('#lgNext').textContent = i === STEPS.length - 1 ? '開始使用' : '下一步 →';
    };
    const onKey = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); closeTour(true); return; }
      if (e.key !== 'Tab') return;
      /* 焦點困在彈窗裡（focus trap）：Tab 走到最後一顆回到第一顆，反過來也一樣。*/
      const f = [...mask.querySelectorAll('button,a[href]')].filter((x) => x.offsetParent !== null);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && (document.activeElement === first || !mask.contains(document.activeElement))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey, true);
    tourState = { mask, opener: opener || document.activeElement, onKey };
    mask.querySelector('#lgTourX').addEventListener('click', () => closeTour(true));
    mask.querySelector('#lgSkip').addEventListener('click', () => closeTour(true));
    mask.querySelector('#lgNext').addEventListener('click', () => {
      if (i === STEPS.length - 1) { closeTour(true); return; }
      i++; paint();
    });
    mask.addEventListener('click', (e) => { if (e.target === mask) closeTour(true); });
    paint();
    mask.querySelector('#lgTourH').focus();
  }
  /* 「到總覽看這一步」：關掉彈窗 → 回總覽 → 把那一段帶到畫面上半部 → 外圈亮一圈 1 秒。
     手機的總覽是分段導覽（一次只顯示一步），所以先按那一步的主軸鈕，再捲。
     桌機沒有 #ovEvents（那是手機才搬出來的卡片），第④步改成打開右側的「今日事件」欄。*/
  function goStep(i) {
    closeTour(false);
    const s = STEPS[i];
    if ((location.hash.replace('#', '').split('/')[0] || 'overview') !== 'overview') location.hash = '#overview';
    const t0 = Date.now();
    const tick = () => {
      const view = document.getElementById('v-overview');
      const ready = view && view.classList.contains('on') && document.querySelector('#ovRotCard');
      if (!ready) { if (Date.now() - t0 < 5000) setTimeout(tick, 120); return; }
      const spine = view.querySelector('.mspine');
      if (spine && spine.offsetParent !== null) {
        /* 2026-10-06 修：手機 v3 把主軸鈕改成 <em>②</em><b>貴不貴</b>，textContent 變「②貴不貴」（中間沒空白），
           拿「② 貴不貴」去比永遠找不到 → 手機按「到總覽看這一步」不會切到那一步、停在第①步。兩邊都去掉空白再比。*/
        const want = s.t.replace(/\s+/g, '');
        const b = [...spine.children].find((x) => (x.textContent || '').replace(/\s+/g, '').indexOf(want) === 0);
        if (b) b.click();
      }
      let el = document.querySelector(s.sel);
      if ((!el || el.offsetParent === null) && i === 3) {
        if (typeof window.twSetSide === 'function') window.twSetSide(true, false);
        el = document.getElementById('side');
      }
      if (!el) return;
      setTimeout(() => {
        const r = el.getBoundingClientRect();
        if (el.id !== 'side') window.scrollTo({ top: Math.max(0, r.top + window.scrollY - 80) });
        el.classList.add('lgflash');
        setTimeout(() => el.classList.remove('lgflash'), 1000);
      }, 60);
    };
    setTimeout(tick, 60);
  }

  // ------------------------------------------------------------------ 路由掛勾
  /* app.js 的 route() 一開頭會問這裡：
       'legal'    → 這一頁由本檔接手（#terms／#privacy／#disclaimer／#leave），app.js 把其他 view 關掉就好
       'redirect' → 使用者剛按了「不同意」、又想去別頁：這一次瀏覽維持在 #leave（重新整理就解除）
       null       → 不關本檔的事，照舊 */
  const ROUTES = ['terms', 'privacy', 'disclaimer', 'leave'];
  /* 會員功能的設定檔是非同步讀的（account.js），可能比第一次畫隱私權政策晚到：到了就重畫一次，才會出現那幾列 */
  window.addEventListener('tw:account-config', () => { if ((location.hash || '') === '#privacy') renderDoc('privacy'); });
  function route(head) {
    syncBanner();
    if (ROUTES.includes(head)) {
      if (head === 'leave') renderLeave(); else renderDoc(head);
      return 'legal';
    }
    if (declined && active() && !readConsent()) { location.replace('#leave'); return 'redirect'; }
    return null;
  }

  // ------------------------------------------------------------------ 啟動
  injectCSS();
  buildFooter();
  ensureView();
  const boot = () => syncBanner();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  window.TwLegal = {
    route, openTour, closeTour: () => closeTour(true),
    /* 給驗收腳本與除錯用：現在是什麼狀態、還缺哪些欄位。*/
    state: () => ({ active: active(), filled: filled(), missing: missing(), consented: readConsent(),
                    declined, storeOK, version: version(), tour: TOUR_V }),
  };
})();
