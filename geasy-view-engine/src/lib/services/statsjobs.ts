import { one, query } from "../db";
import { logActivity } from "../activity";
import { mtproto, mtprotoAvailable, type MtprotoSource } from "../telegram/mtproto";
import { QUEUES, queue } from "../queue";
import { recordSnapshot, type Post } from "./posts";
import { getBot } from "./credentials";
import { log, errMessage } from "../logger";

let override: MtprotoSource | null = null;
/** Test seam: inject a fake MTProto source. */
export function setMtprotoSourceForTests(src: MtprotoSource | null) {
  override = src;
}
export async function metricsSource(): Promise<MtprotoSource | null> {
  if (override) return override;
  return (await mtprotoAvailable()) ? mtproto : null;
}

type ChannelLite = { id: string; tg_chat_id: number; username: string | null };

/** Fetch metrics for posts (≤100) from MTProto and append snapshots. Returns how many were recorded. */
export async function snapshotPosts(ch: ChannelLite, posts: Pick<Post, "id" | "message_id" | "text" | "media_type" | "published_at">[]): Promise<number> {
  const src = await metricsSource();
  if (!src || posts.length === 0) return 0;
  const found = await src.fetchMessages({ chatId: ch.tg_chat_id, username: ch.username }, posts.map((p) => p.message_id));
  let n = 0;
  for (const p of posts) {
    const m = found.get(p.message_id);
    if (!m) {
      // Deleted or not visible to the account: stop polling it (can be re-enabled from Post Manager).
      await query("UPDATE telegram_posts SET tracking_enabled=false, updated_at=now() WHERE id=$1", [p.id]);
      await logActivity({ level: "warn", category: "stats", action: "post_missing", channelId: ch.id, postId: p.id, message: `Post #${p.message_id} not returned by Telegram (deleted or not visible); tracking stopped` });
      continue;
    }
    await recordSnapshot(p.id, "mtproto", { views: m.views, forwards: m.forwards, replies: m.replies, reactions: m.reactions });
    // Complete stubs created from a URL with whatever Telegram returned.
    await query(
      `UPDATE telegram_posts SET
         media_type = CASE WHEN media_type='unknown' THEN $2 ELSE media_type END,
         text = COALESCE(text, $3), published_at = COALESCE(published_at, $4),
         media_group_id = COALESCE(media_group_id, $5), is_forwarded = is_forwarded OR $6
       WHERE id=$1`,
      [p.id, m.mediaType, m.text, m.date, m.groupedId, m.isForwarded],
    );
    n++;
  }
  return n;
}

const DUE_SQL = `
  SELECT p.id, p.message_id, p.text, p.media_type, p.published_at
  FROM telegram_posts p JOIN automation_settings s ON s.channel_id = p.channel_id
  WHERE p.channel_id = $1 AND p.tracking_enabled AND s.monitoring_enabled AND s.stats_enabled
    AND (p.source = 'manual' OR COALESCE(p.published_at, p.created_at) > now() - make_interval(days => s.tracking_days))
    AND (p.last_stats_at IS NULL OR p.last_stats_at <= now() - make_interval(secs => s.monitor_interval_s *
          CASE WHEN COALESCE(p.published_at, p.created_at) > now() - interval '6 hours' THEN 1
               WHEN COALESCE(p.published_at, p.created_at) > now() - interval '48 hours' THEN 4
               ELSE 16 END))
  ORDER BY p.last_stats_at NULLS FIRST
  LIMIT 100`;

export async function snapshotChannel(channelId: string): Promise<number> {
  const ch = await one<ChannelLite & { status: string; title: string }>("SELECT id, tg_chat_id, username, status, title FROM channels WHERE id=$1", [channelId]);
  if (!ch) return 0;
  const due = await query<Pick<Post, "id" | "message_id" | "text" | "media_type" | "published_at">>(DUE_SQL, [channelId]);
  if (due.rowCount === 0) return 0;
  return snapshotPosts(ch, due.rows);
}

/**
 * Runs every minute. Enqueues one snapshot job per channel that has due posts.
 * Adaptive cadence (documented in docs/ARCHITECTURE.md): interval × 1 for posts < 6 h old, × 4 < 48 h, × 16 afterwards.
 */
export async function statsTick(): Promise<{ channels: number }> {
  const src = await metricsSource();
  const bucket = Math.floor(Date.now() / 60_000);
  let channels = 0;
  if (src) {
    const r = await query<{ channel_id: string }>(
      `SELECT DISTINCT s.channel_id FROM automation_settings s JOIN channels c ON c.id=s.channel_id
       WHERE s.monitoring_enabled AND s.stats_enabled AND c.status IN ('connected','no_access','error')`,
    );
    for (const row of r.rows) {
      const due = await query("SELECT 1 FROM (" + DUE_SQL + ") d LIMIT 1", [row.channel_id]);
      if (due.rowCount) {
        await queue(QUEUES.stats).add("snapshot-channel", { channelId: row.channel_id }, { jobId: `snap-${row.channel_id}-${bucket}`, attempts: 4 });
        channels++;
      }
    }
  }
  await refreshSubscribers();
  return { channels };
}

/** Hourly member count via Bot API (official). */
export async function refreshSubscribers() {
  const b = await getBot();
  if (!b) return;
  const r = await query<{ id: string; tg_chat_id: number }>(
    `SELECT c.id, c.tg_chat_id FROM channels c JOIN automation_settings s ON s.channel_id=c.id
     WHERE s.monitoring_enabled AND c.status='connected' AND (c.subscribers_checked_at IS NULL OR c.subscribers_checked_at < now() - interval '1 hour')`,
  );
  for (const c of r.rows) {
    try {
      const n = await b.bot.getChatMemberCount(c.tg_chat_id);
      await query("UPDATE channels SET subscriber_count=$2, subscribers_checked_at=now() WHERE id=$1", [c.id, n]);
      await query("INSERT INTO channel_stats (channel_id, subscribers) VALUES ($1,$2)", [c.id, n]);
    } catch (e) {
      log.warn("member count failed", { channelId: c.id, error: errMessage(e) });
    }
  }
}
