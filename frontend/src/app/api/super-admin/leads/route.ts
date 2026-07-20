import { NextResponse } from "next/server";

import { backendRequest, BackendRequestError } from "@/lib/backend";

import { requireSuperAdminSession } from "../_helpers";

type LeadsResponse = {
  success: boolean;
  leads: Array<Record<string, unknown>>;
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
    const limit = (url.searchParams.get("limit") || "").trim();
    const offset = (url.searchParams.get("offset") || "").trim();
    if (limit) query.set("limit", limit);
    if (offset) query.set("offset", offset);

    const suffix = query.toString() ? `?${query.toString()}` : "";
    const payload = await backendRequest<LeadsResponse>(`/api/leads${suffix}`, { method: "GET" });
    return NextResponse.json(payload);
  } catch (routeError) {
    if (routeError instanceof BackendRequestError) {
      return NextResponse.json(
        { success: false, error: routeError.message },
        { status: routeError.status },
      );
    }
    const message = routeError instanceof Error ? routeError.message : "Lidlarni o'qib bo'lmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
