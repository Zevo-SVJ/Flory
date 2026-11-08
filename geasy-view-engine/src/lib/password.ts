import { randomBytes, scrypt as _scrypt, timingSafeEqual, type ScryptOptions } from "node:crypto";

const N = 2 ** 15, R = 8, P = 1, KEYLEN = 64;

function scrypt(pw: string, salt: Buffer, keylen: number, opts: ScryptOptions): Promise<Buffer> {
  return new Promise((res, rej) => _scrypt(pw, salt, keylen, opts, (e, k) => (e ? rej(e) : res(k))));
}

export const MIN_PASSWORD_LENGTH = 12;

export async function hashPassword(password: string): Promise<string> {
  if (password.length < MIN_PASSWORD_LENGTH) throw new Error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
  const salt = randomBytes(16);
  const h = await scrypt(password, salt, KEYLEN, { N, r: R, p: P, maxmem: 128 * N * R * 2 });
  return `scrypt$${N}$${R}$${P}$${salt.toString("base64url")}$${h.toString("base64url")}`;
}

export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  const [alg, n, r, p, salt, hash] = stored.split("$");
  if (alg !== "scrypt" || !salt || !hash) return false;
  const expected = Buffer.from(hash, "base64url");
  const got = await scrypt(password, Buffer.from(salt, "base64url"), expected.length, {
    N: Number(n), r: Number(r), p: Number(p), maxmem: 128 * Number(n) * Number(r) * 2,
  });
  return got.length === expected.length && timingSafeEqual(got, expected);
}
