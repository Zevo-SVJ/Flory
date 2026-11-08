import { requireUser } from "@/lib/auth/session";
import { logoutAction } from "@/app/actions";
import { Shell } from "@/components/client";

export const dynamic = "force-dynamic";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  return <Shell email={user.email} logout={logoutAction}>{children}</Shell>;
}
