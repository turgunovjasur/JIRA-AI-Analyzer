import { Badge } from "@/components/ui/badge";

import type { TZPRFileChange, TZPRPullRequestDetail } from "@/lib/types";

function renderPatchPreview(file: TZPRFileChange) {
  if (file.smart_context) {
    return <pre className="overflow-x-auto rounded-[16px] bg-slate-950 p-4 font-mono text-xs leading-6 text-slate-50">{file.smart_context}</pre>;
  }
  if (file.patch) {
    return <pre className="overflow-x-auto rounded-[16px] bg-slate-950 p-4 font-mono text-xs leading-6 text-slate-50">{file.patch}</pre>;
  }
  return <p className="text-sm leading-6 text-muted-foreground">Patch ma'lumoti yo'q.</p>;
}

function renderPullRequestCard(pr: TZPRPullRequestDetail, index: number) {
  const files = pr.files || [];
  return (
    <details className="overflow-hidden rounded-[20px] border border-border bg-card shadow-sm" key={`${pr.number || index}-${pr.url || index}`}>
      <summary className="cursor-pointer list-none px-5 py-4">
        <div>
          <strong>{pr.title || `PR #${pr.number || index + 1}`}</strong>
          <p className="mt-1 text-sm text-muted-foreground">
            #{pr.number || "?"} | {pr.state || "unknown"} | {files.length} fayl
          </p>
        </div>
      </summary>
      <div className="grid gap-4 border-t border-border px-5 py-4">
        <p className="text-sm leading-6 text-muted-foreground">
          Source: {pr.source || "unknown"} | +{pr.additions || 0} / -{pr.deletions || 0}
        </p>
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
              <details
                className="overflow-hidden rounded-[18px] border border-border bg-[color:var(--bg-layer)]"
                key={`${file.filename || fileIndex}-${fileIndex}`}
              >
                <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-4 py-4">
                  <div className="min-w-0">
                    <strong>{file.filename || "unknown file"}</strong>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {file.status || "modified"} | +{file.additions || 0} / -{file.deletions || 0}
                    </p>
                  </div>
                  <Badge tone="soft">{file.status || "modified"}</Badge>
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
              </details>
            ))}
          </div>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">PR ichida fayl ma'lumoti qaytmadi.</p>
        )}
      </div>
    </details>
  );
}

type PRDetailsStackProps = {
  prDetails: TZPRPullRequestDetail[];
};

export function PRDetailsStack({ prDetails }: PRDetailsStackProps) {
  if (!prDetails.length) {
    return <p className="text-sm leading-6 text-muted-foreground">PR tafsilotlari mavjud emas.</p>;
  }

  return (
    <div className="mt-5 grid gap-3">
      {prDetails.map((pr, index) => renderPullRequestCard(pr, index))}
    </div>
  );
}
