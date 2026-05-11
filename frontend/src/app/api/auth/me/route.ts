import { NextResponse } from "next/server";

import { getBackendSession } from "@/lib/backend";
import { clearSession, readSessionToken } from "@/lib/session";

export async function GET() {
  const sessionToken = await readSessionToken();
  if (!sessionToken) {
    return NextResponse.json({ success: false, error: "Session topilmadi." }, { status: 401 });
  }

  try {
    const session = await getBackendSession(sessionToken);
    return NextResponse.json(session);
  } catch (error) {
    await clearSession();
    const message =
      error instanceof Error ? error.message : "Backend session validation xatosi.";
    return NextResponse.json({ success: false, error: message }, { status: 401 });
  }
}
