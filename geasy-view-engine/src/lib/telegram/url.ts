export class TelegramRefError extends Error {
  constructor(public code: "empty" | "invalid" | "invite_link" | "unsupported", message: string) {
    super(message);
  }
}

export type ChannelRef = { username: string } | { internalId: string };
export type ParsedRef = ChannelRef & { messageId?: number };

const USERNAME = /^[A-Za-z][A-Za-z0-9_]{4,31}$/;
const RESERVED = new Set(["s", "c", "joinchat", "addstickers", "addemoji", "share", "proxy", "socks", "login", "iv", "boost", "m", "addlist", "contact", "giftcode", "invoice", "setlanguage", "bg", "addtheme", "confirmphone", "msg"]);

/** Bot API chat_id for a t.me/c/<internalId> link. */
export function chatIdFromInternal(internalId: string): number {
  return Number(`-100${internalId}`);
}

export function internalIdFromChatId(chatId: number): string | null {
  const s = String(chatId);
  return s.startsWith("-100") ? s.slice(4) : null;
}

function positiveInt(s: string | undefined): number | undefined {
  if (!s || !/^\d{1,12}$/.test(s)) return undefined;
  const n = Number(s);
  return n > 0 ? n : undefined;
}

/**
 * Parses channel links, post links and @usernames.
 * Accepts: @name, name, t.me/name, t.me/name/123, t.me/s/name/123, t.me/c/123456/789,
 * t.me/c/123456/<topic>/789, tg://resolve?domain=name&post=123, telegram.me/...
 */
export function parseTelegramRef(raw: string): ParsedRef {
  const input = raw.trim();
  if (!input) throw new TelegramRefError("empty", "Empty input");

  // tg://resolve?domain=x&post=1
  if (/^tg:\/\//i.test(input)) {
    let u: URL;
    try { u = new URL(input); } catch { throw new TelegramRefError("invalid", "Invalid tg:// link"); }
    if (u.hostname !== "resolve") throw new TelegramRefError("unsupported", "Unsupported tg:// link");
    const domain = u.searchParams.get("domain") ?? "";
    if (!USERNAME.test(domain)) throw new TelegramRefError("invalid", "Invalid channel username");
    return { username: domain, messageId: positiveInt(u.searchParams.get("post") ?? undefined) };
  }

  let path: string;
  if (/^(https?:\/\/)?(www\.)?(t|telegram)\.me\//i.test(input)) {
    let u: URL;
    try { u = new URL(/^https?:\/\//i.test(input) ? input : `https://${input}`); } catch { throw new TelegramRefError("invalid", "Invalid URL"); }
    path = u.pathname;
  } else if (/^@?[A-Za-z][A-Za-z0-9_]{4,31}$/.test(input)) {
    return { username: input.replace(/^@/, "") };
  } else {
    throw new TelegramRefError("unsupported", "Not a Telegram link (expected t.me/<channel>[/<id>], t.me/c/<id>/<id> or @username)");
  }

  const seg = path.split("/").filter(Boolean).map((s) => decodeURIComponent(s));
  if (seg.length === 0) throw new TelegramRefError("invalid", "Missing channel in link");

  if (seg[0].startsWith("+") || seg[0] === "joinchat") {
    throw new TelegramRefError("invite_link", "Invite links cannot identify a channel. Use the public t.me/<username> link, or add the bot to the channel and use a t.me/c/<id>/<post> link.");
  }

  if (seg[0] === "c") {
    const id = seg[1];
    if (!id || !/^\d{5,13}$/.test(id)) throw new TelegramRefError("invalid", "Invalid private channel id in t.me/c/ link");
    // t.me/c/<id>/<msg>  or  t.me/c/<id>/<topic>/<msg>
    const last = seg.length > 2 ? positiveInt(seg[seg.length - 1]) : undefined;
    if (seg.length > 2 && !last) throw new TelegramRefError("invalid", "Invalid message id");
    return { internalId: id, messageId: last };
  }

  const idx = seg[0] === "s" ? 1 : 0;
  const username = seg[idx];
  if (!username || RESERVED.has(username.toLowerCase()) || !USERNAME.test(username)) {
    throw new TelegramRefError("invalid", `Invalid channel username "${username ?? ""}"`);
  }
  const rest = seg.slice(idx + 1);
  if (rest.length === 0) return { username };
  const msg = positiveInt(rest[rest.length - 1]);
  if (!msg) throw new TelegramRefError("invalid", "Invalid message id");
  return { username, messageId: msg };
}

export function buildPostUrl(channel: { username: string | null; tg_chat_id: number }, messageId: number): string {
  if (channel.username) return `https://t.me/${channel.username}/${messageId}`;
  const internal = internalIdFromChatId(channel.tg_chat_id);
  return internal ? `https://t.me/c/${internal}/${messageId}` : "";
}
