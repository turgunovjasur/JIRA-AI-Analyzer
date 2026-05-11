import { NextResponse } from "next/server";

import { getDefaultRouteForRole } from "@/lib/app-routes";
import { loginWithBackend } from "@/lib/backend";
import { writeSessionToken } from "@/lib/session";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as {
      password?: string;
      username?: string;
    };

    const username = (payload.username || "").trim();
    const password = payload.password || "";

    if (!username || !password) {
      return NextResponse.json(
        { success: false, error: "Login va parol majburiy." },
        { status: 400 },
      );
    }

    const loginResult = await loginWithBackend(username, password);
    if (!loginResult.success || !loginResult.auth || !loginResult.session_token) {
      return NextResponse.json(
        {
          success: false,
          error: loginResult.error_message || "Login muvaffaqiyatsiz tugadi.",
        },
        { status: 401 },
      );
    }

    await writeSessionToken(loginResult.session_token);

    return NextResponse.json({
      success: true,
      redirectTo: getDefaultRouteForRole(loginResult.auth.role),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Backend login request xatosi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
