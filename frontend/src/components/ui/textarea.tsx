import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function Textarea({ className, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn(
        "flex min-h-28 w-full rounded-[12px] border border-input bg-card px-4 py-3 text-sm text-foreground shadow-sm outline-none transition-all duration-150 placeholder:text-muted-foreground/80 focus-visible:border-primary/40 focus-visible:ring-4 focus-visible:ring-ring/10 disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
