import { query } from "./db";
import { log, errMessage } from "./logger";

export type ActivityInput = {
  level?: "info" | "warn" | "error";
  category: "channel" | "webhook" | "stats" | "reaction" | "notify" | "auth" | "system" | "post";
  action: string;
  message: string;
  channelId?: string | null;
  postId?: string | null;
  actor?: string;
  meta?: Record<string, unknown>;
};

/** Never throws: logging must not break the operation being logged. */
export async function logActivity(a: ActivityInput): Promise<void> {
  const level = a.level ?? "info";
  log[level](a.message, { category: a.category, action: a.action, channelId: a.channelId, ...a.meta });
  try {
    await query(
      `INSERT INTO activity_logs (level, category, action, channel_id, post_id, actor, message, meta)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)`,
      [level, a.category, a.action, a.channelId ?? null, a.postId ?? null, a.actor ?? "system", a.message, JSON.stringify(a.meta ?? {})],
    );
  } catch (e) {
    log.error("activity log write failed", { error: errMessage(e) });
  }
}
