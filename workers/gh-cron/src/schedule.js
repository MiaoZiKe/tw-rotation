// 排程表與「這一分鐘該派什麼」的純函式（不碰網路、不碰全域時鐘，方便測試）。
// 分工（重要）：Worker 只看「週一到週五＋已知休市表」，不猜颱風假等臨時休市（例如 2026-10-23 颱風全日休市，休市表事先不會有）。
//   臨時休市日 Worker 會照常多派一次，無害：daily.yml 重跑以主鍵 append 去重；social-live 由 social_snap.py 用資料
//   （即時報價成交日、inst_date、盤中時段）自己判斷不是交易日就不發。
// 時間一律台北（UTC+8，沒有日光節約）。
import { HOLIDAYS } from './holidays.js';

const TPE_OFFSET_MS = 8 * 3600 * 1000;

// days：
//   trading  台股交易日（週一到週五，且不在休市日清單）
//   tueSat   台北週二到週六（對應美股週一到週五收盤後的清晨），不看休市日——新聞照常更新
//   all      每天（含週末、休市日）——IG 晚間主題文章用
//   offday   休市日（週末、國定假日；臨時休市 Worker 不知道，由 social_news.py 自己用主貼文狀態判斷）——週末主題文章用
const D = 'daily.yml';
const S = 'social-live.yml';
// ★★ 2026-11-02 降量模式（Andy：「同意降量」；docs/marketing/social_unit/post_quota.json）：
//   自動發文降到每天最多 2 則（只留交易日盤後主貼文 Threads 1 則；第 2 則保留給 Andy 手寫）。
//   拿掉的派工：盤中 12:00（social-live intraday）、週末主題文章 10:15／10:45／19:00／19:40、交易日備案主題文章 20:58／21:08（social_news.yml）、
//   IG 主題文章晚間 19:42／20:32／21:22／21:32／20:04／20:54／21:44／21:54／22:04（ig_post.yml）、22:12 晚間監工（ig_news_watch.yml）。
//   留著的盤前 08:20：只為了把「盤前消息」寫回網站（site/articles/premarket.json），發文那步被開關檔擋下。
//   資料管線（daily.yml）一條都沒動。要放量：改 post_quota.json，並把上面這些派工加回來（git log 找這一筆）。
export const SCHEDULE = [
  // 盤前（wrangler.toml 的 ENABLE_PREMARKET）：降量模式下只更新網站盤前消息，不發文
  { at: '08:20', days: 'trading', workflow: S, inputs: { kind: 'premarket', dry_run: 'false' }, gate: 'premarket' },
  // 盤後資料
  // 2026-10-27 Andy：「拿到資料就要發布了 關盤後 每半小時就要確認一次，資料齊全就發布」→ 收盤後每 30 分鐘抓一次法人＋期貨，
  // 有新資料就重算部署，部署完 social-live 接著判斷盤後貼文齊了沒（齊了就發、發過就跳過）。沒新資料的輪約 1 分鐘收工。
  ...['14:16', '14:46', '15:16'].map((at) => ({ at, days: 'trading', workflow: D, inputs: { phase: 'inst' } })),
  { at: '15:38', days: 'trading', workflow: D, inputs: { phase: 'price' } },
  // 上市個股法人只能等 FinMind（證交所開放平台沒有個股法人明細），實測約 17:00～17:40 陸續上架 → 16:46～17:56 每 10 分鐘抓一次
  ...['16:16', '16:46', '16:56', '17:06', '17:16', '17:26', '17:36', '17:46', '17:56', '18:16'].map((at) => ({ at, days: 'trading', workflow: D, inputs: { phase: 'inst' } })),
  { at: '18:38', days: 'trading', workflow: D, inputs: { phase: 'full' } },
  ...['19:16', '19:46', '20:16', '20:46', '21:16'].map((at) => ({ at, days: 'trading', workflow: D, inputs: { phase: 'inst' } })),
  { at: '21:38', days: 'trading', workflow: D, inputs: { phase: 'full' } },
  // 清晨：新聞、國際盤、總經。GitHub 原本的 05:07 排程（週一到週五）同樣不可靠，所以也由這裡準時派一次。
  { at: '05:07', days: 'tueSat', workflow: D, inputs: { phase: 'news' } },
];

/** 把 UTC 毫秒轉成台北的 {date:'YYYY-MM-DD', hhmm:'HH:MM', dow:0-6(0=週日)} */
export function taipeiParts(ms) {
  const d = new Date(ms + TPE_OFFSET_MS);
  const p = (n) => String(n).padStart(2, '0');
  return {
    date: `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`,
    hhmm: `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`,
    dow: d.getUTCDay(),
  };
}

export function isTradingDay(date, dow, holidays = HOLIDAYS) {
  return dow >= 1 && dow <= 5 && !holidays.has(date);
}

/**
 * 這一分鐘（scheduledTimeMs 所在的那一分鐘）該派的工作清單。
 * opts.enabled：{premarket:boolean}；opts.holidays：Set（測試用）。
 */
export function dueJobs(scheduledTimeMs, opts = {}) {
  const holidays = opts.holidays || HOLIDAYS;
  const enabled = opts.enabled || {};
  const { date, hhmm, dow } = taipeiParts(scheduledTimeMs);
  const trading = isTradingDay(date, dow, holidays);
  return SCHEDULE.filter((j) => {
    if (j.at !== hhmm) return false;
    if (j.gate && !enabled[j.gate]) return false;
    if (j.days === 'trading') return trading;
    if (j.days === 'tueSat') return dow >= 2 && dow <= 6;
    if (j.days === 'offday') return !trading;
    if (j.days === 'all') return true;
    return false;
  }).map((j) => ({ workflow: j.workflow, inputs: { ...j.inputs }, label: `${date} ${hhmm} ${j.workflow} ${JSON.stringify(j.inputs)}` }));
}
