import { NextResponse } from "next/server";

import { BackendRequestError, createTestcaseRunWithBackend } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";
import type { TestcaseCreateRunRequest } from "@/lib/types";

export async function POST(request: Request) {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json(
      { success: false, error: "Sessiya topilmadi yoki muddati tugagan." },
      { status: 401 },
    );
  }

  const role = session.auth.role;
  const hasRoleAccess =
    role === "super_admin" || role === "company_admin" || role === "user";

  if (!hasRoleAccess) {
    return NextResponse.json(
      { success: false, error: "Test Case Generator uchun ruxsat yo'q." },
      { status: 403 },
    );
  }

  try {
    const payload = (await request.json().catch(() => null)) as TestcaseCreateRunRequest | null;
    const taskKey = (payload?.task_key || "").trim().toUpperCase();

    const scopedToCustomer = role === "company_admin" || role === "user";
    const result = await createTestcaseRunWithBackend({
      task_key: taskKey,
      user_id: scopedToCustomer ? session.auth.user_id || null : null,
      company_id: scopedToCustomer ? session.auth.company_id || null : null,
      test_types: payload?.test_types || ["positive", "negative"],
      custom_context: payload?.custom_context || "",
      output_profile: payload?.output_profile ?? "ui",
    });

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
      error instanceof Error ? error.message : "Testcase run yaratishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
