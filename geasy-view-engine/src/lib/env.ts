import { z } from "zod";

const schema = z.object({
  DATABASE_URL: z.string().min(1),
  REDIS_URL: z.string().min(1).default("redis://127.0.0.1:6379"),
  ENCRYPTION_KEY: z
    .string()
    .regex(/^[0-9a-fA-F]{64}$/, "ENCRYPTION_KEY must be 64 hex chars (openssl rand -hex 32)"),
  PUBLIC_BASE_URL: z.string().url().default("http://localhost:3000"),
  TELEGRAM_API_BASE: z.string().url().default("https://api.telegram.org"),
  WORKER_URL: z.string().url().default("http://127.0.0.1:4000"),
  WORKER_PORT: z.coerce.number().int().default(4000),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

export type Env = z.infer<typeof schema>;

let cached: Env | null = null;

/** Lazily validated so `next build` does not need runtime secrets. */
export function env(): Env {
  if (cached) return cached;
  const parsed = schema.safeParse(process.env);
  if (!parsed.success) {
    const msg = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new Error(`Invalid environment: ${msg}`);
  }
  cached = parsed.data;
  return cached;
}

export function resetEnvCache() {
  cached = null;
}
