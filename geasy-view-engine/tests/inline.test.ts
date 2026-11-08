import fs from "node:fs";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

process.env.QUEUE_MODE = "inline";

const afterTasks: Promise<unknown>[] = [];
vi.mock("next/server", async (orig) => {
  const m = await orig<typeof import("next/server")>();
  return { ...m, after: (fn: () => unknown) => void afterTasks.push(Promise.resolve().then(fn)) };
});

import { FakeTelegram } from "./fake-telegram";
import { closePool, one, pool, query } from "@/lib/db";
import { poolConfig } from "@/lib/db";
import { env, resetEnvCache } from "@/lib/env";
import { runMigrations } from "@/lib/migrate";
import { BUNDLED_MIGRATIONS } from "@/lib/migrations-bundled";
import { getWebhookSecret, saveBotToken, webhookPathToken } from "@/lib/services/credentials";
import { addChannel } from "@/lib/services/channels";
import { runTick } from "@/lib/services/tick";
import { POST as webhook } from "@/app/tg/webhook/[token]/route";
import { GET as cron } from "@/app/api/cron/tick/route";

const tg = new FakeTelegram();
const CH = -1004444444444;
let secret = "", token = "", uid = 9000;

async function hook(update: object, header?: string) {
  const res = await webhook(
    new Request(`http://x/tg/webhook/${token}`, { method: "POST", headers: { "x-telegram-bot-api-secret-token": header ?? secret }, body: JSON.stringify(update) }),
    { params: Promise.resolve({ token }) },
  );
  await Promise.all(afterTasks.splice(0));
  return { status: res.status, body: await res.json() };
}
const post = (id: number) => ({ update_id: ++uid, channel_post: { message_id: id, date: Math.floor(Date.now() / 1000), chat: { id: CH, type: "channel" }, text: `hi ${id}` } });
const job = (k: string) => one<{ status: string; attempts: number; last_error: string | null }>("SELECT status, attempts, last_error FROM automation_jobs WHERE dedupe_key=$1", [k]);

beforeAll(async () => {
  await tg.start();
  tg.chats.set(CH, { type: "channel", title: "Inline Chan", username: "inline_chan" });
  tg.botStatusIn.set(CH, "administrator");
  await runMigrations();
  await saveBotToken("424242:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
  secret = (await getWebhookSecret())!;
  token = webhookPathToken(secret);
  const c = await addChannel("@inline_chan", "test");
  await query("UPDATE automation_settings SET reaction_enabled=true, reaction_emoji='🔥', notify_enabled=true, notify_chat_id=777 WHERE channel_id=$1", [c.id]);
});
afterAll(async () => { await tg.stop(); await closePool(); });

describe("serverless (inline) mode", () => {
  it("bundled migrations are identical to migrations/*.sql", () => {
    const dir = path.resolve("migrations");
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".sql")).sort();
    expect(BUNDLED_MIGRATIONS.map((m) => m.name)).toEqual(files);
    for (const m of BUNDLED_MIGRATIONS) expect(m.sql).toBe(fs.readFileSync(path.join(dir, m.name), "utf8"));
  });

  it("webhook route rejects bad secrets and processes a post right after answering", async () => {
    expect((await hook(post(1), "wrong")).status).toBe(401);
    const u = post(10);
    const r = await hook(u);
    expect(r).toEqual({ status: 200, body: { ok: true, duplicate: false } });
    expect((await one("SELECT 1 FROM telegram_posts WHERE message_id=10"))).not.toBeNull();
    expect((await job(`reaction:${CH}:m:10`))?.status).toBe("done");
    expect((await job(`notify:${CH}:m:10`))?.status).toBe("done");
    expect(tg.calls.filter((c) => c.method === "setMessageReaction")).toHaveLength(1);
    expect((await hook(u)).body.duplicate).toBe(true);
    expect(tg.calls.filter((c) => c.method === "setMessageReaction")).toHaveLength(1);
  });

  it("a retryable failure is retried by the scheduler tick with backoff, not lost", async () => {
    tg.failures.setMessageReaction = [{ code: 502, description: "Bad Gateway" }, { code: 502, description: "Bad Gateway" }, { code: 502, description: "Bad Gateway" }];
    await hook(post(11));
    const j1 = await job(`reaction:${CH}:m:11`);
    expect(j1?.status).toBe("pending");
    expect(j1?.last_error).toContain("502");
    // too early: backoff not elapsed → tick leaves it alone
    await runTick();
    expect((await job(`reaction:${CH}:m:11`))?.status).toBe("pending");
    await query("UPDATE automation_jobs SET updated_at = now() - interval '10 minutes' WHERE dedupe_key=$1", [`reaction:${CH}:m:11`]);
    const t = await runTick();
    expect(t).toMatchObject({ skipped: false });
    expect((await job(`reaction:${CH}:m:11`))?.status).toBe("done");
  });

  it("an unprocessed persisted event is picked up by the tick", async () => {
    const u = post(12);
    await query("INSERT INTO webhook_events (update_id, update_type, payload, received_at) VALUES ($1,'channel_post',$2, now() - interval '2 minutes')", [u.update_id, JSON.stringify(u)]);
    await runTick();
    expect((await one("SELECT 1 FROM telegram_posts WHERE message_id=12"))).not.toBeNull();
    expect((await one<{ status: string }>("SELECT status FROM webhook_events WHERE update_id=$1", [u.update_id]))!.status).toBe("processed");
  });

  it("gives up on events after the maximum number of attempts", async () => {
    const u = post(13);
    await query("INSERT INTO webhook_events (update_id, update_type, payload, attempts, last_attempt_at, received_at) VALUES ($1,'channel_post',$2, 8, now(), now() - interval '1 hour')", [u.update_id, JSON.stringify(u)]);
    await runTick();
    expect((await one<{ status: string }>("SELECT status FROM webhook_events WHERE update_id=$1", [u.update_id]))!.status).toBe("failed");
  });

  it("cron route requires the secret and records the tick", async () => {
    expect((await cron(new Request("http://x/api/cron/tick"))).status).toBe(401);
    expect((await cron(new Request("http://x/api/cron/tick", { headers: { authorization: "Bearer nope" } }))).status).toBe(401);
    const ok = await cron(new Request("http://x/api/cron/tick", { headers: { authorization: `Bearer ${env().CRON_SECRET}` } }));
    expect(ok.status).toBe(202);
    await Promise.all(afterTasks.splice(0));
    expect(await one("SELECT 1 FROM system_state WHERE key='last_tick'")).not.toBeNull();
  });

  it("ticks never overlap (advisory lock)", async () => {
    const c = await pool().connect();
    try {
      await c.query("SELECT pg_advisory_lock(727275)");
      expect(await runTick()).toEqual({ skipped: true });
    } finally {
      await c.query("SELECT pg_advisory_unlock(727275)");
      c.release();
    }
  });
});

describe("configuration safety", () => {
  it("verifies TLS on remote databases and not on localhost", () => {
    const saved = process.env.DATABASE_URL;
    process.env.DATABASE_URL = "postgres://u:p@aws-0-eu-west-3.pooler.supabase.com:5432/postgres?sslmode=require";
    resetEnvCache();
    const remote = poolConfig();
    expect((remote.ssl as { rejectUnauthorized: boolean }).rejectUnauthorized).toBe(true);
    expect(remote.connectionString).not.toContain("sslmode");
    process.env.DATABASE_URL = saved;
    resetEnvCache();
    expect(poolConfig().ssl).toBeUndefined();
  });

  it("derives stable, distinct secrets from DATABASE_URL when none are provided", () => {
    const saved = { ...process.env };
    delete process.env.ENCRYPTION_KEY;
    process.env.DATABASE_URL = "postgres://a:one@localhost/x";
    resetEnvCache();
    const a = env();
    expect(a.ENCRYPTION_KEY).toMatch(/^[0-9a-f]{64}$/);
    expect(a.CRON_SECRET).not.toBe(a.ENCRYPTION_KEY);
    resetEnvCache();
    expect(env().ENCRYPTION_KEY).toBe(a.ENCRYPTION_KEY);
    process.env.DATABASE_URL = "postgres://a:two@localhost/x";
    resetEnvCache();
    expect(env().ENCRYPTION_KEY).not.toBe(a.ENCRYPTION_KEY);
    Object.assign(process.env, saved);
    resetEnvCache();
  });
});
