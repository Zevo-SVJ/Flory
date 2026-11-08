import { query } from "../db";

/** Latest snapshot per post that actually carries MTProto data (views), plus latest reactions regardless of source. */
const LATEST = `
  SELECT p.id, p.channel_id, p.message_id, p.media_type, p.text, p.published_at, p.is_forwarded, p.is_edited, p.source,
         v.views, v.forwards, v.replies, v.captured_at AS stats_at,
         COALESCE((SELECT sum(count)::int FROM post_reactions r WHERE r.post_id=p.id), 0) AS reactions_total
  FROM telegram_posts p
  LEFT JOIN LATERAL (
    SELECT views, forwards, replies, captured_at FROM post_statistics s
    WHERE s.post_id = p.id AND s.source = 'mtproto' ORDER BY captured_at DESC LIMIT 1
  ) v ON true`;

export type PostRow = {
  id: string; channel_id: string; message_id: number; media_type: string; text: string | null; published_at: Date | null;
  is_forwarded: boolean; is_edited: boolean; source: string; views: number | null; forwards: number | null; replies: number | null;
  stats_at: Date | null; reactions_total: number;
};

export async function listPosts(opts: { channelId?: string; limit?: number; offset?: number } = {}) {
  const r = await query<PostRow & { channel_title: string; channel_username: string | null; tg_chat_id: number }>(
    `SELECT l.*, c.title AS channel_title, c.username AS channel_username, c.tg_chat_id
     FROM (${LATEST}) l JOIN channels c ON c.id = l.channel_id
     WHERE ($1::uuid IS NULL OR l.channel_id = $1)
     ORDER BY COALESCE(l.published_at, (SELECT created_at FROM telegram_posts t WHERE t.id=l.id)) DESC
     LIMIT $2 OFFSET $3`,
    [opts.channelId ?? null, opts.limit ?? 50, opts.offset ?? 0],
  );
  return r.rows;
}

export async function postSeries(postId: string) {
  const r = await query<{ captured_at: Date; source: string; views: number | null; forwards: number | null; replies: number | null; reactions_total: number | null; reactions: Record<string, number> }>(
    "SELECT captured_at, source, views, forwards, replies, reactions_total, reactions FROM post_statistics WHERE post_id=$1 ORDER BY captured_at",
    [postId],
  );
  return r.rows;
}

export async function postReactions(postId: string) {
  const r = await query<{ reaction: string; count: number; source: string; updated_at: Date }>(
    "SELECT reaction, count, source, updated_at FROM post_reactions WHERE post_id=$1 ORDER BY count DESC", [postId]);
  return r.rows;
}

/** Per-channel aggregates over posts that have real view data. avg_* are calculated from stored snapshots, not Telegram metrics. */
export async function channelPerformance(days = 30) {
  const r = await query<{
    channel_id: string; title: string; posts: number; posts_with_views: number; avg_views: number | null; avg_reactions: number | null; avg_forwards: number | null; total_views: number | null;
  }>(
    `SELECT c.id AS channel_id, c.title,
            count(l.id)::int AS posts,
            count(l.views)::int AS posts_with_views,
            round(avg(l.views))::int AS avg_views,
            round(avg(l.reactions_total), 1)::float AS avg_reactions,
            round(avg(l.forwards), 1)::float AS avg_forwards,
            sum(l.views)::int AS total_views
     FROM channels c
     LEFT JOIN (${LATEST}) l ON l.channel_id = c.id AND COALESCE(l.published_at, now()) > now() - make_interval(days => $1)
     GROUP BY c.id, c.title ORDER BY c.created_at`,
    [days],
  );
  return r.rows;
}

export async function reactionTotalsOverTime(channelId: string | null, days = 14) {
  const r = await query<{ day: Date; total: number }>(
    `SELECT date_trunc('day', s.captured_at) AS day, sum(last_total)::int AS total FROM (
       SELECT DISTINCT ON (s.post_id, date_trunc('day', s.captured_at)) s.post_id, s.captured_at, s.reactions_total AS last_total
       FROM post_statistics s JOIN telegram_posts p ON p.id = s.post_id
       WHERE s.reactions_total IS NOT NULL AND s.captured_at > now() - make_interval(days => $2) AND ($1::uuid IS NULL OR p.channel_id = $1)
       ORDER BY s.post_id, date_trunc('day', s.captured_at), s.captured_at DESC
     ) s GROUP BY 1 ORDER BY 1`,
    [channelId, days],
  );
  return r.rows;
}

export async function subscriberSeries(channelId: string) {
  const r = await query<{ captured_at: Date; subscribers: number }>(
    "SELECT captured_at, subscribers FROM channel_stats WHERE channel_id=$1 ORDER BY captured_at", [channelId]);
  return r.rows;
}

export async function overviewCounts() {
  const r = await query<{ channels: number; connected: number; posts_24h: number; posts_total: number; jobs_failed_24h: number; events_pending: number; reactions_done_24h: number }>(
    `SELECT (SELECT count(*)::int FROM channels) AS channels,
            (SELECT count(*)::int FROM channels WHERE status='connected') AS connected,
            (SELECT count(*)::int FROM telegram_posts WHERE created_at > now() - interval '24 hours') AS posts_24h,
            (SELECT count(*)::int FROM telegram_posts) AS posts_total,
            (SELECT count(*)::int FROM automation_jobs WHERE status='failed' AND updated_at > now() - interval '24 hours') AS jobs_failed_24h,
            (SELECT count(*)::int FROM webhook_events WHERE status='pending') AS events_pending,
            (SELECT count(*)::int FROM automation_jobs WHERE kind='reaction' AND status='done' AND finished_at > now() - interval '24 hours') AS reactions_done_24h`,
  );
  return r.rows[0];
}

/** Sum over posts of the last MTProto views snapshot of each day: total views of tracked posts, day by day. */
export async function viewsTotalsOverTime(channelId: string | null, days = 14) {
  const r = await query<{ day: Date; total: number }>(
    `SELECT day, sum(v)::int AS total FROM (
       SELECT DISTINCT ON (s.post_id, date_trunc('day', s.captured_at)) date_trunc('day', s.captured_at) AS day, s.views AS v
       FROM post_statistics s JOIN telegram_posts p ON p.id = s.post_id
       WHERE s.source='mtproto' AND s.views IS NOT NULL AND s.captured_at > now() - make_interval(days => $2) AND ($1::uuid IS NULL OR p.channel_id = $1)
       ORDER BY s.post_id, date_trunc('day', s.captured_at), s.captured_at DESC
     ) x GROUP BY day ORDER BY day`,
    [channelId, days],
  );
  return r.rows;
}

export async function topPosts(channelId: string | null, limit = 10, days = 30) {
  const r = await query<PostRow & { channel_title: string }>(
    `SELECT l.*, c.title AS channel_title FROM (${LATEST}) l JOIN channels c ON c.id=l.channel_id
     WHERE l.views IS NOT NULL AND ($1::uuid IS NULL OR l.channel_id=$1) AND COALESCE(l.published_at, now()) > now() - make_interval(days => $3)
     ORDER BY l.views DESC LIMIT $2`,
    [channelId, limit, days],
  );
  return r.rows;
}
