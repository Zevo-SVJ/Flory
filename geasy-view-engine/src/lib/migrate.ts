import fs from "node:fs";
import path from "node:path";
import { pool } from "./db";
import { log } from "./logger";
import { BUNDLED_MIGRATIONS } from "./migrations-bundled";

export async function runMigrations(dir = process.env.MIGRATIONS_DIR ?? path.resolve(process.cwd(), "migrations")) {
  const c = await pool().connect();
  try {
    // Serialise concurrent starters (web + worker).
    await c.query("SELECT pg_advisory_lock(727274)");
    await c.query(
      "CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())",
    );
    const done = new Set((await c.query<{ name: string }>("SELECT name FROM schema_migrations")).rows.map((r) => r.name));
    // Prefer the migrations directory (Docker); fall back to the bundled copy (serverless, no usable filesystem).
    const list: Array<{ name: string; sql: string }> = fs.existsSync(dir)
      ? fs.readdirSync(dir).filter((f) => f.endsWith(".sql")).sort().map((f) => ({ name: f, sql: fs.readFileSync(path.join(dir, f), "utf8") }))
      : BUNDLED_MIGRATIONS;
    const applied: string[] = [];
    for (const { name: f, sql } of list) {
      if (done.has(f)) continue;
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
