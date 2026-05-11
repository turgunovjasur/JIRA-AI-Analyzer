import { SettingsPanel } from "@/components/settings-panel";
import { requireSession } from "@/lib/session";

export default async function SettingsPage() {
  const session = await requireSession();

  return (
    <SettingsPanel
      companyName={session.auth.company_name || "Platform"}
      hasWebhookModule={Boolean(session.companyModules?.webhook)}
      role={session.auth.role}
    />
  );
}
