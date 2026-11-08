import { Queue, type JobsOptions } from "bullmq";
import { Redis } from "ioredis";
import { env } from "./env";

export const QUEUES = { updates: "geasy-updates", actions: "geasy-actions", stats: "geasy-stats" } as const;

const g = globalThis as unknown as { __geasyRedis?: Redis; __geasyQueues?: Map<string, Queue> };

/** BullMQ requires maxRetriesPerRequest=null. Reconnects forever with capped backoff. */
export function redisConnection(): Redis {
  if (!g.__geasyRedis) {
    const r = new Redis(env().REDIS_URL, {
      maxRetriesPerRequest: null,
      retryStrategy: (n) => Math.min(n * 500, 10_000),
    });
    r.on("error", () => {}); // reconnect handles it; avoid unhandled 'error' crashing the process
    g.__geasyRedis = r;
  }
  return g.__geasyRedis;
}

export function queue(name: string): Queue {
  g.__geasyQueues ??= new Map();
  let q = g.__geasyQueues.get(name);
  if (!q) {
    q = new Queue(name, {
      connection: redisConnection(),
      defaultJobOptions: {
        attempts: 6,
        backoff: { type: "exponential", delay: 2_000 },
        removeOnComplete: { age: 3600, count: 1000 },
        removeOnFail: { age: 7 * 86400 },
      } satisfies JobsOptions,
    });
    q.on("error", () => {});
    g.__geasyQueues.set(name, q);
  }
  return q;
}

export async function closeQueues() {
  for (const q of g.__geasyQueues?.values() ?? []) await q.close();
  g.__geasyQueues = undefined;
  if (g.__geasyRedis) {
    g.__geasyRedis.disconnect();
    g.__geasyRedis = undefined;
  }
}
