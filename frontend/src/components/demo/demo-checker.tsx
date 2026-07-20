"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Check,
  ChevronLeft,
  Database,
  FileCode2,
  Frame,
  GitPullRequest,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { BaseCard, Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ComplianceRing } from "@/components/ui/compliance-ring";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import {
  DEMO_CHECKER_AGENTS,
  DEMO_CHECKER_EVENTS,
  DEMO_CHECKER_RESULT,
  DEMO_TASK_KEY,
  type DemoRequirementStatus,
} from "@/lib/demo-data";

type Phase = "idle" | "running" | "done";
type AgentState = "pending" | "running" | "completed";
type Filter = "all" | DemoRequirementStatus;

const STATUS_LABEL: Record<DemoRequirementStatus, string> = {
  completed: "Bajarilgan",
  failed: "Topilmadi",
  skipped: "Skip qilingan",
};

export function DemoChecker() {
  const [taskKey, setTaskKey] = useState(DEMO_TASK_KEY);
  const [phase, setPhase] = useState<Phase>("idle");
  const [agents, setAgents] = useState<AgentState[]>(["pending", "pending", "pending"]);
  const [progress, setProgress] = useState(0);
  const [visibleEvents, setVisibleEvents] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const timers = useRef<number[]>([]);

  const clearTimers = () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  };
  const at = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms));

  useEffect(() => () => clearTimers(), []);

  function reset() {
    clearTimers();
    setPhase("idle");
    setAgents(["pending", "pending", "pending"]);
    setProgress(0);
    setVisibleEvents(0);
    setFilter("all");
  }

  function run() {
    clearTimers();
    setPhase("running");
    setAgents(["running", "pending", "pending"]);
    setProgress(16);
    setVisibleEvents(3);
    at(1200, () => {
      setAgents(["completed", "running", "pending"]);
      setProgress(46);
      setVisibleEvents(4);
    });
    at(2500, () => {
      setAgents(["completed", "completed", "running"]);
      setProgress(76);
      setVisibleEvents(6);
    });
    at(3800, () => {
      setAgents(["completed", "completed", "completed"]);
      setProgress(100);
      setVisibleEvents(7);
    });
    at(4500, () => setPhase("done"));
  }

  const r = DEMO_CHECKER_RESULT;
  const runInProgress = phase === "running";
  const done = phase === "done";
  const reqs = r.requirements;
  const counts = {
    all: reqs.length,
    completed: reqs.filter((x) => x.status === "completed").length,
    failed: reqs.filter((x) => x.status === "failed").length,
    skipped: reqs.filter((x) => x.status === "skipped").length,
  };
  const filtered = filter === "all" ? reqs : reqs.filter((x) => x.status === filter);

  return (
    <div className="grid gap-5">
      {/* header toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="qa-eyebrow inline-flex items-center gap-2">
            <ShieldCheck size={14} /> TZ-PR Checker
          </span>
          <h2 className="qa-page-heading">Multi-agent moslik tekshiruvi</h2>
          <p className="qa-page-desc">
            {runInProgress
              ? `${progress}% · Agentlar ishlamoqda`
              : "TZ va PR mosligini 3 agent tekshiradi: scope → verify → arbiter."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {runInProgress ? (
            <Badge tone="warning">
              <span className="mr-1.5 inline-block h-2 w-2 animate-pulse rounded-full bg-[color:var(--warning)]" />
              Jonli
            </Badge>
          ) : null}
          {phase !== "idle" ? (
            <Button variant="ghost" size="sm" onClick={reset}>
              <RefreshCw size={14} /> Yangi task
            </Button>
          ) : null}
        </div>
      </div>

      {/* input card */}
      {phase === "idle" ? (
        <Card
          as="form"
          className="mx-auto grid w-full max-w-2xl gap-5 p-7"
          onSubmit={(e: React.FormEvent) => {
            e.preventDefault();
            run();
          }}
        >
          <div className="flex flex-col items-center gap-2 text-center">
            <span className="flex h-11 w-11 items-center justify-center rounded-[13px] bg-primary text-white">
              <Play size={18} fill="currentColor" />
            </span>
            <h3 className="text-xl font-semibold text-foreground">Tahlilni boshlash</h3>
            <p className="max-w-md text-sm text-muted-foreground">
              JIRA task kalitini kiriting — Agent1 (scope) → Agent2 (verify) → Agent3 (arbiter) ishga tushadi.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_170px] sm:items-end">
            <Field label="JIRA Task Key">
              <Input
                className="font-mono text-base"
                value={taskKey}
                onChange={(e) => setTaskKey(e.target.value.toUpperCase())}
                placeholder="1234 yoki DEV-1234"
              />
            </Field>
            <Button type="submit" fullWidth>
              <Play size={16} fill="currentColor" /> Boshlash
            </Button>
          </div>
          <p className="text-center text-xs text-muted-foreground">
            Demo: natija oldindan tayyorlangan namuna ({DEMO_TASK_KEY}).
          </p>
        </Card>
      ) : null}

      {/* agent pipeline */}
      {phase !== "idle" ? (
        <div className="grid gap-3 md:grid-cols-3">
          {DEMO_CHECKER_AGENTS.map((agent, i) => {
            const state = agents[i];
            const tone = state === "completed" ? "success" : state === "running" ? "warning" : "soft";
            return (
              <BaseCard
                key={agent.key}
                tone={tone}
                className={cn("flex flex-col gap-3", state === "pending" && "opacity-70")}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px]",
                      state === "running" && "bg-primary text-white",
                      state === "completed" && "bg-[color:var(--success)] text-white",
                      state === "pending" && "bg-[color:var(--bg-strong)] text-muted-foreground",
                    )}
                  >
                    {state === "running" ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                    ) : state === "completed" ? (
                      <Check size={16} />
                    ) : (
                      <span className="text-sm font-bold">{i + 1}</span>
                    )}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground">
                      Agent {i + 1} · {agent.label}
                    </p>
                    <p className="text-xs leading-5 text-muted-foreground">
                      {state === "running"
                        ? agent.running
                        : state === "completed"
                          ? agent.done
                          : "Navbatda — oldingi agent tugashini kutmoqda."}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone={tone === "success" ? "success" : tone === "warning" ? "warning" : "soft"}>
                    {state === "running" ? "Ishlamoqda" : state === "completed" ? "Bajarildi" : "Navbatda"}
                  </Badge>
                  <Badge tone="soft">
                    <Sparkles size={11} className="mr-1" />
                    {agent.model}
                  </Badge>
                </div>
              </BaseCard>
            );
          })}
        </div>
      ) : null}

      {/* progress + event log while running */}
      {runInProgress ? (
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <Card>
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Umumiy progress</h3>
              <span className="ml-auto font-mono text-sm font-semibold text-foreground">{progress}%</span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-[color:var(--bg-strong)]">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <MiniStat label="Run state" value="running" />
              <MiniStat label="Bosqich" value={`agent${agents.filter((s) => s !== "pending").length}`} />
              <MiniStat label="Rejim" value="multi_agent" />
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-2">
              <Database size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Jonli event log</h3>
              <span className="ml-auto inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
            </div>
            <BaseCard tone="soft" className="mt-3 max-h-64 overflow-y-auto p-3 font-mono text-xs" padding="none">
              {DEMO_CHECKER_EVENTS.slice(0, visibleEvents)
                .slice()
                .reverse()
                .map((ev, idx) => (
                  <div key={idx} className="grid grid-cols-[minmax(0,1fr)] gap-1 py-1">
                    <span className={cn(ev.level === "error" && "text-[color:var(--error)]")}>
                      <span className="font-semibold text-primary">{ev.agent}:</span> {ev.message}
                    </span>
                  </div>
                ))}
            </BaseCard>
          </Card>
        </div>
      ) : null}

      {/* results */}
      {done ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard icon={<ShieldCheck size={16} />} label="Moslik" value={`${r.complianceScore}%`} />
            <StatCard icon={<Frame size={16} />} label="Figma" value={r.figma ? "Bor" : "Yo'q"} helper={`${r.figmaSignals} ta signal`} />
            <StatCard icon={<FileCode2 size={16} />} label="Diff" value={`+${r.additions} / -${r.deletions}`} />
            <StatCard icon={<Database size={16} />} label="Fayllar" value={String(r.filesChanged)} />
            <StatCard icon={<GitPullRequest size={16} />} label="PR" value={r.prLabel} />
          </section>

          <Card className="overflow-hidden">
            <div className="flex flex-col gap-5 md:flex-row md:items-center">
              <ComplianceRing score={r.complianceScore} size={104} />
              <div className="grid gap-3">
                <div className="flex flex-wrap gap-2">
                  <Badge tone="success">{r.verdict}</Badge>
                  <Badge tone="success">{r.completed} bajarildi</Badge>
                  <Badge tone="danger">{r.failed} bajarilmadi</Badge>
                </div>
                <h3 className="text-lg font-semibold text-foreground">{r.taskSummary}</h3>
                <ul className="grid gap-1.5">
                  {r.summaryLines.map((line, i) => (
                    <li key={i} className="text-sm leading-6 text-muted-foreground">
                      • {line}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>

          <Card padding="none" className="overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-border p-5 md:flex-row md:items-center md:justify-between">
              <div>
                <span className="qa-eyebrow inline-flex items-center gap-2">
                  <Waypoints size={13} /> Talablar matritsasi
                </span>
                <p className="mt-1 text-sm text-muted-foreground">
                  {reqs.length} talab · agent dalillari bilan
                </p>
              </div>
              <div className="inline-flex flex-wrap rounded-[12px] border border-border p-1">
                {([
                  ["all", `Talablar (${counts.all})`],
                  ["completed", `Bajarilgan (${counts.completed})`],
                  ["failed", `Bajarilmagan (${counts.failed})`],
                  ["skipped", `Skip (${counts.skipped})`],
                ] as [Filter, string][]).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFilter(key)}
                    className={cn(
                      "rounded-[9px] px-3 py-1.5 text-xs font-semibold transition-colors",
                      filter === key ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="divide-y divide-border">
              {filtered.map((req) => (
                <details key={req.id} className="group">
                  <summary className="grid cursor-pointer grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-3 px-5 py-3.5 list-none">
                    <ReqDot status={req.status} />
                    <span className="text-sm text-foreground">
                      <span className="mr-2 font-mono text-xs text-muted-foreground">{req.id}</span>
                      {req.requirement}
                    </span>
                    <span className="flex items-center gap-2">
                      <Badge tone={badgeTone(req.status)}>{STATUS_LABEL[req.status]}</Badge>
                      <ChevronLeft size={15} className="text-muted-foreground transition-transform group-open:-rotate-90" />
                    </span>
                  </summary>
                  <div className="grid gap-3 bg-[color:var(--bg-layer)] px-5 py-4 lg:grid-cols-2">
                    <BaseCard tone="soft" padding="none" className="p-3">
                      <p className="qa-tc-section-label">Agent dalili</p>
                      <p className="mt-1 text-sm leading-6 text-foreground">{req.evidence}</p>
                    </BaseCard>
                    <BaseCard tone="soft" padding="none" className="p-3">
                      <p className="qa-tc-section-label">Manba</p>
                      <div className="mt-1">
                        <Badge tone="soft">{req.source}</Badge>
                      </div>
                    </BaseCard>
                  </div>
                </details>
              ))}
            </div>
          </Card>

          {r.issues.length ? (
            <Card tone="warning">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-[color:var(--warning)]" />
                <h3 className="text-sm font-semibold text-foreground">Potensial muammolar</h3>
              </div>
              <ul className="mt-3 grid gap-2">
                {r.issues.map((issue, i) => (
                  <li key={i} className="qa-warning-item">⚠ {issue}</li>
                ))}
              </ul>
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function badgeTone(status: DemoRequirementStatus): "success" | "danger" | "warning" {
  return status === "completed" ? "success" : status === "failed" ? "danger" : "warning";
}

function ReqDot({ status }: { status: DemoRequirementStatus }) {
  const color =
    status === "completed" ? "var(--success)" : status === "failed" ? "var(--error)" : "var(--warning)";
  return <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />;
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <BaseCard tone="soft" padding="none" className="p-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold text-foreground">{value}</p>
    </BaseCard>
  );
}

function StatCard({
  icon,
  label,
  value,
  helper,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  helper?: string;
}) {
  return (
    <Card className="px-5 py-4">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">{label}</span>
        <span className="text-primary">{icon}</span>
      </div>
      <div className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{value}</div>
      {helper ? <p className="mt-1 text-sm text-muted-foreground">{helper}</p> : null}
    </Card>
  );
}
