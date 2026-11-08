import Link from "next/link";
import { query } from "@/lib/db";
import { listPosts, overviewCounts } from "@/lib/services/analytics";
import { getSystemStatus } from "@/lib/services/status";
import { ago, n, snippet } from "@/lib/fmt";
import { Empty, Metric, Notice, PageHeader, Panel, Stat, StatGrid } from "@/components/ui";
import { AutoRefresh } from "@/components/client";

export const metadata = { title: "Overview" };

export default async function Overview() {
  const [c, sys, posts, logs] = await Promise.all([
    overviewCounts(),
    getSystemStatus(),
    listPosts({ limit: 8 }),
    query<{ created_at: Date; level: string; message: string; category: string }>("SELECT created_at, level, message, category FROM activity_logs ORDER BY id DESC LIMIT 8"),
  ]);
  const alerts: string[] = [];
  if (!sys.bot) alerts.push("No bot configured. Add the token in Settings to start monitoring.");
  if (sys.inline && sys.scheduler && (!sys.scheduler.installed || !sys.scheduler.lastTick || Date.now() - new Date(sys.scheduler.lastTick).getTime() > 5 * 60_000)) {
    alerts.push(sys.scheduler.installed ? "The scheduler has not run for over 5 minutes: failed events/jobs are not being retried. See Settings." : "The scheduler is not installed: retries and maintenance do not run. Open Settings → Scheduler.");
  }
  if (!sys.worker.ok) alerts.push(`Worker: ${sys.worker.detail}. Automatic detection is not running.`);
  if (sys.webhook && "error" in sys.webhook) alerts.push(`Webhook check failed: ${sys.webhook.error}`);
  if (sys.webhook && "lastError" in sys.webhook && sys.webhook.lastError) alerts.push(`Telegram reports a webhook delivery error: ${sys.webhook.lastError}`);
  if (c.channels > c.connected) alerts.push(`${c.channels - c.connected} channel(s) are not connected. See My Channels.`);
  if (c.jobs_failed_24h > 0) alerts.push(`${c.jobs_failed_24h} automation job(s) failed in the last 24 h. See Activity Logs.`);

  return (
    <>
      <AutoRefresh seconds={20} />
      <PageHeader title="Overview" sub="Live state of monitoring, automation and the Telegram connection." />
      {alerts.length > 0 && (
        <div className="mb-6 space-y-2">{alerts.map((a) => <Notice key={a} title={a} />)}</div>
      )}
      <StatGrid cols={5}>
        <Stat label="Channels" value={`${c.connected}/${c.channels}`} hint="connected / total" />
        <Stat label="Posts detected 24h" value={n(c.posts_24h)} hint={`${n(c.posts_total)} total`} />
        <Stat label="Reactions sent 24h" value={n(c.reactions_done_24h)} hint="by your bot" />
        <Stat label="Failed jobs 24h" value={n(c.jobs_failed_24h)} />
        <Stat label="Events pending" value={n(c.events_pending)} hint={sys.lastWebhookAt ? `last webhook ${ago(sys.lastWebhookAt)}` : "no webhook yet"} />
      </StatGrid>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Panel title="Latest posts" flush right={<Link href="/posts" className="text-[12px] text-mute hover:text-fg">Post Manager →</Link>}>
          {posts.length === 0 ? <Empty>No post yet. Posts appear here the moment Telegram delivers them.</Empty> : (
            <div className="overflow-x-auto"><table className="tbl">
              <thead><tr><th>Post</th><th>Channel</th><th className="text-right">Views</th><th className="text-right">Reactions</th></tr></thead>
              <tbody>{posts.map((p) => (
                <tr key={p.id}>
                  <td className="max-w-[260px]"><Link href={`/posts/${p.id}`} className="hover:text-accent"><span className="tag mr-2">{p.media_type}</span>{snippet(p.text, 48) || `#${p.message_id}`}</Link></td>
                  <td className="text-mute">{p.channel_title}</td>
                  <td className="text-right"><Metric v={p.views} /></td>
                  <td className="text-right"><Metric v={p.reactions_total || null} /></td>
                </tr>))}</tbody>
            </table></div>)}
        </Panel>

        <div className="space-y-6">
          <Panel title="System" flush>
            <dl className="divide-y divide-line2 text-[13px]">
              <Row k="Bot" v={sys.bot ? `@${sys.bot.username}` : "Not configured"} ok={!!sys.bot} />
              <Row k={sys.inline ? "Runtime" : "Worker"} v={sys.worker.ok ? `${sys.inline ? "Serverless" : "Running"}${sys.worker.uptime != null ? ` · up ${Math.round(sys.worker.uptime / 60)} min` : ""}` : sys.worker.detail} ok={sys.worker.ok} />
              <Row k="Webhook" v={!sys.webhook ? "—" : "error" in sys.webhook ? "Check failed" : `${sys.webhook.pending} pending at Telegram`} ok={!!sys.webhook && !("error" in sys.webhook) && !sys.webhook.lastError} />
              <Row k="MTProto (views)" v={sys.inline ? "Not available in serverless mode" : sys.mtproto ? `Account ${sys.mtproto.username ? "@" + sys.mtproto.username : sys.mtproto.name ?? ""}` : "Not configured · views unavailable"} ok={!!sys.mtproto} warn={!sys.mtproto || sys.inline} />
            </dl>
          </Panel>
          <Panel title="Recent activity" flush right={<Link href="/logs" className="text-[12px] text-mute hover:text-fg">All logs →</Link>}>
            {logs.rows.length === 0 ? <Empty>Nothing yet.</Empty> : (
              <ul className="divide-y divide-line2">{logs.rows.map((l, i) => (
                <li key={i} className="flex gap-3 px-4 py-2 text-[12.5px]">
                  <span className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${l.level === "error" ? "bg-danger" : l.level === "warn" ? "bg-warn" : "bg-dim"}`} />
                  <span className="min-w-0 flex-1 text-mute"><span className="text-fg">{snippet(l.message, 80)}</span></span>
                  <span className="num shrink-0 text-dim">{ago(l.created_at)}</span>
                </li>))}</ul>)}
          </Panel>
        </div>
      </div>
    </>
  );
}

function Row({ k, v, ok, warn }: { k: string; v: string; ok: boolean; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2.5">
      <dt className="text-mute">{k}</dt>
      <dd className="flex items-center gap-2 text-right"><span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-accent" : warn ? "bg-warn" : "bg-danger"}`} />{v}</dd>
    </div>
  );
}
