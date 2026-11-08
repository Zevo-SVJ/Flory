import { describe, expect, it } from "vitest";
import { decrypt, encrypt } from "@/lib/crypto";
import { hashPassword, verifyPassword } from "@/lib/password";

describe("crypto", () => {
  it("round-trips and uses a fresh IV", () => {
    const a = encrypt("123:secret-token");
    expect(a).not.toContain("secret-token");
    expect(decrypt(a)).toBe("123:secret-token");
    expect(encrypt("x")).not.toBe(encrypt("x"));
  });
  it("rejects tampered ciphertext", () => {
    const parts = encrypt("hello").split(":");
    parts[3] = Buffer.from("tampered").toString("base64url");
    expect(() => decrypt(parts.join(":"))).toThrow();
  });
});

describe("password", () => {
  it("verifies correct and rejects wrong passwords", async () => {
    const h = await hashPassword("correct horse battery");
    expect(await verifyPassword("correct horse battery", h)).toBe(true);
    expect(await verifyPassword("wrong horse battery!", h)).toBe(false);
    expect(await verifyPassword("x", "garbage")).toBe(false);
  });
  it("enforces minimum length", async () => {
    await expect(hashPassword("short")).rejects.toThrow(/at least/);
  });
});
