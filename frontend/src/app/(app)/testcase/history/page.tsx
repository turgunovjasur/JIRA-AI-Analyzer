import { RecentRunsHistory } from "@/components/recent-runs-history";
import { Card } from "@/components/ui/card";
import { requireSession } from "@/lib/session";

export default async function TestcaseHistoryPage() {
  const session = await requireSession();
  const role = session.auth.role;
  const hasModuleAccess =
    role === "super_admin" || Boolean(session.companyModules?.testcase_generator);

  if (!hasModuleAccess) {
    return (
      <Card>
        <p className="font-semibold">Access Denied</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Joriy foydalanuvchi yoki kompaniya uchun Test Case Generator moduli yoqilmagan.
        </p>
      </Card>
    );
  }

  return (
    <RecentRunsHistory
      basePath="/testcase"
      moduleKey="testcase_generator"
      storageKey="qa.open-run.testcase_generator"
      title="Test Case Generator History"
    />
  );
}
