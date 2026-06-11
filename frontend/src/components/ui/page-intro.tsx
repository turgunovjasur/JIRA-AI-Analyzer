import type { ReactNode } from "react";

import { BaseCard } from "@/components/ui/card";
import { cn } from "@/lib/cn";

type PageIntroProps = {
  badge?: ReactNode;
  children?: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: ReactNode;
  title: ReactNode;
};

export function PageIntro({
  badge,
  children,
  className,
  description,
  eyebrow,
  title,
}: PageIntroProps) {
  return (
    <BaseCard
      className={cn(
        "px-6 py-6",
        className,
      )}
      padding="none"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-3">
          {eyebrow ? (
            <span className="inline-flex text-xs font-semibold uppercase tracking-[0.18em] text-primary">
              {eyebrow}
            </span>
          ) : null}
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h2>
            {description ? (
              <p className="max-w-3xl text-sm leading-6 text-muted-foreground">{description}</p>
            ) : null}
          </div>
          {children}
        </div>
        {badge ? <div className="shrink-0">{badge}</div> : null}
      </div>
    </BaseCard>
  );
}
