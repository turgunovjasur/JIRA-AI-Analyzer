"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronLeft,
  Clock3,
  Copy,
  Database,
  FileCode2,
  Frame,
  GitPullRequest,
  Layers3,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  XCircle,
} from "lucide-react";

import { AnalysisStatusBannerView } from "@/components/analysis-status-banner";
import { PreflightChecksView } from "@/components/preflight-checks";
import { PRDetailsStack } from "@/components/pr-details-stack";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BaseCard, Card } from "@/components/ui/card";
import { ComplianceRing } from "@/components/ui/compliance-ring";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import { SettingsBaseCard } from "@/components/settings/base-card-system";
import {
  getOpenRunStorageKey,
  useRecentRuns,
  type RecentRun,
  type RecentRunScope,
} from "@/lib/use-recent-runs";
import { copyTextToClipboard } from "@/lib/clipboard";
import { cn } from "@/lib/cn";
import { getModuleRunErrorMessage, normalizeModuleRunErrorPayload } from "@/lib/module-errors";
import type {
  ModuleRunErrorPayload,
  ModuleStartStatus,
  TZPRAgentRunSnapshot,
  TZPRAnalysisResult,
  TZPRExecutionMode,
  TZPRExtraCodeChange,
  TZPRRequirementMatrixItem,
  TZPRRunEvent,
  TZPRRunSnapshot,
} from "@/lib/types";


type PipelineState = "pending" | "running" | "completed" | "failed";
type RequirementFilter = "all" | "completed" | "failed" | "skipped" | "extra";

const DEFAULT_EXECUTION_MODE: TZPRExecutionMode = "multi_agent";
const RUN_POLL_INTERVAL_MS = 2000;
const MODULE_KEY = "tz_pr_checker";

const FALLBACK_AGENTS: TZPRAgentRunSnapshot[] = [
  {
    agent_key: "agent1_scope_builder",
    agent_label: "Scope Builder",
    agent_order: 1,
    primary_model: "",
    state: "pending",
  },
  {
    agent_key: "agent2_verifier",
    agent_label: "Verifier",
    agent_order: 2,
    primary_model: "",
    state: "pending",
  },
  {
    agent_key: "agent3_arbiter",
    agent_label: "Arbiter",
    agent_order: 3,
    primary_model: "",
    state: "pending",
  },
];

function isTerminalRunState(value?: string | null) {
  return ["completed", "manual_review", "blocked", "failed"].includes((value || "").toLowerCase());
}

function isResolvedRunSnapshot(run?: TZPRRunSnapshot | null) {
  return Boolean(run && (isTerminalRunState(run.run_state) || run.finished_at || run.final_result));
}

function deriveResultError(result: TZPRAnalysisResult) {
  if (result.success) return null;
  if (result.status_banner) return null;
  return result.error_message || "TZ-PR tahlili muvaffaqiyatsiz tugadi.";
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

function getRunTone(value?: string | null): "soft" | "success" | "warning" | "danger" {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed") return "success";
  if (normalized === "manual_review" || normalized === "running" || normalized === "queued") return "warning";
  if (normalized === "blocked" || normalized === "failed") return "danger";
  return "soft";
}

function getAgentTone(value?: string | null): "soft" | "success" | "warning" | "danger" {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed") return "success";
  if (normalized === "running" || normalized === "pending") return "warning";
  if (normalized === "failed" || normalized === "blocked") return "danger";
  return "soft";
}

function normalizePipelineState(value?: string | null): PipelineState {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed" || normalized === "skipped") return "completed";
  if (normalized === "running") return "running";
  if (normalized === "failed" || normalized === "blocked") return "failed";
  return "pending";
}

function getVerdictLabel(result?: TZPRAnalysisResult | null) {
  return (
    result?.analysis_overview?.verdict_label
    || result?.qa_recommendation?.label
    || (result?.success ? "Natija tayyor" : "Xato")
  );
}

function getVerdictTone(result?: TZPRAnalysisResult | null): "success" | "warning" | "danger" | "soft" {
  if (!result?.success) return "danger";
  const verdict = (result.analysis_overview?.verdict || result.qa_recommendation?.action || "").toLowerCase();
  if (verdict === "pass") return "success";
  if (verdict === "fail" || verdict === "return" || verdict === "blocked") return "danger";
  if (verdict === "manual_review") return "warning";
  const score = result.compliance_score;
  if (score == null) return "soft";
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

function getRequirementCounts(result?: TZPRAnalysisResult | null) {
  const matrix = result?.requirement_matrix || [];
  const extra = getExtraItems(result);
  return {
    completed: matrix.filter((row) => (row.status || "").toLowerCase() === "completed").length,
    failed: matrix.filter((row) => (row.status || "").toLowerCase() === "failed").length,
    skipped: matrix.filter((row) => (row.status || "").toLowerCase() === "skipped").length,
    extra: extra.length,
    total: matrix.length,
  };
}

function parseRiskFromText(value: string) {
  const match = value.match(/\[risk:\s*([^\]]+)\]/i);
  return match?.[1]?.trim() || "";
}

function cleanExtraText(value: string) {
  return value
    .replace(/^[-\s]*Extra code change:\s*/i, "")
    .replace(/\s*\[risk:\s*[^\]]+\]\s*$/i, "")
    .trim();
}

function getExtraItems(result?: TZPRAnalysisResult | null): TZPRExtraCodeChange[] {
  const direct = (result?.arbiter_summary?.extra || []).filter((item) => item?.text?.trim());
  if (direct.length) return direct;

  const issues = (result?.analysis_sections || []).find((section) => section.key === "issues");
  const issueItems = (issues?.items?.length ? issues.items : issues?.lines) || [];
  return issueItems
    .filter((item) => /extra code change/i.test(item))
    .map((item) => ({
      text: cleanExtraText(item),
      risk: parseRiskFromText(item),
    }))
    .filter((item) => item.text);
}

function getExtraRiskTone(risk?: string | null): "soft" | "success" | "warning" | "danger" {
  const normalized = (risk || "").toLowerCase();
  if (normalized === "high") return "danger";
  if (normalized === "medium") return "warning";
  if (normalized === "low") return "soft";
  return "soft";
}

function getRequirementEvidence(row: TZPRRequirementMatrixItem) {
  const preferredSources = ["analysis", "code", "pr", "comment", "figma"];
  for (const source of preferredSources) {
    const match = (row.evidence || []).find(
      (item) => item.source === source && item.detail?.trim(),
    );
    if (match?.detail?.trim()) return match.detail.trim();
  }
  return row.notes?.trim() || "Dalil qaytmadi.";
}

function getCodeReferenceUrl(ref: { url?: string; lineStart?: number | null; lineEnd?: number | null }) {
  if (!ref.url) return "";
  if (!ref.lineStart) return ref.url;
  const end = ref.lineEnd && ref.lineEnd > ref.lineStart ? `-L${ref.lineEnd}` : "";
  return `${ref.url}#L${ref.lineStart}${end}`;
}

function getCodeReferenceLabel(ref: { filename: string; lineStart?: number | null; lineEnd?: number | null }) {
  if (!ref.lineStart) return ref.filename;
  const end = ref.lineEnd && ref.lineEnd > ref.lineStart ? `-L${ref.lineEnd}` : "";
  return `${ref.filename}:L${ref.lineStart}${end}`;
}

function getRequirementFiles(row: TZPRRequirementMatrixItem) {
  const refs = (row.code_refs || [])
    .map((ref) => ({
      filename: ref.filename?.trim() || "",
      lineEnd: ref.line_end || null,
      lineStart: ref.line_start || null,
      url: ref.blob_url?.trim() || "",
    }))
    .filter((ref) => ref.filename);
  if (refs.length) {
    return refs.filter(
      (ref, index, array) => array.findIndex((candidate) => candidate.filename === ref.filename) === index,
    );
  }

  return (row.code_files || [])
    .map((filename) => ({ filename: filename.trim(), lineEnd: null, lineStart: null, url: "" }))
    .filter((ref) => ref.filename);
}

function getRequirementFigmaSources(row: TZPRRequirementMatrixItem) {
  return (row.figma_sources || [])
    .map((source) => ({
      label: source.name?.trim() || source.file_key?.trim() || source.node_id?.trim() || "Figma",
      url: source.url?.trim() || "",
    }))
    .filter((source) => source.label);
}

function getRequirementSourceFallback(row: TZPRRequirementMatrixItem) {
  const relation = row.figma_relation?.trim() || "";
  if (!relation) return "Manba qaytmadi.";
  if (/^figma bo'yicha ishonchli xulosa yo'q\.?$/i.test(relation)) return "Manba qaytmadi.";
  if (/^figma summary mavjud/i.test(relation)) return "Manba qaytmadi.";
  return relation;
}

function normalizeRequirementText(value?: string | null) {
  return (value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function getRequirementOrigin(row: TZPRRequirementMatrixItem, result: TZPRAnalysisResult) {
  const direct = row.requirement_source?.trim();
  const matched = (result.requirement_inventory || []).find(
    (item) => normalizeRequirementText(item.text) === normalizeRequirementText(row.requirement),
  );
  const source = (direct || matched?.source || "").trim().toLowerCase();
  if (source === "tz") return "TZ";
  if (source === "comment") return "Comment";
  if (source === "figma") return "Figma";
  if (source === "mixed") return "Mixed";
  return source || "";
}

function getRequirementMergedFrom(row: TZPRRequirementMatrixItem, result: TZPRAnalysisResult) {
  const matched = (result.requirement_inventory || []).find(
    (item) => normalizeRequirementText(item.text) === normalizeRequirementText(row.requirement),
  );
  return (matched?.merged_from || []).map((text) => (text || "").trim()).filter(Boolean);
}

function getSummaryLines(result?: TZPRAnalysisResult | null) {
  const lines = result?.analysis_overview?.summary_lines || [];
  return lines.filter((line) => !/^compliance score:/i.test(line.trim()));
}

function getRunProgress(run?: TZPRRunSnapshot | null, result?: TZPRAnalysisResult | null) {
  if (result?.success || run?.final_result || run?.finished_at || run?.run_state === "completed") return 100;
  const agents = run?.agent_runs || [];
  if (!agents.length) return run?.run_state === "running" ? 18 : 0;
  const completed = agents.filter((agent) => normalizePipelineState(agent.state) === "completed").length;
  const running = agents.some((agent) => normalizePipelineState(agent.state) === "running");
  return Math.min(96, Math.round((completed / Math.max(agents.length, 1)) * 100) + (running ? 12 : 0));
}

function getPipelineAgents(run?: TZPRRunSnapshot | null, result?: TZPRAnalysisResult | null) {
  const actual = run?.agent_runs?.length ? run.agent_runs : result?.agent_runs || [];
  const agents = actual.length ? actual : FALLBACK_AGENTS;
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
  if (index === 0) return "TZ, comment va Figma'dan talablar";
  if (index === 1) return "Talablarni PR kodida tekshirish";
  if (index === 2) return "Yakuniy qaror va moslik bali";
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
    missing: num(metrics.missing_verification_count),
  };
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
    if (index === 0) return "TZ talablarga ajratilmoqda…";
    if (index === 1) return "Talablar PR kodida tekshirilmoqda…";
    if (index === 2) return "Yakuniy qaror chiqarilmoqda…";
    return "Bajarilmoqda…";
  }
  if (state === "failed") {
    return agent.error_text || agent.output_summary || "Xatolik bilan to'xtadi.";
  }
  if (state === "pending") {
    return "Navbatda — oldingi agent tugashini kutmoqda.";
  }
  return agent.output_summary || agent.input_summary || getAgentSubLabel(index);
}

function StatusDot({ state }: { state: PipelineState }) {
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

function AgentPipeline({
  result,
  run,
}: {
  result: TZPRAnalysisResult | null;
  run: TZPRRunSnapshot | null;
}) {
  const agents = getPipelineAgents(run, result).slice(0, 3);

  return (
    <BaseCard as="div" className="grid gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_32px_minmax(0,1fr)_32px_minmax(0,1fr)] lg:items-stretch" padding="none">
      {agents.map((agent, index) => {
        const state = normalizePipelineState(agent.state);
        const nextState = normalizePipelineState(agents[index + 1]?.state);
        const connectorDone = state === "completed";
        const connectorActive = state === "completed" && nextState === "running";

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
                    Agent {index + 1} · {getAgentShortLabel(agent, index)}
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
                      {metrics.fallback > 0 ? (
                        <Badge tone="warning">{metrics.fallback}× fallback</Badge>
                      ) : null}
                      {metrics.retry > 0 ? (
                        <Badge tone="soft">{metrics.retry} qayta urinish</Badge>
                      ) : null}
                      {metrics.technical > 0 ? (
                        <Badge tone="danger">{metrics.technical} texnik xato</Badge>
                      ) : null}
                    </>
                  );
                })()}
              </div>

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
                      <li key={warnIndex}>• {warning}</li>
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
            {event.agent_key ? <strong>{event.agent_key}: </strong> : null}
            {event.message || event.event_type || "Event tafsiloti qaytmadi."}
          </span>
        </div>
      )) : (
        <div className="px-4 py-4 text-muted-foreground">Eventlar hali qaytmadi.</div>
      )}
    </BaseCard>
  );
}

function RequirementMatrix({
  filter,
  onFilterChange,
  result,
}: {
  filter: RequirementFilter;
  onFilterChange: (filter: RequirementFilter) => void;
  result: TZPRAnalysisResult;
}) {
  const counts = getRequirementCounts(result);
  const extraItems = getExtraItems(result);
  const rows = (result.requirement_matrix || []).filter((row) => {
    if (filter === "extra") return false;
    if (filter === "all") return true;
    return (row.status || "").toLowerCase() === filter;
  });

  if (!counts.total && !counts.extra) return null;

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
            <Check size={15} />
            Talablar matritsasi
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {counts.total} talab bo'yicha yakuniy qaror{counts.extra ? `, ${counts.extra} extra item` : ""}
          </p>
        </div>
        <div className="inline-flex rounded-[12px] border border-border bg-[color:var(--bg-layer)] p-1">
          {[
            ["all", `Talablar (${counts.total})`],
            ["completed", `Bajarilgan (${counts.completed})`],
            ["failed", `Bajarilmagan (${counts.failed})`],
            ...(counts.skipped ? [["skipped", `Skip (${counts.skipped})`]] : []),
            ["extra", `Extra item (${counts.extra})`],
          ].map(([value, label]) => (
            <button
              className={cn(
                "rounded-[9px] px-3 py-1.5 text-xs font-semibold text-muted-foreground transition-colors",
                filter === value && "bg-card text-foreground shadow-sm",
              )}
              key={value}
              onClick={() => onFilterChange(value as RequirementFilter)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-border">
        {filter === "extra" ? (
          extraItems.length ? extraItems.map((item, index) => {
            const risk = (item.risk || "").trim();
            const files = (item.files || []).filter((file) => file.trim());
            return (
              <details className="group" key={`extra-${index}`}>
                <summary className="grid cursor-pointer list-none grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-3 px-5 py-4 transition-colors hover:bg-[color:var(--bg-layer)]">
                  <StatusDot state={risk.toLowerCase() === "high" ? "failed" : "running"} />
                  <span className="min-w-0 text-sm leading-6 text-foreground">
                    {item.text || "Extra item matni qaytmadi."}
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge tone={getExtraRiskTone(risk)}>{risk ? `Risk: ${risk}` : "Extra"}</Badge>
                    <ChevronLeft className="rotate-180 text-muted-foreground transition-transform group-open:rotate-90" size={14} />
                  </div>
                </summary>
                <div className="grid gap-3 border-t border-border bg-[color:var(--bg-layer)] px-5 py-4 lg:grid-cols-2">
                  <BaseCard as="div" className="px-4 py-3" padding="none">
                    <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Tavsif</div>
                    <p className="mt-2 text-sm leading-6 text-foreground">{item.text || "Extra item matni qaytmadi."}</p>
                  </BaseCard>
                  <BaseCard as="div" className="px-4 py-3" padding="none">
                    <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Manba</div>
                    <div className="mt-2 flex flex-wrap gap-2 text-sm leading-6 text-foreground">
                      {files.length ? files.map((file) => <span key={file}>{file}</span>) : (
                        <span>Agent2 extra scan</span>
                      )}
                    </div>
                  </BaseCard>
                </div>
              </details>
            );
          }) : (
            <div className="px-5 py-4 text-sm text-muted-foreground">Extra item topilmadi.</div>
          )
        ) : rows.map((row, index) => {
          const status = (row.status || "").toLowerCase();
          const isCompleted = status === "completed";
          const isSkipped = status === "skipped";
          const tone = isCompleted ? "success" : isSkipped ? "warning" : "danger";
          const dotState = isCompleted ? "completed" : isSkipped ? "running" : "failed";
          const files = getRequirementFiles(row);
          const figmaSources = getRequirementFigmaSources(row);
          const requirementOrigin = getRequirementOrigin(row, result);
          const mergedFrom = getRequirementMergedFrom(row, result);

          return (
            <details className="group" key={row.id || index}>
              <summary className="grid cursor-pointer list-none grid-cols-[18px_minmax(0,1fr)_auto] items-center gap-3 px-5 py-4 transition-colors hover:bg-[color:var(--bg-layer)]">
                <StatusDot state={dotState} />
                <span className="min-w-0 text-sm leading-6 text-foreground">
                  {row.requirement || "Talab matni qaytmadi."}
                </span>
                <div className="flex items-center gap-2">
                  <Badge tone={tone}>{row.status_label || (isCompleted ? "Bajarilgan" : isSkipped ? "Skip qilingan" : "Topilmadi")}</Badge>
                  <ChevronLeft className="rotate-180 text-muted-foreground transition-transform group-open:rotate-90" size={14} />
                </div>
              </summary>
              <div className="grid gap-3 border-t border-border bg-[color:var(--bg-layer)] px-5 py-4 lg:grid-cols-2">
                <BaseCard as="div" className="px-4 py-3" padding="none">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Agent dalili</div>
                  <p className="mt-2 text-sm leading-6 text-foreground">{getRequirementEvidence(row)}</p>
                </BaseCard>
                <BaseCard as="div" className="px-4 py-3" padding="none">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Manba</div>
                  <div className="mt-2 space-y-2 text-sm leading-6 text-foreground">
                    {requirementOrigin ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Talab</span>
                        <Badge tone="soft">{requirementOrigin}</Badge>
                      </div>
                    ) : null}
                    {files.length ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Kod dalili</span>
                        {files.map((file) => {
                          const href = getCodeReferenceUrl(file);
                          const label = getCodeReferenceLabel(file);
                          return href ? (
                            <a className="font-medium text-primary hover:underline" href={href} key={`${file.filename}-${file.lineStart || ""}`} rel="noreferrer" target="_blank">
                              {label}
                            </a>
                          ) : (
                            <span key={file.filename}>{label}</span>
                          );
                        })}
                      </div>
                    ) : null}
                    {figmaSources.length ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Figma</span>
                        {figmaSources.map((source) => (
                          source.url ? (
                            <a className="font-medium text-primary hover:underline" href={source.url} key={`${source.label}-${source.url}`} rel="noreferrer" target="_blank">
                              {source.label}
                            </a>
                          ) : (
                            <span key={source.label}>{source.label}</span>
                          )
                        ))}
                      </div>
                    ) : null}
                    {!requirementOrigin && !files.length && !figmaSources.length ? (
                      <span>{getRequirementSourceFallback(row)}</span>
                    ) : null}
                    {mergedFrom.length ? (
                      <div className="space-y-1">
                        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                          Birlashtirilgan talablar (debug)
                        </span>
                        <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                          {mergedFrom.map((text, mergeIndex) => (
                            <li key={`${row.id || index}-merge-${mergeIndex}`}>{text}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                </BaseCard>
              </div>
            </details>
          );
        })}
      </div>
    </Card>
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

type TZPRCheckerProps = {
  recentScope?: RecentRunScope;
};

export function TZPRChecker({ recentScope }: TZPRCheckerProps) {
  const [taskKey, setTaskKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moduleError, setModuleError] = useState<ModuleRunErrorPayload | null>(null);
  const [result, setResult] = useState<TZPRAnalysisResult | null>(null);
  const [activeRun, setActiveRun] = useState<TZPRRunSnapshot | null>(null);
  const { recent, addRecent, removeRecent } = useRecentRuns(MODULE_KEY, recentScope);
  const openRunStorageKey = getOpenRunStorageKey(MODULE_KEY, recentScope);
  const [requirementFilter, setRequirementFilter] = useState<RequirementFilter>("all");
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [startStatus, setStartStatus] = useState<ModuleStartStatus | null>(null);

  // Modul ochilganda (va har run'dan keyin) credential + Gemini kvota holatini olish.
  const refreshStartStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/tzpr/start-status", { cache: "no-store" });
      if (!res.ok) return;
      const data = (await res.json()) as ModuleStartStatus;
      if (data && typeof data === "object" && data.module_key) setStartStatus(data);
    } catch {
      /* status olinmasa gating ko'rsatilmaydi (backend baribir bloklaydi). */
    }
  }, []);

  useEffect(() => {
    void refreshStartStatus();
  }, [refreshStartStatus]);

  const resultHasAgentRunData = Boolean(
    result?.run_id
    || (result?.agent_runs || []).length
    || (result?.run_events || []).length,
  );
  const agentPanelRun: TZPRRunSnapshot | null = activeRun || (
    result && resultHasAgentRunData
      ? {
        run_id: result.run_id || "",
        task_key: result.task_key || taskKey.trim().toUpperCase(),
        execution_mode: result.execution_mode || DEFAULT_EXECUTION_MODE,
        run_state: result.run_state || undefined,
        active_phase: result.run_state ? "finished" : null,
        status_message: "Final resultdan olingan agent ma'lumotlari",
        requested_output_profile: "ui",
        final_result: result,
        error_message: result.error_message || null,
        created_at: null,
        updated_at: null,
        started_at: null,
        finished_at: null,
        agent_runs: result.agent_runs || [],
        run_events: result.run_events || [],
      }
      : null
  );
  const runInProgress = Boolean(activeRun?.run_id) && !isResolvedRunSnapshot(activeRun);
  const progress = getRunProgress(agentPanelRun, result);
  const counts = getRequirementCounts(result);
  const summaryLines = getSummaryLines(result);
  const figmaSummaries = result?.figma_data?.summaries || [];
  const showRunSignals = Boolean((result?.warnings || []).length || figmaSummaries.length);
  const runEvents = agentPanelRun?.run_events || result?.run_events || [];
  const canCopyDebug = Boolean(agentPanelRun || result || moduleError || error);

  useEffect(() => {
    const runId = activeRun?.run_id;
    if (!runId || isResolvedRunSnapshot(activeRun)) return undefined;

    let cancelled = false;
    const intervalId = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/tzpr/runs/${encodeURIComponent(runId)}`, {
          cache: "no-store",
        });
        const payload = (await response.json().catch(() => null)) as
          | (TZPRRunSnapshot & { error?: string })
          | null;

        if (!response.ok) {
          if (!cancelled) setError(payload?.error || "Checker run polling xatosi.");
          return;
        }
        if (!payload || cancelled) return;

        applyRunSnapshot(payload, {
          persistFinal: isResolvedRunSnapshot(payload) || isTerminalRunState(payload.run_state),
        });
      } catch (pollError) {
        if (!cancelled) {
          setError(
            pollError instanceof Error
              ? pollError.message
              : "Checker run polling vaqtida xato yuz berdi.",
          );
        }
      }
    }, RUN_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeRun?.run_id, activeRun?.run_state, activeRun?.finished_at, Boolean(activeRun?.final_result)]);

  useEffect(() => {
    setCopyState("idle");
  }, [agentPanelRun?.run_id, agentPanelRun?.updated_at, result?.task_key, moduleError?.error, error]);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(openRunStorageKey);
      if (!raw) return;
      window.sessionStorage.removeItem(openRunStorageKey);
      const entry = JSON.parse(raw) as RecentRun | null;
      if (entry?.run_id?.trim()) {
        void reopenRun(entry);
      }
    } catch {
      /* Historydan auto-open bo'lmasa, sahifa oddiy holatda qoladi. */
    }
  }, [openRunStorageKey]);

  function rememberRun(snapshot: TZPRRunSnapshot) {
    const runId = snapshot.run_id?.trim();
    const runTaskKey = (snapshot.task_key || snapshot.final_result?.task_key || taskKey).trim().toUpperCase();
    if (!runId || !runTaskKey) return;
    addRecent({
      run_id: runId,
      task_key: runTaskKey,
      saved_at: Date.now(),
      run_state: snapshot.run_state || snapshot.final_result?.run_state || undefined,
    });
  }

  function applyRunSnapshot(snapshot: TZPRRunSnapshot, options?: { persistFinal?: boolean }) {
    setModuleError(null);
    setActiveRun(snapshot);

    // Run yaratilishi/yangilanishi bilanoq recent ro'yxatga yoziladi (dedupe hook ichida).
    rememberRun(snapshot);

    const finalResult = snapshot.final_result || null;
    if (finalResult) {
      setResult(finalResult);
      setError(deriveResultError(finalResult));
      return;
    }

    if (options?.persistFinal && snapshot.error_message?.trim()) {
      setError(snapshot.error_message.trim());
      return;
    }

    if (snapshot.error_message?.trim()) {
      setError(snapshot.error_message.trim());
    }
  }

  async function reopenRun(entry: RecentRun) {
    if (submitting || runInProgress) return;
    setSubmitting(true);
    setError(null);
    setModuleError(null);
    setResult(null);
    setActiveRun(null);
    setRequirementFilter("all");
    setTaskKey(entry.task_key);

    try {
      const response = await fetch(`/api/tzpr/runs/${encodeURIComponent(entry.run_id)}`, {
        cache: "no-store",
      });
      const payload = (await response.json().catch(() => null)) as
        | (TZPRRunSnapshot & { error?: string })
        | null;
      if (!response.ok) {
        if (response.status === 403 || response.status === 404) {
          removeRecent(entry.run_id);
        }
        setError(payload?.error || "Eski runni yuklab bo'lmadi.");
        return;
      }
      if (!payload) {
        setError("Eski run uchun bo'sh javob qaytdi.");
        return;
      }
      // applyRunSnapshot activeRun'ni o'rnatadi → terminal bo'lmasa polling effekti davom etadi.
      applyRunSnapshot(payload, {
        persistFinal: isResolvedRunSnapshot(payload) || isTerminalRunState(payload.run_state),
      });
    } catch (reopenError) {
      setError(
        reopenError instanceof Error
          ? reopenError.message
          : "Eski runni yuklashda xato yuz berdi.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function copyDebugJson() {
    const debugPayload = agentPanelRun || result || moduleError || (
      error
        ? {
          copied_at: new Date().toISOString(),
          error,
          module_key: "tz_pr_checker",
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

  async function startRun() {
    const normalizedTaskKey = taskKey.trim().toUpperCase();
    setSubmitting(true);
    setError(null);
    setModuleError(null);
    setResult(null);
    setActiveRun(null);
    setRequirementFilter("all");

    try {
      const response = await fetch("/api/tzpr/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_key: normalizedTaskKey,
          max_files: null,
          output_profile: "ui",
          show_full_diff: true,
          use_smart_patch: null,
        }),
      });
      const payload = (await response.json().catch(() => null)) as
        | (TZPRRunSnapshot & { error?: string })
        | null;

      if (!response.ok) {
        const normalizedError = normalizeModuleRunErrorPayload(payload, {
          moduleKey: "tz_pr_checker",
          taskKey: normalizedTaskKey,
          message: "TZ-PR multi-agent run yaratib bo'lmadi.",
        });
        setModuleError(normalizedError);
        setError(
          normalizedError.status_banner
            ? null
            : getModuleRunErrorMessage(normalizedError, "TZ-PR multi-agent run yaratib bo'lmadi."),
        );
        return;
      }
      if (!payload) {
        setError("Backend multi-agent run uchun bo'sh javob qaytardi.");
        return;
      }

      applyRunSnapshot(payload, {
        persistFinal: isResolvedRunSnapshot(payload) || isTerminalRunState(payload.run_state),
      });
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Backend bilan ulanishda xato yuz berdi.",
      );
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

  function resetView() {
    if (agentPanelRun) {
      rememberRun(agentPanelRun);
    }
    setResult(null);
    setActiveRun(null);
    setModuleError(null);
    setError(null);
    setRequirementFilter("all");
    setCopyState("idle");
  }

  const pageTitle = result?.task_key || agentPanelRun?.task_key || "Multi-agent Checker";
  const pageSubtitle = runInProgress
    ? `${progress}% · ${agentPanelRun?.status_message || "Agentlar ishlamoqda"}`
    : result?.success
      ? "3 agent yakuniy natijasi"
      : "JIRA task va GitHub PR mosligini AI agentlar orqali tekshiring.";
  const prSelection = result?.pr_selection || null;
  const prFoundCount = prSelection?.found_count ?? result?.pr_details?.length ?? result?.pr_count ?? 0;
  const prMergedCount = prSelection?.merged_count ?? result?.pr_count ?? result?.pr_details?.length ?? 0;
  const prSkippedCount = prSelection?.skipped_count ?? 0;
  const showRunCard = !submitting && !agentPanelRun && !result;

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            <ShieldCheck size={14} />
            TZ-PR Checker
          </div>
          <h1 className="mt-2 flex flex-wrap items-center gap-3 text-2xl font-semibold tracking-tight text-foreground">
            <span className="min-w-0 break-words">{pageTitle}</span>
            {result ? <Badge tone={getVerdictTone(result)}>{getVerdictLabel(result)}</Badge> : null}
            {runInProgress ? <Badge tone="warning"><StatusDot state="running" /> Jonli</Badge> : null}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{pageSubtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild size="sm" type="button" variant="ghost">
            <Link href="/tzpr/history">
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
              <h2 className="mt-4 text-lg font-semibold text-foreground">Tahlilni boshlash</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Multi-agent run ochiladi va har bir bosqich holati jonli ko'rinadi.
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
                    Tekshirilmoqda...
                  </>
                ) : (
                  <>
                    <Play size={15} fill="currentColor" />
                    Boshlash
                  </>
                )}
              </Button>
            </div>
          </Card>
        </section>
      ) : null}

      {agentPanelRun ? (
        <div className="grid gap-4">
          <AgentPipeline result={result} run={agentPanelRun} />

          {runInProgress ? (
            <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
              <Card>
                <div className="flex items-center justify-between gap-3">
                  <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
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
                  <StatusDot state="running" />
                </div>
                <EventLog events={runEvents} />
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {result?.success ? (
        <div className="grid gap-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard
              helper="Checker chiqargan umumiy moslik foizi"
              icon={<ShieldCheck size={18} />}
              label="Moslik"
              value={result.compliance_score != null ? `${result.compliance_score}%` : "N/A"}
            />
            <StatCard
              helper={`${figmaSummaries.length || result.figma_data?.count || 0} ta signal`}
              icon={<Frame size={18} />}
              label="Figma"
              value={figmaSummaries.length || result.figma_data?.count ? "Bor" : "Yo'q"}
            />
            <StatCard
              helper="Qo'shilgan / o'chirilgan qatorlar"
              icon={<FileCode2 size={18} />}
              label="Diff"
              value={`+${result.total_additions || 0} / -${result.total_deletions || 0}`}
            />
            <StatCard
              helper="Ko'rilgan o'zgargan fayllar"
              icon={<Database size={18} />}
              label="Fayllar"
              value={result.files_changed || result.files_analyzed || 0}
            />
            <StatCard
              helper={prSelection ? `${prSkippedCount} ta PR skip qilingan` : "Task bilan bog'langan PR soni"}
              icon={<GitPullRequest size={18} />}
              label="PR"
              value={prSelection ? `${prMergedCount}/${prFoundCount}` : result.pr_count || result.pr_details?.length || 0}
            />
          </div>

          <Card className="overflow-hidden">
            <div className="flex flex-col gap-5 md:flex-row md:items-center">
              <div className="relative h-[104px] w-[104px] shrink-0">
                {result.compliance_score != null ? (
                  <ComplianceRing score={result.compliance_score} size={104} />
                ) : null}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={getVerdictTone(result)}>{getVerdictLabel(result)}</Badge>
                  <Badge tone="soft">{counts.completed} bajarildi</Badge>
                  {counts.failed ? <Badge tone="danger">{counts.failed} bajarilmadi</Badge> : null}
                  {result.ai_retry_count ? <Badge tone="warning">{result.ai_retry_count} retry</Badge> : null}
                </div>
                <h2 className="mt-3 text-xl font-semibold leading-tight text-foreground">
                  {result.task_summary || result.task_info?.summary || "Task summary mavjud emas."}
                </h2>
                <div className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
                  {summaryLines.length ? summaryLines.slice(0, 3).map((line, index) => (
                    <p key={`${result.task_key}-summary-${index}`}>{line}</p>
                  )) : (
                    <p>{result.analysis_overview?.verdict_reason || result.qa_recommendation?.reason || "Yakuniy AI xulosasi qaytmadi."}</p>
                  )}
                </div>
              </div>
            </div>
          </Card>

          <RequirementMatrix filter={requirementFilter} onFilterChange={setRequirementFilter} result={result} />

          {showRunSignals ? (
            <Card>
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                <AlertTriangle size={15} />
                Run signallari
              </div>
              <div className="mt-4 grid gap-3">
                {(result.warnings || []).map((warning, index) => (
                  <div className="qa-warning-item" key={index}>⚠ {warning}</div>
                ))}
                {figmaSummaries.length ? figmaSummaries.map((item, index) => (
                  <BaseCard
                    as="div"
                    className="px-4 py-3"
                    key={`${item.file_key || item.name || "figma"}-${index}`}
                    padding="none"
                    tone="soft"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <strong className="text-sm font-semibold text-foreground">{item.name || item.file_key || "Figma file"}</strong>
                      {item.url ? (
                        <a className="text-xs font-medium text-primary hover:underline" href={item.url} rel="noreferrer" target="_blank">
                          Ochish
                        </a>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.summary || "Summary topilmadi."}</p>
                  </BaseCard>
                )) : null}
              </div>
            </Card>
          ) : null}

          <PRDetailsStack prDetails={result.pr_details || []} prSelection={prSelection} />
        </div>
      ) : result ? (
        <Card>
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-[color:var(--error)] text-white">
              <AlertTriangle size={18} />
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-foreground">TZ-PR tahlili tugamadi</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {result.error_message || "Xatolik tafsiloti qaytmadi."}
              </p>
            </div>
          </div>
          {(result.warnings || []).length ? (
            <div className="mt-4 grid gap-2">
              {(result.warnings || []).map((warning, index) => (
                <div className="qa-warning-item" key={index}>⚠ {warning}</div>
              ))}
            </div>
          ) : null}
          {result.tz_content ? (
            <BaseCard as="details" className="mt-4 overflow-hidden" padding="none" tone="soft">
              <summary className="cursor-pointer px-4 py-4 text-sm font-semibold text-foreground">TZ content</summary>
              <div className="border-t border-border px-4 py-4">
                <div className="qa-analysis-block">{result.tz_content}</div>
              </div>
            </BaseCard>
          ) : null}
          <div className="mt-4">
            <Button onClick={() => void startRun()} size="sm" type="button">
              <RefreshCw size={14} />
              Qayta urinish
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
