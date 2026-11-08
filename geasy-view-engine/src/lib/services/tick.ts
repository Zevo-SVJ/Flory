import { one, pool, query } from "../db";
import { resumePendingJobs } from "./automation";
import { refreshSubscribers } from "./statsjobs";
import { runRetention } from "./maintenance";
import { sweepPendingEvents } from "./updates";

/** One scheduler pass (every minute in serverless mode). Overlap-safe via a session advisory lock. */
export async function runTick() {
  const c = await pool().connect();
  try {
    const got = (await c.query<{ ok: boolean }>("SELECT pg_try_advisory_lock(727275) AS ok")).rows[0].ok;
    if (!got) return { skipped: true as const };
    const events = await sweepPendingEvents();
    const jobs = await resumePendingJobs();
    await refreshSubscribers();
    let retention = false;
    const last = await one<{ age_h: number | null }>("SELECT extract(epoch FROM now() - updated_at)/3600 AS age_h FROM system_state WHERE key='last_retention'");
    if (!last || (last.age_h ?? 99) > 23) {
      await runRetention();
      await query("INSERT INTO system_state (key) VALUES ('last_retention') ON CONFLICT (key) DO UPDATE SET updated_at=now()");
      retention = true;
    }
    await query("INSERT INTO system_state (key, value) VALUES ('last_tick', $1) ON CONFLICT (key) DO UPDATE SET value=$1, updated_at=now()", [JSON.stringify({ events, jobs })]);
    return { skipped: false as const, events, jobs, retention };
  } finally {
    await c.query("SELECT pg_advisory_unlock(727275)").catch(() => {});
    c.release();
  }
}
