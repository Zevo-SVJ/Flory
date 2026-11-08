import Link from "next/link";
import { Empty, PageHeader, Panel } from "@/components/ui";
import { AutoRefresh } from "@/components/client";
import { query } from "@/lib/db";
import { dt } from "@/lib/fmt";

export const metadata = { title: "Activity Logs" };
const CATS = ["channel", "webhook", "stats", "reaction", "notify", "post", "auth", "system"];

export default async function Logs({ searchParams }: { searchParams: Promise<{ category?: string; level?: string; page?: string }> }) {
  const sp = await searchParams;
  const cat = CATS.includes(sp.category ?? "") ? sp.category! : null;
  const level = ["info", "warn", "error"].includes(sp.level ?? "") ? sp.level! : null;
  const page = Math.max(0, Number(sp.page ?? 0) || 0);
  const PAGE = 50;
  const r = await query<{ id: number; created_at: Date; level: string; category: string; action: string; actor: string; message: string; channel_title: string | null; post_id: string | null }>(
    `SELECT l.id, l.created_at, l.level, l.category, l.action, l.actor, l.message, c.title AS channel_title, l.post_id
     FROM activity_logs l LEFT JOIN channels c ON c.id=l.channel_id
     WHERE ($1::text IS NULL OR l.category=$1) AND ($2::text IS NULL OR l.level=$2)
     ORDER BY l.id DESC LIMIT $3 OFFSET $4`, [cat, level, PAGE + 1, page * PAGE]);
  const more = r.rows.length > PAGE;
  const rows = r.rows.slice(0, PAGE);
  const href = (o: Record<string, string | number | null>) => { const q = new URLSearchParams(); for (const [k, v] of Object.entries(o)) if (v != null && v !== "" && v !== 0) q.set(k, String(v)); return `/logs${q.size ? `?${q}` : ""}`; };

  return (
    <>
      {page === 0 && <AutoRefresh seconds={15} />}
      <PageHeader title="Activity Logs" sub="Every automated and manual action, with its actor. Retention is configurable in Settings." />
      <form method="get" className="mb-4 flex flex-wrap gap-2">
        <select name="category" defaultValue={cat ?? ""} className="input !w-auto" aria-label="Category"><option value="">All categories</option>{CATS.map((c) => <option key={c}>{c}</option>)}</select>
        <select name="level" defaultValue={level ?? ""} className="input !w-auto" aria-label="Level"><option value="">All levels</option><option>info</option><option>warn</option><option>error</option></select>
        <button className="btn">Filter</button>
      </form>
      <Panel flush>
        {rows.length === 0 ? <Empty>No entry.</Empty> : (
          <div className="overflow-x-auto"><table className="tbl">
            <thead><tr><th>Time</th><th>Level</th><th>Category</th><th>Actor</th><th>Message</th></tr></thead>
            <tbody>{rows.map((l) => (
              <tr key={l.id}>
                <td className="num whitespace-nowrap text-[12px] text-mute">{dt(l.created_at)}</td>
                <td><span className={`tag ${l.level === "error" ? "!border-danger/40 text-danger" : l.level === "warn" ? "!border-warn/40 text-warn" : ""}`}>{l.level}</span></td>
                <td className="text-mute">{l.category}</td>
                <td className="num text-[12px] text-mute">{l.actor}</td>
                <td className="max-w-[520px]">{l.post_id ? <Link className="hover:text-accent" href={`/posts/${l.post_id}`}>{l.message}</Link> : l.message}{l.channel_title && <span className="ml-2 text-mute">· {l.channel_title}</span>}</td>
              </tr>))}</tbody>
          </table></div>)}
        {(page > 0 || more) && (
          <div className="flex justify-between border-t border-line px-4 py-2.5 text-[12.5px]">
            {page > 0 ? <Link className="text-mute hover:text-fg" href={href({ category: cat, level, page: page - 1 })}>← Newer</Link> : <span />}
            {more && <Link className="text-mute hover:text-fg" href={href({ category: cat, level, page: page + 1 })}>Older →</Link>}
          </div>)}
      </Panel>
    </>
  );
}
