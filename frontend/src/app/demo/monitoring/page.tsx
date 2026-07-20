import { Badge } from "@/components/ui/badge";
import { BaseCard, Card } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { SectionHeader } from "@/components/ui/section-header";
import { StatusPill } from "@/components/ui/status-pill";
import { DEMO_MONITORING } from "@/lib/demo-data";

type Tone = "good" | "bad" | "warn" | "info" | "muted";

function statusTone(status: string): Tone {
  switch (status) {
    case "completed":
    case "done":
      return "good";
    case "error":
      return "bad";
    case "returned":
      return "warn";
    case "blocked":
      return "info";
    case "progressing":
    case "pending":
      return "warn";
    default:
      return "muted";
  }
}

function scoreTone(score: number | null): "success" | "warning" | "danger" | "default" {
  if (score === null) return "default";
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

export default function DemoMonitoringPage() {
  const m = DEMO_MONITORING;

  return (
    <div className="grid gap-5">
      <div className="qa-page-intro">
        <span className="qa-eyebrow">Operations</span>
        <h2 className="qa-page-heading">Monitoring</h2>
        <p className="qa-page-desc">Queue, servis holati va task statistikasi — namuna ma&apos;lumot.</p>
      </div>

      {/* health */}
      <Card>
        <SectionHeader
          eyebrow="System"
          title="Backend holati"
          action={
            <span className="inline-flex items-center gap-2 rounded-full bg-[color:var(--success-soft)] px-3 py-1 text-xs font-semibold text-[color:var(--success)]">
              <span className="h-2 w-2 rounded-full bg-[color:var(--success)]" /> Healthy
            </span>
          }
        />
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {m.health.services.map((s) => (
            <div key={s.name} className="flex items-center justify-between rounded-[12px] border border-border bg-card px-4 py-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{s.name}</span>
              <span className="inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--success)]">
                <span className="h-2 w-2 rounded-full bg-[color:var(--success)]" /> ok
              </span>
            </div>
          ))}
          <div className="flex items-center justify-between rounded-[12px] border border-border bg-card px-4 py-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">execution_mode</span>
            <span className="font-mono text-sm font-semibold text-foreground">{m.health.executionMode}</span>
          </div>
        </div>
        <p className="mt-4 text-xs text-muted-foreground">Oxirgi yangilanish: {m.health.timestamp}</p>
      </Card>

      {/* metrics */}
      <section className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="Total" value={m.metrics.total} />
        <MetricCard label="Bajarildi" value={m.metrics.completed} />
        <MetricCard label="Progressing" value={m.metrics.progressing} />
        <MetricCard label="Returned" value={m.metrics.returned} />
        <MetricCard label="Error" value={m.metrics.error} />
        <MetricCard label="Avg Moslik" value={`${m.metrics.avgCompliance.toFixed(1)}%`} />
      </section>

      {/* service counts */}
      <section className="grid gap-4 lg:grid-cols-3">
        <Card>
          <SectionHeader eyebrow="Task" title="Task holati" />
          <div className="mt-4 grid gap-3">
            <ProgressStat label="Bajarildi" value={m.metrics.completed} total={m.metrics.total} color="var(--success)" />
            <ProgressStat label="Jarayonda" value={m.metrics.progressing} total={m.metrics.total} color="var(--accent)" />
            <ProgressStat label="Qaytarildi" value={m.metrics.returned} total={m.metrics.total} color="#f59e0b" />
            <ProgressStat label="Xato" value={m.metrics.error} total={m.metrics.total} color="var(--error)" />
            <ProgressStat label="Bloklangan" value={m.metrics.blocked} total={m.metrics.total} color="#7c3aed" />
          </div>
        </Card>

        <Card>
          <SectionHeader eyebrow="Servis-1" title="TZ-PR tahlil" />
          <div className="mt-4 grid grid-cols-2 gap-3">
            <CountTile label="Done" value={m.service1.done} tone="good" />
            <CountTile label="Pending" value={m.service1.pending} tone="warn" />
            <CountTile label="Error" value={m.service1.error} tone="bad" />
            <CountTile label="Blocked" value={m.service1.blocked} tone="info" />
          </div>
        </Card>

        <Card>
          <SectionHeader eyebrow="Servis-2" title="Test case" />
          <div className="mt-4 grid grid-cols-2 gap-3">
            <CountTile label="Done" value={m.service2.done} tone="good" />
            <CountTile label="Pending" value={m.service2.pending} tone="warn" />
            <CountTile label="Error" value={m.service2.error} tone="bad" />
            <CountTile label="Blocked" value={m.service2.blocked} tone="info" />
          </div>
        </Card>
      </section>

      {/* recent tasks */}
      <Card>
        <SectionHeader eyebrow="Runtime" title="So'nggi tasklar" action={<Badge>demo · 12 KB</Badge>} />
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left text-xs uppercase tracking-[0.08em] text-muted-foreground">
                <th className="px-3 py-2 font-semibold">Task</th>
                <th className="px-3 py-2 font-semibold">Status</th>
                <th className="px-3 py-2 font-semibold">S1</th>
                <th className="px-3 py-2 font-semibold">S2</th>
                <th className="px-3 py-2 font-semibold">Moslik</th>
                <th className="px-3 py-2 text-center font-semibold">Qaytish</th>
                <th className="px-3 py-2 font-semibold">Vaqt</th>
              </tr>
            </thead>
            <tbody>
              {m.recentTasks.map((t) => (
                <tr key={t.id} className="border-b border-border/60">
                  <td className="px-3 py-2.5 font-mono text-xs text-foreground">{t.id}</td>
                  <td className="px-3 py-2.5"><StatusPill tone={statusTone(t.status)} value={t.status} /></td>
                  <td className="px-3 py-2.5"><StatusPill tone={statusTone(t.s1)} value={t.s1} /></td>
                  <td className="px-3 py-2.5"><StatusPill tone={statusTone(t.s2)} value={t.s2} /></td>
                  <td className="px-3 py-2.5">
                    {t.score === null ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      <Badge tone={scoreTone(t.score)}>{t.score}%</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-center text-foreground">{t.returns}</td>
                  <td className="px-3 py-2.5 text-muted-foreground">{t.updated}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* errors + blocked */}
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionHeader eyebrow="Signals" title="Xatolar" />
          <div className="mt-4 grid gap-3">
            {m.errors.map((e) => (
              <BaseCard key={e.id} tone="soft" padding="none" className="p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-foreground">{e.id}</span>
                  <span className="text-xs text-muted-foreground">{e.updated}</span>
                </div>
                <p className="mt-2 text-sm text-foreground">{e.message}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <span>S1: {e.s1}</span>
                  <span>S2: {e.s2}</span>
                </div>
              </BaseCard>
            ))}
          </div>
        </Card>

        <Card>
          <SectionHeader eyebrow="Queue" title="Bloklangan navbat" />
          <div className="mt-4 grid gap-3">
            {m.blocked.map((b) => (
              <BaseCard key={b.id} tone="soft" padding="none" className="p-4">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-foreground">{b.id}</span>
                  <span className="text-xs text-muted-foreground">retry: {b.retryAt}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <StatusPill tone={statusTone(b.s1)} value={`S1: ${b.s1}`} />
                  <StatusPill tone={statusTone(b.s2)} value={`S2: ${b.s2}`} />
                </div>
                <p className="mt-2 text-sm text-foreground">{b.reason}</p>
              </BaseCard>
            ))}
          </div>
        </Card>
      </section>
    </div>
  );
}

function ProgressStat({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="qa-stat-row">
      <div className="qa-stat-row-header">
        <span className="qa-stat-row-label">{label}</span>
        <span className="qa-stat-row-value">{value} / {total}</span>
      </div>
      <div className="qa-progress-bar">
        <div className="qa-progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function CountTile({ label, value, tone }: { label: string; value: number; tone: Tone }) {
  return (
    <BaseCard tone="soft" padding="none" className="flex items-center justify-between p-3">
      <StatusPill tone={tone} value={label} />
      <span className="text-xl font-semibold text-foreground">{value}</span>
    </BaseCard>
  );
}
