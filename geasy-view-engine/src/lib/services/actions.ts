import { one, query, tx } from "../db";
import { logActivity } from "../activity";
import { requireBot } from "./credentials";
import { TelegramApiError } from "../telegram/bot";
import { buildPostUrl } from "../telegram/url";
import { getSettings } from "./automation";
import { errMessage } from "../logger";

export class RateLimitedError extends Error {
  constructor(public ms: number) {
    super(`rate limited for ${ms}ms`);
  }
}
/** Retrying cannot help (invalid emoji, kicked bot, disabled setting…). */
export class PermanentJobError extends Error {}

type JobRow = {
  id: string; channel_id: string; post_id: string | null; kind: "reaction" | "notify"; status: string; payload: { messageId?: number; emoji?: string; manual?: boolean };
};

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/**
 * Settles a job and refreshes the channel's failure counter in ONE transaction.
 * "Consecutive failures" = failed jobs of a kind since the last successful job of that kind
 * (max over kinds), derived from history so a success of one kind never masks failures of another.
 */
async function finish(id: string, channelId: string, status: "done" | "failed" | "skipped", error?: string) {
  const { n, pause } = await tx(async (c) => {
    // Serialise per channel: jobs of different kinds settle concurrently, and without this lock a transaction
    // that computed its count before the other committed would overwrite the counter with a stale value.
    await c.query("SELECT 1 FROM automation_settings WHERE channel_id=$1 FOR UPDATE", [channelId]);
    await c.query("UPDATE automation_jobs SET status=$2, last_error=$3, finished_at=now(), updated_at=now() WHERE id=$1", [id, status, error ?? null]);
    const r = await c.query<{ n: number }>(
      `SELECT COALESCE(max(x.n), 0)::int AS n FROM (
         SELECT (SELECT count(*) FROM automation_jobs f WHERE f.channel_id=$1 AND f.kind=k.kind AND f.status='failed'
                   AND f.finished_at > COALESCE((SELECT max(d.finished_at) FROM automation_jobs d WHERE d.channel_id=$1 AND d.kind=k.kind AND d.status='done'), '-infinity'::timestamptz)) AS n
         FROM (VALUES ('reaction'),('notify')) AS k(kind)) x`,
      [channelId],
    );
    const u = await c.query<{ pause_after_failures: number }>(
      "UPDATE automation_settings SET consecutive_failures=$2 WHERE channel_id=$1 RETURNING pause_after_failures", [channelId, r.rows[0].n]);
    return { n: r.rows[0].n, pause: u.rows[0]?.pause_after_failures ?? 0 };
  });
  if (status === "failed" && pause > 0 && n >= pause) {
    await query("UPDATE automation_settings SET monitoring_enabled=false, updated_at=now() WHERE channel_id=$1", [channelId]);
    await logActivity({
      level: "error", category: "system", action: "auto_pause", channelId,
      message: `Monitoring paused automatically after ${n} consecutive failures`,
    });
  }
}

/**
 * Executes one persisted job. Safe to call repeatedly: finished jobs are no-ops.
 * `final` = this is the last BullMQ attempt, so a retryable error becomes a permanent failure.
 */
export async function runJob(jobRowId: string, final: boolean): Promise<void> {
  const job = await one<JobRow>("SELECT * FROM automation_jobs WHERE id=$1", [jobRowId]);
  if (!job || job.status === "done" || job.status === "skipped" || job.status === "failed") return;
  await query("UPDATE automation_jobs SET status='running', attempts=attempts+1, updated_at=now() WHERE id=$1", [jobRowId]);

  try {
    const ch = await one<{ id: string; title: string; username: string | null; tg_chat_id: number; status: string; available_reactions: string[] | null }>(
      "SELECT id, title, username, tg_chat_id, status, available_reactions FROM channels WHERE id=$1", [job.channel_id]);
    const s = await getSettings(job.channel_id);
    if (!ch || !s) return finish(jobRowId, job.channel_id, "skipped", "channel removed");
    const { bot, identity } = await requireBot();
    const actor = `bot:@${identity.username ?? identity.id}`;
    const messageId = job.payload.messageId;
    if (!messageId) throw new PermanentJobError("missing message id");

    if (job.kind === "reaction") {
      // Manual jobs come from an explicit click in the dashboard and bypass the per-channel auto-reaction switch.
      if (!job.payload.manual && !s.reaction_enabled) return finish(jobRowId, job.channel_id, "skipped", "reactions disabled for this channel");
      if (ch.status !== "connected") throw new PermanentJobError(`channel is ${ch.status}`);
      const emoji = job.payload.emoji ?? s.reaction_emoji;
      if (ch.available_reactions && !ch.available_reactions.includes(emoji)) {
        await logActivity({ level: "warn", category: "reaction", action: "skipped", channelId: ch.id, postId: job.post_id, actor, message: `Emoji ${emoji} is not allowed in “${ch.title}”` });
        return finish(jobRowId, job.channel_id, "skipped", `emoji ${emoji} not allowed in this channel`);
      }
      await bot.setMessageReaction(ch.tg_chat_id, messageId, emoji);
      await logActivity({ category: "reaction", action: "react", channelId: ch.id, postId: job.post_id, actor, message: `Reacted ${emoji} to post #${messageId} in “${ch.title}”`, meta: { emoji, messageId } });
    } else {
      if (!s.notify_enabled || !s.notify_chat_id) return finish(jobRowId, job.channel_id, "skipped", "notifications disabled");
      const post = job.post_id ? await one<{ text: string | null; media_type: string }>("SELECT text, media_type FROM telegram_posts WHERE id=$1", [job.post_id]) : null;
      const snippet = post?.text ? esc(post.text.slice(0, 200)) + (post.text.length > 200 ? "…" : "") : `<i>${post?.media_type ?? "post"}</i>`;
      const url = buildPostUrl(ch, messageId);
      await bot.sendMessage(s.notify_chat_id, `<b>${esc(ch.title)}</b> · new post\n${snippet}\n${url}`);
      await logActivity({ category: "notify", action: "sent", channelId: ch.id, postId: job.post_id, actor, message: `Notification sent for post #${messageId}`, meta: { destination: s.notify_chat_id } });
    }
    await finish(jobRowId, job.channel_id, "done");
  } catch (e) {
    if (e instanceof TelegramApiError && e.code === 429) {
      await query("UPDATE automation_jobs SET status='pending', last_error=$2, updated_at=now() WHERE id=$1", [jobRowId, errMessage(e)]);
      throw new RateLimitedError(((e.retryAfter ?? 5) + 1) * 1000);
    }
    const permanent = e instanceof PermanentJobError || (e instanceof TelegramApiError && e.permanent);
    const msg = errMessage(e);
    if (permanent || final) {
      await logActivity({ level: "error", category: job.kind === "reaction" ? "reaction" : "notify", action: "failed", channelId: job.channel_id, postId: job.post_id, message: `Job ${job.kind} failed: ${msg}` });
      await finish(jobRowId, job.channel_id, "failed", msg);
      if (permanent) throw new PermanentJobError(msg);
      throw e;
    }
    await query("UPDATE automation_jobs SET status='pending', last_error=$2, updated_at=now() WHERE id=$1", [jobRowId, msg]);
    throw e;
  }
}
