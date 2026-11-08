import { addChannelAction, removeChannelAction, toggleSettingAction, verifyChannelAction } from "@/app/actions";
import { ActionForm, ConfirmForm, SubmitButton } from "@/components/client";
import { Avatar, Empty, Notice, PageHeader, Panel, StatusBadge, Toggle } from "@/components/ui";
import { BOT_SETUP_INSTRUCTIONS, listChannels } from "@/lib/services/channels";
import { getBot } from "@/lib/services/credentials";
import { ago, n } from "@/lib/fmt";
import Link from "next/link";

export const metadata = { title: "My Channels" };

export default async function ChannelsPage() {
  const [channels, bot] = await Promise.all([listChannels(), getBot()]);
  return (
    <>
      <PageHeader title="My Channels" sub="Connect a channel by pasting its link. A public link alone grants nothing: the bot must be an administrator of the channel." />
      {!bot && <div className="mb-6"><Notice title="No bot configured">Add your bot token in <Link className="underline" href="/settings">Settings</Link> before connecting channels.</Notice></div>}

      <Panel title="Connect a channel" className="mb-6">
        <ActionForm action={addChannelAction} resetOnSuccess>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input name="link" required className="input num flex-1" placeholder="https://t.me/channelname  ·  @channelname  ·  https://t.me/c/1234567890/1" autoComplete="off" spellCheck={false} />
            <SubmitButton pendingText="Verifying…">Connect</SubmitButton>
          </div>
        </ActionForm>
        <details className="mt-4 text-[13px]">
          <summary className="cursor-pointer text-mute hover:text-fg">How to authorise the bot{bot ? ` @${bot.identity.username}` : ""} (minimum permissions)</summary>
          <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-mute">{BOT_SETUP_INSTRUCTIONS.map((s) => <li key={s}>{s}</li>)}</ol>
          <p className="mt-3 text-mute">Private channels: add the bot first, then paste any post link of the form <span className="num text-fg">t.me/c/&lt;id&gt;/&lt;post&gt;</span>. Invite links (<span className="num">t.me/+…</span>) cannot be resolved by a bot.</p>
        </details>
      </Panel>

      <Panel flush title={`Channels (${channels.length})`}>
        {channels.length === 0 ? <Empty>No channel yet.</Empty> : (
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Channel</th><th>Status</th><th className="text-right">Subscribers</th><th className="text-right">Posts</th><th>Last post</th><th>Monitoring</th><th /></tr></thead>
              <tbody>
                {channels.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <Avatar id={c.id} title={c.title} hasPhoto={!!c.photo_file_id} />
                        <div className="min-w-0"><div className="truncate font-medium">{c.title}</div>
                          <div className="num truncate text-[12px] text-mute">{c.username ? `@${c.username}` : "private channel"}</div></div>
                      </div>
                    </td>
                    <td>
                      <StatusBadge status={c.status} />
                      {c.status_detail && <div className="mt-0.5 max-w-[260px] text-[11.5px] leading-snug text-mute">{c.status_detail}</div>}
                    </td>
                    <td className="num text-right" title={c.subscribers_checked_at ? `checked ${ago(c.subscribers_checked_at)} · Telegram` : ""}>{n(c.subscriber_count)}</td>
                    <td className="num text-right">{n(c.post_count)}</td>
                    <td className="text-mute">{ago(c.last_post_at)}</td>
                    <td>
                      <form action={toggleSettingAction}>
                        <input type="hidden" name="channelId" value={c.id} /><input type="hidden" name="key" value="monitoring_enabled" />
                        <input type="hidden" name="value" value={String(!c.monitoring_enabled)} />
                        <button className="flex items-center gap-2 text-[12.5px] text-mute hover:text-fg" aria-label={`Turn monitoring ${c.monitoring_enabled ? "off" : "on"} for ${c.title}`}>
                          <Toggle on={c.monitoring_enabled} label="Monitoring" />{c.monitoring_enabled ? "On" : "Off"}</button>
                      </form>
                    </td>
                    <td>
                      <div className="flex justify-end gap-2">
                        <form action={verifyChannelAction}><input type="hidden" name="id" value={c.id} /><SubmitButton className="btn btn-sm" pendingText="…">Verify access</SubmitButton></form>
                        <Link className="btn btn-sm" href={`/automation#${c.id}`}>Settings</Link>
                        <ConfirmForm action={removeChannelAction} message={`Remove “${c.title}”? All its posts and statistics history will be deleted.`}>
                          <input type="hidden" name="id" value={c.id} /><button className="btn btn-sm btn-danger">Remove</button>
                        </ConfirmForm>
                      </div>
                    </td>
                  </tr>))}
              </tbody>
            </table>
          </div>)}
      </Panel>
    </>
  );
}
