import Link from "next/link";
import { connectAndLookupAction, lookupPostAction } from "@/app/actions";
import { PostLookupForm } from "@/components/client";
import { Empty, Metric, Notice, PageHeader, Panel } from "@/components/ui";
import { listPosts } from "@/lib/services/analytics";
import { listChannels } from "@/lib/services/channels";
import { mtprotoAvailable } from "@/lib/telegram/mtproto";
import { ago, dt, snippet } from "@/lib/fmt";
import { buildPostUrl } from "@/lib/telegram/url";

export const metadata = { title: "Post Manager" };

export default async function PostsPage({ searchParams }: { searchParams: Promise<{ channel?: string; page?: string }> }) {
  const sp = await searchParams;
  const page = Math.max(0, Number(sp.page ?? 0) || 0);
  const PAGE = 30;
  const channelId = sp.channel && /^[0-9a-f-]{36}$/.test(sp.channel) ? sp.channel : undefined;
  const [channels, posts, mt] = await Promise.all([listChannels(), listPosts({ channelId, limit: PAGE + 1, offset: page * PAGE }), mtprotoAvailable()]);
  const more = posts.length > PAGE;
  const rows = posts.slice(0, PAGE);
  const qs = (o: Record<string, string | number | undefined>) => {
    const p = new URLSearchParams(Object.entries(o).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)]));
    return p.size ? `?${p}` : "";
  };

  return (
    <>
      <PageHeader title="Post Manager" sub="Paste the URL of one post to load and track it, or browse every post detected automatically." />
      {!mt && (
        <div className="mb-6"><Notice tone="info" title="Views and forward counts need MTProto">
          The Bot API cannot read an existing post, nor its views or forwards. Without a connected Telegram account, a post looked up here is tracked from the moment you register it (reaction counts via the bot); its text and views stay “—”. See Settings.
        </Notice></div>)}
      <Panel title="Look up a post" className="mb-6"><PostLookupForm lookup={lookupPostAction} connect={connectAndLookupAction} /></Panel>

      <Panel flush title="Posts" right={
        <form className="flex items-center gap-2" method="get">
          <select name="channel" defaultValue={channelId ?? ""} className="input !h-7 !w-auto text-[12px]" aria-label="Filter by channel">
            <option value="">All channels</option>{channels.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <button className="btn btn-sm">Filter</button>
        </form>}>
        {rows.length === 0 ? <Empty>No post.</Empty> : (
          <div className="overflow-x-auto"><table className="tbl">
            <thead><tr><th>Post</th><th>Channel</th><th>Published</th><th className="text-right">Views</th><th className="text-right">Forwards</th><th className="text-right">Reactions</th><th>Updated</th></tr></thead>
            <tbody>{rows.map((p) => (
              <tr key={p.id}>
                <td className="max-w-[300px]">
                  <Link href={`/posts/${p.id}`} className="block truncate hover:text-accent">
                    <span className="tag mr-2">{p.media_type}</span>{p.is_forwarded && <span className="tag mr-2">fwd</span>}{p.is_edited && <span className="tag mr-2">edited</span>}
                    {snippet(p.text, 60) || <span className="num text-mute">#{p.message_id}</span>}
                  </Link>
                </td>
                <td className="text-mute"><a className="hover:text-fg" href={buildPostUrl({ username: p.channel_username, tg_chat_id: p.tg_chat_id }, p.message_id)} target="_blank" rel="noreferrer noopener">{p.channel_title}</a></td>
                <td className="whitespace-nowrap text-mute">{p.published_at ? dt(p.published_at) : "—"}</td>
                <td className="text-right"><Metric v={p.views} /></td>
                <td className="text-right"><Metric v={p.forwards} /></td>
                <td className="text-right"><Metric v={p.reactions_total || null} /></td>
                <td className="whitespace-nowrap text-mute">{ago(p.stats_at)}</td>
              </tr>))}</tbody>
          </table></div>)}
        {(page > 0 || more) && (
          <div className="flex justify-between border-t border-line px-4 py-2.5 text-[12.5px]">
            {page > 0 ? <Link className="text-mute hover:text-fg" href={`/posts${qs({ channel: channelId, page: page - 1 || undefined })}`}>← Newer</Link> : <span />}
            {more && <Link className="text-mute hover:text-fg" href={`/posts${qs({ channel: channelId, page: page + 1 })}`}>Older →</Link>}
          </div>)}
      </Panel>
    </>
  );
}
