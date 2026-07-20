"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Check,
  ClipboardList,
  Database,
  FileCode2,
  Layers3,
  ListChecks,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { BaseCard, Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/cn";
import {
  DEMO_TASK_KEY,
  DEMO_TESTCASE_AGENTS,
  DEMO_TESTCASE_EVENTS,
  DEMO_TESTCASE_RESULT,
  type DemoTestCase,
} from "@/lib/demo-data";

type Phase = "idle" | "running" | "done";
type AgentState = "pending" | "running" | "completed";

export function DemoTestcase() {
  const [taskKey, setTaskKey] = useState(DEMO_TASK_KEY);
  const [context, setContext] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [agents, setAgents] = useState<AgentState[]>(["pending", "pending", "pending"]);
  const [progress, setProgress] = useState(0);
  const [visibleEvents, setVisibleEvents] = useState(0);
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
  }

  function run() {
    clearTimers();
    setPhase("running");
    setAgents(["running", "pending", "pending"]);
    setProgress(18);
    setVisibleEvents(2);
    at(1200, () => {
      setAgents(["completed", "running", "pending"]);
      setProgress(50);
      setVisibleEvents(4);
    });
    at(2500, () => {
      setAgents(["completed", "completed", "running"]);
      setProgress(80);
      setVisibleEvents(5);
    });
    at(3800, () => {
      setAgents(["completed", "completed", "completed"]);
      setProgress(100);
      setVisibleEvents(6);
    });
    at(4500, () => setPhase("done"));
  }

  const r = DEMO_TESTCASE_RESULT;
  const runInProgress = phase === "running";
  const done = phase === "done";
  const coveredReqs = Array.from(new Set(r.testCases.flatMap((tc) => tc.requirementIds))).sort();

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="qa-eyebrow inline-flex items-center gap-2">
            <ClipboardList size={14} /> Test Case Generator
          </span>
          <h2 className="qa-page-heading">Multi-agent test case yaratish</h2>
          <p className="qa-page-desc">
            {runInProgress
              ? `${progress}% · Agentlar ishlamoqda`
              : "Talablar asosida test case: Agent1 (talablar) → Agent2 (yozish) → Agent3 (audit)."}
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
            <h3 className="text-xl font-semibold text-foreground">Testcase generatsiyani boshlash</h3>
            <p className="max-w-md text-sm text-muted-foreground">
              JIRA task kalitini kiriting — Agent1/2/3 talablarni ajratib, test case yozadi va audit qiladi.
            </p>
          </div>
          <Field label="JIRA Task Key">
            <Input
              className="font-mono text-base"
              value={taskKey}
              onChange={(e) => setTaskKey(e.target.value.toUpperCase())}
              placeholder="1234 yoki DEV-1234"
            />
          </Field>
          <div className="rounded-[12px] border border-border bg-[color:var(--bg-layer)] p-4">
            <Field label="Qo'shimcha buyruq (ixtiyoriy)">
              <Textarea
                rows={4}
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Masalan: narx chegaralari, mahsulot xususiyatlari, alohida holatlar..."
              />
            </Field>
          </div>
          <Button type="submit" fullWidth>
            <Play size={16} fill="currentColor" /> Generate
          </Button>
          <p className="text-center text-xs text-muted-foreground">
            Demo: natija oldindan tayyorlangan namuna ({DEMO_TASK_KEY}).
          </p>
        </Card>
      ) : null}

      {phase !== "idle" ? (
        <div className="grid gap-3 md:grid-cols-3">
          {DEMO_TESTCASE_AGENTS.map((agent, i) => {
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

      {runInProgress ? (
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <Card>
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Umumiy progress</h3>
              <span className="ml-auto font-mono text-sm font-semibold text-foreground">{progress}%</span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-[color:var(--bg-strong)]">
              <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-2">
              <Database size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Jonli event log</h3>
              <span className="ml-auto inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
            </div>
            <BaseCard tone="soft" className="mt-3 max-h-56 overflow-y-auto p-3 font-mono text-xs" padding="none">
              {DEMO_TESTCASE_EVENTS.slice(0, visibleEvents)
                .slice()
                .reverse()
                .map((ev, idx) => (
                  <div key={idx} className="py-1">
                    <span className="font-semibold text-primary">{ev.agent}:</span> {ev.message}
                  </div>
                ))}
            </BaseCard>
          </Card>
        </div>
      ) : null}

      {done ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard icon={<ClipboardList size={16} />} label="Test Cases" value={String(r.totalTestCases)} />
            <StatCard icon={<Layers3 size={16} />} label="Talablar" value={String(r.totalRequirements)} />
            <StatCard icon={<ShieldCheck size={16} />} label="Qoplangan" value={`${r.covered}/${r.totalRequirements}`} />
            <StatCard icon={<FileCode2 size={16} />} label="High priority" value={String(r.highPriority)} />
          </section>

          <Card padding="none" className="overflow-hidden">
            <div className="flex items-center gap-2 border-b border-border p-5">
              <ListChecks size={16} className="text-primary" />
              <h3 className="text-sm font-semibold text-foreground">Talablar qamrovi</h3>
              <Badge tone="success" className="ml-auto">{r.covered}/{r.totalRequirements} qoplangan</Badge>
            </div>
            <div className="flex flex-wrap gap-2 p-5">
              {coveredReqs.map((id) => (
                <Badge key={id} tone="success">
                  <Check size={12} className="mr-1" /> {id}
                </Badge>
              ))}
            </div>
          </Card>

          <div className="grid gap-3">
            <div className="flex items-center gap-2">
              <span className="qa-eyebrow">Yaratilgan test case&apos;lar</span>
              <Badge>{r.testCases.length} ta</Badge>
            </div>
            {r.testCases.map((tc) => (
              <TestCaseCard key={tc.id} tc={tc} />
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function TestCaseCard({ tc }: { tc: DemoTestCase }) {
  const priorityTone = tc.priority === "High" ? "danger" : tc.priority === "Medium" ? "warning" : "soft";
  return (
    <BaseCard as="details" className="qa-tc-card" padding="none">
      <summary>
        <span className="qa-tc-id">{tc.id}</span>
        <span className="flex-1 text-sm font-semibold text-foreground">{tc.title}</span>
        <Badge tone={priorityTone}>{tc.priority}</Badge>
        <Badge tone="soft">{tc.type}</Badge>
      </summary>
      <div className="qa-tc-body">
        <div>
          <p className="qa-tc-section-label">Tavsif</p>
          <p className="text-sm leading-6 text-foreground">{tc.description}</p>
        </div>
        <div>
          <p className="qa-tc-section-label">Dastlabki shartlar</p>
          <p className="text-sm leading-6 text-muted-foreground">{tc.preconditions}</p>
        </div>
        <div>
          <p className="qa-tc-section-label">Qadamlar</p>
          <ol className="qa-tc-steps">
            {tc.steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </div>
        <div>
          <p className="qa-tc-section-label">Kutilgan natija</p>
          <div className="qa-tc-expected">{tc.expected}</div>
        </div>
        <div>
          <p className="qa-tc-section-label">Qoplagan talablar</p>
          <div className="qa-tag-row">
            {tc.requirementIds.map((id) => (
              <Badge key={id} tone="success">{id}</Badge>
            ))}
          </div>
        </div>
      </div>
    </BaseCard>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Card className="px-5 py-4">
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">{label}</span>
        <span className="text-primary">{icon}</span>
      </div>
      <div className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{value}</div>
    </Card>
  );
}
