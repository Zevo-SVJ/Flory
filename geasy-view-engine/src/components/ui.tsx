import type { ReactNode } from "react";
import type { ChannelStatus } from "@/lib/services/channels";

export function PageHeader({ title, sub, actions }: { title: string; sub?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">{title}</h1>
        {sub && <p className="mt-1 max-w-[70ch] text-[13.5px] text-mute">{sub}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Panel({ title, right, children, className = "", flush = false }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string; flush?: boolean }) {
  return (
    <section className={`panel ${className}`}>
      {title && <div className="panel-h"><h2 className="label">{title}</h2>{right}</div>}
      <div className={flush ? "" : "p-4"}>{children}</div>
    </section>
  );
}

export type Origin = "telegram" | "calculated" | "unavailable";

const ORIGIN: Record<Origin, { text: string; cls: string; title: string }> = {
  telegram: { text: "TELEGRAM", cls: "text-accent border-accent/30", title: "Value reported by Telegram" },
  calculated: { text: "CALCULATED", cls: "text-info border-info/30", title: "Computed by GEASY from stored Telegram snapshots; not a Telegram metric" },
  unavailable: { text: "UNAVAILABLE", cls: "text-dim border-line", title: "The configured Telegram API cannot provide this value" },
};

export function OriginTag({ kind, title }: { kind: Origin; title?: string }) {
  const o = ORIGIN[kind];
  return <span className={`tag ${o.cls}`} title={title ?? o.title}>{o.text}</span>;
}

export function Stat({ label, value, hint, origin }: { label: string; value: ReactNode; hint?: ReactNode; origin?: Origin }) {
  return (
    <div className="bg-bg2 px-4 py-3.5">
      <div className="flex items-center justify-between gap-2"><span className="label">{label}</span>{origin && <OriginTag kind={origin} />}</div>
      <div className="num mt-1.5 text-[24px] font-medium leading-none tracking-tight">{value}</div>
      {hint && <div className="mt-1.5 text-[12px] text-mute">{hint}</div>}
    </div>
  );
}

export function StatGrid({ children, cols = 4 }: { children: ReactNode; cols?: 2 | 3 | 4 | 5 }) {
  const c = { 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4", 5: "sm:grid-cols-3 lg:grid-cols-5" }[cols];
  return <div className={`grid grid-cols-1 gap-px overflow-hidden rounded-md border border-line bg-line ${c}`}>{children}</div>;
}

const STATUS: Record<ChannelStatus, { text: string; dot: string }> = {
  connected: { text: "Connected", dot: "bg-accent" },
  pending: { text: "Pending", dot: "bg-warn" },
  no_access: { text: "No access", dot: "bg-danger" },
  disconnected: { text: "Disconnected", dot: "bg-danger" },
  error: { text: "Error", dot: "bg-warn" },
};

export function StatusBadge({ status }: { status: ChannelStatus }) {
  const s = STATUS[status];
  return <span className="inline-flex items-center gap-1.5 text-[12.5px]"><span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />{s.text}</span>;
}

export function Notice({ tone = "warn", title, children }: { tone?: "warn" | "danger" | "info"; title: string; children?: ReactNode }) {
  const c = { warn: "border-warn/40 text-warn", danger: "border-danger/40 text-danger", info: "border-info/40 text-info" }[tone];
  return (
    <div className={`rounded-md border bg-bg2 px-4 py-3 ${c}`}>
      <div className="text-[13px] font-medium">{title}</div>
      {children && <div className="mt-1 text-[13px] text-mute">{children}</div>}
    </div>
  );
}

export function Avatar({ id, title, hasPhoto, size = 32 }: { id: string; title: string; hasPhoto: boolean; size?: number }) {
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface text-[12px] font-medium text-mute" style={{ width: size, height: size }}>
      {title.slice(0, 1).toUpperCase()}
      {hasPhoto && /* eslint-disable-next-line @next/next/no-img-element */ <img src={`/api/channels/${id}/avatar`} alt="" className="absolute inset-0 h-full w-full object-cover" loading="lazy" />}
    </span>
  );
}

export function Toggle({ on, label }: { on: boolean; label: string }) {
  return (
    <span role="img" aria-label={`${label}: ${on ? "on" : "off"}`} className={`relative inline-block h-[18px] w-[32px] shrink-0 rounded-full border transition-colors ${on ? "border-accent bg-accent/20" : "border-line bg-bg"}`}>
      <span className={`absolute top-[2px] h-[12px] w-[12px] rounded-full transition-all ${on ? "left-[16px] bg-accent" : "left-[2px] bg-dim"}`} />
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="px-4 py-10 text-center text-[13px] text-mute">{children}</div>;
}

export function Metric({ v, reason }: { v: number | null | undefined; reason?: string }) {
  if (v == null) return <span className="num text-dim" title={reason ?? "Not provided by the configured Telegram API"}>—</span>;
  return <span className="num">{new Intl.NumberFormat("en-US").format(v)}</span>;
}
