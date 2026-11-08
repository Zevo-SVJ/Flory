import { one, query } from "../db";
import { logActivity } from "../activity";
import { applyEdit, getPostByMessage, recordSnapshot, upsertWebhookPost, type TgMessage } from "./posts";
import { createJobOnce, getSettings } from "./automation";
import { QUEUES, queue } from "../queue";
import { mtprotoAvailable } from "../telegram/mtproto";
import { getWebhookSecret } from "./credentials";
import { safeEqual } from "../crypto";
import { log, errMessage } from "../logger";
import { inlineMode } from "../env";

export type TgUpdate = {
  update_id: number;
  channel_post?: TgMessage;
  edited_channel_post?: TgMessage;
  message_reaction_count?: {
    chat: { id: number };
    message_id: number;
    reactions: Array<{ type: { type: string; emoji?: string; custom_emoji_id?: string }; total_count: number }>;
  };
  my_chat_member?: { chat: { id: number; type: string; title?: string }; new_chat_member: { status: string } };
};

const UPDATE_TYPES = ["channel_post", "edited_channel_post", "message_reaction_count", "my_chat_member"] as const;

export function updateTypeOf(u: TgUpdate): string {
  return UPDATE_TYPES.find((t) => u[t] !== undefined) ?? "other";
}

/**
 * Persist-then-enqueue. The row is the source of truth: if Redis is down the sweeper
 * re-enqueues it later; if the DB is down we throw so the HTTP layer answers 503 and Telegram retries.
 */
export async function ingestUpdate(u: TgUpdate): Promise<{ duplicate: boolean; eventId: number | null }> {
  const r = await query(
    `INSERT INTO webhook_events (update_id, update_type, payload) VALUES ($1,$2,$3)
     ON CONFLICT (update_id) DO NOTHING RETURNING id`,
    [u.update_id, updateTypeOf(u), JSON.stringify(u)],
  );
  if (r.rowCount === 0) return { duplicate: true, eventId: null };
  const eventId = r.rows[0].id as number;
  // Inline mode has no queue: the caller processes the event right after answering Telegram.
  if (inlineMode()) return { duplicate: false, eventId };
  try {
    await enqueueEvent(eventId);
  } catch (e) {
    log.warn("enqueue failed, sweeper will retry", { updateId: u.update_id, error: errMessage(e) });
  }
  return { duplicate: false, eventId };
}

export async function enqueueEvent(eventId: number) {
  await queue(QUEUES.updates).add("update", { eventId }, { jobId: `evt-${eventId}`, attempts: 8 });
}

/** Re-enqueue persisted events that never got processed (Redis outage, crash between insert and enqueue). */
export const MAX_EVENT_ATTEMPTS = 8;

/**
 * Re-process persisted events that were never completed (Redis outage / crash, or in inline mode a failed attempt).
 * Inline mode: exponential backoff 15 s × 2^attempts (capped 1 h) using last_attempt_at; gives up after MAX_EVENT_ATTEMPTS.
 */
export async function sweepPendingEvents(limit = 500): Promise<number> {
  if (inlineMode()) {
    await query("UPDATE webhook_events SET status='failed', error=COALESCE(error,'gave up after max attempts') WHERE status='pending' AND attempts >= $1", [MAX_EVENT_ATTEMPTS]);
    const r = await query<{ id: number }>(
      `SELECT id FROM webhook_events
       WHERE status='pending' AND attempts < $1
         AND ( (last_attempt_at IS NULL AND received_at < now() - interval '20 seconds')
            OR last_attempt_at < now() - make_interval(secs => LEAST(3600, 15 * power(2, attempts))) )
       ORDER BY id LIMIT $2`,
      [MAX_EVENT_ATTEMPTS, Math.min(limit, 30)],
    );
    let n = 0;
    for (const row of r.rows) {
      try { await processWebhookEvent(row.id); n++; } catch (e) { log.warn("event retry failed", { id: row.id, error: errMessage(e) }); }
    }
    return n;
  }
  const r = await query<{ id: number }>(
    `SELECT id FROM webhook_events WHERE status='pending' AND received_at < now() - interval '30 seconds' ORDER BY id LIMIT $1`, [limit],
  );
  let n = 0;
  for (const row of r.rows) {
    const q = queue(QUEUES.updates);
    const j = await q.getJob(`evt-${row.id}`);
    if (j) {
      const st = await j.getState();
      if (st !== "completed" && st !== "failed") continue;
      await j.remove().catch(() => {});
    }
    await enqueueEvent(row.id);
    n++;
  }
  return n;
}

export async function verifyWebhookRequest(pathToken: string, headerSecret: string | undefined, expectedPathToken: (s: string) => string) {
  const secret = await getWebhookSecret();
  if (!secret || !headerSecret) return false;
  return safeEqual(headerSecret, secret) && safeEqual(pathToken, expectedPathToken(secret));
}

async function markEvent(id: number, status: "processed" | "ignored", note?: string) {
  await query("UPDATE webhook_events SET status=$2, processed_at=now(), error=$3 WHERE id=$1", [id, status, note ?? null]);
}

type ChannelRow = { id: string; title: string; username: string | null; status: string; tg_chat_id: number };

async function channelByChat(chatId: number) {
  return one<ChannelRow>("SELECT id, title, username, status, tg_chat_id FROM channels WHERE tg_chat_id=$1", [chatId]);
}

export async function processWebhookEvent(eventId: number): Promise<void> {
  const ev = await one<{ id: number; payload: TgUpdate; status: string }>("SELECT id, payload, status FROM webhook_events WHERE id=$1", [eventId]);
  if (!ev || ev.status !== "pending" && ev.status !== "failed") return; // already handled: idempotent
  await query("UPDATE webhook_events SET attempts = attempts + 1, last_attempt_at = now() WHERE id=$1", [eventId]);
  const u = ev.payload;

  if (u.channel_post) return handleChannelPost(eventId, u.channel_post);
  if (u.edited_channel_post) return handleEdit(eventId, u.edited_channel_post);
  if (u.message_reaction_count) return handleReactionCount(eventId, u.message_reaction_count);
  if (u.my_chat_member) return handleMyChatMember(eventId, u.my_chat_member);
  await markEvent(eventId, "ignored", "unsupported update type");
}

async function handleChannelPost(eventId: number, m: TgMessage) {
  const ch = await channelByChat(m.chat.id);
  if (!ch) return markEvent(eventId, "ignored", "channel not registered");
  const s = await getSettings(ch.id);
  if (!s?.monitoring_enabled) return markEvent(eventId, "ignored", "monitoring disabled");

  const { post, created } = await upsertWebhookPost(ch.id, m);
  if (ch.status !== "connected") {
    await query("UPDATE channels SET status='connected', status_detail=NULL, status_changed_at=now() WHERE id=$1", [ch.id]);
  }
  if (!created) return markEvent(eventId, "ignored", "duplicate post");

  await logActivity({
    category: "webhook", action: "post_detected", channelId: ch.id, postId: post.id,
    message: `New ${post.media_type} post #${m.message_id} in “${ch.title}”${post.is_forwarded ? " (forwarded)" : ""}`,
    meta: { messageId: m.message_id, mediaGroupId: m.media_group_id ?? null },
  });

  // Albums arrive as N separate channel_post updates sharing a media_group_id: act once per album.
  const target = m.media_group_id ? `g:${m.media_group_id}` : `m:${m.message_id}`;

  if (s.stats_enabled && !inlineMode() && (await mtprotoAvailable())) {
    await queue(QUEUES.stats).add("snapshot-channel", { channelId: ch.id }, { jobId: `snap-new-${post.id}`, delay: 3000, attempts: 5 });
  }
  if (s.reaction_enabled) {
    await createJobOnce({
      channelId: ch.id, postId: post.id, kind: "reaction", dedupeKey: `reaction:${ch.tg_chat_id}:${target}`,
      payload: { messageId: m.message_id }, maxAttempts: s.max_retries,
    });
  }
  if (s.notify_enabled && s.notify_chat_id) {
    await createJobOnce({
      channelId: ch.id, postId: post.id, kind: "notify", dedupeKey: `notify:${ch.tg_chat_id}:${target}`,
      payload: { messageId: m.message_id }, maxAttempts: s.max_retries,
    });
  }
  await markEvent(eventId, "processed");
}

async function handleEdit(eventId: number, m: TgMessage) {
  const ch = await channelByChat(m.chat.id);
  if (!ch) return markEvent(eventId, "ignored", "channel not registered");
  const s = await getSettings(ch.id);
  if (!s?.monitoring_enabled) return markEvent(eventId, "ignored", "monitoring disabled");
  const post = await applyEdit(ch.id, m);
  await logActivity({ category: "webhook", action: "post_edited", channelId: ch.id, postId: post.id, message: `Post #${m.message_id} edited in “${ch.title}”` });
  await markEvent(eventId, "processed");
}

async function handleReactionCount(eventId: number, r: NonNullable<TgUpdate["message_reaction_count"]>) {
  const ch = await channelByChat(r.chat.id);
  if (!ch) return markEvent(eventId, "ignored", "channel not registered");
  const post = await getPostByMessage(ch.id, r.message_id);
  if (!post) return markEvent(eventId, "ignored", "post not tracked");
  const reactions: Record<string, number> = {};
  for (const x of r.reactions) {
    const key = x.type.type === "emoji" ? x.type.emoji! : x.type.type === "custom_emoji" ? `custom:${x.type.custom_emoji_id}` : "paid";
    reactions[key] = (reactions[key] ?? 0) + x.total_count;
  }
  await recordSnapshot(post.id, "bot_api", { views: null, forwards: null, replies: null, reactions });
  await markEvent(eventId, "processed");
}

async function handleMyChatMember(eventId: number, c: NonNullable<TgUpdate["my_chat_member"]>) {
  const ch = await channelByChat(c.chat.id);
  if (!ch) return markEvent(eventId, "ignored", "channel not registered");
  const st = c.new_chat_member.status;
  const next = st === "administrator" || st === "creator" ? "connected" : st === "left" || st === "kicked" ? "disconnected" : "no_access";
  const detail = next === "connected" ? null : `Bot status changed to “${st}”`;
  await query("UPDATE channels SET status=$2, status_detail=$3, status_changed_at=now(), updated_at=now() WHERE id=$1", [ch.id, next, detail]);
  await logActivity({ level: next === "connected" ? "info" : "warn", category: "channel", action: "bot_status", channelId: ch.id, message: `Bot is now “${st}” in “${ch.title}”` });
  await markEvent(eventId, "processed");
}
