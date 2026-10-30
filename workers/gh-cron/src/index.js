// tw-gh-cron：Cloudflare Cron Trigger 準時呼叫 GitHub workflow_dispatch。
// 只有 scheduled handler；fetch 一律 404（不對外服務）。
import { dueJobs, taipeiParts } from './schedule.js';

// 2026-10-30：quote-proxy 自己的 Cron（每 5 分鐘存當日快照）實測沒有觸發（diag 一直空、KV 沒有 Cron 寫的格子），
// 所以由這支（Cron 已證實每分鐘準時）每 5 分鐘敲一次 /tape?run=1 叫它存一格。同一格重複呼叫會去重，休市日 Worker 用 mis 日期自己擋。
export const TAPE_URL = 'https://tw-quote.kcq01010909.workers.dev/tape?run=1';
// 同帳號的 Worker 不能用 fetch 打另一支 *.workers.dev（Cloudflare 1042），一律走服務綁定 env.QUOTE（wrangler.toml 的 [[services]]）。
export async function tapePing(scheduledTime, env, fetchImpl, log = console) {
  fetchImpl = fetchImpl || ((u, o) => (env && env.QUOTE ? env.QUOTE.fetch(u, o) : fetch(u, o)));
  const { hhmm, dow } = taipeiParts(scheduledTime);
  const m = (+hhmm.slice(0, 2)) * 60 + (+hhmm.slice(3));
  if (dow < 1 || dow > 5 || m < 9 * 60 || m > 13 * 60 + 35 || m % 5 !== 0) return null;
  try {
    const r = await fetchImpl(TAPE_URL, { headers: { 'User-Agent': 'tw-gh-cron-worker' } });
    const t = (await r.text().catch(() => '')).slice(0, 120);
    log.log('tape ' + hhmm + ' HTTP ' + r.status + ' ' + t);
    return r.status;
  } catch (e) { log.error('tape 失敗 ' + String(e && e.message ? e.message : e)); return -1; }
}

export async function dispatch(env, job, fetchImpl = fetch) {
  const repo = env.GH_REPO || 'MiaoZiKe/tw-rotation';
  const url = `https://api.github.com/repos/${repo}/actions/workflows/${job.workflow}/dispatches`;
  const res = await fetchImpl(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'tw-gh-cron-worker',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ref: env.GH_REF || 'main', inputs: job.inputs }),
  });
  if (res.status !== 204) {
    // 只印狀態碼與 GitHub 回的錯誤訊息，絕不印 token
    const body = (await res.text().catch(() => '')).slice(0, 300);
    throw new Error(`HTTP ${res.status} ${body}`);
  }
}

export async function runScheduled(scheduledTime, env, fetchImpl = fetch, log = console) {
  const jobs = dueJobs(scheduledTime, { enabled: { premarket: env.ENABLE_PREMARKET === '1' } });
  if (!jobs.length) return [];
  if (!env.GH_DISPATCH_TOKEN) {
    log.error('GH_DISPATCH_TOKEN 未設定，無法派工：' + jobs.map((j) => j.label).join('; '));
    return [];
  }
  const done = [];
  for (const job of jobs) {
    try {
      await dispatch(env, job, fetchImpl);
      log.log('已派工 ' + job.label);
      done.push(job.label);
    } catch (e) {
      log.error('派工失敗 ' + job.label + '：' + String(e && e.message ? e.message : e).replace(env.GH_DISPATCH_TOKEN, '***'));
    }
  }
  return done;
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runScheduled(event.scheduledTime, env));
    ctx.waitUntil(tapePing(event.scheduledTime, env));
  },
  async fetch() {
    return new Response('Not Found', { status: 404 });
  },
};
