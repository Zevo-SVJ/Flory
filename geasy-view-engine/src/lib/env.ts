import { createHmac } from "node:crypto";
import { z } from "zod";

const schema = z.object({
  DATABASE_URL: z.string().min(1),
  /** Optional extra PEM CA for the database TLS connection (verification stays ON). */
  DATABASE_CA_CERT: z.string().optional(),
  REDIS_URL: z.string().min(1).default("redis://127.0.0.1:6379"),
  // Optional: when absent, derived from DATABASE_URL (see derive()).
  ENCRYPTION_KEY: z.string().regex(/^[0-9a-fA-F]{64}$/, "ENCRYPTION_KEY must be 64 hex chars (openssl rand -hex 32)").optional(),
  CRON_SECRET: z.string().min(16).optional(),
  PUBLIC_BASE_URL: z.string().url().optional(),
  TELEGRAM_API_BASE: z.string().url().default("https://api.telegram.org"),
  WORKER_URL: z.string().url().default("http://127.0.0.1:4000"),
  WORKER_PORT: z.coerce.number().int().default(4000),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

export type Env = Omit<z.infer<typeof schema>, "ENCRYPTION_KEY" | "CRON_SECRET" | "PUBLIC_BASE_URL"> & {
  ENCRYPTION_KEY: string;
  CRON_SECRET: string;
  PUBLIC_BASE_URL: string;
};

let cached: Env | null = null;

/**
 * Serverless deployments (Vercel) have no durable place for generated secrets, so when
 * ENCRYPTION_KEY / CRON_SECRET are not provided they are derived (HMAC-SHA256) from DATABASE_URL.
 * Anyone holding DATABASE_URL can already read the database, so this adds no new exposure;
 * the cost is that rotating the database password makes stored tokens undecryptable (re-enter them).
 */
const derive = (label: string, url: string) => createHmac("sha256", `geasy:${label}:v1`).update(url).digest("hex");

/** Lazily validated so `next build` does not need runtime secrets. */
export function env(): Env {
  if (cached) return cached;
  const parsed = schema.safeParse(process.env);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`Invalid environment: ${msg}`);
  }
  const p = parsed.data;
  const vercelUrl = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  cached = {
    ...p,
    ENCRYPTION_KEY: p.ENCRYPTION_KEY ?? derive("enc", p.DATABASE_URL),
    CRON_SECRET: p.CRON_SECRET ?? derive("cron", p.DATABASE_URL),
    PUBLIC_BASE_URL: p.PUBLIC_BASE_URL ?? (vercelUrl ? `https://${vercelUrl}` : "http://localhost:3000"),
  };
  return cached;
}

export function resetEnvCache() {
  cached = null;
}

/**
 * "inline" = no Redis/worker: events and jobs run inside the request that received them
 * (after the HTTP response), and a scheduler (pg_cron) calls /api/cron/tick to retry and sweep.
 * Default on Vercel; set QUEUE_MODE=inline to force it, QUEUE_MODE=bullmq to force the worker mode.
 */
export function inlineMode(): boolean {
  const m = process.env.QUEUE_MODE;
  if (m) return m === "inline";
  return !!process.env.VERCEL;
}
