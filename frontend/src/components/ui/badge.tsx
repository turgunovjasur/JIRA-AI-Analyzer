import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type BadgeTone = "default" | "soft" | "success" | "warning" | "danger";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold tracking-[0.02em]",
  {
    variants: {
      tone: {
        default: "border-border bg-[color:var(--bg-strong)] text-foreground",
        soft: "border-primary/10 bg-accent text-accent-foreground",
        success: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success)]",
        warning: "border-[color:var(--warn-border)] bg-[color:var(--warn-soft)] text-[color:var(--warning)]",
        danger: "border-[color:var(--error-border)] bg-[color:var(--error-soft)] text-[color:var(--error)]",
      },
    },
    defaultVariants: {
      tone: "default",
    },
  },
);

export type BadgeProps = HTMLAttributes<HTMLSpanElement> &
  VariantProps<typeof badgeVariants> & {
    tone?: BadgeTone;
  };

export function Badge({
  className,
  tone = "default",
  ...props
}: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
