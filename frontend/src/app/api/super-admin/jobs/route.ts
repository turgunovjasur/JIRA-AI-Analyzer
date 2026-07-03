import { NextResponse } from "next/server";

import { backendRequest, BackendRequestError } from "@/lib/backend";

import { requireSuperAdminSession } from "../_helpers";

type AdminJobsResponse = {
  success: boolean;
  jobs: Array<Record<string, unknown>>;
  total: number;
  limit: number;
  offset: number;
};

export async function GET(request: Request) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const url = new URL(request.url);
    const query = new URLSearchParams();
    const status = (url.searchParams.get("status") || "").trim();
    const companyId = (url.searchParams.get("company_id") || "").trim();
    const limit = (url.searchParams.get("limit") || "").trim();
    const offset = (url.searchParams.get("offset") || "").trim();
    if (status) query.set("status", status);
    if (companyId) query.set("company_id", companyId);
    if (limit) query.set("limit", limit);
    if (offset) query.set("offset", offset);

    const suffix = query.toString() ? `?${query.toString()}` : "";
    const payload = await backendRequest<AdminJobsResponse>(`/api/admin/jobs${suffix}`, {
      method: "GET",
    });
    return NextResponse.json(payload);
  } catch (routeError) {
    if (routeError instanceof BackendRequestError) {
      return NextResponse.json(
        { success: false, error: routeError.message },
        { status: routeError.status },
      );
    }
    const message =
      routeError instanceof Error ? routeError.message : "Job ro'yxatini o'qib bo'lmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
