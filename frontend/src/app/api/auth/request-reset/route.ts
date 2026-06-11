import { NextResponse } from "next/server";

import { backendRequest } from "@/lib/backend";

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as { username?: string };
    const username = (payload.username || "").trim();
    if (!username) {
      return NextResponse.json({ success: false, error: "Username kiritilmagan." }, { status: 400 });
    }
    await backendRequest("/api/auth/request-reset", {
      method: "POST",
      body: { username },
    });
    return NextResponse.json({ success: true });
  } catch {
    return NextResponse.json({ success: true });
  }
}
