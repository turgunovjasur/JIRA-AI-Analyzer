"use client";

import { Clock3, History, Plus, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";
import { useRecentRuns, type RecentRun } from "@/lib/use-recent-runs";

type RecentRunsHistoryProps = {
  basePath: string;
  moduleKey: string;
  storageKey: string;
  title: string;
};

function formatSavedAt(value?: number) {
  if (!value) return "Noma'lum";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Noma'lum";
  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function getRunTone(value?: string | null): "soft" | "success" | "warning" | "danger" {
  const normalized = (value || "").toLowerCase();
  if (normalized === "completed") return "success";
  if (normalized === "running" || normalized === "queued" || normalized === "manual_review") return "warning";
  if (normalized === "blocked" || normalized === "failed" || normalized === "error") return "danger";
  return "soft";
}

export function RecentRunsHistory({
  basePath,
  moduleKey,
  storageKey,
  title,
}: RecentRunsHistoryProps) {
  const router = useRouter();
  const { recent } = useRecentRuns(moduleKey);

  function openRun(entry: RecentRun) {
    try {
      window.sessionStorage.setItem(storageKey, JSON.stringify(entry));
    } catch {
      // Session storage ishlamasa ham asosiy sahifaga qaytamiz.
    }
    router.push(basePath);
  }

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            <History size={14} />
            History
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Saqlangan oxirgi runlarni list ko'rinishida oching.
          </p>
        </div>
        <Button
          asChild
          className="bg-primary !text-white hover:bg-[color:var(--brand-strong)] hover:!text-white [&_*]:!text-white"
          size="sm"
          type="button"
        >
          <Link href={basePath}>
            <Plus size={14} />
            New Task
          </Link>
        </Button>
      </div>

      <section className="grid gap-3">
        <SectionHeader
          action={<Badge tone="soft">oxirgi {recent.length} ta</Badge>}
          eyebrow="History"
          title="So'nggi tekshiruvlar"
        />

        {recent.length ? (
          <div className="grid gap-3">
            {recent.map((entry) => (
              <button
                className="grid gap-3 rounded-[12px] border border-border bg-card px-4 py-4 text-left transition-colors hover:border-primary/25 hover:bg-[color:var(--bg-layer)]"
                key={entry.run_id}
                onClick={() => openRun(entry)}
                type="button"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="inline-flex min-w-0 items-center gap-2">
                    <Clock3 className="shrink-0 text-muted-foreground" size={15} />
                    <span className="truncate font-mono text-sm font-semibold text-foreground">{entry.task_key}</span>
                  </span>
                  <Badge tone={getRunTone(entry.run_state)}>{entry.run_state || "-"}</Badge>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  <span className="font-mono">{entry.run_id}</span>
                  <span>{formatSavedAt(entry.saved_at)}</span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <Card>
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-accent text-primary">
                <RotateCcw size={16} />
              </div>
              <div>
                <p className="font-semibold text-foreground">History hali bo'sh</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  Birinchi run tugagandan keyin u shu yerda list ko'rinishida chiqadi.
                </p>
              </div>
            </div>
          </Card>
        )}
      </section>
    </div>
  );
}
