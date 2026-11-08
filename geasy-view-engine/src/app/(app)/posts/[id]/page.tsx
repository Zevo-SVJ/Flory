import Link from "next/link";
import { notFound } from "next/navigation";
import { reactNowAction, refreshPostAction, toggleTrackingAction } from "@/app/actions";
import { ActionForm, EmojiPicker, SubmitButton } from "@/components/client";
import { Legend, LineChart, PALETTE, type Series } from "@/components/charts";
import { Metric, Notice, OriginTag, PageHeader, Panel, Stat, StatGrid } from "@/components/ui";
import { postReactions, postSeries } from "@/lib/services/analytics";
import { getChannel } from "@/lib/services/channels";
import { getBot } from "@/lib/services/credentials";
import { getPost } from "@/lib/services/posts";
import { inlineMode } from "@/lib/env";
import { metricsSource } from "@/lib/services/statsjobs";
import { TELEGRAM_REACTION_EMOJI } from "@/lib/telegram/bot";
import { buildPostUrl } from "@/lib/telegram/url";
import { ago, dt, n } from "@/lib/fmt";

export const metadata = { title: "Post" };

export default async function PostDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const post = await getPost(id);
  if (!post) notFound();
  const [ch, series, reactions, src, bot] = await Promise.all([getChannel(post.channel_id), postSeries(id), postReactions(id), metricsSource(), getBot()]);
  if (!ch) notFound();

  const mt = series.filter((s) => s.source === "mtproto");
  const last = mt.at(-1);
  const emojis = [...new Set(series.flatMap((s) => Object.keys(s.reactions)))];
  const topEmojis = reactions.slice(0, 5).map((r) => r.reaction);
  const viewsSeries: Series[] = [{ name: "Views", color: PALETTE[0], points: mt.map((s) => ({ x: +new Date(s.captured_at), y: s.views })) }];
  const fwdSeries: Series[] = [{ name: "Forwards", color: PALETTE[1], points: mt.map((s) => ({ x: +new Date(s.captured_at), y: s.forwards })) }];
  const reactSeries: Series[] = [
    { name: "Total", color: PALETTE[0], points: series.map((s) => ({ x: +new Date(s.captured_at), y: s.reactions_total })) },
    ...topEmojis.filter((e) => emojis.includes(e)).slice(0, 4).map((e, i) => ({ name: e, color: PALETTE[i + 1], points: series.map((s) => ({ x: +new Date(s.captured_at), y: s.reactions_total == null ? null : (s.reactions[e] ?? 0) })) })),
  ];
  const total = reactions.reduce((a, r) => a + r.count, 0);
  const url = buildPostUrl(ch, post.message_id);

  return (
    <>
      <PageHeader
        title={`Post #${post.message_id}`}
        sub={<><Link className="hover:text-fg" href="/posts">Post Manager</Link> / {ch.title} · <span className="tag">{post.media_type}</span>{post.source === "manual" && <> <span className="tag">registered by URL</span></>}</>}
        actions={<>
          {url && <a className="btn btn-sm" href={url} target="_blank" rel="noreferrer noopener">Open in Telegram ↗</a>}
          {src && <form action={refreshPostAction}><input type="hidden" name="postId" value={post.id} /><SubmitButton className="btn btn-sm" pendingText="Refreshing…">Refresh now</SubmitButton></form>}
        </>}
      />

      {!src && (
        <div className="mb-5"><Notice tone="info" title="Views and forwards unavailable">The Bot API does not expose them. {inlineMode() ? "This free serverless deployment cannot read them (they need a permanent MTProto connection)." : "Connect a Telegram account (MTProto) in Settings to read real values."} Reaction counts below come from Telegram via the bot when it receives updates for this channel.</Notice></div>)}
      {post.source === "manual" && !src && post.media_type === "unknown" && (
        <div className="mb-5"><Notice title="Existence of this post is not verified">The Bot API cannot read an existing message by id, so this registration could not be checked against Telegram.</Notice></div>)}
      {!post.tracking_enabled && <div className="mb-5"><Notice title="Tracking is stopped for this post">It will not be polled until you resume it.</Notice></div>}

      <StatGrid cols={5}>
        <Stat label="Views" value={<Metric v={last?.views} reason="Needs MTProto" />} origin={last ? "telegram" : "unavailable"} hint={last ? `at ${ago(last.captured_at)}` : undefined} />
        <Stat label="Reactions" value={<Metric v={reactions.length ? total : null} reason="No reaction data received yet" />} origin={reactions.length ? "telegram" : "unavailable"} hint={reactions[0] ? `via ${reactions[0].source === "mtproto" ? "MTProto" : "Bot API"}` : undefined} />
        <Stat label="Forwards" value={<Metric v={last?.forwards} reason="Needs MTProto" />} origin={last ? "telegram" : "unavailable"} />
        <Stat label="Published" value={<span className="text-[15px]">{post.published_at ? dt(post.published_at) : "—"}</span>} hint={post.is_edited ? `edited ${ago(post.edited_at)}` : undefined} />
        <Stat label="Last update" value={<span className="text-[15px]">{series.length ? ago(series.at(-1)!.captured_at) : "—"}</span>} hint={`${n(series.length)} snapshots`} />
      </StatGrid>

      {post.text && <Panel title="Content" className="mt-6"><p className="whitespace-pre-wrap text-[13.5px] leading-relaxed">{post.text}</p>
        {post.is_forwarded && <p className="mt-2 text-[12px] text-mute">Forwarded{(post.forward_origin as { from?: string } | null)?.from ? ` from ${(post.forward_origin as { from?: string }).from}` : ""}</p>}</Panel>}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel title="Views over time" right={<OriginTag kind={mt.length ? "telegram" : "unavailable"} />}><LineChart series={viewsSeries} empty={src ? "Waiting for first snapshot" : "Unavailable without MTProto"} /></Panel>
        <Panel title="Reaction growth" right={<OriginTag kind={series.some((s) => s.reactions_total != null) ? "telegram" : "unavailable"} />}>
          <LineChart series={reactSeries} empty="No reaction data received yet" />
          <div className="mt-2"><Legend items={reactSeries.map((s) => ({ name: s.name, color: s.color }))} /></div>
        </Panel>
        {mt.length > 0 && <Panel title="Forwards over time" right={<OriginTag kind="telegram" />}><LineChart series={fwdSeries} /></Panel>}
        <Panel title="Reaction breakdown" flush>
          {reactions.length === 0 ? <div className="px-4 py-8 text-center text-[13px] text-mute">No reactions recorded.</div> : (
            <table className="tbl"><thead><tr><th>Reaction</th><th className="text-right">Count</th><th className="text-right">Share</th><th>Source</th></tr></thead>
              <tbody>{reactions.map((r) => (
                <tr key={r.reaction}><td className="text-[16px]">{r.reaction.startsWith("custom:") ? <span className="tag">custom</span> : r.reaction === "paid" ? <span className="tag">paid ★</span> : r.reaction}</td>
                  <td className="num text-right">{n(r.count)}</td><td className="num text-right text-mute">{total ? Math.round((r.count / total) * 100) : 0}%</td>
                  <td className="text-mute">{r.source === "mtproto" ? "MTProto" : "Bot API"} · {ago(r.updated_at)}</td></tr>))}</tbody></table>)}
        </Panel>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel title={`React as ${bot ? "@" + bot.identity.username : "bot"}`}>
          {ch.status !== "connected" ? <p className="text-[13px] text-mute">The bot is not connected to this channel.</p> : (
            <ActionForm action={reactNowAction}>
              <input type="hidden" name="postId" value={post.id} />
              <p className="mb-3 text-[12.5px] text-mute">One reaction from your authorised bot. Every action is logged under the bot's identity. Telegram keeps a single reaction per account per post.</p>
              <EmojiPicker emojis={TELEGRAM_REACTION_EMOJI} disabled={ch.available_reactions ? TELEGRAM_REACTION_EMOJI.filter((e) => !ch.available_reactions!.includes(e)) : []} />
              <div className="mt-3"><SubmitButton pendingText="Queuing…">Send reaction</SubmitButton></div>
            </ActionForm>)}
        </Panel>
        <Panel title="Tracking">
          <p className="text-[13px] text-mute">{post.tracking_enabled ? "Statistics are collected on the schedule of this channel (see Automation)." : "Statistics collection is stopped."}</p>
          <form action={toggleTrackingAction} className="mt-3"><input type="hidden" name="postId" value={post.id} /><input type="hidden" name="value" value={String(!post.tracking_enabled)} />
            <button className="btn">{post.tracking_enabled ? "Stop tracking" : "Resume tracking"}</button></form>
        </Panel>
      </div>
    </>
  );
}
