import type { ModuleRunErrorPayload } from "@/lib/types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function normalizeModuleRunErrorPayload(
  payload: unknown,
  fallback: {
    moduleKey: string;
    taskKey?: string | null;
    message: string;
  },
): ModuleRunErrorPayload {
  if (isRecord(payload)) {
    return {
      ...payload,
      success: false,
      module_key: typeof payload.module_key === "string" ? payload.module_key : fallback.moduleKey,
      task_key: typeof payload.task_key === "string" ? payload.task_key : fallback.taskKey || null,
      error:
        typeof payload.error === "string" && payload.error.trim()
          ? payload.error
          : typeof payload.error_message === "string"
            ? payload.error_message
            : fallback.message,
    } as ModuleRunErrorPayload;
  }

  return {
    success: false,
    module_key: fallback.moduleKey,
    task_key: fallback.taskKey || null,
    error: fallback.message,
    error_message: fallback.message,
  };
}

export function getModuleRunErrorMessage(payload: ModuleRunErrorPayload, fallback: string) {
  return (
    payload.error
    || payload.error_message
    || payload.status_banner?.message
    || fallback
  );
}
