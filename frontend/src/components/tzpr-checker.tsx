"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  AlertTriangle,
  ClipboardList,
  FileCode2,
  GitPullRequest,
  Radar,
  ScanSearch,
} from "lucide-react";

import { ComplianceRing } from "@/components/ui/compliance-ring";
import { PRDetailsStack } from "@/components/pr-details-stack";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import { StatusPill } from "@/components/ui/status-pill";
import { AnalysisStatusBannerView } from "@/components/analysis-status-banner";
import { BaseInputField, SettingsBaseCard } from "@/components/settings/base-card-system";
import type {
  TZPRAnalysisOverview,
  TZPRAnalysisResult,
  TZPRAnalysisSection,
} from "@/lib/types";

const SETTINGS_INPUT_CLASS = "settings-form-input";
const CHECKER_TABS = [
  { key: "overview", label: "Overview" },
  { key: "requirements", label: "Requirement Map" },
  { key: "evidence", label: "Evidence" },
  { key: "raw", label: "Raw AI" },
] as const;

type CheckerTabKey = (typeof CHECKER_TABS)[number]["key"];

function formatCompactNumber(value?: number | null) {
  if (value == null) return "0";
  if (value >= 1000) {
    return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`;
  }
  return String(value);
}

function verdictTone(verdict?: string | null): "good" | "warn" | "bad" | "muted" {
  switch ((verdict || "").toLowerCase()) {
    case "pass":
      return "good";
    case "partial":
      return "warn";
    case "fail":
    case "blocked":
      return "bad";
    default:
      return "muted";
  }
}

function sectionTone(sectionKey: string): "good" | "warn" | "bad" | "info" | "muted" {
  if (sectionKey === "completed") return "good";
  if (sectionKey === "partial" || sectionKey === "issues") return "warn";
  if (sectionKey === "failed") return "bad";
  if (sectionKey === "figma") return "info";
  return "muted";
}

function sectionIcon(sectionKey: string) {
  if (sectionKey === "completed") return "Completed";
  if (sectionKey === "partial") return "Partial";
  if (sectionKey === "failed") return "Missing";
  if (sectionKey === "issues") return "Risks";
  if (sectionKey === "figma") return "Figma";
  return "Section";
}

function cleanItems(section: TZPRAnalysisSection) {
  if (section.items?.length) return section.items;
  return (section.lines || []).filter((line) => line.trim().length > 0);
}

function fallbackOverview(result: TZPRAnalysisResult): TZPRAnalysisOverview {
  const score = result.compliance_score ?? null;
  const verdict = score == null ? "unknown" : score >= 80 ? "pass" : score >= 60 ? "partial" : "fail";
  const label = verdict === "pass" ? "Ready" : verdict === "partial" ? "Review" : verdict === "fail" ? "Need Work" : "Unknown";
  return {
    verdict,
    verdict_label: label,
    verdict_reason: result.error_message || "AI tahlili uchun fallback overview.",
    summary_lines: score == null ? ["Compliance score qaytmadi."] : [`Compliance score: ${score}%`],
    section_counts: {},
    missing_figma_access: !(result.figma_data?.summaries || []).length,
    requested_sections: [],
  };
}

function coverageCount(overview: TZPRAnalysisOverview | null | undefined, key: string) {
  return overview?.section_counts?.[key] ?? 0;
}

function renderSectionCard(section: TZPRAnalysisSection) {
  const items = cleanItems(section);
  const tone = sectionTone(section.key);

  return (
    <Card key={section.key} className="flex h-full flex-col gap-4 p-5" tone="soft">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
            {sectionIcon(section.key)}
          </p>
          <h3 className="mt-2 text-base font-semibold text-foreground">{section.title}</h3>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill tone={tone} value={section.key.toUpperCase()} />
          <Badge tone="soft">{items.length} item</Badge>
        </div>
      </div>

      {items.length ? (
        <div className="grid gap-3">
          {items.map((item, index) => (
            <div
              key={`${section.key}-${index}`}
              className="rounded-[16px] border border-border bg-card px-4 py-3 text-sm leading-6 text-foreground"
            >
              {item}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-muted-foreground">
          Bu bo&apos;lim uchun AI aniq signal qaytarmadi.
        </p>
      )}
    </Card>
  );
}

export function TZPRChecker() {
  const [taskKey, setTaskKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TZPRAnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState<CheckerTabKey>("overview");

  useEffect(() => {
    setActiveTab("overview");
  }, [result?.task_key]);

  const overview = result?.analysis_overview ?? (result ? fallbackOverview(result) : null);
  const requirementSections = useMemo(
    () => (result?.analysis_sections || []).filter((section) => section.key !== "summary" && section.key !== "score"),
    [result?.analysis_sections],
  );

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

    try {
      const response = await fetch("/api/tzpr/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_key: normalizedTaskKey,
          max_files: null,
          output_profile: "ui",
          show_full_diff: true,
        }),
      });

      const payload = (await response.json().catch(() => null)) as
        | (TZPRAnalysisResult & { error?: string })
        | null;

      if (!response.ok) {
        setError(payload?.error || "TZ-PR analyze request xatosi.");
        return;
      }
      if (!payload) {
        setError("Backend bo'sh javob qaytardi.");
        return;
      }

      setResult(payload);
      if (!payload.success) {
        setError(
          payload.status_banner
            ? null
            : (payload.error_message || "TZ-PR tahlili muvaffaqiyatsiz tugadi."),
        );
      }
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Backend bilan ulanishda xato yuz berdi.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <SettingsBaseCard
        header={(
          <SectionHeader
            action={<Badge tone="soft">Smart patch: setting bo&apos;yicha</Badge>}
            eyebrow="Analyze"
            title="Task yuborish"
          />
        )}
        showCustomizer={false}
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
              {submitting ? "Tekshirilmoqda..." : "Tekshirish"}
            </Button>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">
            Interaktiv checker to&apos;liq verdict, requirement map va evidence bilan ishlaydi.
          </p>
        </form>
      </SettingsBaseCard>

      {error ? <Notice tone="error">{error}</Notice> : null}
      {result?.status_banner ? <AnalysisStatusBannerView banner={result.status_banner} /> : null}

      {result?.success ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              helper="AI chiqarilgan moslik bali"
              label="Compliance"
              value={result.compliance_score != null ? `${result.compliance_score}%` : "N/A"}
            />
            <MetricCard
              helper="Checker verdict"
              label="Verdict"
              value={overview?.verdict_label || "Unknown"}
            />
            <MetricCard
              helper="Ko'rilgan o'zgargan fayllar"
              label="Files"
              value={result.files_analyzed || result.files_changed || 0}
            />
            <MetricCard
              helper="Gemini prompt hajmi"
              label="Prompt"
              value={`${formatCompactNumber(result.total_prompt_size)} chars`}
            />
          </section>

          <section className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(300px,0.7fr)]">
            <SettingsBaseCard
              className="qa-compliance-card"
              header={<SectionHeader eyebrow="Decision" title={result.task_key || "Task"} />}
              showCustomizer={false}
            >
              {result.compliance_score != null ? <ComplianceRing score={result.compliance_score} /> : null}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill tone={verdictTone(overview?.verdict)} value={overview?.verdict_label || "Unknown"} />
                  <Badge tone="soft">
                    <GitPullRequest size={11} className="mr-1" />
                    {result.pr_count || 0} PR
                  </Badge>
                  <Badge tone="soft">
                    <FileCode2 size={11} className="mr-1" />
                    {result.files_analyzed || 0} fayl
                  </Badge>
                  {overview?.missing_figma_access ? <Badge tone="warning">Figma limited</Badge> : <Badge tone="soft">Figma ready</Badge>}
                </div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  {result.task_summary || "Task summary mavjud emas."}
                </p>
                <p className="mt-3 text-sm font-medium leading-6 text-foreground">
                  {overview?.verdict_reason || "Verdict reason mavjud emas."}
                </p>
                <div className="mt-4 grid gap-3">
                  {(overview?.summary_lines || []).map((line, index) => (
                    <div
                      key={`summary-${index}`}
                      className="rounded-[14px] border border-border bg-[color:var(--bg-layer)] px-4 py-3 text-sm leading-6 text-foreground"
                    >
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            </SettingsBaseCard>

            <Card className="grid gap-5 p-6" tone="accent">
              <div>
                <div className="inline-flex rounded-full bg-primary/10 p-2 text-primary">
                  <Radar size={16} />
                </div>
                <h3 className="mt-4 text-base font-bold text-foreground">Coverage va diagnostika</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Requirement sectionlari, prompt cleanliness va run signallari shu blokda jamlangan.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[16px] border border-border bg-card px-4 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Coverage</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge tone="soft">Completed: {coverageCount(overview, "completed")}</Badge>
                    <Badge tone="soft">Partial: {coverageCount(overview, "partial")}</Badge>
                    <Badge tone="soft">Missing: {coverageCount(overview, "failed")}</Badge>
                    <Badge tone="soft">Risks: {coverageCount(overview, "issues")}</Badge>
                  </div>
                </div>
                <div className="rounded-[16px] border border-border bg-card px-4 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Comments</div>
                  <div className="mt-2 grid gap-1 text-sm text-muted-foreground">
                    <span>Human comments: {Number(result.comment_analysis?.total_comments || 0)}</span>
                    <span>Filtered AI comments: {Number(result.comment_analysis?.filtered_out_ai_comments || 0)}</span>
                    <span>Dev objections: {(result.dev_objections || []).length}</span>
                  </div>
                </div>
                <div className="rounded-[16px] border border-border bg-card px-4 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Prompt</div>
                  <div className="mt-2 grid gap-1 text-sm text-muted-foreground">
                    <span>Chars: {result.total_prompt_size || 0}</span>
                    <span>Retry: {result.ai_retry_count || 0}</span>
                    <span>Sections: {(overview?.requested_sections || []).join(", ") || "N/A"}</span>
                  </div>
                </div>
                <div className="rounded-[16px] border border-border bg-card px-4 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Warnings</div>
                  <div className="mt-2 grid gap-1 text-sm text-muted-foreground">
                    <span>Run warnings: {(result.warnings || []).length}</span>
                    <span>Comment signal: {String(result.comment_analysis?.summary || "Yo'q")}</span>
                  </div>
                </div>
              </div>
            </Card>
          </section>

          {(result.warnings || []).length ? (
            <SettingsBaseCard
              header={<SectionHeader eyebrow="Warnings" title={`${result.warnings?.length || 0} ogohlantirish`} />}
              showCustomizer={false}
            >
              <div className="mt-4 grid gap-2">
                {(result.warnings || []).map((warning, index) => (
                  <div key={index} className="qa-warning-item">⚠ {warning}</div>
                ))}
              </div>
            </SettingsBaseCard>
          ) : null}

          <SettingsBaseCard
            header={<SectionHeader eyebrow="Analysis View" title="Checker cockpit" />}
            showCustomizer={false}
          >
            <div className="tabs mt-4">
              {CHECKER_TABS.map((tab) => (
                <button
                  key={tab.key}
                  className={`tab-btn ${activeTab === tab.key ? "active" : ""}`}
                  onClick={() => setActiveTab(tab.key)}
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === "overview" ? (
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <Card className="grid gap-4 p-5" tone="soft">
                  <div className="inline-flex rounded-full bg-primary/10 p-2 text-primary">
                    <ClipboardList size={16} />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-foreground">Executive summary</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      Task verdicti va eng muhim signal qisqacha ko&apos;rinishi.
                    </p>
                  </div>
                  <div className="grid gap-3">
                    {(overview?.summary_lines || []).map((line, index) => (
                      <div key={`overview-line-${index}`} className="rounded-[16px] border border-border bg-card px-4 py-3 text-sm leading-6 text-foreground">
                        {line}
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="grid gap-4 p-5" tone="soft">
                  <div className="inline-flex rounded-full bg-primary/10 p-2 text-primary">
                    <AlertTriangle size={16} />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-foreground">Open signals</h3>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      Requirement va analysis qatlamida qolgan eng muhim ochiq nuqtalar.
                    </p>
                  </div>
                  <div className="grid gap-3">
                    <div className="rounded-[16px] border border-border bg-card px-4 py-3 text-sm leading-6 text-muted-foreground">
                      Missing talablar: {coverageCount(overview, "failed")}
                    </div>
                    <div className="rounded-[16px] border border-border bg-card px-4 py-3 text-sm leading-6 text-muted-foreground">
                      Partial talablar: {coverageCount(overview, "partial")}
                    </div>
                    <div className="rounded-[16px] border border-border bg-card px-4 py-3 text-sm leading-6 text-muted-foreground">
                      Risklar: {coverageCount(overview, "issues")}
                    </div>
                    <div className="rounded-[16px] border border-border bg-card px-4 py-3 text-sm leading-6 text-muted-foreground">
                      Figma access: {overview?.missing_figma_access ? "Cheklangan" : "Mavjud"}
                    </div>
                  </div>
                </Card>
              </div>
            ) : null}

            {activeTab === "requirements" ? (
              <div className="mt-5 grid gap-4 xl:grid-cols-2">
                {requirementSections.length ? requirementSections.map(renderSectionCard) : (
                  <div className="rounded-[18px] border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
                    Structured requirement sectionlar qaytmadi.
                  </div>
                )}
              </div>
            ) : null}

            {activeTab === "evidence" ? (
              <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                <div className="grid gap-4">
                  <Card className="grid gap-4 p-5" tone="soft">
                    <div className="flex items-center gap-3">
                      <ScanSearch size={16} className="text-primary" />
                      <h3 className="text-base font-semibold text-foreground">TZ va comment evidence</h3>
                    </div>
                    <div className="grid gap-2 text-sm text-muted-foreground">
                      <span>{String(result.comment_analysis?.summary || "Comment signal yo'q")}</span>
                      <span>Filtered AI comments: {Number(result.comment_analysis?.filtered_out_ai_comments || 0)}</span>
                    </div>
                    <details className="rounded-[16px] border border-border bg-card px-4 py-4">
                      <summary className="cursor-pointer list-none text-sm font-semibold text-foreground">TZ contentni ko&apos;rish</summary>
                      <div className="qa-analysis-block mt-4">{result.tz_content || "TZ content topilmadi."}</div>
                    </details>
                  </Card>

                  <Card className="grid gap-4 p-5" tone="soft">
                    <div className="flex items-center gap-3">
                      <Radar size={16} className="text-primary" />
                      <h3 className="text-base font-semibold text-foreground">Figma evidence</h3>
                    </div>
                    {result.figma_data?.summaries?.length ? (
                      <div className="grid gap-3">
                        {result.figma_data.summaries.map((item, index) => (
                          <div key={index} className="rounded-[16px] border border-border bg-card px-4 py-4">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <strong className="text-sm font-semibold text-foreground">{item.name || item.file_key || "Figma file"}</strong>
                                <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.summary || "Summary topilmadi."}</p>
                              </div>
                              {item.url ? (
                                <a className="text-xs font-medium text-primary hover:underline" href={item.url} rel="noreferrer" target="_blank">
                                  Ochish
                                </a>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm leading-6 text-muted-foreground">
                        Figma evidence mavjud emas yoki access bo&apos;lmagan.
                      </p>
                    )}
                  </Card>
                </div>

                <SettingsBaseCard
                  header={(
                    <SectionHeader
                      action={<Badge tone="soft">{result.pr_details?.length || 0} PR</Badge>}
                      eyebrow="GitHub"
                      title="PR tafsilotlari"
                    />
                  )}
                  showCustomizer={false}
                >
                  <PRDetailsStack prDetails={result.pr_details || []} />
                </SettingsBaseCard>
              </div>
            ) : null}

            {activeTab === "raw" ? (
              <div className="mt-5 grid gap-4">
                <Card className="grid gap-3 p-5" tone="soft">
                  <h3 className="text-base font-semibold text-foreground">Raw AI analysis</h3>
                  <p className="text-sm leading-6 text-muted-foreground">
                    Debug va prompt tuning uchun Gemini qaytargan to&apos;liq matn.
                  </p>
                  <div className="qa-analysis-block">{result.ai_analysis || "AI analysis qaytmadi."}</div>
                </Card>
              </div>
            ) : null}
          </SettingsBaseCard>
        </>
      ) : result ? (
        <SettingsBaseCard
          header={<SectionHeader eyebrow="Analyze Error" title="TZ-PR tahlili tugamadi" />}
          showCustomizer={false}
        >
          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            {result.error_message || "Xatolik tafsiloti qaytmadi."}
          </p>
          {result.warnings?.length ? (
            <div className="mt-4 grid gap-2">
              {result.warnings.map((warning, index) => (
                <div key={index} className="qa-warning-item">⚠ {warning}</div>
              ))}
            </div>
          ) : null}
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
