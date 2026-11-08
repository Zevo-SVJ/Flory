import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { one, query } from "../db";
import { randomToken, sha256 } from "../crypto";
import { hashPassword, verifyPassword } from "../password";
import { logActivity } from "../activity";
import { env } from "../env";

export const COOKIE = "geasy_session";
const TTL_DAYS = 7;
const MAX_FAILS = 5;
const WINDOW_MIN = 15;

export type SessionUser = { id: string; email: string };

export async function createUser(email: string, password: string) {
  const hash = await hashPassword(password);
  await query(
    `INSERT INTO users (email, password_hash) VALUES ($1,$2)
     ON CONFLICT ((lower(email))) DO UPDATE SET password_hash = EXCLUDED.password_hash`,
    [email.trim(), hash],
  );
}

async function clientKey(email: string): Promise<string> {
  const h = await headers();
  const ip = (h.get("x-forwarded-for")?.split(",")[0] ?? h.get("x-real-ip") ?? "unknown").trim();
  return `${ip}|${email.toLowerCase()}`;
}

export type LoginResult = { ok: true } | { ok: false; error: string };

export async function login(email: string, password: string): Promise<LoginResult> {
  const key = await clientKey(email);
  const fails = await one<{ n: number }>(
    "SELECT count(*)::int AS n FROM login_attempts WHERE key=$1 AND attempted_at > now() - make_interval(mins => $2)", [key, WINDOW_MIN]);
  if ((fails?.n ?? 0) >= MAX_FAILS) return { ok: false, error: `Too many attempts. Try again in ${WINDOW_MIN} minutes.` };

  const u = await one<{ id: string; email: string; password_hash: string }>("SELECT id, email, password_hash FROM users WHERE lower(email)=lower($1)", [email.trim()]);
  // Always run a hash comparison so response time does not reveal whether the account exists.
  const ok = await verifyPassword(password, u?.password_hash ?? "scrypt$32768$8$1$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
  if (!u || !ok) {
    await query("INSERT INTO login_attempts (key) VALUES ($1)", [key]);
    await logActivity({ level: "warn", category: "auth", action: "login_failed", message: "Failed login attempt", meta: { email } });
    return { ok: false, error: "Invalid email or password." };
  }
  await query("DELETE FROM login_attempts WHERE key=$1", [key]);

  const token = randomToken();
  const h = await headers();
  await query(
    "INSERT INTO sessions (user_id, token_hash, expires_at, ip, user_agent) VALUES ($1,$2, now() + make_interval(days => $3), $4, $5)",
    [u.id, sha256(token), TTL_DAYS, key.split("|")[0], h.get("user-agent")?.slice(0, 300) ?? null],
  );
  await query("UPDATE users SET last_login_at=now() WHERE id=$1", [u.id]);
  (await cookies()).set(COOKIE, token, {
    httpOnly: true,
    secure: env().PUBLIC_BASE_URL.startsWith("https://"),
    sameSite: "strict",
    path: "/",
    maxAge: TTL_DAYS * 86400,
  });
  await logActivity({ category: "auth", action: "login", actor: `user:${u.email}`, message: "Signed in" });
  return { ok: true };
}

export async function getUser(): Promise<SessionUser | null> {
  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) return null;
  return one<SessionUser>(
    `SELECT u.id, u.email FROM sessions s JOIN users u ON u.id = s.user_id
     WHERE s.token_hash=$1 AND s.expires_at > now()`,
    [sha256(token)],
  );
}

export async function requireUser(): Promise<SessionUser> {
  const u = await getUser();
  if (!u) redirect("/login");
  return u;
}

export async function logout() {
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  if (token) await query("DELETE FROM sessions WHERE token_hash=$1", [sha256(token)]);
  jar.delete(COOKIE);
}
