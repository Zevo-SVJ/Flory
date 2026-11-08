import { one, query } from "../db";
import { logActivity } from "../activity";

export type RetentionPolicy = {
  webhook_events_days: number; activity_logs_days: number; stats_full_days: number; stats_downsample_to_daily: boolean;
};

export async function getRetention(): Promise<RetentionPolicy> {
  return (await one<RetentionPolicy>("SELECT * FROM retention_policy"))!;
}

/** Daily: purge old events/logs/sessions and downsample old snapshots to one per day per post. */
export async function runRetention() {
  const p = await getRetention();
  const ev = await query("DELETE FROM webhook_events WHERE status <> 'pending' AND received_at < now() - make_interval(days => $1)", [p.webhook_events_days]);
  const lg = await query("DELETE FROM activity_logs WHERE created_at < now() - make_interval(days => $1)", [p.activity_logs_days]);
  const ss = await query("DELETE FROM sessions WHERE expires_at < now()");
  const la = await query("DELETE FROM login_attempts WHERE attempted_at < now() - interval '1 day'");
  let down = 0;
  if (p.stats_downsample_to_daily) {
    const r = await query(
      `DELETE FROM post_statistics s USING (
         SELECT id, row_number() OVER (PARTITION BY post_id, date_trunc('day', captured_at) ORDER BY captured_at DESC) AS rn
         FROM post_statistics WHERE captured_at < now() - make_interval(days => $1)
       ) d WHERE s.id = d.id AND d.rn > 1`,
      [p.stats_full_days],
    );
    down = r.rowCount ?? 0;
  }
  const summary = { events: ev.rowCount, logs: lg.rowCount, sessions: ss.rowCount, loginAttempts: la.rowCount, snapshotsDownsampled: down };
  await logActivity({ category: "system", action: "retention", message: "Retention policy applied", meta: summary });
  return summary;
}
