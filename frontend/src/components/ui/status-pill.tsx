import { cn } from "@/lib/cn";

type StatusTone = "good" | "bad" | "warn" | "info" | "muted";

const toneClassName: Record<StatusTone, string> = {
  bad: "border-[color:var(--error-border)] bg-[color:var(--error-soft)] text-[color:var(--error)]",
  good: "border-[color:var(--success-border)] bg-[color:var(--success-soft)] text-[color:var(--success)]",
  info: "border-[color:var(--line-strong)] bg-[color:var(--accent-soft)] text-[color:var(--accent)]",
  muted: "border-border bg-[color:var(--bg-strong)] text-muted-foreground",
  warn: "border-[color:var(--warn-border)] bg-[color:var(--warn-soft)] text-[color:var(--warning)]",
};

type StatusPillProps = {
  className?: string;
  tone?: StatusTone;
  value: string;
};

export function StatusPill({ className, tone = "muted", value }: StatusPillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold tracking-[0.02em]",
        toneClassName[tone],
        className,
      )}
    >
      {value}
    </span>
  );
}
