import { NextResponse } from "next/server";

import { backendRequest, BackendRequestError } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

type ManualTriggerResponse = {
  status?: string;
  task_key?: string;
  company_id?: number;
  message?: string;
  testcase_triggered?: boolean;
};

function isValidTaskKey(value: string) {
  return /^[A-Z][A-Z0-9]+-\d+$/.test(value) || /^\d+$/.test(value);
}

export async function POST(request: Request) {
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
      { success: false, error: "Manual trigger faqat admin rollar uchun." },
      { status: 403 },
    );
  }

  if (role === "company_admin" && !session.companyModules?.monitoring) {
    return NextResponse.json(
      { success: false, error: "Monitoring moduli yopiq." },
      { status: 403 },
    );
  }

  const payload = (await request.json().catch(() => null)) as { task_key?: string } | null;
  const taskKey = (payload?.task_key || "").trim().toUpperCase();
  if (!taskKey) {
    return NextResponse.json(
      { success: false, error: "Task key kiriting." },
      { status: 400 },
    );
  }
  if (!isValidTaskKey(taskKey)) {
    return NextResponse.json(
      { success: false, error: "Task key to'liq bo'lishi kerak: DEV-1234." },
      { status: 400 },
    );
  }

  try {
    const result = await backendRequest<ManualTriggerResponse>(
      `/manual/check/${encodeURIComponent(taskKey)}`,
      { method: "POST" },
    );
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof BackendRequestError) {
      const payload =
        error.payload && typeof error.payload === "object"
          ? error.payload
          : { success: false, error: error.message };
      return NextResponse.json(payload, { status: error.status || 500 });
    }

    const message = error instanceof Error ? error.message : "Manual trigger ishga tushmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
