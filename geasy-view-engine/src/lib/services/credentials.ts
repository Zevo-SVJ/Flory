import { createHash, randomBytes } from "node:crypto";
import { env } from "../env";
import { one, query } from "../db";
import { decrypt, encrypt } from "../crypto";
import { TelegramBot, type TgUser } from "../telegram/bot";

type BotRow = { payload_enc: string; identity: BotIdentity; webhook_secret: string | null; updated_at: Date };
export type BotIdentity = { id: number; username?: string; first_name: string };

let cache: { stamp: number; bot: TelegramBot; identity: BotIdentity } | null = null;

export async function getBot(): Promise<{ bot: TelegramBot; identity: BotIdentity } | null> {
  const row = await one<BotRow>("SELECT payload_enc, identity, webhook_secret, updated_at FROM telegram_credentials WHERE kind='bot'");
  if (!row) {
    cache = null;
    return null;
  }
  const stamp = new Date(row.updated_at).getTime();
  if (cache && cache.stamp === stamp) return { bot: cache.bot, identity: cache.identity };
  const bot = new TelegramBot(decrypt(row.payload_enc));
  cache = { stamp, bot, identity: row.identity };
  return { bot, identity: row.identity };
}

export async function requireBot() {
  const b = await getBot();
  if (!b) throw new Error("No Telegram bot configured. Add the bot token in Settings.");
  return b;
}

export function webhookPathToken(secret: string): string {
  return createHash("sha256").update(`${secret}:path`).digest("hex").slice(0, 24);
}

/** Validates the token with getMe, stores it encrypted, registers the webhook. */
export async function saveBotToken(token: string): Promise<{ identity: BotIdentity; webhookUrl: string }> {
  const trimmed = token.trim();
  if (!/^\d{5,}:[A-Za-z0-9_-]{30,}$/.test(trimmed)) throw new Error("This does not look like a Telegram bot token (expected 123456:ABC...)");
  const bot = new TelegramBot(trimmed);
  const me: TgUser = await bot.getMe();
  if (!me.is_bot) throw new Error("Token does not belong to a bot");
  const identity: BotIdentity = { id: me.id, username: me.username, first_name: me.first_name };

  const existing = await one<{ webhook_secret: string | null }>("SELECT webhook_secret FROM telegram_credentials WHERE kind='bot'");
  const secret = existing?.webhook_secret ?? randomBytes(32).toString("hex");
  const webhookUrl = `${env().PUBLIC_BASE_URL.replace(/\/$/, "")}/tg/webhook/${webhookPathToken(secret)}`;
  await bot.setWebhook(webhookUrl, secret);

  await query(
    `INSERT INTO telegram_credentials (kind, label, payload_enc, identity, webhook_secret)
     VALUES ('bot', $1, $2, $3, $4)
     ON CONFLICT (kind) DO UPDATE SET label=$1, payload_enc=$2, identity=$3, webhook_secret=$4, updated_at=now()`,
    [me.username ?? me.first_name, encrypt(trimmed), JSON.stringify(identity), secret],
  );
  cache = null;
  return { identity, webhookUrl };
}

export async function removeBot(): Promise<void> {
  const b = await getBot();
  if (b) await b.bot.deleteWebhook().catch(() => {});
  await query("DELETE FROM telegram_credentials WHERE kind='bot'");
  cache = null;
}

export async function getWebhookSecret(): Promise<string | null> {
  const r = await one<{ webhook_secret: string | null }>("SELECT webhook_secret FROM telegram_credentials WHERE kind='bot'");
  return r?.webhook_secret ?? null;
}

export async function saveMtprotoSession(apiId: number, apiHash: string, session: string, identity: Record<string, unknown>) {
  await query(
    `INSERT INTO telegram_credentials (kind, label, payload_enc, identity)
     VALUES ('mtproto', $1, $2, $3)
     ON CONFLICT (kind) DO UPDATE SET label=$1, payload_enc=$2, identity=$3, updated_at=now()`,
    [String(identity.username ?? identity.phone ?? "account"), encrypt(JSON.stringify({ apiId, apiHash, session })), JSON.stringify(identity)],
  );
}

export async function getMtprotoCredential(): Promise<{ apiId: number; apiHash: string; session: string; updatedAt: number } | null> {
  const r = await one<{ payload_enc: string; updated_at: Date }>("SELECT payload_enc, updated_at FROM telegram_credentials WHERE kind='mtproto'");
  if (!r) return null;
  return { ...JSON.parse(decrypt(r.payload_enc)), updatedAt: new Date(r.updated_at).getTime() };
}

export async function getCredentialSummary() {
  const rows = await query<{ kind: "bot" | "mtproto"; identity: Record<string, unknown>; updated_at: Date }>(
    "SELECT kind, identity, updated_at FROM telegram_credentials",
  );
  return {
    bot: rows.rows.find((r) => r.kind === "bot") ?? null,
    mtproto: rows.rows.find((r) => r.kind === "mtproto") ?? null,
  };
}
