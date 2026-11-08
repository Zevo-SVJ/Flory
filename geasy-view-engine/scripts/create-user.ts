/** Creates (or resets the password of) the single admin. Reads ADMIN_EMAIL / ADMIN_PASSWORD from env. */
import { closePool, query } from "../src/lib/db";
import { runMigrations } from "../src/lib/migrate";
import { hashPassword } from "../src/lib/password";

async function main() {
  const email = process.env.ADMIN_EMAIL?.trim();
  const password = process.env.ADMIN_PASSWORD;
  if (!email || !password) throw new Error("Set ADMIN_EMAIL and ADMIN_PASSWORD");
  await runMigrations();
  const hash = await hashPassword(password);
  await query(
    `INSERT INTO users (email, password_hash) VALUES ($1,$2)
     ON CONFLICT ((lower(email))) DO UPDATE SET password_hash=EXCLUDED.password_hash`,
    [email, hash],
  );
  await query("DELETE FROM sessions"); // a password reset invalidates every session
  console.log(`Admin ready: ${email}`);
}

main().catch((e) => { console.error(e.message); process.exitCode = 1; }).finally(() => closePool());
