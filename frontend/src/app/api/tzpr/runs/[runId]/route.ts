import { NextResponse } from "next/server";

import { getTzprRunWithBackend } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

type RouteContext = {
  params: Promise<{ runId: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
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
    const params = await context.params;
    const runId = (params.runId || "").trim();
    if (!runId) {
      return NextResponse.json(
        { success: false, error: "Run id majburiy." },
        { status: 400 },
      );
    }
    const result = await getTzprRunWithBackend(runId);
    return NextResponse.json(result);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "TZ-PR runni o'qishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
