import { NextResponse } from "next/server";

import { backendRequest } from "@/lib/backend";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as { new_password?: string; token?: string };
    const token = (payload.token || "").trim();
    const newPassword = payload.new_password || "";
    if (!token || !newPassword) {
      return NextResponse.json(
        { success: false, error: "Token va yangi parol majburiy." },
        { status: 400 },
      );
    }
    const result = await backendRequest<{ success: boolean }>("/api/auth/password-reset", {
      method: "POST",
      body: { token, new_password: newPassword },
    });
    return NextResponse.json({ success: Boolean(result?.success) });
  } catch {
    return NextResponse.json({ success: false }, { status: 500 });
  }
}
