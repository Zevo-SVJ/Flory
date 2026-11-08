import { env } from "../env";
import { query } from "../db";
import { QUEUES, queue } from "../queue";
import { getBot, getCredentialSummary } from "./credentials";
import { errMessage } from "../logger";

export type SystemStatus = {
  bot: { username?: string; id: number } | null;
  mtproto: { name?: string; username?: string } | null;
  webhook: { url: string; pending: number; lastError?: string; lastErrorAt?: Date } | { error: string } | null;
  worker: { ok: boolean; detail: string; uptime?: number };
  queues: { counts: Record<string, { waiting: number; active: number; delayed: number; failed: number }> } | { error: string };
  lastWebhookAt: Date | null;
};

async function withTimeout<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.race([p, new Promise<T>((_, rej) => setTimeout(() => rej(new Error("timeout")), ms))]);
}

export async function getSystemStatus(): Promise<SystemStatus> {
  const [creds, b] = await Promise.all([getCredentialSummary(), getBot()]);

  const webhook: SystemStatus["webhook"] = b
    ? await withTimeout(b.bot.getWebhookInfo(), 4000).then(
        (w) => ({ url: w.url, pending: w.pending_update_count, lastError: w.last_error_message, lastErrorAt: w.last_error_date ? new Date(w.last_error_date * 1000) : undefined }),
        (e) => ({ error: errMessage(e) }),
      )
    : null;

  const worker = await withTimeout(fetch(`${env().WORKER_URL}/health`, { cache: "no-store" }), 2500).then(
    async (r) => {
      const j = (await r.json()) as { status: string; uptime_s?: number };
      return { ok: r.ok, detail: j.status, uptime: j.uptime_s };
    },
    (e) => ({ ok: false, detail: `unreachable (${errMessage(e)})` }),
  );

  const queues = await withTimeout(
    (async () => {
      const out: Record<string, { waiting: number; active: number; delayed: number; failed: number }> = {};
      for (const [k, name] of Object.entries(QUEUES)) { const c = await queue(name).getJobCounts("waiting", "active", "delayed", "failed"); out[k] = { waiting: c.waiting ?? 0, active: c.active ?? 0, delayed: c.delayed ?? 0, failed: c.failed ?? 0 }; }
      return { counts: out };
    })(),
    3000,
  ).catch((e) => ({ error: errMessage(e) }));

  const last = await query<{ t: Date | null }>("SELECT max(received_at) AS t FROM webhook_events");
  return {
    bot: b ? { username: b.identity.username, id: b.identity.id } : null,
    mtproto: creds.mtproto ? { name: creds.mtproto.identity.name as string | undefined, username: creds.mtproto.identity.username as string | undefined } : null,
    webhook,
    worker,
    queues,
    lastWebhookAt: last.rows[0]?.t ?? null,
  };
}
