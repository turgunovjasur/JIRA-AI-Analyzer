import { NextResponse } from "next/server";

import { BackendRequestError, deleteMonitoringTaskWithBackend } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ taskKey: string }> },
) {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json(
      { success: false, error: "Sessiya topilmadi yoki muddati tugagan." },
      { status: 401 },
    );
  }

  const role = session.auth.role;
  if (role !== "super_admin" && role !== "company_admin") {
    return NextResponse.json(
      { success: false, error: "Task o'chirish uchun ruxsat yo'q." },
      { status: 403 },
    );
  }

  const { taskKey: rawTaskKey } = await context.params;
  const taskKey = (rawTaskKey || "").trim().toUpperCase();
  if (!taskKey) {
    return NextResponse.json(
      { success: false, error: "Task key bo'sh." },
      { status: 400 },
    );
  }

  const companyId = role === "company_admin" ? session.auth.company_id || null : null;

  try {
    const result = await deleteMonitoringTaskWithBackend({ taskKey, companyId });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof BackendRequestError) {
      const payload =
        error.payload && typeof error.payload === "object"
          ? error.payload
          : { success: false, error: error.message };
      return NextResponse.json(payload, { status: error.status || 500 });
    }
    const message =
      error instanceof Error ? error.message : "Task o'chirishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
