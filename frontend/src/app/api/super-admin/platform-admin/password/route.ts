import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import { requireSuperAdminSession } from "../../_helpers";

export async function POST(request: Request) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const payload = (await request.json().catch(() => null)) as {
      confirm_password?: string;
      password?: string;
      username?: string;
    } | null;

    const username = (payload?.username || session.auth.user_name || "").trim().toLowerCase();
    const password = payload?.password || "";
    const confirmPassword = payload?.confirm_password || "";

    if (!username) {
      return NextResponse.json(
        { success: false, error: "Super admin username topilmadi." },
        { status: 400 },
      );
    }

    if (password.length < 8) {
      return NextResponse.json(
        { success: false, error: "Parol kamida 8 ta belgi bo'lishi kerak." },
        { status: 400 },
      );
    }

    if (password !== confirmPassword) {
      return NextResponse.json(
        { success: false, error: "Parollar mos kelmadi." },
        { status: 400 },
      );
    }

    const success = await callInternalRpc<boolean>("save_platform_admin", [username, password, true]);
    if (!success) {
      return NextResponse.json(
        { success: false, error: "Platform admin parolini saqlab bo'lmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Platform admin paroli saqlanmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
