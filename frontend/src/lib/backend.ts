import "server-only";

import { cookies } from "next/headers";

import { getBackendBaseUrl } from "@/lib/env";
import type {
  BackendHealth,
  BackendSessionResponse,
  LoginResponse,
  ModuleSettingsSaveRequest,
  ModuleSettingsView,
  MonitoringSnapshot,
  SessionResponse,
  SharedSettingsSaveRequest,
  SharedSettingsView,
  SystemSettingsSaveRequest,
  SystemSettingsView,
  SuperAdminOverview,
  TestCaseGenerateRequest,
  TestCaseGenerationResult,
  WebhookSettingsSaveRequest,
  WebhookSettingsView,
  TZPRCreateRunRequest,
  TZPRRunSnapshot,
} from "@/lib/types";

type BackendRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

const SESSION_COOKIE = "qa_backend_session";

async function buildBackendHeaders(existingHeaders?: HeadersInit) {
  const headers = new Headers(existingHeaders);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("X-Session-ID")) {
    try {
      const cookieStore = await cookies();
      const sessionToken = cookieStore.get(SESSION_COOKIE)?.value;
      if (sessionToken) {
        headers.set("X-Session-ID", sessionToken);
      }
    } catch {
      // Route handler/request context yo'q holatlarda cookie header qo'shilmaydi.
    }
  }
  return headers;
}

export async function backendRequest<T>(
  path: string,
  options: BackendRequestOptions = {},
) {
  const headers = await buildBackendHeaders(options.headers);
  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail =
      (payload && typeof payload === "object" && "detail" in payload
        ? payload.detail
        : null) || response.statusText;
    throw new Error(typeof detail === "string" ? detail : "Backend request failed");
  }

  return payload as T;
}

export function callInternalRpc<T>(
  op: string,
  args: unknown[] = [],
  kwargs: Record<string, unknown> = {},
) {
  return backendRequest<{ result: T }>("/api/internal/rpc", {
    method: "POST",
    body: { op, args, kwargs },
  }).then((payload) => payload.result);
}

export function loginWithBackend(username: string, password: string) {
  return backendRequest<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

export function getBackendSession(sessionToken: string) {
  return backendRequest<BackendSessionResponse>("/api/auth/me", {
    method: "GET",
    headers: {
      "X-Session-ID": sessionToken,
    },
  }).then((payload) => ({
    success: payload.success,
    auth: payload.auth,
    companyModules: payload.company_modules || {},
    expiresAt: payload.expires_at,
  }));
}

export function logoutBackendSession(sessionToken: string) {
  return backendRequest<{ success: boolean }>("/api/auth/logout", {
    method: "POST",
    headers: {
      "X-Session-ID": sessionToken,
    },
  });
}

export function getBackendHealth() {
  return backendRequest<BackendHealth>("/health", { method: "GET" });
}

export function getMonitoringSnapshot(params: {
  companyId?: number | null;
  status?: string;
}) {
  const search = new URLSearchParams();
  if (params.companyId) {
    search.set("company_id", String(params.companyId));
  }
  if (params.status) {
    search.set("status", params.status);
  }
  const query = search.toString();
  return backendRequest<MonitoringSnapshot>(
    `/api/monitoring/snapshot${query ? `?${query}` : ""}`,
    { method: "GET" },
  );
}

export function createTzprRunWithBackend(payload: TZPRCreateRunRequest & {
  company_id?: number | null;
  user_id?: number | null;
}) {
  return backendRequest<TZPRRunSnapshot>("/api/tzpr/runs", {
    method: "POST",
    body: payload,
  });
}

export function getTzprRunWithBackend(runId: string) {
  return backendRequest<TZPRRunSnapshot>(`/api/tzpr/runs/${encodeURIComponent(runId)}`, {
    method: "GET",
  });
}

export function generateTestCasesWithBackend(payload: TestCaseGenerateRequest & {
  company_id?: number | null;
  user_id?: number | null;
}) {
  return backendRequest<TestCaseGenerationResult>("/api/testcase/generate", {
    method: "POST",
    body: payload,
  });
}

export function readSharedSettingsWithBackend(payload: {
  company_id?: number | null;
  is_company_admin: boolean;
  user_id?: number | null;
}) {
  return backendRequest<{ data: Record<string, unknown> }>("/api/settings/api-keys/shared/read", {
    method: "POST",
    body: payload,
  });
}

export function saveSharedSettingsWithBackend(payload: {
  company_id?: number | null;
  is_company_admin: boolean;
  user_id?: number | null;
  data: SharedSettingsSaveRequest;
}) {
  return backendRequest<{ reasons?: string[]; success: boolean }>("/api/settings/api-keys/shared/save", {
    method: "POST",
    body: payload,
  });
}

export function readWebhookConfigWithBackend(payload: {
  company_id?: number | null;
}) {
  return backendRequest<WebhookSettingsView>("/api/settings/webhook/config/read", {
    method: "POST",
    body: payload,
  });
}

export function readModuleSettingsWithBackend(payload: {
  company_id?: number | null;
  user_id?: number | null;
}) {
  return backendRequest<ModuleSettingsView>("/api/settings/modules/config/read", {
    method: "POST",
    body: payload,
  });
}

export function saveModuleSettingsWithBackend(payload: {
  company_id?: number | null;
  user_id?: number | null;
  data: ModuleSettingsSaveRequest;
}) {
  return backendRequest<{ success: boolean }>("/api/settings/modules/config/save", {
    method: "POST",
    body: payload,
  });
}

export function saveWebhookConfigWithBackend(payload: {
  company_id?: number | null;
  data: WebhookSettingsSaveRequest;
}) {
  return backendRequest<{ success: boolean }>("/api/settings/webhook/config/save", {
    method: "POST",
    body: payload,
  });
}

export function readSystemConfigWithBackend(payload: {
  company_id?: number | null;
}) {
  return backendRequest<SystemSettingsView>("/api/settings/system/config/read", {
    method: "POST",
    body: payload,
  });
}

export function saveSystemConfigWithBackend(payload: {
  company_id?: number | null;
  data: SystemSettingsSaveRequest;
}) {
  return backendRequest<{ success: boolean }>("/api/settings/system/config/save", {
    method: "POST",
    body: payload,
  });
}

export function getSuperAdminOverview() {
  return backendRequest<SuperAdminOverview>("/api/super-admin/overview", {
    method: "GET",
  });
}
