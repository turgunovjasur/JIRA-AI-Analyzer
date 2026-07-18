// Next.js instrumentation — har qanday server-side xatoni (route handler,
// server component, Server Action, jumladan "Failed to find Server Action")
// kontekst bilan stdout'ga yozadi. Bu loglar `docker logs frontend` da ko'rinadi.
// Hujjat: https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation

type RequestErrorContext = {
  routerKind?: string;
  routePath?: string;
  routeType?: string;
  renderSource?: string;
};

type ErroredRequest = {
  path?: string;
  method?: string;
  headers?: Record<string, string | string[] | undefined> | Headers;
};

function headerValue(headers: ErroredRequest["headers"], name: string): string {
  if (!headers) return "";
  if (headers instanceof Headers) return headers.get(name) || "";
  const raw = headers[name] ?? headers[name.toLowerCase()];
  return Array.isArray(raw) ? raw.join(",") : String(raw ?? "");
}

export async function onRequestError(
  err: unknown,
  request: ErroredRequest,
  context: RequestErrorContext,
) {
  const message = err instanceof Error ? err.message : String(err);
  const digest =
    err && typeof err === "object" && "digest" in err ? String((err as { digest?: unknown }).digest) : "";
  const requestId = headerValue(request?.headers, "x-request-id");
  const method = request?.method || "?";
  const path = request?.path || context?.routePath || "?";

  console.error(
    `[FE-ERR] ${method} ${path} -> ${message}` +
      (digest ? ` digest=${digest}` : "") +
      (requestId ? ` reqId=${requestId}` : "") +
      ` route=${context?.routeType || "?"}/${context?.renderSource || "?"}`,
  );
  if (err instanceof Error && err.stack) {
    console.error(err.stack);
  }
}
