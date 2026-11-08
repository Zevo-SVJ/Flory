import { one, query, tx } from "../db";

export type TgMessage = {
  message_id: number;
  date: number;
  edit_date?: number;
  chat: { id: number };
  text?: string;
  caption?: string;
  media_group_id?: string;
  photo?: unknown[];
  video?: unknown;
  animation?: unknown;
  document?: unknown;
  audio?: unknown;
  voice?: unknown;
  poll?: unknown;
  forward_origin?: { type: string; [k: string]: unknown };
  forward_date?: number;
};

export type MediaType = "text" | "photo" | "video" | "animation" | "document" | "audio" | "voice" | "poll" | "other" | "unknown";

export function mediaTypeOf(m: TgMessage): MediaType {
  if (m.photo) return "photo";
  if (m.video) return "video";
  if (m.animation) return "animation";
  if (m.voice) return "voice";
  if (m.audio) return "audio";
  if (m.document) return "document";
  if (m.poll) return "poll";
  if (m.text !== undefined) return "text";
  return "other";
}

export type Post = {
  id: string;
  channel_id: string;
  message_id: number;
  source: "webhook" | "manual" | "mtproto";
  media_type: MediaType;
  media_group_id: string | null;
  text: string | null;
  is_forwarded: boolean;
  forward_origin: Record<string, unknown> | null;
  is_edited: boolean;
  edited_at: Date | null;
  published_at: Date | null;
  tracking_enabled: boolean;
  last_stats_at: Date | null;
  created_at: Date;
};

/** Safe summary of forward_origin (no need to keep the whole payload). */
function forwardSummary(m: TgMessage) {
  const o = m.forward_origin;
  if (!o) return null;
  const chat = (o as { chat?: { title?: string; username?: string } }).chat;
  const user = (o as { sender_user?: { first_name?: string; username?: string } }).sender_user;
  return {
    type: o.type,
    from: chat?.title ?? chat?.username ?? user?.username ?? user?.first_name ?? (o as { sender_user_name?: string }).sender_user_name ?? null,
  };
}

/** Insert a new post from a webhook. Returns whether the row was newly created (dedupe). */
export async function upsertWebhookPost(channelId: string, m: TgMessage): Promise<{ post: Post; created: boolean }> {
  const fwd = forwardSummary(m);
  const r = await query<Post & { inserted: boolean }>(
    `INSERT INTO telegram_posts (channel_id, message_id, source, media_type, media_group_id, text, is_forwarded, forward_origin, published_at, is_edited, edited_at)
     VALUES ($1,$2,'webhook',$3,$4,$5,$6,$7,to_timestamp($8), $9, CASE WHEN $9 THEN to_timestamp($10) END)
     ON CONFLICT (channel_id, message_id) DO UPDATE SET
       -- a stub created from a URL gets completed; an existing webhook post is left alone
       media_type = CASE WHEN telegram_posts.media_type='unknown' THEN EXCLUDED.media_type ELSE telegram_posts.media_type END,
       media_group_id = COALESCE(telegram_posts.media_group_id, EXCLUDED.media_group_id),
       text = COALESCE(telegram_posts.text, EXCLUDED.text),
       published_at = COALESCE(telegram_posts.published_at, EXCLUDED.published_at),
       is_forwarded = telegram_posts.is_forwarded OR EXCLUDED.is_forwarded,
       forward_origin = COALESCE(telegram_posts.forward_origin, EXCLUDED.forward_origin),
       updated_at = now()
     RETURNING *, (xmax = 0) AS inserted`,
    [channelId, m.message_id, mediaTypeOf(m), m.media_group_id ?? null, m.text ?? m.caption ?? null, !!fwd, fwd ? JSON.stringify(fwd) : null,
     m.date, !!m.edit_date, m.edit_date ?? null],
  );
  const row = r.rows[0];
  return { post: row, created: row.inserted };
}

export async function applyEdit(channelId: string, m: TgMessage): Promise<Post> {
  const fwd = forwardSummary(m);
  // Edits can arrive before the original (out-of-order delivery): create the row then.
  const r = await query<Post>(
    `INSERT INTO telegram_posts (channel_id, message_id, source, media_type, media_group_id, text, is_forwarded, forward_origin, published_at, is_edited, edited_at)
     VALUES ($1,$2,'webhook',$3,$4,$5,$6,$7,to_timestamp($8), true, to_timestamp($9))
     ON CONFLICT (channel_id, message_id) DO UPDATE SET
       text = EXCLUDED.text, is_edited = true, edited_at = EXCLUDED.edited_at, updated_at = now(),
       media_type = CASE WHEN telegram_posts.media_type='unknown' THEN EXCLUDED.media_type ELSE telegram_posts.media_type END
     RETURNING *`,
    [channelId, m.message_id, mediaTypeOf(m), m.media_group_id ?? null, m.text ?? m.caption ?? null, !!fwd, fwd ? JSON.stringify(fwd) : null, m.date, m.edit_date ?? m.date],
  );
  return r.rows[0];
}

/** Mode B: register a post by URL even when its content is not readable through the Bot API. */
export async function ensureManualPost(channelId: string, messageId: number): Promise<Post> {
  const r = await query<Post>(
    `INSERT INTO telegram_posts (channel_id, message_id, source, media_type) VALUES ($1,$2,'manual','unknown')
     ON CONFLICT (channel_id, message_id) DO UPDATE SET tracking_enabled = true, updated_at = now()
     RETURNING *`,
    [channelId, messageId],
  );
  return r.rows[0];
}

export async function getPostByMessage(channelId: string, messageId: number): Promise<Post | null> {
  return one<Post>("SELECT * FROM telegram_posts WHERE channel_id=$1 AND message_id=$2", [channelId, messageId]);
}

export async function getPost(id: string): Promise<Post | null> {
  return one<Post>("SELECT * FROM telegram_posts WHERE id=$1", [id]);
}

export type Metrics = {
  views: number | null;
  forwards: number | null;
  replies: number | null;
  reactions: Record<string, number> | null; // null = this source cannot tell
};

/**
 * Append a snapshot and refresh the "latest reactions" table, atomically.
 * Values the source cannot provide stay NULL: never invented, never carried over.
 */
export async function recordSnapshot(postId: string, source: "bot_api" | "mtproto", m: Metrics) {
  await tx(async (c) => {
    const total = m.reactions ? Object.values(m.reactions).reduce((a, b) => a + b, 0) : null;
    await c.query(
      `INSERT INTO post_statistics (post_id, source, views, forwards, replies, reactions_total, reactions) VALUES ($1,$2,$3,$4,$5,$6,$7)`,
      [postId, source, m.views, m.forwards, m.replies, total, JSON.stringify(m.reactions ?? {})],
    );
    if (m.reactions) {
      const keys = Object.keys(m.reactions);
      await c.query("DELETE FROM post_reactions WHERE post_id=$1 AND NOT (reaction = ANY($2::text[]))", [postId, keys]);
      for (const k of keys) {
        await c.query(
          `INSERT INTO post_reactions (post_id, reaction, count, source) VALUES ($1,$2,$3,$4)
           ON CONFLICT (post_id, reaction) DO UPDATE SET count=$3, source=$4, updated_at=now()`,
          [postId, k, m.reactions[k], source],
        );
      }
    }
    // Only MTProto polls drive the polling schedule; passive Bot API reaction events must not delay them.
    if (source === "mtproto") await c.query("UPDATE telegram_posts SET last_stats_at = now() WHERE id=$1", [postId]);
  });
}
