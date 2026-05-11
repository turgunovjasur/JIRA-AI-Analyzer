import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type MetricCardProps = {
  className?: string;
  helper?: ReactNode;
  label: ReactNode;
  value: ReactNode;
};

export function MetricCard({ className, helper, label, value }: MetricCardProps) {
  return (
    <article
      className={cn(
        "rounded-[18px] border border-border bg-card px-5 py-5 shadow-sm",
        className,
      )}
    >
      <span className="inline-flex text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
        {label}
      </span>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-foreground">{value}</div>
      {helper ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{helper}</p> : null}
    </article>
  );
}
