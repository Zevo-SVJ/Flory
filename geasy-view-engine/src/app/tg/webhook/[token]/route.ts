import { after, NextResponse } from "next/server";
import { webhookPathToken } from "@/lib/services/credentials";
import { ingestUpdate, processWebhookEvent, verifyWebhookRequest, type TgUpdate } from "@/lib/services/updates";
import { log, errMessage } from "@/lib/logger";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/** Telegram webhook (serverless mode). Persist first, answer 200, process after the response. */
export async function POST(req: Request, ctx: { params: Promise<{ token: string }> }) {
  const { token } = await ctx.params;
  if (!/^[A-Za-z0-9]{8,64}$/.test(token)) return NextResponse.json({ error: "not found" }, { status: 404 });

  let authorised: boolean;
  try {
    authorised = await verifyWebhookRequest(token, req.headers.get("x-telegram-bot-api-secret-token") ?? undefined, webhookPathToken);
  } catch (e) {
    log.error("webhook auth check failed (db?)", { error: errMessage(e) });
    return NextResponse.json({ error: "unavailable" }, { status: 503 }); // Telegram retries
  }
  if (!authorised) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const text = await req.text();
  if (text.length > 1_000_000) return NextResponse.json({ error: "payload too large" }, { status: 413 });
  let update: TgUpdate;
  try {
    update = JSON.parse(text);
    if (!Number.isSafeInteger(update?.update_id)) throw new Error("no update_id");
  } catch {
    return NextResponse.json({ error: "bad payload" }, { status: 400 });
  }

  try {
    const r = await ingestUpdate(update);
    if (r.eventId != null) {
      const id = r.eventId;
      // Failures leave the event 'pending'; the scheduler retries with backoff.
      after(() => processWebhookEvent(id).catch((e) => log.warn("event processing failed, will retry", { id, error: errMessage(e) })));
    }
    return NextResponse.json({ ok: true, duplicate: r.duplicate });
  } catch (e) {
    log.error("ingest failed", { error: errMessage(e) });
    return NextResponse.json({ error: "unavailable" }, { status: 503 }); // not persisted → Telegram redelivers
  }
}
