import { refreshAllStatsAction, saveSettingsAction } from "@/app/actions";
import { ActionForm, SubmitButton } from "@/components/client";
import { Empty, Panel, PageHeader, Stat, StatGrid } from "@/components/ui";
import { query } from "@/lib/db";
import { getSettings } from "@/lib/services/automation";
import { listChannels } from "@/lib/services/channels";
import { getSystemStatus } from "@/lib/services/status";
import { mtprotoAvailable } from "@/lib/telegram/mtproto";
import { TELEGRAM_REACTION_EMOJI } from "@/lib/telegram/bot";
import { n } from "@/lib/fmt";
import { StatusBadge } from "@/components/ui";

export const metadata = { title: "Automation" };

function Check({ name, label, on }: { name: string; label: string; on: boolean }) {
  return <label className="flex items-center gap-2 text-[13px]"><input type="checkbox" name={name} defaultChecked={on} className="h-4 w-4 accent-[#C7F36B]" />{label}</label>;
}
function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return <label className="block"><span className="label">{label}</span><div className="mt-1.5">{children}</div>{hint && <span className="mt-1 block text-[11.5px] text-dim">{hint}</span>}</label>;
}

export default async function Automation() {
  const [channels, sys, mt, jobs] = await Promise.all([
    listChannels(), getSystemStatus(), mtprotoAvailable(),
    query<{ status: string; kind: string; n: number }>("SELECT status, kind, count(*)::int AS n FROM automation_jobs WHERE created_at > now() - interval '24 hours' GROUP BY 1,2"),
  ]);
  const settings = await Promise.all(channels.map((c) => getSettings(c.id)));
  const on = (k: "monitoring_enabled" | "stats_enabled" | "reaction_enabled" | "notify_enabled") => settings.filter((s) => s?.[k]).length;
  const jc = (status: string) => jobs.rows.filter((j) => j.status === status).reduce((a, j) => a + j.n, 0);
  const q = sys.queues;

  return (
    <>
      <PageHeader title="Automation" sub="Each channel has its own configuration. Changes apply to the next post or polling cycle." actions={
        <form action={refreshAllStatsAction}><SubmitButton className="btn btn-sm" pendingText="Queued…">Run stats cycle now</SubmitButton></form>} />

      <StatGrid cols={5}>
        <Stat label="Monitoring" value={`${on("monitoring_enabled")}/${channels.length}`} hint="channels ON" />
        <Stat label="Statistics" value={`${on("stats_enabled")}/${channels.length}`} hint={mt ? "polled via MTProto" : "MTProto not configured"} />
        <Stat label="Auto reaction" value={`${on("reaction_enabled")}/${channels.length}`} />
        <Stat label="Notifications" value={`${on("notify_enabled")}/${channels.length}`} />
        <Stat label="Jobs 24h" value={`${n(jc("done"))} ok`} hint={`${n(jc("failed"))} failed · ${n(jc("skipped"))} skipped · ${n(jc("pending") + jc("running"))} open`} />
      </StatGrid>

      <Panel title="Queues & worker" className="mt-6" flush>
        <div className="grid gap-px bg-line sm:grid-cols-4">
          <div className="bg-bg2 px-4 py-3 text-[13px]"><div className="label">Worker</div><div className="mt-1">{sys.worker.ok ? "Running" : sys.worker.detail}</div></div>
          {"error" in q ? <div className="bg-bg2 px-4 py-3 text-[13px] text-danger sm:col-span-3">Redis: {q.error}</div> :
            Object.entries(q.counts).map(([k, v]) => (
              <div key={k} className="bg-bg2 px-4 py-3 text-[13px]"><div className="label">{k}</div>
                <div className="num mt-1 text-mute">{v.waiting} waiting · {v.active} active · {v.delayed} delayed · <span className={v.failed ? "text-danger" : ""}>{v.failed} failed</span></div></div>))}
        </div>
      </Panel>

      <h2 className="label mb-3 mt-8">Per-channel configuration</h2>
      {channels.length === 0 && <Panel><Empty>Connect a channel first.</Empty></Panel>}
      <div className="space-y-6">
        {channels.map((c, i) => {
          const s = settings[i]!;
          return (
            <Panel key={c.id} title={<span id={c.id} className="scroll-mt-20">{c.title}</span>} right={<StatusBadge status={c.status} />}>
              <ActionForm action={saveSettingsAction}>
                <input type="hidden" name="channelId" value={c.id} />
                <div className="grid gap-x-8 gap-y-4 md:grid-cols-2 xl:grid-cols-3">
                  <div className="space-y-2.5"><span className="label">Switches</span>
                    <Check name="monitoring_enabled" label="Automatic monitoring" on={s.monitoring_enabled} />
                    <Check name="stats_enabled" label="Automatic statistics tracking" on={s.stats_enabled} />
                    <Check name="reaction_enabled" label="Automatic reaction from the bot" on={s.reaction_enabled} />
                    <Check name="notify_enabled" label="Post notifications" on={s.notify_enabled} />
                  </div>
                  <div className="space-y-4">
                    <Field label="Default reaction emoji" hint={c.available_reactions ? `Allowed here: ${c.available_reactions.join(" ") || "none"}` : undefined}>
                      <select name="reaction_emoji" defaultValue={s.reaction_emoji} className="input">{TELEGRAM_REACTION_EMOJI.map((e) => <option key={e} value={e}>{e}</option>)}</select></Field>
                    <Field label="Notification destination (chat id)" hint="Numeric id of your chat with the bot, or a group/channel where the bot can post. Get yours from @userinfobot.">
                      <input name="notify_chat_id" defaultValue={s.notify_chat_id ?? ""} inputMode="numeric" pattern="-?[0-9]*" className="input num" placeholder="e.g. 123456789" /></Field>
                  </div>
                  <div className="space-y-4">
                    <Field label="Monitoring interval (s)" hint="Base polling interval for posts < 6 h old. Older posts are polled 4× then 16× less often.">
                      <input name="monitor_interval_s" type="number" min={60} max={86400} defaultValue={s.monitor_interval_s} className="input num" /></Field>
                    <Field label="Track posts for (days)"><input name="tracking_days" type="number" min={1} max={365} defaultValue={s.tracking_days} className="input num" /></Field>
                  </div>
                  <Field label="Max retries per job" hint="Exponential backoff between attempts."><input name="max_retries" type="number" min={0} max={20} defaultValue={s.max_retries} className="input num" /></Field>
                  <Field label="Pause channel after N consecutive failures" hint={`0 = never. Currently ${s.consecutive_failures} consecutive failure(s).`}>
                    <input name="pause_after_failures" type="number" min={0} max={100} defaultValue={s.pause_after_failures} className="input num" /></Field>
                </div>
                <div className="mt-4"><SubmitButton pendingText="Saving…">Save</SubmitButton></div>
              </ActionForm>
            </Panel>);
        })}
      </div>
    </>
  );
}
