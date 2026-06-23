import { NextResponse } from "next/server";

import { BackendRequestError, createTzprRunWithBackend } from "@/lib/backend";
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

  if (!hasRoleAccess) {
    return NextResponse.json(
      { success: false, error: "TZ-PR Checker uchun ruxsat yo'q." },
      { status: 403 },
    );
  }

  try {
    const payload = (await request.json().catch(() => null)) as TZPRCreateRunRequest | null;
    const taskKey = (payload?.task_key || "").trim().toUpperCase();

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
    if (error instanceof BackendRequestError) {
      const payload =
        error.payload && typeof error.payload === "object"
          ? error.payload
          : { success: false, error: error.message };
      return NextResponse.json(payload, { status: error.status || 500 });
    }
    const message =
      error instanceof Error ? error.message : "TZ-PR run yaratishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
