/* ============================================================================
   比比（右下角客服鈕的天竺鼠）：情境待機＋環狀互動選單（2026-10-11）
   ----------------------------------------------------------------------------
   Andy 10-11：「將右下方的GIF圖多點變化，會依據不同分頁，不同功能，漲跌，白天晚上，假日平日國定假日等情境下去變化…
     目的是讓比比看起來更像真的在陪伴你。並且最好是有新增互動效果，例如可以摸摸他 餵它吃草 跟他玩球 讓他轉圈圈…
     互動紐的形式像圖一這樣游標移動過去，會出現其他互動小圈(上方都會有簡單的物件圖)，點擊後出現對應動作」
   圖一：比比在中間，周圍一圈小圓圈。

   這支只接手 support.js 建好的 #supFab（不重做按鈕）：
     ① 待機：只有一款＝第一版客服鈕那支 8 格跳躍 GIF（idle_hop，一直循環；Andy 10-12）。情境（國定假日 → 週末 → 深夜 → 盤中漲跌 → 分頁）
        只決定泡泡說明句，不換圖；換頁／每 5 分鐘／盤中報價更新時重算說明句。
     ② 環狀選單：桌機滑鼠移到比比上展開；手機（html.m4／≤640，或沒有滑鼠的裝置）點一下展開、點空白收起。
        以比比當下位置為圓心、只排一層（角落＝扇形弧、畫面中間＝一整圈），每頁 5 格、最後一格「下一頁 ›」（10-11 晚 Andy）。
     ③ 點小圈：球／草／摸摸／轉圈／爆米花跑「動作編排」腳本（比比整顆離開原位、道具照物理走，見下面「動作編排引擎」）；
        其他動作換圖＋小特效。播完回情境待機；播的時候其他小圈冷卻（連點不爆）。
        點比比本體：桌機照舊打開客服面板（既有行為、既有驗收不變）；手機第一下是展開環，環裡的「問比比」才開客服。
     ④ 互動次數記在這台裝置（localStorage tw.bibi.n，不送伺服器），比比偶爾回一句「今天第 3 次摸我了～」。
   客服鈕被關掉（html.fab-off）、管理區（fab.hidden）、被抽屜蓋住（supaway）時，環與提示泡泡一律不出現。
   素材：site/brand/bibi/<名稱>.webp（160px 動態 WebP，scripts/anim/bibi_site.py 產生，用到才載）。
   ★ 動畫單位新素材到了：跑 bibi_site.py 轉檔 → 改下面 ACTS 的 file／PART。待機不准再加情境款（DECISIONS #357）。
   ============================================================================ */
(function () {
  'use strict';

  /* ---------- 素材對照表（MAP）：情境／動作 → 檔名（site/brand/bibi/<file>.webp） ----------
     want＝動畫單位正在做的專屬素材；到了就把 file 改成 want（MS 也補上它的總長，bibi_site.py 最後一行會印）。 */
  const MS = {   // 每組一輪的毫秒數；bibi_site.py 最後一行印的就是這張表
    // 待機（唯一一款，循環）：第一版客服鈕的 8 格跳躍 GIF（bibi_site.py idle_hop）
    idle_hop: 800,
    sleep_loop: 1360,                     // 點「睡覺」之後一直睡（互動，不是待機；10-12 四腳版：趴著蓋被子，8 格循環）
    // 互動（動畫單位 G1／G2 專屬素材；播一輪＝這個毫秒數就回情境待機）
    // 互動（動畫單位 10-11 深夜照原版造型重畫；bibi_site.py 最後一行印的毫秒數）
    highfive: 1230, dance: 1690, hug: 1470, wake_once: 1630, selfie: 1200,   // wake_once／selfie：10-12 四腳版
    eat_grass_v2: 2110, ball_catch: 2170, ball_catch_l: 2170, popcorn: 1530, pet_v2: 1730, spin_v2: 1580, dizzy: 1420,
    run_r: 600, run_l: 600, run_start_r: 460, run_stop_r: 1060,
    hit: 650, cry: 1000,                  // 打他（播一次，最後一格＝cry 第 1 格）／哭哭（循環一輪）：10-12 四腳版
    eat_q: 1900, spin_q: 1290,            // 10-12 四腳版：側面低頭吃地上的草（16 格）／四腳小跑繞一圈＋暈眩（13 格），播完都回 Default
    face_star: 1370,
    receive: 1370, receive_grass: 1370, receive_ball: 1370,   // 互動「接東西」（動畫單位照原版造型重做的骨架版）
  };
  /* 分頁（hash 第一段）→ 情境鍵＋泡泡說明句（10-12 起只換說明句，不換圖） */
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
  /* 環狀選單的 18 個小圈（「問比比」最內層，由內往外排；10-12 加玩具六件組）。fx＝點了冒什麼小特效；say＝回應（隨機一句）；cnt＝第 N 次的回應 */
  /* once：素材是播一次的專屬動作（播一輪＝MS 毫秒就回待機）；沒有 once 的是現有素材代替（循環素材，播兩輪） */
  const ACTS = [
    { id: 'ask', name: '問比比', ask: true },
    { id: 'popcorn', name: '爆米花', file: 'popcorn', once: true, fx: 'star', say: ['爆米花跳！啵啵啵～', '開心到跳起來了！'], cnt: (n) => `今天爆米花跳了 ${n} 次！` },
    { id: 'pet', name: '摸摸頭', file: 'pet_v2', once: true, fx: 'heart', say: ['好舒服～', '再摸一下嘛', '嘿嘿，癢癢的'], cnt: (n) => `今天第 ${n} 次摸我了～` },
    { id: 'grass', name: '餵牧草', file: 'eat_q', once: true, fx: 'grass', say: ['嚼嚼嚼…牧草好香！', '謝謝你餵我～'], cnt: (n) => `今天吃了 ${n} 口牧草，好飽～` },
    { id: 'ball', name: '玩球', file: 'ball_catch', once: true, fx: 'ball', say: ['接到了！', '再丟一次！'], cnt: (n) => `今天陪我玩了 ${n} 次球！` },
    /* 玩具六件組（Andy 10-12：「我很喜歡丟球的互動效果，希望能多點這樣的」）：腳本在下面「玩具六件組」；file＝減少動態偏好時只換的那張圖 */
    { id: 'snack', name: '撒零食', file: 'popcorn', once: true, fx: 'star', say: ['吃光光了！', '每一顆都好香～'], cnt: (n) => `今天撒了 ${n} 次零食，比比圓滾滾` },
    { id: 'bubble', name: '吹泡泡', file: 'popcorn', once: true, fx: 'star', say: ['泡泡全部戳破了！', '啵啵啵～好好玩'], cnt: (n) => `今天吹了 ${n} 次泡泡！` },
    { id: 'feather', name: '羽毛棒', file: 'popcorn', once: true, fx: 'star', say: ['抓到羽毛了！', '再晃一次嘛～'], cnt: (n) => `今天玩了 ${n} 次羽毛棒！` },
    { id: 'yarn', name: '毛線球', file: 'ball_catch', once: true, fx: 'star', say: ['掙脫了！比比最強', '毛線好難纏…'], cnt: (n) => `今天被毛線纏了 ${n} 次…` },
    { id: 'plane', name: '紙飛機', file: 'face_star', once: true, fx: 'star', say: ['飛機飛好遠！', '再射一架嘛～'], cnt: (n) => `今天看了 ${n} 架紙飛機！` },
    { id: 'leaf', name: '落葉', file: 'popcorn', once: true, fx: 'star', say: ['撲到葉子了！', '秋天好好玩～'], cnt: (n) => `今天撲了 ${n} 次落葉！` },
    { id: 'spin', name: '轉圈圈', file: 'spin_q', once: true, fx: 'star', say: ['轉轉轉～頭好暈', '咕嚕咕嚕…眼睛在轉圈'], cnt: (n) => `今天轉了 ${n} 圈，頭好暈～` },
    { id: 'hit', name: '打他', file: 'hit', once: true, fx: 'star', say: ['嗚嗚…好痛', '哇——比比哭哭了'], cnt: (n) => `今天被打了 ${n} 次…嗚嗚` },
    { id: 'five', name: '擊掌', file: 'highfive', once: true, fx: 'star', say: ['耶！擊掌！', '啪！今天也一起加油'], cnt: (n) => `今天第 ${n} 次擊掌，默契 100！` },
    { id: 'dance', name: '跳舞', file: 'dance', once: true, fx: 'note', say: ['跳起來～', '比比的舞步帥嗎？'], cnt: (n) => `今天跳了 ${n} 支舞！` },
    { id: 'hug', name: '抱抱', file: 'hug', once: true, fx: 'heart', say: ['抱抱～比比陪著你', '暖暖的'], cnt: (n) => `今天第 ${n} 個抱抱，好幸福` },
    { id: 'sleep', name: '睡覺', file: 'sleep_loop', fx: 'z', sleep: true, say: ['比比去睡一下，Zzz…'], wake: { name: '叫醒', file: 'wake_once', once: true, fx: 'star', say: ['醒來了！繼續陪你看盤'] } },
    { id: 'selfie', name: '拍照比耶', file: 'selfie', once: true, fx: 'flash', say: ['咔嚓！比耶～', '拍得可愛嗎？'], cnt: (n) => `今天拍了 ${n} 張，比比是網美` },
  ];
  /* 素材對照（was＝10-11 G1／G2 交件前用的替代素材，留著是為了萬一新素材要退回時知道原本是哪一組） */
  /* 小圈上的物件圖：動畫單位 10-11 交的 10 個圖示（docs/anim/bibi_icons → brand/bibi/icons/*.webp，奶油白圓底＋粗描邊，深淺主題都清楚）。
     沒列在這裡的（叫醒）用下面的線條圖示，外框照圖示同款畫。 */
  const ICON_IMG = { ask: 'chat', popcorn: 'popcorn', hit: 'hammer', pet: 'hand', grass: 'grass', ball: 'ball', spin: 'spin', five: 'highfive', dance: 'music', hug: 'heart', sleep: 'moon', selfie: 'camera' };
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
    snack: '<g stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><rect x="2.6" y="13.4" width="8.4" height="5.2" rx="2.6" fill="#e9a65a" transform="rotate(-20 6.8 16)"/><rect x="12.6" y="14.2" width="8.4" height="5.2" rx="2.6" fill="#8fcf6a" transform="rotate(16 16.8 16.8)"/><rect x="7.6" y="7.6" width="8.4" height="5.2" rx="2.6" fill="#f2c45a"/></g><path d="M19 3.4v3.4M17.3 5.1h3.4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
    bubble: '<circle cx="10" cy="13" r="6.5" fill="#bfe6ff" fill-opacity=".7" stroke="currentColor" stroke-width="1.5"/><circle cx="17.6" cy="6.6" r="3.6" fill="#bfe6ff" fill-opacity=".7" stroke="currentColor" stroke-width="1.4"/><circle cx="18.2" cy="17.6" r="2.1" fill="#bfe6ff" stroke="currentColor" stroke-width="1.2"/><path d="M6.6 11.2a3.8 3.8 0 0 1 2.7-2.6" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round"/>',
    feather: '<path d="M3 21.5L13.5 4" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/><path d="M13.5 4c3 .8 4.6 2.8 4.6 5.6" stroke="currentColor" stroke-width="1.1" fill="none"/><path d="M18.1 9.4c-3.2 2.2-3.8 6.6-1.1 11.4 3.1-3 3.8-7.6 1.1-11.4z" fill="#ff8fd1" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>',
    yarn: '<circle cx="11" cy="11.6" r="7.6" fill="#ff9db8" stroke="currentColor" stroke-width="1.6"/><path d="M4.4 9.2c4 1 9 5 11 9.6M5.4 15.8c3-4 7-7.6 12.2-7.6M9 4.4c2 4 2.6 9.2 1 14.8" fill="none" stroke="currentColor" stroke-width="1.1"/><path d="M17.6 15.6c2.2 1 3.4 3.2 2.8 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    plane: '<path d="M22 3L2 10.6l7.2 2.6L22 3z" fill="#fff" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M22 3L9.2 13.2l2.2 7.4 3.4-4.6z" fill="#cfe6ff" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M2.6 19.6c2-1.1 3.6-1.1 5.2 0" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" fill="none" stroke-dasharray="1.4 2"/>',
    leaf: '<path d="M4 20C4 10 10 4 20 4c0 10-6 16-16 16z" fill="#ffb067" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M4.6 19.4L15 9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><path d="M15.4 21.4c.4-1.6 1.6-2.6 3.4-2.8-.2 1.8-1.4 2.8-3.4 2.8z" fill="#ffb3c9" stroke="currentColor" stroke-width="1.1" stroke-linejoin="round"/>',
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
    bub: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="6" fill="#bfe6ff" fill-opacity=".5" stroke="#3d9bd6" stroke-width="2"/></svg>',
    crumb: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5" fill="#e9a65a" stroke="#7a4a1a" stroke-width="1.4"/></svg>',
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
  const AV = '1012b';
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
/* 爆米花圖示（動畫單位 popcorn_icon）本身沒有圓底：補上跟其他圖示同款的奶油圓底＋深描邊 */
.bibiring .bopt.bpic[data-act=popcorn]{background:#fdf5e9;border:2.5px solid #1a0907}
.bibiring .bopt.bpic[data-act=popcorn] img{padding:5px;box-sizing:border-box;border-radius:0}
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
html.fab-off .bibiring,html.fab-off .bibitip,html.fab-off .bibifx,html.fab-off #bibiStage{display:none!important}
/* ---------- 動作編排（10-11 晚）：比比整顆可以離開右下角 ----------
   #supFab 本身不動（拖曳記位、避讓判斷都量它）；動的是裡面包著兩張圖的 .bibiwrap（位移）與 .bibibody（擠壓伸展／傾斜），
   都在 position:fixed 的鈕裡面，用 transform 位移 → 不撐出捲軸、不擋點擊（pointer-events:none）。
   道具（球、草、手、星星…）放在 #bibiStage：fixed 蓋整個視窗、overflow:hidden（道具飛到哪都不會撐出捲軸，手機也留在 390 內）。 */
.supfab .bibiwrap,.supfab .bibibody{position:absolute;inset:0;pointer-events:none;display:block}
.supfab .bibiwrap{will-change:transform}
.supfab .bibibody{transform-origin:50% 96%}
.supfab .bibihop{position:absolute;inset:0;pointer-events:none;display:block;transform-origin:50% 96%}
.supfab.bibirun{pointer-events:none}
.supfab.bibirun .supgif.bibiimg,.supfab.bibiquick .supgif.bibiimg{transition:none}   /* 動作中、跳一下（Default↔jump）直接切格：交叉淡化會看到兩隻半透明疊在一起 */
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
    /* Andy 10-12：「比比改成一直跳，但是是在主畫面狀態，我說的狀態就是第一版做出來的樣式，一直處於跳的狀態」＋「是這張喔」（9 格跳躍分格圖）
       → 待機只有一款：第一版客服鈕那支 8 格跳躍 GIF（idle_hop）一直循環。深夜／國定假日／大跌／週末／聖誕／各分頁都不換圖，只換泡泡說明句。
       系統開「減少動態」＝同一支 GIF 的第 1 格靜態圖。 */
    r.file = reduce() ? IDLE_STILL : IDLE_HOP;
    return r;
  }
  function idle0() {
    const t = tpe(), hol = T.hol || HOL || {};
    if (hol[t.ymd]) return { key: 'holiday', say: `今天${String(hol[t.ymd]).replace(/（.*$/, '')}，台股休市，比比也放假一天～` };
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
    show(f);
    hopSched();
  }
  /* ---------- 待機 ----------
     Andy 10-12：待機只用第一版跳躍 GIF（site/brand/src/support_anim_1009.gif → bibi_site.py idle_hop，160px 透明動態 WebP、無限循環）。
     jump（圖二）與 default_idle（圖三）10-12 起都不再用在待機。 */
  const IDLE_HOP = 'idle_hop', IDLE_STILL = 'idle_hop_still';
  function hopSched() { /* 待機素材本身循環，不必排程（留著給舊呼叫點） */ }

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
  /* 10-11 深夜 Andy 看了線上版：「互動按鈕改成原本那樣」（選擇題確認＝全部小圈一次攤開，回到第一版：分層扇形一次全部顯示、拿掉「下一頁」）。
     以比比當下位置為圓心，每一層半徑算出「整顆小圈都在視窗內」的角度範圍，由內往外一層層排，直到全部放完；
     比比在右下角＝往左上的扇形；被拖到左邊／上方自動往右／往下翻；在畫面中間＝一整圈。「問比比」排第一個＝最內層（離比比最近）。 */
  let openWH = '', ring = null, hoverFab = false, openT = 0, closeT = 0, openedAt = 0, ringMaxR = 0;
  const OPT = () => (isMob() ? 40 : 44);   // 手機 40px（Andy 規則 ≥40、≥32 觸控下限）；桌機 44px
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
    ring.innerHTML = '<div class="bzone"></div><svg class="btrack" aria-hidden="true"></svg>'
      + ACTS.map((a) => `<button type="button" class="bopt${a.ask ? ' bask' : ''}${ICON_IMG[a.id] ? ' bpic' : ' bsvg2'}" role="menuitem" data-act="${a.id}">${iconOf(a.id)}</button>`).join('');
    document.body.appendChild(ring);
    ring.querySelectorAll('.bopt[data-act]').forEach((b) => { const a = ACTS.find((x) => x.id === b.dataset.act); b.title = a.name; b.setAttribute('aria-label', a.name); });
    ring.addEventListener('click', (e) => {
      const b = e.target.closest('.bopt');
      if (!b) { if (tapMode()) { closeRing(); stopRun('tap'); } return; }    // 手機：點圈內空白＝收起
      e.stopPropagation();
      act(b.dataset.act, b);
    });
    ring.addEventListener('pointerover', (e) => {
      if (e.pointerType === 'touch') return;
      const b = e.target.closest('.bopt'); if (!b) return;
      if (Date.now() - openedAt < 450) return;   // 小圈剛彈到游標底下的那一下不算「指到」，泡泡先講心情
      if (mode === 'idle' || b.classList.contains('bask')) say(b.getAttribute('aria-label'));
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
  /** 分層扇形：由內往外，每一層找「整顆小圈都在視窗內」最長的一段連續角度，能放幾個放幾個，放滿全部為止。
      回傳 { pts:[{x,y}]（相對圓心，順序＝ACTS 順序）, arcs（每層虛線軌道）, maxR } */
  function layout(cx, cy) {
    const mob = isMob(), S = OPT(), gap = mob ? 6 : 8, step = S + gap;
    const radii = mob ? [76, 124, 172, 220, 268, 316, 364] : [84, 136, 188, 240, 292, 344, 396];   // 18 顆（10-12 玩具六件組）放不下就再往外一層
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
        let best = { len: 0, st: 0 };
        for (let st = 0; st < 360; st++) {
          if (!ok[st] || ok[(st + 359) % 360]) continue;
          let len = 0; while (len < 360 && ok[(st + len) % 360]) len++;
          if (len > best.len) best = { len, st };
        }
        if (best.len < 2) continue;
        const span = best.len - 1, stepDeg = step / r * 180 / Math.PI;
        const cap = Math.floor(span / stepDeg) + 1;
        n = Math.min(left, cap); if (n < 1) continue;
        const tot = (n - 1) * stepDeg, mid = best.st + span / 2;
        for (let i = 0; i < n; i++) angs.push(mid - tot / 2 + i * stepDeg);
        arcs.push({ r, a0: mid - tot / 2 - stepDeg * 0.45, a1: mid + tot / 2 + stepDeg * 0.45 });
      }
      angs.forEach((d) => { const t = d * Math.PI / 180; out.push({ x: Math.round(Math.cos(t) * r), y: Math.round(Math.sin(t) * r), r }); });
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
    if (!canRing() || (ring && ring.classList.contains('on')) || (run && run.act)) return;   // 比比跑出去玩的時候不開環（圓心是空的）
    stopFidget(); preload();
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
      b.style.transitionDelay = reduce() ? '0ms' : (i * 24) + 'ms';
      b.style.width = b.style.height = OPT() + 'px'; b.style.margin = `${-OPT() / 2}px 0 0 ${-OPT() / 2}px`;
    });
    syncSleepBtn();
    ring.hidden = false; fab.dataset.ring = '1';
    void ring.offsetWidth;
    ring.classList.add('on');
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
    hideTip(); setTimeout(hopSched, 0);
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
  let actFrom = null, hitUntil = 0, hitLog = [];
  function act(id, btn) {
    const a0 = ACTS.find((x) => x.id === id); if (!a0) return;
    if (a0.ask) { closeRing(true); if (window.TwSupport && window.TwSupport.open) window.TwSupport.open(); return; }
    if (mode === 'act') return;                       // 冷卻：上一個動作還沒播完
    /* 打他：不准連打（Andy：「點太多次時加冷卻」）—— 每次打完至少隔 4 秒；一分鐘內第 3 次起隔 15 秒 */
    if (a0.id === 'hit' && Date.now() < hitUntil) { say('比比還在痛…等一下再玩嘛', 1800); return; }
    if (a0.id === 'hit') {
      const now = Date.now(); hitLog = hitLog.filter((t) => now - t < 60000); hitLog.push(now);
      hitUntil = now + 4500 + (hitLog.length >= 3 ? 15000 : 4000);   // 4.5 秒＝整段（飛＋敲＋哭）的長度
    }
    const br = btn && btn.getBoundingClientRect ? btn.getBoundingClientRect() : null;
    actFrom = br && br.width ? { x: br.left + br.width / 2, y: br.top + br.height / 2, w: br.width } : null;   // 道具從被點的那顆小圈飛出來
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
      setTimeout(() => { if (run && run.act && run.id === a.id && !run.said && ['ball', 'grass', 'hit', 'snack', 'bubble', 'feather', 'yarn', 'plane', 'leaf'].indexOf(run.id) < 0) cue(); }, 60);   // 摸摸／轉圈開頭就說；球、草等到接住／開吃、打他等到哭才說
      return;
    }
    if (ring) ring.classList.add('cool');
    show(a.file, !!a.once);
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
     receive_*：動畫單位照原版 Default 造型重做的骨架版（第一版 Andy 退件「已經跟原來的不同了」，重做版 CEO 對照過 → 互動可以接）。
     清空就退回替代（face_star＋SVG 手）。⚠ 待機只用 idle_hop（Andy 10-12），不用骨架的 happy_hop、也不用 jump／default_idle。 */
  const PART = { run_l: 'run_l', run_r: 'run_r', run_start_r: 'run_start_r', run_stop_r: 'run_stop_r',
    ball_catch: 'ball_catch', ball_catch_l: 'ball_catch_l', eat: 'eat_q', pet: 'pet_v2', spin: 'spin_q', popcorn: 'popcorn',   // eat／spin：10-12 四腳版（spin 素材本身有暈眩，不再另接 dizzy）
    receive: 'receive', receive_grass: 'receive_grass', receive_ball: 'receive_ball',
    hit: 'hit', cry: 'cry',                         // 打他（播一次）／哭哭（循環）：動畫單位 10-11 深夜交件
    // 玩具六件組（10-12）：動畫單位的專屬素材還沒到，先用現有動作代替（跳撲＝popcorn、蹲低＝idle_hop_still）
    snack_eat: 'idle_hop_still', leap: 'popcorn', crouch: 'idle_hop_still',   // 低頭吃零食：四腳版 eat_q 畫了地上的草、跟零食對不上 → 先用蹲低靜態格＋網頁的低頭啃動作，bibi_snack 到了換掉
  };
  /* 替代素材太長時只播這麼久（key＝零件、值＝[替代檔名, 毫秒]；換成真零件後檔名對不上就自動照 MS 播完整段） */
  /* 道具圖：動畫單位的 PNG 到了填檔名（放 site/brand/bibi/props/<名>.png）；空字串＝用下面畫的 inline SVG */
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
    heart: () => FX.heart,
  };
  const E = {
    inOut: (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
    out: (k) => 1 - Math.pow(1 - k, 3),
    in: (k) => k * k * k,
    damp: (k, f) => Math.max(-0.12, Math.exp(-5 * k) * Math.cos(f * Math.PI * k)),   // 回彈：越來越小的來回（反向最多 0.12：回彈時身體只微微拉高，天竺鼠不會「站起來」）
  };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const ABORT = { abort: true };
  let wrapEl = null, bodyEl = null, stage = null, run = null, runTok = 0, rafId = 0, fidgetT = 0, noFidget = true, tipFollow = false, lastStop = '';
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
  /** 同時跑的那一段（不馬上 await）：被打斷時它也會丟 ABORT，先掛一個空的 catch，免得變成「沒人接的 Promise 錯誤」 */
  const par = (p) => { p.catch(() => {}); return p; };
  function ensureStage() {
    if (stage && stage.isConnected) return stage;
    stage = document.createElement('div'); stage.id = 'bibiStage'; stage.setAttribute('aria-hidden', 'true');
    document.body.appendChild(stage); return stage;
  }
  function clearStage() { if (stage) stage.innerHTML = ''; }
  /** 道具：寬 w 高 h，用 at() 以「中心點」擺位置 */
  function prop(kind, w, h) {
    const el = document.createElement('div'); el.className = 'bp bp-' + kind + (kind === 'shadow' ? ' bshadow' : '');
    el.style.width = w + 'px'; el.style.height = h + 'px'; el._w = w; el._h = h; el.style.opacity = '0';   // 第一次 at() 擺好位置才出現（不然會在左上角閃一格）
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
  let preloaded = false;
  function preload() {
    if (preloaded) return; preloaded = true;
    Object.keys(PART).forEach((k) => { if (PART[k]) { const i = new Image(); i.src = src(PART[k]); } });
    ['ball', 'grass'].forEach((f) => { const i = new Image(); i.src = `brand/bibi/props/${f}.webp?v=${AV}`; });
  }
  function idleFile() { return sleeping ? SLEEP_FILE : ((idleNow && idleNow.file) || IDLE_HOP); }

  /* ---------- 給的動作（Andy 10-11 深夜：「伸出去的手太奇怪了，需要修正」） ----------
     不再出手：道具（球／草）從「被點的那顆小圈」沿弧線飛到比比右前方、輕輕彈一下，比比播 receive_grass／receive_ball 接住
     （素材第 3 格＝360ms 肉掌接到，之後東西畫在素材裡，網頁的道具就收掉）。
     sc()＝素材庫場景座標（比比中心 x=248、網站圖的裁切框左上 (28,52)、寬 440）→ 螢幕座標。 */
  const sc = (g, X, Y) => ({ x: g.cx + (X - 248) * g.s / 440, y: g.top + (Y - 52) * g.s / 440 });
  const GRAB = 360;                          // receive 第 3 格開始＝接到的那一刻（140＋220）
  /** 道具圖（brand/bibi/props/<名>.webp，bibi_site.py props 從動畫單位的 ball_prop／grass_prop 裁出來）；w×h 是螢幕尺寸 */
  function propPic(kind, w, h) {
    const el = document.createElement('div'); el.className = 'bp bp-' + kind;
    el.style.width = Math.round(w) + 'px'; el.style.height = Math.round(h) + 'px'; el._w = w; el._h = h; el.style.opacity = '0';
    el.innerHTML = `<img src="brand/bibi/props/${kind}.webp?v=${AV}" alt="" draggable="false" style="width:100%;height:100%;display:block">`;
    ensureStage().appendChild(el); return el;
  }
  /** 從哪裡飛出來：被點的小圈中心；用程式叫的（Bibi.act）沒有小圈 → 比比左上方 */
  function srcPoint(g) {
    if (actFrom && actFrom.w) return { x: actFrom.x, y: actFrom.y };
    return { x: clamp(g.cx + g.dir * 150, 20, g.vw - 20), y: Math.max(20, g.top - 110) };
  }
  /** 給東西：道具從小圈沿弧線飛到 P、落點輕彈一下，比比同時播「接」；接到那一刻道具收掉。回傳 { hold：比比抱東西的位置 } */
  async function receive(g, kind) {
    /* Andy 10-12：「比比是天竺鼠，他是4隻腳的…不可以因為配合互動就改變身體原有設定」→ 草落在比比面前的地上（躺著），
       不是停在半空讓比比用手接；比比低頭去拿（往前探、壓低） */
    const k = g.s / 440, grassLie = kind === 'grass';
    const P = grassLie ? { x: sc(g, 372, 0).x, y: g.foot - g.s * 0.045 } : sc(g, 372, 360);
    const S = srcPoint(g);
    const w = kind === 'grass' ? g.s * 0.2 : (g.mob ? 20 : 24), h = kind === 'grass' ? w * 128 / 60 : w;
    const el = propPic(kind, w, h);
    at(el, S.x, S.y, '', 0);                                   // 一建立就放在小圈上（不然第一格會在畫面左上角閃一下）
    /* 飛 520ms＋彈 110ms；「接」素材第 3 格（360ms）要剛好在落進肉掌那一刻 → 飛到第 270ms 才開始播接；
       比比本體從第 0 格就往前探（位移／身體變形），0.2 秒內一定看得到在動 */
    const T1 = 520, lift = Math.max(50, Math.abs(S.x - P.x) * 0.35), recvAt = T1 + 110 - GRAB;
    let recv = false;
    await tween(T1, (u, t) => {                                // 弧線飛過來（邊飛邊轉）
      if (!recv && t >= recvAt) { recv = true; show(PART['receive_' + kind] || PART.receive, true); }
      const e = E.inOut(u), x = S.x + (P.x - S.x) * e, y = S.y + (P.y + (grassLie ? 0 : 8) - S.y) * e - lift * Math.sin(Math.PI * u);
      at(el, x, y, ` rotate(${((kind === 'ball' ? 540 : 84) * e).toFixed(1)}deg)`, Math.min(1, u * 5));   // 草邊飛邊轉成橫躺
      pose(0, -3 * Math.sin(Math.PI * u), { sk: -4 * u, sy: 1 - 0.03 * u });   // 看到東西、往前探（身體壓低，不站起來）
    });
    await tween(110, (u) => {                                  // 落地輕彈一下（草：躺在地上彈一下）
      at(el, P.x, P.y + (grassLie ? 0 : 8) - (grassLie ? 6 : 10) * Math.sin(Math.PI * u), kind === 'ball' ? ' rotate(540deg)' : ' rotate(84deg)' + ` scale(${(1 + 0.06 * Math.sin(Math.PI * u)).toFixed(2)})`, 1);
      pose(0, 0, { sk: -4 * (1 - u), sy: 0.97 + 0.03 * u });
    });
    if (grassLie) await tween(160, (u) => pose(0, 0, { sk: -6 * u, sy: 1 - 0.05 * u, sx: 1 + 0.03 * u }));   // 低頭湊過去
    el.remove();                                               // 素材裡的肉掌接住了
    cue(kind === 'grass' ? '哇！牧草～給我的嗎？' : '哇！是球～');
    burstAt('star', P.x, P.y - 12, 3, 1.4);
    await tween(Math.max(0, (MS[PART['receive_' + kind]] || 1370) - GRAB), (u) => { const d = E.damp(u, 2.5); pose(0, 0, { sx: 1 + 0.05 * d, sy: 1 - 0.06 * d }); });
    return { hold: sc(g, 248, kind === 'grass' ? 372 : 392), k };
  }

  /* ---------- 腳本：玩球 ----------
     球從小圈飛過來、比比接住（receive_ball）→ 球從懷裡掉到腳邊一踢：往空間大的那一側滾（右下角＝往左）——拋物線、落地反彈越來越低
     （落地瞬間壓扁）、邊滾邊轉、越滾越慢、影子跟著縮放；比比先往後縮再衝（run_l／run_r），跑步時整顆上下彈、身體前傾，
     速度跟球一起慢下來；追上時急停回彈＋星星、播撲球（ball_catch／ball_catch_l，素材裡自己抱著球）；再跑回原位（run_r＋run_stop_r）。 */
  async function ballScript(g) {
    const dir = g.dir, R = g.mob ? 10 : 12, gap = g.s * 0.36, cx = g.cx;
    const D = clamp(dir < 0 ? cx - 34 - R : g.vw - 34 - R - cx, 110, g.mob ? 240 : 560);
    const bx0 = cx + dir * g.s * 0.28, bx1 = cx + dir * D, ground = g.foot;
    const H = g.mob ? [52, 26, 12, 5] : [70, 34, 16, 6], Tb = g.mob ? 1450 : 1800, lag = 360, T = Tb + 240;
    const segs = H.map(Math.sqrt), sum = segs.reduce((a, b) => a + b, 0), TB = Tb * 0.8;
    const sh = prop('shadow', R * 2.2, 7), ball = propPic('ball', R * 2, R * 2);
    sh.style.opacity = '0';
    /* 0.（Andy 10-12：天竺鼠是四隻腳的，不用手接）球從被點的小圈飛出、落在比比面前的地上彈兩下，滾到比比腳邊；
       比比看著它、身體往前湊 → 下一步用身體一頂把球推出去 */
    const S = srcPoint(g), L = cx + dir * Math.min(g.s * 1.5, Math.abs(S.x - cx) * 0.8 + g.s * 0.4);
    at(ball, S.x, S.y, '', 0);
    await tween(420, (u) => {                                  // 弧線飛到地上
      const e = E.in(u), x = S.x + (L - S.x) * u, y = S.y + (ground - R - S.y) * e - 50 * Math.sin(Math.PI * u) * (1 - u);
      at(ball, x, y, ` rotate(${(-dir * 360 * u).toFixed(1)}deg)`, Math.min(1, u * 5));
      const q = clamp(1 - (ground - R - y) / 120, 0, 1); at(sh, x, ground + 1, ` scale(${(0.4 + 0.6 * q).toFixed(2)})`, (0.5 * q).toFixed(2));
      pose(0, 0, { sk: -3 * u });                              // 0.2 秒內就在動：看過去、往前湊
    });
    cue('哇！是球～');
    const rollT = 700;
    await tween(rollT, (u) => {                                // 落地彈兩下、一路滾到腳邊、越滾越慢
      const x = L + (bx0 - L) * E.out(u), hb = u < 0.5 ? 14 * Math.abs(Math.sin(u * 2 * Math.PI)) * (1 - u * 1.6) : 0;
      at(ball, x, ground - R - hb, ` rotate(${((x - L) / R * 180 / Math.PI).toFixed(1)}deg)` + (hb < 1 && u < 0.5 ? ' scale(1.1,.88)' : ''), 1);
      at(sh, x, ground + 1, ` scale(${(1 - 0.03 * hb).toFixed(2)})`, 0.55);
      pose(-dir * 2 * u, 0, { sk: -4, sy: 1 - 0.04 * u, sx: 1 + 0.03 * u });   // 壓低身體等球過來
    });
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
    // 1. 身體縮起來蓄力（往後收、壓扁）→ 用整個身體往前一頂
    await tween(240, (k) => pose(-dir * (2 + 4 * E.out(k)), 0, { sx: 1 + 0.08 * E.out(k), sy: 1 - 0.1 * E.out(k), sk: dir * 4 * k }));
    await tween(120, (k) => pose(-dir * 6 + dir * 16 * E.out(k), 0, { sx: 1.08 - 0.06 * k, sy: 0.9 + 0.08 * k, sk: -dir * 8 * k }));   // 頂！
    // 2. 球飛出去；比比先往後縮一下（反向仰）再衝；跑步一路上下彈、往前傾；速度照球一起減
    const Db = (bx1 - cx) - dir * gap;
    let ran = false;
    await tween(T, (k, t) => {
      drawBall(ballAt(t));
      if (t < lag) {                                           // 頂完回彈一下，看球滾走
        const u = t / lag, d = E.damp(u, 2);
        pose(dir * 10, 0, { sx: 1 + 0.04 * d, sy: 1 - 0.05 * d, sk: -dir * 6 * (1 - u) });
        return;
      }
      if (!ran) { ran = true; show(dir < 0 ? PART.run_l : PART.run_r); }
      const u = (t - lag) / (T - lag), p = Db * E.inOut(u), back = dir * 10 * (1 - E.out(Math.min(1, u * 5)));   // 從頂出去的位置接著追
      const bob = -Math.abs(Math.sin((t - lag) / 150 * Math.PI)) * (g.mob ? 4 : 5);   // run 素材 600ms／8 格＝一步 150ms：上下彈跟腳步對上
      const sp = Math.sin(Math.PI * u);
      pose(p + back, bob, { sk: -dir * 7 * sp, sx: 1 - 0.02 * sp, sy: 1 + 0.025 * sp });
    });
    // 3. 撲到：急停前傾回彈、冒星星；撲球素材自己抱著球 → 網頁的球收掉
    const bxEnd = ballAt(Tb).x;
    cue();
    burstAt('star', bxEnd, ground - R * 2 - 6, 6, 1.6);
    show(dir < 0 ? PART.ball_catch_l : PART.ball_catch, true);
    await tween(240, (k) => {
      const d = E.damp(k, 3);
      pose(Db, 0, { sk: -dir * 12 * d, sx: 1 + 0.06 * d, sy: 1 - 0.08 * d });
      ball.style.opacity = sh.style.opacity = (1 - k).toFixed(2);
    });
    ball.remove(); sh.remove();
    await wait(Math.max(300, (MS[dir < 0 ? PART.ball_catch_l : PART.ball_catch] || 2170) - 240));
    // 4. 跑回原位：起跑 → 跑 → 到位時煞車（run_stop_r 只有面向右的，往右跑回家時才用）
    const back = dir < 0;
    if (back && PART.run_start_r) { show(PART.run_start_r, true); await tween(MS[PART.run_start_r] || 460, (k) => pose(Db + 6 * E.in(k), 0, { sk: -5 * k })); }
    show(dir < 0 ? PART.run_r : PART.run_l);
    const Tr = clamp(Math.abs(Db) / (g.mob ? 260 : 340) * 1000, 650, 1900), x0 = Db + (back && PART.run_start_r ? 6 : 0);
    await tween(Tr, (k, t) => {
      const sp = Math.sin(Math.PI * k);
      pose(x0 * (1 - E.inOut(k)), -Math.abs(Math.sin(t / 150 * Math.PI)) * (g.mob ? 4 : 5), { sk: dir * 7 * sp, sx: 1 - 0.02 * sp, sy: 1 + 0.025 * sp });
    });
    if (back && PART.run_stop_r) {
      show(PART.run_stop_r, true);
      await tween(MS[PART.run_stop_r] || 1060, (k) => { const d = E.damp(k, 3); pose(0, 0, { sk: dir * 9 * d, sx: 1 + 0.05 * d, sy: 1 - 0.06 * d }); });
    } else {
      show(idleFile());
      await tween(380, (k) => { const d = E.damp(k, 3); pose(0, 0, { sk: dir * 11 * d, sx: 1 + 0.06 * d, sy: 1 - 0.08 * d }); });
    }
  }

  /* ---------- 腳本：餵牧草（10-12 四腳版） ----------
     動畫單位四腳版 eat_q（bibi_eat_grass，16 格）：素材裡已經畫了地上的牧草，比比側面低頭吃、最後回 Default。
     → 網頁只負責「草從小圈飛過去、落在比比面前的地上」那一段（飛的那把用 props/grass.webp），落地那一刻收掉、播 eat_q；
       不再播 receive_grass（站起來用手接），吃的時候也不疊網頁的草（素材裡有）。
     落點＝素材裡那把草的位置：160px 素材的 x≈38（比比臉朝左）、貼地 → 螢幕上 比比中心往左 0.26 個圖寬、腳底。 */
  async function grassScript(g) {
    const S = srcPoint(g), P = { x: g.cx - g.s * 0.26, y: g.foot - g.s * 0.03 };
    const w = g.s * 0.12, h = w * 128 / 60, el = propPic('grass', w, h);
    at(el, S.x, S.y, '', 0);
    const lift = Math.max(50, Math.abs(S.x - P.x) * 0.35);
    await tween(520, (u) => {                                  // 弧線飛過來，邊飛邊轉成橫躺
      const e = E.inOut(u);
      at(el, S.x + (P.x - S.x) * e, S.y + (P.y - S.y) * e - lift * Math.sin(Math.PI * u), ` rotate(${(84 * e).toFixed(1)}deg)`, Math.min(1, u * 5));
      pose(0, 0, { sk: 4 * u, sy: 1 - 0.03 * u });             // 看到草、往前（左）湊，四腳不離地
    });
    await tween(110, (u) => { at(el, P.x, P.y - 6 * Math.sin(Math.PI * u), ' rotate(84deg)', 1); pose(0, 0, { sk: 4 * (1 - u), sy: 0.97 + 0.03 * u }); });
    el.remove();                                               // 素材裡的草接手
    show(PART.eat, true);
    cue();
    await tween(MS[PART.eat] || 1900, (k, t) => {
      if (t > 200 && t < 1250 && Math.floor(t / 260) !== Math.floor((t - 17) / 260)) burstAt('grass', P.x + g.s * 0.08, P.y - g.s * 0.12, 1, 1.4);
    });
  }
  function floatText(text, x, y) {
    const c = document.createElement('div'); c.className = 'bchew'; c.textContent = text;
    c.style.setProperty('--x', Math.round(x - 18) + 'px'); c.style.setProperty('--y', Math.round(y) + 'px');
    ensureStage().appendChild(c); setTimeout(() => c.remove(), 950);
  }

  /* ---------- 腳本：摸摸頭 ----------
     Andy 10-11 深夜：「伸出去的手太奇怪了」→ 不畫手：比比瞇眼享受（pet_v2），頭上冒一圈愛心（一顆一顆彈出來、慢慢繞、最後飄走），身體跟著一縮一縮。 */
  async function petScript(g) {
    show(PART.pet, true);
    const hx = g.cx, hy = g.top + g.s * 0.22, n = 6, hearts = [];
    for (let i = 0; i < n; i++) hearts.push(prop('heart', 15, 15));
    const T = Math.max(1500, MS[PART.pet] || 1730);
    await tween(T, (k, t) => {
      const rx = g.s * 0.42, ry = g.s * 0.13;
      hearts.forEach((h, i) => {
        const born = i * 90, age = t - born;
        if (age < 0) { h.style.opacity = '0'; return; }
        const a = -Math.PI / 2 + i * 2 * Math.PI / n + t / 900, pop = Math.min(1, age / 200), out = k > 0.82 ? (k - 0.82) / 0.18 : 0;
        const sc0 = pop < 1 ? 0.4 + 0.8 * E.out(pop) : 1 + 0.08 * Math.sin(t / 120 + i);
        at(h, hx + Math.cos(a) * rx, hy + Math.sin(a) * ry - 26 * out, ` scale(${sc0.toFixed(2)})`, (1 - out).toFixed(2));
      });
      const c = Math.max(0, Math.sin(t / 290 * Math.PI));     // 每 0.58 秒享受地縮一下
      pose(0, 0, { sy: 1 - 0.06 * c, sx: 1 + 0.04 * c });
    });
  }

  /* ---------- 腳本：轉圈圈（10-12 四腳版） ----------
     spin_q（bibi_spin，13 格、1290ms）：四腳小跑繞一圈 → 急停歪一邊 → 暈眩臉 → 回 Default，暈眩畫在素材裡，不再另外接 dizzy 循環。
     網頁只在跑的那段讓整顆微微離地。 */
  async function spinScript(g) {
    show(PART.spin, true);
    await tween(MS[PART.spin] || 1290, (k, t) => { const u = Math.min(1, t / 600); pose(0, -3 * Math.sin(Math.PI * u), {}); });
  }

  /* ---------- 腳本：天竺鼠爆米花跳（popcorn 素材：彈三下越來越小） ----------
     素材自己在原地彈，網頁再把整顆往上送一點（跟素材的三個最高點對齊），落地冒星星。 */
  async function popcornScript(g) {
    const dir = g.dir, J = g.mob ? 22 : 30;
    show(PART.popcorn, true); cue();
    const hops = [[50, 330, J], [400, 610, J * 0.45], [610, 750, J * 0.18]];   // popcorn 素材 storyboard：第 2～5 格、7～9 格、10～11 格
    let starred = 0;
    await tween(MS[PART.popcorn] || 1530, (k, t) => {
      let y = 0, r = 0;
      hops.forEach(([a, b, h], i) => { if (t >= a && t <= b) { const u = (t - a) / (b - a); y = -h * Math.sin(Math.PI * u); r = (i === 0 ? -dir * 8 : dir * 4) * Math.sin(Math.PI * u); } });
      const land = hops.findIndex(([, b]) => t >= b);
      pose(0, y, { r });
      for (let i = starred; i < hops.length; i++) if (t >= hops[i][1]) { burstAt('star', g.cx + (Math.random() - 0.5) * g.s * 0.4, g.foot - 6, i === 0 ? 3 : 1, 1.8); starred = i + 1; }
      void land;
    });
  }

  /* ---------- 腳本：打他 → 哭哭（Andy 10-11 深夜：「需要新增打他互動，並且他會哭哭」） ----------
     玩具槌（動畫單位 hammer_prop）從被點的小圈飛過去、在頭上輕敲一下 → 播 hit（被敲：壓扁、頭上冒包＋星星、含淚；
     最後一格是 Default，所以只播前 5 格 630ms）→ 循環播 cry 約 3.5 秒（素材自己抽泣、噴淚）→ 回待機。
     包、星星、眼淚都畫在素材裡，網頁只負責槌子飛過去、敲下去那一下和「嗚嗚」字。 */
  async function hitScript(g) {
    const S = srcPoint(g), head = sc(g, 248, 236);
    const w = g.mob ? 34 : 42, hm = propPic('hammer', w, w * 128 / 120);
    hm.style.transformOrigin = '82% 88%';                      // 繞著握把尾端揮
    at(hm, S.x, S.y, ' rotate(-200deg)', 0);
    const top = { x: head.x + g.s * 0.2, y: head.y - g.s * 0.3 };
    await tween(300, (u) => {                                  // 從小圈飛過去（邊飛邊轉、舉高）
      const e = E.inOut(u);
      at(hm, S.x + (top.x - S.x) * e, S.y + (top.y - S.y) * e - 40 * Math.sin(Math.PI * u), ` rotate(${(-200 * (1 - e) - 30).toFixed(1)}deg)`, Math.min(1, u * 5));
      pose(0, 0, { sy: 1 - 0.03 * u });                        // 比比縮一下（知道要被敲了）
    });
    await tween(100, (u) => at(hm, top.x, top.y + 10 * E.in(u), ` rotate(${(-30 + 60 * E.in(u)).toFixed(1)}deg)`));   // 咚！
    show(PART.hit, true);                                      // 被敲：素材第 1 格就是壓扁＋衝擊線
    burstAt('star', head.x, head.y - 8, 3, 2.2);
    const HIT_MS = MS[PART.hit] || 650;                        // 10-12 四腳版 hit 6 格整段播完（最後一格＝cry 第 1 格，直接接哭）
    await tween(HIT_MS, (u) => {                               // 槌子彈開淡出
      at(hm, top.x + 24 * u, top.y + 10 - 34 * Math.sin(Math.PI * Math.min(1, u * 1.6)), ` rotate(${(30 - 70 * u).toFixed(1)}deg)`, Math.max(0, 1 - u * 2.2).toFixed(2));
      pose(0, 0, { sy: 1 - 0.03 * (1 - u) });
    });
    hm.remove();
    cue();
    show(PART.cry);                                            // 哭哭：循環素材（抽噎、噴淚）
    let said = 0;
    await tween(3500, (u, t) => {
      if (!said && t > 200) { said = 1; floatText('嗚嗚', g.cx, g.top + g.s * 0.02); }          // 頭頂上方（說明泡泡在旁邊，不會疊到）
      if (said === 1 && t > 1700) { said = 2; floatText('嗚嗚', g.cx, g.top); }
    });
  }
  /* ======================================================================================
     玩具六件組（Andy 10-12：「我很喜歡丟球的互動效果，希望能多點這樣的」）
     照「玩球」的做法：道具從被點的小圈飛出、有物理（落地、反彈、滾動、飄、晃），比比真的在畫面上移動去追，最後回原位。
     撒零食／吹泡泡／羽毛棒／毛線球／紙飛機／落葉。動畫單位的專屬素材（docs/anim/bibi_<名>/）還沒到：
     道具先用下面畫的 SVG、比比用現有的動作（run_l／run_r／run_stop_r 跑、popcorn 跳撲、idle_hop_still 蹲低＋網頁身體前傾當低頭啃）代替；
     到了只改 PART 的 snack_eat／leap／crouch 那幾格＋bibi_site.py 轉檔，腳本不用動。
     ⚠ 比比是四隻腳的天竺鼠：全程不准做縱向拉長（站起來）的變形，跳只用位移（pose 的 y），身體只准壓扁／微傾。
     ⚠ 位置一律夾在視窗內（bx()）；道具都在 #bibiStage（fixed、overflow:hidden）→ 不撐捲軸，手機留在 390 內。
     ====================================================================================== */
  const TOY = {
    pellet: (c) => `<svg viewBox="0 0 20 14" aria-hidden="true"><rect x="1.5" y="2" width="17" height="10" rx="5" fill="${c}" stroke="#2b1611" stroke-width="1.7"/><path d="M7 5.2v3.6M10 5.2v3.6M13 5.2v3.6" stroke="#2b1611" stroke-opacity=".35" stroke-width="1.2" stroke-linecap="round"/></svg>`,
    bubble: () => '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="17" fill="#bfe6ff" fill-opacity=".28" stroke="#3d9bd6" stroke-width="2"/><path d="M9.5 15.5a11.5 11.5 0 0 1 8.5-7.5" stroke="#fff" stroke-width="2.8" fill="none" stroke-linecap="round"/><circle cx="27.5" cy="27" r="2.2" fill="#fff" opacity=".8"/></svg>',
    feather: () => '<svg viewBox="0 0 30 52" aria-hidden="true"><path d="M15 3C5 14 5 32 15 50C25 32 25 14 15 3z" fill="#ff8fd1" stroke="#2b1611" stroke-width="1.9" stroke-linejoin="round"/><path d="M15 7v41" stroke="#2b1611" stroke-width="1.4"/><path d="M15 17l-6-4M15 25l-7-4M15 33l-6-4M15 17l6-4M15 25l7-4M15 33l6-4" stroke="#c94f9e" stroke-width="1.3" stroke-linecap="round"/></svg>',
    yarn: () => '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="17" fill="#ff9db8" stroke="#2b1611" stroke-width="2.4"/><path d="M5 14c8 2 20 10 26 21M7 27c6-8 16-16 28-16M13 5c4 8 6 21 2 32M26 4c-2 10 0 22 9 28" fill="none" stroke="#c9577a" stroke-width="1.7"/></svg>',
    tangle: () => '<svg viewBox="0 0 100 70" aria-hidden="true"><g fill="none" stroke="#2b1611" stroke-width="4.6" stroke-linecap="round" opacity=".55"><ellipse cx="50" cy="38" rx="44" ry="17" transform="rotate(-12 50 38)"/><ellipse cx="50" cy="33" rx="40" ry="13" transform="rotate(14 50 33)"/><path d="M8 47c20 14 64 12 84-7"/></g>'
      + '<g fill="none" stroke="#ff7fa6" stroke-width="3" stroke-linecap="round"><ellipse cx="50" cy="38" rx="44" ry="17" transform="rotate(-12 50 38)"/><ellipse cx="50" cy="33" rx="40" ry="13" transform="rotate(14 50 33)"/><path d="M8 47c20 14 64 12 84-7"/></g></svg>',
    plane: () => '<svg viewBox="0 0 48 32" aria-hidden="true"><path d="M46 16L2 3l10 13L2 29z" fill="#fdf5e9" stroke="#2b1611" stroke-width="2" stroke-linejoin="round"/><path d="M46 16L12 16l-4 8z" fill="#cfe6ff" stroke="#2b1611" stroke-width="1.7" stroke-linejoin="round"/></svg>',
    leaf: (c) => `<svg viewBox="0 0 30 30" aria-hidden="true"><path d="M4 26C4 12 12 4 26 4c0 14-8 22-22 22z" fill="${c}" stroke="#2b1611" stroke-width="1.8" stroke-linejoin="round"/><path d="M5 25L19 11" stroke="#2b1611" stroke-width="1.3" stroke-linecap="round"/></svg>`,
  };
  /** 道具（SVG）：kind＝class 名（bp-<kind>，驗收用它找）、w×h 螢幕尺寸 */
  function toy(kind, w, h, html) {
    const el = document.createElement('div'); el.className = 'bp bp-' + kind;
    el.style.width = Math.round(w) + 'px'; el.style.height = Math.round(h) + 'px'; el._w = w; el._h = h; el.style.opacity = '0';
    el.innerHTML = html; ensureStage().appendChild(el); return el;
  }
  /** 一條線（毛線、羽毛棒的繩子）：蓋整個視窗的 SVG，path 由腳本每格改 d */
  function threadLayer(kind, color, width) {
    const el = document.createElement('div'); el.className = 'bp bp-' + kind;
    el.style.width = '100%'; el.style.height = '100%';
    el.innerHTML = `<svg width="100%" height="100%" aria-hidden="true"><path d="" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    ensureStage().appendChild(el); el._p = el.querySelector('path'); return el;
  }
  /** 背景動畫（泡泡飄、葉子落、羽毛晃）：跟比比的動作同時跑；回傳停止函式。被打斷時照樣丟 ABORT 收掉。 */
  function loopBg(fn) {
    const st = { on: true }, STOP = { stop: true };
    par(tween(60000, (k, t) => { if (!st.on) throw STOP; fn(t); }));
    return () => { st.on = false; };
  }
  /** 比比位移夾在視窗內（整顆圖都在畫面裡） */
  const bx = (g, x) => clamp(x, g.s / 2 + 4 - g.cx, g.vw - g.s / 2 - 4 - g.cx);
  const bobY = (g, t) => -Math.abs(Math.sin(t / 150 * Math.PI)) * (g.mob ? 4 : 5);   // run 素材一步 150ms
  /** 跑到位移 x1（從 x0），回傳實際到的位置。跑步上下彈、往前傾，身體只微微拉長（≤1.03） */
  async function runTo(g, x0, x1, speed) {
    x1 = bx(g, x1);
    const d = x1 - x0;
    if (Math.abs(d) < 3) { pose(x1, 0); return x1; }
    show(d < 0 ? PART.run_l : PART.run_r);
    const sg = Math.sign(d), T = clamp(Math.abs(d) / (speed || (g.mob ? 260 : 340)) * 1000, 260, 1600);
    await tween(T, (k, t) => { const sp = Math.sin(Math.PI * k); pose(x0 + d * E.inOut(k), bobY(g, t), { sk: -sg * 7 * sp, sx: 1 - 0.02 * sp, sy: 1 + 0.025 * sp }); });
    return x1;
  }
  /** 跑回原位：往右跑回家有煞車素材（run_stop_r），往左就急停回彈 */
  async function goHome(g, x) {
    if (Math.abs(x) >= 3) {
      await runTo(g, x, 0);
      if (x < 0 && PART.run_stop_r) {
        show(PART.run_stop_r, true);
        await tween(Math.min(700, MS[PART.run_stop_r] || 700), (k) => { const d = E.damp(k, 3); pose(0, 0, { sk: -9 * d, sx: 1 + 0.05 * d, sy: 1 - 0.06 * d }); });
      }
    }
    show(idleFile());
    await tween(300, (k) => { const d = E.damp(k, 3); pose(0, 0, { sx: 1 + 0.05 * d, sy: 1 - 0.06 * d }); });
  }
  /** 跳撲（四腳離地：只有位移往上，身體不拉長）：從 x0 跳到 x1、高 H；onPeak 在最高點叫一次；落地壓扁回彈 */
  async function leap(g, x0, x1, H, ms, onPeak) {
    x1 = bx(g, x1);
    show(PART.leap, true);
    const dx = x1 - x0; let peaked = false;
    await tween(ms, (k) => {
      const e = E.inOut(k), up = Math.sin(Math.PI * k);
      pose(x0 + dx * e, -H * up, { r: -Math.sign(dx) * 7 * up, sx: 1 - 0.02 * up, sy: 1 + 0.02 * up });
      if (!peaked && k >= 0.5) { peaked = true; if (onPeak) onPeak(); }
    });
    await tween(170, (k) => { const d = E.damp(k, 3); pose(x1, 0, { sx: 1 + 0.06 * d, sy: 1 - 0.08 * d }); });
    return x1;
  }

  /* ---------- 撒零食：一次撒 4～6 顆、落在比比附近不同位置；比比跑過去一顆一顆低頭吃，吃完才回原位 ---------- */
  async function snackScript(g) {
    const dir = g.dir, S = srcPoint(g), ground = g.foot - 4, n = 4 + Math.floor(Math.random() * 3);
    const span = g.mob ? 190 : 320, w = g.mob ? 16 : 19, h = w * 0.7;
    const cols = ['#e9a65a', '#8fcf6a', '#f2c45a', '#ff9f80'];
    const P = [];
    for (let i = 0; i < n; i++) {
      const x = clamp(g.cx + dir * (g.s * 0.5 + span * (i + 0.5) / n) + (Math.random() - 0.5) * 18, 14, g.vw - 14);
      const el = toy('snack', w, h, TOY.pellet(cols[i % cols.length]));
      at(el, S.x, S.y, '', 0);
      P.push({ el, x, y: ground - h / 2, rot: (Math.random() - 0.5) * 80, d: i * 80 });
    }
    const FLY = 480, T = FLY + 80 * (n - 1) + 160;
    await tween(T, (k, t) => {                                   // 一顆一顆撒出去：弧線、落地小彈一下
      P.forEach((p) => {
        const u = clamp((t - p.d) / FLY, 0, 1), v = clamp((t - p.d - FLY) / 160, 0, 1);
        if (t < p.d) return;
        const x = S.x + (p.x - S.x) * E.out(u), lift = 60 + Math.abs(S.x - p.x) * 0.25;
        const y = u < 1 ? S.y + (p.y - S.y) * E.in(u) - lift * Math.sin(Math.PI * u) : p.y - 8 * Math.sin(Math.PI * v);
        at(p.el, x, y, ` rotate(${(p.rot * u).toFixed(1)}deg)`, Math.min(1, u * 6));
      });
      pose(0, 0, { sk: -dir * 3 * Math.min(1, t / 300) });     // 0.2 秒內就在動：看過去
    });
    cue('哇！好多零食～');
    let x = 0;
    P.sort((a, b) => Math.abs(a.x - g.cx) - Math.abs(b.x - g.cx));
    for (const p of P) {
      const face = p.x < g.cx + x ? -1 : 1;                      // 往哪邊跑＝臉朝哪邊，嘴巴對準零食
      x = await runTo(g, x, p.x - g.cx - face * g.s * 0.3);
      show(PART.snack_eat, true);
      await tween(620, (k, t) => {
        const c = Math.sin(Math.PI * Math.min(1, k * 2.4));
        pose(x + face * 3 * c, 0, { sk: -face * 9 * c, sy: 1 - 0.08 * c, sx: 1 + 0.04 * c });   // 低頭啃一口（往零食那邊探、壓低，四腳不離地）
        at(p.el, p.x, p.y, ` rotate(${p.rot.toFixed(1)}deg) scale(${(1 - 0.85 * E.in(k)).toFixed(2)})`, (1 - k * 0.9).toFixed(2));
      });
      burstAt('crumb', p.x, p.y - 6, 3, 1.6);
      p.el.remove();
    }
    floatText('好飽～', g.cx + x, g.top);
    await goHome(g, x);
  }

  /* ---------- 吹泡泡：3～5 顆從小圈吹出來、慢慢往上飄、左右晃；比比追到底下跳起來戳破，破掉噴粒子 ---------- */
  async function bubbleScript(g) {
    const dir = g.dir, S = srcPoint(g), n = 3 + Math.floor(Math.random() * 3), R = g.mob ? 13 : 16;
    const span = g.mob ? 200 : 330, rise = g.mob ? 14 : 18, t0 = performance.now(), lo = topLim() + R + 4;
    const B = [];
    for (let i = 0; i < n; i++) {
      B.push({ el: toy('bubble', R * 2, R * 2, TOY.bubble()), x0: clamp(g.cx + dir * (g.s * 0.35 + span * (i + 0.5) / n), R + 8, g.vw - R - 8),
        y0: g.top + 6 - Math.random() * 18, born: i * 260, ph: Math.random() * 6, popped: false });
    }
    const pos = (b, t) => {                                      // 先從小圈飄到起點（500ms），之後慢慢上升、左右晃
      const a = t - b.born;
      if (a < 500) { const u = E.out(clamp(a / 500, 0, 1)); return { x: S.x + (b.x0 - S.x) * u, y: S.y + (b.y0 - S.y) * u, op: clamp(a / 120, 0, 1) }; }
      const s = (a - 500) / 1000;
      return { x: b.x0 + 14 * Math.sin(s * 2.4 + b.ph), y: Math.max(lo, b.y0 - rise * s), op: 1 };
    };
    B.forEach((b) => at(b.el, S.x, S.y, '', 0));
    const stop = loopBg(() => {
      const t = performance.now() - t0;
      B.forEach((b) => { if (b.popped || t < b.born) return; const p = pos(b, t); at(b.el, p.x, p.y, ` scale(${(0.6 + 0.4 * Math.min(1, (t - b.born) / 500)).toFixed(2)})`, p.op); });
    });
    pose(0, 0, { sk: -dir * 3 });
    await wait(260);
    cue('泡泡！比比要抓到它～');
    let x = 0;
    const order = B.slice().sort((a, b) => Math.abs(a.x0 - g.cx) - Math.abs(b.x0 - g.cx));
    for (const b of order) {
      const now = performance.now() - t0;
      if (now < b.born + 500) await wait(b.born + 500 - now);
      x = await runTo(g, x, pos(b, performance.now() - t0).x - g.cx);
      const LEAP = 520, tp = performance.now() - t0 + LEAP / 2, tgt = pos(b, tp);
      const H = clamp(g.top - (tgt.y + R * 0.6), 18, g.mob ? 80 : 100);
      x = await leap(g, x, tgt.x - g.cx, H, LEAP, () => {
        b.popped = true;
        const p = pos(b, performance.now() - t0);
        b.el.style.opacity = '0';
        burstAt('bub', p.x, p.y, 6, 2);
        floatText('啵！', p.x, p.y - 4);
      });
    }
    stop();
    await goHome(g, x);
  }

  /* ---------- 羽毛棒：羽毛（繩子連著被點的小圈）在比比前上方左右晃；比比蹲低扭屁股，然後往前撲 2～3 次，最後一下抓到 ---------- */
  async function featherScript(g) {
    const dir = g.dir, S = srcPoint(g), fw = g.mob ? 16 : 20, fh = fw * 52 / 30;
    const string = threadLayer('string', '#2b1611', 1.6), fe = toy('feather', fw, fh, TOY.feather());
    const fy0 = g.top - (g.mob ? 8 : 12);
    const F = { x: clamp(g.cx + dir * g.s * 0.85, 24, g.vw - 24), y: fy0, sw: 1 }, t0 = performance.now();
    let held = null;                                             // 抓到之後羽毛跟著比比的嘴
    const drawF = (x, y, rot, op) => {
      at(fe, x, y + fh / 2, ` rotate(${rot.toFixed(1)}deg)`, op);
      string._p.setAttribute('d', `M ${S.x.toFixed(1)} ${S.y.toFixed(1)} Q ${((S.x + x) / 2).toFixed(1)} ${(Math.max(S.y, y) + 30).toFixed(1)} ${x.toFixed(1)} ${y.toFixed(1)}`);
      string.style.opacity = String(op);
    };
    at(fe, S.x, S.y, '', 0); drawF(S.x, S.y, 0, 0);
    await tween(420, (k) => { const e = E.out(k); drawF(S.x + (F.x - S.x) * e, S.y + (F.y - S.y) * e, 0, Math.min(1, k * 5)); pose(0, 0, { sk: -dir * 3 * k }); });
    const stop = loopBg(() => {                                  // 左右晃（鐘擺）
      if (held) { drawF(held().x, held().y, -dir * 70, 1); return; }
      const t = (performance.now() - t0) / 1000, a = Math.sin(t * 6.2) * F.sw;
      drawF(F.x + 22 * a, F.y + 5 * Math.abs(a), -a * 28, 1);
    });
    cue('羽毛！比比盯上了…');
    let x = 0;
    const crouch = async (ms) => {                               // 蹲低、扭屁股（身體壓扁、左右扭，四腳不離地）
      show(PART.crouch);
      await tween(ms, (k, t) => { const w = Math.sin(t / 65 * Math.PI); pose(x - dir * 2 * w, 0, { sx: 1.07, sy: 0.9 + 0.01 * w, sk: 5 * w }); });
    };
    await crouch(1000);
    const N = 3, step = g.mob ? 38 : 56;
    for (let i = 0; i < N; i++) {
      if (i < N - 1) {                                           // 羽毛被抽走：往前（畫面內側）挪一段
        const fx0 = F.x, fx1 = clamp(F.x + dir * step, 24, g.vw - 24);
        par(tween(260, (k) => { F.x = fx0 + (fx1 - fx0) * E.out(k); F.sw = 1.5; }));
      }
      const tx = (i < N - 1 ? F.x + dir * step : F.x) - g.cx - dir * g.s * 0.25;
      x = await leap(g, x, tx, g.mob ? 22 : 30, 440, () => { if (i === N - 1) { held = () => ({ x: g.cx + OFF.x + dir * g.s * 0.3, y: g.top + OFF.y + g.s * 0.45 }); burstAt('star', F.x, F.y + fh / 2, 4, 1.8); } });
      F.sw = 1;
      if (i < N - 1) await crouch(420);
    }
    cue('抓到了！');
    await tween(400, (k, t) => { const w = Math.sin(t / 60 * Math.PI); pose(x, 0, { r: 4 * w, sy: 0.98, sx: 1.02 }); });
    held = null; stop();
    const hx = g.cx + x + dir * g.s * 0.3, hy = g.top + g.s * 0.45;
    par(tween(500, (k) => drawF(hx + (S.x - hx) * E.in(k), hy + (S.y - hy) * E.in(k), -dir * 70 * (1 - k), 1 - k)));   // 收回小圈那邊
    await goHome(g, x);
  }

  /* ---------- 毛線球：線球從小圈飛來、被比比一頂滾出去，後面拖一條線；比比追到撲上去 → 被線纏成一團、扭一扭掙脫 → 跑回家 ---------- */
  async function yarnScript(g) {
    const dir = g.dir, R = g.mob ? 10 : 12, ground = g.foot, S = srcPoint(g);
    const D = clamp(dir < 0 ? g.cx - 40 - R : g.vw - 40 - R - g.cx, 110, g.mob ? 220 : 480);
    const ball = toy('yarn', R * 2, R * 2, TOY.yarn()), line = threadLayer('thread', '#ff7fa6', 2.4);
    const trail = [];
    const drawLine = () => line._p.setAttribute('d', trail.length ? 'M ' + trail.map((p) => p.x.toFixed(1) + ' ' + p.y.toFixed(1)).join(' L ') : '');
    const L0 = g.cx + dir * g.s * 0.55;
    at(ball, S.x, S.y, '', 0);
    await tween(440, (u) => {                                    // 弧線飛到比比腳邊
      const x = S.x + (L0 - S.x) * u, y = S.y + (ground - R - S.y) * E.in(u) - 50 * Math.sin(Math.PI * u) * (1 - u);
      at(ball, x, y, ` rotate(${(-dir * 300 * u).toFixed(1)}deg)`, Math.min(1, u * 5));
      pose(0, 0, { sk: -dir * 3 * u });
    });
    cue('毛線球！');
    trail.push({ x: L0, y: ground - 1 });                        // 線頭留在落地的地方
    await tween(220, (k) => pose(-dir * 4 * E.out(k), 0, { sx: 1 + 0.07 * E.out(k), sy: 1 - 0.09 * E.out(k) }));   // 蓄力
    await tween(110, (k) => pose(-dir * 4 + dir * 12 * E.out(k), 0, { sk: -dir * 7 * k }));                        // 頂！
    const bx0 = L0, bx1 = g.cx + dir * D, Tb = g.mob ? 1300 : 1700, lag = 300;
    const ballAt = (t) => {                                      // 滾出去：越滾越慢、前段小彈兩下、線越拖越長
      const u = clamp(t / Tb, 0, 1), x = bx0 + (bx1 - bx0) * E.out(u), hb = u < 0.35 ? 12 * Math.abs(Math.sin(u / 0.35 * 2 * Math.PI)) * (1 - u * 2) : 0;
      return { x, y: ground - R - Math.max(0, hb), rot: (x - bx0) / R * 180 / Math.PI };
    };
    let x = dir * 8, ran = false;
    const Db = bx(g, bx1 - g.cx - dir * g.s * 0.45);
    await tween(Tb + 200, (k, t) => {
      const b = ballAt(t);
      at(ball, b.x, b.y, ` rotate(${b.rot.toFixed(1)}deg)`, 1);
      const last = trail[trail.length - 1];
      if (Math.abs(b.x - last.x) > 6) { trail.push({ x: b.x - dir * R * 0.6, y: ground - 1 - (trail.length % 2) * 1.5 }); drawLine(); }
      if (t < lag) { pose(x, 0, { sk: -dir * 5 * (1 - t / lag) }); return; }
      if (!ran) { ran = true; show(dir < 0 ? PART.run_l : PART.run_r); }
      const u = clamp((t - lag) / (Tb + 200 - lag), 0, 1), sp = Math.sin(Math.PI * u);
      pose(dir * 8 + (Db - dir * 8) * E.inOut(u), bobY(g, t), { sk: -dir * 7 * sp, sx: 1 - 0.02 * sp, sy: 1 + 0.025 * sp });
    });
    x = Db;
    const bEnd = ballAt(Tb);
    x = await leap(g, x, bEnd.x - g.cx, g.mob ? 18 : 24, 380, () => { ball.style.opacity = '0'; });   // 撲上去
    // 被纏住：線從線頭一路繞到比比身上，身上一團線；扭一扭
    const tg = toy('tangle', g.s * 0.95, g.s * 0.66, TOY.tangle());
    const where = () => ({ x: g.cx + OFF.x, y: g.top + OFF.y + g.s * 0.6 });
    trail.push({ x: g.cx + x, y: ground - g.s * 0.3 }); drawLine();
    cue('哎呀～被毛線纏住了！');
    show(PART.crouch);
    await tween(1400, (k, t) => {
      const w = Math.sin(t / 85 * Math.PI), q = where();
      pose(x + 3 * w, 0, { r: 8 * w, sx: 1.04, sy: 0.95 });
      at(tg, q.x, q.y, ` rotate(${(-6 * w).toFixed(1)}deg) scale(${Math.min(1, 0.5 + k * 4).toFixed(2)})`, Math.min(1, k * 6));
      trail[trail.length - 1] = { x: q.x, y: q.y }; drawLine();
    });
    // 掙脫：線團彈開、線淡掉
    burstAt('star', g.cx + x, g.top + g.s * 0.3, 5, 2);
    floatText('掙脫！', g.cx + x, g.top);
    await tween(320, (k) => {
      const q = where(), d = E.damp(k, 3);
      at(tg, q.x, q.y - 14 * k, ` scale(${(1 + 0.6 * k).toFixed(2)})`, (1 - k).toFixed(2));
      line.style.opacity = (1 - k).toFixed(2); ball.style.opacity = '0';
      pose(x, 0, { sx: 1 + 0.06 * d, sy: 1 - 0.08 * d });
    });
    tg.remove(); line.remove(); ball.remove();
    await goHome(g, x);
  }

  /* ---------- 紙飛機：飛機沿曲線在畫面上繞一圈（整條路線都在視窗內）、比比抬頭跟著轉，最後飛機落地滑一下，比比跑過去聞聞 ---------- */
  async function planeScript(g) {
    const dir = g.dir, S = srcPoint(g), pw = g.mob ? 30 : 38, ph = pw * 32 / 48, ground = g.foot - ph / 2;
    const R1 = g.mob ? 120 : 180, R2 = g.mob ? 64 : 90, tl = topLim();
    const C = { x: clamp(g.cx + dir * R1 * 0.95, R1 + pw, g.vw - R1 - pw), y: clamp(g.top - R2 - 24, tl + R2 + ph, g.vh - R2 - ph - 10) };
    const pl = toy('plane', pw, ph, TOY.plane());
    const Lx = clamp(g.cx + dir * (g.mob ? 170 : 280), pw, g.vw - pw);
    const a0 = Math.atan2((S.y - C.y) / R2, (S.x - C.x) / R1);   // 小圈在橢圓上對應的角度＝從最靠近小圈的那一點切進去
    const ell = (a) => ({ x: C.x + R1 * Math.cos(a), y: C.y + R2 * Math.sin(a) });
    const E0 = ell(a0), spinDir = dir < 0 ? -1 : 1;
    let prev = { x: S.x, y: S.y };
    const place = (p) => {                                      // 機頭朝飛行方向
      const ang = Math.atan2(p.y - prev.y, p.x - prev.x) * 180 / Math.PI;
      if (Math.hypot(p.x - prev.x, p.y - prev.y) > 0.3) pl._ang = ang;
      at(pl, p.x, p.y, ` rotate(${(pl._ang || 0).toFixed(1)}deg)`, 1); prev = p;
    };
    let x = 0;
    const look = (p, extra) => {                                 // 抬頭跟著轉：身體往飛機那邊歪、腳步小挪
      const rel = clamp((p.x - (g.cx + x)) / (g.mob ? 160 : 260), -1, 1);
      pose(x + (extra || 0), 0, { r: 8 * rel, sk: -6 * rel, sy: 0.97, sx: 1.02 });
    };
    at(pl, S.x, S.y, '', 0);
    show(PART.crouch);
    await tween(420, (k) => { const e = E.inOut(k); place({ x: S.x + (E0.x - S.x) * e, y: S.y + (E0.y - S.y) * e - 30 * Math.sin(Math.PI * k) }); look(prev); });
    cue('紙飛機！飛好高～');
    const LOOP = g.mob ? 2000 : 2400;
    await tween(LOOP, (k, t) => {                                // 繞一整圈
      const a = a0 + spinDir * 2 * Math.PI * E.inOut(k);
      place(ell(a));
      x = 6 * Math.sin(t / 260);                                 // 跟著小步原地轉
      look(prev);
    });
    const Ls = { x: prev.x, y: prev.y };
    await tween(900, (k) => {                                    // 往下滑翔、落地
      const e = E.in(k), px = Ls.x + (Lx - Ls.x) * E.out(k), py = Ls.y + (ground - Ls.y) * e - 24 * Math.sin(Math.PI * k);
      place({ x: px, y: py }); look(prev);
    });
    await tween(220, (k) => { at(pl, Lx + dir * 14 * E.out(k), ground, ` rotate(${(dir < 0 ? 180 : 0)}deg) scale(1,${(1 - 0.12 * Math.sin(Math.PI * k)).toFixed(2)})`, 1); });   // 落地滑一下
    pl._x = Lx + dir * 14;
    const face = pl._x < g.cx + x ? -1 : 1;
    x = await runTo(g, x, pl._x - g.cx - face * g.s * 0.42);
    show(PART.crouch);
    cue('嗅嗅…是紙做的！');
    for (let i = 0; i < 3; i++) {                                // 聞三下：往前探、縮回
      await tween(300, (k) => { const c = Math.sin(Math.PI * k); pose(x + face * 4 * c, 0, { sk: -face * 6 * c, sy: 1 - 0.05 * c, sx: 1 + 0.03 * c }); });
      if (i === 0) floatText('嗅嗅', pl._x, ground - 20);
    }
    await tween(260, (k) => { pl.style.opacity = (1 - k).toFixed(2); });
    await goHome(g, x);
  }

  /* ---------- 落葉／花瓣：5～8 片從上面飄下來（左右晃、翻轉），比比原地彈跳去撲，撲到的閃一下收掉，沒撲到的落地淡掉 ---------- */
  async function leafScript(g) {
    const dir = g.dir, n = 5 + Math.floor(Math.random() * 4), lw = g.mob ? 16 : 20, t0 = performance.now();
    const cols = ['#ffb067', '#f7d154', '#ffb3c9', '#ff8a65'];
    const top = Math.max(topLim() + 14, g.top - (g.mob ? 150 : 210)), ground = g.foot - 4, v = g.mob ? 62 : 72;
    const reach = g.mob ? 34 : 50, LH = g.mob ? 30 : 40, catchY = g.top - LH * 0.55;   // 撲到最高點時頭頂的高度
    const Lf = [];
    for (let i = 0; i < n; i++) {
      const x0 = clamp(g.cx + dir * (-12 + Math.random() * (g.mob ? 110 : 160)), lw + 6, g.vw - lw - 6);
      Lf.push({ el: toy('leaf', lw, lw, TOY.leaf(cols[i % cols.length])), x0, y0: top - Math.random() * 30, born: 200 + i * 430, ph: Math.random() * 6, st: 'fall', tEnd: 0 });
    }
    const pos = (L, t) => {
      const a = (t - L.born) / 1000, y = Math.min(ground, L.y0 + v * a);
      return { x: L.x0 + 16 * Math.sin(a * 3.1 + L.ph), y, rot: 40 * Math.sin(a * 2.3 + L.ph) + a * 90, landed: y >= ground };
    };
    Lf.forEach((L) => at(L.el, L.x0, L.y0, '', 0));
    const stop = loopBg(() => {
      const t = performance.now() - t0;
      Lf.forEach((L) => {
        if (L.st === 'caught' || t < L.born) return;
        const p = pos(L, t);
        if (p.landed && L.st === 'fall') { L.st = 'ground'; L.tEnd = t; }
        const op = L.st === 'ground' ? clamp(1 - (t - L.tEnd - 500) / 500, 0, 1) : clamp((t - L.born) / 200, 0, 1);
        at(L.el, p.x, p.y, ` rotate(${p.rot.toFixed(1)}deg) scaleX(${Math.cos((t - L.born) / 330 + L.ph).toFixed(2)})`, op);
      });
    });
    pose(0, -4, { sy: 0.98 });                                   // 0.2 秒內就在動：抬頭準備
    cue('葉子飄下來了～');
    let x = 0, busyTill = 0;
    const tc = (L) => L.born + (catchY - L.y0) / v * 1000;      // 葉子落到頭頂高度的時間
    const order = Lf.slice().sort((a, b) => tc(a) - tc(b));
    const LEAP = 480;
    for (const L of order) {
      const at_ = tc(L), startAt = at_ - LEAP / 2, now = performance.now() - t0;
      if (startAt < now || startAt < busyTill) continue;         // 來不及／前一下還沒落地：讓它落地
      await tween(startAt - now, (k, t) => { const c = Math.max(0, Math.sin((now + t) / 120)); pose(x, 0, { sx: 1 + 0.04 * c, sy: 1 - 0.05 * c }); });   // 等的時候原地小蹦
      const p = pos(L, at_), tx = clamp(p.x - g.cx, -reach * 1.6, reach * 1.6);   // 原地彈跳：最多往旁邊挪一小步（bx 再夾在視窗內）
      x = await leap(g, x, tx, LH, LEAP, () => {
        L.st = 'caught'; L.el.style.opacity = '0';
        const q = pos(L, performance.now() - t0);
        burstAt('star', q.x, q.y, 3, 2);
      });
      busyTill = performance.now() - t0;
    }
    const last = Math.max(...Lf.map((L) => L.born + (ground - L.y0) / v * 1000)) + 1000, now = performance.now() - t0;
    if (last > now) await tween(last - now, (k, t) => { const c = Math.max(0, Math.sin(t / 140)); pose(x, 0, { sx: 1 + 0.03 * c, sy: 1 - 0.04 * c }); });
    stop();
    await goHome(g, x);
  }
  const CHOREO = { snack: snackScript, bubble: bubbleScript, feather: featherScript, yarn: yarnScript, plane: planeScript, leaf: leafScript, ball: ballScript, grass: grassScript, pet: petScript, spin: spinScript, popcorn: popcornScript, hit: hitScript };

  /* ---------- 待機小動作：眨眼／伸懶腰／跳一下（只動 transform）----------
     10-12 起預設不自動跑：待機本身就是一直跳的 GIF，再疊小動作會亂；「東張西望」會換圖（tilt），違反「待機一律 idle_hop」，拿掉。
     只留給 Bibi.test({ fidget: true }) 驗收用。 */
  const FIDGET = {
    blink: async () => { for (let i = 0; i < 2; i++) await tween(240, (k) => { const c = Math.sin(Math.PI * k); pose(0, 0, { sy: 1 - 0.07 * c, sx: 1 + 0.03 * c }); }); },
    stretch: async () => {                       // 天竺鼠伸懶腰＝身體往前後拉長、壓低（四隻腳著地，不站起來）
      await tween(320, (k) => pose(0, 0, { sx: 1 + 0.03 * E.out(k), sy: 1 - 0.03 * E.out(k) }));
      await tween(520, (k) => { const e = E.out(k); pose(0, 0, { sx: 1.03 + 0.09 * e, sy: 0.97 - 0.05 * e, sk: -3 * e }); });
      await wait(320);
      await tween(420, (k) => { const d = E.damp(k, 2.5); pose(0, 0, { sx: 1 + 0.12 * d, sy: 1 - 0.08 * d, sk: -3 * (1 - k) }); });
    },
    hop: async (g) => {
      const J = g.mob ? 14 : 18;
      await tween(150, (k) => pose(0, 0, { sx: 1 + 0.08 * k, sy: 1 - 0.12 * k }));
      await tween(230, (k) => pose(0, -J * E.out(k), { sx: 1.08 - 0.1 * k, sy: 0.88 + 0.14 * k }));   // 彈跳時只微微拉長（≤1.02），不站起來
      await tween(210, (k) => pose(0, -J * (1 - E.in(k)), { sx: 0.98 + 0.02 * k, sy: 1.02 }));
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
    run = null; tipFollow = false; setTimeout(hopSched, 0);
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
    startRun(a.id, true); tipFollow = true; run.line = line; watchOn(); run.tipSide = ['pet', 'popcorn', 'hit', 'spin', 'leaf'].indexOf(a.id) >= 0;   // 摸摸頭（手在頭上）、爆米花跳（跳很高）：泡泡放旁邊，不擋到
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
    document.addEventListener('visibilitychange', () => { if (document.hidden) stopRun('hidden'); else hopSched(); });
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
    MAP: { ACTS, MS, IDLE: IDLE_HOP, STILL: IDLE_STILL },
    state: () => ({ file: fab && fab.dataset.bibi || shown, shown, want, mode, idle: idleNow && idleNow.key, say: idleNow && idleNow.say, sleeping, ring: ringOpen(),
      run: run ? run.id : '', phase: run && run.phase || '', happy: shown === IDLE_HOP, off: { x: OFF.x, y: OFF.y }, body: bodyEl ? bodyEl.style.transform : '', stop: lastStop, props: stage ? stage.children.length : 0,
      src: imgs[front] ? (imgs[front].getAttribute('src') || '').replace(/[?#].*$/, '') : '',
      tip: tip && !tip.hidden && tip.classList.contains('on') ? tip.textContent : '' }),
    test: (o) => { o = o || {}; if ('now' in o) T.now = o.now; if ('pct' in o) T.pct = o.pct; if ('hol' in o) T.hol = o.hol;
      if ('fidget' in o) { noFidget = !o.fidget; if (noFidget) { clearTimeout(fidgetT); stopFidget(); } else schedFidget(); } applyIdle(); return idleNow; },
    fidget: (k) => doFidget(k), stop: (why) => stopRun(why || 'api'), PART, BASE: IDLE_HOP,
    reset: () => { T.now = null; T.pct = undefined; T.hol = null; applyIdle(); },
    idle: () => idle(), open: openRing, close: closeRing, act,
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
