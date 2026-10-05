/* ============================================================================
   選股探索（#explore）—— site/explore.js（Andy 2026-10-05，規格：docs/explore_page_spec.md）
   ----------------------------------------------------------------------------
   給股票新手的入口：不講「策略」，講六個白話問題（「哪些公司很會賺錢？」……）。
   每一題一張泡泡圖：整個市場都畫出來，符合的上色、其餘淡灰，答案那一塊用底色框起來 ——
   新手不用先懂指標，看「我的答案在圖上哪一塊」就好。清單是配角，而且**不排名次**（依成交值排序）。

   為什麼是泡泡圖而不是排行榜：排行榜只回答「誰第一」，新手會把第一名當成「最該買」；
   泡泡圖回答的是「符合的公司跟其他公司差多遠」，條件本身才是重點（法遵：不排最值得買名次）。

   資料：fundamental.json（ROE／毛利／營收）＋ stocks.json（族群、成交值）＋ explore.json（歷史類欄位，
   pipeline/compute/explore.py）。預覽版讀正式站資料、正式站還沒有 explore.json 時，退回既有 JSON 現算
   （cheap→同族群本益比百分位、inst→inst_streak 前 60 名、steady→candidates 約 640 檔、div→不可用），
   頁頂多一行灰字講明（規格 §6）。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const App = () => window.App || {};
  const LS = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } },
  };
  const n1 = (v, d) => (v == null || !isFinite(v) ? '—' : Number(v).toFixed(d == null ? 1 : d));
  const MIN_TV = 10;          // 近 20 日平均成交值下限（百萬元）：太冷門的價格不可靠

  /* ---------------- 名詞小教室 ----------------
     每一則：一句「它是什麼」＋一句「新手怎麼用」。只解釋定義等於沒寫（AGENTS：說明要寫到「所以我該怎麼用」）。 */
  const TERMS = {
    roe: ['ROE（股東權益報酬率）', '公司拿股東的 100 元，一年替股東賺回多少。', '15% 以上通常算很會賺；但借很多錢的公司 ROE 也會被墊高，要一起看負債。'],
    gm: ['毛利率', '賣 100 元的東西，扣掉直接成本後還剩多少。', '毛利高代表產品有議價力、不容易被殺價；不同產業差很多，最好跟同業比。'],
    pe: ['本益比', '股價是每股一年盈餘的幾倍；數字越小＝用越少的錢買到同樣的獲利。', '虧損公司沒有本益比。不同產業的正常本益比差很多，所以這一頁只拿它跟「自己過去」比。'],
    pepct: ['本益比歷史位置', '目前本益比落在自己近 5 年各季本益比的第幾百分位：0＝歷史最便宜、100＝歷史最貴。', '位置低不代表一定會漲 —— 也可能是市場覺得它未來賺得會比較少（例如景氣下滑）。'],
    rev: ['月營收年增率', '這個月營收跟去年同一個月比，多了或少了幾 %。', '跟去年同月比可以避開淡旺季；連續好幾個月都成長，比單月暴增更可靠。'],
    streak: ['連續年增月數', '月營收年增率連續幾個月都是正的。', '數字越大代表成長越有延續性；單月暴增可能只是一次性訂單。'],
    inst: ['三大法人', '外資、投信、自營商這三類機構投資人。', '他們資金大、研究多，常被當成「聰明錢」參考，但法人也會看錯、也會短線進出。'],
    buyday: ['連買天數', '三大法人合計每天的買賣超相加，連續淨買超到今天為止幾天。', '連續買比單日大買更能看出態度；今天一轉賣，天數就歸零。'],
    vol: ['波動度', '近 60 個交易日每天漲跌幅的起伏程度，換算成一年（年化）。', '數字越小走勢越平穩；20% 左右算穩、50% 以上代表常常一天大漲大跌。'],
    ma: ['均線（20 日／60 日）', '最近 20 天（約一個月）／60 天（約一季）收盤價的平均。', '股價站在均線上面，代表最近進場的人平均是賺錢的，走勢偏多；跌破則相反。'],
    dy: ['現金殖利率', '近 12 個月發的現金股利 ÷ 目前股價。', '殖利率高不一定好：股價大跌也會讓殖利率變高，要配合「連續配息」一起看。'],
    divy: ['連續配息年數', '從去年往回數，連續幾年都有發現金股利（今年還沒過完不算）。', '能連續很多年配息，代表獲利與現金流比較穩定。'],
    tv: ['成交值', '一天內這檔股票成交的總金額（本頁用近 20 日平均）。', '成交值越大越好買賣、價格越不容易被少數人影響；泡泡越大＝成交值越大。'],
  };

  /* ---------------- 六個問題 ----------------
     th：寬鬆／標準／嚴格三段門檻（規格 §5）。test(r, t) 回傳是否符合；x／y 是圖上的兩個軸。 */
  const LV = [['loose', '寬鬆'], ['std', '標準'], ['strict', '嚴格']];
  const isFin = (r) => /金融|銀行|保險|證券|金控/.test(r.group || '') ;
  const Q = [
    { id: 'earn', q: '哪些公司很會賺錢？', sub: '股東的錢拿去用，賺回來的比例高、產品毛利也高。',
      th: { loose: [10, 15], std: [15, 20], strict: [20, 30] },
      rule: (t) => `ROE ≥ ${t[0]}% 且 毛利率 ≥ ${t[1]}%（金融業沒有毛利率，只看 ROE）`,
      test: (r, t) => r.roe != null && r.roe >= t[0] && (r.gm == null ? isFin(r) : r.gm >= t[1]),
      x: { k: 'gm', name: '毛利率 %', term: 'gm', clip: [-20, 90] }, y: { k: 'roe', name: 'ROE %', term: 'roe', clip: [-30, 60] },
      zone: (t) => ({ x0: t[1], y0: t[0] }), zoneTxt: '右上角這一塊＝又會賺、毛利又高',
      mean: '這些公司「拿到錢就能變出更多錢」，而且賣的東西不太會被殺價。長期來看，股價最終會跟著獲利走。',
      care: ['ROE 是去年到最近一季的成績，不保證明年；景氣循環股在高峰時 ROE 最漂亮。', '借很多錢的公司 ROE 也會被墊高。', '會賺錢的公司通常已經不便宜 —— 可以再勾「比自己過去便宜」一起看。'],
      terms: ['roe', 'gm'],
      why: (r) => [`ROE ${n1(r.roe)}%`, r.gm != null ? `毛利率 ${n1(r.gm)}%` : '金融業（無毛利率）'] },
    { id: 'cheap', q: '哪些股票比自己過去便宜？', sub: '本益比落在自己近 5 年的低檔區。',
      th: { loose: [40], std: [30], strict: [20] },
      rule: (t) => `本益比在自己近 5 年的第 ${t[0]} 百分位以下（有獲利才算）`,
      fbRule: (t) => `本益比在同族群的第 ${t[0]} 百分位以下（暫用同族群比較）`,
      test: (r, t) => r.pepct != null && r.pe > 0 && r.pepct <= t[0],
      x: { k: 'pepct', name: '本益比歷史位置（0＝最便宜）', term: 'pepct', clip: [0, 100] }, y: { k: 'roe', name: 'ROE %', term: 'roe', clip: [-30, 60] },
      zone: (t) => ({ x1: t[0] }), zoneTxt: '左邊這一塊＝比自己過去便宜；越上面越會賺',
      mean: '同一家公司，現在的價格相對它自己過去的獲利，算是打折中。圖的上下再看它賺不賺錢：左上角是「便宜又會賺」。',
      care: ['便宜可能有原因：市場預期它未來獲利會下滑（例如景氣反轉、失去大客戶）。', '只看過去 5 年，不能代表「合理價」。', '虧損公司沒有本益比，不會出現在這一題。'],
      terms: ['pepct', 'pe', 'roe'],
      why: (r) => [`本益比 ${n1(r.pe)} 倍`, `${FB.cheap ? '同族群' : '自己近 5 年'}第 ${n1(r.pepct, 0)} 百分位`] },
    { id: 'grow', q: '誰的營收正在變好？', sub: '月營收連續好幾個月都比去年同期多。',
      th: { loose: [2, 5], std: [3, 10], strict: [6, 20] },
      rule: (t) => `月營收年增連續 ≥ ${t[0]} 個月，且最新一月年增 ≥ ${t[1]}%`,
      test: (r, t) => r.rs != null && r.rs >= t[0] && r.ry != null && r.ry >= t[1],
      x: { k: 'ry', name: '最新月營收年增 %', term: 'rev', clip: [-60, 150] }, y: { k: 'rs', name: '連續年增月數', term: 'streak', clip: [0, 24], jitter: 0.35 },
      zone: (t) => ({ x0: t[1], y0: t[0] }), zoneTxt: '右上角＝成長幅度大、而且持續了好幾個月',
      mean: '生意一個月比一個月好，而且不是只有一個月。營收通常比獲利早反映，是新手最容易追蹤的「體溫計」。',
      care: ['去年同期如果特別差（基期低），年增率會看起來很漂亮。', '營收成長不等於賺錢：毛利可能在下滑。', '月營收每月 10 日前公布，資料月份請看標題旁的日期。'],
      terms: ['rev', 'streak'],
      why: (r) => [`最新月營收年增 ${n1(r.ry)}%`, `連續 ${r.rs} 個月年增`] },
    { id: 'inst', q: '法人最近在買誰？', sub: '外資、投信、自營商合計，連續好幾天淨買超。',
      th: { loose: [3], std: [5], strict: [10] },
      rule: (t) => `三大法人合計連續淨買超 ≥ ${t[0]} 個交易日`,
      fbRule: (t) => `三大法人合計連續淨買超 ≥ ${t[0]} 個交易日（暫用連買前 60 名）`,
      test: (r, t) => r.bd != null && r.bd >= t[0],
      x: { k: 'bd', name: '連買天數', term: 'buyday', clip: [0, 40], jitter: 0.3 }, y: { k: 'net', name: '近 10 日淨買超（張）', term: 'inst', clip: null },
      zone: (t) => ({ x0: t[0] }), zoneTxt: '右邊這一塊＝連續買最多天的；越上面買得越多張',
      mean: '大資金連續幾天站在買方，代表他們對這家公司有一段時間的看法，不是一時興起。',
      care: ['法人也會看錯，連買之後反手賣出很常見。', '張數要跟這檔平常的成交量比，大型股買幾千張可能只是零頭。', '外資有時是被動調整指數成分，不一定代表看好。'],
      terms: ['inst', 'buyday'],
      why: (r) => [`三大法人連買 ${r.bd} 天`, r.net != null ? `${FB.inst ? '連買期間累積' : '近 10 日淨買超'} ${Math.round(r.net).toLocaleString()} 張` : ''] },
    { id: 'steady', q: '哪些股價走得穩？', sub: '每天起伏不大，而且站在均線上面。',
      th: { loose: [40, 0], std: [30, 1], strict: [22, 1] },
      rule: (t) => `60 日波動度 ≤ ${t[0]}%，且站上 ${t[1] ? '20 日與 60 日均線' : '60 日均線'}`,
      fbRule: (t) => `均線多頭排列、與 20 日均線乖離 ≤ ${t[0] / 6 | 0}%（暫用候選股約 640 檔）`,
      test: (r, t) => FB.steady ? (r.align === 1 && r.bias != null && Math.abs(r.bias) <= (t[0] / 6 | 0))
        : (r.vol != null && r.vol <= t[0] && r.a60 === 1 && (!t[1] || r.a20 === 1)),
      x: { k: 'vol', name: '60 日波動度 %（越左越穩）', term: 'vol', clip: [0, 120] }, y: { k: 'ret', name: '近 60 日漲跌 %', term: 'ma', clip: [-60, 120] },
      fbx: { k: 'bias', name: '與 20 日均線乖離 %', term: 'ma', clip: [-30, 30] }, fby: { k: 'rsi', name: 'RSI', term: 'ma', clip: [0, 100] },
      zone: (t) => (FB.steady ? { x0: -(t[0] / 6 | 0), x1: t[0] / 6 | 0 } : { x1: t[0] }), zoneTxt: '左邊這一塊＝起伏小；上色的又站在均線上',
      mean: '走勢平穩、而且最近一個月與一季進場的人平均都是賺的。對新手來說比較不會「一買就被洗出場」。',
      care: ['穩不代表會漲，可能只是牛皮盤整。', '過去 60 天穩，不保證之後也穩：財報、消息都可能讓它突然大動。', '大型權值股通常比較穩，小型股要特別小心。'],
      terms: ['vol', 'ma'],
      why: (r) => FB.steady ? [`與 20 日均線乖離 ${n1(r.bias)}%`, '均線多頭排列'] : [`60 日波動度 ${n1(r.vol)}%`, `${r.a20 ? '站上' : '低於'} 20 日均線、${r.a60 ? '站上' : '低於'} 60 日均線`] },
    { id: 'div', q: '配息穩定的公司？', sub: '殖利率不低，而且連續很多年都有發現金股利。',
      th: { loose: [3, 3], std: [4, 5], strict: [5, 8] },
      rule: (t) => `近 12 個月現金殖利率 ≥ ${t[0]}%，且連續 ≥ ${t[1]} 年配現金`,
      test: (r, t) => r.dy != null && r.dy >= t[0] && r.dv != null && r.dv >= t[1],
      x: { k: 'dy', name: '現金殖利率 %', term: 'dy', clip: [0, 15] }, y: { k: 'dv', name: '連續配息年數', term: 'divy', clip: [0, 20], jitter: 0.35 },
      zone: (t) => ({ x0: t[0], y0: t[1] }), zoneTxt: '右上角＝殖利率高、而且配得很久',
      mean: '每年穩穩發現金給股東，代表公司賺得到「真的現金」。適合想領股利、不想天天看盤的人。',
      care: ['股價大跌也會讓殖利率變高 —— 要確認不是因為公司出問題。', '配息後股價要漲回除息前（填息）才算真的賺到。', '股利要繳稅，也可能被併入所得。'],
      terms: ['dy', 'divy'],
      why: (r) => [`現金殖利率 ${n1(r.dy, 2)}%`, `連續 ${r.dv} 年配現金`] },
  ];
  const QBY = {}; Q.forEach((q) => { QBY[q.id] = q; });

  /* ---------------- 狀態 ---------------- */
  const FB = { cheap: false, inst: false, steady: false, div: false, any: false };
  const S = {
    q: 'earn',
    lv: (() => { try { return JSON.parse(LS.get('tw.explore.lv') || '{}') || {}; } catch (e) { return {}; } })(),
    combo: (() => { const v = (LS.get('tw.explore.combo') || 'earn,cheap').split(',').filter((x) => QBY[x]); return v.length ? v : ['earn', 'cheap']; })(),
    region: null,       // 文氏圖點了哪一塊（遮罩數字，bit i ＝ combo[i]）；null＝全交集
    full: false,        // 名單是否展開全部
  };
  let R = [], RBY = {}, asof = '', revYm = '', period = '', groupColor = {}, built = false, chartInst = null;

  async function loadAll() {
    const A = App();
    const need = ['fundamental', 'stocks'];
    const [fund, stocks] = await Promise.all(need.map((n) => A.load(n).catch(() => null)));
    let ex = null;
    try { ex = await A.load('explore'); } catch (e) { ex = null; }
    FB.any = !(ex && Array.isArray(ex.rows) && ex.rows.length);
    let streak = null, cand = null;
    if (FB.any) {
      [streak, cand] = await Promise.all([A.load('inst_streak').catch(() => null), A.load('candidates').catch(() => null)]);
      FB.cheap = FB.inst = FB.steady = FB.div = true;
    }
    const fx = {}; (fund || []).forEach((f) => { fx[f.code] = f; });
    const exRow = {};
    if (!FB.any) {
      const C = ex.cols; asof = ex.asof || '';
      ex.rows.forEach((row) => { const o = {}; C.forEach((c, i) => { o[c] = row[i]; }); exRow[o.code] = o; });
    }
    const st = {}; (streak && streak.total || []).forEach((s) => { st[s.code] = s; });
    const cd = {}; (cand || []).forEach((c) => { cd[c.code] = c; });
    const rows = [];
    const per = {}, ym = {};
    (stocks || []).forEach((s) => {
      const f = fx[s.code] || {};
      if (!s.code || /^00/.test(s.code) || s.group_id === 'ind_ETF' || f.group_id === 'ind_ETF') return;
      const e = exRow[s.code] || {};
      const tv = e.tv20 != null ? e.tv20 : (s.turnover != null ? s.turnover / 1e6 : null);
      if (tv == null || tv < MIN_TV) return;
      if (f.latest_period) per[f.latest_period] = (per[f.latest_period] || 0) + 1;
      if (f.rev_ym) ym[f.rev_ym] = (ym[f.rev_ym] || 0) + 1;
      const r = {
        code: s.code, name: s.name || f.name || s.code, group: s.group || f.group_name || '—', gid: s.group_id,
        ind: f.group_name || '', close: s.close, chg: s.chg_pct, tv,
        roe: f.roe, gm: f.gross_margin, pe: f.pe, loss: !!f.is_loss, ry: f.rev_yoy, rs: f.rev_streak, rym: f.rev_ym, spike: !!f.rev_flag_spike,
        pepct: FB.cheap ? f.percentile : e.pe_pct,
        bd: FB.inst ? (st[s.code] ? st[s.code].streak_days : 0) : e.buy_days,
        net: FB.inst ? (st[s.code] ? st[s.code].accumulated / 1000 : null) : e.net10,
        vol: e.vol60, a20: e.above20, a60: e.above60, ret: e.ret60,
        dy: e.dy, dv: e.div_years,
      };
      if (FB.steady) { const c = cd[s.code]; if (!c) { r.align = null; } else { r.align = c.ma_align; r.bias = c.bias20; r.rsi = c.rsi; } }
      rows.push(r);
    });
    const top = (o) => Object.keys(o).sort((a, b) => o[b] - o[a])[0] || '';
    period = top(per); revYm = top(ym);
    if (!asof) { const m = A.D && A.D.meta; asof = (m && (m.latest || m.as_of || m.date)) || (stocks && stocks[0] && stocks[0].date) || ''; }
    // 族群顏色：成交值前 8 大族群各一色（跨題目一致，換題時同一個族群不會換顏色）
    const gsum = {}; rows.forEach((r) => { gsum[r.group] = (gsum[r.group] || 0) + r.tv; });
    const pal = (A.PALETTE || ['#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8ad8', '#5bc0ff', '#ffd25b', '#7bffb4']);
    groupColor = {};
    Object.keys(gsum).sort((a, b) => gsum[b] - gsum[a]).slice(0, 8).forEach((g, i) => { groupColor[g] = pal[i % pal.length]; });
    R = rows; RBY = {}; rows.forEach((r) => { RBY[r.code] = r; });
  }

  const lvOf = (id) => (S.lv[id] && QBY[id].th[S.lv[id]] ? S.lv[id] : 'std');
  const thOf = (id) => QBY[id].th[lvOf(id)];
  const usable = (id) => !(id === 'div' && FB.div);
  const ruleOf = (q) => (FB[q.id] && q.fbRule ? q.fbRule : q.rule)(thOf(q.id));
  function matches(id) {
    if (!usable(id)) return [];
    const q = QBY[id], t = thOf(id);
    return R.filter((r) => { try { return q.test(r, t); } catch (e) { return false; } }).sort((a, b) => b.tv - a.tv);
  }
  const dateOf = (id) => (id === 'earn' ? (period ? `財報 ${period}` : '') : id === 'grow' ? (revYm ? `營收 ${revYm}` : '')
    : id === 'cheap' && FB.cheap ? (period ? `財報 ${period}` : '') : asof ? `資料 ${asof}` : '');

  /* ---------------- 畫面骨架 ---------------- */
  function shell(root) {
    root.innerHTML = `
      <div class="xp-legal" role="note" id="xpLegal">條件篩選結果僅供研究，不構成投資建議；本站非證券投資顧問。</div>
      <div class="xp-fb" id="xpFb" hidden>部分題目的歷史資料還在準備中，暫用簡化口徑（標題旁會註明）；「配息穩定」暫時無法篩選。</div>
      <div class="card xp-qcard" id="xpQs">
        <h3>六個好問題 <small>先挑一個你想問的，下面的圖會換成那一題的答案</small></h3>
        <div class="xp-qgrid" id="xpQgrid" role="tablist" aria-label="選一個問題"></div>
      </div>
      <div class="xp-main">
        <div class="card xp-lens" id="xpLens">
          <div class="row spread xp-lhead">
            <h3><span id="xpLensT"></span> <small id="xpLensD" class="xp-date"></small></h3>
            <div class="seg" id="xpLv" role="group" aria-label="門檻">${LV.map(([k, n]) => `<button type="button" data-lv="${k}">${n}</button>`).join('')}</div>
          </div>
          <div class="xp-rule" id="xpRule"></div>
          <div class="xp-chart" id="xpChart"></div>
          <div class="xp-how" id="xpHow"></div>
          <div class="xp-zero" id="xpZero" hidden></div>
        </div>
        <div class="card xp-side" id="xpSide"></div>
      </div>
      <div class="card xp-list" id="xpList"></div>
      <div class="card xp-combo" id="xpCombo">
        <h3>條件積木 <small>勾 2～3 個問題，看「同時符合」的有幾家</small></h3>
        <div class="xp-cpick" id="xpPick"></div>
        <div class="xp-cbody">
          <div class="xp-venn" id="xpVenn"></div>
          <div class="xp-cres" id="xpCres"></div>
        </div>
      </div>
      <aside class="xp-card" id="xpCard" hidden aria-label="白話卡"></aside>
      <div class="xp-term" id="xpTerm" hidden role="dialog" aria-label="名詞小教室"></div>`;
    $('#xpLv', root).addEventListener('click', (e) => {
      const b = e.target.closest('button[data-lv]'); if (!b) return;
      S.lv[S.q] = b.dataset.lv; LS.set('tw.explore.lv', JSON.stringify(S.lv)); paintAll();
    });
    root.addEventListener('click', (e) => {
      const tb = e.target.closest('.xp-tb'); if (tb) { e.stopPropagation(); openTerm(tb.dataset.term, tb); return; }
      const qb = e.target.closest('.xp-q'); if (qb) { setQ(qb.dataset.q); return; }
      const row = e.target.closest('[data-xcode]'); if (row && !e.target.closest('a')) { openCard(row.dataset.xcode); return; }
      const rg = e.target.closest('[data-region]'); if (rg) { S.region = +rg.dataset.region; paintCombo(); return; }
      const more = e.target.closest('#xpMore'); if (more) { S.full = !S.full; paintList(); return; }
      const lz = e.target.closest('[data-loosen]'); if (lz) { S.lv[S.q] = 'loose'; LS.set('tw.explore.lv', JSON.stringify(S.lv)); paintAll(); return; }
      const cz = e.target.closest('[data-cloose]'); if (cz) { S.combo.forEach((id) => { S.lv[id] = 'loose'; }); LS.set('tw.explore.lv', JSON.stringify(S.lv)); paintAll(); return; }
    });
    $('#xpPick', root).addEventListener('change', (e) => {
      const cb = e.target.closest('input[type=checkbox]'); if (!cb) return;
      const on = $$('#xpPick input:checked').map((x) => x.value);
      if (on.length > 3) { cb.checked = false; flash('最多勾 3 題 —— 題目越多，同時符合的公司越少。'); return; }
      S.combo = on; S.region = null; LS.set('tw.explore.combo', on.join(',')); paintCombo();
    });
    document.addEventListener('click', (e) => {
      const t = $('#xpTerm'); if (t && !t.hidden && !e.target.closest('#xpTerm') && !e.target.closest('.xp-tb')) t.hidden = true;
    });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape') return;
      const t = $('#xpTerm'); if (t && !t.hidden) { t.hidden = true; return; }
      const c = $('#xpCard'); if (c && !c.hidden) closeCard();
    });
    window.addEventListener('hashchange', () => { if (!/^#explore/.test(location.hash)) { closeCard(); const t = $('#xpTerm'); if (t) t.hidden = true; } });
  }
  function flash(msg) {
    const el = $('#xpCres'); if (!el) return;
    const p = document.createElement('div'); p.className = 'xp-flash'; p.textContent = msg; el.prepend(p);
    setTimeout(() => p.remove(), 2600);
  }
  const tb = (k) => (TERMS[k] ? `<button type="button" class="xp-tb" data-term="${k}" aria-label="${esc(TERMS[k][0])}是什麼">?</button>` : '');

  /* ---------------- A：問題卡 ---------------- */
  function paintQs() {
    $('#xpQgrid').innerHTML = Q.map((q, i) => {
      const ok = usable(q.id), n = ok ? matches(q.id).length : null;
      return `<button type="button" class="xp-q${q.id === S.q ? ' on' : ''}${ok ? '' : ' off'}" data-q="${q.id}" role="tab" aria-selected="${q.id === S.q}">
        <span class="xp-qn">${i + 1}</span><b>${esc(q.q)}</b><span class="xp-qs">${esc(q.sub)}</span>
        <span class="xp-qc">${ok ? `符合 <em>${n}</em> 家` : '資料準備中'}</span><span class="xp-qd">${esc(dateOf(q.id))}</span></button>`;
    }).join('');
  }

  /* ---------------- B：問題放大鏡（泡泡圖） ---------------- */
  function axisOf(q, w) { return FB[q.id] && q['fb' + w] ? q['fb' + w] : q[w]; }
  function clipV(v, c) { return c ? Math.max(c[0], Math.min(c[1], v)) : v; }
  function paintLens() {
    const q = QBY[S.q], t = thOf(q.id), ok = usable(q.id);
    $('#xpLensT').textContent = q.q;
    $('#xpLensD').textContent = dateOf(q.id);
    $$('#xpLv button').forEach((b) => b.classList.toggle('on', b.dataset.lv === lvOf(q.id)));
    const X = axisOf(q, 'x'), Y = axisOf(q, 'y');
    const hit = new Set(matches(q.id).map((r) => r.code));
    $('#xpRule').innerHTML = ok ? `<b>條件：</b>${esc(ruleOf(q))}　<span class="xp-hitn">符合 <em id="xpHitN">${hit.size}</em> 家 ／ 共 ${R.length} 家</span>` : '<b>這一題的資料還在準備中。</b>';
    $('#xpHow').innerHTML = `<b>怎麼看：</b>每一顆泡泡是一家公司，泡泡越大＝成交值越大；<span class="xp-zonek"></span>${esc(q.zoneTxt)}。`
      + `上色的是符合條件的公司（顏色＝族群），灰色是其他公司。<b>所以：</b>先看答案那一塊裡有沒有你認得的公司，點泡泡看白話卡。`;
    const A = App(), CH = A.CH || {};
    const el = $('#xpChart');
    if (!ok || !A.chart) { if (A.empty) A.empty(el, '資料準備中'); else el.innerHTML = ''; zeroHint(0); return; }
    const pts = [];
    const jit = (code, amt) => { if (!amt) return 0; let h = 0; for (const ch of code) h = (h * 31 + ch.charCodeAt(0)) | 0; return ((h % 1000) / 1000 - 0.5) * 2 * amt; };
    R.forEach((r) => {
      const xv = r[X.k], yv = r[Y.k];
      if (xv == null || yv == null || !isFinite(xv) || !isFinite(yv)) return;
      pts.push({ r, x: clipV(+xv, X.clip) + jit(r.code, X.jitter), y: clipV(+yv, Y.clip) + jit(r.code + 'y', Y.jitter), on: hit.has(r.code) });
    });
    const size = (tv) => Math.max(5, Math.min(34, Math.sqrt(tv) * 0.55));
    const ys = pts.map((p) => p.y).sort((a, b) => a - b);
    let yClip = Y.clip;
    if (!yClip && ys.length) {           // 張數這種沒有天然範圍的軸：用 2%～98% 分位數夾住，免得一兩檔極端值把其他人壓扁成一條線
      const lo = ys[Math.floor(ys.length * 0.02)], hi = ys[Math.floor(ys.length * 0.98)];
      yClip = [lo, hi]; pts.forEach((p) => { p.y = clipV(p.y, yClip); });
    }
    const rng = (arr) => (arr.length ? [Math.min(...arr), Math.max(...arr)] : [0, 1]);
    const xb = X.clip || rng(pts.map((p) => p.x)), yb = yClip || rng(pts.map((p) => p.y));
    const z = q.zone(t), ma = {};
    const area = [[{ xAxis: z.x0 != null ? z.x0 : xb[0], yAxis: z.y0 != null ? z.y0 : yb[0] }, { xAxis: z.x1 != null ? z.x1 : xb[1], yAxis: z.y1 != null ? z.y1 : yb[1] }]];
    ma.markArea = { silent: true, itemStyle: { color: A.hexA ? A.hexA(CH.cyan || '#3ee0ff', 0.08) : 'rgba(62,224,255,.08)', borderColor: CH.cyan || '#3ee0ff', borderWidth: 1, borderType: 'dashed' },
      label: { show: true, position: 'insideTopRight', color: CH.cyan || '#3ee0ff', fontSize: 12, formatter: '答案在這一塊' }, data: area };
    const toD = (p) => ({ value: [p.x, p.y, p.r.tv], code: p.r.code, name: p.r.name,
      symbolSize: size(p.r.tv), itemStyle: p.on ? { color: groupColor[p.r.group] || (CH.amber || '#ffb454'), opacity: 0.88, borderColor: CH.panel || '#0a1020', borderWidth: 1 } : undefined });
    const off = pts.filter((p) => !p.on).map(toD), on = pts.filter((p) => p.on).map(toD);
    const fmtAx = (v) => (Math.abs(v) >= 1000 ? Math.round(v / 1000) + 'k' : Math.round(v * 10) / 10);
    const opt = {
      animation: false,
      grid: { left: 64, right: 24, top: 30, bottom: 56 },
      tooltip: Object.assign({}, A.tip || {}, { trigger: 'item', formatter: (p) => {
        const r = RBY[p.data.code]; if (!r) return '';
        return `<b>${esc(r.name)} ${esc(r.code)}</b><br>${esc(r.group)}<br>${esc(X.name)}：${n1(r[X.k])}<br>${esc(Y.name)}：${n1(r[Y.k])}<br>${hit.has(r.code) ? '✓ 符合這一題' : '不符合這一題'}<br><span style="opacity:.7">點一下看白話卡</span>`;
      } }),
      xAxis: Object.assign({}, A.axisStyle || {}, { type: 'value', name: X.name, nameLocation: 'middle', nameGap: 32, nameTextStyle: { color: CH.ink2, fontSize: 13 },
        min: xb[0], max: xb[1], scale: true, axisLabel: Object.assign({}, (A.axisStyle || {}).axisLabel, { formatter: fmtAx }) }),
      yAxis: Object.assign({}, A.axisStyle || {}, { type: 'value', name: Y.name, nameLocation: 'middle', nameGap: 46, nameTextStyle: { color: CH.ink2, fontSize: 13 },
        min: yb[0], max: yb[1], scale: true, axisLabel: Object.assign({}, (A.axisStyle || {}).axisLabel, { formatter: fmtAx }) }),
      series: [
        { name: '其他公司', type: 'scatter', data: off, itemStyle: { color: CH.ink3 || '#6f7ea3', opacity: 0.22 }, emphasis: { scale: 1.4 }, z: 1 },
        Object.assign({ name: '符合', type: 'scatter', data: on, emphasis: { scale: 1.35, label: { show: true, formatter: (p) => p.data.name, color: CH.ink, fontSize: 12, position: 'top' } }, z: 3 }, ma),
      ],
    };
    chartInst = A.chart(el, opt);
    if (chartInst && !el._xpWired) {
      el._xpWired = true;
      chartInst.on('click', (p) => { if (p && p.data && p.data.code) openCard(p.data.code); });
    }
    el._xpPts = { on: on.map((d) => d.code), off: off.length, q: q.id };
    zeroHint(hit.size);
  }
  function zeroHint(n) {
    const z = $('#xpZero'); if (!z) return;
    const q = QBY[S.q];
    if (n > 0 || !usable(q.id)) { z.hidden = true; return; }
    z.hidden = false;
    z.innerHTML = lvOf(q.id) === 'loose'
      ? '目前沒有公司符合 —— 即使是「寬鬆」門檻。可能是資料月份剛換，過幾天再看看，或換一個問題。'
      : `目前沒有公司符合「${esc(LV.find((x) => x[0] === lvOf(q.id))[1])}」門檻。<button type="button" class="xp-btn" data-loosen="1">放寬條件（改用寬鬆）</button>`;
  }
  function paintSide() {
    const q = QBY[S.q];
    $('#xpSide').innerHTML = `<h3>這代表什麼</h3><p class="xp-mean">${esc(q.mean)}</p>
      <h3>要小心什麼</h3><ul class="xp-care">${q.care.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>
      <h3>名詞小教室</h3><div class="xp-terms">${q.terms.concat(['tv']).map((k) => `<span class="xp-tchip">${esc(TERMS[k][0])}${tb(k)}</span>`).join('')}</div>
      <p class="xp-fine">${esc(FB[q.id] ? '這一題暫用簡化口徑：' + ruleOf(q) : '條件口徑與資料來源見規格文件；門檻可以在圖右上角切換寬鬆／標準／嚴格。')}</p>`;
  }

  /* ---------------- 符合名單 ---------------- */
  function rowHTML(r, why) {
    const A = App();
    const spk = A.sparkSVG ? A.sparkSVG(r.code, { w: 96, h: 26 }) : '';
    const chg = r.chg == null ? '—' : (r.chg > 0 ? '+' : '') + n1(r.chg, 2) + '%';
    return `<tr data-xcode="${esc(r.code)}" tabindex="0"><td class="xp-nm"><b>${esc(r.name)}</b> <span class="xp-cd">${esc(r.code)}</span></td>
      <td><span class="xp-gdot" style="background:${groupColor[r.group] || 'var(--ink-3)'}"></span>${esc(r.group)}</td>
      <td class="xp-spk" data-spk-x="${esc(r.code)}">${spk}</td>
      <td class="num ${r.chg > 0 ? 'up' : r.chg < 0 ? 'down' : ''}">${chg}</td>
      <td class="xp-why">${why.filter(Boolean).map(esc).join('・')}</td>
      <td class="num">${n1(r.tv / 100, 1)}</td></tr>`;
  }
  function tableHTML(list, whyFn, limit, id) {
    const shown = limit ? list.slice(0, limit) : list;
    return `<div class="xp-tbl"><table id="${id}"><thead><tr><th>公司</th><th>族群</th><th>近期走勢</th><th class="num">今日漲跌</th><th>為什麼符合</th><th class="num">成交值（億，20 日均）</th></tr></thead>
      <tbody>${shown.map((r) => rowHTML(r, whyFn(r))).join('')}</tbody></table></div>`;
  }
  function paintList() {
    const q = QBY[S.q], list = matches(q.id), LIM = 20;
    const box = $('#xpList');
    box.innerHTML = `<h3>符合「${esc(q.q)}」的公司 <small>${list.length} 家・依成交值排序（不是好壞名次）・點一列看白話卡</small></h3>`
      + (list.length ? tableHTML(list, q.why, S.full ? 0 : LIM, 'xpTbl')
        + (list.length > LIM ? `<button type="button" class="xp-btn" id="xpMore">${S.full ? '收起，只看前 ' + LIM + ' 家' : '顯示全部 ' + list.length + ' 家'}</button>` : '')
        : '<div class="xp-none">目前沒有符合的公司（可以在上面的圖切到「寬鬆」）。</div>');
    sparkFill(box);
  }
  function sparkFill(box) {
    const A = App(); if (!A.sparkLoad) return;
    A.sparkLoad().then(() => { $$('[data-spk-x]', box).forEach((td) => { if (!td.innerHTML.trim()) td.innerHTML = A.sparkSVG(td.dataset.spkX, { w: 96, h: 26 }); }); }).catch(() => {});
  }

  /* ---------------- C：條件積木（文氏圖） ---------------- */
  function sets() { const o = {}; S.combo.forEach((id) => { o[id] = new Set(matches(id).map((r) => r.code)); }); return o; }
  function regionCodes(mask) {
    const ss = sets(), ids = S.combo;
    return R.filter((r) => ids.every((id, i) => ((mask >> i) & 1) === (ss[id].has(r.code) ? 1 : 0))).sort((a, b) => b.tv - a.tv);
  }
  function paintCombo() {
    $('#xpPick').innerHTML = Q.map((q) => `<label class="xp-pk${usable(q.id) ? '' : ' off'}"><input type="checkbox" value="${q.id}"${S.combo.includes(q.id) ? ' checked' : ''}${usable(q.id) ? '' : ' disabled'}>
      <span>${esc(q.q)}</span><small>${usable(q.id) ? matches(q.id).length + ' 家' : '準備中'}</small></label>`).join('');
    const ids = S.combo.filter(usable), venn = $('#xpVenn'), res = $('#xpCres');
    if (ids.length < 2) {
      venn.innerHTML = '<div class="xp-vhint">再勾一題（共 2～3 題），這裡會畫出兩個圈圈，重疊的地方就是「同時符合」。</div>';
      res.innerHTML = ''; venn.dataset.n = ''; return;
    }
    S.combo = ids;
    const full = (1 << ids.length) - 1;
    if (S.region == null || S.region <= 0 || S.region > full) S.region = full;
    const cnt = {}; for (let m = 1; m <= full; m++) cnt[m] = regionCodes(m).length;
    const A = App(), CH = A.CH || {};
    const cols = [CH.cyan || '#3ee0ff', CH.amber || '#ffb454', CH.violet || '#8b7bff'];
    const W = 420, H = ids.length === 3 ? 330 : 250, r = ids.length === 3 ? 92 : 100;
    const C = ids.length === 2 ? [[W / 2 - 62, 128], [W / 2 + 62, 128]] : [[W / 2 - 58, 120], [W / 2 + 58, 120], [W / 2, 215]];
    // 每一塊的標示位置（手調過：落在那一塊裡面、不壓到別塊的字）
    const P2 = { 1: [W / 2 - 112, 128], 2: [W / 2 + 112, 128], 3: [W / 2, 128] };
    const P3 = { 1: [W / 2 - 100, 92], 2: [W / 2 + 100, 92], 4: [W / 2, 268], 3: [W / 2, 82], 5: [W / 2 - 64, 196], 6: [W / 2 + 64, 196], 7: [W / 2, 156] };
    const P = ids.length === 2 ? P2 : P3;
    const circles = C.map((c, i) => `<circle cx="${c[0]}" cy="${c[1]}" r="${r}" fill="${cols[i]}" fill-opacity=".14" stroke="${cols[i]}" stroke-width="2"/>`).join('');
    const labels = Object.keys(P).map((m) => {
      const [x, y] = P[m], sel = +m === S.region, inter = +m === full;
      return `<g class="xp-rg${sel ? ' on' : ''}" data-region="${m}" role="button" tabindex="0" aria-label="${esc(regionName(+m, ids))}：${cnt[m]} 家">
        <rect x="${x - 26}" y="${y - 17}" width="52" height="30" rx="8"/><text x="${x}" y="${y + 4}" text-anchor="middle" class="${inter ? 'big' : ''}">${cnt[m]}</text></g>`;
    }).join('');
    const names = ids.map((id, i) => {
      const c = C[i], ly = ids.length === 3 && i === 2 ? c[1] + r + 18 : c[1] - r - 10;
      return `<text x="${c[0] + (ids.length === 2 ? (i ? 40 : -40) : i === 0 ? -40 : i === 1 ? 40 : 0)}" y="${ly}" text-anchor="middle" class="xp-vname" fill="${cols[i]}">${esc(QBY[id].q.replace(/[？?]$/, ''))}</text>`;
    }).join('');
    venn.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px" role="img" aria-label="條件交集文氏圖">${circles}${names}${labels}</svg>
      <div class="xp-vkey">點圈圈裡的數字，右邊名單換成那一塊。正中間（${ids.length} 圈重疊）＝全部同時符合。</div>`;
    venn.dataset.n = String(cnt[full]);
    const list = regionCodes(S.region);
    const whyAll = (row) => ids.filter((id, i) => (S.region >> i) & 1).flatMap((id) => QBY[id].why(row).slice(0, 1));
    res.innerHTML = `<h4 id="xpRegT">${esc(regionName(S.region, ids))}：<em id="xpInterN">${list.length}</em> 家</h4>`
      + (list.length ? tableHTML(list, whyAll, 15, 'xpCtbl') + (list.length > 15 ? `<div class="xp-fine">只列成交值前 15 家。</div>` : '')
        : `<div class="xp-none">這一塊目前沒有公司。<button type="button" class="xp-btn" data-cloose="1">把勾選的題目都放寬</button>　或少勾一題。</div>`);
    sparkFill(res);
  }
  function regionName(m, ids) {
    const inn = ids.filter((id, i) => (m >> i) & 1).map((id) => `「${QBY[id].q.replace(/[？?]$/, '')}」`);
    const out = ids.filter((id, i) => !((m >> i) & 1));
    return out.length ? `只符合${inn.join('與')}` : `同時符合${inn.join('與')}`;
  }

  /* ---------------- 白話卡（原地展開，不離開這一頁） ---------------- */
  async function openCard(code) {
    const r = RBY[code]; if (!r) return;
    const box = $('#xpCard'); if (!box) return;
    const A = App();
    const checks = Q.map((q) => {
      if (!usable(q.id)) return `<li class="na">${esc(q.q)}　<small>資料準備中</small></li>`;
      let ok = false; try { ok = q.test(r, thOf(q.id)); } catch (e) { ok = false; }
      return `<li class="${ok ? 'ok' : 'no'}"><span class="mk">${ok ? '✓' : '—'}</span>${esc(q.q)}<small>${esc(q.why(r).filter(Boolean).join('・'))}</small></li>`;
    }).join('');
    const risks = [];
    if (r.loss) risks.push('最近四季合計是虧損，沒有本益比。');
    if (r.vol != null && r.vol >= 50) risks.push(`股價起伏很大（60 日波動度 ${n1(r.vol)}%），一天大漲大跌很常見。`);
    if (r.ret != null && r.ret >= 40) risks.push(`近 60 日已經漲了 ${n1(r.ret)}%，追高要小心。`);
    if (r.ret != null && r.ret <= -25) risks.push(`近 60 日跌了 ${n1(Math.abs(r.ret))}%，先弄清楚為什麼跌。`);
    if (r.spike) risks.push('最新月營收的變化特別大，可能是一次性因素。');
    if (r.tv < 50) risks.push('成交值偏小，買賣價差可能比較大。');
    QBY[S.q].care.slice(0, 1).forEach((c) => risks.push(c));
    box.innerHTML = `<div class="xp-ch"><div><b>${esc(r.name)}</b> <span class="xp-cd">${esc(r.code)}</span><div class="xp-cg"><span class="xp-gdot" style="background:${groupColor[r.group] || 'var(--ink-3)'}"></span>${esc(r.group)}</div></div>
        <button type="button" class="xp-x" id="xpCardX" aria-label="關閉白話卡">×</button></div>
      <div class="xp-csp">${A.sparkSVG ? A.sparkSVG(r.code, { w: 300, h: 64 }) : ''}</div>
      <h4>這家做什麼</h4><p id="xpDo">${esc(r.group)}${r.ind && r.ind !== r.group ? `（產業別：${esc(r.ind)}）` : ''}<span class="xp-load">・讀取中…</span></p>
      <h4>六個問題，它符合哪幾題</h4><ul class="xp-chk">${checks}</ul>
      <h4>要小心什麼</h4><ul class="xp-rk">${risks.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>
      <a class="xp-go" id="xpGo" href="#stock/${esc(r.code)}">看個股頁（K 線、營收、法人）→</a>
      <p class="xp-fine">以上是條件比對的結果，僅供研究，不構成投資建議。</p>`;
    box.hidden = false; box.dataset.code = code;
    $('#xpCardX').onclick = closeCard;
    $('#xpGo').addEventListener('click', () => { setTimeout(closeCard, 0); });
    try {
      const res = await fetch(`data/stock/${encodeURIComponent(code)}.json`);
      const d = res.ok ? await res.json() : null, b = d && d.basics;
      if (box.dataset.code !== code) return;
      const p = $('#xpDo');
      if (p && b) {
        const bits = [];
        if (b.full_name) bits.push(esc(b.full_name));
        bits.push(`屬於「${esc(r.group)}」族群${b.industry ? `，官方產業別是「${esc(b.industry)}」` : ''}`);
        if (b.listed_date) bits.push(`${esc(String(b.listed_date).slice(0, 4))} 年掛牌`);
        if (b.capital_billion) bits.push(`股本約 ${n1(b.capital_billion, 0)} 億元`);
        p.innerHTML = bits.join('，') + '。';
      } else if (p) { const l = $('.xp-load', p); if (l) l.remove(); }
    } catch (e) { const l = $('#xpDo .xp-load'); if (l) l.remove(); }
  }
  function closeCard() { const b = $('#xpCard'); if (b) { b.hidden = true; b.dataset.code = ''; } }

  /* ---------------- 名詞小教室 ---------------- */
  function openTerm(k, btn) {
    const t = TERMS[k], box = $('#xpTerm'); if (!t || !box) return;
    if (!box.hidden && box.dataset.k === k) { box.hidden = true; return; }
    box.innerHTML = `<b>${esc(t[0])}</b><p>${esc(t[1])}</p><p class="xp-use"><b>新手怎麼用：</b>${esc(t[2])}</p>`;
    box.dataset.k = k; box.hidden = false;
    const rc = btn.getBoundingClientRect(), bw = Math.min(320, window.innerWidth - 24);
    box.style.width = bw + 'px';
    box.style.left = Math.max(12, Math.min(window.innerWidth - bw - 12, rc.left - bw / 2)) + 'px';
    const below = rc.bottom + 8, h = box.offsetHeight;
    box.style.top = (below + h > window.innerHeight - 8 ? Math.max(8, rc.top - h - 8) : below) + 'px';
  }

  /* ---------------- 進入點 ---------------- */
  function setQ(id) {
    if (!QBY[id] || id === S.q && built) { return; }
    const h = '#explore/' + id;
    if (location.hash !== h) { location.hash = h; return; }   // route() 會回頭叫 show()
    S.q = id; S.full = false; paintAll(true);
  }
  function paintAll(onlyLens) {
    $('#xpFb').hidden = !FB.any;
    paintQs(); paintLens(); paintSide(); paintList();
    if (!onlyLens) paintCombo(); else paintCombo();
  }
  async function render(sub) {
    const root = $('#v-explore'); if (!root) return;
    root.innerHTML = '<div class="card"><div class="empty">選股探索載入中…</div></div>';
    try { await loadAll(); } catch (e) { root.innerHTML = '<div class="card"><div class="empty">資料載入失敗，請重新整理</div></div>'; return; }
    shell(root); built = true;
    S.q = QBY[sub] ? sub : 'earn';
    paintAll();
  }
  function show(sub) {
    if (!built) return render(sub);
    const id = QBY[sub] ? sub : 'earn';
    if (id !== S.q) { S.q = id; S.full = false; }
    paintAll();
  }
  window.TwExplore = {
    render, show, Q, TERMS,
    /* 給 _uitest.py 對帳用：目前題目、每題的符合集合、條件積木選了哪幾題與交集家數 */
    debug: () => ({ q: S.q, fb: Object.assign({}, FB), n: R.length, combo: S.combo.slice(), region: S.region,
      hits: Object.fromEntries(Q.map((q) => [q.id, matches(q.id).map((r) => r.code)])),
      inter: S.combo.length >= 2 ? regionCodes((1 << S.combo.length) - 1).map((r) => r.code) : [] }),
  };
})();
