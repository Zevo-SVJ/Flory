const levels = { debug: 10, info: 20, warn: 30, error: 40 } as const;
type Level = keyof typeof levels;

function threshold(): number {
  const l = (process.env.LOG_LEVEL ?? "info") as Level;
  return levels[l] ?? levels.info;
}

function emit(level: Level, msg: string, meta?: Record<string, unknown>) {
  if (levels[level] < threshold()) return;
  const line = JSON.stringify({ t: new Date().toISOString(), level, msg, ...meta });
  (level === "error" ? process.stderr : process.stdout).write(line + "\n");
}

export const log = {
  debug: (m: string, meta?: Record<string, unknown>) => emit("debug", m, meta),
  info: (m: string, meta?: Record<string, unknown>) => emit("info", m, meta),
  warn: (m: string, meta?: Record<string, unknown>) => emit("warn", m, meta),
  error: (m: string, meta?: Record<string, unknown>) => emit("error", m, meta),
};

export function errMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
