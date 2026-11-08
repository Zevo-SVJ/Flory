export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  // Not during `next build`, and only when a database is configured.
  if (process.env.NEXT_PHASE === "phase-production-build" || !process.env.DATABASE_URL) return;
  const { inlineMode } = await import("./lib/env");
  if (!inlineMode()) return; // Docker mode: the worker runs migrations
  const { ensureReady } = await import("./lib/bootstrap");
  await ensureReady();
}
