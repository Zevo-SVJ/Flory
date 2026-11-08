import { describe, expect, it } from "vitest";
import { parseTelegramRef, TelegramRefError, buildPostUrl } from "@/lib/telegram/url";

describe("parseTelegramRef", () => {
  it.each([
    ["https://t.me/channelname/123", { username: "channelname", messageId: 123 }],
    ["t.me/channelname/123?single", { username: "channelname", messageId: 123 }],
    ["https://t.me/s/channelname/45", { username: "channelname", messageId: 45 }],
    ["https://telegram.me/channelname", { username: "channelname" }],
    ["@channelname", { username: "channelname" }],
    ["channelname", { username: "channelname" }],
    ["https://t.me/c/1234567890/123", { internalId: "1234567890", messageId: 123 }],
    ["https://t.me/c/1234567890/7/123", { internalId: "1234567890", messageId: 123 }],
    ["https://t.me/c/1234567890", { internalId: "1234567890" }],
    ["tg://resolve?domain=channelname&post=9", { username: "channelname", messageId: 9 }],
  ])("%s", (input, expected) => {
    expect(parseTelegramRef(input)).toEqual(expected);
  });

  it.each([
    ["", "empty"],
    ["https://t.me/+AbCdEf123", "invite_link"],
    ["https://t.me/joinchat/AAAA", "invite_link"],
    ["https://example.com/channelname/1", "unsupported"],
    ["https://t.me/ab/1", "invalid"],
    ["https://t.me/channelname/abc", "invalid"],
    ["https://t.me/channelname/0", "invalid"],
    ["https://t.me/c/abc/1", "invalid"],
    ["https://t.me/addstickers/pack", "invalid"],
    ["tg://join?invite=xyz", "unsupported"],
  ])("rejects %s", (input, code) => {
    try {
      parseTelegramRef(input);
      throw new Error("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(TelegramRefError);
      expect((e as TelegramRefError).code).toBe(code);
    }
  });

  it("builds post urls", () => {
    expect(buildPostUrl({ username: "abc_def", tg_chat_id: -1001 }, 5)).toBe("https://t.me/abc_def/5");
    expect(buildPostUrl({ username: null, tg_chat_id: -1001234567890 }, 5)).toBe("https://t.me/c/1234567890/5");
  });
});
