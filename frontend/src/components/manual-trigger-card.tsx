"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";

type TriggerState =
  | { tone: "success"; message: string }
  | { tone: "error"; message: string }
  | { tone: "warning"; message: string }
  | null;

function normalizeTaskKey(value: string) {
  return value.trim().toUpperCase();
}

function isValidTaskKey(value: string) {
  return /^[A-Z][A-Z0-9]+-\d+$/.test(value) || /^\d+$/.test(value);
}

export function ManualTriggerCard() {
  const router = useRouter();
  const [taskKey, setTaskKey] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<TriggerState>(null);

  async function submitManualTrigger(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedTaskKey = normalizeTaskKey(taskKey);
    if (!normalizedTaskKey) {
      setResult({ tone: "error", message: "Task key kiriting." });
      return;
    }
    if (!isValidTaskKey(normalizedTaskKey)) {
      setResult({ tone: "error", message: "Task key to'liq bo'lishi kerak: DEV-1234." });
      return;
    }

    setPending(true);
    setResult(null);

    try {
      const response = await fetch("/api/monitoring/manual-trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_key: normalizedTaskKey }),
      });
      const payload = await response.json().catch(() => null);
      const backendStatus = typeof payload?.status === "string" ? payload.status : "";
      if (!response.ok || backendStatus === "error") {
        const message =
          typeof payload?.error === "string"
            ? payload.error
            : typeof payload?.reason === "string"
              ? payload.reason
            : "Manual trigger ishga tushmadi.";
        setResult({ tone: "error", message });
        router.refresh();
        return;
      }
      if (backendStatus === "ignored") {
        const message =
          typeof payload?.reason === "string"
            ? payload.reason
            : "Manual trigger o'tkazib yuborildi.";
        setResult({ tone: "warning", message });
        router.refresh();
        return;
      }

      const status = backendStatus || "processing";
      const resolvedTaskKey =
        typeof payload?.task_key === "string" && payload.task_key
          ? payload.task_key
          : normalizedTaskKey;
      setResult({
        tone: "success",
        message: `${resolvedTaskKey} monitoringga qo'shildi va servislar ishga tushdi (${status}).`,
      });
      setTaskKey(resolvedTaskKey);
      router.refresh();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Manual trigger ishga tushmadi.";
      setResult({ tone: "error", message });
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <SectionHeader eyebrow="Manual trigger" title="Taskni qo'lda ishga tushirish" />
      <form className="mt-4 grid gap-3 md:grid-cols-[minmax(180px,320px)_auto]" onSubmit={submitManualTrigger}>
        <Input
          autoComplete="off"
          disabled={pending}
          onChange={(event) => setTaskKey(event.target.value)}
          placeholder="DEV-1234"
          value={taskKey}
        />
        <Button disabled={pending} type="submit">
          {pending ? "Yuborilmoqda..." : "Run"}
        </Button>
      </form>
      {result ? (
        <Notice className="mt-4" tone={result.tone}>
          {result.message}
        </Notice>
      ) : null}
    </Card>
  );
}
