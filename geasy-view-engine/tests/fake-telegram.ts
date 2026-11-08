import http from "node:http";

export type Call = { method: string; params: Record<string, any> };

/** Minimal Bot API double: records calls, serves canned chats, can inject failures. */
export class FakeTelegram {
  calls: Call[] = [];
  chats = new Map<number, { type: string; title: string; username?: string; available_reactions?: any[] }>();
  botStatusIn = new Map<number, string>();
  failures: Record<string, Array<{ code: number; description: string; retry_after?: number }>> = {};
  server!: http.Server;
  BOT_ID = 4242;

  async start(port = 18997) {
    this.server = http.createServer(async (req, res) => {
      const chunks: Buffer[] = [];
      for await (const c of req) chunks.push(c as Buffer);
      const params = chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : {};
      const method = req.url!.split("/").pop()!;
      this.calls.push({ method, params });
      const send = (obj: unknown, code = 200) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(obj)); };
      const fail = this.failures[method]?.shift();
      if (fail) return send({ ok: false, error_code: fail.code, description: fail.description, parameters: fail.retry_after ? { retry_after: fail.retry_after } : undefined }, fail.code);
      const ok = (result: unknown) => send({ ok: true, result });
      const err = (code: number, description: string) => send({ ok: false, error_code: code, description }, code);
      switch (method) {
        case "getMe": return ok({ id: this.BOT_ID, is_bot: true, first_name: "Geasy", username: "geasy_test_bot" });
        case "setWebhook": case "deleteWebhook": return ok(true);
        case "getWebhookInfo": return ok({ url: "https://geasy.test/tg/webhook/x", pending_update_count: 0 });
        case "getChat": {
          const key = typeof params.chat_id === "string" ? [...this.chats.entries()].find(([, c]) => `@${c.username}` === params.chat_id)?.[0] : params.chat_id;
          const c = key !== undefined ? this.chats.get(key) : undefined;
          if (!c) return err(400, "Bad Request: chat not found");
          return ok({ id: key, ...c });
        }
        case "getChatMember": return ok({ status: this.botStatusIn.get(params.chat_id) ?? "left", user: { id: params.user_id } });
        case "getChatMemberCount": return ok(1234);
        case "setMessageReaction": case "sendMessage": return ok(method === "sendMessage" ? { message_id: 1 } : true);
        default: return err(404, "Not Found");
      }
    });
    await new Promise<void>((r) => this.server.listen(port, "127.0.0.1", r));
  }
  stop() { return new Promise<void>((r) => this.server.close(() => r())); }
  count(method: string) { return this.calls.filter((c) => c.method === method).length; }
}
