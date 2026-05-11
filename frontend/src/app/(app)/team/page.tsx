import { Card } from "@/components/ui/card";
import { CompanyAdminPanel } from "@/components/company-admin-panel";
import { requireSession } from "@/lib/session";

export default async function TeamPage() {
  const session = await requireSession();

  if (session.auth.role !== "company_admin") {
    return (
      <Card>
        <span className="eyebrow">Access Denied</span>
        <h2>Team sahifasi faqat company admin uchun</h2>
        <p>Joriy sessiyada company-level user boshqaruvi uchun ruxsat yo'q.</p>
      </Card>
    );
  }

  return <CompanyAdminPanel companyName={session.auth.company_name || "Company"} />;
}
