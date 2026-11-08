import { changePasswordAction, removeBotAction, saveBotAction, saveRetentionAction, signOutEverywhereAction } from "@/app/actions";
import { ActionForm, ConfirmForm, SubmitButton } from "@/components/client";
import { Notice, PageHeader, Panel } from "@/components/ui";
import { getRetention } from "@/lib/services/maintenance";
import { getSystemStatus } from "@/lib/services/status";
import { requireUser } from "@/lib/auth/session";
import { env } from "@/lib/env";
import { ago } from "@/lib/fmt";

export const metadata = { title: "Settings" };

export default async function Settings() {
  const [user, sys, ret] = await Promise.all([requireUser(), getSystemStatus(), getRetention()]);
  const wh = sys.webhook;
  return (
    <>
      <PageHeader title="Settings" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Telegram bot (Bot API)">
          {sys.bot ? (
            <div className="text-[13px]">
              <p>Connected as <span className="num text-accent">@{sys.bot.username}</span>. The token is stored encrypted (AES-256-GCM) and never sent to the browser.</p>
              {wh && ("error" in wh ? <p className="mt-2 text-danger">Webhook check failed: {wh.error}</p> : (
                <dl className="mt-3 space-y-1 text-mute">
                  <div>Webhook: <span className="num text-fg">{wh.url ? new URL(wh.url).host + "/tg/webhook/••••" : "not set"}</span></div>
                  <div>Pending at Telegram: <span className="num text-fg">{wh.pending}</span></div>
                  {wh.lastError && <div className="text-danger">Last delivery error {ago(wh.lastErrorAt)}: {wh.lastError}</div>}
                  <div>Last webhook received: <span className="text-fg">{ago(sys.lastWebhookAt)}</span></div>
                </dl>))}
              <ConfirmForm action={removeBotAction} message="Remove the bot? Monitoring stops until you add a bot again." className="mt-4"><button className="btn btn-sm btn-danger">Remove bot</button></ConfirmForm>
              <p className="label mt-5">Replace token</p>
            </div>) : <p className="text-[13px] text-mute">Create a bot with @BotFather, paste its token here. GEASY registers the webhook automatically at <span className="num">{env().PUBLIC_BASE_URL}</span>.</p>}
          <ActionForm action={saveBotAction} className="mt-2 space-y-2" resetOnSuccess>
            <input name="token" type="password" autoComplete="off" className="input num" placeholder="123456789:AA…" required />
            <SubmitButton pendingText="Verifying…">{sys.bot ? "Replace and re-register webhook" : "Verify and save"}</SubmitButton>
          </ActionForm>
          {!env().PUBLIC_BASE_URL.startsWith("https://") && <div className="mt-3"><Notice title="PUBLIC_BASE_URL is not HTTPS">Telegram only delivers webhooks to HTTPS URLs. Fix it in your .env before saving the token.</Notice></div>}
        </Panel>

        <Panel title="Telegram account (MTProto) · views & forwards">
          <div className="text-[13px] text-mute">
            <p><span className="text-fg">Why:</span> the Bot API has no view counter, no forward counter and cannot read an existing post. These come from MTProto, read-only, using the official API with your own <span className="num">api_id</span>. Without it those values show “—”, never a guess.</p>
            <p className="mt-3">Status: {sys.mtproto ? <span className="text-accent">connected as {sys.mtproto.username ? "@" + sys.mtproto.username : sys.mtproto.name}</span> : <span className="text-warn">not configured</span>}</p>
            <p className="mt-3">The account must be a member of the channels. Login is interactive (phone code), run once on the server:</p>
            <pre className="num mt-2 overflow-x-auto rounded border border-line bg-bg p-3 text-[12px] text-fg">docker compose run --rm -it worker node dist/scripts/mtproto-login.mjs</pre>
            <p className="mt-2 text-[12px]">Get <span className="num">api_id</span>/<span className="num">api_hash</span> at my.telegram.org → API development tools. The session is stored encrypted in the database.</p>
          </div>
        </Panel>

        <Panel title="Data retention">
          <ActionForm action={saveRetentionAction} className="space-y-3 text-[13px]">
            <label className="block"><span className="label">Keep webhook events (days)</span><input name="webhook_events_days" type="number" min={1} defaultValue={ret.webhook_events_days} className="input num mt-1.5" /></label>
            <label className="block"><span className="label">Keep activity logs (days)</span><input name="activity_logs_days" type="number" min={1} defaultValue={ret.activity_logs_days} className="input num mt-1.5" /></label>
            <label className="block"><span className="label">Keep every snapshot for (days)</span><input name="stats_full_days" type="number" min={1} defaultValue={ret.stats_full_days} className="input num mt-1.5" /></label>
            <label className="flex items-center gap-2"><input type="checkbox" name="stats_downsample_to_daily" defaultChecked={ret.stats_downsample_to_daily} className="h-4 w-4 accent-[#C7F36B]" />Afterwards keep one snapshot per day per post</label>
            <SubmitButton pendingText="Saving…">Save</SubmitButton>
          </ActionForm>
        </Panel>

        <Panel title="Account">
          <p className="mb-3 text-[13px] text-mute">Signed in as <span className="text-fg">{user.email}</span></p>
          <ActionForm action={changePasswordAction} className="space-y-2" resetOnSuccess>
            <input name="current" type="password" autoComplete="current-password" className="input" placeholder="Current password" required />
            <input name="next" type="password" autoComplete="new-password" minLength={12} className="input" placeholder="New password (12+ characters)" required />
            <input name="confirm" type="password" autoComplete="new-password" minLength={12} className="input" placeholder="Confirm new password" required />
            <SubmitButton pendingText="Updating…">Change password</SubmitButton>
          </ActionForm>
          <form action={signOutEverywhereAction} className="mt-4"><button className="btn btn-sm">Sign out on all devices</button></form>
        </Panel>
      </div>
    </>
  );
}
