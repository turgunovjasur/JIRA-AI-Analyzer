import { NextResponse } from "next/server";

import { BackendRequestError, getTestcaseStartStatusWithBackend } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

export async function GET() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json(
      { success: false, error: "Sessiya topilmadi yoki muddati tugagan." },
      { status: 401 },
    );
  }

  const role = session.auth.role;
  if (!(role === "super_admin" || role === "company_admin" || role === "user")) {
    return NextResponse.json({ success: false, error: "Ruxsat yo'q." }, { status: 403 });
  }

  try {
    const result = await getTestcaseStartStatusWithBackend({
      user_id: session.auth.user_id || null,
      company_id: session.auth.company_id || null,
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
    const message = error instanceof Error ? error.message : "Start-status xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
