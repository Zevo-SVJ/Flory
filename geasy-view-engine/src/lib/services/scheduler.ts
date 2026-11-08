import { one, query } from "../db";
import { env } from "../env";
import { errMessage } from "../logger";

const JOB = "geasy-tick";

function tickUrl() {
  return `${env().PUBLIC_BASE_URL.replace(/\/$/, "")}/api/cron/tick`;
}

/**
 * Registers a Supabase pg_cron job that calls /api/cron/tick every minute (through pg_net).
 * Idempotent: re-running with the same URL/secret changes nothing; a new URL/secret updates the job.
 * Needs the pg_cron and pg_net extensions (enabled in Supabase → Database → Extensions).
 */
export async function installScheduler(): Promise<{ ok: true; changed: boolean } | { ok: false; error: string }> {
  try {
    await query("CREATE EXTENSION IF NOT EXISTS pg_cron");
    await query("CREATE EXTENSION IF NOT EXISTS pg_net");
    const cmd = (
      await one<{ cmd: string }>(
        `SELECT format($f$ SELECT net.http_post(url := %L, headers := jsonb_build_object('Authorization', %L, 'Content-Type', 'application/json'), body := '{}'::jsonb, timeout_milliseconds := 5000) $f$, $1::text, $2::text) AS cmd`,
        [tickUrl(), `Bearer ${env().CRON_SECRET}`],
      )
    )!.cmd;
    const existing = await one<{ command: string }>("SELECT command FROM cron.job WHERE jobname = $1", [JOB]);
    if (existing?.command === cmd) return { ok: true, changed: false };
    await query("SELECT cron.schedule($1, '* * * * *', $2)", [JOB, cmd]);
    return { ok: true, changed: true };
  } catch (e) {
    return { ok: false, error: errMessage(e) };
  }
}

export async function getSchedulerStatus(): Promise<{ installed: boolean; lastTick: Date | null; detail?: string }> {
  const last = await one<{ updated_at: Date }>("SELECT updated_at FROM system_state WHERE key='last_tick'");
  let installed = false;
  let detail: string | undefined;
  try {
    installed = !!(await one("SELECT 1 FROM cron.job WHERE jobname=$1 AND active", [JOB]));
  } catch (e) {
    detail = errMessage(e);
  }
  return { installed, lastTick: last?.updated_at ?? null, detail };
}
