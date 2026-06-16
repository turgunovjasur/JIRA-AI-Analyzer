"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import {
  Activity,
  ChevronLeft,
  ClipboardList,
  FileCode2,
  Layers3,
  ListChecks,
  ShieldCheck,
} from "lucide-react";

import { AnalysisStatusBannerView } from "@/components/analysis-status-banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BaseCard, Card } from "@/components/ui/card";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import {
  BaseCheckGroup,
  BaseInputField,
  BaseTextAreaField,
  SettingsBaseCard,
} from "@/components/settings/base-card-system";
import { cn } from "@/lib/cn";
import type {
  GeneratedTestCase,
  TestCaseGenerationResult,
  TestcaseRunSnapshot,
  TZPRAgentRunSnapshot,
} from "@/lib/types";
import { useRecentRuns, type RecentRun } from "@/lib/use-recent-runs";

const TEST_TYPE_OPTIONS = [
  { value: "positive", label: "Positive" },
  { value: "negative", label: "Negative" },
  { value: "boundary", label: "Chegara" },
  { value: "edge", label: "Ekstremal" },
];

const TEST_TYPE_CHECK_OPTIONS = TEST_TYPE_OPTIONS.map((item) => ({
  badge: item.value,
  key: item.value,
  label: item.label,
}));
const SETTINGS_INPUT_CLASS = "settings-form-input";

const TERMINAL_RUN_STATES = new Set(["completed", "error", "failed", "blocked", "manual_review"]);
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Run tugaguncha (terminal holatgacha) snapshot'ni so'rab turadi (~2s interval).
async function pollTestcaseRun(
  runId: string,
  onTick: (snapshot: TestcaseRunSnapshot) => void,
): Promise<TestcaseRunSnapshot> {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    const res = await fetch(`/api/testcase/runs/${encodeURIComponent(runId)}`, {
      cache: "no-store",
    });
    const snap = (await res.json().catch(() => null)) as
      | (TestcaseRunSnapshot & { error?: string })
      | null;
    if (!res.ok) {
      throw new Error(snap?.error || "Testcase run holatini o'qishda xato.");
    }
    if (snap?.run_state) {
      onTick(snap);
      if (TERMINAL_RUN_STATES.has(snap.run_state)) {
        return snap;
      }
    }
    await sleep(2000);
  }
  throw new Error("Testcase run juda uzoq davom etdi (timeout).");
}

type CoverageFilter = "all" | "covered" | "uncovered";

function priorityTone(priority: string): "danger" | "warning" | "soft" {
  if (priority === "High") return "danger";
  if (priority === "Medium") return "warning";
  return "soft";
}

function StatusDot({ covered }: { covered: boolean }) {
  return (
    <span
      className={cn(
        "h-2 w-2 shrink-0 rounded-full",
        covered ? "bg-[color:var(--success)]" : "bg-[color:var(--error)]",
      )}
    />
  );
}

function StatCard({
  helper,
  icon,
  label,
  value,
}: {
  helper?: ReactNode;
  icon: ReactNode;
  label: string;
  value: ReactNode;
}) {
  return (
    <Card className="px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">{label}</span>
        <span className="text-primary">{icon}</span>
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-foreground">{value}</div>
      {helper ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{helper}</p> : null}
    </Card>
  );
}

const AGENT_STATE_META: Record<
  string,
  { badge: "success" | "warning" | "danger" | "soft"; label: string }
> = {
  pending: { badge: "soft", label: "kutmoqda" },
  running: { badge: "warning", label: "ishlamoqda" },
  completed: { badge: "success", label: "tugadi" },
  failed: { badge: "danger", label: "xato" },
  blocked: { badge: "danger", label: "bloklandi" },
  skipped: { badge: "soft", label: "o'tkazildi" },
};

const AGENT_ICONS = [<Layers3 key="a1" size={15} />, <Activity key="a2" size={15} />];

// Run snapshot'idagi agent holatlarini JONLI ko'rsatadi (kutmoqda → ishlamoqda → tugadi/xato).
function AgentRunFlow({ agentRuns }: { agentRuns: TZPRAgentRunSnapshot[] }) {
  const sorted = [...agentRuns].sort(
    (a, b) => (a.agent_order ?? 0) - (b.agent_order ?? 0),
  );
  return (
    <BaseCard
      as="div"
      className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_32px_minmax(0,1fr)] lg:items-stretch"
      padding="none"
    >
      {sorted.map((agent, index) => {
        const state = agent.state || "pending";
        const meta = AGENT_STATE_META[state] || AGENT_STATE_META.pending;
        const done = state === "completed";
        const active = state === "running";
        return (
          <div className="contents" key={agent.agent_key}>
            <BaseCard
              as="div"
              className="px-4 py-4"
              padding="none"
              tone={done ? "success" : undefined}
            >
              <div className="flex min-w-0 items-start gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border",
                    done
                      ? "border-[color:var(--success)] bg-[color:var(--success)] text-white"
                      : active
                        ? "border-primary text-primary"
                        : "border-border text-muted-foreground",
                  )}
                >
                  {AGENT_ICONS[index] || <Activity size={15} />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {agent.agent_label || agent.agent_key}
                  </p>
                  {agent.error_text ? (
                    <p className="mt-1 text-xs leading-5 text-[color:var(--error)]">{agent.error_text}</p>
                  ) : null}
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {active ? (
                  <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
                ) : null}
                <Badge tone={meta.badge}>{meta.label}</Badge>
              </div>
            </BaseCard>
            {index < sorted.length - 1 ? (
              <div
                className={cn(
                  "hidden self-center rounded-full lg:block lg:h-1",
                  done ? "bg-[color:var(--success)]" : "bg-border",
                )}
              />
            ) : null}
          </div>
        );
      })}
    </BaseCard>
  );
}

function RequirementsCoverage({
  filter,
  onFilterChange,
  result,
}: {
  filter: CoverageFilter;
  onFilterChange: (filter: CoverageFilter) => void;
  result: TestCaseGenerationResult;
}) {
  const requirements = result.requirements || [];
  const total = requirements.length;
  if (!total) return null;

  const uncovered = new Set(result.requirement_coverage?.uncovered_ids || []);
  const coveredCount = result.requirement_coverage?.covered_count ?? total - uncovered.size;
  const testCases = result.test_cases || [];

  const rows = requirements.filter((req) => {
    if (filter === "covered") return !uncovered.has(req.id);
    if (filter === "uncovered") return uncovered.has(req.id);
    return true;
  });

  return (
    <Card className="overflow-hidden" padding="none">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
            <ListChecks size={15} />
            Talablar qamrovi
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {total} talabdan {coveredCount} tasi test case bilan qoplangan
          </p>
        </div>
        <div className="inline-flex rounded-[12px] border border-border bg-[color:var(--bg-layer)] p-1">
          {([
            ["all", `Talablar (${total})`],
            ["covered", `Qoplangan (${coveredCount})`],
            ["uncovered", `Qoplanmagan (${uncovered.size})`],
          ] as [CoverageFilter, string][]).map(([value, label]) => (
            <button
              className={cn(
                "rounded-[9px] px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-colors",
                filter === value && "bg-card text-foreground shadow-sm",
              )}
              key={value}
              onClick={() => onFilterChange(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-border">
        {rows.length ? (
          rows.map((req, index) => {
            const isCovered = !uncovered.has(req.id);
            const covering = testCases.filter((tc) => (tc.requirement_ids || []).includes(req.id));
            return (
              <details className="group" key={req.id || index}>
                <summary className="grid cursor-pointer list-none grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-3 px-5 py-4 transition-colors hover:bg-[color:var(--bg-layer)]">
                  <StatusDot covered={isCovered} />
                  <span className="min-w-0 text-sm leading-6 text-foreground">
                    <span className="mr-1 font-mono text-xs text-muted-foreground">{req.id}</span>
                    {req.text}
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge tone={isCovered ? "success" : "danger"}>
                      {isCovered ? `${covering.length} ta TC` : "Qoplanmagan"}
                    </Badge>
                    <ChevronLeft
                      className="rotate-180 text-muted-foreground transition-transform group-open:rotate-90"
                      size={14}
                    />
                  </div>
                </summary>
                <div className="grid gap-3 border-t border-border bg-[color:var(--bg-layer)] px-5 py-4 lg:grid-cols-2">
                  <BaseCard as="div" className="px-4 py-3" padding="none">
                    <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Talab</div>
                    <p className="mt-2 text-sm leading-6 text-foreground">{req.text}</p>
                    <div className="mt-2">
                      <Badge tone="soft">manba: {req.source}</Badge>
                    </div>
                  </BaseCard>
                  <BaseCard as="div" className="px-4 py-3" padding="none">
                    <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                      Qoplovchi test case&apos;lar
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {covering.length ? (
                        covering.map((tc) => (
                          <Badge key={tc.id} tone="soft">{tc.id}</Badge>
                        ))
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          Bu talab uchun test case yo&apos;q — qo&apos;shilishi kerak.
                        </span>
                      )}
                    </div>
                  </BaseCard>
                </div>
              </details>
            );
          })
        ) : (
          <div className="px-5 py-4 text-sm text-muted-foreground">Bu filtrda talab yo&apos;q.</div>
        )}
      </div>
    </Card>
  );
}

function renderTestCaseCard(testCase: GeneratedTestCase) {
  return (
    <BaseCard
      as="details"
      className="qa-tc-card"
      key={`${testCase.id}-${testCase.title}`}
      padding="none"
    >
      <summary>
        <span className="qa-tc-id">{testCase.id}</span>
        <span className="flex-1 text-sm font-semibold text-foreground">{testCase.title}</span>
        <div className="flex shrink-0 gap-2">
          <Badge tone={priorityTone(testCase.priority)}>{testCase.priority}</Badge>
          <Badge tone="soft">{testCase.test_type}</Badge>
        </div>
      </summary>

      <div className="qa-tc-body">
        <div>
          <span className="qa-tc-section-label">Tavsif</span>
          <p className="text-foreground">{testCase.description}</p>
        </div>

        <div>
          <span className="qa-tc-section-label">Dastlabki shartlar</span>
          <p className="text-foreground">{testCase.preconditions}</p>
        </div>

        <div>
          <span className="qa-tc-section-label">Qadamlar</span>
          <ol className="qa-tc-steps">
            {testCase.steps.map((step, index) => (
              <li key={`${testCase.id}-step-${index}`}>{step}</li>
            ))}
          </ol>
        </div>

        <div>
          <span className="qa-tc-section-label">Kutilgan natija</span>
          <div className="qa-tc-expected">{testCase.expected_result}</div>
        </div>

        {testCase.requirement_ids?.length ? (
          <div>
            <span className="qa-tc-section-label">Qoplagan talablar</span>
            <div className="qa-tag-row">
              {testCase.requirement_ids.map((rid) => (
                <Badge key={`${testCase.id}-${rid}`} tone="success">{rid}</Badge>
              ))}
            </div>
          </div>
        ) : null}

        {testCase.tags?.length ? (
          <div className="qa-tag-row">
            {testCase.tags.map((tag) => (
              <Badge key={`${testCase.id}-${tag}`} tone="soft">#{tag}</Badge>
            ))}
          </div>
        ) : null}
      </div>
    </BaseCard>
  );
}

export function TestCaseGenerator() {
  const [taskKey, setTaskKey] = useState("");
  const [customContext, setCustomContext] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>(["positive", "negative"]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TestCaseGenerationResult | null>(null);
  const [coverageFilter, setCoverageFilter] = useState<CoverageFilter>("all");
  const [progress, setProgress] = useState<{ state?: string; message?: string | null } | null>(null);
  const [activeRun, setActiveRun] = useState<TestcaseRunSnapshot | null>(null);
  const { recent, addRecent } = useRecentRuns("testcase_generator");

  function applyFinalSnapshot(snapshot: TestcaseRunSnapshot) {
    setActiveRun(snapshot);
    const finalResult = snapshot.final_result || null;
    if (finalResult) {
      setResult(finalResult);
    }
    const ok = snapshot.run_state === "completed" && Boolean(finalResult?.success);
    if (!ok && !finalResult?.status_banner) {
      setError(
        snapshot.error_message
          || finalResult?.error_message
          || "Testcase run muvaffaqiyatsiz tugadi.",
      );
    }
  }

  async function trackRun(runId: string, runTaskKey: string) {
    const snapshot = await pollTestcaseRun(runId, (snap) => {
      setProgress({ state: snap.run_state, message: snap.status_message });
      setActiveRun(snap);
    });
    applyFinalSnapshot(snapshot);
    addRecent({
      run_id: runId,
      task_key: runTaskKey,
      saved_at: Date.now(),
      run_state: snapshot.run_state,
    });
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedTaskKey = taskKey.trim().toUpperCase();
    if (!normalizedTaskKey) {
      setError("Task key kiriting.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setResult(null);
    setCoverageFilter("all");
    setProgress({ state: "queued", message: "Run yaratilmoqda..." });
    setActiveRun(null);

    try {
      const createRes = await fetch("/api/testcase/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_key: normalizedTaskKey,
          test_types: selectedTypes,
          custom_context: customContext.trim(),
        }),
      });
      const created = (await createRes.json().catch(() => null)) as
        | (TestcaseRunSnapshot & { error?: string })
        | null;
      if (!createRes.ok) {
        setError(created?.error || "Testcase run yaratishda xato.");
        return;
      }
      const runId = created?.run_id;
      if (!runId) {
        setError("Backend run id qaytarmadi.");
        return;
      }
      setActiveRun(created);
      await trackRun(runId, normalizedTaskKey);
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Backend bilan ulanishda xato yuz berdi.";
      setError(message);
    } finally {
      setSubmitting(false);
      setProgress(null);
    }
  }

  async function reopenRun(entry: RecentRun) {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    setCoverageFilter("all");
    setActiveRun(null);
    setTaskKey(entry.task_key);
    setProgress({ state: "loading", message: "Eski natija yuklanmoqda..." });
    try {
      await trackRun(entry.run_id, entry.task_key);
    } catch (reopenError) {
      setError(
        reopenError instanceof Error
          ? reopenError.message
          : "Eski runni yuklashda xato.",
      );
    } finally {
      setSubmitting(false);
      setProgress(null);
    }
  }

  const total = result?.requirement_coverage?.total_requirements ?? result?.requirements?.length ?? 0;
  const coveredCount = result?.requirement_coverage?.covered_count ?? 0;
  const testCaseCount = result?.total_test_cases ?? result?.test_cases?.length ?? 0;

  return (
    <>
      <SettingsBaseCard
        header={(
          <SectionHeader
            action={<Badge tone="soft">Agent1 → Agent2</Badge>}
            eyebrow="Generate"
            title="Task yuborish"
          />
        )}
      >
        <form className="grid gap-5" onSubmit={onSubmit}>
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_180px] lg:items-end">
            <BaseInputField
              className={SETTINGS_INPUT_CLASS}
              label="Task Key"
              onChange={(value) => setTaskKey(value.toUpperCase())}
              placeholder="DEV-1234"
              value={taskKey}
            />
            <Button disabled={submitting} type="submit">
              {submitting ? "Yaratilmoqda..." : "Generate"}
            </Button>
          </div>

          <BaseCheckGroup
            onChange={(nextValues) => {
              setSelectedTypes((current) => (nextValues.length ? nextValues : current));
            }}
            options={TEST_TYPE_CHECK_OPTIONS}
            value={selectedTypes}
          />

          <BaseTextAreaField
            label="Qo'shimcha buyruq (ixtiyoriy)"
            onChange={setCustomContext}
            placeholder="Mahsulot, narx, limit, maxsus biznes qoidalarini yozing..."
            rows={5}
            value={customContext}
          />
        </form>
      </SettingsBaseCard>

      {recent.length ? (
        <SettingsBaseCard
          header={<SectionHeader eyebrow="History" title="So'nggi tekshiruvlar" />}
        >
          <div className="mt-4 grid gap-2">
            {recent.map((entry) => (
              <button
                className="flex items-center justify-between gap-3 rounded-[10px] border border-border bg-[color:var(--bg-layer)] px-4 py-3 text-left transition-colors hover:bg-card disabled:opacity-50"
                disabled={submitting}
                key={entry.run_id}
                onClick={() => reopenRun(entry)}
                type="button"
              >
                <span className="font-mono text-sm font-semibold text-foreground">{entry.task_key}</span>
                <Badge
                  tone={
                    entry.run_state === "completed"
                      ? "success"
                      : entry.run_state === "error" || entry.run_state === "failed"
                        ? "danger"
                        : "soft"
                  }
                >
                  {entry.run_state || "—"}
                </Badge>
              </button>
            ))}
          </div>
        </SettingsBaseCard>
      ) : null}

      {submitting ? (
        <Card className="px-5 py-4">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
            <span>
              {progress?.message || "Testcase yaratilmoqda..."}
              {progress?.state ? ` · ${progress.state}` : ""}
            </span>
          </div>
        </Card>
      ) : null}

      {activeRun?.agent_runs?.length ? <AgentRunFlow agentRuns={activeRun.agent_runs} /> : null}

      {error ? <Notice tone="error">{error}</Notice> : null}
      {result?.status_banner ? <AnalysisStatusBannerView banner={result.status_banner} /> : null}

      {result?.success ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              helper="Yaratilgan umumiy testcase soni"
              icon={<ClipboardList size={18} />}
              label="Test Cases"
              value={testCaseCount}
            />
            <StatCard
              helper="Agent1 ajratgan talablar"
              icon={<Layers3 size={18} />}
              label="Talablar"
              value={total}
            />
            <StatCard
              helper="Test case bilan qoplangan talablar"
              icon={<ShieldCheck size={18} />}
              label="Qoplangan"
              value={total ? `${coveredCount}/${total}` : 0}
            />
            <StatCard
              helper="High priority test case soni"
              icon={<FileCode2 size={18} />}
              label="High priority"
              value={result.by_priority?.High || 0}
            />
          </section>

          {result.warnings?.length ? (
            <SettingsBaseCard
              header={<SectionHeader eyebrow="Warnings" title="Ogohlantirishlar" />}
            >
              <div className="mt-4 grid gap-2">
                {result.warnings.map((warning, index) => (
                  <div key={index} className="qa-warning-item">⚠ {warning}</div>
                ))}
              </div>
            </SettingsBaseCard>
          ) : null}

          <RequirementsCoverage
            filter={coverageFilter}
            onFilterChange={setCoverageFilter}
            result={result}
          />

          <SettingsBaseCard
            header={(
              <SectionHeader
                action={<Badge tone="soft">{testCaseCount} ta</Badge>}
                eyebrow="Test Cases"
                title="Yaratilgan scenariylar"
              />
            )}
          >
            {result.test_cases?.length ? (
              <div className="mt-5 grid gap-3">
                {result.test_cases.map((testCase) => renderTestCaseCard(testCase))}
              </div>
            ) : (
              <p className="mt-5 text-sm text-muted-foreground">Test case&apos;lar topilmadi.</p>
            )}
          </SettingsBaseCard>

          {result.comment_changes_detected && result.comment_summary ? (
            <Notice tone="warning">{result.comment_summary}</Notice>
          ) : null}

          <SettingsBaseCard
            header={<SectionHeader eyebrow="Technical Spec" title="TZ content" />}
          >
            <div className="qa-analysis-block mt-4">
              {result.tz_content || "TZ content qaytmadi."}
            </div>
          </SettingsBaseCard>
        </>
      ) : result ? (
        <SettingsBaseCard
          header={<SectionHeader eyebrow="Generation Error" title="Test case generation tugamadi" />}
        >
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            {result.error_message || "Xatolik tafsiloti qaytmadi."}
          </p>
          {result.tz_content ? (
            <>
              <h3 className="mt-6 text-base font-semibold">TZ content</h3>
              <div className="qa-analysis-block mt-3">{result.tz_content}</div>
            </>
          ) : null}
        </SettingsBaseCard>
      ) : null}
    </>
  );
}
