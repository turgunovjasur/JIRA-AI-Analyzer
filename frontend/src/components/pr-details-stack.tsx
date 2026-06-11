import { Badge } from "@/components/ui/badge";
import { BaseCard } from "@/components/ui/card";

import type {
  TZPRFileChange,
  TZPRPullRequestDetail,
  TZPRPullRequestSelection,
  TZPRPullRequestSelectionItem,
} from "@/lib/types";

function getPatchSource(file: TZPRFileChange) {
  if (file.smart_context?.trim()) {
    return {
      label: "Smart patch",
      tone: "success" as const,
      text: file.smart_context,
    };
  }

  if (file.patch?.trim()) {
    return {
      label: "Raw diff",
      tone: "soft" as const,
      text: file.patch,
    };
  }

  return null;
}

function normalizePatchLines(text: string) {
  return text
    .replace(/^```diff\s*/i, "")
    .replace(/^```/i, "")
    .replace(/\s*```$/, "")
    .split("\n");
}

function getStatusTone(status?: string | null) {
  const value = (status || "").toLowerCase();

  if (value === "added") return "success" as const;
  if (value === "removed" || value === "deleted") return "danger" as const;
  if (value === "renamed") return "warning" as const;

  return "soft" as const;
}

function getLineClasses(line: string) {
  if (line.startsWith("@@")) {
    return "bg-[color:var(--accent-soft)] text-[color:var(--accent)]";
  }
  if (line.startsWith("+") && !line.startsWith("+++")) {
    return "bg-[color:var(--success-soft)] text-[color:var(--success)]";
  }
  if (line.startsWith("-") && !line.startsWith("---")) {
    return "bg-[color:var(--error-soft)] text-[color:var(--error)]";
  }
  if (
    line.startsWith("diff ") ||
    line.startsWith("index ") ||
    line.startsWith("+++") ||
    line.startsWith("---")
  ) {
    return "bg-white/6 text-slate-300";
  }

  return "text-slate-100";
}

function renderPatchPreview(file: TZPRFileChange) {
  const source = getPatchSource(file);

  if (!source) {
    return <p className="text-sm leading-6 text-muted-foreground">Patch ma'lumoti yo'q.</p>;
  }

  const lines = normalizePatchLines(source.text);

  return (
    <BaseCard as="div" className="overflow-hidden !bg-[color:var(--surface-dark)]" padding="none">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/8 px-4 py-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Kod preview
          </div>
          <p className="mt-1 text-xs text-slate-300">
            Diff satrma-satr rang bilan ko'rsatiladi
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={source.tone}>{source.label}</Badge>
          <Badge className="border-white/10 bg-white/8 text-slate-200">{lines.length} qator</Badge>
        </div>
      </div>

      <div className="max-h-[420px] overflow-auto px-3 py-3">
        <div className="grid gap-1">
          {lines.map((line, index) => (
            <div
              key={`patch-line-${index}`}
              className={`grid grid-cols-[44px_minmax(0,1fr)] items-start gap-3 rounded-[10px] px-2 py-1.5 font-mono text-xs leading-6 ${getLineClasses(line)}`}
            >
              <span className="select-none text-right text-[11px] text-slate-500">
                {index + 1}
              </span>
              <code className="block overflow-x-auto whitespace-pre">{line || " "}</code>
            </div>
          ))}
        </div>
      </div>
    </BaseCard>
  );
}

function renderPullRequestCard(pr: TZPRPullRequestDetail, index: number) {
  const files = pr.files || [];

  return (
    <BaseCard
      as="details"
      className="overflow-hidden"
      key={`${pr.number || index}-${pr.url || index}`}
      padding="none"
    >
      <summary className="cursor-pointer list-none px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <strong className="text-base text-foreground">{pr.title || `PR #${pr.number || index + 1}`}</strong>
            <p className="mt-1 text-sm text-muted-foreground">
              #{pr.number || "?"} | {pr.state || "unknown"} | {files.length} fayl
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="soft">{pr.source || "unknown"}</Badge>
            <Badge tone="success">+{pr.additions || 0}</Badge>
            <Badge tone="danger">-{pr.deletions || 0}</Badge>
          </div>
        </div>
      </summary>
      <div className="grid gap-4 border-t border-border px-5 py-4">
        {pr.url ? (
          <p>
            <a className="text-sm font-medium text-primary hover:underline" href={pr.url} rel="noreferrer" target="_blank">
              PR linkini ochish
            </a>
          </p>
        ) : null}

        {files.length ? (
          <div className="grid gap-3">
            {files.map((file, fileIndex) => (
              <BaseCard
                as="details"
                className="overflow-hidden"
                key={`${file.filename || fileIndex}-${fileIndex}`}
                padding="none"
                tone="soft"
              >
                <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-4 py-4">
                  <div className="min-w-0">
                    <strong className="break-all text-sm text-foreground">{file.filename || "unknown file"}</strong>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {file.status || "modified"} | +{file.additions || 0} / -{file.deletions || 0}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={getStatusTone(file.status)}>{file.status || "modified"}</Badge>
                    <Badge tone="success">+{file.additions || 0}</Badge>
                    <Badge tone="danger">-{file.deletions || 0}</Badge>
                  </div>
                </summary>
                <div className="grid gap-4 border-t border-border px-4 py-4">
                  {renderPatchPreview(file)}
                  {file.blob_url ? (
                    <p>
                      <a className="text-sm font-medium text-primary hover:underline" href={file.blob_url} rel="noreferrer" target="_blank">
                        GitHub faylini ochish
                      </a>
                    </p>
                  ) : null}
                </div>
              </BaseCard>
            ))}
          </div>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">PR ichida fayl ma'lumoti qaytmadi.</p>
        )}
      </div>
    </BaseCard>
  );
}

function formatPrLabel(pr: TZPRPullRequestSelectionItem, index: number) {
  const number = pr.number ? `#${pr.number}` : `PR ${index + 1}`;
  return pr.title ? `${number} - ${pr.title}` : number;
}

function renderSelectionList(items: TZPRPullRequestSelectionItem[], emptyText: string, tone: "success" | "warning") {
  if (!items.length) {
    return <p className="text-sm leading-6 text-muted-foreground">{emptyText}</p>;
  }

  return (
    <div className="grid gap-2">
      {items.map((item, index) => (
        <BaseCard
          as="div"
          className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
          key={`${item.number || index}-${item.url || index}`}
          padding="none"
          tone="soft"
        >
          <div className="min-w-0">
            {item.url ? (
              <a className="break-words text-sm font-medium text-primary hover:underline" href={item.url} rel="noreferrer" target="_blank">
                {formatPrLabel(item, index)}
              </a>
            ) : (
              <span className="break-words text-sm font-medium text-foreground">{formatPrLabel(item, index)}</span>
            )}
            <p className="mt-1 text-xs text-muted-foreground">
              {item.state || "unknown"} | {item.files_count || 0} fayl
              {item.reason ? ` | ${item.reason}` : ""}
            </p>
          </div>
          <Badge tone={tone}>{tone === "success" ? "Merged" : "Skipped"}</Badge>
        </BaseCard>
      ))}
    </div>
  );
}

function renderPrSelectionSummary(prSelection?: TZPRPullRequestSelection | null) {
  if (!prSelection) {
    return null;
  }

  const merged = prSelection.merged || [];
  const skipped = prSelection.skipped || [];

  return (
    <BaseCard as="div" className="grid gap-4 px-4 py-4" padding="none" tone="soft">
      <div className="flex flex-wrap gap-2">
        <Badge tone="soft">{prSelection.found_count || 0} topildi</Badge>
        <Badge tone="success">{prSelection.merged_count || 0} merged</Badge>
        <Badge tone={prSelection.skipped_count ? "warning" : "soft"}>{prSelection.skipped_count || 0} skipped</Badge>
        <Badge tone="soft">{prSelection.analyzed_count || 0} tahlil qilindi</Badge>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Merged PR'lar</div>
          {renderSelectionList(merged, "Merged PR qaytmadi.", "success")}
        </div>
        <div>
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Skipped PR'lar</div>
          {renderSelectionList(skipped, "Skipped PR yo'q.", "warning")}
        </div>
      </div>
    </BaseCard>
  );
}

type PRDetailsStackProps = {
  prDetails: TZPRPullRequestDetail[];
  prSelection?: TZPRPullRequestSelection | null;
};

export function PRDetailsStack({ prDetails, prSelection }: PRDetailsStackProps) {
  if (!prDetails.length && !prSelection) {
    return <p className="text-sm leading-6 text-muted-foreground">PR tafsilotlari mavjud emas.</p>;
  }

  return (
    <div className="grid gap-3">
      {renderPrSelectionSummary(prSelection)}
      {prDetails.map((pr, index) => renderPullRequestCard(pr, index))}
    </div>
  );
}
