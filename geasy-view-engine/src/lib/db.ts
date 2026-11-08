import pg from "pg";
import { env } from "./env";
import { log, errMessage } from "./logger";

// bigint/bigserial → number. Telegram chat ids (~-1e12) are far below 2^53.
pg.types.setTypeParser(20, (v) => Number(v));

const g = globalThis as unknown as { __geasyPool?: pg.Pool };

export function pool(): pg.Pool {
  if (!g.__geasyPool) {
    const p = new pg.Pool({
      connectionString: env().DATABASE_URL,
      max: 10,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 5_000,
    });
    // An idle client dying (DB restart) must not crash the process.
    p.on("error", (e) => log.warn("pg idle client error", { error: errMessage(e) }));
    g.__geasyPool = p;
  }
  return g.__geasyPool;
}

const TRANSIENT_CODES = new Set([
  "ECONNREFUSED", "ECONNRESET", "ETIMEDOUT", "EPIPE", "57P01", "57P02", "57P03", "53300", "08000", "08003", "08006",
]);

function isTransient(e: unknown): boolean {
  const code = (e as { code?: string })?.code;
  if (code && TRANSIENT_CODES.has(code)) return true;
  const msg = errMessage(e);
  return /Connection terminated|timeout exceeded when trying to connect|the database system is (starting up|shutting down)/i.test(msg);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Query with retry/backoff for transient connection failures (temporary DB outage). */
export async function query<T extends pg.QueryResultRow = pg.QueryResultRow>(
  text: string,
  params: unknown[] = [],
): Promise<pg.QueryResult<T>> {
  let attempt = 0;
  for (;;) {
    try {
      return await pool().query<T>(text, params);
    } catch (e) {
      attempt++;
      if (!isTransient(e) || attempt >= 4) throw e;
      const delay = 250 * 2 ** (attempt - 1);
      log.warn("db transient error, retrying", { attempt, delay, error: errMessage(e) });
      await sleep(delay);
    }
  }
}

export async function one<T extends pg.QueryResultRow = pg.QueryResultRow>(text: string, params: unknown[] = []): Promise<T | null> {
  const r = await query<T>(text, params);
  return r.rows[0] ?? null;
}

export async function tx<T>(fn: (c: pg.PoolClient) => Promise<T>): Promise<T> {
  const c = await pool().connect();
  try {
    await c.query("BEGIN");
    const r = await fn(c);
    await c.query("COMMIT");
    return r;
  } catch (e) {
    await c.query("ROLLBACK").catch(() => {});
    throw e;
  } finally {
    c.release();
  }
}

export async function closePool() {
  if (g.__geasyPool) {
    await g.__geasyPool.end();
    g.__geasyPool = undefined;
  }
}
