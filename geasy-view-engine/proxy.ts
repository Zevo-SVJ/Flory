import { NextResponse, type NextRequest } from "next/server";

/** First line of defence: no session cookie → /login. The cookie is fully validated server-side by requireUser(). */
export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  // Public by design: login page, health, Telegram webhook and scheduler tick (both authenticated by their own secrets).
  if (pathname === "/login" || pathname === "/api/health" || pathname.startsWith("/tg/webhook/") || pathname.startsWith("/api/cron/")) return NextResponse.next();
  if (!req.cookies.get("geasy_session")?.value) {
    if (pathname.startsWith("/api/")) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg).*)"],
};
