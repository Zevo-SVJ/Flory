import { one, query } from "./db";
import { env, inlineMode } from "./env";
import { runMigrations } from "./migrate";
import { hashPassword } from "./password";
import { installScheduler } from "./services/scheduler";
import { logActivity } from "./activity";
import { errMessage, log } from "./logger";

let started: Promise<void> | null = null;

/**
 * Zero-touch first start (serverless): migrate, create the admin from ADMIN_EMAIL/ADMIN_PASSWORD if no user exists,
 * and register the pg_cron scheduler. Runs once per instance; every step is idempotent and failures are logged, not fatal.
 */
export function ensureReady(): Promise<void> {
  started ??= (async () => {
    try {
      await runMigrations();
    } catch (e) {
      log.error("migrations failed", { error: errMessage(e) });
      started = null; // retry on next call
      return;
    }
    try {
      const email = process.env.ADMIN_EMAIL?.trim();
      const password = process.env.ADMIN_PASSWORD;
      if (email && password && password.length >= 12) {
        const n = await one<{ n: number }>("SELECT count(*)::int AS n FROM users");
        if (n && n.n === 0) {
          await query("INSERT INTO users (email, password_hash) VALUES ($1,$2) ON CONFLICT DO NOTHING", [email, await hashPassword(password)]);
          await logActivity({ category: "system", action: "admin_created", message: `Admin account created for ${email}` });
        }
      }
    } catch (e) {
      log.error("admin bootstrap failed", { error: errMessage(e) });
    }
    if (inlineMode()) {
      const r = await installScheduler();
      if (!r.ok) {
        await logActivity({ level: "warn", category: "system", action: "scheduler_failed", message: `Scheduler not installed: ${r.error}. Enable pg_cron and pg_net in Supabase → Database → Extensions, then open Settings → Scheduler.` });
      } else if (r.changed) {
        await logActivity({ category: "system", action: "scheduler_installed", message: `Scheduler installed (pg_cron → ${env().PUBLIC_BASE_URL}/api/cron/tick every minute)` });
      }
    }
  })();
  return started;
}
