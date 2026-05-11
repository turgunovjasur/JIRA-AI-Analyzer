import { Activity, Blocks, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { SectionHeader } from "@/components/ui/section-header";
import { getBackendHealth } from "@/lib/backend";
import { requireSession } from "@/lib/session";

const MODULE_META: Record<string, { title: string; note: string; icon: React.ReactNode }> = {
  tz_pr_checker: {
    title: "TZ-PR Checker",
    note: "Spec va PR mosligini tekshirish",
    icon: <ShieldCheck size={20} />,
  },
  testcase_generator: {
    title: "Test Case Generator",
    note: "QA draft test case yaratish",
    icon: <Blocks size={20} />,
  },
  monitoring: {
    title: "Monitoring",
    note: "Queue va runtime holati",
    icon: <Activity size={20} />,
  },
};

const MODULE_ROUTES: Record<string, string> = {
  tz_pr_checker: "/tzpr",
  testcase_generator: "/testcase",
  monitoring: "/monitoring",
};

export default async function DashboardPage() {
  const session = await requireSession();
  if (session.auth.role === "super_admin") {
    redirect("/admin");
  }

  const health = await getBackendHealth().catch(() => null);

  const enabledModules = Object.entries(session.companyModules || {})
    .filter(([, enabled]) => enabled)
    .map(([key]) => key);

  const moduleLinks = enabledModules
    .filter((key) => MODULE_META[key] && MODULE_ROUTES[key])
    .map((key) => ({ key, href: MODULE_ROUTES[key], ...MODULE_META[key] }));

  return (
    <>
      {/* Greeting */}
      <div className="qa-page-intro">
        <span className="qa-eyebrow">Workspace</span>
        <h2 className="qa-page-heading">
          Salom, {session.auth.user_name || "foydalanuvchi"} 👋
        </h2>
        <p className="qa-page-desc">
          Bugungi ish oqimingizni boshlang — modullarni tanlang yoki so'nggi tasklar bilan davom eting.
        </p>
      </div>

      {/* Key metrics */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Company"
          value={session.auth.company_name || "Platform"}
          helper={session.auth.role}
        />
        <MetricCard
          label="Faol modullar"
          value={enabledModules.length}
          helper="Yoqilgan modullar soni"
        />
        <MetricCard
          label="Backend"
          value={health?.status || "unknown"}
          helper={health?.service || "Status tekshirilmoqda"}
        />
        <MetricCard
          label="Rol"
          value={session.auth.role || "unknown"}
          helper={session.auth.company_code || "global"}
        />
      </section>

      {/* Module quick links */}
      {moduleLinks.length > 0 ? (
        <Card>
          <SectionHeader
            eyebrow="Quick Access"
            title="Modullar"
            action={<Badge tone="soft">{moduleLinks.length} faol</Badge>}
          />
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {moduleLinks.map((item) => (
              <Link
                className="qa-module-card group"
                href={item.href}
                key={item.href}
              >
                <div className="qa-module-card-icon">
                  {item.icon}
                </div>
                <div>
                  <strong className="block text-sm font-bold text-foreground">
                    {item.title}
                  </strong>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.note}</p>
                </div>
              </Link>
            ))}
          </div>
        </Card>
      ) : (
        <Card tone="soft">
          <p className="text-sm text-muted-foreground">
            Hech qanday modul yoqilmagan. Admin bilan bog&apos;laning.
          </p>
        </Card>
      )}
    </>
  );
}
