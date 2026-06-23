"use client";

import { useCallback, useEffect, useState } from "react";

export type RecentRun = {
  run_id: string;
  task_key: string;
  saved_at: number;
  run_state?: string;
};

export type RecentRunScope = {
  companyId?: number | null;
  role?: string | null;
  userId?: number | null;
};

const MAX_RECENT = 3;
const STORAGE_VERSION = "v2";

function normalizeScopePart(prefix: string, value?: number | string | null) {
  const raw = value === null || value === undefined ? "" : String(value).trim().toLowerCase();
  return `${prefix}-${raw || "none"}`.replace(/[^a-z0-9_-]/g, "_");
}

function buildScopeKey(scope?: RecentRunScope) {
  return [
    normalizeScopePart("role", scope?.role || "unknown"),
    normalizeScopePart("company", scope?.companyId),
    normalizeScopePart("user", scope?.userId),
  ].join(".");
}

export function getRecentRunsStorageKey(moduleKey: string, scope?: RecentRunScope) {
  return `qa.recent-runs.${STORAGE_VERSION}.${moduleKey}.${buildScopeKey(scope)}`;
}

export function getOpenRunStorageKey(moduleKey: string, scope?: RecentRunScope) {
  return `qa.open-run.${STORAGE_VERSION}.${moduleKey}.${buildScopeKey(scope)}`;
}

function clearStorageKeys(storage: Storage, prefixes: string[]) {
  const keys: string[] = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key && prefixes.some((prefix) => key.startsWith(prefix))) {
      keys.push(key);
    }
  }
  keys.forEach((key) => storage.removeItem(key));
}

export function clearRunHistoryStorage() {
  try {
    clearStorageKeys(window.localStorage, ["qa.recent-runs."]);
  } catch {
    /* localStorage tozalab bo'lmadi — e'tibor bermaymiz */
  }

  try {
    clearStorageKeys(window.sessionStorage, ["qa.open-run."]);
  } catch {
    /* sessionStorage tozalab bo'lmadi — e'tibor bermaymiz */
  }
}

/**
 * Modul bo'yicha "So'nggi tekshiruvlar"ni localStorage'da saqlaydi (max 3 ta TASK).
 * Bir task uchun faqat oxirgi run qoladi (task_key bo'yicha dedupe).
 */
export function useRecentRuns(moduleKey: string, scope?: RecentRunScope) {
  const storageKey = getRecentRunsStorageKey(moduleKey, scope);
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
