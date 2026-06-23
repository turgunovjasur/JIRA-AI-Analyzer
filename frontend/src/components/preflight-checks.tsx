import { AlertTriangle, Check, CircleMinus, ListChecks, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ModulePreflightCheck } from "@/lib/types";

type PreflightChecksViewProps = {
  checks?: ModulePreflightCheck[] | null;
};

function checkTone(status?: string | null): "success" | "warning" | "danger" | "soft" {
  const normalized = (status || "").toLowerCase();
  if (normalized === "ok") return "success";
  if (normalized === "fail") return "danger";
  if (normalized === "warning") return "warning";
  return "soft";
}

function CheckIcon({ status }: { status?: string | null }) {
  const normalized = (status || "").toLowerCase();
  if (normalized === "ok") return <Check size={15} />;
  if (normalized === "fail") return <XCircle size={15} />;
  if (normalized === "warning") return <AlertTriangle size={15} />;
  return <CircleMinus size={15} />;
}

export function PreflightChecksView({ checks }: PreflightChecksViewProps) {
  const rows = (checks || []).filter(Boolean);
  if (!rows.length) return null;

  const failed = rows.filter((item) => item.status === "fail").length;

  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2 text-sm font-semibold text-foreground">
          <ListChecks size={16} />
          Boshlang'ich checklar
        </div>
        <Badge tone={failed ? "danger" : "success"}>
          {failed ? `${failed} xato` : "Hammasi OK"}
        </Badge>
      </div>

      <div className="grid gap-2">
        {rows.map((item, index) => (
          <div
            className="grid gap-2 rounded-lg border border-border bg-[color:var(--bg-layer)] px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start"
            key={`${item.id || item.label || "check"}-${index}`}
          >
            <div className="min-w-0">
              <div className="flex min-w-0 items-center gap-2">
                <span className="text-muted-foreground"><CheckIcon status={item.status} /></span>
                <span className="min-w-0 break-words text-sm font-semibold text-foreground">
                  {item.label || item.id || "Check"}
                </span>
              </div>
              {item.message ? (
                <p className="mt-1 break-words text-sm leading-6 text-muted-foreground">{item.message}</p>
              ) : null}
              {item.action ? (
                <p className="mt-1 break-words text-xs font-medium text-foreground">{item.action}</p>
              ) : null}
            </div>
            <Badge tone={checkTone(item.status)}>{item.status || "unknown"}</Badge>
          </div>
        ))}
      </div>
    </section>
  );
}
