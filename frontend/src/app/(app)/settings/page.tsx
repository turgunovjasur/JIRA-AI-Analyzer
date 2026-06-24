import { SettingsPanel } from "@/components/settings-panel";
import { requireSession } from "@/lib/session";

export default async function SettingsPage() {
  const session = await requireSession();

  const modules = session.companyModules || {};

  return (
    <SettingsPanel
      companyName={session.auth.company_name || "Platform"}
      hasCheckerModule={Boolean(modules.tz_pr_checker)}
      hasService1={Boolean(modules.webhook_service1)}
      hasService2={Boolean(modules.webhook_service2)}
      hasTestcaseModule={Boolean(modules.testcase_generator)}
      hasWebhookModule={Boolean(modules.webhook)}
      role={session.auth.role}
    />
  );
}
