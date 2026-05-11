import { redirect } from "next/navigation";

import { SuperAdminPanel } from "@/components/super-admin-panel";
import { requireSession } from "@/lib/session";

export default async function AdminPage() {
  const session = await requireSession();
  if (session.auth.role !== "super_admin") {
    redirect("/dashboard");
  }

  return (
    <SuperAdminPanel
      authSource={session.auth.auth_source || null}
      currentUsername={session.auth.user_name || ""}
    />
  );
}
