/** Dependency-free SVG charts. Null values break the line: gaps are shown, never interpolated. */
export type Series = { name: string; color: string; points: Array<{ x: number; y: number | null }> };

export const PALETTE = ["#C7F36B", "#7CB7FF", "#F5B84B", "#FF7B7B", "#9298A6", "#5ED3C3"];

function niceMax(v: number) {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  const m = v / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}

const fmtTick = (v: number) => (v >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${+(v / 1e3).toFixed(1)}k` : String(Math.round(v)));

export function LineChart({ series, height = 180, empty = "No data yet" }: { series: Series[]; height?: number; empty?: string }) {
  const pts = series.flatMap((s) => s.points.filter((p) => p.y != null) as Array<{ x: number; y: number }>);
  if (pts.length === 0) {
    return <div className="flex items-center justify-center text-[13px] text-mute" style={{ height }}>{empty}</div>;
  }
  const W = 640, H = height, L = 40, R = 8, T = 8, B = 22;
  const xs = pts.map((p) => p.x);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const yMax = niceMax(Math.max(...pts.map((p) => p.y)));
  const sx = (x: number) => (x1 === x0 ? (L + W - R) / 2 : L + ((x - x0) / (x1 - x0)) * (W - L - R));
  const sy = (y: number) => T + (1 - y / yMax) * (H - T - B);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * yMax);
  const xt = x1 === x0 ? [x0] : [0, 1, 2, 3].map((i) => x0 + ((x1 - x0) * i) / 3);
  const fmtX = (x: number) => new Date(x).toLocaleString("en-GB", { month: "short", day: "numeric", ...(x1 - x0 < 2 * 86400_000 ? { hour: "2-digit", minute: "2-digit" } : {}), timeZone: "UTC" });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" style={{ height: "auto", aspectRatio: `${W}/${H}` }}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} stroke="#1d212c" />
          <text x={L - 6} y={sy(t) + 3} textAnchor="end" fontSize="10" fill="#5d6372" fontFamily="var(--font-mono)">{fmtTick(t)}</text>
        </g>
      ))}
      {xt.map((x, i) => (
        <text key={i} x={sx(x)} y={H - 6} textAnchor={xt.length === 1 ? "middle" : i === 0 ? "start" : i === xt.length - 1 ? "end" : "middle"} fontSize="10" fill="#5d6372" fontFamily="var(--font-mono)">{fmtX(x)}</text>
      ))}
      {series.map((s) => {
        const segs: string[] = [];
        let cur = "";
        for (const p of s.points) {
          if (p.y == null) { if (cur) segs.push(cur); cur = ""; continue; }
          cur += `${cur ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`;
        }
        if (cur) segs.push(cur);
        const single = s.points.filter((p) => p.y != null).length === 1;
        return (
          <g key={s.name}>
            {segs.map((d, i) => <path key={i} d={d} fill="none" stroke={s.color} strokeWidth="1.75" strokeLinejoin="round" />)}
            {(s.points.length <= 40 || single) &&
              s.points.filter((p) => p.y != null).map((p, i) => (
                <circle key={i} cx={sx(p.x)} cy={sy(p.y as number)} r="2.5" fill="#101218" stroke={s.color} strokeWidth="1.5">
                  <title>{`${s.name}: ${p.y} · ${fmtX(p.x)}`}</title>
                </circle>
              ))}
          </g>
        );
      })}
    </svg>
  );
}

export function Legend({ items }: { items: Array<{ name: string; color: string }> }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-mute">
      {items.map((i) => (
        <span key={i.name} className="inline-flex items-center gap-1.5">
          <span className="inline-block h-[3px] w-3 rounded-full" style={{ background: i.color }} />{i.name}
        </span>
      ))}
    </div>
  );
}

export function BarList({ rows, unit = "" }: { rows: Array<{ label: string; sub?: string; value: number | null }>; unit?: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value ?? 0));
  if (rows.length === 0) return <div className="py-8 text-center text-[13px] text-mute">No data yet</div>;
  return (
    <ul className="divide-y divide-line2">
      {rows.map((r, i) => (
        <li key={i} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 px-4 py-2.5">
          <div className="min-w-0">
            <div className="truncate text-[13px]">{r.label}</div>
            {r.sub && <div className="truncate text-[11px] text-mute">{r.sub}</div>}
          </div>
          <div className="num text-[13px]">{r.value == null ? "—" : new Intl.NumberFormat("en-US").format(r.value)}{unit}</div>
          <div className="col-span-2 h-[3px] rounded-full bg-line2">
            <div className="h-full rounded-full bg-accent" style={{ width: `${((r.value ?? 0) / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
