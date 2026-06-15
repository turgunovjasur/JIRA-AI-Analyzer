import { NextResponse } from "next/server";

import { generateTestCasesWithBackend } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

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
    const payload = (await request.json()) as {
      custom_context?: string;
      include_pr?: boolean;
      task_key?: string;
      test_types?: string[];
      use_smart_patch?: boolean;
    };

    const taskKey = (payload.task_key || "").trim().toUpperCase();
    if (!taskKey) {
      return NextResponse.json(
        { success: false, error: "Task key majburiy." },
        { status: 400 },
      );
    }

    const scopedToCustomer = role === "company_admin" || role === "user";
    const result = await generateTestCasesWithBackend({
      task_key: taskKey,
      user_id: scopedToCustomer ? session.auth.user_id || null : null,
      company_id: scopedToCustomer ? session.auth.company_id || null : null,
      include_pr: payload.include_pr ?? true,
      use_smart_patch: payload.use_smart_patch ?? false,
      test_types: payload.test_types || ["positive", "negative"],
      custom_context: payload.custom_context || "",
    });

    return NextResponse.json(result);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Testcase backend request xatosi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
