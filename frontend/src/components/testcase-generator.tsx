"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronLeft,
  Clock3,
  ClipboardList,
  Copy,
  Database,
  FileCode2,
  Layers3,
  ListChecks,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";

import { AnalysisStatusBannerView } from "@/components/analysis-status-banner";
import { PreflightChecksView } from "@/components/preflight-checks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BaseCard, Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import { Textarea } from "@/components/ui/textarea";
import { SettingsBaseCard } from "@/components/settings/base-card-system";
import { useRunPolling } from "@/hooks/use-run-polling";
import { copyTextToClipboard } from "@/lib/clipboard";
import { cn } from "@/lib/cn";
import { getModuleRunErrorMessage, normalizeModuleRunErrorPayload } from "@/lib/module-errors";
import { type RecentRunScope } from "@/lib/use-recent-runs";
import type {
  GeneratedTestCase,
  TestCaseGenerationResult,
  TestcaseScenario,
  TestcaseRunSnapshot,
  TZPRAgentRunSnapshot,
  TZPRRunEvent,
} from "@/lib/types";

type PipelineState = "pending" | "running" | "completed" | "failed";

const MODULE_KEY = "testcase_generator";

const FALLBACK_TESTCASE_AGENTS: TZPRAgentRunSnapshot[] = [
  {
    agent_key: "agent1_requirements",
    agent_label: "Talablar",
    agent_order: 1,
    primary_model: "",
    state: "pending",
  },
  {
    agent_key: "agent2_testcase",
    agent_label: "Testcase writer",
    agent_order: 2,
    primary_model: "",
    state: "pending",
  },
  {
    agent_key: "agent3_audit",
    agent_label: "Audit",
    agent_order: 3,
    primary_model: "",
    state: "pending",
  },
];

type CoverageFilter = "all" | "covered" | "uncovered";

function priorityTone(priority: string): "danger" | "warning" | "soft" {
  if (priority === "High") return "danger";
  if (priority === "Medium") return "warning";
  return "soft";
}

function isTerminalRunState(value?: string | null) {
  return ["completed", "manual_review", "blocked", "failed", "error"].includes((value || "").toLowerCase());
}

function isResolvedRunSnapshot(run?: TestcaseRunSnapshot | null) {
  return Boolean(run && (isTerminalRunState(run.run_state) || run.finished_at || run.final_result));
}

function deriveResultError(result: TestCaseGenerationResult) {
  if (result.success || result.status_banner) return null;
  return result.error_message || "Testcase generation muvaffaqiyatsiz tugadi.";
}

function formatDateTime(value?: string | null) {
  if (!value) return "Noma'lum";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Noma'lum";
  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function formatAgentDuration(agent?: TZPRAgentRunSnapshot | null) {
  const started = agent?.started_at ? new Date(agent.started_at).getTime() : null;
  const finished = agent?.finished_at ? new Date(agent.finished_at).getTime() : null;
  if (!started) return "Boshlanmagan";
  const end = finished && finished >= started ? finished : Date.now();
  return `${Math.max(0, Math.round((end - started) / 1000))}s`;
}

function getAgentTone(value?: string | null): "soft" | "success" | "warning" | "danger" {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed" || normalized === "skipped") return "success";
  if (normalized === "running" || normalized === "pending") return "warning";
  if (normalized === "failed" || normalized === "blocked" || normalized === "error") return "danger";
  return "soft";
}

function normalizePipelineState(value?: string | null): PipelineState {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed" || normalized === "skipped") return "completed";
  if (normalized === "running") return "running";
  if (normalized === "failed" || normalized === "blocked" || normalized === "error") return "failed";
  return "pending";
}

function getRunProgress(run?: TestcaseRunSnapshot | null, result?: TestCaseGenerationResult | null) {
  if (result?.success || run?.final_result || run?.finished_at || run?.run_state === "completed") return 100;
  const agents = run?.agent_runs || [];
  if (!agents.length) return run?.run_state === "running" ? 18 : 0;
  const completed = agents.filter((agent) => normalizePipelineState(agent.state) === "completed").length;
  const running = agents.some((agent) => normalizePipelineState(agent.state) === "running");
  return Math.min(96, Math.round((completed / Math.max(agents.length, 1)) * 100) + (running ? 12 : 0));
}

function getPipelineAgents(run?: TestcaseRunSnapshot | null) {
  const actual = run?.agent_runs || [];
  const agents = actual.length ? actual : FALLBACK_TESTCASE_AGENTS;
  return [...agents].sort((left, right) => (left.agent_order || 99) - (right.agent_order || 99));
}

function getAgentShortLabel(agent: TZPRAgentRunSnapshot, index: number) {
  const label = agent.agent_label || agent.agent_key || `Agent ${index + 1}`;
  return label
    .replace(/^Agent\s*\d+\s*[·:-]\s*/i, "")
    .replace(/^agent\d+[_-]?/i, "")
    .replace(/_/g, " ");
}

function getAgentSubLabel(index: number) {
  if (index === 0) return "TZ matnidan talablar ajratiladi";
  if (index === 1) return "Testcase yoziladi, missing requirement bo'lsa repair ishlaydi";
  if (index === 2) return "Duplicate audit va scenario grouping bajariladi";
  return "Multi-agent bosqichi";
}

function shortModelName(model?: string | null) {
  const value = (model || "").trim();
  if (!value) return "";
  if (/flash/i.test(value)) return "Flash";
  if (/\bpro\b/i.test(value)) return "Pro";
  return value.replace(/^gemini-?/i, "");
}

function getAgentMetrics(agent: TZPRAgentRunSnapshot) {
  const artifact = (agent.artifact ?? null) as Record<string, unknown> | null;
  const metrics = (artifact?.metrics ?? {}) as Record<string, unknown>;
  const num = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : 0);
  return {
    retry: num(metrics.retry_count),
    technical: num(metrics.technical_failure_count),
    fallback: num(metrics.fallback_model_call_count),
    requirements: num(metrics.requirement_count),
    testCases: num(metrics.test_case_count),
    covered: num(metrics.covered_requirement_count),
    missing: num(metrics.missing_requirement_count),
    repairs: num(metrics.repair_count),
    scenarios: num(metrics.scenario_count),
    findings: num(metrics.audit_finding_count),
  };
}

function getEventAgentKey(event: TZPRRunEvent) {
  const direct = (event.agent_key || "").trim();
  if (direct) return direct;
  const text = `${event.message || ""} ${event.event_type || ""}`.toLowerCase();
  if (text.includes("agent1")) return "agent1_requirements";
  if (text.includes("agent2")) return "agent2_testcase";
  if (text.includes("agent3")) return "agent3_audit";
  return "";
}

function AgentActivityList({ events }: { events: TZPRRunEvent[] }) {
  if (!events.length) return null;
  return (
    <BaseCard as="div" className="mt-3 px-3 py-2" padding="none" tone="soft">
      <div className="text-xs font-semibold text-foreground">Jarayonlar</div>
      <div className="mt-2 grid gap-2 text-xs leading-5">
        {events.slice(-4).map((event, index) => (
          <div className="grid grid-cols-[64px_minmax(0,1fr)] gap-2" key={`${event.id || index}-${event.created_at || ""}`}>
            <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>
            <span className={cn("min-w-0 text-muted-foreground", event.level === "error" && "text-[color:var(--error)]")}>
              {event.message || event.event_type || "Event tafsiloti qaytmadi."}
            </span>
          </div>
        ))}
      </div>
    </BaseCard>
  );
}

function EventLog({ events }: { events: TZPRRunEvent[] }) {
  return (
    <BaseCard as="div" className="max-h-64 overflow-y-auto font-mono text-xs" padding="none" tone="soft">
      {events.length ? events.slice(-8).reverse().map((event, index) => (
        <div
          className="grid grid-cols-[92px_minmax(0,1fr)] gap-3 border-b border-border px-4 py-3 last:border-0"
          key={`${event.id || index}-${event.created_at || ""}`}
        >
          <span className="text-muted-foreground">{formatDateTime(event.created_at)}</span>
          <span className={cn("min-w-0 text-foreground", event.level === "error" && "text-[color:var(--error)]")}>
            {getEventAgentKey(event) ? <strong>{getEventAgentKey(event)}: </strong> : null}
            {event.message || event.event_type || "Event tafsiloti qaytmadi."}
          </span>
        </div>
      )) : (
        <div className="px-4 py-4 text-muted-foreground">Eventlar hali qaytmadi.</div>
      )}
    </BaseCard>
  );
}

function getAgentModelInfo(agent: TZPRAgentRunSnapshot) {
  const primary = (agent.primary_model || "").trim();
  const actual = (agent.actual_model || primary || "").trim();
  const metrics = getAgentMetrics(agent);
  const fallbackUsed =
    Boolean(agent.used_fallback) ||
    metrics.fallback > 0 ||
    (Boolean(primary) && Boolean(actual) && primary !== actual);
  const transitioned = Boolean(primary) && Boolean(actual) && primary !== actual;
  return { primary, actual, fallbackUsed, transitioned };
}

function getAgentPhaseText(agent: TZPRAgentRunSnapshot, index: number, state: PipelineState) {
  if (state === "running") {
    if (index === 0) return "Agent1 talablarni ajratmoqda...";
    if (index === 1) return "Agent2 testcase yaratmoqda...";
    if (index === 2) return "Agent3 audit va grouping qilmoqda...";
    return "Bajarilmoqda...";
  }
  if (state === "failed") {
    return agent.error_text || agent.output_summary || "Xatolik bilan to'xtadi.";
  }
  if (state === "pending") {
    return "Navbatda - oldingi bosqich tugashini kutmoqda.";
  }
  return agent.output_summary || agent.input_summary || getAgentSubLabel(index);
}

function RequirementStatusDot({ covered }: { covered: boolean }) {
  return (
    <span
      className={cn(
        "h-2 w-2 shrink-0 rounded-full",
        covered ? "bg-[color:var(--success)]" : "bg-[color:var(--error)]",
      )}
    />
  );
}

function AgentStatusDot({ state }: { state: PipelineState }) {
  return (
    <span
      className={cn(
        "h-2 w-2 shrink-0 rounded-full",
        state === "pending" && "bg-zinc-400",
        state === "running" && "animate-pulse bg-primary shadow-[0_0_0_4px_var(--accent-soft)]",
        state === "completed" && "bg-[color:var(--success)]",
        state === "failed" && "bg-[color:var(--error)]",
      )}
    />
  );
}

function AgentIcon({ state, index }: { state: PipelineState; index: number }) {
  if (state === "running") {
    return <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />;
  }
  if (state === "completed") return <Check size={15} strokeWidth={2.5} />;
  if (state === "failed") return <XCircle size={15} strokeWidth={2.5} />;
  if (index === 0) return <Layers3 size={15} />;
  if (index === 1) return <Activity size={15} />;
  return <Sparkles size={15} />;
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

function AgentPipeline({ run }: { run: TestcaseRunSnapshot | null }) {
  const agents = getPipelineAgents(run).slice(0, 3);
  const events = run?.run_events || [];
  return (
    <BaseCard
      as="div"
      className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_32px_minmax(0,1fr)_32px_minmax(0,1fr)] lg:items-stretch"
      padding="none"
    >
      {agents.map((agent, index) => {
        const state = normalizePipelineState(agent.state);
        const nextState = normalizePipelineState(agents[index + 1]?.state);
        const connectorDone = state === "completed";
        const connectorActive = state === "completed" && nextState === "running";
        const agentEvents = events.filter((event) => getEventAgentKey(event) === agent.agent_key);

        return (
          <div className="contents" key={agent.agent_key || index}>
            <BaseCard
              as="div"
              className={cn(
                "px-4 py-4 transition-colors",
                state === "pending" && "opacity-70",
              )}
              padding="none"
              tone={state === "completed" ? "success" : state === "failed" ? "danger" : state === "running" ? "warning" : "soft"}
            >
              <div className="flex min-w-0 items-start gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] border bg-card text-muted-foreground",
                    state === "running" && "border-primary bg-primary text-white",
                    state === "completed" && "border-[color:var(--success)] bg-[color:var(--success)] text-white",
                    state === "failed" && "border-[color:var(--error)] bg-[color:var(--error)] text-white",
                  )}
                >
                  <AgentIcon index={index} state={state} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-foreground">
                    Agent {index + 1} - {getAgentShortLabel(agent, index)}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {getAgentPhaseText(agent, index, state)}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Badge tone={getAgentTone(agent.state)}>{agent.state || "pending"}</Badge>
                {(() => {
                  const model = getAgentModelInfo(agent);
                  if (model.fallbackUsed && model.transitioned) {
                    return (
                      <Badge tone="warning" className="inline-flex items-center gap-1">
                        <RefreshCw size={11} />
                        {shortModelName(model.primary)}
                        <ArrowRight size={10} />
                        {shortModelName(model.actual)}
                      </Badge>
                    );
                  }
                  return <Badge tone="soft">{shortModelName(model.actual) || "model"}</Badge>;
                })()}
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock3 size={12} />
                  {formatAgentDuration(agent)}
                </span>
                {(() => {
                  const metrics = getAgentMetrics(agent);
                  return (
                    <>
                      {metrics.fallback > 0 ? <Badge tone="warning">{metrics.fallback}x fallback</Badge> : null}
                      {metrics.retry > 0 ? <Badge tone="soft">{metrics.retry} qayta urinish</Badge> : null}
                      {metrics.technical > 0 ? <Badge tone="danger">{metrics.technical} texnik xato</Badge> : null}
                      {metrics.requirements > 0 ? <Badge tone="soft">{metrics.requirements} talab</Badge> : null}
                      {metrics.testCases > 0 ? <Badge tone="soft">{metrics.testCases} TC</Badge> : null}
                      {metrics.scenarios > 0 ? <Badge tone="soft">{metrics.scenarios} scenario</Badge> : null}
                      {metrics.missing > 0 ? <Badge tone="danger">{metrics.missing} qoplanmagan</Badge> : null}
                      {metrics.repairs > 0 ? <Badge tone="warning">{metrics.repairs} repair</Badge> : null}
                      {metrics.findings > 0 ? <Badge tone="warning">{metrics.findings} finding</Badge> : null}
                    </>
                  );
                })()}
              </div>

              <AgentActivityList events={agentEvents} />

              {agent.error_text ? (
                <BaseCard as="div" className="mt-3 px-3 py-2 text-xs leading-5 text-[color:var(--error)]" padding="none" tone="danger">
                  {agent.error_text}
                </BaseCard>
              ) : null}

              {(agent.warnings || []).length ? (
                <BaseCard as="div" className="mt-2 px-3 py-2" padding="none" tone="warning">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-[color:var(--warning)]">
                    <AlertTriangle size={12} />
                    Nima bo'ldi?
                  </div>
                  <ul className="mt-1 space-y-1 text-xs leading-5 text-muted-foreground">
                    {(agent.warnings || []).slice(0, 3).map((warning, warnIndex) => (
                      <li key={warnIndex}>- {warning}</li>
                    ))}
                    {(agent.warnings || []).length > 3 ? (
                      <li className="text-muted-foreground/70">
                        +{(agent.warnings || []).length - 3} ta yana
                      </li>
                    ) : null}
                  </ul>
                </BaseCard>
              ) : null}
            </BaseCard>
            {index < agents.length - 1 ? (
              <div
                className={cn(
                  "hidden self-center rounded-full lg:block lg:h-1",
                  connectorDone && "bg-[color:var(--success)]",
                  connectorActive && "bg-primary",
                  !connectorDone && "bg-border",
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
                  <RequirementStatusDot covered={isCovered} />
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

function renderScenarioCard(scenario: TestcaseScenario, index: number) {
  const cases = scenario.test_cases || [];
  return (
    <BaseCard
      as="details"
      className="qa-tc-card"
      key={`${scenario.scenario_title}-${index}`}
      padding="none"
    >
      <summary>
        <span className="qa-tc-id">SC-{String(index + 1).padStart(2, "0")}</span>
        <span className="flex-1 text-sm font-semibold text-foreground">
          {scenario.scenario_title || "Test scenario"}
        </span>
        <div className="flex shrink-0 gap-2">
          <Badge tone="soft">{cases.length} ta TC</Badge>
          {scenario.screen_or_flow ? <Badge tone="soft">{scenario.screen_or_flow}</Badge> : null}
        </div>
      </summary>

      <div className="qa-tc-body">
        {scenario.requirement_ids?.length ? (
          <div className="qa-tag-row">
            {scenario.requirement_ids.map((rid) => (
              <Badge key={`${scenario.scenario_title}-${rid}`} tone="success">{rid}</Badge>
            ))}
          </div>
        ) : null}
        <div className="grid gap-3">
          {cases.map((testCase) => renderTestCaseCard(testCase))}
        </div>
      </div>
    </BaseCard>
  );
}

type TestCaseGeneratorProps = {
  recentScope?: RecentRunScope;
};

export function TestCaseGenerator({ recentScope }: TestCaseGeneratorProps) {
  const [taskKey, setTaskKey] = useState("");
  const [customContext, setCustomContext] = useState("");
  const [coverageFilter, setCoverageFilter] = useState<CoverageFilter>("all");
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");

  const {
    activeRun,
    setActiveRun,
    result,
    setResult,
    error,
    setError,
    moduleError,
    setModuleError,
    submitting,
    setSubmitting,
    startStatus,
    refreshStartStatus,
    recent,
    runInProgress,
    applyRunSnapshot,
    rememberRun,
  } = useRunPolling<TestCaseGenerationResult, TestcaseRunSnapshot>({
    moduleKey: MODULE_KEY,
    recentScope,
    apiBasePath: "/api/testcase",
    taskKey,
    isTerminalRunState,
    deriveResultError,
    // Testcase snapshot error_message'ni faqat terminal (persistFinal) holatda ko'rsatadi.
    getSnapshotErrorMessage: (snapshot, persistFinal) =>
      persistFinal && snapshot.error_message?.trim() ? snapshot.error_message : null,
    onBeforeReopen: (entry) => {
      setCoverageFilter("all");
      setTaskKey(entry.task_key);
    },
    pollErrorMessage: "Testcase run polling xatosi.",
    pollFailureMessage: "Testcase run polling vaqtida xato yuz berdi.",
    reopenFailureMessage: "Eski runni yuklashda xato.",
  });

  const agentPanelRun = activeRun;
  const progress = getRunProgress(agentPanelRun, result);
  const runEvents = agentPanelRun?.run_events || [];
  const canCopyDebug = Boolean(agentPanelRun || result || moduleError || error);

  useEffect(() => {
    setCopyState("idle");
  }, [agentPanelRun?.run_id, agentPanelRun?.updated_at, result?.task_key, moduleError?.error, error]);

  async function startRun() {
    if (submitting || runInProgress) return;
    const normalizedTaskKey = taskKey.trim().toUpperCase();
    setSubmitting(true);
    setError(null);
    setModuleError(null);
    setResult(null);
    setCoverageFilter("all");
    setActiveRun(null);

    try {
      const createRes = await fetch("/api/testcase/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_key: normalizedTaskKey,
          custom_context: customContext.trim(),
        }),
      });
      const created = (await createRes.json().catch(() => null)) as
        | (TestcaseRunSnapshot & { error?: string })
        | null;
      if (!createRes.ok) {
        const normalizedError = normalizeModuleRunErrorPayload(created, {
          moduleKey: "testcase_generator",
          taskKey: normalizedTaskKey,
          message: "Testcase run yaratishda xato.",
        });
        setModuleError(normalizedError);
        setError(
          normalizedError.status_banner
            ? null
            : getModuleRunErrorMessage(normalizedError, "Testcase run yaratishda xato."),
        );
        return;
      }
      const runId = created?.run_id;
      if (!runId) {
        setError("Backend run id qaytarmadi.");
        return;
      }
      applyRunSnapshot(created, {
        persistFinal: isResolvedRunSnapshot(created) || isTerminalRunState(created.run_state),
      });
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Backend bilan ulanishda xato yuz berdi.";
      setError(message);
    } finally {
      setSubmitting(false);
      // Run urinishidan keyin Gemini kvota / qolgan urinishni yangilash.
      void refreshStartStatus();
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await startRun();
  }

  async function copyDebugJson() {
    const debugPayload = agentPanelRun || result || moduleError || (
      error
        ? {
          copied_at: new Date().toISOString(),
          error,
          module_key: "testcase_generator",
          task_key: taskKey.trim().toUpperCase() || null,
        }
        : null
    );
    const debugJson = debugPayload ? JSON.stringify(debugPayload, null, 2) : "";
    if (!debugJson.trim()) {
      setCopyState("error");
      return;
    }

    const copied = await copyTextToClipboard(debugJson);
    if (copied) {
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1600);
    } else {
      setCopyState("error");
    }
  }

  function resetView() {
    if (agentPanelRun) {
      rememberRun(agentPanelRun);
    }
    setResult(null);
    setActiveRun(null);
    setModuleError(null);
    setError(null);
    setCoverageFilter("all");
    setCopyState("idle");
  }

  const total = result?.requirement_coverage?.total_requirements ?? result?.requirements?.length ?? 0;
  const coveredCount = result?.requirement_coverage?.covered_count ?? 0;
  const testCaseCount = result?.total_test_cases ?? result?.test_cases?.length ?? 0;
  const pageTitle = result?.task_key || agentPanelRun?.task_key || "Test Case Generator";
  const pageSubtitle = runInProgress
    ? `${progress}% · ${agentPanelRun?.status_message || "Agentlar testcase yaratmoqda"}`
    : result?.success
      ? "Agentlar yaratgan testcase va scenario grouping natijasi"
      : "JIRA task asosida requirement coverage bilan testcase generatsiya qiling.";
  const showRunCard = !submitting && !agentPanelRun && !result;

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            <ClipboardList size={14} />
            Test Case Generator
          </div>
          <h1 className="mt-2 flex flex-wrap items-center gap-3 text-2xl font-semibold tracking-tight text-foreground">
            <span className="min-w-0 break-words">{pageTitle}</span>
            {runInProgress ? <Badge tone="warning"><AgentStatusDot state="running" /> Jonli</Badge> : null}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{pageSubtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild size="sm" type="button" variant="ghost">
            <Link href="/testcase/history">
              <Clock3 size={14} />
              History
              <Badge tone="soft">{recent.length}</Badge>
            </Link>
          </Button>
          {canCopyDebug ? (
            <Button onClick={() => void copyDebugJson()} size="sm" type="button" variant="ghost">
              <Copy size={14} />
              {copyState === "copied" ? "Nusxalandi" : copyState === "error" ? "Copy xatosi" : "Copy JSON"}
            </Button>
          ) : null}
          {agentPanelRun || result ? (
            <Button
              className="bg-primary !text-white hover:bg-[color:var(--brand-strong)] hover:!text-white"
              onClick={resetView}
              size="sm"
              type="button"
            >
              <ChevronLeft size={14} />
              New Task
            </Button>
          ) : null}
        </div>
      </div>

      {moduleError?.status_banner ? <AnalysisStatusBannerView banner={moduleError.status_banner} /> : null}
      {moduleError?.preflight_checks?.length ? <PreflightChecksView checks={moduleError.preflight_checks} /> : null}
      {result?.status_banner ? <AnalysisStatusBannerView banner={result.status_banner} /> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}

      {startStatus?.message ? (
        <Notice
          tone={
            startStatus.level === "error"
              ? "error"
              : startStatus.level === "warning"
                ? "warning"
                : "info"
          }
        >
          {startStatus.message}
        </Notice>
      ) : null}

      {showRunCard ? (
        <section className="grid gap-4">
          <Card
            as="form"
            className="mx-auto grid w-full max-w-2xl gap-5 p-7"
            onSubmit={onSubmit}
          >
            <div className="text-center">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-[13px] bg-primary text-white shadow-sm">
                <Play size={18} fill="currentColor" />
              </div>
              <h2 className="mt-4 text-lg font-semibold text-foreground">Testcase generatsiyani boshlash</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Agent1 talablarni ajratadi, Agent2 testcase yozadi, Agent3 audit va scenario grouping qiladi.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_170px] sm:items-end">
              <Field label="JIRA Task Key">
                <Input
                  autoFocus={showRunCard}
                  className="font-mono text-base"
                  onChange={(event) => setTaskKey(event.target.value.toUpperCase())}
                  placeholder="1234 yoki DEV-1234"
                  value={taskKey}
                />
              </Field>

              <Button disabled={submitting || runInProgress || Boolean(startStatus?.blocked)} fullWidth type="submit">
                {submitting || runInProgress ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Yaratilmoqda...
                  </>
                ) : (
                  <>
                    <Play size={15} fill="currentColor" />
                    Generate
                  </>
                )}
              </Button>
            </div>

            <div className="grid gap-4 rounded-[12px] border border-border bg-[color:var(--bg-layer)] p-4">
              <div className="grid gap-2">
                <Field label="Qo'shimcha buyruq (ixtiyoriy)">
                  <Textarea
                    onChange={(event) => setCustomContext(event.target.value)}
                    placeholder="Mahsulot, narx, limit, maxsus biznes qoidalarini yozing..."
                    rows={5}
                    value={customContext}
                  />
                </Field>
              </div>
            </div>
          </Card>
        </section>
      ) : null}

      {agentPanelRun ? (
        <div className="grid gap-4">
          <AgentPipeline run={agentPanelRun} />

          {runInProgress ? (
            <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
              <Card>
                <div className="flex items-center justify-between gap-3">
                  <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                    <AgentStatusDot state="running" />
                    <Activity size={15} />
                    Umumiy progress
                  </div>
                  <span className="font-mono text-sm font-semibold text-foreground">{progress}%</span>
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-[color:var(--bg-strong)]">
                  <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <BaseCard as="div" className="px-3 py-3" padding="none" tone="soft">
                    <p className="text-xs text-muted-foreground">Run state</p>
                    <p className="mt-1 font-semibold text-foreground">{agentPanelRun.run_state || "queued"}</p>
                  </BaseCard>
                  <BaseCard as="div" className="px-3 py-3" padding="none" tone="soft">
                    <p className="text-xs text-muted-foreground">Bosqich</p>
                    <p className="mt-1 font-semibold text-foreground">{agentPanelRun.active_phase || "queued"}</p>
                  </BaseCard>
                  <BaseCard as="div" className="px-3 py-3" padding="none" tone="soft">
                    <p className="text-xs text-muted-foreground">Yangilandi</p>
                    <p className="mt-1 font-semibold text-foreground">{formatDateTime(agentPanelRun.updated_at)}</p>
                  </BaseCard>
                </div>
              </Card>
              <Card>
                <div className="mb-3 flex items-center justify-between gap-2">
                  <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                    <Database size={15} />
                    Jonli event log
                  </div>
                  <AgentStatusDot state="running" />
                </div>
                <EventLog events={runEvents} />
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

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

          {result.audit_findings?.length ? (
            <SettingsBaseCard
              header={<SectionHeader eyebrow="Agent3" title="Audit izohlari" />}
            >
              <div className="mt-4 grid gap-2">
                {result.audit_findings.map((finding, index) => (
                  <div key={index} className="qa-warning-item">
                    <strong>{finding.type}</strong>: {finding.reason}
                  </div>
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
            {result.test_scenarios?.length ? (
              <div className="mt-5 grid gap-3">
                {result.test_scenarios.map((scenario, index) => renderScenarioCard(scenario, index))}
              </div>
            ) : result.test_cases?.length ? (
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
    </div>
  );
}
