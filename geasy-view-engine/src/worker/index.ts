import http from "node:http";
import { Worker, UnrecoverableError, type Job } from "bullmq";
import { query, closePool } from "@/lib/db";
import { runMigrations } from "@/lib/migrate";
import { QUEUES, queue, redisConnection, closeQueues } from "@/lib/queue";
import { log, errMessage } from "@/lib/logger";
import { logActivity } from "@/lib/activity";
import { ingestUpdate, processWebhookEvent, sweepPendingEvents, verifyWebhookRequest, type TgUpdate } from "@/lib/services/updates";
import { PermanentJobError, RateLimitedError, runJob } from "@/lib/services/actions";
import { resumePendingJobs } from "@/lib/services/automation";
import { snapshotChannel, statsTick } from "@/lib/services/statsjobs";
import { runRetention } from "@/lib/services/maintenance";
import { webhookPathToken } from "@/lib/services/credentials";
import { disconnectMtproto } from "@/lib/telegram/mtproto";
import { env } from "@/lib/env";

const started = Date.now();

// ───────────────────────── HTTP: webhook + health ─────────────────────────
function readBody(req: http.IncomingMessage, max = 1_000_000): Promise<string> {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => {
      size += c.length;
      if (size > max) {
        reject(new Error("payload too large"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function health() {
  const out: Record<string, unknown> = { uptime_s: Math.round((Date.now() - started) / 1000) };
  let ok = true;
  try { await query("SELECT 1"); out.db = "ok"; } catch (e) { ok = false; out.db = errMessage(e); }
  try { out.redis = (await redisConnection().ping()) === "PONG" ? "ok" : "bad"; if (out.redis !== "ok") ok = false; } catch (e) { ok = false; out.redis = errMessage(e); }
  return { ok, body: { status: ok ? "ok" : "degraded", ...out } };
}

const server = http.createServer(async (req, res) => {
  const send = (code: number, body: unknown) => {
    res.writeHead(code, { "content-type": "application/json" });
    res.end(JSON.stringify(body));
  };
  try {
    const url = new URL(req.url ?? "/", "http://x");
    if (req.method === "GET" && url.pathname === "/health") {
      const h = await health();
      return send(h.ok ? 200 : 503, h.body);
    }
    const m = url.pathname.match(/^\/tg\/webhook\/([A-Za-z0-9]{8,64})$/);
    if (req.method === "POST" && m) {
      let authorised: boolean;
      try {
        authorised = await verifyWebhookRequest(m[1], req.headers["x-telegram-bot-api-secret-token"] as string | undefined, webhookPathToken);
      } catch (e) {
        log.error("webhook auth check failed (db?)", { error: errMessage(e) });
        return send(503, { error: "unavailable" }); // Telegram will retry
      }
      if (!authorised) {
        log.warn("webhook rejected: bad secret");
        return send(401, { error: "unauthorized" });
      }
      let update: TgUpdate;
      try {
        update = JSON.parse(await readBody(req));
        if (!Number.isSafeInteger(update?.update_id)) throw new Error("no update_id");
      } catch {
        return send(400, { error: "bad payload" });
      }
      try {
        const r = await ingestUpdate(update);
        return send(200, { ok: true, duplicate: r.duplicate });
      } catch (e) {
        log.error("ingest failed", { error: errMessage(e) });
        return send(503, { error: "unavailable" }); // not persisted → ask Telegram to redeliver
      }
    }
    send(404, { error: "not found" });
  } catch (e) {
    log.error("http handler error", { error: errMessage(e) });
    if (!res.headersSent) send(500, { error: "internal" });
  }
});

// ───────────────────────── Queue workers ─────────────────────────
const workers: Worker[] = [];

function mk(name: string, concurrency: number, processor: (job: Job, w: Worker) => Promise<unknown>, extra: Record<string, unknown> = {}) {
  const w: Worker = new Worker(name, (job) => processor(job, w), { connection: redisConnection(), concurrency, ...extra });
  w.on("error", (e) => log.warn("worker error", { queue: name, error: errMessage(e) }));
  workers.push(w);
  return w;
}

async function bootstrap() {
  env(); // fail fast on bad config
  await runMigrations();

  mk(QUEUES.updates, 4, async (job) => {
    await processWebhookEvent(job.data.eventId);
  }).on("failed", async (job, err) => {
    if (!job || job.attemptsMade < (job.opts.attempts ?? 1)) return;
    const id = job.data.eventId as number;
    await query("UPDATE webhook_events SET status='failed', error=$2 WHERE id=$1 AND status='pending'", [id, errMessage(err)]).catch(() => {});
    await logActivity({ level: "error", category: "webhook", action: "event_failed", message: `Webhook event ${id} failed permanently: ${errMessage(err)}` });
  });

  mk(
    QUEUES.actions,
    2,
    async (job, w) => {
      const final = job.attemptsMade + 1 >= (job.opts.attempts ?? 1);
      try {
        await runJob(job.data.jobRowId, final);
      } catch (e) {
        if (e instanceof RateLimitedError) {
          await w.rateLimit(e.ms);
          throw Worker.RateLimitError();
        }
        if (e instanceof PermanentJobError) throw new UnrecoverableError(e.message);
        throw e;
      }
    },
    { limiter: { max: 20, duration: 1000 } },
  );

  mk(QUEUES.stats, 1, async (job) => {
    switch (job.name) {
      case "snapshot-channel": {
        try {
          return await snapshotChannel(job.data.channelId);
        } catch (e) {
          await logActivity({ level: "warn", category: "stats", action: "snapshot_failed", channelId: job.data.channelId, message: `Snapshot failed (attempt ${job.attemptsMade + 1}): ${errMessage(e)}` });
          throw e;
        }
      }
      case "tick":
        return statsTick();
      case "sweep": {
        const events = await sweepPendingEvents();
        const jobs = await resumePendingJobs();
        if (events || jobs) await logActivity({ category: "system", action: "sweep", message: `Recovered ${events} pending webhook event(s) and ${jobs} job(s)` });
        return { events, jobs };
      }
      case "retention":
        return runRetention();
      default:
        log.warn("unknown stats job", { name: job.name });
    }
  });

  const q = queue(QUEUES.stats);
  await q.upsertJobScheduler("tick", { every: 60_000 }, { name: "tick", opts: { attempts: 1 } });
  await q.upsertJobScheduler("sweep", { every: 30_000 }, { name: "sweep", opts: { attempts: 1 } });
  await q.upsertJobScheduler("retention", { pattern: "17 3 * * *" }, { name: "retention", opts: { attempts: 1 } });

  // Resume after restart: whatever was pending in Postgres goes back on the queues right now.
  const events = await sweepPendingEvents();
  const jobs = await resumePendingJobs();
  await logActivity({ category: "system", action: "start", message: `Worker started (resumed ${events} event(s), ${jobs} job(s))` });

  await new Promise<void>((r) => server.listen(env().WORKER_PORT, "0.0.0.0", r));
  log.info("worker listening", { port: env().WORKER_PORT });
}

async function shutdown(sig: string) {
  log.info("shutting down", { sig });
  server.close();
  await Promise.allSettled(workers.map((w) => w.close()));
  await disconnectMtproto();
  await closeQueues();
  await closePool();
  process.exit(0);
}
process.on("SIGTERM", () => void shutdown("SIGTERM"));
process.on("SIGINT", () => void shutdown("SIGINT"));
process.on("unhandledRejection", (e) => log.error("unhandledRejection", { error: errMessage(e) }));

bootstrap().catch((e) => {
  log.error("worker failed to start", { error: errMessage(e) });
  process.exit(1);
});
