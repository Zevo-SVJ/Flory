import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { FakeTelegram } from "./fake-telegram";
import { one, query, closePool } from "@/lib/db";
import { runMigrations } from "@/lib/migrate";
import { getWebhookSecret, saveBotToken, webhookPathToken } from "@/lib/services/credentials";
import { addChannel, verifyChannel, UserFacingError, listChannels } from "@/lib/services/channels";
import { sweepPendingEvents } from "@/lib/services/updates";
import { setMtprotoSourceForTests, snapshotChannel, snapshotPosts } from "@/lib/services/statsjobs";
import { runRetention } from "@/lib/services/maintenance";
import { ensureManualPost } from "@/lib/services/posts";
import { channelPerformance, listPosts } from "@/lib/services/analytics";

const tg = new FakeTelegram();
const BASE = "http://127.0.0.1:14000";
const TOKEN = "424242:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
const CH1 = -1001111111111;
const CH2 = -1002222222222;
const CH3 = -1003333333333;
let secret = "";
let pathToken = "";
let uid = 1000;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
async function until<T>(fn: () => Promise<T | null | undefined | false>, ms = 15000): Promise<T> {
  const end = Date.now() + ms;
  for (;;) {
    const v = await fn();
    if (v) return v;
    if (Date.now() > end) throw new Error("timeout waiting for condition");
    await sleep(100);
  }
}

async function hook(update: object, opts: { header?: string; path?: string; raw?: string } = {}) {
  const res = await fetch(`${BASE}/tg/webhook/${opts.path ?? pathToken}`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-telegram-bot-api-secret-token": opts.header ?? secret },
    body: opts.raw ?? JSON.stringify(update),
  });
  return { status: res.status, body: await res.json().catch(() => null) };
}

const post = (chat: number, id: number, extra: object = {}) => ({
  update_id: ++uid,
  channel_post: { message_id: id, date: Math.floor(Date.now() / 1000), chat: { id: chat, type: "channel" }, text: `hello ${id}`, ...extra },
});

async function chId(chat: number) {
  return (await one<{ id: string }>("SELECT id FROM channels WHERE tg_chat_id=$1", [chat]))!.id;
}
async function setSettings(chat: number, patch: Record<string, unknown>) {
  const cols = Object.keys(patch);
  await query(`UPDATE automation_settings SET ${cols.map((c, i) => `${c}=$${i + 2}`).join(",")} WHERE channel_id=$1`, [await chId(chat), ...Object.values(patch)]);
}
async function job(kind: string, dedupe: string) {
  return one<{ status: string; attempts: number; last_error: string | null }>("SELECT status, attempts, last_error FROM automation_jobs WHERE kind=$1 AND dedupe_key=$2", [kind, dedupe]);
}

beforeAll(async () => {
  await tg.start();
  tg.chats.set(CH1, { type: "channel", title: "Geasy One", username: "geasy_one" });
  tg.chats.set(CH2, { type: "channel", title: "Geasy Two", username: "geasy_two", available_reactions: [{ type: "emoji", emoji: "❤" }] });
  tg.chats.set(CH3, { type: "channel", title: "Private Three" });
  tg.botStatusIn.set(CH1, "administrator");
  tg.botStatusIn.set(CH2, "administrator");
  tg.botStatusIn.set(CH3, "left");
  await runMigrations();
  await import("@/worker/index");
  await until(async () => (await fetch(`${BASE}/health`).catch(() => null))?.status === 200);
});

afterAll(async () => {
  setMtprotoSourceForTests(null);
  await tg.stop();
  await closePool();
});

describe("bot + channels", () => {
  it("rejects malformed tokens and stores a valid one encrypted, registering the webhook", async () => {
    await expect(saveBotToken("nope")).rejects.toThrow(/does not look/);
    const { identity, webhookUrl } = await saveBotToken(TOKEN);
    expect(identity.username).toBe("geasy_test_bot");
    secret = (await getWebhookSecret())!;
    pathToken = webhookPathToken(secret);
    expect(webhookUrl).toBe(`https://geasy.test/tg/webhook/${pathToken}`);
    const sw = tg.calls.find((c) => c.method === "setWebhook")!;
    expect(sw.params.secret_token).toBe(secret);
    expect(sw.params.allowed_updates).toContain("message_reaction_count");
    const raw = await one<{ payload_enc: string }>("SELECT payload_enc FROM telegram_credentials WHERE kind='bot'");
    expect(raw!.payload_enc).not.toContain("AAAAAAAA");
  });

  it("adds channels, distinguishes real access from a mere public URL", async () => {
    const c1 = await addChannel("https://t.me/geasy_one", "test");
    expect(c1.status).toBe("connected");
    expect(c1.subscriber_count).toBe(1234);
    expect(c1.available_reactions).toBeNull();
    const c2 = await addChannel("@geasy_two", "test");
    expect(c2.available_reactions).toEqual(["❤"]);
    const c3 = await addChannel("https://t.me/c/3333333333/10", "test");
    expect(c3.status).toBe("no_access"); // bot is not a member: no authorisation implied
    expect(c3.is_private).toBe(true);
    expect((await listChannels()).length).toBe(3);
    // idempotent re-add
    await addChannel("geasy_one", "test");
    expect((await listChannels()).length).toBe(3);
  });

  it("gives clear errors for bad input and unknown channels", async () => {
    await expect(addChannel("https://t.me/+invite", "t")).rejects.toThrow(UserFacingError);
    await expect(addChannel("https://t.me/doesnotexist", "t")).rejects.toThrow(/cannot find/);
    tg.chats.set(-1009, { type: "supergroup", title: "G", username: "somegroup" });
    await expect(addChannel("@somegroup", "t")).rejects.toThrow(/not a channel/);
  });

  it("re-verifies access after the bot is promoted", async () => {
    tg.botStatusIn.set(CH3, "administrator");
    const c = await verifyChannel(await chId(CH3));
    expect(c.status).toBe("connected");
  });
});

describe("webhook security", () => {
  it("rejects bad secrets, bad paths and bad payloads", async () => {
    expect((await hook(post(CH1, 1), { header: "wrong" })).status).toBe(401);
    expect((await hook(post(CH1, 1), { path: "a".repeat(24) })).status).toBe(401);
    expect((await hook({}, { raw: "{not json" })).status).toBe(400);
    expect((await hook({ nope: 1 })).status).toBe(400);
    expect((await fetch(`${BASE}/tg/webhook/${pathToken}`, { method: "POST", body: "{}" })).status).toBe(401);
    expect((await one("SELECT 1 FROM webhook_events"))).toBeNull();
  });
});

describe("automatic post detection", () => {
  it("creates one post for duplicate deliveries and starts reaction + notify jobs once", async () => {
    await setSettings(CH1, { reaction_enabled: true, reaction_emoji: "🔥", notify_enabled: true, notify_chat_id: 777 });
    const u = post(CH1, 100, { photo: [{}], text: undefined, caption: "caption text" });
    expect((await hook(u)).body.duplicate).toBe(false);
    expect((await hook(u)).body.duplicate).toBe(true);
    await until(async () => (await job("reaction", `reaction:${CH1}:m:100`))?.status === "done");
    await until(async () => (await job("notify", `notify:${CH1}:m:100`))?.status === "done");
    const p = await one<{ media_type: string; text: string; source: string }>("SELECT media_type, text, source FROM telegram_posts WHERE message_id=100");
    expect(p).toMatchObject({ media_type: "photo", text: "caption text", source: "webhook" });
    expect((await query("SELECT 1 FROM webhook_events WHERE update_id=$1", [u.update_id])).rowCount).toBe(1);
    expect(tg.calls.filter((c) => c.method === "setMessageReaction" && c.params.message_id === 100)).toHaveLength(1);
    const react = tg.calls.find((c) => c.method === "setMessageReaction")!;
    expect(react.params).toMatchObject({ chat_id: CH1, reaction: [{ type: "emoji", emoji: "🔥" }] });
    const note = tg.calls.find((c) => c.method === "sendMessage")!;
    expect(note.params.chat_id).toBe(777);
    expect(note.params.text).toContain("Geasy One");
    expect(note.params.text).toContain("https://t.me/geasy_one/100");
    const log = await one<{ actor: string }>("SELECT actor FROM activity_logs WHERE action='react'");
    expect(log!.actor).toBe("bot:@geasy_test_bot"); // identity stays traceable
  });

  it("handles video, forwarded and album posts; albums act once", async () => {
    const gid = "album-1";
    for (const id of [201, 202, 203]) await hook(post(CH1, id, { photo: [{}], media_group_id: gid }));
    await hook(post(CH1, 210, { video: {} }));
    await hook(post(CH1, 211, { forward_origin: { type: "channel", chat: { title: "Origin Ch" } } }));
    await until(async () => (await job("reaction", `reaction:${CH1}:g:${gid}`))?.status === "done");
    await until(async () => (await query("SELECT 1 FROM telegram_posts WHERE message_id IN (201,202,203,210,211)")).rowCount === 5);
    expect((await query("SELECT 1 FROM automation_jobs WHERE dedupe_key LIKE $1", [`reaction:${CH1}:g:${gid}`])).rowCount).toBe(1);
    expect((await one<{ media_type: string }>("SELECT media_type FROM telegram_posts WHERE message_id=210"))!.media_type).toBe("video");
    const f = await one<{ is_forwarded: boolean; forward_origin: any }>("SELECT is_forwarded, forward_origin FROM telegram_posts WHERE message_id=211");
    expect(f!.is_forwarded).toBe(true);
    expect(f!.forward_origin.from).toBe("Origin Ch");
    expect((await query("SELECT 1 FROM telegram_posts WHERE media_group_id=$1", [gid])).rowCount).toBe(3);
  });

  it("applies edits", async () => {
    await hook({ update_id: ++uid, edited_channel_post: { message_id: 100, date: 1, edit_date: Math.floor(Date.now() / 1000), chat: { id: CH1 }, caption: "edited!", photo: [{}] } });
    const p = await until(async () => {
      const r = await one<{ is_edited: boolean; text: string }>("SELECT is_edited, text FROM telegram_posts WHERE message_id=100");
      return r?.is_edited ? r : null;
    });
    expect(p.text).toBe("edited!");
  });

  it("ignores unregistered channels and disabled monitoring", async () => {
    await hook(post(-100999, 1));
    await setSettings(CH2, { monitoring_enabled: false });
    await hook(post(CH2, 5));
    await until(async () => (await query("SELECT 1 FROM webhook_events WHERE status='ignored'")).rowCount! >= 2);
    expect((await query("SELECT 1 FROM telegram_posts WHERE message_id=5")).rowCount).toBe(0);
    await setSettings(CH2, { monitoring_enabled: true });
  });

  it("records reaction counts from message_reaction_count without inventing views", async () => {
    await hook({
      update_id: ++uid,
      message_reaction_count: { chat: { id: CH1 }, message_id: 100, date: 1, reactions: [
        { type: { type: "emoji", emoji: "🔥" }, total_count: 7 }, { type: { type: "emoji", emoji: "👍" }, total_count: 3 } ] },
    });
    await until(async () => (await query("SELECT 1 FROM post_reactions")).rowCount === 2);
    const s = await one<{ views: number | null; reactions_total: number; source: string }>("SELECT views, reactions_total, source FROM post_statistics ORDER BY id DESC LIMIT 1");
    expect(s).toEqual({ views: null, reactions_total: 10, source: "bot_api" });
    // a later update that drops an emoji removes it from the current view
    await hook({ update_id: ++uid, message_reaction_count: { chat: { id: CH1 }, message_id: 100, date: 2, reactions: [{ type: { type: "emoji", emoji: "🔥" }, total_count: 8 }] } });
    await until(async () => (await query("SELECT 1 FROM post_reactions")).rowCount === 1);
  });

  it("tracks bot membership changes", async () => {
    await hook({ update_id: ++uid, my_chat_member: { chat: { id: CH3, type: "channel" }, new_chat_member: { status: "kicked" } } });
    await until(async () => (await one<{ status: string }>("SELECT status FROM channels WHERE tg_chat_id=$1", [CH3]))!.status === "disconnected");
  });
});

describe("reaction job reliability", () => {
  it("skips emojis the channel does not allow, without calling Telegram", async () => {
    await setSettings(CH2, { reaction_enabled: true, reaction_emoji: "🔥" });
    const before = tg.count("setMessageReaction");
    await hook(post(CH2, 300));
    const j = await until(async () => { const x = await job("reaction", `reaction:${CH2}:m:300`); return x && x.status !== "pending" && x.status !== "running" ? x : null; });
    expect(j.status).toBe("skipped");
    expect(tg.count("setMessageReaction")).toBe(before);
  });

  it("retries transient 5xx inside the client with backoff", async () => {
    tg.failures.setMessageReaction = [{ code: 502, description: "Bad Gateway" }, { code: 502, description: "Bad Gateway" }];
    const before = tg.count("setMessageReaction");
    await hook(post(CH1, 400));
    await until(async () => (await job("reaction", `reaction:${CH1}:m:400`))?.status === "done");
    expect(tg.count("setMessageReaction") - before).toBe(3);
  });

  it("honours 429 retry_after through the queue", async () => {
    tg.failures.setMessageReaction = [{ code: 429, description: "Too Many Requests", retry_after: 1 }];
    const before = tg.count("setMessageReaction");
    await hook(post(CH1, 401));
    await until(async () => (await job("reaction", `reaction:${CH1}:m:401`))?.status === "done", 20000);
    expect(tg.count("setMessageReaction") - before).toBe(2);
  });

  it("fails permanently on invalid reactions, logs it and counts the failure", async () => {
    tg.failures.setMessageReaction = [{ code: 400, description: "Bad Request: REACTION_INVALID" }];
    await hook(post(CH1, 402));
    const j = await until(async () => { const x = await job("reaction", `reaction:${CH1}:m:402`); return x?.status === "failed" ? x : null; });
    expect(j.last_error).toContain("REACTION_INVALID");
    expect((await one<{ consecutive_failures: number }>("SELECT consecutive_failures FROM automation_settings WHERE channel_id=$1", [await chId(CH1)]))!.consecutive_failures).toBe(1);
    expect((await query("SELECT 1 FROM activity_logs WHERE level='error' AND category='reaction'")).rowCount).toBeGreaterThan(0);
  });

  it("auto-pauses a channel after N consecutive failures when configured", async () => {
    await setSettings(CH1, { pause_after_failures: 2 });
    tg.failures.setMessageReaction = [{ code: 400, description: "Bad Request: REACTION_INVALID" }];
    await hook(post(CH1, 403));
    await until(async () => (await one<{ monitoring_enabled: boolean }>("SELECT monitoring_enabled FROM automation_settings WHERE channel_id=$1", [await chId(CH1)]))!.monitoring_enabled === false);
    await setSettings(CH1, { monitoring_enabled: true, pause_after_failures: 0, consecutive_failures: 0 });
  });
});

describe("crash recovery", () => {
  it("re-enqueues persisted events that never reached the queue", async () => {
    const u = post(CH1, 500);
    await query("INSERT INTO webhook_events (update_id, update_type, payload, received_at) VALUES ($1,'channel_post',$2, now() - interval '2 minutes')", [u.update_id, JSON.stringify(u)]);
    expect(await sweepPendingEvents()).toBeGreaterThanOrEqual(1);
    await until(async () => (await query("SELECT 1 FROM telegram_posts WHERE message_id=500")).rowCount === 1);
  });
});

describe("statistics from MTProto", () => {
  it("records real views/forwards/reactions and respects the polling schedule", async () => {
    const ch = (await one<{ id: string; tg_chat_id: number; username: string | null }>("SELECT id, tg_chat_id, username FROM channels WHERE tg_chat_id=$1", [CH1]))!;
    let calls = 0;
    setMtprotoSourceForTests({
      async fetchMessages(_peer, ids) {
        calls++;
        return new Map(ids.filter((i) => i !== 211).map((i) => [i, {
          messageId: i, date: new Date(), views: 1000 + calls, forwards: 5, replies: 2, reactions: { "🔥": 9, "👍": 4 },
          text: null, mediaType: "photo" as const, groupedId: null, isForwarded: false }]));
      },
    });
    await query("UPDATE telegram_posts SET last_stats_at=NULL WHERE channel_id=$1", [ch.id]);
    const n = await snapshotChannel(ch.id);
    expect(n).toBeGreaterThan(5);
    const s = await one<{ views: number; forwards: number; reactions_total: number; source: string }>(
      "SELECT views, forwards, reactions_total, source FROM post_statistics WHERE source='mtproto' AND post_id=(SELECT id FROM telegram_posts WHERE message_id=100 AND channel_id=$1) ORDER BY id DESC LIMIT 1", [ch.id]);
    expect(s).toMatchObject({ views: 1001, forwards: 5, reactions_total: 13, source: "mtproto" });
    // post 211 is not returned → treated as deleted, tracking stops
    expect((await one<{ tracking_enabled: boolean }>("SELECT tracking_enabled FROM telegram_posts WHERE message_id=211 AND channel_id=$1", [ch.id]))!.tracking_enabled).toBe(false);
    // immediately after, nothing is due
    expect(await snapshotChannel(ch.id)).toBe(0);
    expect(calls).toBe(1);
    // analytics see real numbers
    const perf = (await channelPerformance(30)).find((c) => c.channel_id === ch.id)!;
    expect(perf.posts_with_views).toBeGreaterThan(5);
    expect(perf.avg_views).toBe(1001);
    const rows = await listPosts({ channelId: ch.id });
    expect(rows.find((r) => r.message_id === 100)!.views).toBe(1001);
  });

  it("registers an individual post by URL and fills it from MTProto", async () => {
    const chId1 = await chId(CH1);
    const stub = await ensureManualPost(chId1, 9001);
    expect(stub.media_type).toBe("unknown");
    expect(stub.source).toBe("manual");
    setMtprotoSourceForTests({
      async fetchMessages(_p, ids) {
        return new Map(ids.map((i) => [i, { messageId: i, date: new Date("2026-01-01"), views: 42, forwards: 1, replies: null, reactions: {}, text: "old post", mediaType: "text" as const, groupedId: null, isForwarded: false }]));
      },
    });
    await snapshotPosts({ id: chId1, tg_chat_id: CH1, username: "geasy_one" }, [stub]);
    const p = await one<{ text: string; media_type: string; published_at: Date }>("SELECT text, media_type, published_at FROM telegram_posts WHERE id=$1", [stub.id]);
    expect(p).toMatchObject({ text: "old post", media_type: "text" });
    expect(new Date(p!.published_at).getFullYear()).toBe(2026);
  });
});

describe("retention", () => {
  it("downsamples old snapshots to one per day and purges old events/logs", async () => {
    const p = (await one<{ id: string }>("SELECT id FROM telegram_posts WHERE message_id=100"))!;
    await query("DELETE FROM post_statistics WHERE post_id=$1", [p.id]);
    for (const h of [1, 2, 3, 4]) {
      await query("INSERT INTO post_statistics (post_id, captured_at, source, views) VALUES ($1, now() - interval '60 days' + make_interval(hours => $2), 'mtproto', $3)", [p.id, h, h]);
    }
    await query("INSERT INTO post_statistics (post_id, source, views) VALUES ($1,'mtproto',99)", [p.id]);
    await query("UPDATE webhook_events SET received_at = now() - interval '30 days' WHERE id = (SELECT min(id) FROM webhook_events WHERE status<>'pending')");
    const before = (await query("SELECT 1 FROM webhook_events")).rowCount!;
    const s = await runRetention();
    expect(s.snapshotsDownsampled).toBe(3);
    expect((await query("SELECT 1 FROM post_statistics WHERE post_id=$1", [p.id])).rowCount).toBe(2);
    expect((await query("SELECT 1 FROM webhook_events")).rowCount).toBe(before - 1);
  });
});
