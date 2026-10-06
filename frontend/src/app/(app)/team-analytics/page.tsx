import { redirect } from "next/navigation";
import { TeamAnalyticsDashboard } from "@/components/team-analytics-dashboard";
import { requireSession } from "@/lib/session";

export default async function TeamAnalyticsPage() {
  const session = await requireSession();
  if (session.auth.role !== "company_admin" || !session.companyModules?.team_analytics) redirect("/dashboard");
  return <TeamAnalyticsDashboard />;
}
