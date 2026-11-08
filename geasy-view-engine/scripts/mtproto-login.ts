/**
 * One-time interactive login of the Telegram user account used to READ view/forward counts.
 * api_id / api_hash: https://my.telegram.org → API development tools (your own app, official API).
 * The session is stored AES-256-GCM encrypted in Postgres; nothing is written to disk.
 */
import readline from "node:readline/promises";
import { TelegramClient } from "telegram";
import { StringSession } from "telegram/sessions/index.js";
import { closePool } from "../src/lib/db";
import { saveMtprotoSession } from "../src/lib/services/credentials";

async function main() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const apiId = Number(await rl.question("api_id: "));
  const apiHash = (await rl.question("api_hash: ")).trim();
  if (!apiId || !apiHash) throw new Error("api_id and api_hash are required");
  const client = new TelegramClient(new StringSession(""), apiId, apiHash, { connectionRetries: 5 });
  await client.start({
    phoneNumber: () => rl.question("Phone (international format): "),
    phoneCode: () => rl.question("Code received in Telegram: "),
    password: () => rl.question("2FA password (if any): "),
    onError: (e) => console.error("Login error:", e.message),
  });
  const me = (await client.getMe()) as unknown as { id: unknown; username?: string; firstName?: string };
  const session = client.session.save() as unknown as string;
  await saveMtprotoSession(apiId, apiHash, session, { id: String(me.id), username: me.username, name: me.firstName });
  console.log(`MTProto session saved for ${me.username ?? me.firstName}. Restart the worker to use it.`);
  await client.disconnect();
  rl.close();
}

main().catch((e) => { console.error(e.message); process.exitCode = 1; }).finally(() => closePool());
