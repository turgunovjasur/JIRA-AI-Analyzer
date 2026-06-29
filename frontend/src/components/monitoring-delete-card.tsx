"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";

export function MonitoringDeleteCard() {
  const router = useRouter();
  const [taskKey, setTaskKey] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  async function onDelete(event: React.FormEvent) {
    event.preventDefault();
    const normalized = taskKey.trim().toUpperCase();
    if (!normalized) return;
    if (!window.confirm(`${normalized} taskini DB'dan o'chirishni tasdiqlaysizmi? Bu qayta ishlashga ruxsat beradi.`)) {
      return;
    }

    setSubmitting(true);
    setResult(null);
    try {
      const response = await fetch(`/api/monitoring/tasks/${encodeURIComponent(normalized)}`, {
        method: "DELETE",
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload?.success) {
        const message =
          payload?.error ||
          (response.status === 404 ? "Task topilmadi." : "O'chirishda xato yuz berdi.");
        setResult({ tone: "error", text: message });
        return;
      }
      setResult({ tone: "success", text: `${normalized} o'chirildi — endi qayta ishlash mumkin.` });
      setTaskKey("");
      router.refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "O'chirishda xato yuz berdi.";
      setResult({ tone: "error", text: message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <SectionHeader
        eyebrow="Maintenance"
        title="Task o'chirish"
        action={null}
      />
      <p className="mt-2 text-sm text-muted-foreground">
        Avval ishlangan taskni DB&apos;dan o&apos;chiradi — duplicate himoyasi olib tashlanadi va task
        qayta ishlanadi.
      </p>
      <form className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={onDelete}>
        <div className="flex-1">
          <Field label="Task key">
            <Input
              onChange={(e) => setTaskKey(e.target.value)}
              placeholder="DEV-8245"
              value={taskKey}
            />
          </Field>
        </div>
        <Button disabled={submitting || !taskKey.trim()} type="submit" variant="danger">
          {submitting ? "O'chirilmoqda..." : "O'chirish"}
        </Button>
      </form>
      {result ? (
        <div className="mt-3">
          <Notice tone={result.tone}>{result.text}</Notice>
        </div>
      ) : null}
    </Card>
  );
}
