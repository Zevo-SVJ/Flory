import { NextResponse } from "next/server";
import { getUser } from "@/lib/auth/session";
import { getChannel } from "@/lib/services/channels";
import { getBot } from "@/lib/services/credentials";

export const dynamic = "force-dynamic";

/** Authenticated avatar proxy: the bot token never reaches the browser. */
export async function GET(_: Request, ctx: { params: Promise<{ id: string }> }) {
  if (!(await getUser())) return new NextResponse(null, { status: 401 });
  const { id } = await ctx.params;
  if (!/^[0-9a-f-]{36}$/.test(id)) return new NextResponse(null, { status: 404 });
  const ch = await getChannel(id);
  const b = await getBot();
  if (!ch?.photo_file_id || !b) return new NextResponse(null, { status: 404 });
  try {
    const f = await b.bot.getFile(ch.photo_file_id);
    if (!f.file_path) return new NextResponse(null, { status: 404 });
    const r = await b.bot.downloadFile(f.file_path);
    if (!r.ok) return new NextResponse(null, { status: 404 });
    return new NextResponse(r.body, { headers: { "content-type": r.headers.get("content-type") ?? "image/jpeg", "cache-control": "private, max-age=3600" } });
  } catch {
    return new NextResponse(null, { status: 404 });
  }
}
