import { NextResponse } from "next/server";

import { backendRequest, BackendRequestError } from "@/lib/backend";

// PUBLIC route — landing/demo contact formasi uchun (sessiya talab qilinmaydi).
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ success: false, error: "Noto'g'ri so'rov." }, { status: 400 });
  }

  const record = (body ?? {}) as Record<string, unknown>;
  const name = typeof record.name === "string" ? record.name.trim() : "";
  const phone = typeof record.phone === "string" ? record.phone.trim() : "";
  const role = typeof record.role === "string" ? record.role.trim() : "";
  const source = typeof record.source === "string" && record.source.trim() ? record.source.trim() : "landing";

  if (!name || !phone || !role) {
    return NextResponse.json(
      { success: false, error: "Ism familiya, telefon va kasb majburiy." },
      { status: 400 },
    );
  }

  try {
    const payload = await backendRequest<{ success: boolean; lead_id?: number }>("/api/leads", {
      method: "POST",
      body: { name, phone, role, source },
    });
    return NextResponse.json(payload);
  } catch (routeError) {
    if (routeError instanceof BackendRequestError) {
      return NextResponse.json({ success: false, error: routeError.message }, { status: routeError.status });
    }
    const message = routeError instanceof Error ? routeError.message : "Yuborib bo'lmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
