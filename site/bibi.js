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
    pet: 3250, eat_grass: 3220, ball: 2950, spin: 2080, highfive: 1480, dance: 1560, hug: 1640, wake_once: 1440, selfie: 1480,
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
  const src = (f) => 'brand/bibi/' + f + '.webp';
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
.bibiring.cool .bopt:not(.bask){opacity:.45;cursor:default}
.bibiring.cool .bopt:not(.bask):hover{transform:translate(var(--x),var(--y)) scale(1)}
.bibitip{position:fixed;z-index:1202;max-width:220px;padding:7px 11px;border-radius:12px;background:var(--panel-2);color:var(--ink);border:1px solid var(--line-2);
  font-size:13px;line-height:1.45;box-shadow:0 10px 24px -10px rgba(0,0,0,.55);pointer-events:none;opacity:0;transform:translateY(4px);transition:opacity .18s,transform .18s;white-space:normal}
.bibitip.on{opacity:1;transform:none}
.bibitip[hidden]{display:none}
.bibifx{position:fixed;z-index:1202;width:20px;height:20px;margin:-10px 0 0 -10px;pointer-events:none;animation:bibifx 1.15s ease-out forwards}
.bibifx svg{width:100%;height:100%;display:block}
@keyframes bibifx{0%{transform:translate(0,0) scale(.4) rotate(0);opacity:0}15%{opacity:1}100%{transform:translate(var(--fx),var(--fy)) scale(1) rotate(var(--fr));opacity:0}}
.bibiflash{position:fixed;z-index:1203;width:150px;height:150px;margin:-75px 0 0 -75px;border-radius:50%;pointer-events:none;background:radial-gradient(closest-side,#fff,rgba(255,255,255,0));animation:bibiflash .5s ease-out forwards}
@keyframes bibiflash{0%{opacity:0}20%{opacity:.95}100%{opacity:0}}
html.fab-off .bibiring,html.fab-off .bibitip,html.fab-off .bibifx{display:none!important}
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
        return { key: 'down', say: `大盤小跌 ${pf(p)}%，沒關係，比比陪你` };
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
  let replay = 0;
  /** once＝播一次的專屬動作：網址加 #n 讓瀏覽器從第一格重播（同一個檔、同一份快取；10-11 實測換 #片段 會重播、換新 <img> 不會） */
  function show(file, once) {
    if (!fab) return;
    want = file;
    if (file === shown && !once) return;
    const back = imgs[1 - front], url = src(file) + (once ? '#r' + (++replay) : '');
    const swap = () => {
      if (want !== file) return;        // 載入中又換了別的：以最後一個為準
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
    show(sleeping ? SLEEP_FILE : (idleNow.file || (IDLE[idleNow.key] || IDLE.other).file));
  }

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
    const c = center(), w = tip.offsetWidth, h = tip.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
    let left = c.x - w / 2, top = c.y - 46 - h - 8;
    if (ring && ring.classList.contains('on')) {
      /* 環開著：泡泡放在所有小圈的上緣之上（放不下就放下緣之下），水平對齊小圈群的中間 */
      const bs = [...ring.querySelectorAll('.bopt')].map((b) => ({ x: c.x + parseFloat(b.style.getPropertyValue('--x')), y: c.y + parseFloat(b.style.getPropertyValue('--y')) }));
      const half = OPT() / 2, minY = Math.min(c.y - 46, ...bs.map((q) => q.y - half)), maxY = Math.max(c.y + 46, ...bs.map((q) => q.y + half));
      const mx = bs.reduce((t, q) => t + q.x, c.x) / (bs.length + 1);
      left = mx - w / 2; top = minY - h - 8;
      if (top < 8) top = maxY + 8;
    } else if (top < 8) top = c.y + 46 + 8;
    left = Math.max(8, Math.min(vw - w - 8, left)); top = Math.max(8, Math.min(vh - h - 8, top));
    tip.style.left = Math.round(left) + 'px'; tip.style.top = Math.round(top) + 'px';
  }

  /* ---------- 環 ---------- */
  let openWH = '', ring = null, hoverFab = false, openT = 0, closeT = 0, openedAt = 0, ringMaxR = 0;
  const OPT = () => (isMob() ? 40 : 42);
  function center() {
    const r = fab.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }
  function topLim() {
    const tb = document.querySelector('header.topbar');
    if (tb && tb.getClientRects().length) { const cs = getComputedStyle(tb), r = tb.getBoundingClientRect(); if ((cs.position === 'fixed' || cs.position === 'sticky') && r.bottom > 0) return r.bottom + 6; }
    return 8;
  }
  function buildRing() {
    ring = document.createElement('div'); ring.id = 'bibiRing'; ring.className = 'bibiring'; ring.hidden = true;
    ring.setAttribute('role', 'menu'); ring.setAttribute('aria-label', '跟比比玩');
    ring.innerHTML = '<div class="bzone"></div><svg class="btrack" aria-hidden="true"></svg>' + ACTS.map((a, i) => `<button type="button" class="bopt${a.ask ? ' bask' : ''}${ICON_IMG[a.id] ? ' bpic' : ''}" role="menuitem" data-act="${a.id}" style="transition-delay:${i * 28}ms">${iconOf(a.id)}</button>`).join('');
    document.body.appendChild(ring);
    ring.querySelectorAll('.bopt').forEach((b) => { const a = ACTS.find((x) => x.id === b.dataset.act); b.title = a.name; b.setAttribute('aria-label', a.name); });
    ring.addEventListener('click', (e) => {
      const b = e.target.closest('.bopt');
      if (!b) { if (tapMode()) closeRing(); return; }    // 手機：點圈內空白＝收起
      e.stopPropagation(); act(b.dataset.act);
    });
    ring.addEventListener('pointerover', (e) => {
      if (e.pointerType === 'touch') return;
      const b = e.target.closest('.bopt'); if (!b) return;
      if (Date.now() - openedAt < 450) return;   // 比比剛走出來、小圈滑到游標底下的那一下不算「指到」，泡泡先講心情
      if (mode === 'idle' || b.classList.contains('bask')) say(b.getAttribute('aria-label'));
    });
  }
  function iconOf(id) {
    if (ICON_IMG[id]) return `<img src="brand/bibi/icons/${ICON_IMG[id]}.webp" alt="" draggable="false">`;
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
    return fab && !fab.hidden && !fabOff() && !fab.classList.contains('supaway') && !fab.classList.contains('supdrag') && ($('supPanel') || {}).hidden !== false;
  }
  /** 以比比當下的位置為圓心排小圈：每一層半徑算出「整顆小圈都在視窗內」的角度範圍（比比在右下角＝往左上的扇形；
      被拖到左邊／上方就自動往右／往下翻；在畫面中間＝一整圈），由內往外一層一層放，放滿 10 個為止。
      回傳 [{x, y}]（相對圓心）、每層的弧線（畫虛線軌道）、最外層半徑。 */
  function layout(cx, cy) {
    const mob = isMob(), S = OPT(), gap = mob ? 6 : 8, step = S + gap;
    const radii = mob ? [78, 126, 174, 222] : [84, 136, 188, 240];
    const vw = document.documentElement.clientWidth || window.innerWidth, vh = window.innerHeight, pad = 6;
    const L = pad, Rr = vw - pad, Tt = Math.max(pad, topLim()), B = vh - pad;
    const fits = (r, d) => { const t = d * Math.PI / 180, x = cx + r * Math.cos(t), y = cy + r * Math.sin(t); return x - S / 2 >= L && x + S / 2 <= Rr && y - S / 2 >= Tt && y + S / 2 <= B; };
    const out = [], arcs = []; let left = ACTS.length, maxR = 0;
    for (const r of radii) {
      if (!left) break;
      const ok = []; for (let d = 0; d < 360; d++) ok.push(fits(r, d));
      let n, angs = [];
      if (ok.every(Boolean)) {
        n = Math.min(left, Math.floor(2 * Math.PI * r / step));
        for (let i = 0; i < n; i++) angs.push(-90 + i * 360 / n);
        arcs.push({ r, full: true });
      } else {
        /* 最長的一段連續可放角度（可能跨過 0°） */
        let best = { len: 0, st: 0 };
        for (let st = 0; st < 360; st++) {
          if (!ok[st] || ok[(st + 359) % 360]) continue;
          let len = 0; while (len < 360 && ok[(st + len) % 360]) len++;
          if (len > best.len) best = { len, st };
        }
        if (best.len < 2) continue;
        const span = (best.len - 1), stepDeg = step / r * 180 / Math.PI;
        const cap = Math.floor(span / stepDeg) + 1;
        n = Math.min(left, cap); if (n < 1) continue;
        const tot = (n - 1) * stepDeg, mid = best.st + span / 2;
        for (let i = 0; i < n; i++) angs.push(mid - tot / 2 + i * stepDeg);
        arcs.push({ r, a0: mid - tot / 2 - stepDeg * 0.45, a1: mid + tot / 2 + stepDeg * 0.45 });
      }
      angs.forEach((d) => { const t = d * Math.PI / 180; out.push({ x: Math.round(Math.cos(t) * r), y: Math.round(Math.sin(t) * r) }); });
      left -= n; maxR = r;
    }
    return { pts: out, arcs, maxR };
  }
  function arcPath(a) {
    if (a.full) return `M ${a.r} 0 A ${a.r} ${a.r} 0 1 1 ${-a.r} 0 A ${a.r} ${a.r} 0 1 1 ${a.r} 0`;
    const p = (d) => { const t = d * Math.PI / 180; return `${(Math.cos(t) * a.r).toFixed(1)} ${(Math.sin(t) * a.r).toFixed(1)}`; };
    return `M ${p(a.a0)} A ${a.r} ${a.r} 0 ${a.a1 - a.a0 > 180 ? 1 : 0} 1 ${p(a.a1)}`;
  }
  function openRing() {
    clearTimeout(closeT); clearTimeout(openT);
    if (!canRing() || (ring && ring.classList.contains('on'))) return;
    if (!ring) buildRing();
    const r = fab.getBoundingClientRect(), X = r.left + r.width / 2, Y = r.top + r.height / 2;
    const L = layout(X, Y);
    fab.classList.add('bibiopen');
    ring.style.left = Math.round(X) + 'px'; ring.style.top = Math.round(Y) + 'px';
    const zone = L.maxR + OPT() / 2 + 14;
    ring.querySelector('.bzone').style.cssText = `left:${-zone}px;top:${-zone}px;width:${zone * 2}px;height:${zone * 2}px`;
    ring.querySelector('.btrack').innerHTML = L.arcs.map((a) => `<path d="${arcPath(a)}"/>`).join('');
    ringMaxR = L.maxR;
    openedAt = Date.now(); openWH = innerWidth + 'x' + innerHeight;
    ring.querySelectorAll('.bopt').forEach((b, i) => {
      const q = L.pts[i] || { x: 0, y: -L.maxR };
      b.style.setProperty('--x', q.x + 'px'); b.style.setProperty('--y', q.y + 'px');
      b.style.transitionDelay = reduce() ? '0ms' : (i * 28) + 'ms';
      b.style.width = b.style.height = OPT() + 'px'; b.style.margin = `${-OPT() / 2}px 0 0 ${-OPT() / 2}px`;
    });
    syncSleepBtn();
    ring.hidden = false; fab.dataset.ring = '1';
    void ring.offsetWidth;
    ring.classList.add('on');
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

  /* ---------- 動作 ---------- */
  function act(id) {
    const a0 = ACTS.find((x) => x.id === id); if (!a0) return;
    if (a0.ask) { closeRing(true); if (window.TwSupport && window.TwSupport.open) window.TwSupport.open(); return; }
    if (mode === 'act') return;                       // 冷卻：上一個動作還沒播完
    let a = a0;
    if (a0.sleep && sleeping) a = Object.assign({ id: 'wake' }, a0.wake);
    const n = bump(a0.id === 'sleep' ? (sleeping ? 'wake' : 'sleep') : a0.id);
    mode = 'act'; fab.dataset.bibiAct = a.id === 'wake' ? 'wake' : a0.id;
    if (ring) ring.classList.add('cool');
    show(a.file, !!a.once);
    /* 轉圈圈：專屬素材到了就照素材轉；還在用歪頭代替時，CSS 讓整隻轉 360° */
    if (a0.id === 'spin' && a.file === 'tilt') { fab.classList.remove('bibispin'); void fab.offsetWidth; fab.classList.add('bibispin'); }
    burst(a.fx);
    let line = a.say[Math.floor(Math.random() * a.say.length)];
    if (a.cnt && (n === 3 || n % 5 === 0)) line = a.cnt(n);
    say(line, 2600);
    const dur = a.once ? (MS[a.file] || 2500) + 150 : Math.max(1800, Math.min(3200, (MS[a.file] || 1200) * 2));
    clearTimeout(actTimer);
    actTimer = setTimeout(() => {
      mode = 'idle'; delete fab.dataset.bibiAct; fab.classList.remove('bibispin');
      if (a0.sleep) { sleeping = a.id !== 'wake'; fab.dataset.bibiSleep = sleeping ? '1' : ''; syncSleepBtn(); }
      if (ring) ring.classList.remove('cool');
      applyIdle();
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

  /* ---------- 接上 #supFab ---------- */
  function attach() {
    fab = $('supFab'); if (!fab || fab.dataset.bibiOn) return !!fab;
    fab.dataset.bibiOn = '1';
    const a = fab.querySelector('img.supgif');
    if (!a) return false;
    a.classList.add('bibiimg'); a.removeAttribute('width'); a.removeAttribute('height');
    const b = a.cloneNode(false); b.classList.add('bibiback'); b.removeAttribute('src');
    a.after(b);
    imgs = [a, b]; front = 0;
    shown = (a.getAttribute('src') || '').replace(/^.*\/([^/]+)\.webp$/, '$1');
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
      if (!ringOpen()) return;
      const t = e.target;
      if (t && t.closest && (t.closest('#supFab') || t.closest('#bibiRing'))) return;
      closeRing();
    }, true);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ringOpen()) closeRing(true); });
    window.addEventListener('hashchange', () => { closeRing(true); setTimeout(applyIdle, 0); });
    /* 視窗真的變大小才收（手機好幾支會自己派假的 resize 叫圖表重排，例如 mobile3.js 換指數卡；那種不算） */
    window.addEventListener('resize', () => { if (ringOpen() && openWH !== innerWidth + 'x' + innerHeight) closeRing(true); });
    window.addEventListener('tw:quotes', () => { const t = tpe(); if (t.hm >= 540 && t.hm <= 810) applyIdle(); });
    /* 客服關掉／被抽屜蓋住／進管理區：環一起收 */
    try {
      new MutationObserver(() => { if (ringOpen() && !canRing() && !($('supPanel') || {}).hidden === false) closeRing(true); if (fabOff()) { closeRing(true); hideTip(); } })
        .observe(html, { attributes: true, attributeFilter: ['class'] });
      new MutationObserver(() => { if (!fab) return; if ((fab.hidden || fab.classList.contains('supaway')) && ringOpen()) closeRing(true); })
        .observe(fab, { attributes: true, attributeFilter: ['class', 'hidden'] });
    } catch (e) { /* 舊瀏覽器：靠點擊與換頁收起 */ }
    applyIdle();
    loadHol().then(applyIdle);
    setInterval(applyIdle, IDLE_EVERY);
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
      src: imgs[front] ? (imgs[front].getAttribute('src') || '').replace(/#.*$/, '') : '', tip: tip && !tip.hidden && tip.classList.contains('on') ? tip.textContent : '' }),
    test: (o) => { o = o || {}; if ('now' in o) T.now = o.now; if ('pct' in o) T.pct = o.pct; if ('hol' in o) T.hol = o.hol; applyIdle(); return idleNow; },
    reset: () => { T.now = null; T.pct = undefined; T.hol = null; applyIdle(); },
    idle: () => idle(), open: openRing, close: closeRing, act,
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
