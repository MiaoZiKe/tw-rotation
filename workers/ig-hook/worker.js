// IG 留言 Webhook ＋「追蹤閘門」Worker（四個帳號共用一支）。2026-11-20 Andy：要「留言觸發自動私訊＋確認追蹤＋追蹤後再給連結」，
// 不要一直靠定時檢查（定時版 scripts/healing_comments.py／channel_comments 保留當備援）。
//
// 流程（ManyChat 式）：
//  1. Meta Instagram Webhook 的 comments 欄位 → POST /ig-hook。先驗 X-Hub-Signature-256（App Secret），不符回 403。
//     GET /ig-hook 處理 hub.challenge 驗證（VERIFY_TOKEN）。先回 200，真正處理放 ctx.waitUntil。
//  2. 留言含該帳號 dm_config.json ig_hook.keywords → Private Reply（recipient.comment_id，每則留言 Meta 只准 1 次）
//     內容「追蹤後按下面按鈕拿完整資訊」＋一顆 postback 按鈕；成功後同時公開回覆「已經將『主題』完整資訊給你囉～」。
//  3. 讀者按按鈕 → messaging_postbacks webhook → GET /{IGSID}?fields=is_user_follow_business：
//     true → 私訊送連結；false → 回「還沒看到你的追蹤，追蹤後再按一次」並再附一顆按鈕。
//     （Meta 沒有「新追蹤者」事件，所以一定要讀者自己按按鈕。）
//  4. 每個事件寫紀錄（KV log:*）：只存帳號代碼、事件類型、結果、是否追蹤、留言 id 的雜湊與時間；
//     不存帳號名稱、使用者編號原文、留言全文（跟隱私權政策一致，commit 45ff9eba2）。保留 30 天。
//  5. 去重：KV 以「留言 id SHA-256 前 16 碼」（跟 scripts/healing_comments.py 的 h() 同一個算法）。
//     GET /handled（Bearer SYNC_TOKEN）讓定時檢查查「哪些留言已經由 webhook 處理」，兩邊不重複回。
// 閘門：dm_config.json ig_hook.mode 是 "live" 才真的送；其他（預設 "dry"）只記錄、不對任何人發訊息。
// 帳號：env.ACCOUNTS（wrangler.toml 的 JSON）列出每個帳號的 config_url 與權杖機密名稱；權杖不是 IGAA 開頭或沒設 → 該帳號略過（走備援）。

const DAY = 86400;
const NF_MAX = 5;      // 同一人同一天「還沒追蹤」提醒上限
const MAX_TRIES = 3;   // 私訊失敗最多重試次數（Meta 重送 webhook 時）

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    if (url.pathname === "/handled" || url.pathname === "/log") return admin(url, req, env);
    if (url.pathname !== "/ig-hook") return new Response("not found", { status: 404 });
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

// ---------- 小工具 ----------
export async function verifySig(raw, header, secret) {
  if (!secret || !header.startsWith("sha256=")) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(raw)));
  return safeEq([...mac].map((b) => b.toString(16).padStart(2, "0")).join(""), header.slice(7));
}

function safeEq(a, b) {
  a = String(a); b = String(b);
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// 跟 Python 端 scripts/healing_comments.py 的 h() 一致：SHA-256 十六進位前 16 碼
export async function h16(s) {
  const d = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(s))));
  return [...d].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}

export const norm = (s) => String(s || "").normalize("NFKC").toLowerCase().replace(/\s+/g, "");
export const hasKw = (t, kws) => (kws || []).some((k) => norm(k) && norm(t).includes(norm(k)));
const today = (now) => new Date(now + 8 * 3600e3).toISOString().slice(0, 10); // 台北日期
const fill = (s, o) => Object.entries(o).reduce((t, [k, v]) => t.replaceAll("{" + k + "}", v), String(s || ""));

async function cachedJson(env, key, url) {
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
  return null;
}

async function graph(env, token, method, path, params) {
  const u = new URL(env.GRAPH + path);
  const init = { method, headers: { Authorization: "Bearer " + token } };
  if (method === "GET") for (const [k, v] of Object.entries(params || {})) u.searchParams.set(k, v);
  else { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(params || {}); }
  const r = await fetch(u.toString(), init);
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.error) throw new Error(`HTTP ${r.status} ${(j.error && j.error.message) || ""}`.trim());
  return j;
}

async function logEvent(env, now, acct, type, result, extra) {
  await env.KV.put(`log:${now}:${Math.random().toString(36).slice(2, 8)}`,
    JSON.stringify({ at: new Date(now).toISOString(), acct, type, result, ...(extra || {}) }), { expirationTtl: 30 * DAY });
}

async function rateOk(env, now, max) {
  const k = "rl:" + Math.floor(now / 60000);
  const n = Number((await env.KV.get(k)) || 0);
  if (n >= max) return false;
  await env.KV.put(k, String(n + 1), { expirationTtl: 120 });
  return true;
}

// ---------- 帳號解析 ----------
export function accountList(env) {
  try { return JSON.parse(env.ACCOUNTS || "[]"); } catch { return []; }
}

// 以權杖查出這個帳號的 IG 專業帳號編號與帳號名（快取 1 天；只在 KV，不進紀錄）
async function identify(env, acc) {
  const token = env[acc.token_env];
  if (!token || !String(token).startsWith("IGAA")) return null;
  const ck = "acct:" + acc.code;
  let info = await env.KV.get(ck, "json");
  if (!info) {
    const me = await graph(env, token, "GET", "/me", { fields: "user_id,username" });
    info = { ids: [String(me.id || ""), String(me.user_id || "")].filter(Boolean), username: me.username || "" };
    await env.KV.put(ck, JSON.stringify(info), { expirationTtl: DAY });
  }
  return { ...acc, token, ...info };
}

async function findAccount(env, entryId) {
  for (const acc of accountList(env)) {
    let a = null;
    try { a = await identify(env, acc); } catch { a = null; }
    if (a && a.ids.includes(String(entryId))) return a;
  }
  return null;
}

// ---------- 事件處理（可單獨測試）----------
export async function handle(body, env, now = Date.now()) {
  const out = [];
  for (const entry of body.entry || []) {
    const acc = await findAccount(env, entry.id);
    if (!acc) { out.push("找不到對應帳號或權杖非 IGAA，略過"); continue; }
    const cfgAll = await cachedJson(env, "config:" + acc.code, acc.config_url);
    const cfg = cfgAll && cfgAll.ig_hook;
    if (!cfg || !cfg.enabled) { out.push("設定讀不到或關閉"); continue; }
    const live = cfg.mode === "live";
    for (const ch of entry.changes || []) if (ch.field === "comments") out.push(await onComment(ch.value || {}, acc, cfg, env, now, live));
    for (const m of entry.messaging || []) if (m.postback && !(m.message && m.message.is_echo)) out.push(await onPostback(m, acc, cfg, env, now, live));
  }
  return out;
}

function topicOf(cfg, key) {
  const t = (cfg.by_media || {})[key] || {};
  return { topic: t.topic || cfg.topic || "完整資訊", link: t.link || cfg.link || "" };
}

async function onComment(v, acc, cfg, env, now, live) {
  const cid = String(v.id || ""), who = String((v.from || {}).id || "");
  if (!cid || !who || acc.ids.includes(who) || v.parent_id || !hasKw(v.text, cfg.keywords)) return "略過";
  const ch = await h16(cid), ck = `c:${acc.code}:${ch}`;
  const rec = await env.KV.get(ck, "json");
  if (rec && (rec.r === "sent" || rec.tries >= MAX_TRIES)) return "重複";
  const mediaKey = (cfg.by_media || {})[String((v.media || {}).id || "")] ? String(v.media.id) : "default";
  if (!live) { await logEvent(env, now, acc.code, "comment", "dry", { ch }); return "只記錄（dry）"; }
  if (!(await rateOk(env, now, Number(cfg.max_per_minute || 10)))) { await logEvent(env, now, acc.code, "comment", "rate-limited", { ch }); return "速率上限"; }
  const { topic } = topicOf(cfg, mediaKey);
  const vars = { handle: acc.username || cfg.handle || "", topic };
  try {
    await graph(env, acc.token, "POST", "/me/messages", {
      recipient: { comment_id: cid },
      message: { attachment: { type: "template", payload: { template_type: "button",
        text: fill(cfg.dm_text, vars), buttons: [{ type: "postback", title: cfg.button_title || "我已追蹤，給我連結", payload: "fc:" + mediaKey }] } } },
    });
  } catch (e) {
    const msg = String(e);
    const already = /already|2534|2018108/i.test(msg);   // Meta：這則留言已私回過
    await env.KV.put(ck, JSON.stringify({ r: already ? "sent" : "failed", tries: ((rec || {}).tries || 0) + 1, t: now }), { expirationTtl: 8 * DAY });
    await logEvent(env, now, acc.code, "comment", already ? "already-replied" : "send-failed", { ch });
    return already ? "Meta 說已私回過" : "失敗：" + msg.slice(0, 100);
  }
  await env.KV.put(ck, JSON.stringify({ r: "sent", tries: ((rec || {}).tries || 0) + 1, t: now }), { expirationTtl: 8 * DAY });
  let pub = "off";
  if (cfg.public_reply) {
    try { await graph(env, acc.token, "POST", `/${cid}/replies`, { message: fill(cfg.public_reply, vars) }); pub = "ok"; }
    catch { pub = "failed"; }
  }
  await logEvent(env, now, acc.code, "comment", "prompted", { ch, public: pub });
  return "已私回";
}

async function onPostback(m, acc, cfg, env, now, live) {
  const who = String((m.sender || {}).id || ""), pl = String((m.postback || {}).payload || "");
  if (!who || acc.ids.includes(who) || !pl.startsWith("fc:")) return "略過";
  const mediaKey = pl.slice(3) || "default";
  const mk = `pb:${acc.code}:` + (await h16((m.postback || {}).mid || `${who}:${m.timestamp}`));
  if (await env.KV.get(mk)) return "重複";
  if (!live) { await logEvent(env, now, acc.code, "postback", "dry"); return "只記錄（dry）"; }
  if (!(await rateOk(env, now, Number(cfg.max_per_minute || 10)))) return "速率上限";
  await env.KV.put(mk, "1", { expirationTtl: 2 * DAY });
  const { topic, link } = topicOf(cfg, mediaKey);
  const vars = { handle: acc.username || cfg.handle || "", topic, link };
  const uh = await h16(who), dk = `dl:${acc.code}:${uh}:${await h16(mediaKey)}`;
  const send = (message) => graph(env, acc.token, "POST", "/me/messages", { recipient: { id: who }, message });
  try {
    if (await env.KV.get(dk)) { await send({ text: fill(cfg.already_text, vars) }); await logEvent(env, now, acc.code, "postback", "already-delivered"); return "已送過"; }
    let prof;
    try { prof = await graph(env, acc.token, "GET", "/" + who, { fields: "is_user_follow_business" }); } catch { prof = null; }
    if (prof && prof.is_user_follow_business === true) {
      await send({ text: fill(cfg.ok_text, vars) });
      await env.KV.put(dk, "1", { expirationTtl: 30 * DAY });
      await logEvent(env, now, acc.code, "postback", "delivered", { follow: true });
      return "已送連結";
    }
    if (!prof) { await send({ text: fill(cfg.unknown_text, vars) }); await logEvent(env, now, acc.code, "postback", "follow-unknown"); return "查不到追蹤狀態"; }
    const nk = `nf:${acc.code}:${uh}:${today(now)}`;
    const n = Number((await env.KV.get(nk)) || 0);
    if (n >= NF_MAX) { await logEvent(env, now, acc.code, "postback", "nf-limit", { follow: false }); return "提醒次數到上限"; }
    await env.KV.put(nk, String(n + 1), { expirationTtl: 2 * DAY });
    await send({ attachment: { type: "template", payload: { template_type: "button", text: fill(cfg.not_following_text, vars),
      buttons: [{ type: "postback", title: cfg.button_title || "我已追蹤，給我連結", payload: "fc:" + mediaKey }] } } });
    await logEvent(env, now, acc.code, "postback", "not-following", { follow: false });
    return "提醒追蹤";
  } catch (e) {
    await env.KV.delete(mk);
    await logEvent(env, now, acc.code, "postback", "send-failed");
    return "失敗：" + String(e).slice(0, 100);
  }
}

// ---------- 管理端點（給定時檢查去重、給人檢視紀錄；Bearer SYNC_TOKEN）----------
async function admin(url, req, env) {
  const auth = (req.headers.get("authorization") || "").replace(/^Bearer /, "");
  if (!env.SYNC_TOKEN || !safeEq(auth, env.SYNC_TOKEN)) return new Response("forbidden", { status: 403 });
  const j = (o) => new Response(JSON.stringify(o), { headers: { "content-type": "application/json" } });
  if (url.pathname === "/handled") {
    const code = url.searchParams.get("account") || "";
    const ids = (url.searchParams.get("ids") || "").split(",").filter((x) => /^[0-9a-f]{16}$/.test(x)).slice(0, 200);
    const done = [];
    for (const id of ids) { const r = await env.KV.get(`c:${code}:${id}`, "json"); if (r && r.r === "sent") done.push(id); }
    return j({ handled: done });
  }
  const list = await env.KV.list({ prefix: "log:", limit: Math.min(Number(url.searchParams.get("limit") || 50), 200) });
  const logs = [];
  for (const k of list.keys) { const v = await env.KV.get(k.name, "json"); if (v) logs.push(v); }
  return j({ logs });
}
