import { NextResponse } from "next/server";

import { logoutBackendSession } from "@/lib/backend";
import { clearSession, readSessionToken } from "@/lib/session";

export async function POST() {
  const sessionToken = await readSessionToken();
  if (sessionToken) {
    try {
      await logoutBackendSession(sessionToken);
    } catch {
      // Cookie tozalanishi logout uchun yetarli fallback.
    }
  }
  await clearSession();
  return NextResponse.json({ success: true });
}
