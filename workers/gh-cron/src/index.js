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

// 2026-11-09：daily.yml 的 concurrency 群組（tw-rotation-data-write）只留 1 個 pending，新排進來的會把原本 pending 的 price／full 擠掉。
// 所以派 inst 之前先查 daily.yml 有沒有排隊中或執行中的 run；有就這次不派（10 分鐘後下一個 inst 再看）。
// 查詢失敗一律放行（照常派），不讓 GitHub API 的小狀況變成整天不抓法人。超過 STALE_MS 的 run 視為卡死，不算。
export const GUARD_STATUSES = ['queued', 'pending', 'waiting', 'in_progress'];
export const STALE_MS = 2 * 3600 * 1000;
export async function busyDailyRuns(env, now, fetchImpl = fetch) {
  const repo = env.GH_REPO || 'MiaoZiKe/tw-rotation';
  const found = [];
  for (const st of GUARD_STATUSES) {
    const res = await fetchImpl(`https://api.github.com/repos/${repo}/actions/workflows/daily.yml/runs?status=${st}&per_page=30`, {
      headers: {
        Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'tw-gh-cron-worker',
      },
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
    const j = await res.json();
    for (const r of (j && j.workflow_runs) || []) {
      const t = Date.parse(r.created_at || '');
      if (Number.isFinite(t) && now - t > STALE_MS) continue;
      found.push({ id: r.id, status: st, title: r.display_title || r.name || '' });
    }
  }
  // 2026-11-10：只有 collect（寫資料湖、佔 concurrency 群組）還沒做完的 run 才算忙；
  // collect 已結束、只剩 deploy 在 pages 群組排隊的 run 不佔寫入群組，不該擋 inst（11-10 事故：擋了 43 分鐘）。
  const busy = [];
  for (const f of found) {
    const res = await fetchImpl(`https://api.github.com/repos/${repo}/actions/runs/${f.id}/jobs?per_page=30`, {
      headers: {
        Authorization: `Bearer ${env.GH_DISPATCH_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'tw-gh-cron-worker',
      },
    });
    if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
    const jj = await res.json();
    const collect = ((jj && jj.jobs) || []).find((x) => x.name === 'collect');
    if (collect && collect.status === 'completed') continue;
    busy.push(f);
  }
  return busy;
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
      if (job.workflow === 'daily.yml' && job.inputs && job.inputs.phase === 'inst') {
        let busy = [];
        try { busy = await busyDailyRuns(env, scheduledTime, fetchImpl); }
        catch (e) { log.error('查 daily.yml 排隊狀態失敗，照常派 inst：' + String(e && e.message ? e.message : e)); }
        if (busy.length) {
          log.log('略過 ' + job.label + '：daily.yml 有 ' + busy.map((b) => `${b.status}#${b.id}${b.title}`).join(', ') + '，讓路給排隊中的 price／full，下一輪再派');
          continue;
        }
      }
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
