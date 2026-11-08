import Link from "next/link";
import { BarList, LineChart, PALETTE } from "@/components/charts";
import { Empty, Metric, Notice, OriginTag, PageHeader, Panel, Stat, StatGrid } from "@/components/ui";
import { channelPerformance, reactionTotalsOverTime, subscriberSeries, topPosts, viewsTotalsOverTime } from "@/lib/services/analytics";
import { listChannels } from "@/lib/services/channels";
import { mtprotoAvailable } from "@/lib/telegram/mtproto";
import { inlineMode } from "@/lib/env";
import { n, snippet } from "@/lib/fmt";

export const metadata = { title: "Analytics" };

export default async function Analytics({ searchParams }: { searchParams: Promise<{ channel?: string; days?: string }> }) {
  const sp = await searchParams;
  const days = [7, 14, 30, 90].includes(Number(sp.days)) ? Number(sp.days) : 14;
  const channels = await listChannels();
  const sel = channels.find((c) => c.id === sp.channel);
  const cid = sel?.id ?? null;
  const [perf, views, reacts, top, subs, mt] = await Promise.all([
    channelPerformance(days), viewsTotalsOverTime(cid, days), reactionTotalsOverTime(cid, days), topPosts(cid, 10, days), cid ? subscriberSeries(cid) : Promise.resolve([]), mtprotoAvailable(),
  ]);
  const scope = cid ? perf.filter((p) => p.channel_id === cid) : perf;
  const withViews = scope.reduce((a, p) => a + p.posts_with_views, 0);
  const sumViews = scope.reduce((a, p) => a + (p.total_views ?? 0), 0);
  const avgViews = withViews ? Math.round(sumViews / withViews) : null;
  const wAvg = (k: "avg_reactions" | "avg_forwards") => { const rows = scope.filter((p) => p[k] != null && p.posts_with_views > 0); const w = rows.reduce((a, p) => a + p.posts_with_views, 0); return w ? Math.round((rows.reduce((a, p) => a + (p[k] as number) * p.posts_with_views, 0) / w) * 10) / 10 : null; };
  const href = (o: { channel?: string; days?: number }) => { const q = new URLSearchParams(); const c = "channel" in o ? o.channel : cid ?? undefined; if (c) q.set("channel", c); q.set("days", String(o.days ?? days)); return `/analytics?${q}`; };

  return (
    <>
      <PageHeader title="Analytics" sub="Telegram counters are shown as reported. Averages are calculated by GEASY from stored snapshots and labelled as such. Nothing is estimated or projected." />
      {!mt && <div className="mb-6"><Notice tone="info" title="View statistics require MTProto">{inlineMode() ? "Not available in the free serverless deployment." : "Connect a Telegram account in Settings."} Reaction analytics work with the bot alone.</Notice></div>}

      <div className="mb-5 flex flex-wrap items-center gap-2 text-[12.5px]">
        <Link href={href({ channel: undefined })} className={`btn btn-sm ${!cid ? "!border-accent" : ""}`}>All channels</Link>
        {channels.map((c) => <Link key={c.id} href={href({ channel: c.id })} className={`btn btn-sm ${cid === c.id ? "!border-accent" : ""}`}>{c.title}</Link>)}
        <span className="mx-1 h-4 w-px bg-line" />
        {[7, 14, 30, 90].map((d) => <Link key={d} href={href({ days: d })} className={`btn btn-sm ${days === d ? "!border-accent" : ""}`}>{d}d</Link>)}
      </div>

      <StatGrid cols={4}>
        <Stat label="Avg views / post" value={<Metric v={avgViews} reason="Needs MTProto data" />} origin="calculated" hint={`${n(withViews)} posts with data`} />
        <Stat label="Avg reactions / post" value={<Metric v={wAvg("avg_reactions")} />} origin="calculated" />
        <Stat label="Avg forwards / post" value={<Metric v={wAvg("avg_forwards")} />} origin="calculated" />
        <Stat label="Subscribers" value={<Metric v={sel ? sel.subscriber_count : channels.reduce((a, c) => a + (c.subscriber_count ?? 0), 0) || null} />} origin="telegram" />
      </StatGrid>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel title="Views over time" right={<OriginTag kind="calculated" title="Sum of the last snapshot per day of each tracked post" />}>
          <LineChart series={[{ name: "Total views of tracked posts", color: PALETTE[0], points: views.map((v) => ({ x: +new Date(v.day), y: v.total })) }]} empty="No view snapshots in this period" />
        </Panel>
        <Panel title="Reaction growth" right={<OriginTag kind="calculated" title="Sum of the last snapshot per day of each tracked post" />}>
          <LineChart series={[{ name: "Total reactions", color: PALETTE[1], points: reacts.map((v) => ({ x: +new Date(v.day), y: v.total })) }]} empty="No reaction data in this period" />
        </Panel>
        {cid && <Panel title="Subscribers" right={<OriginTag kind="telegram" />}><LineChart series={[{ name: "Subscribers", color: PALETTE[2], points: subs.map((s) => ({ x: +new Date(s.captured_at), y: s.subscribers })) }]} /></Panel>}
        <Panel title="Post comparison · top by views" flush>
          <BarList rows={top.map((p) => ({ label: snippet(p.text, 60) || `${p.media_type} #${p.message_id}`, sub: `${p.channel_title} · ${n(p.reactions_total)} reactions · ${n(p.forwards)} forwards`, value: p.views }))} />
        </Panel>
      </div>

      <Panel title="Channel performance" flush className="mt-6" right={<span className="text-[12px] text-mute">last {days} days</span>}>
        {perf.length === 0 ? <Empty>No channel.</Empty> : (
          <div className="overflow-x-auto"><table className="tbl">
            <thead><tr><th>Channel</th><th className="text-right">Posts</th><th className="text-right">With views</th><th className="text-right">Avg views</th><th className="text-right">Avg reactions</th><th className="text-right">Avg forwards</th></tr></thead>
            <tbody>{perf.map((p) => (<tr key={p.channel_id}><td>{p.title}</td><td className="num text-right">{n(p.posts)}</td><td className="num text-right">{n(p.posts_with_views)}</td>
              <td className="text-right"><Metric v={p.avg_views} /></td><td className="text-right"><Metric v={p.avg_reactions} /></td><td className="text-right"><Metric v={p.avg_forwards} /></td></tr>))}</tbody>
          </table></div>)}
      </Panel>
    </>
  );
}
