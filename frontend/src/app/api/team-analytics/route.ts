import { NextResponse } from "next/server";
import { backendRequest, BackendRequestError } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

async function proxy(request: Request, method: "GET" | "PUT") {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth.logged_in) {
    return NextResponse.json({ error: "Sessiya topilmadi" }, { status: 401 });
  }
  if (session.auth.role !== "company_admin") {
    return NextResponse.json({ error: "Company admin huquqi kerak" }, { status: 403 });
  }
  try {
    const params = new URL(request.url).searchParams;
    const query = new URLSearchParams();
    for (const key of ["limit", "offset", "assignee_id", "jira_source"]) {
      if (params.has(key)) query.set(key, params.get(key)!);
    }
    const path = method === "GET" ? `/api/team-analytics/snapshot?${query}` : "/api/team-analytics/settings";
    let body: unknown;
    if (method === "PUT") {
      try { body = await request.json(); }
      catch { return NextResponse.json({ error: "JSON noto'g'ri" }, { status: 400 }); }
    }
    const result = await backendRequest(path, { method, body });
    return NextResponse.json(result);
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "Team Analytics xatosi" },
      { status: error instanceof BackendRequestError ? error.status : 500 });
  }
}

export const GET = (request: Request) => proxy(request, "GET");
export const PUT = (request: Request) => proxy(request, "PUT");
