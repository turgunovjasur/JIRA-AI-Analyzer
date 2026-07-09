"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export function MonitoringRefreshButton() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function handleRefresh() {
    startTransition(() => {
      router.refresh();
    });
  }

  return (
    <Button
      aria-label="Ma'lumotlarni yangilash"
      disabled={pending}
      onClick={handleRefresh}
      size="sm"
      variant="ghost"
    >
      <svg
        aria-hidden="true"
        className={pending ? "animate-spin" : undefined}
        fill="none"
        height="16"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
        viewBox="0 0 24 24"
        width="16"
      >
        <path d="M21 12a9 9 0 1 1-2.64-6.36" />
        <path d="M21 3v6h-6" />
      </svg>
      {pending ? "Yangilanmoqda..." : "Yangilash"}
    </Button>
  );
}
