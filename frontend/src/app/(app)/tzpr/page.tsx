import { Card } from "@/components/ui/card";
import { TZPRChecker } from "@/components/tzpr-checker";
import { requireSession } from "@/lib/session";

export default async function TZPRPage() {
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

  return <TZPRChecker />;
}
