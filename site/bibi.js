/* ============================================================================
   比比（右下角客服鈕的天竺鼠）：情境待機＋環狀互動選單（2026-10-11）
   ----------------------------------------------------------------------------
   Andy 10-11：「將右下方的GIF圖多點變化，會依據不同分頁，不同功能，漲跌，白天晚上，假日平日國定假日等情境下去變化…
     目的是讓比比看起來更像真的在陪伴你。並且最好是有新增互動效果，例如可以摸摸他 餵它吃草 跟他玩球 讓他轉圈圈…
     互動紐的形式像圖一這樣游標移動過去，會出現其他互動小圈(上方都會有簡單的物件圖)，點擊後出現對應動作」
   圖一：比比在中間，周圍一圈小圓圈。

   這支只接手 support.js 建好的 #supFab（不重做按鈕）：
     ① 情境待機：依「國定假日 → 週末 → 深夜 → 盤中漲跌 → 分頁」決定比比現在播哪一段，換頁／每 5 分鐘／盤中報價更新時重算，
        換的時候兩張圖交叉淡入淡出（先載好才換，不閃）。
     ② 環狀選單：桌機滑鼠移到比比上展開；手機（html.m4／≤640，或沒有滑鼠的裝置）點一下展開、點空白收起。
        比比在右下角，整圈放不下 —— 展開時比比自己往左上「走出來」到放得下整圈的位置（transform，放開就回原位），
        所以畫面跟圖一一樣：比比在正中間、10 個小圈繞一整圈，而且整圈一定在視窗內。
     ③ 點小圈：比比播對應動作＋小特效（愛心／草屑／球／星星…），播完回情境待機；播的時候其他小圈冷卻（連點不爆）。
        點比比本體：桌機照舊打開客服面板（既有行為、既有驗收不變）；手機第一下是展開環，環裡的「問比比」才開客服。
     ④ 互動次數記在這台裝置（localStorage tw.bibi.n，不送伺服器），比比偶爾回一句「今天第 3 次摸我了～」。
   客服鈕被關掉（html.fab-off）、管理區（fab.hidden）、被抽屜蓋住（supaway）時，環與提示泡泡一律不出現。
   素材：site/brand/bibi/<名稱>.webp（160px 動態 WebP，scripts/anim/bibi_site.py 產生，用到才載）。
   ★ 動畫單位新素材到了：跑 bibi_site.py 轉檔 → 改下面 IDLE／ACTS 的 file（want 欄寫的就是要換成的新素材名）。
   ============================================================================ */
(function () {
  'use strict';

  /* ---------- 素材對照表（MAP）：情境／動作 → 檔名（site/brand/bibi/<file>.webp） ----------
     want＝動畫單位正在做的專屬素材；到了就把 file 改成 want（MS 也補上它的總長，bibi_site.py 最後一行會印）。 */
  const MS = {   // 每組一輪的毫秒數；bibi_site.py 最後一行印的就是這張表
    // 情境待機（循環）
    wave: 1000, coins: 840, growth: 1290, magnifier: 1050, fire: 1050, calc: 1160, news: 1070, piggy: 1030, calendar: 1160,
    bulb: 1050, clock: 1060, star_save: 1000, face_proud: 1630,
    weekend: 1560, sleep_loop: 1800, idle_down: 1440, idle_bigup: 1200,
    festival_newyear: 1560, festival_dragon: 1560, festival_moon: 1560, festival_xmas: 1560,
    // 互動（動畫單位 G1／G2 專屬素材；播一輪＝這個毫秒數就回情境待機）
    pet: 2350, eat_grass: 2520, ball: 2250,   // ball／eat_grass／pet 已剪掉開頭 700～900ms 的待機格（bibi_site.py TRIM_HEAD）
    spin: 2080, highfive: 1480, dance: 1560, hug: 1640, wake_once: 1440, selfie: 1480,
    // 動作編排的零件（10-11 晚；PART 那張表）：跑步替代 hop_l／hop_r（循環）、抬頭看 face_curious、東張西望 tilt
    hop_l: 840, hop_r: 840, face_curious: 1470, tilt: 1040, face_star: 1370,
    // 動畫單位 10-11 晚骨架重做第 1 組：開心的跳（待機預設，循環）、接東西（播一次；第 3 格 370ms 接到）
    happy_hop: 1230, receive: 1380, receive_grass: 1380, receive_ball: 1380,
  };
  const IDLE = {
    holiday: { file: 'idle_bigup' },      // 國定假日：實際用哪一款看 HOLIDAY（依節日名稱挑帽子）；表外的節日用這個
    xmas: { file: 'festival_xmas' },      // 12/24～25（行憲紀念日那天走 HOLIDAY，也是聖誕帽）
    weekend: { file: 'weekend' },
    night: { file: 'sleep_loop' },
    up2: { file: 'idle_bigup' },
    up: { file: 'face_proud' },
    down: { file: 'idle_down' },          // 跌一律「安慰」款（Andy：陪伴，不要驚恐）；大跌、小跌只差說明句
    down2: { file: 'idle_down' },
    overview: { file: 'wave' }, flow: { file: 'coins' }, rotation: { file: 'growth' }, industry: { file: 'magnifier' },
    themes: { file: 'fire' }, stock: { file: 'calc' }, etf: { file: 'piggy' }, season: { file: 'calendar' },
    explore: { file: 'bulb' }, market: { file: 'clock' }, watch: { file: 'star_save' }, news: { file: 'news' }, other: { file: 'wave' },
  };
  /* 國定假日（site/tw_holidays.json 的名稱）→ 節日款。比對用「包含」，所以「春節」「和平紀念日補假」都對得到。
     肅穆的紀念日（和平紀念日、清明節）不戴慶祝帽，用週末放鬆款；颱風等臨時休市也是放鬆款。 */
  const HOLIDAY = [
    [['春節', '除夕', '開國紀念日', '元旦'], 'festival_newyear'],
    [['端午'], 'festival_dragon'],
    [['中秋'], 'festival_moon'],
    [['行憲紀念日', '聖誕'], 'festival_xmas'],
    [['和平紀念日', '清明', '颱風', '停市'], 'weekend'],
    [['國慶', '光復', '兒童節', '勞動節', '教師節', '軍人節'], 'idle_bigup'],
  ];
  const holFile = (name) => { for (const [ks, f] of HOLIDAY) if (ks.some((k) => String(name).indexOf(k) >= 0)) return f; return IDLE.holiday.file; };
  /* 分頁（hash 第一段）→ 待機情境＋一句話 */
  const PAGES = [
    [['overview', ''], 'overview', '歡迎回來！比比陪你看今天的盤勢'],
    [['flow'], 'flow', '比比在追錢往哪個族群跑'],
    [['heatmap', 'industry', 'heat'], 'industry', '比比拿放大鏡看產業細節'],
    [['themes'], 'themes', '這個題材好熱，比比也燒起來了'],
    [['stock'], 'stock', '比比幫你按計算機算這一檔'],
    [['etf'], 'etf', '存 ETF 像存錢筒，一點一點變多'],
    [['season'], 'season', '比比翻日曆看季節規律'],
    [['earnings', 'calendar'], 'season', '財報日子比比幫你記著'],
    [['explore'], 'explore', '比比想到選股好點子了！'],
    [['market'], 'market', '比比幫你盯著盤中時間'],
    [['watch'], 'watch', '你的自選股比比幫你收好了'],
    [['news', 'event', 'events', 'delivery'], 'news', '比比在看今天的財經消息'],
  ];
  /* 環狀選單的 10 個小圈（順時針，從正上方開始）。fx＝點了冒什麼小特效；say＝回應（隨機一句）；cnt＝第 N 次的回應 */
  /* once：素材是播一次的專屬動作（播一輪＝MS 毫秒就回待機）；沒有 once 的是現有素材代替（循環素材，播兩輪） */
  const ACTS = [
    { id: 'ask', name: '問比比', ask: true },
    { id: 'popcorn', name: '爆米花', file: 'face_star', once: true, fx: 'star', say: ['爆米花跳！啵啵啵～', '開心到跳起來了！'], cnt: (n) => `今天爆米花跳了 ${n} 次！` },
    { id: 'pet', name: '摸摸頭', file: 'pet', once: true, was: 'face_love', fx: 'heart', say: ['好舒服～', '再摸一下嘛', '嘿嘿，癢癢的'], cnt: (n) => `今天第 ${n} 次摸我了～` },
    { id: 'grass', name: '餵牧草', file: 'eat_grass', once: true, was: 'boba', fx: 'grass', say: ['嚼嚼嚼…牧草好香！', '謝謝你餵我～'], cnt: (n) => `今天吃了 ${n} 口牧草，好飽～` },
    { id: 'ball', name: '玩球', file: 'ball', once: true, was: 'hop_l', fx: 'ball', say: ['接到了！', '再丟一次！'], cnt: (n) => `今天陪我玩了 ${n} 次球！` },
    { id: 'spin', name: '轉圈圈', file: 'spin', once: true, was: 'tilt', fx: 'star', say: ['轉轉轉～有點暈', '咕嚕咕嚕轉一圈！'], cnt: (n) => `今天轉了 ${n} 圈，頭好暈～` },
    { id: 'five', name: '擊掌', file: 'highfive', once: true, was: 'face_clap', fx: 'star', say: ['耶！擊掌！', '啪！今天也一起加油'], cnt: (n) => `今天第 ${n} 次擊掌，默契 100！` },
    { id: 'dance', name: '跳舞', file: 'dance', once: true, was: 'celebrate', fx: 'note', say: ['跳起來～', '比比的舞步帥嗎？'], cnt: (n) => `今天跳了 ${n} 支舞！` },
    { id: 'hug', name: '抱抱', file: 'hug', once: true, was: 'heart_wish', fx: 'heart', say: ['抱抱～比比陪著你', '暖暖的'], cnt: (n) => `今天第 ${n} 個抱抱，好幸福` },
    { id: 'sleep', name: '睡覺', file: 'sleep_loop', was: 'face_sleepy', fx: 'z', sleep: true, say: ['比比去睡一下，Zzz…'], wake: { name: '叫醒', file: 'wake_once', once: true, was: 'face_star', fx: 'star', say: ['醒來了！繼續陪你看盤'] } },
    { id: 'selfie', name: '拍照比耶', file: 'selfie', once: true, was: 'face_wink', fx: 'flash', say: ['咔嚓！比耶～', '拍得可愛嗎？'], cnt: (n) => `今天拍了 ${n} 張，比比是網美` },
  ];
  /* 素材對照（was＝10-11 G1／G2 交件前用的替代素材，留著是為了萬一新素材要退回時知道原本是哪一組） */
  /* 小圈上的物件圖：動畫單位 10-11 交的 10 個圖示（docs/anim/bibi_icons → brand/bibi/icons/*.webp，奶油白圓底＋粗描邊，深淺主題都清楚）。
     沒列在這裡的（叫醒）用下面的線條圖示，外框照圖示同款畫。 */
  const ICON_IMG = { ask: 'chat', pet: 'hand', grass: 'grass', ball: 'ball', spin: 'spin', five: 'highfive', dance: 'music', hug: 'heart', sleep: 'moon', selfie: 'camera' };
  const SVG = {
    ask: '<path d="M5 5.5h14a2.5 2.5 0 0 1 2.5 2.5v7A2.5 2.5 0 0 1 19 17.5h-6l-4.2 3.3v-3.3H5A2.5 2.5 0 0 1 2.5 15V8A2.5 2.5 0 0 1 5 5.5z" fill="#7cc4ff" fill-opacity=".35" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M10 9.6a2 2 0 1 1 2.6 1.9c-.5.2-.6.5-.6 1v.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="12" cy="14.9" r=".95" fill="currentColor"/>',
    pet: '<ellipse cx="12" cy="15" rx="5" ry="4.2" fill="#ffb3c4" stroke="currentColor" stroke-width="1.5"/><circle cx="6.4" cy="9.6" r="1.9" fill="#ffb3c4" stroke="currentColor" stroke-width="1.4"/><circle cx="10" cy="7" r="1.9" fill="#ffb3c4" stroke="currentColor" stroke-width="1.4"/><circle cx="14" cy="7" r="1.9" fill="#ffb3c4" stroke="currentColor" stroke-width="1.4"/><circle cx="17.6" cy="9.6" r="1.9" fill="#ffb3c4" stroke="currentColor" stroke-width="1.4"/>',
    grass: '<path d="M4 20.5h16" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M7 20.5C6.6 15 5 12 3.5 10.5c3 .8 5 3.6 5.4 7.4M12 20.5c-.2-6 .3-10 1.6-14 1 4.3.8 9.2-.4 14M17 20.5c.3-4 2-7 3.8-8.6-.4 3.6-1.4 6.4-2.6 8.6" fill="#6cc46a" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>',
    ball: '<circle cx="12" cy="12" r="8.2" fill="#ffad5c" stroke="currentColor" stroke-width="1.6"/><path d="M4.3 9.6c4.6 1.6 10.8 1.6 15.4 0M4.3 14.4c4.6-1.6 10.8-1.6 15.4 0M12 3.8c-2.6 5-2.6 11.4 0 16.4" fill="none" stroke="currentColor" stroke-width="1.3"/>',
    spin: '<path d="M19 12a7 7 0 1 1-2.1-5" fill="none" stroke="#b28cff" stroke-width="2.4" stroke-linecap="round"/><path d="M19 12a7 7 0 1 1-2.1-5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/><path d="M17.6 3.2l-.4 4.2-4.1-.6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="1.6" fill="currentColor"/>',
    five: '<path d="M8 20.5c-2.2-1.4-3.6-3.6-3.6-6.4V9.5a1.4 1.4 0 0 1 2.8 0v3M7.2 12V5.6a1.4 1.4 0 0 1 2.8 0v6M10 11.5V4.4a1.4 1.4 0 0 1 2.8 0v7.1M12.8 11.6V5.6a1.4 1.4 0 0 1 2.8 0v8.2c0 3.7-2.4 6.7-6 6.7" fill="#ffd36b" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/><path d="M18.5 4.5l1.6-1.6M19.5 8.4h2.2M17.8 1.8v0" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    dance: '<path d="M9 17.5V6.2l10-2.2v11.3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><ellipse cx="6.8" cy="17.6" rx="2.6" ry="2.1" fill="#ff8fd1" stroke="currentColor" stroke-width="1.4"/><ellipse cx="16.8" cy="15.4" rx="2.6" ry="2.1" fill="#ff8fd1" stroke="currentColor" stroke-width="1.4"/><path d="M9 9.6l10-2.2" stroke="currentColor" stroke-width="1.7"/>',
    hug: '<path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.2a4.3 4.3 0 0 1 7.5 2.6C19.5 15.4 12 20 12 20z" fill="#ff7a93" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M8.6 10.2c.3-.9 1-1.4 1.9-1.4" fill="none" stroke="#fff" stroke-width="1.3" stroke-linecap="round"/>',
    sleep: '<path d="M15.5 18.6A7.6 7.6 0 0 1 9.2 5.1a7.6 7.6 0 1 0 9.6 10.7 7.6 7.6 0 0 1-3.3 2.8z" fill="#ffe08a" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M14.6 4.2h3.6l-3.6 4h3.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
    popcorn: '<g fill="#fff3c4" stroke="currentColor" stroke-width="1.2"><circle cx="7.6" cy="9.4" r="2.5"/><circle cx="16.4" cy="9.4" r="2.5"/><circle cx="12" cy="7.6" r="2.9"/><circle cx="9.6" cy="5.2" r="2.1"/><circle cx="14.5" cy="5.3" r="2.1"/></g><path d="M5.6 10.8h12.8l-1.7 10a1.5 1.5 0 0 1-1.5 1.3H8.8a1.5 1.5 0 0 1-1.5-1.3z" fill="#fff"/><path d="M9.3 10.8l.8 11.3M14.7 10.8l-.8 11.3" stroke="#ec5a4c" stroke-width="2.3"/><path d="M5.6 10.8h12.8l-1.7 10a1.5 1.5 0 0 1-1.5 1.3H8.8a1.5 1.5 0 0 1-1.5-1.3z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>',
    wake: '<circle cx="12" cy="12" r="4.4" fill="#ffc94d" stroke="currentColor" stroke-width="1.5"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    selfie: '<rect x="3" y="7" width="18" height="12.5" rx="2.6" fill="#8fd3ff" fill-opacity=".45" stroke="currentColor" stroke-width="1.6"/><path d="M8.4 7l1.4-2.4h4.4L15.6 7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="12" cy="13.2" r="3.4" fill="#fff" fill-opacity=".6" stroke="currentColor" stroke-width="1.6"/><circle cx="17.6" cy="9.8" r=".9" fill="currentColor"/>',
  };
  /* 小特效粒子（不用表情符號：深淺主題都用同一組有底色的 SVG） */
  const FX = {
    heart: '<svg viewBox="0 0 24 24"><path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7.2a4.3 4.3 0 0 1 7.5 2.6C19.5 15.4 12 20 12 20z" fill="#ff6f8e"/></svg>',
    grass: '<svg viewBox="0 0 24 24"><path d="M6 20c1-6 4-11 10-15-3 5-4.5 10-5 15z" fill="#5fbf5a"/></svg>',
    ball: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="#ffa54d" stroke="#7a3d00" stroke-width="1.2"/><path d="M3.6 9.6c5 1.7 11.8 1.7 16.8 0M12 3c-2.8 5.6-2.8 12.4 0 18" fill="none" stroke="#7a3d00" stroke-width="1.1"/></svg>',
    star: '<svg viewBox="0 0 24 24"><path d="M12 2.5l2.7 6.2 6.8.6-5.1 4.5 1.5 6.6L12 17l-5.9 3.4 1.5-6.6-5.1-4.5 6.8-.6z" fill="#ffd23f" stroke="#a87700" stroke-width=".8"/></svg>',
    note: '<svg viewBox="0 0 24 24"><path d="M10 17V5l9-2v11" fill="none" stroke="#c15fd6" stroke-width="2.2"/><circle cx="7.5" cy="17.5" r="3" fill="#c15fd6"/><circle cx="16.5" cy="15" r="3" fill="#c15fd6"/></svg>',
    z: '<svg viewBox="0 0 24 24"><path d="M6 6h11L7 18h11" fill="none" stroke="#7aa7ff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    flash: '<svg viewBox="0 0 24 24"><path d="M12 1l2.2 8.8L23 12l-8.8 2.2L12 23l-2.2-8.8L1 12l8.8-2.2z" fill="#fff6b0" stroke="#e0b400" stroke-width=".8"/></svg>',
  };

  const SLEEP_FILE = 'sleep_loop';   // 點「睡覺」之後一直播的睡覺循環（直到點「叫醒」）
  const NLS = 'tw.bibi.n';       // 互動次數（這台裝置；viewreset 的 KEEP_PREFIX 有 tw.bibi.）
  const IDLE_EVERY = 5 * 60 * 1000;
  const html = document.documentElement;
  const isMob = () => html.classList.contains('m4') || window.innerWidth <= 640;
  const tapMode = () => isMob() || !(window.matchMedia && matchMedia('(hover: hover)').matches);
  const reduce = () => !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const fabOff = () => html.classList.contains('fab-off');
  const $ = (id) => document.getElementById(id);
  /* 素材版本戳：換了 brand/bibi/ 裡的圖（同檔名）就改這個字串，使用者不用清快取就拿到新圖（10-11 週末款換圖後 Andy 仍看到舊圖） */
  const AV = '1011c';
  const src = (f) => 'brand/bibi/' + f + '.webp?v=' + AV;
  const T = { now: null, pct: undefined, hol: null };   // 驗收注入（Bibi.test）：假時間、假漲跌、假休市表

  /* ---------- 樣式 ---------- */
  const CSS = `
/* 比比圖：一律用同一個裁切框的 160px 素材（腳底同一高度），顯示得比按鈕大一點、往上長，換動作時大小位置不跳 */
.supfab.supgifonly .supgif.bibiimg{position:absolute;width:104px;height:104px;left:calc(50% - 52px);bottom:-3px;max-width:none;transform:none;transition:opacity .35s ease;pointer-events:none}
.supfab.supgifonly:hover .supgif.bibiimg{transform:none}
.supfab.supgifonly .supgif.bibiimg.bibiback{opacity:0}
@media (max-width:820px){.supfab.supgifonly .supgif.bibiimg{width:84px;height:84px;left:calc(50% - 42px);bottom:-2px}}
.supfab.bibispin .supgif.bibiimg{animation:bibispin .9s cubic-bezier(.45,.05,.4,1) 2!important;transform-origin:50% 72%!important}
@keyframes bibispin{from{transform:scale(var(--bs,1)) rotate(0)}to{transform:scale(var(--bs,1)) rotate(360deg)}}
/* 環：以比比中心為圓心（left/top＝圓心座標、寬高 0）；底下一塊透明圓盤讓滑鼠在圈裡移動不會收起（在客服鈕底下一層） */
.bibiring{position:fixed;left:0;top:0;width:0;height:0;z-index:1199;pointer-events:none}
.bibiring[hidden]{display:none}
.bibiring .bzone{position:absolute;border-radius:50%;pointer-events:auto;background:radial-gradient(closest-side,color-mix(in srgb,var(--panel-2) 86%,transparent) 0,color-mix(in srgb,var(--panel-2) 74%,transparent) 82%,transparent 100%);-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px);opacity:0;transition:opacity .25s}
.bibiring.on .bzone{opacity:1}
.bibiring .btrack{position:absolute;left:0;top:0;width:1px;height:1px;overflow:visible;pointer-events:none;opacity:0;transition:opacity .3s}
.bibiring .btrack path{fill:none;stroke:color-mix(in srgb,var(--cyan) 60%,transparent);stroke-width:2;stroke-dasharray:5 5}
.bibiring.on .btrack{opacity:1}
/* 環打開時比比放大一點（走到正中間當主角） */
.supfab.bibiopen{--bs:1.12}
.supfab.bibiopen .supgif.bibiimg{transform:scale(var(--bs));transform-origin:50% 92%;transition:opacity .35s ease,transform .28s}
.bibiring .bopt{position:absolute;left:0;top:0;width:42px;height:42px;margin:-21px 0 0 -21px;border-radius:50%;pointer-events:auto;cursor:pointer;padding:0;display:grid;place-items:center;
  background:var(--panel-2);color:var(--ink);border:1.5px solid var(--line-2);box-shadow:0 6px 16px -6px rgba(0,0,0,.45);
  transform:translate(0,0) scale(.3);opacity:0;transition:transform .32s cubic-bezier(.3,1.5,.5,1),opacity .2s,border-color .15s,background .15s;-webkit-tap-highlight-color:transparent}
.bibiring.on .bopt{transform:translate(var(--x),var(--y)) scale(1);opacity:1}
.bibiring .bopt svg{width:26px;height:26px;display:block;pointer-events:none}
.bibiring .bopt img{width:100%;height:100%;display:block;pointer-events:none;border-radius:50%}
/* 有動畫單位圖示的小圈：圖示自己就是圓底＋描邊，按鈕不再加底色與框（只留陰影）；叫醒（線條圖示）用同款奶油底＋深描邊 */
.bibiring .bopt.bpic{background:none;border:0}
.bibiring .bopt.bpic:hover,.bibiring .bopt.bpic:focus-visible{background:none;box-shadow:0 0 0 3px var(--cyan),0 6px 16px -6px rgba(0,0,0,.45)}
.bibiring .bopt.bsvg2{background:#fdf5e9;border:2.5px solid #1a0907;color:#1a0907}
.bibiring .bopt:hover,.bibiring .bopt:focus-visible{border-color:var(--cyan);background:color-mix(in srgb,var(--cyan) 16%,var(--panel-2));transform:translate(var(--x),var(--y)) scale(1.13);outline:none}
.bibiring .bopt.bask{border-color:var(--cyan)}
.bibiring .bopt.pg-off,.bibiring.on .bopt.pg-off{transform:translate(0,0) scale(.3);opacity:0;pointer-events:none}
.bibiring .bopt.bnext{position:absolute}
.bibiring .bopt.bnext .bpg{position:absolute;left:50%;bottom:-15px;transform:translateX(-50%);font-style:normal;font-size:11px;line-height:1;color:var(--ink-2);white-space:nowrap;pointer-events:none}
.bibiring.cool .bopt:not(.bask):not(.bnext){opacity:.45;cursor:default}
.bibiring.cool .bopt:not(.bask):not(.bnext):hover{transform:translate(var(--x),var(--y)) scale(1)}
.bibitip{position:fixed;z-index:1202;max-width:220px;padding:7px 11px;border-radius:12px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);
  font-size:13px;line-height:1.45;box-shadow:0 10px 24px -10px rgba(0,0,0,.55);pointer-events:none;opacity:0;transform:translateY(4px);transition:opacity .18s,transform .18s;white-space:normal}
.bibitip.on{opacity:1;transform:none}
.bibitip[hidden]{display:none}
.bibifx{position:fixed;z-index:1202;width:20px;height:20px;margin:-10px 0 0 -10px;pointer-events:none;animation:bibifx 1.15s ease-out forwards}
.bibifx svg{width:100%;height:100%;display:block}
@keyframes bibifx{0%{transform:translate(0,0) scale(.4) rotate(0);opacity:0}15%{opacity:1}100%{transform:translate(var(--fx),var(--fy)) scale(1) rotate(var(--fr));opacity:0}}
.bibiflash{position:fixed;z-index:1203;width:150px;height:150px;margin:-75px 0 0 -75px;border-radius:50%;pointer-events:none;background:radial-gradient(closest-side,#fff,rgba(255,255,255,0));animation:bibiflash .5s ease-out forwards}
@keyframes bibiflash{0%{opacity:0}20%{opacity:.95}100%{opacity:0}}
html.fab-off .bibiring,html.fab-off .bibitip,html.fab-off .bibifx,html.fab-off #bibiStage{display:none!important}
/* ---------- 動作編排（10-11 晚）：比比整顆可以離開右下角 ----------
   #supFab 本身不動（拖曳記位、避讓判斷都量它）；動的是裡面包著兩張圖的 .bibiwrap（位移）與 .bibibody（擠壓伸展／傾斜），
   都在 position:fixed 的鈕裡面，用 transform 位移 → 不撐出捲軸、不擋點擊（pointer-events:none）。
   道具（球、草、手、星星…）放在 #bibiStage：fixed 蓋整個視窗、overflow:hidden（道具飛到哪都不會撐出捲軸，手機也留在 390 內）。 */
.supfab .bibiwrap,.supfab .bibibody{position:absolute;inset:0;pointer-events:none;display:block}
.supfab .bibiwrap{will-change:transform}
.supfab .bibibody{transform-origin:50% 96%}
.supfab .bibihop{position:absolute;inset:0;pointer-events:none;display:block;transform-origin:50% 96%}
/* 開心的跳（待機預設）：每 2.4 秒蹲→彈起→落地壓扁→小回彈；環開著、動作中、待機小動作中都先停 */
.supfab.bibihappy:not(.bibiopen):not([data-bibi-run]):not([data-bibi-act]) .bibihop{animation:bibihappy 2.4s ease-in-out infinite}
@keyframes bibihappy{0%,44%,100%{transform:none}50%{transform:scale(1.07,.9)}58%{transform:translateY(-15px) scale(.95,1.07)}66%{transform:translateY(-18px)}74%{transform:translateY(0) scale(1.08,.9)}80%{transform:translateY(-5px) scale(.98,1.03)}86%{transform:translateY(0) scale(1.03,.97)}92%{transform:none}}
@media (max-width:820px){@keyframes bibihappy{0%,44%,100%{transform:none}50%{transform:scale(1.07,.9)}58%{transform:translateY(-11px) scale(.95,1.07)}66%{transform:translateY(-13px)}74%{transform:translateY(0) scale(1.08,.9)}80%{transform:translateY(-4px) scale(.98,1.03)}86%{transform:translateY(0) scale(1.03,.97)}92%{transform:none}}}
@media (prefers-reduced-motion:reduce){.supfab.bibihappy .bibihop{animation:none!important}}
.supfab.bibirun{pointer-events:none}
.supfab.bibirun .supgif.bibiimg{transition:opacity .1s linear}   /* 動作中換圖要快（.35s 的交叉淡化在跑步時會看到半透明的比比） */
#bibiStage{position:fixed;left:0;top:0;width:100vw;height:100vh;overflow:hidden;pointer-events:none;z-index:1201}
#bibiStage>*{position:absolute;left:0;top:0;pointer-events:none;will-change:transform}
#bibiStage svg{display:block;width:100%;height:100%;overflow:visible}
#bibiStage .bshadow{border-radius:50%;background:radial-gradient(closest-side,rgba(20,10,5,.32),rgba(20,10,5,0))}
#bibiStage .bchew{font-size:12px;font-weight:800;line-height:1;padding:3px 7px;border-radius:999px;background:#fdf5e9;color:#5a3a12;border:1.5px solid #2b1611;white-space:nowrap;opacity:0;animation:bibichew .9s ease-out forwards}
@keyframes bibichew{0%{opacity:0;transform:translate(var(--x),var(--y)) scale(.6)}20%{opacity:1;transform:translate(var(--x),calc(var(--y) - 6px)) scale(1.05)}100%{opacity:0;transform:translate(var(--x),calc(var(--y) - 26px)) scale(1)}}
@media (prefers-reduced-motion:reduce){
  .bibiring .bopt{transition:opacity .15s,border-color .15s;transition-delay:0s!important}
  .bibiring .bopt,.bibiring.on .bopt{transform:translate(var(--x),var(--y)) scale(1)}
  .bibifx{animation-duration:.8s}
}`;

  /* ---------- 小工具 ---------- */
  function tpe() {   // 台北時間的年月日時分（不靠使用者電腦時區）
    const d = T.now ? new Date(T.now) : new Date();
    const t = new Date(d.getTime() + 8 * 3600 * 1000);
    const ymd = t.toISOString().slice(0, 10);
    return { ymd, dow: t.getUTCDay(), hm: t.getUTCHours() * 60 + t.getUTCMinutes() };
  }
  let HOL = null;
  function loadHol() {
    if (HOL) return Promise.resolve(HOL);
    const p = window.CalGrid && window.CalGrid.load ? window.CalGrid.load() : fetch('tw_holidays.json', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)).then((j) => (j && j.days) || {});
    return p.then((d) => { HOL = d || {}; return HOL; }).catch(() => { HOL = {}; return HOL; });
  }
  /* 盤中加權漲跌幅：即時層（live.js）有抓到加權（t00）才用；沒有就不判斷漲跌（不拿昨天的收盤冒充今天） */
  function idxPct() {
    if (T.pct !== undefined) return T.pct;
    const L = window.Live, q = L && L.quotes && L.quotes.t00;
    return q && q.chgPct != null && isFinite(q.chgPct) ? +q.chgPct : null;
  }
  function pageOf() {
    const h = (location.hash || '').replace(/^#/, ''), parts = h.split('/'), head = parts[0] || '';
    /* 子分頁比母分頁更準的幾個（#flow 預設會轉到 #flow/rotation、#themes 會轉到 #heatmap/theme） */
    const sub = head + '/' + (parts[1] || '');
    if (sub === 'flow/rotation') return ['rotation', '比比在看族群輪動，錢一圈一圈長大'];
    if (sub === 'heatmap/theme') return ['themes', '這個題材好熱，比比也燒起來了'];
    if (sub === 'etf/cal') return ['season', 'ETF 配息日子比比幫你記著'];
    if (sub === 'etf/inc') return ['stock', '比比幫你按計算機試算存股'];
    if (sub === 'explore/news') return ['news', '比比在看今天的財經消息'];
    for (const [heads, key, say] of PAGES) if (heads.indexOf(head) >= 0) return [key, say];
    return ['other', '比比在這裡陪你，有問題可以問我'];
  }
  const pf = (p) => Math.abs(p).toFixed(Math.abs(p) >= 10 ? 1 : 2).replace(/\.?0+$/, '') ;
  /** 情境待機：回 { key, file, say }，優先序 國定假日 → 週末 → 深夜 → 盤中漲跌 → 分頁 */
  function idle() {
    const r = idle0();
    r.happy = NOT_HAPPY.indexOf(r.key) < 0;
    if (r.happy && PART.happy) r.file = PART.happy;
    return r;
  }
  function idle0() {
    const t = tpe(), hol = T.hol || HOL || {};
    if (hol[t.ymd]) return { key: 'holiday', file: holFile(hol[t.ymd]), say: `今天${String(hol[t.ymd]).replace(/（.*$/, '')}，台股休市，比比也放假一天～` };
    if (t.dow === 0 || t.dow === 6) return { key: 'weekend', say: '週末不開盤，比比喝杯珍奶放鬆一下～' };
    if (t.hm >= 23 * 60 || t.hm < 6 * 60) return { key: 'night', say: '深夜了，比比想睡覺…你也早點休息' };
    if (t.hm >= 9 * 60 && t.hm <= 13 * 60 + 30) {
      const p = idxPct();
      if (p != null && p !== 0) {
        if (p >= 1) return { key: 'up2', say: `今天大盤漲 ${pf(p)}%，比比好開心！` };
        if (p > 0) return { key: 'up', say: `大盤小漲 ${pf(p)}%，比比偷偷得意～` };
        if (p <= -1) return { key: 'down2', say: `大盤跌 ${pf(p)}%，先深呼吸，比比陪著你` };
        return { key: 'down', file: (IDLE[pageOf()[0]] || IDLE.other).file, say: `大盤小跌 ${pf(p)}%，沒關係，比比陪你` };   // 小跌也開心的跳（Andy 10-11 晚只留「大跌」安慰）
      }
    }
    if (/-12-2[45]$/.test(t.ymd)) return { key: 'xmas', say: '聖誕快樂！比比戴上聖誕帽陪你看盤～' };
    const [k, say] = pageOf();
    return { key: k, say };
  }

  /* ---------- 互動次數（只存這台裝置） ---------- */
  function counts() {
    const today = tpe().ymd;
    let o = null; try { o = JSON.parse(localStorage.getItem(NLS) || 'null'); } catch (e) { o = null; }
    if (!o || typeof o !== 'object') o = { d: today, c: {}, all: 0 };
    if (o.d !== today) { o.d = today; o.c = {}; }
    return o;
  }
  function bump(id) {
    const o = counts(); o.c[id] = (o.c[id] || 0) + 1; o.all = (o.all || 0) + 1;
    try { localStorage.setItem(NLS, JSON.stringify(o)); } catch (e) { /* 私密視窗：只是不記，照樣互動 */ }
    return o.c[id];
  }

  /* ---------- 圖層：兩張 img 交叉淡入淡出 ---------- */
  let fab = null, imgs = [], front = 0, shown = '', want = '', mode = 'idle', idleNow = null, actTimer = 0, sleeping = false, sayTimer = 0;
  let replay = 0, showTok = 0;
  /** once＝播一次的專屬動作：網址加 #n 讓瀏覽器從第一格重播（同一個檔、同一份快取；10-11 實測換 #片段 會重播、換新 <img> 不會） */
  function show(file, once) {
    if (!fab) return;
    want = file;
    if (file === shown && !once) return;
    const back = imgs[1 - front], url = src(file) + (once ? '#r' + (++replay) : ''), tok = ++showTok;
    let done = false;
    const swap = () => {
      /* 只認最後一次 show()，而且只換一次（load 與保險計時器都可能叫到；換兩次 front 會翻回舊圖） */
      if (done || tok !== showTok || want !== file || imgs[1 - front] !== back) return;
      done = true;
      back.classList.remove('bibiback'); imgs[front].classList.add('bibiback');
      front = 1 - front; shown = file; fab.dataset.bibi = file;
    };
    if (back.getAttribute('src') === url && back.complete && back.naturalWidth) { swap(); return; }
    back.onload = swap; back.onerror = () => { if (want === file) { shown = ''; } };
    back.setAttribute('src', url);
    if (once) setTimeout(() => { if (want === file && shown !== file && back.complete && back.naturalWidth) swap(); }, 400);   // 只換 #片段 時有的瀏覽器不再發 load
  }
  function applyIdle() {
    if (!fab) return;
    idleNow = idle();
    fab.dataset.bibiIdle = idleNow.key;
    if (mode !== 'idle') return;
    const f = idleFile();
    /* 開心的跳（Andy 10-11 晚：「大部分情況盡量維持開心的跳」）：素材 happy_hop 還沒到 → 圖照情境款、整顆用 CSS 小跳；
       躺著／睡著／安慰的那幾款圖跳起來很怪，不跳（weekend 躺墊子、sleep_loop、idle_down）。 */
    fab.classList.toggle('bibihappy', !!(idleNow.happy && !sleeping && !PART.happy && NOHOP.indexOf(f) < 0));
    show(f);
  }
  /* 不跳「開心的跳」的情境：深夜睡覺、國定假日（節日帽／肅穆紀念日）、聖誕帽、大跌安慰（Andy 10-11 晚點名的例外） */
  const NOT_HAPPY = ['night', 'holiday', 'xmas', 'down2'];
  const NOHOP = ['weekend', 'sleep_loop', 'idle_down'];

  /* ---------- 提示泡泡 ---------- */
  let tip = null;
  function tipText() { return sleeping ? '比比睡著了…點「叫醒」叫他起來' : (idleNow ? idleNow.say : ''); }
  function say(text, ms) {
    if (!tip || !fab || fabOff() || fab.hidden) return;
    tip.textContent = text; tip.hidden = false;
    placeTip();
    requestAnimationFrame(() => tip.classList.add('on'));
    clearTimeout(sayTimer);
    if (ms) sayTimer = setTimeout(() => { if (ring && ring.classList.contains('on') || hoverFab) { tip.textContent = tipText(); placeTip(); } else hideTip(); }, ms);
  }
  function hideTip() { if (!tip) return; tip.classList.remove('on'); clearTimeout(sayTimer); sayTimer = setTimeout(() => { if (!tip.classList.contains('on')) tip.hidden = true; }, 200); }
  function placeTip() {
    if (!tip || tip.hidden) return;
    /* 比比跑出去時泡泡只跟著他左右走（不跟著上下彈，不然字會抖）；摸摸頭時手在頭上 → 泡泡放到比比靠畫面內側的旁邊 */
    const c0 = center(), c = { x: c0.x + OFF.x, y: c0.y }, w = tip.offsetWidth, h = tip.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
    let left = c.x - w / 2, top = c.y - 46 - h - 8;
    if (run && run.act && run.tipSide) {
      const sd = c.x > vw / 2 ? -1 : 1, half = (window.innerWidth <= 820 ? 84 : 104) * 0.5;
      left = sd < 0 ? c.x - half - 6 - w : c.x + half + 6; top = c.y - h - 4;
    } else if (ring && ring.classList.contains('on')) {
      /* 環開著：泡泡放在所有小圈的上緣之上（放不下就放下緣之下），水平對齊小圈群的中間 */
      const bs = [...ring.querySelectorAll('.bopt:not(.pg-off)')].map((b) => ({ x: c.x + parseFloat(b.style.getPropertyValue('--x')), y: c.y + parseFloat(b.style.getPropertyValue('--y')) }));
      const half = OPT() / 2, minY = Math.min(c.y - 46, ...bs.map((q) => q.y - half)), maxY = Math.max(c.y + 46, ...bs.map((q) => q.y + half));
      const mx = bs.reduce((t, q) => t + q.x, c.x) / (bs.length + 1);
      left = mx - w / 2; top = minY - h - 8;
      if (top < 8) top = maxY + 8;
    } else if (top < 8) top = c.y + 46 + 8;
    left = Math.max(8, Math.min(vw - w - 8, left)); top = Math.max(8, Math.min(vh - h - 8, top));
    tip.style.left = Math.round(left) + 'px'; tip.style.top = Math.round(top) + 'px';
  }

  /* ---------- 環 ---------- */
  /* 10-11 晚 Andy 看了線上版：「這樣有點多，至多外圍一圈，其他的就用點選下一格的方式」
     → 只排一層：比比在角落＝一段扇形弧、在畫面中間＝一整圈；一層放不下全部時，最後一格固定是「下一頁 ›」，
       點了換下一批（最後一頁的下一頁回第一頁）；「問比比」固定在第一頁第一個。 */
  let openWH = '', ring = null, hoverFab = false, openT = 0, closeT = 0, openedAt = 0, ringMaxR = 0;
  let page = 0, perPage = ACTS.length, slots = [], pageBusy = 0;
  const OPT = () => 44;                 // 小圈 44px（手機觸控建議值；桌機同尺寸，兩邊一致）
  const PER = 5;                        // 角落扇形每頁 5 格（含「下一頁」）
  function center() {
    const r = fab.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }
  function topLim() {
    const tb = document.querySelector('header.topbar');
    if (tb && tb.getClientRects().length) { const cs = getComputedStyle(tb), r = tb.getBoundingClientRect(); if ((cs.position === 'fixed' || cs.position === 'sticky') && r.bottom > 0) return r.bottom + 6; }
    return 8;
  }
  const NEXT_SVG = '<path d="M9 5.5l6.5 6.5L9 18.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>';
  function buildRing() {
    ring = document.createElement('div'); ring.id = 'bibiRing'; ring.className = 'bibiring'; ring.hidden = true;
    ring.setAttribute('role', 'menu'); ring.setAttribute('aria-label', '跟比比玩');
    ring.innerHTML = '<div class="bzone"></div><svg class="btrack" aria-hidden="true"></svg>'
      + ACTS.map((a) => `<button type="button" class="bopt pg-off${a.ask ? ' bask' : ''}${ICON_IMG[a.id] ? ' bpic' : ' bsvg2'}" role="menuitem" data-act="${a.id}" tabindex="-1">${iconOf(a.id)}</button>`).join('')
      + `<button type="button" class="bopt bnext bsvg2 pg-off" role="menuitem" data-act="next" tabindex="-1" title="下一頁" aria-label="下一頁"><svg viewBox="0 0 24 24" aria-hidden="true">${NEXT_SVG}</svg><i class="bpg"></i></button>`;
    document.body.appendChild(ring);
    ring.querySelectorAll('.bopt[data-act]:not(.bnext)').forEach((b) => { const a = ACTS.find((x) => x.id === b.dataset.act); b.title = a.name; b.setAttribute('aria-label', a.name); });
    ring.addEventListener('click', (e) => {
      const b = e.target.closest('.bopt');
      if (!b) { if (tapMode()) { closeRing(); stopRun('tap'); } return; }    // 手機：點圈內空白＝收起
      e.stopPropagation();
      if (b.classList.contains('pg-off')) return;
      if (b.dataset.act === 'next') { turnPage(); return; }
      act(b.dataset.act);
    });
    ring.addEventListener('pointerover', (e) => {
      if (e.pointerType === 'touch') return;
      const b = e.target.closest('.bopt'); if (!b || b.classList.contains('pg-off')) return;
      if (Date.now() - openedAt < 450) return;   // 小圈剛彈到游標底下的那一下不算「指到」，泡泡先講心情
      if (mode === 'idle' || b.classList.contains('bask') || b.classList.contains('bnext')) say(b.getAttribute('aria-label'));
    });
  }
  function iconOf(id) {
    if (ICON_IMG[id]) return `<img src="brand/bibi/icons/${ICON_IMG[id]}.webp?v=${AV}" alt="" draggable="false">`;
    return `<svg viewBox="0 0 24 24" aria-hidden="true">${SVG[id] || ''}</svg>`;
  }
  function syncSleepBtn() {
    if (!ring) return;
    const b = ring.querySelector('.bopt[data-act="sleep"]'); if (!b) return;
    const name = sleeping ? '叫醒' : '睡覺';
    b.title = name; b.setAttribute('aria-label', name); b.innerHTML = iconOf(sleeping ? 'wake' : 'sleep'); b.dataset.state = sleeping ? 'wake' : 'sleep';
    b.classList.toggle('bpic', !!ICON_IMG[sleeping ? 'wake' : 'sleep']); b.classList.toggle('bsvg2', !ICON_IMG[sleeping ? 'wake' : 'sleep']);
  }
  function canRing() {
    return fab && !fab.hidden && !fabOff() && !fab.classList.contains('supaway') && !fab.classList.contains('supdrag') && ($('supPanel') || {}).hidden !== false && !blockerOpen();
  }
  /** 只排一層：以比比當下位置為圓心，找「整顆小圈都在視窗內」的角度範圍。
      四周都放得下（比比被拖到畫面中間）＝一整圈、每頁 PER 格；否則從小半徑往外找，第一個放得下 PER 格的半徑就用它。
      回傳 { pts:[{x,y}]（每頁的格位，相對圓心）, arc, r } */
  function layout(cx, cy) {
    const S = OPT(), step = S + 8, N = ACTS.length;
    const vw = document.documentElement.clientWidth || window.innerWidth, vh = window.innerHeight, pad = 6;
    const L = pad, Rr = vw - pad, Tt = Math.max(pad, topLim()), B = vh - pad;
    const fits = (r, d) => { const t = d * Math.PI / 180, x = cx + r * Math.cos(t), y = cy + r * Math.sin(t); return x - S / 2 >= L && x + S / 2 <= Rr && y - S / 2 >= Tt && y + S / 2 <= B; };
    const r0 = isMob() ? 80 : 86;
    let best = null;
    for (let r = r0; r <= r0 + 120; r += 4) {
      const ok = []; for (let d = 0; d < 360; d++) ok.push(fits(r, d));
      if (ok.every(Boolean)) {
        /* 四周都放得下（比比在畫面中間）＝一整圈；一樣每頁 PER 格（Andy：「至多外圍一圈，其他的就用點選下一格」），平均分在圈上 */
        const n = Math.min(PER, N), angs = []; for (let i = 0; i < n; i++) angs.push(-90 + i * 360 / n);
        return mk(r, angs, { r, full: true });
      }
      let run = { len: 0, st: 0 };
      for (let st = 0; st < 360; st++) {
        if (!ok[st] || ok[(st + 359) % 360]) continue;
        let len = 0; while (len < 360 && ok[(st + len) % 360]) len++;
        if (len > run.len) run = { len, st };
      }
      if (run.len < 2) continue;
      const span = run.len - 1, stepDeg = step / r * 180 / Math.PI, cap = Math.floor(span / stepDeg) + 1;
      const c = { r, cap, span, stepDeg, mid: run.st + span / 2 };
      if (!best || c.cap > best.cap) best = c;
      if (cap >= PER) break;
    }
    if (!best) best = { r: r0, cap: 1, span: 0, stepDeg: 0, mid: 225 };
    const n = Math.max(2, Math.min(PER, best.cap)), tot = (n - 1) * best.stepDeg;
    const angs = []; for (let i = 0; i < n; i++) angs.push(best.mid - tot / 2 + i * best.stepDeg);
    return mk(best.r, angs, { r: best.r, a0: best.mid - tot / 2 - best.stepDeg * 0.45, a1: best.mid + tot / 2 + best.stepDeg * 0.45 });
    function mk(r, angs, arc) { return { r, arc, pts: angs.map((d) => { const t = d * Math.PI / 180; return { x: Math.round(Math.cos(t) * r), y: Math.round(Math.sin(t) * r) }; }) }; }
  }
  function arcPath(a) {
    if (a.full) return `M ${a.r} 0 A ${a.r} ${a.r} 0 1 1 ${-a.r} 0 A ${a.r} ${a.r} 0 1 1 ${a.r} 0`;
    const p = (d) => { const t = d * Math.PI / 180; return `${(Math.cos(t) * a.r).toFixed(1)} ${(Math.sin(t) * a.r).toFixed(1)}`; };
    return `M ${p(a.a0)} A ${a.r} ${a.r} 0 ${a.a1 - a.a0 > 180 ? 1 : 0} 1 ${p(a.a1)}`;
  }
  const pageCount = () => (perPage >= ACTS.length ? 1 : Math.ceil(ACTS.length / (perPage - 1)));
  /** 把第 p 頁的小圈放到格位上（其他收回圓心、不可點）；一頁放不下全部時最後一格是「下一頁」 */
  function paintPage(p) {
    const all = [...ring.querySelectorAll('.bopt')], nextB = ring.querySelector('.bnext');
    const pages = pageCount(), per = pages > 1 ? perPage - 1 : ACTS.length;
    page = ((p % pages) + pages) % pages;
    const ids = ACTS.slice(page * per, page * per + per).map((a) => a.id);
    const show = ids.map((id) => ring.querySelector(`.bopt[data-act="${id}"]`));
    if (pages > 1) show.push(nextB);
    all.forEach((b) => { if (show.indexOf(b) < 0) { b.classList.add('pg-off'); b.tabIndex = -1; b.style.transitionDelay = '0ms'; } });
    show.forEach((b, i) => {
      const q = slots[i] || slots[slots.length - 1];
      b.style.setProperty('--x', q.x + 'px'); b.style.setProperty('--y', q.y + 'px');
      b.style.width = b.style.height = OPT() + 'px'; b.style.margin = `${-OPT() / 2}px 0 0 ${-OPT() / 2}px`;
      b.style.transitionDelay = reduce() ? '0ms' : (i * 30) + 'ms';
      b.classList.remove('pg-off'); b.removeAttribute('tabindex');
    });
    nextB.querySelector('.bpg').textContent = pages > 1 ? `${page + 1}/${pages}` : '';
    nextB.setAttribute('aria-label', pages > 1 && page === pages - 1 ? '回第一頁' : '下一頁'); nextB.title = nextB.getAttribute('aria-label');
    ring.dataset.page = String(page + 1); ring.dataset.pages = String(pages);
  }
  /** 翻頁：目前這批先縮回圓心，再彈出下一批（減少動態偏好＝直接換） */
  function turnPage() {
    if (pageBusy) return;
    const cur = [...ring.querySelectorAll('.bopt:not(.pg-off)')];
    if (reduce()) { paintPage(page + 1); return; }
    cur.forEach((b) => { b.style.transitionDelay = '0ms'; b.classList.add('pg-off'); });
    pageBusy = setTimeout(() => { pageBusy = 0; paintPage(page + 1); }, 170);
  }
  function openRing() {
    clearTimeout(closeT); clearTimeout(openT);
    if (!canRing() || (ring && ring.classList.contains('on')) || (run && run.act)) return;   // 比比跑出去玩的時候不開環（圓心是空的）
    stopFidget(); preload();
    if (!ring) buildRing();
    const r = fab.getBoundingClientRect(), X = r.left + r.width / 2, Y = r.top + r.height / 2;
    const L = layout(X, Y);
    slots = L.pts; perPage = L.pts.length;
    fab.classList.add('bibiopen');
    ring.style.left = Math.round(X) + 'px'; ring.style.top = Math.round(Y) + 'px';
    const zone = L.r + OPT() / 2 + 14;
    ring.querySelector('.bzone').style.cssText = `left:${-zone}px;top:${-zone}px;width:${zone * 2}px;height:${zone * 2}px`;
    ring.querySelector('.btrack').innerHTML = `<path d="${arcPath(L.arc)}"/>`;
    ringMaxR = L.r;
    openedAt = Date.now(); openWH = innerWidth + 'x' + innerHeight;
    clearTimeout(pageBusy); pageBusy = 0;
    syncSleepBtn();
    ring.querySelectorAll('.bopt').forEach((b) => b.classList.add('pg-off'));
    ring.hidden = false; fab.dataset.ring = '1';
    void ring.offsetWidth;
    ring.classList.add('on');
    paintPage(0);                       // 每次打開都從第一頁開始（「問比比」在第一個）
    watchOn();
    ring.classList.toggle('cool', mode === 'act');
    setTimeout(() => say(tapMode() ? (tipText() + '（點小圈跟比比玩）') : tipText()), reduce() ? 0 : 200);
  }
  function closeRing(instant) {
    clearTimeout(openT); clearTimeout(closeT);
    if (!fab) return;
    delete fab.dataset.ring;
    fab.classList.remove('bibiopen');
    if (ring) { ring.classList.remove('on'); setTimeout(() => { if (ring && !ring.classList.contains('on')) ring.hidden = true; }, 260); }
    hideTip();
  }
  const ringOpen = () => !!(ring && ring.classList.contains('on'));
  /* 環開著（或比比跑出去玩）時，任何抽屜／選單／彈窗打開就收環、叫比比回來（手機單位 10-11 實測：環開著點 #m4Burger 開左側抽屜，環沒收）。
     supaway 只管「蓋到鈕的位置」，左側抽屜沒蓋到右下角的鈕，所以要自己看。只在環開著／動作中才觀察（平常不掛，省效能）。 */
  const BLOCK_SEL = '#m4Drawer, #acctMenu, [role="dialog"], [aria-modal="true"], .msheet, dialog[open]';
  function blockerOpen() {
    for (const el of document.querySelectorAll(BLOCK_SEL)) {
      if (el.closest('#supPanel, #twTour, #bibiRing, #bibiTip, #bibiStage') || el.hidden || el.closest('[hidden]')) continue;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      const r = el.getBoundingClientRect(); if (r.width > 0 && r.height > 0) return el.id || el.className || el.tagName;
    }
    return '';
  }
  let blockMo = null, blockT = 0;
  function watchOn() {
    if (blockMo || !window.MutationObserver) return;
    blockMo = new MutationObserver(() => {
      if (blockT) return;
      blockT = setTimeout(() => { blockT = 0; if (!ringOpen() && !(run && run.act)) { watchOff(); return; } if (blockerOpen()) { stopRun('drawer'); closeRing(true); } }, 30);
    });
    blockMo.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'class', 'open', 'aria-hidden', 'aria-modal'] });
  }
  function watchOff() { if (blockMo) { blockMo.disconnect(); blockMo = null; } clearTimeout(blockT); blockT = 0; }

  /* ---------- 動作 ---------- */
  function act(id) {
    const a0 = ACTS.find((x) => x.id === id); if (!a0) return;
    if (a0.ask) { closeRing(true); if (window.TwSupport && window.TwSupport.open) window.TwSupport.open(); return; }
    if (mode === 'act') return;                       // 冷卻：上一個動作還沒播完
    stopFidget();
    let a = a0;
    if (a0.sleep && sleeping) a = Object.assign({ id: 'wake' }, a0.wake);
    const n = bump(a0.id === 'sleep' ? (sleeping ? 'wake' : 'sleep') : a0.id);
    mode = 'act'; fab.dataset.bibiAct = a.id === 'wake' ? 'wake' : a0.id;
    /* 有編排腳本的（球／草／摸摸／轉圈）：比比要離開原位、道具要空間 → 環先收起（這一下不算打斷），泡泡跟著比比走 */
    if (CHOREO[a.id] && !reduce()) {
      if (ringOpen()) closeRing(true);
      let line0 = a.say[Math.floor(Math.random() * a.say.length)];
      if (a.cnt && (n === 3 || n % 5 === 0)) line0 = a.cnt(n);
      playChoreo(a, line0);
      setTimeout(() => { if (run && run.act && run.id === a.id && !run.said && run.id !== 'ball' && run.id !== 'grass') cue(); }, 60);   // 摸摸／轉圈開頭就說；球、草等到接住／開吃才說
      return;
    }
    if (ring) ring.classList.add('cool');
    show(a.file, !!a.once);
    /* 轉圈圈：專屬素材到了就照素材轉；還在用歪頭代替時，CSS 讓整隻轉 360° */
    if (a0.id === 'spin' && a.file === 'tilt') { fab.classList.remove('bibispin'); void fab.offsetWidth; fab.classList.add('bibispin'); }
    { const f = a.file, t0 = Date.now(); const go = () => { if (mode !== 'act') return; if (shown === f || Date.now() - t0 > 700) burst(a.fx); else setTimeout(go, 40); }; go(); }
    let line = a.say[Math.floor(Math.random() * a.say.length)];
    if (a.cnt && (n === 3 || n % 5 === 0)) line = a.cnt(n);
    say(line, 2600);
    const dur = a.once ? (MS[a.file] || 2500) + 150 : Math.max(1800, Math.min(3200, (MS[a.file] || 1200) * 2));
    clearTimeout(actTimer);
    actTimer = setTimeout(() => {
      mode = 'idle'; delete fab.dataset.bibiAct; fab.classList.remove('bibispin');
      if (a0.sleep) { sleeping = a.id !== 'wake'; fab.dataset.bibiSleep = sleeping ? '1' : ''; syncSleepBtn(); }
      if (ring) ring.classList.remove('cool');
      applyIdle(); schedFidget();
    }, dur);
  }
  function burst(kind) {
    if (!kind || !FX[kind] && kind !== 'flash') return;
    const c = center(), n = reduce() ? 2 : (kind === 'flash' ? 4 : 7);
    if (kind === 'flash') {
      const f = document.createElement('div'); f.className = 'bibiflash'; f.style.left = c.x + 'px'; f.style.top = (c.y - 10) + 'px';
      document.body.appendChild(f); setTimeout(() => f.remove(), 600);
    }
    for (let i = 0; i < n; i++) {
      const s = document.createElement('div'); s.className = 'bibifx';
      s.innerHTML = FX[kind] || FX.star;
      const ang = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.1, dist = (reduce() ? 30 : 46) + Math.random() * 34;
      s.style.left = (c.x + (Math.random() - 0.5) * 24) + 'px'; s.style.top = (c.y - 18) + 'px';
      s.style.setProperty('--fx', Math.round(Math.cos(ang) * dist) + 'px');
      s.style.setProperty('--fy', Math.round(Math.sin(ang) * dist - (kind === 'z' ? 20 : 0)) + 'px');
      s.style.setProperty('--fr', Math.round((Math.random() - 0.5) * 120) + 'deg');
      s.style.animationDelay = (i * 70) + 'ms';
      document.body.appendChild(s); setTimeout(() => s.remove(), 1400 + i * 70);
    }
  }

  /* ======================================================================================
     動作編排引擎（10-11 晚）
     Andy：「動畫效果太差了，需要是點擊互動按鈕，他會有對應動作，不是基於原本的GIF 加點東西上去。
            例如我點球，他會跟著球跑，我點草，他會有吃草畫面等等」＋「動作要在豐富生動一點」。
     → 每個互動是一段腳本（async 函式）：比比整顆離開原位（.bibiwrap 位移＋.bibibody 擠壓伸展／傾斜），
       道具（球／草／手／暈眩螺旋）在 #bibiStage 上照物理走（拋物線、反彈遞減、旋轉、減速、影子）。
     規則：開始前比比一定在原位（位移 0）；腳本結束、或中途被打斷（換頁、手機點空白收環、Esc、關客服、被抽屜蓋住、
       視窗變大小、分頁切到背景）→ 立刻回原位、道具清掉、回情境待機。打斷靠 runTok：每一格都檢查自己還是不是最新的那一次。
     減少動態偏好：不跑腳本，退回「換圖＋兩顆小特效」（只保留最小動作），待機小動作也不做。
     ====================================================================================== */
  /* 零件對照（MAP）：動畫單位的專屬零件到了，把右邊換成新檔名就好（先 bibi_site.py 轉 160px、MS 補總長），機制不用改。
     現在的替代：跑步＝素材庫 hop_l／hop_r（run_l／run_r 還沒到）；撲球／吃草／摸摸／轉圈＝G1 的 ball／eat_grass／pet／spin（_v2 還沒到）。 */
  /* receive＝手把草／球遞過來時往前接（receive 未到先用 face_star）；popcorn＝天竺鼠爆米花跳（未到先用 face_star＋編排位移）；
     happy＝待機「開心的跳」（happy_hop 未到＝空字串：沿用情境款的圖、由 CSS 讓整顆小跳＋落地擠壓回彈；填了檔名就改播素材、CSS 小跳自動停） */
  const PART = { run_l: 'hop_l', run_r: 'hop_r', ball_catch: 'ball', eat: 'eat_grass', pet: 'pet', spin: 'spin', look: 'face_curious', peek: 'tilt',
    receive: 'receive', receive_grass: 'receive_grass', receive_ball: 'receive_ball', popcorn: 'face_star', happy: 'happy_hop' };
  /* 替代素材太長時只播這麼久（key＝零件、值＝[替代檔名, 毫秒]；換成真零件後檔名對不上就自動照 MS 播完整段） */
  const PART_MS = { ball_catch: ['ball', 1500] };
  /* 道具圖：動畫單位的 PNG 到了填檔名（放 site/brand/bibi/props/<名>.png）；空字串＝用下面畫的 inline SVG */
  /* 給草／給球的手是動畫單位的 PNG（site/brand/bibi/props/，bibi_site.py props 產生）；球滾出去之後用下面畫的 SVG 球（照素材那顆的樣子） */
  const PROP_IMG = { ball: '', grass: '', hand: '' };
  let svgN = 0;
  const PROP_SVG = {
    /* 球：跟素材裡那顆一樣的紅白球（紅底＋斜白帶＋深咖啡描邊＋左上高光） */
    ball: () => { const id = 'bbc' + (++svgN); return `<svg viewBox="0 0 40 40" aria-hidden="true"><defs><clipPath id="${id}"><circle cx="20" cy="20" r="17"/></clipPath></defs>`
      + `<g clip-path="url(#${id})"><rect width="40" height="40" fill="#e85a4f"/><ellipse cx="20" cy="20" rx="8" ry="18" fill="#fff6ee" stroke="#2b1611" stroke-width="1.8" transform="rotate(-18 20 20)"/></g>`
      + '<circle cx="20" cy="20" r="2.7" fill="#f6c945" stroke="#2b1611" stroke-width="1.3"/>'
      + '<circle cx="20" cy="20" r="17" fill="none" stroke="#2b1611" stroke-width="2.6"/><ellipse cx="13" cy="11.5" rx="3.6" ry="2" fill="#fff" opacity=".8" transform="rotate(-38 13 11.5)"/></svg>'; },
    /* 牧草：三片葉子綁一個粉紅結（跟小圈圖示同一套：飽和綠＋深描邊） */
    grass: () => '<svg viewBox="0 0 40 52" aria-hidden="true"><g stroke="#24401f" stroke-width="1.8" stroke-linejoin="round">'
      + '<path d="M17 49C14 38 9 30 3 25c8 1 15 8 18 22z" fill="#86d26f"/><path d="M23 49C26 37 31 28 38 22c-2 10-7 19-11 27z" fill="#79c763"/>'
      + '<path d="M18 49c-1-15 0-30 4-44 4 14 4 30 1 44z" fill="#5db552"/></g><path d="M21 12c.6 9 .5 22-.3 33" stroke="#3f8a3a" stroke-width="1.1" fill="none"/>'
      + '<rect x="13.5" y="39" width="14" height="6" rx="3" fill="#ffb3c4" stroke="#2b1611" stroke-width="1.6"/></svg>',
    /* 手：手掌朝下、從右上伸進來（米色手＋淺藍袖口＋深描邊、手指分線） */
    hand: () => '<svg viewBox="0 0 64 48" aria-hidden="true"><g stroke="#2b1611" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">'
      + '<rect x="44" y="9" width="18" height="24" rx="5" fill="#8ec9ff"/>'
      + '<path d="M45 12C36 8 22 9 12 12c-6 2-9 6-7 10s9 6 17 7c8 1 15 2 23 1z" fill="#ffe3cf"/>'
      + '<path d="M33 30c0 6-3 10-8 10-3 0-3-4 0-6 2-1 3-3 3-5" fill="#ffe3cf"/></g>'
      + '<g stroke="#c98f74" stroke-width="1.4" fill="none" stroke-linecap="round"><path d="M12 16.5c7 .3 13 .8 19 1.6"/><path d="M9 21.5c8 .6 15 1.2 22 1.8"/></g>'
      + '<ellipse cx="38" cy="19" rx="3" ry="2" fill="#ffb3a8" opacity=".7"/></svg>',
    shadow: () => '',
    /* 暈眩螺旋（轉完頭上那一圈） */
    dizzy: () => '<svg viewBox="0 0 60 30" aria-hidden="true"><path d="M30 15m-2.5 0a2.5 2.5 0 1 1 5 0a5.5 5.5 0 1 1-11 0a8.5 8.5 0 1 1 17 0a11.5 11.5 0 1 1-23 0" fill="none" stroke="#9a7ae0" stroke-width="2.4" stroke-linecap="round"/></svg>',
    star: () => FX.star,
  };
  const E = {
    inOut: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    out: (k) => 1 - Math.pow(1 - k, 3),
    in: (k) => k * k * k,
    damp: (k, f) => Math.exp(-5 * k) * Math.cos(f * Math.PI * k),   // 回彈：越來越小的來回
  };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ABORT = { abort: true };
  let wrapEl = null, bodyEl = null, stage = null, run = null, runTok = 0, rafId = 0, fidgetT = 0, noFidget = false, tipFollow = false, lastStop = '';
  const OFF = { x: 0, y: 0 };
  /** 比比的位移（相對原位）＋身體的擠壓伸展：sx/sy 縮放、sk 傾斜（正＝上半身往左）、r 旋轉 */
  function pose(x, y, o) {
    o = o || {}; OFF.x = x; OFF.y = y;
    if (!wrapEl) return;
    wrapEl.style.transform = (x || y) ? `translate(${x.toFixed(1)}px,${y.toFixed(1)}px)` : '';
    const sx = o.sx == null ? 1 : o.sx, sy = o.sy == null ? 1 : o.sy, sk = o.sk || 0, r = o.r || 0;
    bodyEl.style.transform = (sx !== 1 || sy !== 1 || sk || r) ? `rotate(${r.toFixed(2)}deg) skewX(${sk.toFixed(2)}deg) scale(${sx.toFixed(3)},${sy.toFixed(3)})` : '';
  }
  /** 一段 ms 毫秒的補間：每格叫 fn(k∈0..1, 經過毫秒)。被打斷（runTok 換了）就丟 ABORT，腳本整段停下。 */
  function tween(ms, fn) {
    const tok = runTok;
    return new Promise((res, rej) => {
      const t0 = performance.now();
      const step = (now) => {
        if (tok !== runTok) { rej(ABORT); return; }
        const el = Math.max(0, now - t0), k = ms > 0 ? Math.min(1, el / ms) : 1;
        try { fn(k, el); } catch (e) { rej(e); return; }
        if (tipFollow && tip && !tip.hidden) placeTip();
        if (k >= 1) res(); else rafId = requestAnimationFrame(step);
      };
      rafId = requestAnimationFrame(step);
    });
  }
  const wait = (ms) => tween(ms, () => {});
  function ensureStage() {
    if (stage && stage.isConnected) return stage;
    stage = document.createElement('div'); stage.id = 'bibiStage'; stage.setAttribute('aria-hidden', 'true');
    document.body.appendChild(stage); return stage;
  }
  function clearStage() { if (stage) stage.innerHTML = ''; }
  /** 道具：寬 w 高 h，用 at() 以「中心點」擺位置 */
  function prop(kind, w, h) {
    const el = document.createElement('div'); el.className = 'bp bp-' + kind + (kind === 'shadow' ? ' bshadow' : '');
    el.style.width = w + 'px'; el.style.height = h + 'px'; el._w = w; el._h = h;
    el.innerHTML = PROP_IMG[kind] ? `<img src="brand/bibi/props/${PROP_IMG[kind]}.png?v=${AV}" alt="" style="width:100%;height:100%;display:block">` : (PROP_SVG[kind] ? PROP_SVG[kind]() : '');
    ensureStage().appendChild(el); return el;
  }
  function at(el, cx, cy, extra, op) {
    el.style.transform = `translate(${(cx - el._w / 2).toFixed(1)}px,${(cy - el._h / 2).toFixed(1)}px)${extra || ''}`;
    if (op != null) el.style.opacity = String(op);
  }
  /** 小粒子（愛心／草屑／星星）從 (x,y) 噴出 */
  function burstAt(kind, x, y, n, spread) {
    for (let i = 0; i < n; i++) {
      const s = document.createElement('div'); s.className = 'bibifx';
      s.innerHTML = FX[kind] || FX.star;
      const ang = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * (spread || 1.1), dist = 26 + Math.random() * 30;
      s.style.left = (x + (Math.random() - 0.5) * 16) + 'px'; s.style.top = y + 'px';
      s.style.setProperty('--fx', Math.round(Math.cos(ang) * dist) + 'px');
      s.style.setProperty('--fy', Math.round(Math.sin(ang) * dist) + 'px');
      s.style.setProperty('--fr', Math.round((Math.random() - 0.5) * 140) + 'deg');
      s.style.animationDelay = (i * 60) + 'ms';
      document.body.appendChild(s); setTimeout(() => s.remove(), 1300 + i * 60);
    }
  }
  /** 量比比在原位的幾何（量 #supFab，不量圖：圖可能正在放大或位移）：s＝圖寬、foot＝腳底、top＝圖頂、dir＝往哪一側空間大 */
  function geo() {
    const fr = fab.getBoundingClientRect(), small = window.innerWidth <= 820, s = small ? 84 : 104;
    const bottom = fr.bottom + (small ? 2 : 3), vw = document.documentElement.clientWidth || window.innerWidth;
    const cx = fr.left + fr.width / 2;
    return { cx, s, foot: bottom - s * 0.05, top: bottom - s, vw, vh: window.innerHeight, mob: isMob(), dir: cx > vw / 2 ? -1 : 1 };
  }
  const partMs = (k) => (PART_MS[k] && PART[k] === PART_MS[k][0] ? PART_MS[k][1] : (MS[PART[k]] || 1500));
  let preloaded = false;
  function preload() {
    if (preloaded) return; preloaded = true;
    Object.keys(PART).forEach((k) => { if (PART[k]) { const i = new Image(); i.src = src(PART[k]); } });
    ['hand', 'hand_grass', 'hand_ball'].forEach((f) => { const i = new Image(); i.src = `brand/bibi/props/${f}.webp?v=${AV}`; });   // 空手要先載好：接到的那一刻換圖不能閃
  }
  function idleFile() { return sleeping ? SLEEP_FILE : ((idleNow && idleNow.file) || (IDLE[idleNow && idleNow.key] || IDLE.other).file); }

  /* ---------- 給的動作（Andy 10-11 晚：「給草 給球，要有給的動作」；動畫單位交件 docs/anim/bibi_receive） ----------
     道具是 512 畫布、跟比比素材同一個場景座標（比比中心 x=248、腳底 y=482；網站圖的裁切框左上 (28,52)、寬 440），
     手從畫面右邊伸進來；比比播 receive_grass／receive_ball：第 3 格（370ms）肉掌在右前方接到東西、之後抱在胸前。
     sc()＝場景座標 → 螢幕座標；道具用同一個比例 k 縮放，大小就跟比比對得上。
     比比在右下角時右邊沒有空間給手 → 先往畫面內側小跳一步讓出位置（toward），接完東西再從那裡開始吃／追。 */
  const sc = (g, X, Y) => ({ x: g.cx + (X - 248) * g.s / 440, y: g.top + (Y - 52) * g.s / 440 });
  const GRAB = 370;                          // receive 第 3 格開始＝接到的那一刻（storyboard：150＋220）
  function propImg(kind, file, g) {
    const w = Math.round(512 * g.s / 440);
    const el = document.createElement('div'); el.className = 'bp bp-' + kind; el.style.width = el.style.height = w + 'px'; el._w = el._h = w;
    el.innerHTML = `<img src="brand/bibi/props/${file}.webp?v=${AV}" alt="" draggable="false" style="width:100%;height:100%;display:block">`;
    ensureStage().appendChild(el); return el;
  }
  /** 手（拿著東西）：讓道具畫布上的點 (u,v) 停在螢幕 (tx,ty)；從右上方畫面外伸進來 */
  function giveHand(g, file, u, v, tx, ty) {
    const k = g.s / 440, el = propImg('hand', file, g);
    const ex = tx + (256 - u) * k, ey = ty + (256 - v) * k;    // 畫布中心的終點
    const H = { el, ex, ey, sx: ex + (g.mob ? 110 : 160), sy: ey - (g.mob ? 60 : 90), x: 0, y: 0,
      at(x, y, rot, op) { H.x = x; H.y = y; at(el, x, y, ` rotate(${(rot || 0).toFixed(1)}deg)`, op); } };
    H.at(H.sx, H.sy, 12, 0);
    return H;
  }
  const handEnter = (H, ms) => tween(ms, (k) => { const e = E.out(k); H.at(H.sx + (H.ex - H.sx) * e, H.sy + (H.ey - H.sy) * e, 12 * (1 - e), Math.min(1, k * 4)); });
  /** 東西交出去了：手換成空手（不換的話手縮回去時會帶著第二根草／第二顆球） */
  function handEmpty(H) { const i = H.el.querySelector('img'); if (i) i.src = `brand/bibi/props/hand.webp?v=${AV}`; H.el.className = 'bp bp-hand'; }
  const handOut = (H, ms) => { const x0 = H.x, y0 = H.y; return tween(ms, (k) => { const e = E.in(k); H.at(x0 + (H.sx - x0) * e, y0 + (H.sy - y0) * e, 10 * e, (1 - k).toFixed(2)); }); };
  /** 比比要往畫面內側讓多少，右邊才放得下手（肉掌＋一點袖子） */
  function toward(g) {
    const k = g.s / 440, need = (g.cx + 178 * k) + 215 * k + 8;   // 接東西的點在比比中心右邊 147k；手的肉掌再往右 ~215k
    return need > g.vw ? -(need - g.vw) - 6 : 0;
  }
  /** 比比小跳一步到 x（相對原位），落地擠壓回彈 */
  const hopTo = (x0, x1, ms, hgt) => tween(ms, (k) => {
    const e = E.inOut(k), up = Math.sin(Math.PI * k);
    pose(x0 + (x1 - x0) * e, -hgt * up, { sx: 1 - 0.05 * up + (k > 0.85 ? 0.08 * (k - 0.85) / 0.15 : 0), sy: 1 + 0.07 * up - (k > 0.85 ? 0.1 * (k - 0.85) / 0.15 : 0), sk: x1 < x0 ? 5 * up : -5 * up });
  });
  /** 給東西的共同前段：手伸進來、比比同時往內側跳一步並播 receive；接到那一刻手變空手、縮回去。回傳比比站的位置（相對原位） */
  async function receive(g, kind) {
    const off = toward(g), file = kind === 'grass' ? 'hand_grass' : 'hand_ball';
    const P = sc(g, kind === 'grass' ? 392 : 426, kind === 'grass' ? 262 : 352);   // 接的點（receive 第 3 格肉掌；球比較大，球心再往右一點才不會蓋到臉）
    const H = giveHand(g, file, kind === 'grass' ? 236 : 296, kind === 'grass' ? 278 : 262, P.x + off, P.y);
    show(PART['receive_' + kind] || PART.receive, true);       // 0.2 秒內就在動（Andy：「直接進入互動動作」）
    const step = off ? hopTo(0, off, 300, g.mob ? 9 : 12) : tween(300, (k) => pose(0, -6 * Math.sin(Math.PI * k), { sy: 1 + 0.05 * Math.sin(Math.PI * k) }));
    await handEnter(H, GRAB - 20); await step;
    await wait(20);
    handEmpty(H);
    burstAt('star', P.x + off, P.y - 8, 3, 1.4);
    await handOut(H, 380);
    H.el.remove();
    await wait(Math.max(0, (MS[PART['receive_' + kind]] || 1380) - GRAB - 400));
    return off;
  }

  /* ---------- 腳本：玩球 ----------
     ★ 10-11 晚 Andy：「給球要有給的動作」→ 一隻手拿著球從右邊伸進來，比比往前接（receive_ball）、抱在胸前；
     接著球從懷裡掉到腳邊，比比一踢：球往空間大的那一側滾（右下角＝往左）——拋物線、每次落地反彈越來越低（落地瞬間壓扁）、
     邊滾邊轉、越滾越慢、影子跟著縮放；比比先往後縮一下再衝（擠壓→伸展），跑步時整顆上下彈、身體往前傾，速度跟球一起慢下來；
     追上時急停前傾回彈＋冒星星、球滾進懷裡、播撲球；再跑回原位、到位時回彈站穩。 */
  async function ballScript(g) {
    const off = await receive(g, 'ball');
    const P = (x, y, o) => pose(x + off, y, o);              // 下面的位移都以「接球的位置」為起點
    const dir = g.dir, R = g.mob ? 10 : 12, gap = g.s * 0.36, cx = g.cx + off;
    const D = clamp(dir < 0 ? cx - 34 - R : g.vw - 34 - R - cx, 110, g.mob ? 240 : 560);
    const bx0 = cx + dir * g.s * 0.28, bx1 = cx + dir * D, ground = g.foot;
    const H = g.mob ? [52, 26, 12, 5] : [70, 34, 16, 6], Tb = g.mob ? 1450 : 1800, lag = 360, T = Tb + 240;
    const segs = H.map(Math.sqrt), sum = segs.reduce((a, b) => a + b, 0), TB = Tb * 0.8;
    const sh = prop('shadow', R * 2.2, 7), ball = prop('ball', R * 2, R * 2);
    const ballAt = (t) => {
      const tt = clamp(t, 0, Tb); let acc = 0, h = 0, land = false;
      for (let i = 0; i < H.length; i++) { const d = segs[i] / sum * TB; if (tt < acc + d) { const u = (tt - acc) / d; h = H[i] * 4 * u * (1 - u); land = (u < 0.07 || u > 0.93) && i > 0; break; } acc += d; }
      const x = bx0 + (bx1 - bx0) * E.out(tt / Tb);
      return { x, h, land, rot: (x - bx0) / R * 180 / Math.PI };
    };
    const drawBall = (b) => {
      at(ball, b.x, ground - R - b.h, ` rotate(${b.rot.toFixed(1)}deg)` + (b.land ? ' scale(1.12,.86)' : ''), 1);
      const q = clamp(b.h / H[0], 0, 1); at(sh, b.x, ground + 1, ` scale(${(1 - 0.55 * q).toFixed(3)})`, (1 - 0.6 * q).toFixed(2));
    };
    // 1. 球從懷裡掉到腳邊（彈一下），身體縮起來蓄力 → 一踢
    show(PART.look);
    const chest = sc(g, 248, 400); chest.x += off;
    await tween(300, (k) => {
      const x = chest.x + (bx0 - chest.x) * k, y = chest.y + (ground - R - chest.y) * (k * k) - (k > 0.7 ? 10 * Math.sin(Math.PI * (k - 0.7) / 0.3) : 0);
      at(ball, x, y, '', 1); sh.style.opacity = (0.6 * k).toFixed(2); at(sh, x, ground + 1, ` scale(${(0.5 + 0.5 * k).toFixed(2)})`);
      P(-dir * 3 * E.out(k), 0, { sx: 1 + 0.08 * E.out(k), sy: 1 - 0.1 * E.out(k) });
    });
    // 2. 球飛出去；比比先往後縮一下（反向仰）再衝；跑步一路上下彈、往前傾；速度照球一起減
    const Db = (bx1 - cx) - dir * gap;
    let ran = false;
    await tween(T, (k, t) => {
      drawBall(ballAt(t));
      if (t < lag) {
        const u = t / lag;
        P(-dir * (3 + 7 * E.out(u)), 0, { sx: 1.08 - 0.12 * u, sy: 0.9 + 0.14 * u, sk: dir * 8 * E.out(u) });
        return;
      }
      if (!ran) { ran = true; show(dir < 0 ? PART.run_l : PART.run_r); }
      const u = (t - lag) / (T - lag), p = Db * E.inOut(u), back = -dir * 10 * (1 - E.out(Math.min(1, u * 5)));
      const bob = -Math.abs(Math.sin((t - lag) / 210 * Math.PI)) * (g.mob ? 5 : 7);
      const sp = Math.sin(Math.PI * u);   // 中段最快：身體最前傾、拉長
      P(p + back, bob, { sk: -dir * 9 * sp, sx: 1 - 0.04 * sp, sy: 1 + 0.05 * sp });
    });
    // 3. 撲到：急停前傾回彈、球滾進懷裡、冒星星
    const bxEnd = ballAt(Tb).x, me = cx + Db;
    cue();
    burstAt('star', bxEnd, ground - R * 2 - 6, 6, 1.6);
    show(PART.ball_catch, true);
    await tween(440, (k) => {
      const d = E.damp(k, 3);
      P(Db, 0, { sk: -dir * 15 * d, sx: 1 + 0.07 * d, sy: 1 - 0.09 * d });
      const bx = bxEnd + (me + dir * g.s * 0.12 - bxEnd) * E.out(k);
      at(ball, bx, ground - R - 10 * Math.sin(Math.PI * k), ` rotate(${((bx - bx0) / R * 180 / Math.PI).toFixed(1)}deg) scale(${(1 - 0.4 * k).toFixed(2)})`, (1 - k).toFixed(2));
      sh.style.opacity = (0.4 * (1 - k)).toFixed(2);
    });
    ball.remove(); sh.remove();
    await wait(Math.max(300, partMs('ball_catch') - 440));
    // 4. 跑回原位（不是接球的位置，是右下角的家）：先蓄力、加速、減速、到位回彈
    const home = -off;
    show(dir < 0 ? PART.run_r : PART.run_l);
    await tween(150, (k) => P(Db + dir * 4 * E.out(k), 0, { sx: 1.06, sy: 0.92, sk: -dir * 5 * k }));
    const Tr = clamp(Math.abs(home - Db) / (g.mob ? 260 : 340) * 1000, 650, 1900);
    await tween(Tr, (k, t) => {
      const sp = Math.sin(Math.PI * k);
      P(Db + (home - Db) * E.inOut(k) + dir * 4 * (1 - k), -Math.abs(Math.sin(t / 210 * Math.PI)) * (g.mob ? 5 : 7), { sk: dir * 9 * sp, sx: 1 - 0.04 * sp, sy: 1 + 0.05 * sp });
    });
    show(idleFile());
    await tween(380, (k) => { const d = E.damp(k, 3); pose(0, 0, { sk: dir * 11 * d, sx: 1 + 0.06 * d, sy: 1 - 0.08 * d }); });
  }

  /* ---------- 腳本：餵牧草 ----------
     ★ 10-11 晚 Andy：「給草要有給的動作」→ 一隻手拿著牧草從右上伸進來，比比往前接（receive_grass）、抱在胸前；
     接著播吃草（eat_grass，已剪掉開頭的待機格）：一口一口、每口冒草屑、跳出「嚼嚼」、身體跟著縮；吃完小跳回原位。 */
  async function grassScript(g) {
    const off = await receive(g, 'grass');
    const cx = g.cx + off;
    cue();
    show(PART.eat, true);
    const Te = partMs('eat'), bites = 5, per = Te / (bites + 1);
    for (let i = 0; i < bites; i++) {
      await tween(per, (k) => { const c = Math.sin(Math.PI * Math.min(1, k * 2.2)); pose(off, 0, { sy: 1 - 0.045 * c, sx: 1 + 0.03 * c }); });   // 嚼一口身體縮一下
      burstAt('grass', cx + g.s * 0.08, g.top + g.s * 0.6, 3, 1.6);
      if (i % 2 === 0) chew(cx + g.dir * g.s * 0.62, g.top + g.s * 0.3);   // 「嚼嚼」放在比比靠畫面內側的旁邊（頭上是說明泡泡）
    }
    await wait(per * 0.6);
    if (off) { show(idleFile()); await hopTo(off, 0, 340, g.mob ? 9 : 12); }
    await tween(260, (k) => { const d = E.damp(k, 2.5); pose(0, 0, { sx: 1 + 0.07 * d, sy: 1 - 0.09 * d }); });
  }
  function chew(x, y) {
    const c = document.createElement('div'); c.className = 'bchew'; c.textContent = '嚼嚼';
    c.style.setProperty('--x', Math.round(x - 18) + 'px'); c.style.setProperty('--y', Math.round(y) + 'px');
    ensureStage().appendChild(c); setTimeout(() => c.remove(), 950);
  }

  /* ---------- 腳本：摸摸頭 ----------
     手（動畫單位的手）從右上伸進來（減速停在頭上）、來回摸 3 下（每一趟加減速、往下壓），每摸一下比比縮一下、冒愛心；摸完手縮回去。 */
  async function petScript(g) {
    /* 手用動畫單位給草／給球那隻（空手版，bibi_site.py props 拆出來的），畫風跟比比一致；肉掌中心在畫布 (370,185) → 對準頭頂 */
    const k = g.s / 440, hand = propImg('hand', 'hand', g), dx = (256 - 370) * k, dy = (256 - 185) * k, W = 60, Hh = 40;
    const AT = (x, y, extra, op) => at(hand, x + dx, y + dy, extra, op);
    const hx = g.cx, hy = g.top + g.s * 0.22 - Hh * 0.3;
    const sx0 = Math.min(g.vw - W / 2 - 4, g.cx + g.s * 0.95), sy0 = Math.max(Hh / 2 + 4, g.top - g.s * 0.75);
    show(PART.pet, true);
    await tween(560, (k) => { const e = E.out(k); AT( sx0 + (hx + 16 - sx0) * e, sy0 + (hy - sy0) * e, ` rotate(${(-22 * (1 - e)).toFixed(1)}deg)`, Math.min(1, k * 2.5)); });
    let x = hx + 16;
    for (let i = 0; i < 6; i++) {          // 6 趟＝來回 3 下
      const from = x, to = i % 2 === 0 ? hx - 16 : hx + 16;
      let popped = false;
      await tween(360, (k) => {
        const e = E.inOut(k), press = Math.sin(Math.PI * k);
        x = from + (to - from) * e;
        AT( x, hy + 5 * press, ` rotate(${(-6 * (to - from) / 32 * press).toFixed(1)}deg)`);
        pose(0, 0, { sy: 1 - 0.09 * press, sx: 1 + 0.05 * press });   // 被摸到就縮一下
        if (!popped && k >= 0.5) { popped = true; burstAt('heart', hx + (Math.random() - 0.5) * 20, hy - 6, i % 2 ? 2 : 1, 1.2); }
      });
    }
    await tween(420, (k) => { const e = E.in(k); AT( x + (sx0 - x) * e, hy + (sy0 - hy) * e, ` rotate(${(-18 * e).toFixed(1)}deg)`, 1 - k); pose(0, 0, { sy: 1 + 0.04 * Math.sin(Math.PI * k) }); });
    hand.remove();
  }

  /* ---------- 腳本：轉圈圈 ----------
     播轉圈（轉的時候整顆微微離地）；轉完頭上冒暈眩螺旋＋三顆星繞圈，比比左右晃 2 下（越晃越小）才站穩。 */
  async function spinScript(g) {
    show(PART.spin, true);
    await tween(Math.min(partMs('spin'), 2200), (k) => pose(0, -4 * Math.sin(Math.PI * k), { sy: 1 + 0.03 * Math.sin(Math.PI * k) }));
    const dz = prop('dizzy', Math.round(g.s * 0.62), Math.round(g.s * 0.31)), stars = [0, 1, 2].map(() => prop('star', 13, 13));
    const hx = g.cx, hy = g.top + g.s * 0.08;
    await tween(1500, (k, t) => {
      const fade = k < 0.12 ? k / 0.12 : (k > 0.85 ? (1 - k) / 0.15 : 1), sc = 0.8 + 0.2 * fade;
      at(dz, hx, hy, ` scale(${sc.toFixed(2)},${(0.45 * sc).toFixed(2)}) rotate(${(t * 0.5).toFixed(1)}deg)`, fade.toFixed(2));
      stars.forEach((s, i) => { const a = t / 260 + i * 2.094; at(s, hx + Math.cos(a) * g.s * 0.3, hy + Math.sin(a) * g.s * 0.09, '', fade.toFixed(2)); });
      const w = Math.sin(k * Math.PI * 4) * (1 - k);   // 左右晃 2 下、越晃越小
      pose(4 * w, 0, { r: 8 * w, sk: -3 * w });
    });
  }
  /* ---------- 腳本：天竺鼠爆米花跳（Andy 10-11 晚：「新增一個爆米花圖案，他就會做出天竺鼠爆米花跳」） ----------
     真的天竺鼠 popcorning：蹲一下 → 突然垂直彈高（拉長）→ 空中扭 15° 再轉回 → 落地壓扁 → 連彈 2～3 下越來越小，每次落地冒小星星。 */
  async function popcornScript(g) {
    const dir = g.dir, J = g.mob ? 50 : 72, tw = -dir * 15;
    show(PART.popcorn, true); cue();
    await tween(190, (k) => pose(0, 0, { sx: 1 + 0.12 * E.out(k), sy: 1 - 0.16 * E.out(k) }));   // 蹲
    burstAt('star', g.cx, g.foot - 6, 3, 2);
    let star = false;
    await tween(560, (k) => {                   // 彈高：起跳與落下最快（拉長）、最高點最慢；空中扭 15° 再回
      const y = -J * 4 * k * (1 - k), st = Math.abs(1 - 2 * k) * 0.14;
      pose(0, y, { r: tw * Math.sin(Math.PI * k), sx: 1 - st * 0.6, sy: 1 + st });
      if (!star && k > 0.45) { star = true; burstAt('star', g.cx, g.top + g.s * 0.1 + y, 4, 1.4); }
    });
    for (const [h, ms] of [[J * 0.36, 320], [J * 0.15, 230], [J * 0.05, 160]]) {
      await tween(110, (k) => { const c = Math.sin(Math.PI * k); pose(0, 0, { sx: 1 + 0.14 * c * h / J * 2.4, sy: 1 - 0.18 * c * h / J * 2.4 }); });   // 落地壓扁
      burstAt('star', g.cx + (Math.random() - 0.5) * g.s * 0.5, g.foot - 4, 1, 1.6);
      await tween(ms, (k) => { const st = Math.abs(1 - 2 * k) * 0.08 * h / J * 2.4; pose(0, -h * 4 * k * (1 - k), { r: -tw * 0.3 * Math.sin(Math.PI * k) * h / J, sx: 1 - st * 0.6, sy: 1 + st }); });
    }
    await tween(320, (k) => { const d = E.damp(k, 2.5); pose(0, 0, { sx: 1 + 0.1 * d, sy: 1 - 0.13 * d }); });
  }
  const CHOREO = { ball: ballScript, grass: grassScript, pet: petScript, spin: spinScript, popcorn: popcornScript };

  /* ---------- 待機小動作（每 20～40 秒隨機一次）：眨眼／伸懶腰／東張西望／跳一下（現有素材＋位移） ---------- */
  const FIDGET = {
    blink: async () => { for (let i = 0; i < 2; i++) await tween(240, (k) => { const c = Math.sin(Math.PI * k); pose(0, 0, { sy: 1 - 0.07 * c, sx: 1 + 0.03 * c }); }); },
    stretch: async () => {
      await tween(260, (k) => pose(0, 0, { sx: 1 + 0.06 * E.out(k), sy: 1 - 0.08 * E.out(k) }));
      await tween(520, (k) => { const e = E.out(k); pose(0, -3 * e, { sx: 1.06 - 0.14 * e, sy: 0.92 + 0.22 * e }); });
      await wait(320);
      await tween(420, (k) => { const d = E.damp(k, 2.5); pose(0, -3 * (1 - k), { sx: 1 - 0.08 * d, sy: 1 + 0.14 * d }); });
    },
    look: async () => {
      show(PART.peek);
      await tween(380, (k) => pose(-3 * E.inOut(k), 0, { r: -5 * E.inOut(k) }));
      await wait(260);
      await tween(560, (k) => { const e = E.inOut(k); pose(-3 + 6 * e, 0, { r: -5 + 10 * e }); });
      await wait(260);
      await tween(360, (k) => { const e = E.inOut(k); pose(3 * (1 - e), 0, { r: 5 * (1 - e) }); });
    },
    hop: async (g) => {
      const J = g.mob ? 14 : 18;
      await tween(150, (k) => pose(0, 0, { sx: 1 + 0.08 * k, sy: 1 - 0.12 * k }));
      await tween(230, (k) => pose(0, -J * E.out(k), { sx: 1.08 - 0.13 * k, sy: 0.88 + 0.2 * k }));
      await tween(210, (k) => pose(0, -J * (1 - E.in(k)), { sx: 0.95 + 0.03 * k, sy: 1.08 - 0.06 * k }));
      await tween(300, (k) => { const d = E.damp(k, 2.5); pose(0, 0, { sx: 1 + 0.1 * d, sy: 1 - 0.14 * d }); });
    },
  };
  function startRun(id, isAct) {
    runTok++; cancelAnimationFrame(rafId); clearStage();
    run = { id, act: !!isAct }; fab.dataset.bibiRun = id;
    if (isAct) fab.classList.add('bibirun');   // 動作中鈕本身不接點擊（比比不在那裡）；待機小動作不擋，滑鼠移過去照樣開環
    ensureStage(); pose(0, 0);
  }
  function endRun() {
    run = null; tipFollow = false;
    if (fab) { fab.classList.remove('bibirun'); delete fab.dataset.bibiRun; }
    pose(0, 0); clearStage();
  }
  function finishAct() {
    mode = 'idle'; if (fab) delete fab.dataset.bibiAct;
    if (ring) ring.classList.remove('cool');
    applyIdle(); schedFidget();
  }
  /** 打斷：立刻回原位、道具清掉。動作被打斷＝回情境待機；小動作被打斷＝只回原位（東張西望換過圖就換回來） */
  function stopRun(why) {
    if (!run) return false;
    const wasAct = run.act; lastStop = why || '';
    runTok++; cancelAnimationFrame(rafId); clearTimeout(actTimer);
    endRun();
    if (wasAct) finishAct(); else if (want !== idleFile()) applyIdle();
    return true;
  }
  const stopFidget = () => { if (run && !run.act) stopRun('fidget'); };
  /** 腳本在「對的那一刻」叫 cue() 說這個動作的台詞（例如接到球才說「接到了！」）；cue('…') 說指定的一句 */
  function cue(text) {
    if (!run || !run.act) return;
    if (text) { say(text, 1800); return; }
    if (run.line && !run.said) { run.said = true; say(run.line, 2600); }
  }
  function playChoreo(a, line) {
    clearTimeout(fidgetT); stopFidget(); preload();
    const g = geo();                      // 量原位（鈕本身不會動，只有裡面的圖層在動）
    startRun(a.id, true); tipFollow = true; run.line = line; watchOn(); run.tipSide = a.id === 'pet' || a.id === 'popcorn';   // 摸摸頭（手在頭上）、爆米花跳（跳很高）：泡泡放旁邊，不擋到
    const tok = runTok;
    CHOREO[a.id](g).then(() => { if (tok === runTok) { if (!run.said) cue(); endRun(); finishAct(); } },
      (e) => { if (e !== ABORT && tok === runTok) { endRun(); finishAct(); if (window.console) console.warn('bibi', e); } });
  }
  function schedFidget() {
    clearTimeout(fidgetT);
    if (noFidget || reduce()) return;
    fidgetT = setTimeout(() => doFidget(), 20000 + Math.random() * 20000);
  }
  function doFidget(kind) {
    const p = $('supPanel');
    if (!fab || run || mode !== 'idle' || sleeping || ringOpen() || hoverFab || document.hidden || !canRing() || (p && !p.hidden) || reduce()) { schedFidget(); return false; }
    const ks = Object.keys(FIDGET); kind = FIDGET[kind] ? kind : ks[Math.floor(Math.random() * ks.length)];
    const g = geo();
    startRun('f_' + kind, false);
    const tok = runTok;
    FIDGET[kind](g).then(() => { if (tok === runTok) { endRun(); if (want !== idleFile()) applyIdle(); } schedFidget(); },
      (e) => { if (e !== ABORT && tok === runTok) endRun(); schedFidget(); });
    return kind;
  }

  /* ---------- 接上 #supFab ---------- */
  function attach() {
    fab = $('supFab'); if (!fab || fab.dataset.bibiOn) return !!fab;
    fab.dataset.bibiOn = '1';
    const a = fab.querySelector('img.supgif');
    if (!a) return false;
    a.classList.add('bibiimg'); a.removeAttribute('width'); a.removeAttribute('height');
    const b = a.cloneNode(false); b.classList.add('bibiback'); b.removeAttribute('src');
    /* 兩張圖包進「位移層 .bibiwrap ＞ 身體層 .bibibody」：動作編排只動這兩層的 transform，鈕本身（拖曳、避讓量的是它）不動 */
    wrapEl = document.createElement('span'); wrapEl.className = 'bibiwrap'; wrapEl.setAttribute('aria-hidden', 'true');
    bodyEl = document.createElement('span'); bodyEl.className = 'bibibody';
    const hopEl = document.createElement('span'); hopEl.className = 'bibihop';   // 待機「開心的跳」的 CSS 動畫掛在這層（跟編排的 transform 分開，互不覆蓋）
    hopEl.appendChild(bodyEl); wrapEl.appendChild(hopEl); a.before(wrapEl); bodyEl.appendChild(a); bodyEl.appendChild(b);
    imgs = [a, b]; front = 0;
    shown = '';   // 開場那張（support.js 的 wave.webp，沒有版本戳）一律換成帶版本戳的待機圖
    fab.title = '';   // 改用自己的提示泡泡（說比比現在在幹嘛）；讀屏仍讀 aria-label「客服：比比・問題小助手」
    tip = document.createElement('div'); tip.id = 'bibiTip'; tip.className = 'bibitip'; tip.hidden = true; tip.setAttribute('aria-hidden', 'true');
    document.body.appendChild(tip);

    /* 桌機：滑鼠移到比比上 → 展開環；離開比比與環 → 收起 */
    fab.addEventListener('pointerenter', (e) => {
      if (e.pointerType === 'touch' || tapMode()) return;
      hoverFab = true; clearTimeout(closeT);
      if (!ringOpen()) { say(tipText()); openT = setTimeout(openRing, 140); }
    });
    fab.addEventListener('pointerleave', (e) => { if (e.pointerType !== 'touch') hoverFab = false; });
    document.addEventListener('pointermove', (e) => {
      if (e.pointerType === 'touch' || tapMode()) return;
      if (fab.classList.contains('supdrag')) { if (ringOpen()) closeRing(true); return; }
      if (!ringOpen() && !openT) return;
      const inside = e.target && e.target.closest && (e.target.closest('#supFab') || e.target.closest('#bibiRing'));
      if (inside) { clearTimeout(closeT); closeT = 0; return; }
      if (!closeT) closeT = setTimeout(() => { closeT = 0; if (!ringOpen()) { clearTimeout(openT); openT = 0; hideTip(); return; } closeRing(); }, 320);
    }, { passive: true });
    /* 點比比本體：桌機照舊開客服（先把環收掉、比比走回原位）；手機第一下展開環、再點一下收起 */
    document.addEventListener('click', (e) => {
      const t = e.target; if (!t || !t.closest || !t.closest('#supFab')) return;
      if (tapMode()) {
        const p = $('supPanel');
        if (p && !p.hidden) return;               // 客服面板開著：照舊交給 support.js（收起面板）
        e.stopImmediatePropagation(); e.preventDefault();
        if (ringOpen()) closeRing(); else openRing();
        return;
      }
      clearTimeout(openT); openT = 0;
      if (ringOpen()) closeRing(true); else hideTip();
    }, true);
    /* 點別的地方收起（手機最常用；桌機滑鼠離開本來就會收） */
    document.addEventListener('pointerdown', (e) => {
      const t = e.target;
      if (t && t.closest && (t.closest('#supFab') || t.closest('#bibiRing'))) return;
      /* 手機點空白＝收環；比比正在外面玩也一起叫回原位（桌機滑鼠點頁面不打斷，等他玩完） */
      if (run && (tapMode() || e.pointerType === 'touch')) stopRun('tap');
      if (!ringOpen()) return;
      closeRing();
    }, true);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { stopRun('esc'); if (ringOpen()) closeRing(true); } });
    window.addEventListener('hashchange', () => { stopRun('page'); closeRing(true); setTimeout(applyIdle, 0); });
    document.addEventListener('visibilitychange', () => { if (document.hidden) stopRun('hidden'); });
    /* 視窗真的變大小才收（手機好幾支會自己派假的 resize 叫圖表重排，例如 mobile3.js 換指數卡；那種不算） */
    let runWH = innerWidth + 'x' + innerHeight;
    window.addEventListener('resize', () => {
      const wh = innerWidth + 'x' + innerHeight;
      if (ringOpen() && openWH !== wh) closeRing(true);
      if (run && runWH !== wh) stopRun('resize');   // 視窗真的變大小：跑出去的位置算的是舊視窗，叫回原位
      runWH = wh;
    });
    window.addEventListener('tw:quotes', () => { const t = tpe(); if (t.hm >= 540 && t.hm <= 810) applyIdle(); });
    /* 客服關掉／被抽屜蓋住／進管理區：環一起收 */
    try {
      new MutationObserver(() => { if (ringOpen() && !canRing() && !($('supPanel') || {}).hidden === false) closeRing(true); if (fabOff()) { stopRun('off'); closeRing(true); hideTip(); } })
        .observe(html, { attributes: true, attributeFilter: ['class'] });
      new MutationObserver(() => { if (!fab) return; if (fab.hidden || fab.classList.contains('supaway')) { stopRun('away'); if (ringOpen()) closeRing(true); } })
        .observe(fab, { attributes: true, attributeFilter: ['class', 'hidden'] });
    } catch (e) { /* 舊瀏覽器：靠點擊與換頁收起 */ }
    applyIdle();
    loadHol().then(applyIdle);
    setInterval(applyIdle, IDLE_EVERY);
    schedFidget();
    return true;
  }

  function boot() {
    const s = document.createElement('style'); s.id = 'bibiCss'; s.textContent = CSS; document.head.appendChild(s);
    if (attach()) return;
    /* support.js 在 DOMContentLoaded 才建 #supFab：等它出現 */
    let n = 0; const iv = setInterval(() => { if (attach() || ++n > 80) clearInterval(iv); }, 100);
  }
  /* 驗收用：注入假時間／假漲跌／假休市表、直接播某個動作、讀目前狀態 */
  window.Bibi = {
    MAP: { IDLE, ACTS, MS },
    state: () => ({ file: fab && fab.dataset.bibi || shown, shown, want, mode, idle: idleNow && idleNow.key, say: idleNow && idleNow.say, sleeping, ring: ringOpen(),
      run: run ? run.id : '', happy: !!(fab && fab.classList.contains('bibihappy')), off: { x: OFF.x, y: OFF.y }, body: bodyEl ? bodyEl.style.transform : '', stop: lastStop, props: stage ? stage.children.length : 0,
      src: imgs[front] ? (imgs[front].getAttribute('src') || '').replace(/[?#].*$/, '') : '',
      page: ring ? +(ring.dataset.page || 0) : 0, pages: ring ? +(ring.dataset.pages || 0) : 0, tip: tip && !tip.hidden && tip.classList.contains('on') ? tip.textContent : '' }),
    test: (o) => { o = o || {}; if ('now' in o) T.now = o.now; if ('pct' in o) T.pct = o.pct; if ('hol' in o) T.hol = o.hol;
      if ('fidget' in o) { noFidget = !o.fidget; if (noFidget) { clearTimeout(fidgetT); stopFidget(); } else schedFidget(); } applyIdle(); return idleNow; },
    fidget: (k) => doFidget(k), stop: (why) => stopRun(why || 'api'), PART,
    reset: () => { T.now = null; T.pct = undefined; T.hol = null; applyIdle(); },
    idle: () => idle(), open: openRing, close: closeRing, act,
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
