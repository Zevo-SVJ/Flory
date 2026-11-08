// Dev/e2e helper: a local Bot API double with two channels. Not used in production.
import { FakeTelegram } from "../fake-telegram";

const tg = new FakeTelegram();
await tg.start(18999); // e2e uses 18999, vitest uses 18997
tg.chats.set(-1001111111111, { type: "channel", title: "Geasy One", username: "geasy_one" });
tg.chats.set(-1002222222222, { type: "channel", title: "Private Desk", available_reactions: [{ type: "emoji", emoji: "👍" }, { type: "emoji", emoji: "🔥" }] });
tg.botStatusIn.set(-1001111111111, "administrator");
tg.botStatusIn.set(-1002222222222, "left");
console.log("fake telegram on 18999");
