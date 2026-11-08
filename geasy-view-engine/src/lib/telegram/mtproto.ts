/**
 * MTProto adapter (user account, official API via api_id/api_hash from my.telegram.org).
 *
 * WHY IT EXISTS: the Bot API exposes no view counter, no forward counter and no way to read an
 * existing message by id. MTProto (messages/channels.getMessages → Message.views, .forwards,
 * .reactions) is the documented source for those. Reading does NOT increment views
 * (only messages.getMessagesViews with increment=true does, and we never call it).
 *
 * The account must be a member of the channel. Everything here is read-only.
 * The `telegram` (GramJS) package is archived upstream; it is confined to this file so it can be
 * swapped (e.g. for the maintained fork `teleproto`) without touching the rest of the app.
 */
import { getMtprotoCredential } from "../services/credentials";
import { log, errMessage } from "../logger";
import type { MediaType } from "../services/posts";

export type MtMessage = {
  messageId: number;
  date: Date | null;
  views: number | null;
  forwards: number | null;
  replies: number | null;
  reactions: Record<string, number>;
  text: string | null;
  mediaType: MediaType;
  groupedId: string | null;
  isForwarded: boolean;
};

export type ChannelPeer = { chatId: number; username: string | null };

export interface MtprotoSource {
  fetchMessages(peer: ChannelPeer, ids: number[]): Promise<Map<number, MtMessage>>;
}

type Gram = typeof import("telegram");
let state: { stamp: number; client: import("telegram").TelegramClient; gram: Gram } | null = null;

async function connect() {
  const cred = await getMtprotoCredential();
  if (!cred) return null;
  if (state && state.stamp === cred.updatedAt) return state;
  if (state) await state.client.disconnect().catch(() => {});
  const gram: Gram = await import("telegram");
  const { StringSession } = await import("telegram/sessions/index.js");
  const client = new gram.TelegramClient(new StringSession(cred.session), cred.apiId, cred.apiHash, { connectionRetries: 5, useWSS: false });
  await client.connect();
  if (!(await client.checkAuthorization())) throw new Error("MTProto session is no longer authorised. Run `npm run mtproto:login` again.");
  state = { stamp: cred.updatedAt, client, gram };
  log.info("mtproto connected");
  return state;
}

export async function mtprotoAvailable(): Promise<boolean> {
  return (await getMtprotoCredential()) !== null;
}

function mapMedia(m: import("telegram").Api.Message): MediaType {
  const media = m.media as { className?: string; document?: { mimeType?: string; attributes?: Array<{ className: string; voice?: boolean; roundMessage?: boolean }> } } | undefined;
  if (!media) return m.message ? "text" : "other";
  if (media.className === "MessageMediaPhoto") return "photo";
  if (media.className === "MessageMediaPoll") return "poll";
  if (media.className === "MessageMediaDocument") {
    const mime = media.document?.mimeType ?? "";
    const attrs = media.document?.attributes ?? [];
    if (attrs.some((a) => a.className === "DocumentAttributeAnimated")) return "animation";
    if (mime.startsWith("video/")) return "video";
    if (attrs.some((a) => a.className === "DocumentAttributeAudio" && a.voice)) return "voice";
    if (mime.startsWith("audio/")) return "audio";
    return "document";
  }
  return "other";
}

export const mtproto: MtprotoSource = {
  async fetchMessages(peer, ids) {
    const s = await connect();
    if (!s) throw new Error("MTProto not configured");
    const { client, gram } = s;
    let input;
    try {
      input = await client.getInputEntity(peer.username ?? new gram.Api.PeerChannel({ channelId: BigInt(String(peer.chatId).replace(/^-100/, "")) as never }));
    } catch {
      // Access hashes are only known for chats seen in dialogs; load them once and retry.
      await client.getDialogs({ limit: 300 });
      input = await client.getInputEntity(peer.username ?? new gram.Api.PeerChannel({ channelId: BigInt(String(peer.chatId).replace(/^-100/, "")) as never }));
    }
    const msgs = await client.getMessages(input, { ids });
    const out = new Map<number, MtMessage>();
    for (const m of msgs) {
      if (!m || m.className !== "Message") continue; // deleted / empty ids come back as undefined or MessageEmpty
      const reactions: Record<string, number> = {};
      for (const r of m.reactions?.results ?? []) {
        const rt = r.reaction as { className: string; emoticon?: string; documentId?: { toString(): string } };
        const key = rt.className === "ReactionEmoji" ? rt.emoticon! : rt.className === "ReactionCustomEmoji" ? `custom:${rt.documentId}` : "paid";
        reactions[key] = (reactions[key] ?? 0) + r.count;
      }
      out.set(m.id, {
        messageId: m.id,
        date: m.date ? new Date(m.date * 1000) : null,
        views: m.views ?? null,
        forwards: m.forwards ?? null,
        replies: m.replies?.replies ?? null,
        reactions,
        text: m.message || null,
        mediaType: mapMedia(m),
        groupedId: m.groupedId ? String(m.groupedId) : null,
        isForwarded: !!m.fwdFrom,
      });
    }
    return out;
  },
};

export async function disconnectMtproto() {
  if (state) await state.client.disconnect().catch((e) => log.warn("mtproto disconnect", { error: errMessage(e) }));
  state = null;
}
