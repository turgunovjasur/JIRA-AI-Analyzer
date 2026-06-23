import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import { requireSuperAdminSession } from "../_helpers";

type SuperAdminSystemPayload = {
  task_wait_timeout: number;
  checker_testcase_delay: number;
  blocked_retry_delay: number;
  gemini_min_interval: number;
  blocked_check_interval: number;
  gemini_max_retries: number;
  key_freeze_duration: number;
  db_connection_timeout: number;
  http_timeout: number;
  executor_timeout: number;
};

const SYSTEM_DEFAULTS: SuperAdminSystemPayload = {
  task_wait_timeout: 60,
  checker_testcase_delay: 15,
  blocked_retry_delay: 5,
  gemini_min_interval: 6,
  blocked_check_interval: 30,
  gemini_max_retries: 3,
  key_freeze_duration: 600,
  db_connection_timeout: 30,
  http_timeout: 30,
  executor_timeout: 120,
};

function parsePositiveInt(value: unknown, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  const intValue = Math.trunc(parsed);
  return intValue > 0 ? intValue : fallback;
}

export async function GET() {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const [
      taskWaitTimeout,
      checkerTestcaseDelay,
      blockedRetryDelay,
      geminiMinInterval,
      blockedCheckInterval,
      geminiMaxRetries,
      keyFreezeDuration,
      dbConnectionTimeout,
      httpTimeout,
      executorTimeout,
    ] = await Promise.all([
      callInternalRpc<string>("get_global_setting", ["queue_task_wait_timeout_sec", String(SYSTEM_DEFAULTS.task_wait_timeout)]),
      callInternalRpc<string>("get_global_setting", ["queue_checker_testcase_delay_sec", String(SYSTEM_DEFAULTS.checker_testcase_delay)]),
      callInternalRpc<string>("get_global_setting", ["queue_blocked_retry_delay_min", String(SYSTEM_DEFAULTS.blocked_retry_delay)]),
      callInternalRpc<string>("get_global_setting", ["queue_gemini_min_interval_sec", String(SYSTEM_DEFAULTS.gemini_min_interval)]),
      callInternalRpc<string>("get_global_setting", ["queue_blocked_check_interval_sec", String(SYSTEM_DEFAULTS.blocked_check_interval)]),
      callInternalRpc<string>("get_global_setting", ["queue_gemini_max_retries", String(SYSTEM_DEFAULTS.gemini_max_retries)]),
      callInternalRpc<string>("get_global_setting", ["queue_key_freeze_duration_sec", String(SYSTEM_DEFAULTS.key_freeze_duration)]),
      callInternalRpc<string>("get_global_setting", ["queue_db_connection_timeout_sec", String(SYSTEM_DEFAULTS.db_connection_timeout)]),
      callInternalRpc<string>("get_global_setting", ["queue_http_timeout_sec", String(SYSTEM_DEFAULTS.http_timeout)]),
      callInternalRpc<string>("get_global_setting", ["queue_executor_timeout_sec", String(SYSTEM_DEFAULTS.executor_timeout)]),
    ]);

    return NextResponse.json({
      success: true,
      data: {
        task_wait_timeout: parsePositiveInt(taskWaitTimeout, SYSTEM_DEFAULTS.task_wait_timeout),
        checker_testcase_delay: parsePositiveInt(checkerTestcaseDelay, SYSTEM_DEFAULTS.checker_testcase_delay),
        blocked_retry_delay: parsePositiveInt(blockedRetryDelay, SYSTEM_DEFAULTS.blocked_retry_delay),
        gemini_min_interval: parsePositiveInt(geminiMinInterval, SYSTEM_DEFAULTS.gemini_min_interval),
        blocked_check_interval: parsePositiveInt(blockedCheckInterval, SYSTEM_DEFAULTS.blocked_check_interval),
        gemini_max_retries: parsePositiveInt(geminiMaxRetries, SYSTEM_DEFAULTS.gemini_max_retries),
        key_freeze_duration: parsePositiveInt(keyFreezeDuration, SYSTEM_DEFAULTS.key_freeze_duration),
        db_connection_timeout: parsePositiveInt(dbConnectionTimeout, SYSTEM_DEFAULTS.db_connection_timeout),
        http_timeout: parsePositiveInt(httpTimeout, SYSTEM_DEFAULTS.http_timeout),
        executor_timeout: parsePositiveInt(executorTimeout, SYSTEM_DEFAULTS.executor_timeout),
      } satisfies SuperAdminSystemPayload,
    });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "System sozlamalarini o'qib bo'lmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const payload = (await request.json().catch(() => null)) as Partial<SuperAdminSystemPayload> | null;
    if (!payload || typeof payload !== "object") {
      return NextResponse.json({ success: false, error: "Noto'g'ri system payload." }, { status: 400 });
    }

    const data: SuperAdminSystemPayload = {
      task_wait_timeout: parsePositiveInt(payload.task_wait_timeout, SYSTEM_DEFAULTS.task_wait_timeout),
      checker_testcase_delay: parsePositiveInt(payload.checker_testcase_delay, SYSTEM_DEFAULTS.checker_testcase_delay),
      blocked_retry_delay: parsePositiveInt(payload.blocked_retry_delay, SYSTEM_DEFAULTS.blocked_retry_delay),
      gemini_min_interval: parsePositiveInt(payload.gemini_min_interval, SYSTEM_DEFAULTS.gemini_min_interval),
      blocked_check_interval: parsePositiveInt(payload.blocked_check_interval, SYSTEM_DEFAULTS.blocked_check_interval),
      gemini_max_retries: parsePositiveInt(payload.gemini_max_retries, SYSTEM_DEFAULTS.gemini_max_retries),
      key_freeze_duration: parsePositiveInt(payload.key_freeze_duration, SYSTEM_DEFAULTS.key_freeze_duration),
      db_connection_timeout: parsePositiveInt(payload.db_connection_timeout, SYSTEM_DEFAULTS.db_connection_timeout),
      http_timeout: parsePositiveInt(payload.http_timeout, SYSTEM_DEFAULTS.http_timeout),
      executor_timeout: parsePositiveInt(payload.executor_timeout, SYSTEM_DEFAULTS.executor_timeout),
    };

    const updates: Array<[string, string]> = [
      ["queue_task_wait_timeout_sec", String(data.task_wait_timeout)],
      ["queue_checker_testcase_delay_sec", String(data.checker_testcase_delay)],
      ["queue_blocked_retry_delay_min", String(data.blocked_retry_delay)],
      ["queue_gemini_min_interval_sec", String(data.gemini_min_interval)],
      ["queue_blocked_check_interval_sec", String(data.blocked_check_interval)],
      ["queue_gemini_max_retries", String(data.gemini_max_retries)],
      ["queue_key_freeze_duration_sec", String(data.key_freeze_duration)],
      ["queue_db_connection_timeout_sec", String(data.db_connection_timeout)],
      ["queue_http_timeout_sec", String(data.http_timeout)],
      ["queue_executor_timeout_sec", String(data.executor_timeout)],
    ];

    const results = await Promise.all(
      updates.map(([key, value]) => callInternalRpc<boolean>("set_global_setting", [key, value])),
    );
    if (results.some((result) => !result)) {
      return NextResponse.json({ success: false, error: "System sozlamalar saqlanmadi." }, { status: 400 });
    }

    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "System sozlamalar saqlanmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
