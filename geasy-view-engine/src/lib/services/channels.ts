import { one, query, tx } from "../db";
import { logActivity } from "../activity";
import { requireBot } from "./credentials";
import { chatIdFromInternal, parseTelegramRef, TelegramRefError, type ChannelRef } from "../telegram/url";
import { TelegramApiError, type TgChat } from "../telegram/bot";

export type ChannelStatus = "pending" | "connected" | "no_access" | "disconnected" | "error";

export type Channel = {
  id: string;
  tg_chat_id: number;
  username: string | null;
  title: string;
  photo_file_id: string | null;
  subscriber_count: number | null;
  subscribers_checked_at: Date | null;
  is_private: boolean;
  status: ChannelStatus;
  status_detail: string | null;
  available_reactions: string[] | null;
  created_at: Date;
};

export const BOT_SETUP_INSTRUCTIONS = [
  "Open the channel → Administrators → Add administrator → select your bot.",
  "Grant the minimum: leave every optional permission off unless Telegram requires at least one. The bot only needs to be an administrator to receive posts and reactions counts.",
  "Back here, press “Verify access”.",
];

function reactionsList(chat: TgChat): string[] | null {
  if (!chat.available_reactions) return null; // omitted by Telegram = all emoji allowed
  return chat.available_reactions.filter((r) => r.type === "emoji" && r.emoji).map((r) => r.emoji as string);
}

export class UserFacingError extends Error {}

function describeTelegramError(e: unknown): string {
  if (e instanceof TelegramApiError) {
    if (/chat not found/i.test(e.description)) return "Telegram cannot find this channel with the bot. Check the link, and for private channels add the bot as administrator first.";
    if (e.code === 401) return "The bot token was rejected by Telegram. Update it in Settings.";
    return e.message;
  }
  return e instanceof Error ? e.message : String(e);
}

async function inspect(ref: number | string) {
  const { bot, identity } = await requireBot();
  let chat: TgChat;
  try {
    chat = await bot.getChat(ref);
  } catch (e) {
    throw new UserFacingError(describeTelegramError(e));
  }
  if (chat.type !== "channel") throw new UserFacingError(`This link points to a ${chat.type}, not a channel.`);

  let status: ChannelStatus = "connected";
  let detail: string | null = null;
  try {
    const m = await bot.getChatMember(chat.id, identity.id);
    if (m.status !== "administrator" && m.status !== "creator") {
      status = "no_access";
      detail = `Bot is “${m.status}” in this channel. It must be an administrator to receive posts.`;
    }
  } catch (e) {
    status = "no_access";
    detail = `Bot cannot read its membership: ${describeTelegramError(e)}`;
  }

  let count: number | null = null;
  if (status === "connected") {
    try { count = await bot.getChatMemberCount(chat.id); } catch { /* not fatal */ }
  }
  return { chat, status, detail, count };
}

export async function addChannel(input: string, actor: string): Promise<Channel> {
  let parsed;
  try {
    parsed = parseTelegramRef(input);
  } catch (e) {
    if (e instanceof TelegramRefError) throw new UserFacingError(e.message);
    throw e;
  }
  const ref: number | string = "username" in parsed ? `@${parsed.username}` : chatIdFromInternal(parsed.internalId);
  const { chat, status, detail, count } = await inspect(ref);

  const row = await tx(async (c) => {
    const r = await c.query<Channel>(
      `INSERT INTO channels (tg_chat_id, username, title, photo_file_id, subscriber_count, subscribers_checked_at, is_private, status, status_detail, available_reactions)
       VALUES ($1,$2,$3,$4,$5, CASE WHEN $5::int IS NULL THEN NULL ELSE now() END, $6,$7,$8,$9)
       ON CONFLICT (tg_chat_id) DO UPDATE SET username=$2, title=$3, photo_file_id=$4,
         subscriber_count=COALESCE($5, channels.subscriber_count), status=$7, status_detail=$8, available_reactions=$9, updated_at=now(), status_changed_at=now()
       RETURNING *`,
      [chat.id, chat.username ?? null, chat.title ?? "Untitled", chat.photo?.small_file_id ?? null, count, !chat.username, status, detail,
       JSON.stringify(reactionsList(chat))],
    );
    await c.query("INSERT INTO automation_settings (channel_id) VALUES ($1) ON CONFLICT DO NOTHING", [r.rows[0].id]);
    if (count != null) await c.query("INSERT INTO channel_stats (channel_id, subscribers) VALUES ($1,$2)", [r.rows[0].id, count]);
    return r.rows[0];
  });
  await logActivity({ category: "channel", action: "add", channelId: row.id, actor, message: `Channel “${row.title}” added (${status})`, meta: { status } });
  return row;
}

export async function verifyChannel(id: string, actor = "system"): Promise<Channel> {
  const ch = await getChannel(id);
  if (!ch) throw new UserFacingError("Channel not found");
  try {
    const { chat, status, detail, count } = await inspect(ch.tg_chat_id);
    const r = await one<Channel>(
      `UPDATE channels SET username=$2, title=$3, photo_file_id=$4, subscriber_count=COALESCE($5, subscriber_count),
         subscribers_checked_at = CASE WHEN $5::int IS NULL THEN subscribers_checked_at ELSE now() END,
         status=$6, status_detail=$7, available_reactions=$8, updated_at=now(),
         status_changed_at = CASE WHEN status <> $6 THEN now() ELSE status_changed_at END
       WHERE id=$1 RETURNING *`,
      [id, chat.username ?? null, chat.title ?? ch.title, chat.photo?.small_file_id ?? null, count, status, detail, JSON.stringify(reactionsList(chat))],
    );
    if (count != null) await query("INSERT INTO channel_stats (channel_id, subscribers) VALUES ($1,$2)", [id, count]);
    await logActivity({ category: "channel", action: "verify", channelId: id, actor, message: `Access verified: ${status}`, meta: { status, detail } });
    return r!;
  } catch (e) {
    const msg = e instanceof UserFacingError ? e.message : describeTelegramError(e);
    const transient = !(e instanceof UserFacingError) && !(e instanceof TelegramApiError && e.permanent);
    const r = await one<Channel>(
      "UPDATE channels SET status=$2, status_detail=$3, status_changed_at=now(), updated_at=now() WHERE id=$1 RETURNING *",
      [id, transient ? "error" : "no_access", msg],
    );
    await logActivity({ level: "warn", category: "channel", action: "verify", channelId: id, actor, message: `Access check failed: ${msg}` });
    return r!;
  }
}

export async function getChannel(id: string): Promise<Channel | null> {
  return one<Channel>("SELECT * FROM channels WHERE id=$1", [id]);
}

export async function findChannelByRef(ref: ChannelRef): Promise<Channel | null> {
  if ("username" in ref) return one<Channel>("SELECT * FROM channels WHERE lower(username)=lower($1)", [ref.username]);
  return one<Channel>("SELECT * FROM channels WHERE tg_chat_id=$1", [chatIdFromInternal(ref.internalId)]);
}

export async function removeChannel(id: string, actor: string) {
  const ch = await getChannel(id);
  if (!ch) return;
  await query("DELETE FROM channels WHERE id=$1", [id]);
  await logActivity({ category: "channel", action: "remove", actor, message: `Channel “${ch.title}” removed (posts and history deleted)` });
}

export async function listChannels() {
  const r = await query<Channel & {
    monitoring_enabled: boolean; stats_enabled: boolean; reaction_enabled: boolean; post_count: number; last_post_at: Date | null;
  }>(
    `SELECT c.*, s.monitoring_enabled, s.stats_enabled, s.reaction_enabled,
            (SELECT count(*)::int FROM telegram_posts p WHERE p.channel_id=c.id) AS post_count,
            (SELECT max(published_at) FROM telegram_posts p WHERE p.channel_id=c.id) AS last_post_at
     FROM channels c JOIN automation_settings s ON s.channel_id=c.id
     ORDER BY c.created_at`,
  );
  return r.rows;
}
