import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type SectionHeaderProps = {
  action?: ReactNode;
  className?: string;
  eyebrow?: ReactNode;
  title: ReactNode;
};

export function SectionHeader({ action, className, eyebrow, title }: SectionHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-3 md:flex-row md:items-start md:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? (
          <span className="inline-flex text-xs font-semibold uppercase tracking-[0.18em] text-primary">
            {eyebrow}
          </span>
        ) : null}
        <h3 className="text-xl font-semibold tracking-tight text-foreground">{title}</h3>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
