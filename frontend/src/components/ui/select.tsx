import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export function Select({ className, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        "flex h-12 w-full rounded-[12px] border border-input bg-card px-4 py-2 text-sm text-foreground shadow-sm outline-none transition-all duration-150 focus-visible:border-primary/40 focus-visible:ring-4 focus-visible:ring-ring/10 disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
