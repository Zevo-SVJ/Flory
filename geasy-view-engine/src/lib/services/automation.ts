import { one, query } from "../db";
import { QUEUES, queue } from "../queue";
import { log, errMessage } from "../logger";

export type AutomationSettings = {
  channel_id: string;
  monitoring_enabled: boolean;
  stats_enabled: boolean;
  reaction_enabled: boolean;
  reaction_emoji: string;
  notify_enabled: boolean;
  notify_chat_id: number | null;
  monitor_interval_s: number;
  tracking_days: number;
  max_retries: number;
  pause_after_failures: number;
  consecutive_failures: number;
};

export async function getSettings(channelId: string): Promise<AutomationSettings | null> {
  return one<AutomationSettings>("SELECT * FROM automation_settings WHERE channel_id=$1", [channelId]);
}

export type JobKind = "reaction" | "notify";

/**
 * Idempotent job creation: the UNIQUE dedupe_key guarantees one job per (kind, target)
 * even if the same webhook is delivered twice or two workers race.
 * Returns the job id only if this call created it.
 */
export async function createJobOnce(args: {
  channelId: string; postId: string | null; kind: JobKind; dedupeKey: string; payload?: Record<string, unknown>; maxAttempts?: number;
}): Promise<string | null> {
  const r = await query<{ id: string }>(
    `INSERT INTO automation_jobs (channel_id, post_id, kind, dedupe_key, payload)
     VALUES ($1,$2,$3,$4,$5) ON CONFLICT (dedupe_key) DO NOTHING RETURNING id`,
    [args.channelId, args.postId, args.kind, args.dedupeKey, JSON.stringify({ ...(args.payload ?? {}), maxAttempts: args.maxAttempts })],
  );
  const id = r.rows[0]?.id ?? null;
  if (id) await enqueueJob(id, args.maxAttempts);
  return id;
}

export async function enqueueJob(jobRowId: string, maxAttempts?: number) {
  // jobId = row id → BullMQ also refuses duplicates.
  await queue(QUEUES.actions).add("run", { jobRowId }, { jobId: jobRowId, attempts: (maxAttempts ?? 5) + 1 });
}

/** Re-enqueue jobs that exist in Postgres but were lost from Redis (crash, Redis flush). */
export async function resumePendingJobs(): Promise<number> {
  const r = await query<{ id: string; payload: { maxAttempts?: number } }>(
    `SELECT id, payload FROM automation_jobs WHERE status IN ('pending','running') AND updated_at < now() - interval '2 minutes' LIMIT 200`,
  );
  let n = 0;
  for (const j of r.rows) {
    try {
      const existing = await queue(QUEUES.actions).getJob(j.id);
      if (existing) {
        const st = await existing.getState();
        if (st !== "completed" && st !== "failed") continue;
        await existing.remove().catch(() => {});
      }
      await query("UPDATE automation_jobs SET status='pending', updated_at=now() WHERE id=$1", [j.id]);
      await enqueueJob(j.id, j.payload?.maxAttempts);
      n++;
    } catch (e) {
      log.warn("resume job failed", { id: j.id, error: errMessage(e) });
    }
  }
  return n;
}
