import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "flex h-12 w-full rounded-[12px] border border-input bg-card px-4 py-2 text-sm text-foreground shadow-sm outline-none transition-all duration-150 placeholder:text-muted-foreground/80 focus-visible:border-primary/40 focus-visible:ring-4 focus-visible:ring-ring/10 disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
