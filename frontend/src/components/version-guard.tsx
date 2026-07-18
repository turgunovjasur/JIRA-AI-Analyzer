"use client";

import { useEffect, useState } from "react";

// Redeploy'dan keyin brauzerdagi eski JS bundle "jim yiqilish"ga sabab bo'ladi
// (masalan "Failed to find Server Action"). Bu komponent server build ID'sini
// kuzatadi; o'zgarsa foydalanuvchiga yangilashni taklif qiladi.

const POLL_MS = 2 * 60 * 1000; // har 2 daqiqa

async function fetchBuildId(signal?: AbortSignal): Promise<string | null> {
  try {
    const res = await fetch("/api/version", { cache: "no-store", signal });
    if (!res.ok) return null;
    const data = (await res.json()) as { buildId?: string };
    return typeof data.buildId === "string" ? data.buildId : null;
  } catch {
    return null;
  }
}

export function VersionGuard() {
  const [baseline, setBaseline] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  useEffect(() => {
    // Dev rejimda HMR build ID'ni tez-tez o'zgartiradi — bannerni faqat
    // production'da kuzatamiz (redeploy holati uchun).
    if (process.env.NODE_ENV !== "production") return;

    let active = true;
    const controller = new AbortController();

    fetchBuildId(controller.signal).then((id) => {
      if (active && id) setBaseline(id);
    });

    async function check() {
      const id = await fetchBuildId();
      if (!active || !id) return;
      setBaseline((current) => {
        if (current && id !== current) setStale(true);
        return current ?? id;
      });
    }

    const timer = window.setInterval(check, POLL_MS);
    const onFocus = () => void check();
    window.addEventListener("focus", onFocus);

    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  if (!stale) return null;

  return (
    <div
      role="status"
      style={{
        position: "fixed",
        insetInlineStart: 0,
        insetInlineEnd: 0,
        bottom: 0,
        zIndex: 9999,
        display: "flex",
        gap: "0.75rem",
        alignItems: "center",
        justifyContent: "center",
        padding: "0.75rem 1rem",
        background: "#1f2937",
        color: "#f9fafb",
        fontSize: "0.875rem",
        boxShadow: "0 -2px 12px rgba(0,0,0,0.25)",
      }}
    >
      <span>Yangi versiya chiqdi. Ishlashda muammo bo'lmasligi uchun sahifani yangilang.</span>
      <button
        type="button"
        onClick={() => window.location.reload()}
        style={{
          background: "#22c55e",
          color: "#052e16",
          border: "none",
          borderRadius: "0.375rem",
          padding: "0.375rem 0.875rem",
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        Yangilash
      </button>
    </div>
  );
}
