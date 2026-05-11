import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type NoticeTone = "error" | "success" | "warning" | "info";

const noticeVariants = cva("rounded-[14px] border px-4 py-3 text-sm leading-6 shadow-sm", {
  variants: {
    tone: {
      error: "border-[color:var(--error-border)] bg-[color:var(--error-soft)] text-[color:var(--error)]",
      success: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success)]",
      warning: "border-[color:var(--warn-border)] bg-[color:var(--warn-soft)] text-[color:var(--warning)]",
      info: "border-[color:var(--line-strong)] bg-[color:var(--accent-soft)] text-[color:var(--accent)]",
    },
  },
  defaultVariants: {
    tone: "info",
  },
});

export type NoticeProps = HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof noticeVariants> & {
    children: ReactNode;
    tone?: NoticeTone;
  };

export function Notice({
  children,
  className,
  tone = "info",
  ...props
}: NoticeProps) {
  return (
    <div className={cn(noticeVariants({ tone }), className)} {...props}>
      {children}
    </div>
  );
}
