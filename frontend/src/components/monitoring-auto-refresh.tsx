"use client";

import { useEffect } from "react";

function isEditingElement(element: Element | null) {
  if (!element) return false;
  const tagName = element.tagName.toLowerCase();
  return tagName === "input" || tagName === "textarea" || tagName === "select";
}

export function MonitoringAutoRefresh({ intervalMs = 15000 }: { intervalMs?: number }) {
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      if (isEditingElement(document.activeElement)) return;

      window.location.reload();
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [intervalMs]);

  return null;
}
