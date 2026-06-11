import { NextResponse } from "next/server";

import { createTzprRunWithBackend } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";
import type { TZPRCreateRunRequest } from "@/lib/types";

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
    role === "super_admin" || Boolean(session.companyModules?.tz_pr_checker);

  if (!hasRoleAccess || !hasModuleAccess) {
    return NextResponse.json(
      { success: false, error: "TZ-PR Checker uchun ruxsat yo'q." },
      { status: 403 },
    );
  }

  try {
    const payload = (await request.json().catch(() => null)) as TZPRCreateRunRequest | null;
    const taskKey = (payload?.task_key || "").trim().toUpperCase();
    if (!taskKey) {
      return NextResponse.json(
        { success: false, error: "Task key majburiy." },
        { status: 400 },
      );
    }

    const result = await createTzprRunWithBackend({
      task_key: taskKey,
      user_id: session.auth.user_id || null,
      company_id: session.auth.company_id || null,
      max_files: payload?.max_files ?? null,
      output_profile: payload?.output_profile ?? "ui",
      show_full_diff: payload?.show_full_diff ?? true,
      use_smart_patch: payload?.use_smart_patch ?? null,
    });

    return NextResponse.json(result);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "TZ-PR run yaratishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
