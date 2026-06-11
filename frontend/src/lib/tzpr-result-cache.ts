import type { TZPRAnalysisResult, TZPRExecutionMode, UserRole } from "@/lib/types";

export type TZPRResultCacheScope = {
  companyCode?: string | null;
  companyId?: number | null;
  role?: UserRole | null;
  userId?: number | null;
};

export type TZPRCachedResultEntry = {
  checkedAt: string;
  executionMode?: TZPRExecutionMode;
  result: TZPRAnalysisResult;
  taskKey: string;
};

type TZPRCachedResultEnvelope = {
  entries: TZPRCachedResultEntry[];
  version: number;
};

const TZPR_RESULT_CACHE_VERSION = 1;
export const MAX_TZPR_CACHED_RESULTS = 3;
const TZPR_RESULT_CACHE_KEY_PREFIX = "tzpr-result-history";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isAnalysisResult(value: unknown): value is TZPRAnalysisResult {
  return isRecord(value)
    && typeof value.success === "boolean"
    && typeof value.task_key === "string";
}

function isCachedResultEntry(value: unknown): value is TZPRCachedResultEntry {
  return isRecord(value)
    && typeof value.checkedAt === "string"
    && typeof value.taskKey === "string"
    && (value.executionMode === undefined || value.executionMode === "multi_agent")
    && isAnalysisResult(value.result);
}

function getScopeValue(...values: Array<string | number | null | undefined>) {
  for (const value of values) {
    if (value !== null && value !== undefined && String(value).trim()) {
      return String(value).trim().toLowerCase();
    }
  }
  return "global";
}

export function buildTZPRResultCacheKey(scope: TZPRResultCacheScope) {
  const companyScope = getScopeValue(scope.companyId, scope.companyCode);
  const userScope = getScopeValue(scope.userId, scope.role);
  return `${TZPR_RESULT_CACHE_KEY_PREFIX}:v${TZPR_RESULT_CACHE_VERSION}:${companyScope}:${userScope}`;
}

export function readTZPRResultHistory(storage: Storage, storageKey: string) {
  try {
    const raw = storage.getItem(storageKey);
    if (!raw) return [];

    const parsed = JSON.parse(raw) as TZPRCachedResultEnvelope | null;
    if (!parsed || parsed.version !== TZPR_RESULT_CACHE_VERSION || !Array.isArray(parsed.entries)) {
      return [];
    }

    return parsed.entries
      .filter(isCachedResultEntry)
      .slice(0, MAX_TZPR_CACHED_RESULTS);
  } catch {
    return [];
  }
}

export function writeTZPRResultHistory(
  storage: Storage,
  storageKey: string,
  entries: TZPRCachedResultEntry[],
) {
  const payload: TZPRCachedResultEnvelope = {
    entries: entries.slice(0, MAX_TZPR_CACHED_RESULTS),
    version: TZPR_RESULT_CACHE_VERSION,
  };
  storage.setItem(storageKey, JSON.stringify(payload));
}

export function upsertTZPRResultHistory(
  entries: TZPRCachedResultEntry[],
  nextEntry: TZPRCachedResultEntry,
) {
  const normalizedTaskKey = nextEntry.taskKey.trim().toUpperCase();
  const nextEntries = [
    {
      ...nextEntry,
      taskKey: normalizedTaskKey,
    },
    ...entries.filter((entry) => entry.taskKey.trim().toUpperCase() !== normalizedTaskKey),
  ];
  return nextEntries.slice(0, MAX_TZPR_CACHED_RESULTS);
}
