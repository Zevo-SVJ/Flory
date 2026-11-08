import { after, NextResponse } from "next/server";
import { safeEqual } from "@/lib/crypto";
import { env } from "@/lib/env";
import { log, errMessage } from "@/lib/logger";
import { runTick } from "@/lib/services/tick";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

async function handle(req: Request) {
  const auth = req.headers.get("authorization") ?? "";
  if (!safeEqual(auth, `Bearer ${env().CRON_SECRET}`)) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  // Answer immediately (pg_net has a short client timeout) and do the work after the response.
  after(() => runTick().catch((e) => log.error("tick failed", { error: errMessage(e) })));
  return NextResponse.json({ accepted: true }, { status: 202 });
}

export const POST = handle;
export const GET = handle;
