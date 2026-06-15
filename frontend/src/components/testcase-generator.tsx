"use client";

import { useState, type FormEvent } from "react";
import { ClipboardList, FileCode2, ListChecks } from "lucide-react";

import { PRDetailsStack } from "@/components/pr-details-stack";
import { AnalysisStatusBannerView } from "@/components/analysis-status-banner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BaseCard } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import {
  BaseCheckGroup,
  BaseInputField,
  BaseTextAreaField,
  SettingsBaseCard,
} from "@/components/settings/base-card-system";
import type { GeneratedTestCase, TestCaseGenerationResult } from "@/lib/types";

const TEST_TYPE_OPTIONS = [
  { value: "positive", label: "Positive" },
  { value: "negative", label: "Negative" },
];

const TEST_TYPE_CHECK_OPTIONS = TEST_TYPE_OPTIONS.map((item) => ({
  badge: item.value,
  key: item.value,
  label: item.label,
}));
const SETTINGS_INPUT_CLASS = "settings-form-input";

function priorityTone(priority: string): "danger" | "warning" | "soft" {
  if (priority === "High") return "danger";
  if (priority === "Medium") return "warning";
  return "soft";
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
        <span className="flex-1 text-sm font-semibold text-foreground">
          {testCase.title}
        </span>
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
      const response = await fetch("/api/testcase/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_key: normalizedTaskKey,
          include_pr: true,
          test_types: selectedTypes,
          custom_context: customContext.trim(),
        }),
      });

      const payload = (await response.json().catch(() => null)) as
        | (TestCaseGenerationResult & { error?: string })
        | null;

      if (!response.ok) {
        setError(payload?.error || "Testcase generation request xatosi.");
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
            : (payload.error_message || "Test case generation muvaffaqiyatsiz tugadi."),
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
            action={<Badge tone="soft">PR yoqilgan</Badge>}
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

      {error ? <Notice tone="error">{error}</Notice> : null}
      {result?.status_banner ? <AnalysisStatusBannerView banner={result.status_banner} /> : null}

      {result?.success ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <MetricCard
              helper="Yaratilgan umumiy testcase soni"
              label="Test Cases"
              value={result.total_test_cases || 0}
            />
            <MetricCard
              helper="Task bilan bog'langan PR soni"
              label="PR Count"
              value={result.pr_count || 0}
            />
            <MetricCard
              helper="Ko'rilgan o'zgargan fayllar"
              label="Files"
              value={result.files_changed || 0}
            />
          </section>

          <section className="grid gap-4 lg:grid-cols-3">
            <SettingsBaseCard>
              <div className="inline-flex rounded-full bg-primary/10 p-2 text-primary">
                <ClipboardList size={16} />
              </div>
              <h3 className="mt-4 text-base font-bold text-foreground">{result.task_key}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {result.task_summary || "Task summary mavjud emas."}
              </p>
            </SettingsBaseCard>
            <SettingsBaseCard>
              <div className="inline-flex rounded-full bg-primary/10 p-2 text-primary">
                <ListChecks size={16} />
              </div>
              <h3 className="mt-4 text-base font-bold text-foreground">
                {result.by_priority?.High || 0}
              </h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                High priority testcase soni
              </p>
            </SettingsBaseCard>
            <SettingsBaseCard>
              <div className="inline-flex rounded-full bg-primary/10 p-2 text-primary">
                <FileCode2 size={16} />
              </div>
              <h3 className="mt-4 text-base font-bold text-foreground">
                {result.custom_context_used ? "Ha" : "Yo&apos;q"}
              </h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Qo&apos;shimcha buyruq ishlatilganmi
              </p>
            </SettingsBaseCard>
          </section>

          {result.by_priority && Object.keys(result.by_priority).length > 0 ? (
            <SettingsBaseCard
              header={<SectionHeader eyebrow="Priority" title="Ustuvorlik bo&apos;yicha" />}
            >
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(result.by_priority).map(([priority, count]) => (
                  <Badge key={priority} tone={priorityTone(priority)}>
                    {priority}: {count}
                  </Badge>
                ))}
              </div>
            </SettingsBaseCard>
          ) : null}

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

          <SettingsBaseCard
            header={<SectionHeader eyebrow="Overview" title="Task overview" />}
          >
            {result.comment_changes_detected && result.comment_summary ? (
              <Notice className="mt-4" tone="warning">{result.comment_summary}</Notice>
            ) : null}
            <div className="qa-analysis-block mt-4">
              {result.task_overview || "Task overview qaytmadi."}
            </div>
          </SettingsBaseCard>

          <SettingsBaseCard
            header={(
              <SectionHeader
                action={<Badge tone="soft">{result.total_test_cases || 0} ta</Badge>}
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

          <SettingsBaseCard
            header={<SectionHeader eyebrow="Code Changes" title="PR tafsilotlari" />}
          >
            <PRDetailsStack prDetails={result.pr_details || []} />
          </SettingsBaseCard>

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
