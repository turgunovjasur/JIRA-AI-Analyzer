import { Card } from "@/components/ui/card";
import { TestCaseGenerator } from "@/components/testcase-generator";
import { requireSession } from "@/lib/session";

export default async function TestCasePage() {
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

  return <TestCaseGenerator />;
}
