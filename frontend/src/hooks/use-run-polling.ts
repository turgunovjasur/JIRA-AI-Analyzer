"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getOpenRunStorageKey,
  useRecentRuns,
  type RecentRun,
  type RecentRunScope,
} from "@/lib/use-recent-runs";
import type { ModuleRunErrorPayload, ModuleStartStatus } from "@/lib/types";

export const DEFAULT_RUN_POLL_INTERVAL_MS = 2000;

export type RunResultBase = {
  task_key: string;
  error_message?: string | null;
};

export type RunSnapshotBase<TResult extends RunResultBase> = {
  run_id: string;
  task_key: string;
  run_state?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
  final_result?: TResult | null;
};

export type UseRunPollingOptions<
  TResult extends RunResultBase,
  TSnapshot extends RunSnapshotBase<TResult>,
> = {
  moduleKey: string;
  recentScope?: RecentRunScope;
  /** "/api/tzpr" yoki "/api/testcase" — runs va start-status endpointlari shu bazadan olinadi. */
  apiBasePath: string;
  /** Form input'dagi joriy task key — rememberRun uchun fallback. */
  taskKey: string;
  /** Modul o'z terminal-state ro'yxatini o'zi belgilaydi (testcase'da "error" ham bor). */
  isTerminalRunState: (value?: string | null) => boolean;
  /** final_result kelganda error state qanday hisoblanadi (modul xabarlari farq qiladi). */
  deriveResultError: (result: TResult) => string | null;
  /**
   * final_result bo'lmagan snapshot'dan error matnini chiqaradi.
   * null qaytarilsa error state'ga TEGILMAYDI (checker/testcase shu yerda farq qiladi).
   */
  getSnapshotErrorMessage: (snapshot: TSnapshot, persistFinal: boolean) => string | null;
  /** RecentRun.run_state qiymati (checker final_result.run_state'ga ham qaraydi). */
  getRememberedRunState?: (snapshot: TSnapshot) => string | undefined;
  /** reopenRun boshida moduldagi qo'shimcha state reset (filter, taskKey input). */
  onBeforeReopen?: (entry: RecentRun) => void;
  pollErrorMessage: string;
  pollFailureMessage: string;
  reopenFailureMessage: string;
  pollIntervalMs?: number;
};

/**
 * Run yaratish/kuzatish bo'yicha checker va testcase modullari uchun umumiy logika:
 * - start-status (credential + Gemini kvota) olish
 * - run snapshot polling (terminal holatgacha, 2s interval)
 * - snapshot'ni state'ga qo'llash (applyRunSnapshot) + recent-runs ro'yxati
 * - history'dan runni qayta ochish (reopenRun + sessionStorage auto-open)
 */
export function useRunPolling<
  TResult extends RunResultBase,
  TSnapshot extends RunSnapshotBase<TResult>,
>(options: UseRunPollingOptions<TResult, TSnapshot>) {
  const {
    moduleKey,
    recentScope,
    apiBasePath,
    taskKey,
    isTerminalRunState,
    deriveResultError,
    getSnapshotErrorMessage,
    getRememberedRunState,
    onBeforeReopen,
    pollErrorMessage,
    pollFailureMessage,
    reopenFailureMessage,
    pollIntervalMs = DEFAULT_RUN_POLL_INTERVAL_MS,
  } = options;

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moduleError, setModuleError] = useState<ModuleRunErrorPayload | null>(null);
  const [result, setResult] = useState<TResult | null>(null);
  const [activeRun, setActiveRun] = useState<TSnapshot | null>(null);
  const [startStatus, setStartStatus] = useState<ModuleStartStatus | null>(null);

  const { recent, addRecent, removeRecent } = useRecentRuns(moduleKey, recentScope);
  const openRunStorageKey = getOpenRunStorageKey(moduleKey, recentScope);

  const isResolvedRunSnapshot = useCallback(
    (run?: TSnapshot | null) =>
      Boolean(run && (isTerminalRunState(run.run_state) || run.finished_at || run.final_result)),
    [isTerminalRunState],
  );

  const runInProgress = Boolean(activeRun?.run_id) && !isResolvedRunSnapshot(activeRun);

  // Modul ochilganda (va har run'dan keyin) credential + Gemini kvota holatini olish.
  const refreshStartStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBasePath}/start-status`, { cache: "no-store" });
      if (!res.ok) return;
      const data = (await res.json()) as ModuleStartStatus;
      if (data && typeof data === "object" && data.module_key) setStartStatus(data);
    } catch {
      /* status olinmasa gating ko'rsatilmaydi (backend baribir bloklaydi). */
    }
  }, [apiBasePath]);

  useEffect(() => {
    void refreshStartStatus();
  }, [refreshStartStatus]);

  function rememberRun(snapshot: TSnapshot) {
    const runId = snapshot.run_id?.trim();
    const runTaskKey = (snapshot.task_key || snapshot.final_result?.task_key || taskKey)
      .trim()
      .toUpperCase();
    if (!runId || !runTaskKey) return;
    addRecent({
      run_id: runId,
      task_key: runTaskKey,
      saved_at: Date.now(),
      run_state: getRememberedRunState
        ? getRememberedRunState(snapshot)
        : snapshot.run_state || undefined,
    });
  }

  function applyRunSnapshot(snapshot: TSnapshot, applyOptions?: { persistFinal?: boolean }) {
    setModuleError(null);
    setActiveRun(snapshot);

    // Run yaratilishi/yangilanishi bilanoq recent ro'yxatga yoziladi (dedupe hook ichida).
    rememberRun(snapshot);

    const finalResult = snapshot.final_result || null;
    if (finalResult) {
      setResult(finalResult);
      setError(deriveResultError(finalResult));
      return;
    }

    const snapshotError = getSnapshotErrorMessage(snapshot, Boolean(applyOptions?.persistFinal));
    if (snapshotError !== null) {
      setError(snapshotError);
    }
  }

  async function reopenRun(entry: RecentRun) {
    if (submitting || runInProgress) return;
    setSubmitting(true);
    setError(null);
    setModuleError(null);
    setResult(null);
    setActiveRun(null);
    onBeforeReopen?.(entry);

    try {
      const response = await fetch(`${apiBasePath}/runs/${encodeURIComponent(entry.run_id)}`, {
        cache: "no-store",
      });
      const payload = (await response.json().catch(() => null)) as
        | (TSnapshot & { error?: string })
        | null;
      if (!response.ok) {
        if (response.status === 403 || response.status === 404) {
          removeRecent(entry.run_id);
        }
        setError(payload?.error || "Eski runni yuklab bo'lmadi.");
        return;
      }
      if (!payload) {
        setError("Eski run uchun bo'sh javob qaytdi.");
        return;
      }
      // applyRunSnapshot activeRun'ni o'rnatadi → terminal bo'lmasa polling effekti davom etadi.
      applyRunSnapshot(payload, {
        persistFinal: isResolvedRunSnapshot(payload) || isTerminalRunState(payload.run_state),
      });
    } catch (reopenError) {
      setError(reopenError instanceof Error ? reopenError.message : reopenFailureMessage);
    } finally {
      setSubmitting(false);
    }
  }

  const hasFinalResult = Boolean(activeRun?.final_result);

  useEffect(() => {
    const runId = activeRun?.run_id;
    if (!runId || isResolvedRunSnapshot(activeRun)) return undefined;

    let cancelled = false;
    const intervalId = window.setInterval(async () => {
      try {
        const response = await fetch(`${apiBasePath}/runs/${encodeURIComponent(runId)}`, {
          cache: "no-store",
        });
        const payload = (await response.json().catch(() => null)) as
          | (TSnapshot & { error?: string })
          | null;

        if (!response.ok) {
          if (!cancelled) setError(payload?.error || pollErrorMessage);
          return;
        }
        if (!payload || cancelled) return;

        applyRunSnapshot(payload, {
          persistFinal: isResolvedRunSnapshot(payload) || isTerminalRunState(payload.run_state),
        });
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError instanceof Error ? pollError.message : pollFailureMessage);
        }
      }
    }, pollIntervalMs);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
    // Asl komponentlardagi kabi: faqat run identifikatori/holati o'zgarganda restart bo'ladi.
  }, [activeRun?.run_id, activeRun?.run_state, activeRun?.finished_at, hasFinalResult]);

  const activeRunIsResolved = isResolvedRunSnapshot(activeRun);

  useEffect(() => {
    if (!activeRun?.run_id || !activeRunIsResolved) return;
    // Kvota backendda run terminal holatga kelganda hisoblanadi. Shu paytda
    // start-statusni qayta o'qimasak banner run boshidagi eski qiymatda qoladi.
    // Checker run_state'ni saqlagandan keyin quota increment qilishi mumkin;
    // qisqa kechiktirilgan ikkinchi o'qish shu race'ni ham yopadi.
    void refreshStartStatus();
    const refreshTimer = window.setTimeout(() => {
      void refreshStartStatus();
    }, 1000);
    return () => window.clearTimeout(refreshTimer);
  }, [activeRun?.run_id, activeRunIsResolved, refreshStartStatus]);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(openRunStorageKey);
      if (!raw) return;
      window.sessionStorage.removeItem(openRunStorageKey);
      const entry = JSON.parse(raw) as RecentRun | null;
      if (entry?.run_id?.trim()) {
        void reopenRun(entry);
      }
    } catch {
      /* Historydan auto-open bo'lmasa, sahifa oddiy holatda qoladi. */
    }
  }, [openRunStorageKey]);

  return {
    activeRun,
    setActiveRun,
    result,
    setResult,
    error,
    setError,
    moduleError,
    setModuleError,
    submitting,
    setSubmitting,
    startStatus,
    refreshStartStatus,
    recent,
    runInProgress,
    isResolvedRunSnapshot,
    applyRunSnapshot,
    rememberRun,
    reopenRun,
  };
}
