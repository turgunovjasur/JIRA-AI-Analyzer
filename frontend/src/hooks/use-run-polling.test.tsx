import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_RUN_POLL_INTERVAL_MS,
  useRunPolling,
  type RunResultBase,
  type RunSnapshotBase,
  type UseRunPollingOptions,
} from "@/hooks/use-run-polling";
import { getRecentRunsStorageKey } from "@/lib/use-recent-runs";

type TestResult = RunResultBase;
type TestSnapshot = RunSnapshotBase<TestResult>;

const MODULE_KEY = "test_module";
const API_BASE = "/api/tzpr";

function isTerminalRunState(value?: string | null) {
  return ["completed", "manual_review", "blocked", "failed"].includes((value || "").toLowerCase());
}

function jsonResponse(payload: unknown, init?: { ok?: boolean; status?: number }) {
  return {
    ok: init?.ok ?? true,
    status: init?.status ?? 200,
    json: async () => payload,
  } as Response;
}

function makeSnapshot(overrides?: Partial<TestSnapshot>): TestSnapshot {
  return {
    run_id: "RUN-1",
    task_key: "DEV-1",
    run_state: "running",
    finished_at: null,
    error_message: null,
    final_result: null,
    ...overrides,
  };
}

function makeOptions(
  overrides?: Partial<UseRunPollingOptions<TestResult, TestSnapshot>>,
): UseRunPollingOptions<TestResult, TestSnapshot> {
  return {
    moduleKey: MODULE_KEY,
    apiBasePath: API_BASE,
    taskKey: "DEV-1",
    isTerminalRunState,
    deriveResultError: (result) => (result.error_message ? result.error_message : null),
    getSnapshotErrorMessage: (snapshot) => snapshot.error_message?.trim() || null,
    pollErrorMessage: "Polling xatosi.",
    pollFailureMessage: "Polling vaqtida xato.",
    reopenFailureMessage: "Reopen xatosi.",
    ...overrides,
  };
}

const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();

function runsFetchCalls() {
  return fetchMock.mock.calls.filter(([url]) => String(url).includes("/runs/"));
}

beforeEach(() => {
  vi.useFakeTimers();
  window.localStorage.clear();
  window.sessionStorage.clear();
  fetchMock.mockReset();
  // start-status har mount'da chaqiriladi — default javob.
  fetchMock.mockImplementation(async (url) => {
    if (String(url).endsWith("/start-status")) {
      return jsonResponse({
        module_key: MODULE_KEY,
        blocked: false,
        level: "info",
        message: "",
        gemini_source: "user",
      });
    }
    throw new Error(`Unexpected fetch: ${String(url)}`);
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("useRunPolling", () => {
  it("start-status'ni mount'da yuklaydi", async () => {
    const { result } = renderHook(() => useRunPolling<TestResult, TestSnapshot>(makeOptions()));

    await act(async () => {});

    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/start-status`, { cache: "no-store" });
    expect(result.current.startStatus?.module_key).toBe(MODULE_KEY);
  });

  it("terminal bo'lmagan run'ni har intervalda poll qiladi va terminalda to'xtaydi", async () => {
    const runningSnapshot = makeSnapshot();
    const completedSnapshot = makeSnapshot({
      run_state: "completed",
      finished_at: "2026-07-03T10:00:00Z",
      final_result: { task_key: "DEV-1", error_message: null },
    });
    const runPayloads = [runningSnapshot, completedSnapshot];
    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith("/start-status")) {
        return jsonResponse({ module_key: MODULE_KEY });
      }
      if (String(url) === `${API_BASE}/runs/RUN-1`) {
        return jsonResponse(runPayloads.shift() ?? completedSnapshot);
      }
      throw new Error(`Unexpected fetch: ${String(url)}`);
    });

    const { result } = renderHook(() => useRunPolling<TestResult, TestSnapshot>(makeOptions()));
    await act(async () => {});

    act(() => {
      result.current.applyRunSnapshot(runningSnapshot);
    });
    expect(result.current.runInProgress).toBe(true);
    expect(runsFetchCalls()).toHaveLength(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RUN_POLL_INTERVAL_MS);
    });
    expect(runsFetchCalls()).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/runs/RUN-1`, { cache: "no-store" });
    expect(result.current.runInProgress).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RUN_POLL_INTERVAL_MS);
    });
    expect(runsFetchCalls()).toHaveLength(2);
    expect(result.current.result?.task_key).toBe("DEV-1");
    expect(result.current.runInProgress).toBe(false);

    // Terminal holatdan keyin polling to'xtashi kerak.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RUN_POLL_INTERVAL_MS * 3);
    });
    expect(runsFetchCalls()).toHaveLength(2);
  });

  it("allaqachon resolved snapshot uchun polling boshlamaydi", async () => {
    const { result } = renderHook(() => useRunPolling<TestResult, TestSnapshot>(makeOptions()));
    await act(async () => {});

    act(() => {
      result.current.applyRunSnapshot(
        makeSnapshot({ run_state: "completed", final_result: { task_key: "DEV-1" } }),
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RUN_POLL_INTERVAL_MS * 3);
    });
    expect(runsFetchCalls()).toHaveLength(0);
    expect(result.current.runInProgress).toBe(false);
  });

  it("poll javobi ok bo'lmasa error state'ga xabar yozadi", async () => {
    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith("/start-status")) {
        return jsonResponse({ module_key: MODULE_KEY });
      }
      return jsonResponse({}, { ok: false, status: 500 });
    });

    const { result } = renderHook(() => useRunPolling<TestResult, TestSnapshot>(makeOptions()));
    await act(async () => {});

    act(() => {
      result.current.applyRunSnapshot(makeSnapshot());
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RUN_POLL_INTERVAL_MS);
    });

    expect(result.current.error).toBe("Polling xatosi.");
    // Xato bo'lsa ham run resolved bo'lmagani uchun polling davom etadi.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RUN_POLL_INTERVAL_MS);
    });
    expect(runsFetchCalls()).toHaveLength(2);
  });

  it("applyRunSnapshot final_result'siz snapshotda getSnapshotErrorMessage natijasini qo'llaydi", async () => {
    const { result } = renderHook(() => useRunPolling<TestResult, TestSnapshot>(makeOptions()));
    await act(async () => {});

    act(() => {
      result.current.applyRunSnapshot(makeSnapshot({ error_message: "  AI xatosi  " }));
    });
    expect(result.current.error).toBe("AI xatosi");

    // null qaytsa error state'ga tegilmaydi.
    act(() => {
      result.current.applyRunSnapshot(makeSnapshot({ error_message: null }));
    });
    expect(result.current.error).toBe("AI xatosi");
  });

  it("reopenRun 404 bo'lsa recent ro'yxatdan olib tashlaydi va error yozadi", async () => {
    const entry = { run_id: "RUN-404", task_key: "DEV-9", saved_at: Date.now() };
    window.localStorage.setItem(getRecentRunsStorageKey(MODULE_KEY), JSON.stringify([entry]));

    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith("/start-status")) {
        return jsonResponse({ module_key: MODULE_KEY });
      }
      if (String(url) === `${API_BASE}/runs/RUN-404`) {
        return jsonResponse({ error: "Run topilmadi." }, { ok: false, status: 404 });
      }
      throw new Error(`Unexpected fetch: ${String(url)}`);
    });

    const onBeforeReopen = vi.fn();
    const { result } = renderHook(() =>
      useRunPolling<TestResult, TestSnapshot>(makeOptions({ onBeforeReopen })),
    );
    await act(async () => {});
    expect(result.current.recent).toHaveLength(1);

    await act(async () => {
      await result.current.reopenRun(entry);
    });

    expect(onBeforeReopen).toHaveBeenCalledWith(entry);
    expect(result.current.error).toBe("Run topilmadi.");
    expect(result.current.recent).toHaveLength(0);
    expect(result.current.submitting).toBe(false);
  });

  it("reopenRun muvaffaqiyatli snapshotni qo'llaydi", async () => {
    const entry = { run_id: "RUN-1", task_key: "DEV-1", saved_at: Date.now() };
    const snapshot = makeSnapshot({
      run_state: "completed",
      final_result: { task_key: "DEV-1" },
    });
    fetchMock.mockImplementation(async (url) => {
      if (String(url).endsWith("/start-status")) {
        return jsonResponse({ module_key: MODULE_KEY });
      }
      if (String(url) === `${API_BASE}/runs/RUN-1`) {
        return jsonResponse(snapshot);
      }
      throw new Error(`Unexpected fetch: ${String(url)}`);
    });

    const { result } = renderHook(() => useRunPolling<TestResult, TestSnapshot>(makeOptions()));
    await act(async () => {});

    await act(async () => {
      await result.current.reopenRun(entry);
    });

    expect(result.current.activeRun?.run_id).toBe("RUN-1");
    expect(result.current.result?.task_key).toBe("DEV-1");
    expect(result.current.runInProgress).toBe(false);
  });
});
