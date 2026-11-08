import fs from "node:fs";
import path from "node:path";
import { pool } from "./db";
import { log } from "./logger";

export async function runMigrations(dir = process.env.MIGRATIONS_DIR ?? path.resolve(process.cwd(), "migrations")) {
  const c = await pool().connect();
  try {
    // Serialise concurrent starters (web + worker).
    await c.query("SELECT pg_advisory_lock(727274)");
    await c.query(
      "CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())",
    );
    const done = new Set((await c.query<{ name: string }>("SELECT name FROM schema_migrations")).rows.map((r) => r.name));
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".sql")).sort();
    const applied: string[] = [];
    for (const f of files) {
      if (done.has(f)) continue;
      const sql = fs.readFileSync(path.join(dir, f), "utf8");
      try {
        await c.query("BEGIN");
        await c.query(sql);
        await c.query("INSERT INTO schema_migrations (name) VALUES ($1)", [f]);
        await c.query("COMMIT");
        applied.push(f);
        log.info("migration applied", { file: f });
      } catch (e) {
        await c.query("ROLLBACK");
        throw new Error(`Migration ${f} failed: ${(e as Error).message}`);
      }
    }
    return applied;
  } finally {
    await c.query("SELECT pg_advisory_unlock(727274)").catch(() => {});
    c.release();
  }
}
