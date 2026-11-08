"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, startTransition, useActionState, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useFormStatus } from "react-dom";
import type { ActionState } from "@/app/actions";

const PendingCtx = createContext(false);

/**
 * Submit handler that keeps what the user typed. React 19 resets a form after a function `action`,
 * which would wipe the input after an error; submitting through a transition avoids that.
 * `resetOnSuccess` clears the form only when the action reports ok.
 */
function useKeepForm(action: (s: ActionState, fd: FormData) => Promise<ActionState>, resetOnSuccess: boolean) {
  const [state, formAction, pending] = useActionState(action, null);
  const ref = useRef<HTMLFormElement>(null);
  useEffect(() => { if (resetOnSuccess && state?.ok) ref.current?.reset(); }, [state, resetOnSuccess]);
  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget, (e.nativeEvent as SubmitEvent).submitter);
    startTransition(() => formAction(fd));
  };
  return { state, pending, ref, onSubmit };
}

export function SubmitButton({ children, className = "btn btn-primary", pendingText }: { children: ReactNode; className?: string; pendingText?: string }) {
  const fs = useFormStatus();
  const ctxPending = useContext(PendingCtx);
  const pending = fs.pending || ctxPending;
  return (
    <button type="submit" className={className} disabled={pending} aria-busy={pending}>
      {pending ? (pendingText ?? "Working…") : children}
    </button>
  );
}

export function ConfirmForm({ action, message, children, className }: { action: (fd: FormData) => void | Promise<void>; message: string; children: ReactNode; className?: string }) {
  return (
    <form action={action} className={className} onSubmit={(e) => { if (!confirm(message)) e.preventDefault(); }}>
      {children}
    </form>
  );
}

export function Feedback({ state }: { state: ActionState }) {
  if (!state) return null;
  if (state.error) return <p role="alert" className="mt-2 text-[13px] text-danger">{state.error}</p>;
  if (state.message) return <p role="status" className="mt-2 text-[13px] text-accent">{state.message}</p>;
  return null;
}

/** Generic form bound to a server action returning ActionState. */
export function ActionForm({ action, children, className, resetOnSuccess = false }: { action: (s: ActionState, fd: FormData) => Promise<ActionState>; children: ReactNode; className?: string; resetOnSuccess?: boolean }) {
  const { state, pending, ref, onSubmit } = useKeepForm(action, resetOnSuccess);
  return (
    <PendingCtx.Provider value={pending}>
      <form ref={ref} onSubmit={onSubmit} className={className}>
        {children}
        <Feedback state={state} />
      </form>
    </PendingCtx.Provider>
  );
}

export function PostLookupForm({
  lookup, connect,
}: {
  lookup: (s: ActionState, fd: FormData) => Promise<ActionState>;
  connect: (s: ActionState, fd: FormData) => Promise<ActionState>;
}) {
  const a = useKeepForm(lookup, false);
  const c = useKeepForm(connect, false);
  return (
    <div>
      <PendingCtx.Provider value={a.pending}>
        <form ref={a.ref} onSubmit={a.onSubmit} className="flex flex-col gap-2 sm:flex-row">
          <input name="url" required className="input num flex-1" placeholder="https://t.me/channelname/123  ·  https://t.me/c/1234567890/123" autoComplete="off" spellCheck={false} />
          <SubmitButton pendingText="Looking up…">Load post</SubmitButton>
        </form>
      </PendingCtx.Provider>
      <Feedback state={a.state} />
      {a.state?.connectUrl && (
        <PendingCtx.Provider value={c.pending}>
          <form ref={c.ref} onSubmit={c.onSubmit} className="mt-2">
            <input type="hidden" name="url" value={a.state.connectUrl} />
            <SubmitButton className="btn" pendingText="Connecting…">Connect this channel and load the post</SubmitButton>
            <Feedback state={c.state} />
          </form>
        </PendingCtx.Provider>
      )}
    </div>
  );
}

export function EmojiPicker({ emojis, name = "emoji", defaultValue, disabled = [] }: { emojis: readonly string[]; name?: string; defaultValue?: string; disabled?: string[] }) {
  const [sel, setSel] = useState(defaultValue ?? "");
  return (
    <div>
      <input type="hidden" name={name} value={sel} />
      <div className="grid grid-cols-[repeat(auto-fill,minmax(38px,1fr))] gap-1" role="radiogroup" aria-label="Reaction">
        {emojis.map((e) => {
          const off = disabled.includes(e);
          return (
            <button
              key={e} type="button" role="radio" aria-checked={sel === e} disabled={off} onClick={() => setSel(e)} title={off ? "Not enabled in this channel" : e}
              className={`h-9 rounded border text-[18px] leading-none transition ${sel === e ? "border-accent bg-accent/10" : "border-line hover:border-[#3a4052]"} ${off ? "cursor-not-allowed opacity-25" : ""}`}
            >{e}</button>
          );
        })}
      </div>
    </div>
  );
}

/** Soft auto-refresh of server data (no full reload). */
export function AutoRefresh({ seconds = 15 }: { seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => { if (document.visibilityState === "visible") router.refresh(); }, seconds * 1000);
    return () => clearInterval(id);
  }, [router, seconds]);
  return null;
}

const NAV = [
  { href: "/", label: "Overview", k: "01" },
  { href: "/channels", label: "My Channels", k: "02" },
  { href: "/posts", label: "Post Manager", k: "03" },
  { href: "/analytics", label: "Analytics", k: "04" },
  { href: "/reactions", label: "Reactions", k: "05" },
  { href: "/automation", label: "Automation", k: "06" },
  { href: "/logs", label: "Activity Logs", k: "07" },
  { href: "/settings", label: "Settings", k: "08" },
];

export function Shell({ email, logout, children }: { email: string; logout: () => Promise<void>; children: ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  const active = (h: string) => (h === "/" ? path === "/" : path === h || path.startsWith(h + "/"));
  const current = NAV.find((n) => active(n.href));

  const nav = (
    <nav aria-label="Main" className="flex flex-col gap-px px-2">
      {NAV.map((n) => (
        <Link key={n.href} href={n.href} aria-current={active(n.href) ? "page" : undefined}
          className={`group relative flex items-center gap-3 rounded px-3 py-2 text-[13.5px] transition-colors ${active(n.href) ? "bg-surface text-fg" : "text-mute hover:bg-surface/60 hover:text-fg"}`}>
          {active(n.href) && <span className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded bg-accent" />}
          <span className="num text-[10px] text-dim">{n.k}</span>
          {n.label}
        </Link>
      ))}
    </nav>
  );

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[224px_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-bg2 lg:flex">
        <Brand />
        <div className="flex-1 overflow-y-auto py-2">{nav}</div>
        <Account email={email} logout={logout} />
      </aside>

      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-bg2/95 px-4 py-2.5 backdrop-blur lg:hidden">
        <div className="flex items-center gap-3">
          <button className="btn btn-sm" aria-expanded={open} aria-label="Menu" onClick={() => setOpen((v) => !v)}>{open ? "Close" : "Menu"}</button>
          <span className="text-[13px] font-medium">{current?.label ?? "GEASY"}</span>
        </div>
        <span className="label">GEASY</span>
      </header>
      {open && (
        <div className="fixed inset-x-0 top-[49px] bottom-0 z-20 flex flex-col overflow-y-auto bg-bg2 pb-4 lg:hidden">
          <div className="py-2">{nav}</div>
          <div className="mt-auto"><Account email={email} logout={logout} /></div>
        </div>
      )}

      <main className="min-w-0 px-4 py-6 sm:px-8 sm:py-8">
        <div className="page-in mx-auto max-w-[1180px]">{children}</div>
      </main>
    </div>
  );
}

function Brand() {
  return (
    <div className="px-5 pb-4 pt-5">
      <div className="flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full bg-accent" />
        <span className="text-[15px] font-semibold tracking-[.14em]">GEASY</span>
      </div>
      <div className="label mt-1 pl-4">View Engine</div>
    </div>
  );
}

function Account({ email, logout }: { email: string; logout: () => Promise<void> }) {
  return (
    <div className="border-t border-line p-3">
      <div className="truncate px-1 text-[12px] text-mute" title={email}>{email}</div>
      <form action={logout} className="mt-2"><button className="btn btn-sm w-full">Sign out</button></form>
    </div>
  );
}
