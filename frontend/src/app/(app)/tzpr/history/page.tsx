import { Card } from "@/components/ui/card";
import { RecentRunsHistory } from "@/components/recent-runs-history";
import { requireSession } from "@/lib/session";

export default async function TZPRHistoryPage() {
  const session = await requireSession();
  const role = session.auth.role;
  const hasModuleAccess = role === "super_admin" || Boolean(session.companyModules?.tz_pr_checker);

  if (!hasModuleAccess) {
    return (
      <Card>
        <p className="font-semibold">Access Denied</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Joriy foydalanuvchi yoki kompaniya uchun TZ-PR Checker moduli yoqilmagan.
        </p>
      </Card>
    );
  }

  return (
    <RecentRunsHistory
      basePath="/tzpr"
      moduleKey="tz_pr_checker"
      recentScope={{
        companyId: session.auth.company_id ?? null,
        role: session.auth.role ?? null,
        userId: session.auth.user_id ?? null,
      }}
      title="TZ-PR Checker History"
    />
  );
}
