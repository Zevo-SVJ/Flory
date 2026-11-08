/** Validates a bot token (getMe), stores it encrypted and registers the webhook. Reads BOT_TOKEN from env. */
import { closePool } from "../src/lib/db";
import { runMigrations } from "../src/lib/migrate";
import { saveBotToken } from "../src/lib/services/credentials";

async function main() {
  const token = process.env.BOT_TOKEN;
  if (!token) throw new Error("Set BOT_TOKEN");
  await runMigrations();
  const { identity, webhookUrl } = await saveBotToken(token);
  console.log(`Bot @${identity.username} verified. Webhook registered: ${webhookUrl.replace(/\/[^/]+$/, "/••••")}`);
}

main()
  .catch((e) => { console.error("ERROR:", e.message); process.exitCode = 1; })
  .finally(() => closePool());
