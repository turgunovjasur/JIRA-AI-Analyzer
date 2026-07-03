import { NextResponse } from "next/server";

import { backendRequest, BackendRequestError } from "@/lib/backend";

import { requireSuperAdminSession } from "../../_helpers";

type RouteContext = {
  params: Promise<{ jobId: string }>;
};

export async function DELETE(_request: Request, context: RouteContext) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  const params = await context.params;
  const jobId = Number(params.jobId);
  if (!Number.isInteger(jobId) || jobId <= 0) {
    return NextResponse.json({ success: false, error: "Job id noto'g'ri." }, { status: 400 });
  }

  try {
    const payload = await backendRequest<{ success: boolean; job_id: number }>(
      `/api/admin/jobs/${jobId}`,
      { method: "DELETE" },
    );
    return NextResponse.json(payload);
  } catch (routeError) {
    if (routeError instanceof BackendRequestError) {
      return NextResponse.json(
        { success: false, error: routeError.message },
        { status: routeError.status },
      );
    }
    const message =
      routeError instanceof Error ? routeError.message : "Job o'chirilmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
