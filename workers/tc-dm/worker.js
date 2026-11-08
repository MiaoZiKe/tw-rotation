// 頻道②「科技透明圈」IG 私訊 Worker（webhook 即時版）。2026-11-08 Andy：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。
//
// ★ 兩段式（Meta 規定）：User Profile API 的 is_user_follow_business 要等「對方先傳訊息、建立同意」之後才查得到，
//   只留言的人查了會回「User consent is required」。所以：
//   第 1 段 comments webhook：留言含關鍵字 → Private Reply（recipient.comment_id）私訊「追蹤 @帳號 後回覆『好了』」。
//          每則留言只能私回 1 次、期限 7 天。
//   第 2 段 messages webhook：對方回「好了」（同意成立、24 小時回覆窗）→ GET /{IGSID}?fields=is_user_follow_business
//          true → 送整理；false → 「還沒看到你追蹤喔」（每人每天最多 3 次）。
// 安全：POST 一律驗 X-Hub-Signature-256（HMAC-SHA256，IG_APP_SECRET）；不符回 403。先回 200，處理放 ctx.waitUntil。
// 去重：KV 以 comment_id 雜湊去重（Meta 會重送）；每人每天 per_user_per_day 次；每分鐘 max_per_minute 則。
// 隱私：KV 只存 SHA-256 雜湊、時間與結果；不存留言內容、帳號名稱、私訊內容。紀錄 log:* 保留 30 天。
// follow_gate（2026-11-09 法遵審後加，預設 true）：false＝不查追蹤，留言後直接私回 prompt_no_gate＋重點內容（同一則；
//   Meta 每則留言只准私回 1 則），追蹤只當鼓勵。true＝上面的兩段式（Andy 指示；追蹤門檻屬未確認風險）。
// 閘門：dm_config.json 的 ig_dm.mode 不是 "webhook"，或 legal_reviewed 不是 true → 只記錄不送。

const DAY = 86400;
const NF_MAX = 3;

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (url.pathname !== "/ig-webhook") return new Response("not found", { status: 404 });
    if (req.method === "GET") {
      const q = url.searchParams;
      if (q.get("hub.mode") === "subscribe" && env.VERIFY_TOKEN && q.get("hub.verify_token") === env.VERIFY_TOKEN)
        return new Response(q.get("hub.challenge") || "", { status: 200 });
      return new Response("forbidden", { status: 403 });
    }
    if (req.method !== "POST") return new Response("method not allowed", { status: 405 });
    const raw = await req.text();
    if (!(await verifySig(raw, req.headers.get("x-hub-signature-256") || "", env.IG_APP_SECRET || "")))
      return new Response("bad signature", { status: 403 });
    let body;
    try { body = JSON.parse(raw); } catch { return new Response("bad json", { status: 400 }); }
    ctx.waitUntil(handle(body, env).catch((e) => console.log("處理失敗", String(e).slice(0, 200))));
    return new Response("EVENT_RECEIVED", { status: 200 });
  },
};

export async function verifySig(raw, header, secret) {
  if (!secret || !header.startsWith("sha256=")) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(raw)));
  const hex = [...mac].map((b) => b.toString(16).padStart(2, "0")).join("");
  const got = header.slice(7);
  if (got.length !== hex.length) return false;
  let diff = 0;
  for (let i = 0; i < hex.length; i++) diff |= hex.charCodeAt(i) ^ got.charCodeAt(i);
  return diff === 0;
}

export async function sha(s) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(s))));
  return [...d].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

const contentOf = (d, post) => ((d.contents || {})[post]) || ((d.contents || {}).default) || "";
export const norm = (s) => String(s || "").normalize("NFKC").toLowerCase().replace(/\s+/g, "");
export const hasKw = (t, kws) => (kws || []).some((k) => norm(k) && norm(t).includes(norm(k)));
const today = (now) => new Date(now + 8 * 3600e3).toISOString().slice(0, 10); // 台北日期

async function cachedJson(env, key, url, fallback) {
  const c = await env.KV.get("cache:" + key, "json");
  if (c) return c;
  try {
    const r = await fetch(url, { cf: { cacheTtl: 300 } });
    if (r.ok) {
      const j = await r.json();
      await env.KV.put("cache:" + key, JSON.stringify(j), { expirationTtl: 300 });
      return j;
    }
  } catch {}
  return fallback;
}

async function graph(env, method, path, params) {
  const u = new URL(env.GRAPH + path);
  const init = { method, headers: { Authorization: "Bearer " + env.IG_TOKEN } };
  if (method === "GET") for (const [k, v] of Object.entries(params || {})) u.searchParams.set(k, v);
  else { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(params || {}); }
  const r = await fetch(u.toString(), init);
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(`HTTP ${r.status} ${(j.error && j.error.message) || ""}`.trim());
  return j;
}

async function logEvent(env, now, type, result) {
  await env.KV.put(`log:${now}:${Math.random().toString(36).slice(2, 8)}`, JSON.stringify({ type, result }), { expirationTtl: 30 * DAY });
}

async function rateOk(env, now, max) {
  const k = "rl:" + Math.floor(now / 60000);
  const n = Number((await env.KV.get(k)) || 0);
  if (n >= max) return false;
  await env.KV.put(k, String(n + 1), { expirationTtl: 120 });
  return true;
}

export async function handle(body, env, now = Date.now()) {
  const cfg = await cachedJson(env, "config", env.CONFIG_URL, null);
  if (!cfg || !cfg.ig_dm || !cfg.ig_dm.enabled) return { skipped: "設定讀不到或關閉" };
  const d = cfg.ig_dm;
  const live = d.mode === "webhook" && cfg.legal_reviewed === true && !!env.IG_TOKEN;
  const out = [];
  for (const entry of body.entry || []) {
    const own = String(entry.id || "");
    for (const ch of entry.changes || []) if (ch.field === "comments") out.push(await onComment(ch.value || {}, own, cfg, env, now, live));
    for (const m of entry.messaging || []) if (m.message && !m.message.is_echo) out.push(await onMessage(m, own, cfg, env, now, live));
  }
  return { live, out };
}

async function handleName(env, cfg) {
  if (cfg.ig_handle) return cfg.ig_handle;
  const c = await env.KV.get("cache:handle");
  if (c) return c;
  try {
    const me = await graph(env, "GET", "/me", { fields: "username" });
    if (me.username) { await env.KV.put("cache:handle", me.username, { expirationTtl: DAY }); return me.username; }
  } catch {}
  return "科技透明圈";
}

async function onComment(v, own, cfg, env, now, live) {
  const d = cfg.ig_dm, who = String((v.from || {}).id || ""), cid = String(v.id || "");
  if (!cid || !who || who === own || !hasKw(v.text, cfg.keywords)) return "略過";
  const ck = "c:" + (await sha(cid)), uh = await sha(who), dayKey = `u:${uh}:${today(now)}`;
  if (await env.KV.get(ck)) return "重複";
  if (Number((await env.KV.get(dayKey)) || 0) >= Number(d.per_user_per_day || 1)) return "今天已私訊過";
  if (!live) { await logEvent(env, now, "comment", "dry"); return "只記錄"; }
  if (!(await rateOk(env, now, Number(d.max_per_minute || 10)))) { await logEvent(env, now, "comment", "rate-limited"); return "速率上限"; }
  const handle = await handleName(env, cfg);
  const posted = await cachedJson(env, "posted", env.POSTED_URL, { posts: [] });
  const mid = String((v.media || {}).id || "");
  const post = ((posted.posts || []).find((p) => String(p.ids_ig || p.ig_id || "") === mid) || {}).id || "default";
  const gate = d.follow_gate !== false;
  const text = gate ? String(d.prompt || "").replaceAll("{handle}", handle)
    : String(d.prompt_no_gate || "").replaceAll("{handle}", handle) + "\n\n" + contentOf(d, post);
  try {
    await graph(env, "POST", "/me/messages", { recipient: { comment_id: cid }, message: { text } });
  } catch (e) { await logEvent(env, now, "comment", "send-failed"); return "失敗：" + String(e).slice(0, 100); }
  await env.KV.put(ck, "1", { expirationTtl: 8 * DAY });
  await env.KV.put(dayKey, String(Number((await env.KV.get(dayKey)) || 0) + 1), { expirationTtl: 2 * DAY });
  await env.KV.put("p:" + uh, JSON.stringify({ post, sent: !gate, nf: {} }), { expirationTtl: 7 * DAY });
  await logEvent(env, now, "comment", "prompted");
  return "已私回";
}

async function onMessage(m, own, cfg, env, now, live) {
  const d = cfg.ig_dm, who = String((m.sender || {}).id || "");
  if (!who || who === own || !hasKw(m.message.text, d.followed_keywords)) return "略過";
  const uh = await sha(who), pk = "p:" + uh;
  const p = await env.KV.get(pk, "json");
  if (!p) return "不是從留言來的，略過";
  const mk = "m:" + (await sha(m.message.mid || `${who}:${m.timestamp}`));
  if (await env.KV.get(mk)) return "重複";
  if (!live) { await logEvent(env, now, "message", "dry"); return "只記錄"; }
  if (!(await rateOk(env, now, Number(d.max_per_minute || 10)))) return "速率上限";
  await env.KV.put(mk, "1", { expirationTtl: 2 * DAY });
  const handle = await handleName(env, cfg);
  const send = (text) => graph(env, "POST", "/me/messages", { recipient: { id: who }, message: { text } });
  try {
    if (p.sent) { await send(d.already_sent || ""); return "已送過"; }
    const prof = await graph(env, "GET", "/" + who, { fields: "is_user_follow_business" });
    if (prof.is_user_follow_business === true) {
      await send(contentOf(d, p.post));
      p.sent = true;
      await env.KV.put(pk, JSON.stringify(p), { expirationTtl: 30 * DAY });
      await logEvent(env, now, "message", "delivered");
      return "已送整理";
    }
    const t = today(now);
    if (Number((p.nf || {})[t] || 0) >= NF_MAX) return "提醒次數到上限";
    await send(String(d.not_following || "").replaceAll("{handle}", handle));
    p.nf = { [t]: Number((p.nf || {})[t] || 0) + 1 };
    await env.KV.put(pk, JSON.stringify(p), { expirationTtl: 7 * DAY });
    await logEvent(env, now, "message", "not-following");
    return "提醒追蹤";
  } catch (e) {
    await env.KV.delete(mk);
    await logEvent(env, now, "message", "send-failed");
    return "失敗：" + String(e).slice(0, 100);
  }
}
