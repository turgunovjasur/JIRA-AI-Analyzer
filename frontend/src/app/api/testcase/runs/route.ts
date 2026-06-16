import { NextResponse } from "next/server";

import { createTestcaseRunWithBackend } from "@/lib/backend";
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
  const hasModuleAccess =
    role === "super_admin" || Boolean(session.companyModules?.testcase_generator);

  if (!hasRoleAccess || !hasModuleAccess) {
    return NextResponse.json(
      { success: false, error: "Test Case Generator uchun ruxsat yo'q." },
      { status: 403 },
    );
  }

  try {
    const payload = (await request.json().catch(() => null)) as TestcaseCreateRunRequest | null;
    const taskKey = (payload?.task_key || "").trim().toUpperCase();
    if (!taskKey) {
      return NextResponse.json(
        { success: false, error: "Task key majburiy." },
        { status: 400 },
      );
    }

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
    const message =
      error instanceof Error ? error.message : "Testcase run yaratishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
