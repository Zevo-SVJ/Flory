import { redirect } from "next/navigation";
import { getUser } from "@/lib/auth/session";
import { loginAction } from "@/app/actions";
import { ActionForm, SubmitButton } from "@/components/client";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sign in" };

export default async function LoginPage() {
  if (await getUser()) redirect("/");
  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-[360px]">
        <div className="mb-8">
          <div className="flex items-center gap-2"><span className="inline-block h-2 w-2 rounded-full bg-accent" /><span className="text-[18px] font-semibold tracking-[.14em]">GEASY</span></div>
          <div className="label mt-1 pl-4">View Engine · Private</div>
        </div>
        <ActionForm action={loginAction} className="space-y-3">
          <label className="block"><span className="label">Email</span>
            <input name="email" type="email" required autoComplete="username" className="input mt-1.5" autoFocus /></label>
          <label className="block"><span className="label">Password</span>
            <input name="password" type="password" required autoComplete="current-password" className="input mt-1.5" /></label>
          <SubmitButton className="btn btn-primary w-full" pendingText="Signing in…">Sign in</SubmitButton>
        </ActionForm>
        <p className="mt-6 text-[12px] text-dim">Restricted system. Access is logged.</p>
      </div>
    </main>
  );
}
