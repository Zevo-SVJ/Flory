"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { z } from "zod";
import { COOKIE, login, logout, requireUser } from "@/lib/auth/session";
import { one, query } from "@/lib/db";
import { sha256 } from "@/lib/crypto";
import { hashPassword, verifyPassword } from "@/lib/password";
import { logActivity } from "@/lib/activity";
import { addChannel, removeChannel, UserFacingError, verifyChannel, getChannel, findChannelByRef } from "@/lib/services/channels";
import { getBot, removeBot, saveBotToken } from "@/lib/services/credentials";
import { createJobOnce } from "@/lib/services/automation";
import { ensureManualPost, getPost, getPostByMessage } from "@/lib/services/posts";
import { mtprotoAvailable } from "@/lib/telegram/mtproto";
import { metricsSource, snapshotPosts } from "@/lib/services/statsjobs";
import { parseTelegramRef, TelegramRefError } from "@/lib/telegram/url";
import { TELEGRAM_REACTION_EMOJI } from "@/lib/telegram/bot";
import { errMessage } from "@/lib/logger";
import { QUEUES, queue } from "@/lib/queue";

export type ActionState = { ok?: boolean; error?: string; message?: string; connectUrl?: string } | null;

const fail = (e: unknown): ActionState => ({ error: e instanceof UserFacingError || e instanceof TelegramRefError || e instanceof z.ZodError ? (e instanceof z.ZodError ? e.issues.map((i) => i.message).join("; ") : e.message) : errMessage(e) });
const actorOf = (u: { email: string }) => `user:${u.email}`;

// ── auth ───────────────────────────────────────────────
export async function loginAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const p = z.object({ email: z.string().email(), password: z.string().min(1).max(200) }).safeParse({ email: fd.get("email"), password: fd.get("password") });
  if (!p.success) return { error: "Enter a valid email and password." };
  const r = await login(p.data.email, p.data.password);
  if (!r.ok) return { error: r.error };
  redirect("/");
}

export async function logoutAction() {
  await logout();
  redirect("/login");
}

export async function changePasswordAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  try {
    const p = z.object({ current: z.string().min(1), next: z.string().min(12, "New password must be at least 12 characters").max(200), confirm: z.string() })
      .refine((v) => v.next === v.confirm, { message: "Confirmation does not match" })
      .parse({ current: fd.get("current"), next: fd.get("next"), confirm: fd.get("confirm") });
    const row = await one<{ password_hash: string }>("SELECT password_hash FROM users WHERE id=$1", [u.id]);
    if (!row || !(await verifyPassword(p.current, row.password_hash))) return { error: "Current password is incorrect." };
    await query("UPDATE users SET password_hash=$2 WHERE id=$1", [u.id, await hashPassword(p.next)]);
    const token = (await cookies()).get(COOKIE)?.value;
    await query("DELETE FROM sessions WHERE user_id=$1 AND token_hash <> $2", [u.id, token ? sha256(token) : ""]);
    await logActivity({ category: "auth", action: "password_changed", actor: actorOf(u), message: "Password changed; other sessions signed out" });
    return { ok: true, message: "Password updated. Other sessions were signed out." };
  } catch (e) { return fail(e); }
}

// ── channels ───────────────────────────────────────────
export async function addChannelAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  try {
    const ch = await addChannel(String(fd.get("link") ?? ""), actorOf(u));
    revalidatePath("/channels");
    return ch.status === "connected"
      ? { ok: true, message: `“${ch.title}” connected. New posts will be detected automatically.` }
      : { ok: true, message: `“${ch.title}” saved but NOT authorised: ${ch.status_detail ?? "bot is not an administrator"}. Add the bot as administrator, then press “Verify access”.` };
  } catch (e) { return fail(e); }
}

export async function verifyChannelAction(fd: FormData) {
  const u = await requireUser();
  await verifyChannel(String(fd.get("id")), actorOf(u));
  revalidatePath("/channels");
}

export async function removeChannelAction(fd: FormData) {
  const u = await requireUser();
  await removeChannel(String(fd.get("id")), actorOf(u));
  revalidatePath("/", "layout");
}

// ── automation settings ────────────────────────────────
const BOOL_KEYS = ["monitoring_enabled", "stats_enabled", "reaction_enabled", "notify_enabled"] as const;

export async function toggleSettingAction(fd: FormData) {
  const u = await requireUser();
  const key = z.enum(BOOL_KEYS).parse(fd.get("key"));
  const value = fd.get("value") === "true";
  const id = z.string().uuid().parse(fd.get("channelId"));
  await query(`UPDATE automation_settings SET ${key}=$2, consecutive_failures = CASE WHEN $3 THEN 0 ELSE consecutive_failures END, updated_at=now() WHERE channel_id=$1`, [id, value, key === "monitoring_enabled" && value]);
  await logActivity({ category: "system", action: "setting", channelId: id, actor: actorOf(u), message: `${key} → ${value ? "ON" : "OFF"}` });
  revalidatePath("/", "layout");
}

const settingsSchema = z.object({
  channelId: z.string().uuid(),
  monitoring_enabled: z.boolean(),
  stats_enabled: z.boolean(),
  reaction_enabled: z.boolean(),
  reaction_emoji: z.enum(TELEGRAM_REACTION_EMOJI as unknown as [string, ...string[]], { message: "This emoji is not accepted by Telegram reactions" }),
  notify_enabled: z.boolean(),
  notify_chat_id: z.coerce.number().int().optional().nullable(),
  monitor_interval_s: z.coerce.number().int().min(60, "Interval must be ≥ 60 s").max(86400),
  tracking_days: z.coerce.number().int().min(1).max(365),
  max_retries: z.coerce.number().int().min(0).max(20),
  pause_after_failures: z.coerce.number().int().min(0).max(100),
});

export async function saveSettingsAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  try {
    const chat = String(fd.get("notify_chat_id") ?? "").trim();
    const d = settingsSchema.parse({
      channelId: fd.get("channelId"),
      monitoring_enabled: fd.get("monitoring_enabled") === "on",
      stats_enabled: fd.get("stats_enabled") === "on",
      reaction_enabled: fd.get("reaction_enabled") === "on",
      reaction_emoji: fd.get("reaction_emoji"),
      notify_enabled: fd.get("notify_enabled") === "on",
      notify_chat_id: chat === "" ? null : chat,
      monitor_interval_s: fd.get("monitor_interval_s"),
      tracking_days: fd.get("tracking_days"),
      max_retries: fd.get("max_retries"),
      pause_after_failures: fd.get("pause_after_failures"),
    });
    if (d.notify_enabled && d.notify_chat_id == null) return { error: "Set a notification destination (chat id) or turn notifications off." };
    const ch = await getChannel(d.channelId);
    if (ch?.available_reactions && d.reaction_enabled && !ch.available_reactions.includes(d.reaction_emoji)) {
      return { error: `${d.reaction_emoji} is not enabled in this channel (allowed: ${ch.available_reactions.join(" ") || "none"}).` };
    }
    await query(
      `UPDATE automation_settings SET monitoring_enabled=$2, stats_enabled=$3, reaction_enabled=$4, reaction_emoji=$5, notify_enabled=$6, notify_chat_id=$7,
         monitor_interval_s=$8, tracking_days=$9, max_retries=$10, pause_after_failures=$11, updated_at=now() WHERE channel_id=$1`,
      [d.channelId, d.monitoring_enabled, d.stats_enabled, d.reaction_enabled, d.reaction_emoji, d.notify_enabled, d.notify_chat_id ?? null,
       d.monitor_interval_s, d.tracking_days, d.max_retries, d.pause_after_failures],
    );
    await logActivity({ category: "system", action: "settings_saved", channelId: d.channelId, actor: actorOf(u), message: "Automation settings saved" });
    revalidatePath("/", "layout");
    return { ok: true, message: "Saved." };
  } catch (e) { return fail(e); }
}

export async function setReactionEmojiAction(fd: FormData) {
  const u = await requireUser();
  const id = z.string().uuid().parse(fd.get("channelId"));
  const emoji = z.enum(TELEGRAM_REACTION_EMOJI as unknown as [string, ...string[]]).parse(fd.get("emoji"));
  await query("UPDATE automation_settings SET reaction_emoji=$2, updated_at=now() WHERE channel_id=$1", [id, emoji]);
  await logActivity({ category: "reaction", action: "emoji_set", channelId: id, actor: actorOf(u), message: `Default reaction set to ${emoji}` });
  revalidatePath("/reactions");
}

// ── Post Manager (mode B) ──────────────────────────────
async function lookup(url: string): Promise<{ postId?: string; error?: string; connectUrl?: string }> {
  const ref = parseTelegramRef(url);
  if (!ref.messageId) return { error: "This link points to a channel, not a post. Use a link like https://t.me/channel/123." };
  const ch = await findChannelByRef(ref);
  if (!ch) return { error: "This channel is not connected yet. Connect it first (the bot must be an administrator).", connectUrl: url };
  const existing = await getPostByMessage(ch.id, ref.messageId);
  if (existing) return { postId: existing.id };

  const hasMt = await mtprotoAvailable();
  if (!hasMt && ch.status !== "connected") {
    return { error: `The bot has no access to “${ch.title}” (${ch.status_detail ?? ch.status}). Add the bot as administrator and verify access from My Channels.` };
  }
  const stub = await ensureManualPost(ch.id, ref.messageId);
  if (hasMt) {
    try {
      const n = await snapshotPosts(ch, [stub]);
      if (n === 0) {
        await query("DELETE FROM telegram_posts WHERE id=$1 AND source='manual'", [stub.id]);
        return { error: `Telegram did not return message #${ref.messageId} for the connected account: it was deleted, or the account cannot see it.` };
      }
    } catch (e) {
      // Network/FLOOD error: keep the stub, the scheduler will fill it in; the detail page says what is missing.
      await logActivity({ level: "warn", category: "stats", action: "lookup_fetch_failed", channelId: ch.id, postId: stub.id, message: `MTProto fetch failed: ${errMessage(e)}` });
    }
  }
  return { postId: stub.id };
}

export async function lookupPostAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  let postId: string | undefined;
  try {
    const r = await lookup(String(fd.get("url") ?? ""));
    if (r.error) return { error: r.error, connectUrl: r.connectUrl };
    postId = r.postId;
    await logActivity({ category: "post", action: "lookup", postId, actor: actorOf(u), message: `Post looked up: ${String(fd.get("url")).slice(0, 120)}` });
  } catch (e) { return fail(e); }
  redirect(`/posts/${postId}`);
}

export async function connectAndLookupAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  let postId: string | undefined;
  try {
    const url = String(fd.get("url") ?? "");
    await addChannel(url, actorOf(u));
    const r = await lookup(url);
    if (r.error) return { error: r.error };
    postId = r.postId;
  } catch (e) { return fail(e); }
  revalidatePath("/channels");
  redirect(`/posts/${postId}`);
}

export async function refreshPostAction(fd: FormData) {
  const u = await requireUser();
  const post = await getPost(String(fd.get("postId")));
  if (!post) return;
  const ch = await getChannel(post.channel_id);
  if (!ch || !(await metricsSource())) return;
  try {
    await snapshotPosts(ch, [post]);
    await query("UPDATE telegram_posts SET tracking_enabled=true WHERE id=$1", [post.id]);
    await logActivity({ category: "stats", action: "manual_refresh", channelId: ch.id, postId: post.id, actor: actorOf(u), message: `Statistics refreshed for post #${post.message_id}` });
  } catch (e) {
    await logActivity({ level: "warn", category: "stats", action: "manual_refresh_failed", channelId: ch.id, postId: post.id, actor: actorOf(u), message: `Refresh failed: ${errMessage(e)}` });
  }
  revalidatePath(`/posts/${post.id}`);
}

export async function toggleTrackingAction(fd: FormData) {
  const u = await requireUser();
  const id = z.string().uuid().parse(fd.get("postId"));
  const on = fd.get("value") === "true";
  await query("UPDATE telegram_posts SET tracking_enabled=$2, updated_at=now() WHERE id=$1", [id, on]);
  await logActivity({ category: "post", action: "tracking", postId: id, actor: actorOf(u), message: `Tracking ${on ? "enabled" : "disabled"}` });
  revalidatePath(`/posts/${id}`);
}

export async function reactNowAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  try {
    const postId = z.string().uuid().parse(fd.get("postId"));
    const emoji = z.enum(TELEGRAM_REACTION_EMOJI as unknown as [string, ...string[]], { message: "Pick a reaction" }).parse(fd.get("emoji"));
    const post = await getPost(postId);
    const ch = post && (await getChannel(post.channel_id));
    if (!post || !ch) return { error: "Post not found" };
    if (ch.status !== "connected") return { error: "The bot is not connected to this channel." };
    if (ch.available_reactions && !ch.available_reactions.includes(emoji)) return { error: `${emoji} is not enabled in this channel.` };
    const b = await getBot();
    const created = await createJobOnce({
      channelId: ch.id, postId, kind: "reaction", dedupeKey: `manual-reaction:${ch.tg_chat_id}:${post.message_id}:${emoji}`,
      payload: { messageId: post.message_id, emoji, manual: true, requestedBy: u.email }, maxAttempts: 3,
    });
    if (!created) return { error: `A ${emoji} reaction was already requested for this post.` };
    await logActivity({ category: "reaction", action: "manual_request", channelId: ch.id, postId, actor: actorOf(u), message: `Reaction ${emoji} requested as @${b?.identity.username}` });
    revalidatePath(`/posts/${postId}`);
    return { ok: true, message: `Queued: @${b?.identity.username} will react ${emoji}.` };
  } catch (e) { return fail(e); }
}

export async function refreshAllStatsAction() {
  await requireUser();
  await queue(QUEUES.stats).add("tick", {}, { jobId: `manual-tick-${Date.now()}`, attempts: 1 });
  revalidatePath("/", "layout");
}

// ── settings ───────────────────────────────────────────
export async function saveBotAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  try {
    const { identity } = await saveBotToken(String(fd.get("token") ?? ""));
    await logActivity({ category: "system", action: "bot_saved", actor: actorOf(u), message: `Bot @${identity.username} connected, webhook registered` });
    revalidatePath("/", "layout");
    return { ok: true, message: `Bot @${identity.username} verified. Webhook registered.` };
  } catch (e) { return fail(e); }
}

export async function removeBotAction() {
  const u = await requireUser();
  await removeBot();
  await logActivity({ level: "warn", category: "system", action: "bot_removed", actor: actorOf(u), message: "Bot token removed and webhook deleted" });
  revalidatePath("/", "layout");
}

export async function saveRetentionAction(_: ActionState, fd: FormData): Promise<ActionState> {
  const u = await requireUser();
  try {
    const d = z.object({
      webhook_events_days: z.coerce.number().int().min(1).max(3650),
      activity_logs_days: z.coerce.number().int().min(1).max(3650),
      stats_full_days: z.coerce.number().int().min(1).max(3650),
    }).parse(Object.fromEntries(fd));
    await query("UPDATE retention_policy SET webhook_events_days=$1, activity_logs_days=$2, stats_full_days=$3, stats_downsample_to_daily=$4",
      [d.webhook_events_days, d.activity_logs_days, d.stats_full_days, fd.get("stats_downsample_to_daily") === "on"]);
    await logActivity({ category: "system", action: "retention_saved", actor: actorOf(u), message: "Retention policy updated" });
    return { ok: true, message: "Saved. Applied nightly at 03:17 UTC." };
  } catch (e) { return fail(e); }
}

export async function signOutEverywhereAction() {
  const u = await requireUser();
  await query("DELETE FROM sessions WHERE user_id=$1", [u.id]);
  redirect("/login");
}
