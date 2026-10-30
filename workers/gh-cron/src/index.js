// tw-gh-cron：Cloudflare Cron Trigger 準時呼叫 GitHub workflow_dispatch。
// 只有 scheduled handler；fetch 一律 404（不對外服務）。
import { dueJobs } from './schedule.js';

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
  },
  async fetch() {
    return new Response('Not Found', { status: 404 });
  },
};
