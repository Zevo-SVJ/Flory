import Link from "next/link";
import { setReactionEmojiAction, toggleSettingAction } from "@/app/actions";
import { EmojiPicker, SubmitButton } from "@/components/client";
import { Empty, Notice, PageHeader, Panel, Toggle } from "@/components/ui";
import { query } from "@/lib/db";
import { listChannels } from "@/lib/services/channels";
import { getBot } from "@/lib/services/credentials";
import { getSettings } from "@/lib/services/automation";
import { TELEGRAM_REACTION_EMOJI } from "@/lib/telegram/bot";
import { ago, n } from "@/lib/fmt";

export const metadata = { title: "Reactions" };

export default async function Reactions() {
  const [channels, bot, totals, jobs] = await Promise.all([
    listChannels(), getBot(),
    query<{ reaction: string; total: number; posts: number }>("SELECT reaction, sum(count)::int AS total, count(*)::int AS posts FROM post_reactions GROUP BY reaction ORDER BY total DESC LIMIT 12"),
    query<{ id: string; status: string; last_error: string | null; created_at: Date; finished_at: Date | null; payload: { emoji?: string; manual?: boolean; messageId?: number }; title: string; post_id: string | null }>(
      `SELECT j.id, j.status, j.last_error, j.created_at, j.finished_at, j.payload, c.title, j.post_id FROM automation_jobs j JOIN channels c ON c.id=j.channel_id WHERE j.kind='reaction' ORDER BY j.created_at DESC LIMIT 15`),
  ]);
  const settings = new Map((await Promise.all(channels.map(async (c) => [c.id, await getSettings(c.id)] as const))));
  return (
    <>
      <PageHeader title="Reactions" sub={<>One authorised identity reacts: {bot ? <span className="num text-fg">@{bot.identity.username}</span> : "no bot configured"}. No other account is used, and every action is logged under that identity. Telegram keeps one reaction per account per post.</>} />
      {!bot && <div className="mb-6"><Notice title="No bot configured">Add one in <Link className="underline" href="/settings">Settings</Link>.</Notice></div>}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          {channels.length === 0 && <Panel><Empty>Connect a channel first.</Empty></Panel>}
          {channels.map((c) => {
            const s = settings.get(c.id)!;
            const disabled = c.available_reactions ? TELEGRAM_REACTION_EMOJI.filter((e) => !c.available_reactions!.includes(e)) : [];
            return (
              <Panel key={c.id} title={c.title} right={
                <form action={toggleSettingAction}>
                  <input type="hidden" name="channelId" value={c.id} /><input type="hidden" name="key" value="reaction_enabled" /><input type="hidden" name="value" value={String(!s.reaction_enabled)} />
                  <button className="flex items-center gap-2 text-[12.5px] text-mute hover:text-fg"><Toggle on={s.reaction_enabled} label="Auto reaction" />Auto-react to new posts: {s.reaction_enabled ? "ON" : "OFF"}</button>
                </form>}>
                <p className="mb-3 text-[12.5px] text-mute">
                  {c.available_reactions === null ? "All standard reactions are enabled in this channel." : c.available_reactions.length === 0 ? "Reactions are disabled in this channel." : `Enabled in this channel: ${c.available_reactions.join(" ")}`}
                  {" "}Default: <span className="text-[16px]">{s.reaction_emoji}</span>
                </p>
                <form action={setReactionEmojiAction}>
                  <input type="hidden" name="channelId" value={c.id} />
                  <EmojiPicker emojis={TELEGRAM_REACTION_EMOJI} defaultValue={s.reaction_emoji} disabled={disabled} />
                  <div className="mt-3"><SubmitButton className="btn btn-sm" pendingText="Saving…">Set default reaction</SubmitButton></div>
                </form>
              </Panel>);
          })}
        </div>

        <div className="space-y-6">
          <Panel title="Existing reactions · all posts" flush>
            {totals.rows.length === 0 ? <Empty>No reaction recorded yet.</Empty> : (
              <table className="tbl"><thead><tr><th>Reaction</th><th className="text-right">Count</th><th className="text-right">Posts</th></tr></thead>
                <tbody>{totals.rows.map((r) => <tr key={r.reaction}><td className="text-[16px]">{r.reaction.startsWith("custom:") ? <span className="tag">custom</span> : r.reaction === "paid" ? <span className="tag">paid ★</span> : r.reaction}</td><td className="num text-right">{n(r.total)}</td><td className="num text-right text-mute">{n(r.posts)}</td></tr>)}</tbody></table>)}
          </Panel>
          <Panel title="Reaction jobs" flush>
            {jobs.rows.length === 0 ? <Empty>No job yet.</Empty> : (
              <ul className="divide-y divide-line2">{jobs.rows.map((j) => (
                <li key={j.id} className="px-4 py-2.5 text-[12.5px]">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{j.payload.emoji ?? ""} {j.post_id ? <Link className="hover:text-accent" href={`/posts/${j.post_id}`}>#{j.payload.messageId}</Link> : `#${j.payload.messageId}`} · <span className="text-mute">{j.title}</span>{j.payload.manual && <span className="tag ml-2">manual</span>}</span>
                    <span className={`tag ${j.status === "done" ? "text-accent" : j.status === "failed" ? "text-danger" : ""}`}>{j.status}</span>
                  </div>
                  {j.last_error && <div className="mt-0.5 truncate text-[11.5px] text-mute" title={j.last_error}>{j.last_error}</div>}
                  <div className="num mt-0.5 text-[11px] text-dim">{ago(j.finished_at ?? j.created_at)}</div>
                </li>))}</ul>)}
          </Panel>
        </div>
      </div>
    </>
  );
}
