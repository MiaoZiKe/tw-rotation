/* ============================================================================
   把一篇「已公開的精選文章」組成交給 GPT 的交接 Issue（管理區 #admin/articles 已上架文章的「傳給 GPT」用）—— 2026-10-16 建
   ----------------------------------------------------------------------------
   Andy 2026-10-16：「精選貼文產出後，我可以選擇我要的貼文，整理給 GPT」「不是做完就發送，要有個功能鈕，我可以選擇文章，
   將內容傳到 GPT 那邊，文章是我決定」。所以「按鈕」本身就是 Andy 的決定動作：不排隊、不經 Claude 排程、不碰 Worker，
   純前端把文章 JSON 組成 Markdown，開一則預先填好的 GitHub 新 Issue（repo MiaoZiKe/tw-rotation，label social-handoff，一篇一則）；
   Andy 在 GitHub 按 Submit new issue 才算送出。
   ⚠ repo 是 public：只放「文章已經公開的內容」（標題、摘要、三句話重點、數字卡、來源、站內連結），不放任何管理資料、會員資料、點閱數。
   兩種交接（Andy 10-16：「傳給 GPT 按鈕要分成製作影片或是 IG 文章」）：type＝'ig'（IG 貼文：十頁輪播＋說明＋Threads）、'video'（影片：腳本＋分鏡＋封面＋字幕＋Reels／Threads 文案）。
   Issue 標題帶類型、label 多一個（gpt-ig-post／gpt-video）、「請產出」不同，其餘內容相同；兩種各自記「已傳送」。
   網址預填有長度上限（瀏覽器與 GitHub 約 8 KB 內最安全）：全部放得下就全放；放不下就依序拿掉「站內連結 → 關鍵數據 → 來源（縮成前 3 筆）→ 來源」，
   並在 Issue 裡寫「完整內容請看下面的完整文章 JSON 連結」；另外提供「複製完整交接內容」給人貼進 Issue 的文字框。
   只有純函式（build）與「已傳送」紀錄（localStorage，每次讀寫 try/catch）；畫面在 articles.js。
   驗收：scripts/_uitest.py「文章主題兩分頁1016」（解析連結驗 title／labels／body 各項）。
   ============================================================================ */
(function () {
  'use strict';
  const REPO = 'MiaoZiKe/tw-rotation';
  const SITE = 'https://miaozike.github.io/tw-rotation/';
  const RAW = 'https://raw.githubusercontent.com/' + REPO + '/main/site/articles/posts/';
  const STYLE = 'https://github.com/' + REPO + '/blob/main/docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md';
  const MAX_URL = 8000;
  const LS_SENT = 'tw.art.gptsent2';   // 鍵＝<文章 id>|<ig 或 video>
  const TYPES = { ig: { name: 'IG 貼文', label: 'gpt-ig-post' }, video: { name: '影片', label: 'gpt-video' } };
  const LAYOUT = 'https://github.com/' + REPO + '/blob/main/docs/marketing/video_1010/layout_rules.md';
  const CATN = { news: '比比快訊', intro: '比比產業鏈', know: '比比知識' };
  const s1 = (x) => String(x == null ? '' : x).replace(/\r?\n/g, ' ').trim();
  const cell = (x) => s1(x).replace(/\|/g, '／');                 // 表格欄裡不能有直線
  const tpeDay = () => new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10);

  /* 「三句話重點」：blocks 裡標題是「三句話重點」的後面第一個 ul */
  function threePoints(post) {
    const bs = Array.isArray(post.blocks) ? post.blocks : [];
    const i = bs.findIndex((b) => b && b.t === 'h' && /三句話重點/.test(String(b.text || '')));
    if (i < 0) return [];
    for (let k = i + 1; k < bs.length; k++) {
      if (bs[k] && bs[k].t === 'ul') return (bs[k].items || []).map(s1).filter(Boolean).slice(0, 3);
      if (bs[k] && bs[k].t === 'h') break;
    }
    return [];
  }
  function kpiRows(post) {
    const out = [];
    (post.blocks || []).forEach((b) => { if (b && b.t === 'kpi') (b.items || []).forEach((x) => { if (x && x.label) out.push(x); }); });
    return out;
  }
  const httpsOnly = (u) => (/^https:\/\/[^\s<>"']{4,500}$/.test(String(u || '')) ? String(u) : '');

  /* 每一段都是 {k, md}；k 決定放不下時先拿掉誰 */
  function ask(type) {
    if (type === 'video') return `## 請產出（影片）\n- [ ] 短影片腳本（直式 1080×1920、建議 30～60 秒）\n- [ ] 逐鏡分鏡表（秒數／畫面／字卡大小字／比比動作表情道具／轉場／音效）\n- [ ] 封面圖\n- [ ] 字幕稿\n- [ ] IG Reels 與 Threads 文案\n- [ ] 來源表\n- [ ] 素材來源清單（每張素材標作者與來源類別）\n\n備註：\n- 比比造型以 \`docs/anim/bibi_library/reference/parts_sheet_1011.webp\` 為準\n- 畫面元素不可重疊（規則：${LAYOUT}）\n- 最終影片如何渲染由 Andy 決定`;
    return `## 請產出（IG 貼文）\n- [ ] IG 輪播十頁（1080×1350）\n- [ ] IG 貼文說明\n- [ ] Threads 文案\n- [ ] 來源表\n- [ ] 素材來源清單（每張素材標作者與來源類別）`;
  }
  function sections(post, srcLimit, type) {
    const id = String(post.id), pts = threePoints(post), kp = kpiRows(post), src = (post.sources || []).filter((x) => x && x.title);
    const S = [];
    S.push({ k: 'must', md: `## 母文章\n- 文章 id：\`${id}\`\n- 網址：${SITE}#article/${encodeURIComponent(id)}\n- 類別：${CATN[post.cat] || s1(post.cat)}　日期：${s1(post.date)}${post.updated ? `（更新 ${s1(post.updated)}）` : ''}` });
    S.push({ k: 'must', md: `## 一句話核心觀點\n${s1(post.summary) || s1(post.title)}` });
    S.push({ k: 'must', md: `## 三句話重點\n${pts.length ? pts.map((p, i) => `${i + 1}. ${p}`).join('\n') : '（文章沒有「三句話重點」區塊，請依完整文章 JSON 自行整理）'}` });
    if (kp.length) S.push({ k: 'kpi', md: `## 關鍵數據\n| 項目 | 數值 | 單位 | 變動 | 說明 |\n|---|---|---|---|---|\n${kp.map((x) => `| ${cell(x.label)} | ${cell(x.value)} | ${cell(x.unit)} | ${cell(x.delta)} | ${cell(x.note)} |`).join('\n')}` });
    if (src.length) {
      const list = (srcLimit ? src.slice(0, srcLimit) : src).map((x, i) => `${i + 1}. ${cell(x.title)}｜${cell(x.publisher)}｜${cell(x.date) || '（未標日期）'}｜${httpsOnly(x.url) || '（無連結）'}`);
      S.push({ k: srcLimit ? 'src3' : 'src', md: `## 來源（共 ${src.length} 筆${srcLimit && src.length > srcLimit ? `，這裡只列前 ${srcLimit} 筆，其餘見完整文章 JSON` : ''}）\n${list.join('\n')}` });
    }
    const sl = (post.site_links || []).filter((x) => x && x.label && /^#[\w/.-]{1,80}$/.test(String(x.hash || '')));
    if (sl.length) S.push({ k: 'links', md: `## 站內連結\n${sl.map((x) => `- ${cell(x.label)}：${SITE}${x.hash}`).join('\n')}` });
    S.push({ k: 'must', md: `## 內容限制\n- 不點名個股推薦、不寫買賣建議、不保證獲利\n- 預估與財測不寫成事實，要標明「財測」「預估」\n- 新聞用自己的話寫並附來源\n- 結尾附免責：整理公開資訊，非投顧，投資請自行判斷。` });
    S.push({ k: 'must', md: `## 視覺規範\n${STYLE}` });
    S.push({ k: 'must', md: ask(type) });
    S.push({ k: 'must', md: `## 完整文章 JSON\n${RAW}${encodeURIComponent(id)}.json` });
    return S;
  }
  const mkUrl = (title, body, type) => 'https://github.com/' + REPO + '/issues/new?title=' + encodeURIComponent(title) + '&body=' + encodeURIComponent(body) + '&labels=' + encodeURIComponent('social-handoff,' + TYPES[type].label);
  const join = (S) => S.map((x) => x.md).join('\n\n');

  /* build(post) → { title, body（網址裡的）, full（完整內容，給「複製」）, url, trimmed:[被拿掉的段落名], len }
     放不下 8 KB 時逐級省略：0 全放 → 1 拿掉站內連結 → 2 再拿掉關鍵數據 → 3 來源縮成前 3 筆 → 4 連來源也拿掉（必要項一定留：母文章、核心觀點、三句話、限制、規範、請產出、JSON 連結） */
  function level(post, lv, type) {
    let S = sections(post, lv === 3 ? 3 : 0, type);
    if (lv >= 1) S = S.filter((x) => x.k !== 'links');
    if (lv >= 2) S = S.filter((x) => x.k !== 'kpi');
    if (lv >= 4) S = S.filter((x) => x.k !== 'src' && x.k !== 'src3');
    return S;
  }
  const LVN = ['', '站內連結', '關鍵數據', '來源（只列前 3 筆）', '來源'];
  function build(post, type) {
    type = TYPES[type] ? type : 'ig';
    const title = '[社群交接] ' + tpeDay() + '｜' + TYPES[type].name + '｜' + s1(post.title);
    const full = join(level(post, 0, type));
    let lv = 0, body = full, url = mkUrl(title, body, type); const trimmed = [];
    while (url.length > MAX_URL && lv < 4) {
      lv++;
      trimmed.push(LVN[lv]);
      body = join(level(post, lv, type)) + '\n\n> 這則 Issue 的網址有長度上限，部分段落被省略（' + trimmed.join('、') + '）；完整內容請看上面「完整文章 JSON」連結。';
      url = mkUrl(title, body, type);
    }
    return { title, body, full, url, trimmed, len: url.length, type, labels: ['social-handoff', TYPES[type].label] };
  }

  /* 已傳送紀錄：{文章 id: 毫秒時間} */
  function sentAll() { try { const o = JSON.parse(localStorage.getItem(LS_SENT) || '{}'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } }
  function markSent(id, type) { try { const o = sentAll(); o[id + '|' + type] = Date.now(); localStorage.setItem(LS_SENT, JSON.stringify(o)); } catch (e) { /* 私密視窗：只在這次有效 */ } }
  const sentText = (id, type) => { const t = Number(sentAll()[id + '|' + type]); if (!Number.isFinite(t) || t <= 0) return ''; return new Date(t + 8 * 3600e3).toISOString().slice(5, 16).replace('T', ' '); };

  window.TwGptHandoff = { build, markSent, sentText, sentAll, threePoints, TYPES };
})();
