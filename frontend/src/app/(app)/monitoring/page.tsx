import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { BaseCard, Card } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import { StatusPill } from "@/components/ui/status-pill";
import { getMonitoringSnapshot } from "@/lib/backend";
import { requireSession } from "@/lib/session";
import type {
  MonitoringBlockedTaskRow,
  MonitoringErrorRow,
  MonitoringOverallStatsRow,
  MonitoringRecentTaskRow,
  MonitoringServiceStatusRow,
} from "@/lib/types";

const FILTERS = [
  "Barchasi",
  "completed",
  "progressing",
  "returned",
  "error",
  "blocked",
  "none",
] as const;

function statusTone(value: string | null | undefined) {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed" || normalized === "done") return "good" as const;
  if (normalized === "error") return "bad" as const;
  if (normalized === "returned") return "warn" as const;
  if (normalized === "blocked") return "info" as const;
  if (normalized === "progressing" || normalized === "pending" || normalized === "running") {
    return "warn" as const;
  }
  return "muted" as const;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("uz", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function groupServiceCounts(
  rows: MonitoringServiceStatusRow[],
  key: "service1_status" | "service2_status",
) {
  const grouped = new Map<string, number>();
  for (const row of rows) {
    const status = (row[key] || "unknown").toString();
    grouped.set(status, (grouped.get(status) || 0) + Number(row.count || 0));
  }
  return Array.from(grouped.entries());
}

function ProgressStat({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="qa-stat-row">
      <div className="qa-stat-row-header">
        <span className="qa-stat-row-label">{label}</span>
        <span className="qa-stat-row-value">{value} / {total}</span>
      </div>
      <div className="qa-progress-bar">
        <div
          className="qa-progress-fill"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function RecentTasksTable({ rows }: { rows: MonitoringRecentTaskRow[] }) {
  if (!rows.length) return <p className="text-sm text-muted-foreground">Tasklar topilmadi.</p>;
  return (
    <BaseCard as="div" className="overflow-x-auto" padding="none">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <th className="px-4 py-3 text-left">Task</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-left">S1</th>
            <th className="px-4 py-3 text-left">S2</th>
            <th className="px-4 py-3 text-left">Moslik</th>
            <th className="px-4 py-3 text-left">Qaytish</th>
            <th className="px-4 py-3 text-left">Vaqt</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={`${row.task_id}-${row.updated_at}`}
              className="border-b border-border last:border-0 hover:bg-muted/20"
            >
              <td className="px-4 py-3 font-mono text-sm font-medium">{row.task_id || "—"}</td>
              <td className="px-4 py-3"><StatusPill tone={statusTone(row.task_status)} value={row.task_status || "—"} /></td>
              <td className="px-4 py-3"><StatusPill tone={statusTone(row.service1_status)} value={row.service1_status || "—"} /></td>
              <td className="px-4 py-3"><StatusPill tone={statusTone(row.service2_status)} value={row.service2_status || "—"} /></td>
              <td className="px-4 py-3">
                {row.compliance_score != null ? (
                  <Badge tone={row.compliance_score >= 80 ? "success" : row.compliance_score >= 60 ? "warning" : "danger"}>
                    {row.compliance_score}%
                  </Badge>
                ) : "—"}
              </td>
              <td className="px-4 py-3 text-center">{row.return_count ?? 0}</td>
              <td className="px-4 py-3 text-muted-foreground">{formatDate(row.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </BaseCard>
  );
}

function ErrorList({ rows }: { rows: MonitoringErrorRow[] }) {
  if (!rows.length) return <p className="text-sm text-muted-foreground">Xatoliklar yo&apos;q.</p>;
  return (
    <div className="grid gap-3">
      {rows.slice(0, 6).map((row) => (
        <BaseCard
          as="div"
          key={`${row.task_id}-${row.updated_at}`}
          className="p-4"
          padding="none"
          tone="soft"
        >
          <div className="flex items-start justify-between gap-2">
            <strong className="font-mono text-sm">{row.task_id || "Unknown"}</strong>
            <span className="shrink-0 text-xs text-muted-foreground">{formatDate(row.updated_at)}</span>
          </div>
          <div className="mt-2"><StatusPill tone={statusTone(row.task_status)} value={row.task_status || "—"} /></div>
          {row.error_message ? <p className="mt-2 text-sm text-muted-foreground">{row.error_message}</p> : null}
          {row.service1_error ? <p className="mt-1 text-xs text-muted-foreground">S1: {row.service1_error}</p> : null}
          {row.service2_error ? <p className="mt-1 text-xs text-muted-foreground">S2: {row.service2_error}</p> : null}
        </BaseCard>
      ))}
    </div>
  );
}

function BlockedList({ rows }: { rows: MonitoringBlockedTaskRow[] }) {
  if (!rows.length) return <p className="text-sm text-muted-foreground">Retry kutayotgan task yo&apos;q.</p>;
  return (
    <div className="grid gap-3">
      {rows.slice(0, 6).map((row) => (
        <BaseCard
          as="div"
          key={`${row.task_id}-${row.blocked_retry_at}`}
          className="p-4"
          padding="none"
          tone="soft"
        >
          <div className="flex items-start justify-between gap-2">
            <strong className="font-mono text-sm">{row.task_id || "Unknown"}</strong>
            <span className="shrink-0 text-xs text-muted-foreground">{formatDate(row.blocked_retry_at)}</span>
          </div>
          <div className="mt-2 flex gap-2">
            <StatusPill tone={statusTone(row.service1_status)} value={row.service1_status || "—"} />
            <StatusPill tone={statusTone(row.service2_status)} value={row.service2_status || "—"} />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">{row.block_reason || "Sabab noma&apos;lum."}</p>
        </BaseCard>
      ))}
    </div>
  );
}

function OverallStats({ stats }: { stats: MonitoringOverallStatsRow }) {
  const total = stats.total_tasks || 1;
  return (
    <div className="grid gap-4">
      <ProgressStat label="Bajarildi" value={stats.completed || 0} total={total} color="var(--success)" />
      <ProgressStat label="Jarayonda" value={stats.progressing || 0} total={total} color="var(--accent)" />
      <ProgressStat label="Qaytarildi" value={stats.returned || 0} total={total} color="#f59e0b" />
      <ProgressStat label="Xato" value={stats.error || 0} total={total} color="var(--error)" />
      <ProgressStat label="Bloklangan" value={stats.blocked || 0} total={total} color="#7c3aed" />
    </div>
  );
}

export default async function MonitoringPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const session = await requireSession();
  const role = session.auth.role;
  const resolvedSearchParams = searchParams ? await searchParams : {};
  const selectedStatusRaw = resolvedSearchParams?.status;
  const selectedStatusValue = Array.isArray(selectedStatusRaw)
    ? selectedStatusRaw[0]
    : selectedStatusRaw;
  const selectedStatus = FILTERS.includes(
    (selectedStatusValue as (typeof FILTERS)[number]) || "Barchasi",
  )
    ? ((selectedStatusValue as (typeof FILTERS)[number]) || "Barchasi")
    : "Barchasi";

  if (role !== "super_admin" && role !== "company_admin") {
    return (
      <Card>
        <p className="font-semibold">Access Denied</p>
        <p className="mt-2 text-sm text-muted-foreground">Monitoring faqat admin rollar uchun.</p>
      </Card>
    );
  }

  if (role === "company_admin" && !session.companyModules?.monitoring) {
    return (
      <Card>
        <p className="font-semibold">Monitoring moduli yopiq</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Monitoring faqat webhook moduli yoqilgan kompaniyalarda ochiladi.
        </p>
      </Card>
    );
  }

  const companyId = role === "company_admin" ? session.auth.company_id : null;

  try {
    const snapshot = await getMonitoringSnapshot({ companyId, status: selectedStatus });
    const stats = snapshot.overall_stats?.[0] || {};
    const service1 = groupServiceCounts(snapshot.service_status_counts || [], "service1_status");
    const service2 = groupServiceCounts(snapshot.service_status_counts || [], "service2_status");

    return (
      <>
        <div className="qa-page-intro">
          <span className="qa-eyebrow">Operations</span>
          <h2 className="qa-page-heading">Monitoring</h2>
          <p className="qa-page-desc">Queue holati, xizmat ishlashi va so&apos;nggi tasklar real-time.</p>
        </div>

        <section className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <MetricCard helper="Jami tasklar" label="Total" value={stats.total_tasks ?? 0} />
          <MetricCard helper="Muvaffaqiyatli" label="Bajarildi" value={stats.completed ?? 0} />
          <MetricCard helper="Jarayonda" label="Progressing" value={stats.progressing ?? 0} />
          <MetricCard helper="Qaytarildi" label="Returned" value={stats.returned ?? 0} />
          <MetricCard helper="Xato" label="Error" value={stats.error ?? 0} />
          <MetricCard
            helper="O&apos;rtacha moslik"
            label="Avg Moslik"
            value={
              stats.avg_compliance != null
                ? `${Number(stats.avg_compliance).toFixed(1)}%`
                : "N/A"
            }
          />
        </section>

        <Card>
          <SectionHeader eyebrow="Filter" title="Status bo&apos;yicha" />
          <div className="mt-4 flex flex-wrap gap-2">
            {FILTERS.map((filter) => {
              const active = filter === selectedStatus;
              const href = filter === "Barchasi" ? "/monitoring" : `/monitoring?status=${filter}`;
              return (
                <Link
                  key={filter}
                  href={href}
                  className={
                    active
                      ? "inline-flex rounded-full border border-primary/15 bg-primary/10 px-3 py-1.5 text-sm font-semibold text-primary"
                      : "inline-flex rounded-full border border-border bg-white px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                  }
                >
                  {filter}
                </Link>
              );
            })}
          </div>
        </Card>

        <section className="grid gap-4 lg:grid-cols-3">
          <Card>
            <SectionHeader eyebrow="Overview" title="Task holati" />
            <div className="mt-5">
              <OverallStats stats={stats} />
            </div>
          </Card>
          <Card>
            <SectionHeader eyebrow="Service 1" title="TZ-PR tahlil" />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {service1.map(([status, count]) => (
                <BaseCard as="div" className="p-3" key={`s1-${status}`} padding="none" tone="soft">
                  <StatusPill tone={statusTone(status)} value={status} />
                  <strong className="mt-2 block text-xl font-bold">{count}</strong>
                </BaseCard>
              ))}
            </div>
          </Card>
          <Card>
            <SectionHeader eyebrow="Service 2" title="Test case" />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {service2.map(([status, count]) => (
                <BaseCard as="div" className="p-3" key={`s2-${status}`} padding="none" tone="soft">
                  <StatusPill tone={statusTone(status)} value={status} />
                  <strong className="mt-2 block text-xl font-bold">{count}</strong>
                </BaseCard>
              ))}
            </div>
          </Card>
        </section>

        <Card>
          <SectionHeader
            eyebrow="Recent Tasks"
            title="So&apos;nggi tasklar"
            action={
              <Badge tone="soft">
                {snapshot.source_label || "DB"}
                {snapshot.db_size_kb ? ` · ${snapshot.db_size_kb.toFixed(1)} KB` : ""}
              </Badge>
            }
          />
          <div className="mt-4">
            <RecentTasksTable rows={snapshot.recent_tasks || []} />
          </div>
        </Card>

        <Card>
          <SectionHeader eyebrow="Errors" title="So&apos;nggi xatoliklar" />
          <div className="mt-4"><ErrorList rows={snapshot.errors_log || []} /></div>
        </Card>

        <Card>
          <SectionHeader eyebrow="Blocked Queue" title="Retry kutayotgan tasklar" />
          <div className="mt-4"><BlockedList rows={snapshot.blocked_tasks || []} /></div>
        </Card>
      </>
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Monitoring ochilmadi.";
    return <Notice tone="error"><strong>Monitoring xatosi:</strong> {message}</Notice>;
  }
}
