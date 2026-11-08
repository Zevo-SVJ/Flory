import { env } from "../env";
import { log, errMessage } from "../logger";

export class TelegramApiError extends Error {
  constructor(
    public method: string,
    public code: number,
    public description: string,
    public retryAfter?: number,
  ) {
    super(`Telegram ${method} failed (${code}): ${description}`);
  }
  /** Errors that retrying cannot fix. */
  get permanent(): boolean {
    return this.code >= 400 && this.code < 500 && this.code !== 429 && this.code !== 408;
  }
}

export type TgChat = {
  id: number;
  type: string;
  title?: string;
  username?: string;
  photo?: { small_file_id: string; big_file_id: string };
  available_reactions?: Array<{ type: string; emoji?: string; custom_emoji_id?: string }>;
};

export type TgChatMember = { status: string; user: { id: number }; [k: string]: unknown };
export type TgUser = { id: number; is_bot: boolean; first_name: string; username?: string };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export class TelegramBot {
  constructor(
    private token: string,
    private base: string = env().TELEGRAM_API_BASE,
  ) {}

  /** Calls a Bot API method. Retries network errors and 5xx with exponential backoff; 429 is surfaced with retryAfter. */
  async call<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    let lastErr: unknown;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await fetch(`${this.base}/bot${this.token}/${method}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(params),
          signal: AbortSignal.timeout(15_000),
        });
        let body: { ok: boolean; result?: T; error_code?: number; description?: string; parameters?: { retry_after?: number } };
        try {
          body = await res.json();
        } catch {
          throw new TelegramApiError(method, res.status, `non-JSON response (HTTP ${res.status})`);
        }
        if (body.ok) return body.result as T;
        const err = new TelegramApiError(method, body.error_code ?? res.status, body.description ?? "unknown", body.parameters?.retry_after);
        if (err.code >= 500 && attempt < 2) {
          lastErr = err;
        } else {
          throw err;
        }
      } catch (e) {
        if (e instanceof TelegramApiError && !(e.code >= 500)) throw e;
        lastErr = e;
        if (attempt === 2) break;
      }
      const delay = 500 * 2 ** attempt;
      log.warn("telegram call retry", { method, attempt: attempt + 1, delay, error: errMessage(lastErr) });
      await sleep(delay);
    }
    throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
  }

  getMe = () => this.call<TgUser>("getMe");
  getChat = (chatId: number | string) => this.call<TgChat>("getChat", { chat_id: chatId });
  getChatMemberCount = (chatId: number | string) => this.call<number>("getChatMemberCount", { chat_id: chatId });
  getChatMember = (chatId: number | string, userId: number) => this.call<TgChatMember>("getChatMember", { chat_id: chatId, user_id: userId });

  setWebhook(url: string, secretToken: string) {
    return this.call<true>("setWebhook", {
      url,
      secret_token: secretToken,
      allowed_updates: ["channel_post", "edited_channel_post", "message_reaction_count", "my_chat_member"],
      max_connections: 20,
    });
  }
  deleteWebhook = () => this.call<true>("deleteWebhook", { drop_pending_updates: false });
  getWebhookInfo = () =>
    this.call<{ url: string; pending_update_count: number; last_error_date?: number; last_error_message?: string }>("getWebhookInfo");

  setMessageReaction(chatId: number, messageId: number, emoji: string) {
    return this.call<true>("setMessageReaction", {
      chat_id: chatId,
      message_id: messageId,
      reaction: [{ type: "emoji", emoji }],
      is_big: false,
    });
  }

  sendMessage(chatId: number, text: string) {
    return this.call<{ message_id: number }>("sendMessage", { chat_id: chatId, text, parse_mode: "HTML", link_preview_options: { is_disabled: true } });
  }

  getFile = (fileId: string) => this.call<{ file_path?: string }>("getFile", { file_id: fileId });

  async downloadFile(filePath: string): Promise<Response> {
    return fetch(`${this.base}/file/bot${this.token}/${filePath}`, { signal: AbortSignal.timeout(15_000) });
  }
}

/** Emoji accepted by Telegram's setMessageReaction (Bot API docs, ReactionTypeEmoji). */
export const TELEGRAM_REACTION_EMOJI = [
  "👍", "👎", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩", "🤮", "💩", "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳",
  "❤‍🔥", "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈",
  "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂", "🤷", "🤷‍♀", "😡",
] as const;
