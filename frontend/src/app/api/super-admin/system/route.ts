import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import { requireSuperAdminSession } from "../_helpers";

type SuperAdminSystemPayload = {
  ai_max_retries: number;
  key_freeze_duration: number;
  db_busy_timeout: number;
  db_connection_timeout: number;
  http_timeout: number;
  executor_timeout: number;
};

const SYSTEM_DEFAULTS: SuperAdminSystemPayload = {
  ai_max_retries: 3,
  key_freeze_duration: 600,
  db_busy_timeout: 30000,
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
      aiMaxRetries,
      keyFreezeDuration,
      dbBusyTimeout,
      dbConnectionTimeout,
      httpTimeout,
      executorTimeout,
    ] = await Promise.all([
      callInternalRpc<string>("get_global_setting", ["queue_ai_max_retries", String(SYSTEM_DEFAULTS.ai_max_retries)]),
      callInternalRpc<string>("get_global_setting", ["queue_key_freeze_duration_sec", String(SYSTEM_DEFAULTS.key_freeze_duration)]),
      callInternalRpc<string>("get_global_setting", ["queue_db_busy_timeout_ms", String(SYSTEM_DEFAULTS.db_busy_timeout)]),
      callInternalRpc<string>("get_global_setting", ["queue_db_connection_timeout_sec", String(SYSTEM_DEFAULTS.db_connection_timeout)]),
      callInternalRpc<string>("get_global_setting", ["queue_http_timeout_sec", String(SYSTEM_DEFAULTS.http_timeout)]),
      callInternalRpc<string>("get_global_setting", ["queue_executor_timeout_sec", String(SYSTEM_DEFAULTS.executor_timeout)]),
    ]);

    return NextResponse.json({
      success: true,
      data: {
        ai_max_retries: parsePositiveInt(aiMaxRetries, SYSTEM_DEFAULTS.ai_max_retries),
        key_freeze_duration: parsePositiveInt(keyFreezeDuration, SYSTEM_DEFAULTS.key_freeze_duration),
        db_busy_timeout: parsePositiveInt(dbBusyTimeout, SYSTEM_DEFAULTS.db_busy_timeout),
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
      ai_max_retries: parsePositiveInt(payload.ai_max_retries, SYSTEM_DEFAULTS.ai_max_retries),
      key_freeze_duration: parsePositiveInt(payload.key_freeze_duration, SYSTEM_DEFAULTS.key_freeze_duration),
      db_busy_timeout: parsePositiveInt(payload.db_busy_timeout, SYSTEM_DEFAULTS.db_busy_timeout),
      db_connection_timeout: parsePositiveInt(payload.db_connection_timeout, SYSTEM_DEFAULTS.db_connection_timeout),
      http_timeout: parsePositiveInt(payload.http_timeout, SYSTEM_DEFAULTS.http_timeout),
      executor_timeout: parsePositiveInt(payload.executor_timeout, SYSTEM_DEFAULTS.executor_timeout),
    };

    const updates: Array<[string, string]> = [
      ["queue_ai_max_retries", String(data.ai_max_retries)],
      ["queue_key_freeze_duration_sec", String(data.key_freeze_duration)],
      ["queue_db_busy_timeout_ms", String(data.db_busy_timeout)],
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
