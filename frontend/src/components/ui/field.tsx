import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type FieldProps = {
  children: ReactNode;
  className?: string;
  hint?: ReactNode;
  label: ReactNode;
};

export function Field({ children, className, hint, label }: FieldProps) {
  return (
    <label className={cn("grid gap-2", className)}>
      <span className="text-sm font-medium text-foreground">{label}</span>
      {children}
      {hint ? <small className="text-xs leading-5 text-muted-foreground">{hint}</small> : null}
    </label>
  );
}
