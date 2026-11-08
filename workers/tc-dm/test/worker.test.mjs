// node --test workers/tc-dm/test/worker.test.mjs —— 驗簽、去重、兩段式（先私回、對方回「好了」才查追蹤）、閘門。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import worker, { verifySig, handle } from "../worker.js";

const CFG = JSON.parse(readFileSync(new URL("../../../social/tc/dm_config.json", import.meta.url)));

function kv() {
  const m = new Map();
  return { m, async get(k, t) { const v = m.get(k); return v == null ? null : t === "json" ? JSON.parse(v) : v; },
    async put(k, v) { m.set(k, v); }, async delete(k) { m.delete(k); } };
}

function setup({ mode = "webhook", legal = true, follows = true } = {}) {
  const cfg = structuredClone(CFG);
  cfg.ig_dm.mode = mode; cfg.legal_reviewed = legal;
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    const u = String(url);
    calls.push({ u, method: init.method || "GET", body: init.body ? JSON.parse(init.body) : null });
    const j = (o) => new Response(JSON.stringify(o), { status: 200 });
    if (u.endsWith("dm_config.json")) return j(cfg);
    if (u.endsWith("posted.json")) return j({ posts: [{ id: "20261105_quanta", ids_ig: "m1" }] });
    if (u.includes("/me?")) return j({ username: "tc_ig" });
    if (u.includes("/u9?")) return j({ is_user_follow_business: follows });
    if (u.endsWith("/me/messages")) return j({ message_id: "x" });
    return new Response("{}", { status: 404 });
  };
  const env = { KV: kv(), IG_TOKEN: "TOK", IG_APP_SECRET: "sec", VERIFY_TOKEN: "vt", GRAPH: "https://graph.instagram.com/v24.0",
    CONFIG_URL: "https://raw/dm_config.json", POSTED_URL: "https://raw/posted.json" };
  return { env, calls, sent: () => calls.filter((c) => c.u.endsWith("/me/messages")).map((c) => c.body) };
}

const comment = (id = "c1", text = "想看透明整理") => ({ entry: [{ id: "222", changes: [{ field: "comments",
  value: { id, text, from: { id: "u9", username: "amy" }, media: { id: "m1" } } }] }] });
const message = (mid = "mid1", text = "好了") => ({ entry: [{ id: "222", messaging: [{ sender: { id: "u9" }, timestamp: 1, message: { mid, text } }] }] });

test("驗簽：對的過、錯的擋", async () => {
  const { createHmac } = await import("node:crypto");
  const raw = '{"a":1}';
  const sig = "sha256=" + createHmac("sha256", "sec").update(raw).digest("hex");
  assert.equal(await verifySig(raw, sig, "sec"), true);
  assert.equal(await verifySig(raw, sig, "other"), false);
  assert.equal(await verifySig(raw, "", "sec"), false);
  const { env } = setup();
  const r = await worker.fetch(new Request("https://w/ig-webhook", { method: "POST", body: raw, headers: { "x-hub-signature-256": "sha256=00" } }), env, { waitUntil() {} });
  assert.equal(r.status, 403);
});

test("webhook 驗證 GET 回 challenge", async () => {
  const { env } = setup();
  const ok = await worker.fetch(new Request("https://w/ig-webhook?hub.mode=subscribe&hub.verify_token=vt&hub.challenge=123"), env, {});
  assert.equal(await ok.text(), "123");
  const bad = await worker.fetch(new Request("https://w/ig-webhook?hub.mode=subscribe&hub.verify_token=no&hub.challenge=1"), env, {});
  assert.equal(bad.status, 403);
});

test("兩段式：先私回請追蹤，回「好了」才查追蹤並送整理；不重複", async () => {
  const s = setup();
  await handle(comment(), s.env, Date.UTC(2026, 10, 10, 12));
  assert.deepEqual(s.sent()[0].recipient, { comment_id: "c1" });
  assert.match(s.sent()[0].message.text, /@tc_ig.*好了/);
  assert.ok(!s.calls.some((c) => c.u.includes("/u9?")), "第 1 則私訊前不能查追蹤");
  await handle(comment(), s.env, Date.UTC(2026, 10, 10, 12, 1));          // Meta 重送 → 去重
  assert.equal(s.sent().length, 1);
  await handle(message(), s.env, Date.UTC(2026, 10, 10, 12, 5));
  const last = s.sent().at(-1);
  assert.deepEqual(last.recipient, { id: "u9" });
  assert.match(last.message.text, /58～69K/);
  for (const v of s.env.KV.m.values()) assert.ok(!String(v).includes("amy") && !String(v).includes("透明整理"));
  for (const k of s.env.KV.m.keys()) assert.ok(!k.includes("u9") && !k.includes("c1"));
});

test("沒追蹤 → 提醒；每天最多 3 次", async () => {
  const s = setup({ follows: false });
  await handle(comment(), s.env, Date.UTC(2026, 10, 10, 12));
  for (let i = 0; i < 5; i++) await handle(message("mid" + i), s.env, Date.UTC(2026, 10, 10, 12, 5 + i));
  const nf = s.sent().filter((b) => /還沒看到你追蹤/.test(b.message.text));
  assert.equal(nf.length, 3);
});

test("mode 不是 webhook 或沒過法遵 → 只記錄不送", async () => {
  for (const o of [{ mode: "poll" }, { legal: false }]) {
    const s = setup(o);
    await handle(comment(), s.env, Date.UTC(2026, 10, 10, 12));
    assert.equal(s.sent().length, 0);
  }
});

test("每人每天 1 次", async () => {
  const s = setup();
  await handle(comment("c1"), s.env, Date.UTC(2026, 10, 10, 12));
  await handle(comment("c2"), s.env, Date.UTC(2026, 10, 10, 13));
  assert.equal(s.sent().length, 1);
});

test("follow_gate=false：不查追蹤，留言後直接私回開頭句＋重點", async () => {
  const s = setup({ follows: false });
  const cfg = JSON.parse(readFileSync(new URL("../../../social/tc/dm_config.json", import.meta.url)));
  cfg.ig_dm.mode = "webhook"; cfg.ig_dm.follow_gate = false;
  const orig = globalThis.fetch;
  globalThis.fetch = async (u, i) => (String(u).endsWith("dm_config.json") ? new Response(JSON.stringify(cfg)) : orig(u, i));
  await handle(comment(), s.env, Date.UTC(2026, 10, 10, 12));
  await handle(message(), s.env, Date.UTC(2026, 10, 10, 12, 5));
  assert.match(s.sent()[0].message.text, /^謝謝留言！重點整理在下一則，想看後續可以追蹤 @tc_ig[\s\S]*58～69K/);
  assert.ok(!s.calls.some((c) => c.u.includes("/u9?")));
  assert.ok(!s.sent().some((b) => /還沒看到你追蹤/.test(b.message.text)));
});
