"use client";

import { useCallback, useEffect, useState } from "react";

export type RecentRun = {
  run_id: string;
  task_key: string;
  saved_at: number;
  run_state?: string;
};

const MAX_RECENT = 3;

/**
 * Modul bo'yicha "So'nggi tekshiruvlar"ni localStorage'da saqlaydi (max 3 ta TASK).
 * Bir task uchun faqat oxirgi run qoladi (task_key bo'yicha dedupe).
 */
export function useRecentRuns(moduleKey: string) {
  const storageKey = `qa.recent-runs.${moduleKey}`;
  const [recent, setRecent] = useState<RecentRun[]>([]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw) as RecentRun[];
        if (Array.isArray(parsed)) {
          setRecent(parsed.slice(0, MAX_RECENT));
        }
      }
    } catch {
      /* localStorage o'qib bo'lmadi — e'tibor bermaymiz */
    }
  }, [storageKey]);

  const write = useCallback(
    (items: RecentRun[]) => {
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(items));
      } catch {
        /* yozib bo'lmadi — e'tibor bermaymiz */
      }
    },
    [storageKey],
  );

  const addRecent = useCallback(
    (entry: RecentRun) => {
      setRecent((current) => {
        const key = entry.task_key.trim().toUpperCase();
        const deduped = current.filter(
          (item) => item.task_key.trim().toUpperCase() !== key,
        );
        const next = [entry, ...deduped].slice(0, MAX_RECENT);
        write(next);
        return next;
      });
    },
    [write],
  );

  const removeRecent = useCallback(
    (runId: string) => {
      setRecent((current) => {
        const next = current.filter((item) => item.run_id !== runId);
        write(next);
        return next;
      });
    },
    [write],
  );

  return { recent, addRecent, removeRecent };
}
