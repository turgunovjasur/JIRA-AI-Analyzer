import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import { requireSuperAdminSession } from "../_helpers";

export async function POST(request: Request) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const payload = (await request.json().catch(() => null)) as {
      api_key_1?: string;
      api_key_2?: string;
      fallback_model?: string;
      key_freeze_minutes?: number;
      model?: string;
    } | null;

    const freezeMinutesRaw = Number(payload?.key_freeze_minutes ?? 10);
    const freezeMinutes = Number.isFinite(freezeMinutesRaw)
      ? Math.max(0, Math.trunc(freezeMinutesRaw))
      : 10;

    const updates: Array<[string, string]> = [
      ["gemini_default_model", (payload?.model || "").trim()],
      ["gemini_default_fallback_model", (payload?.fallback_model || "gemini-2.5-flash").trim()],
      ["gemini_key_freeze_minutes", String(freezeMinutes)],
    ];

    // Bo'sh qiymat yuborilsa, saqlangan kalitni o'chirmaymiz.
    const apiKey1 = (payload?.api_key_1 || "").trim();
    if (apiKey1) {
      updates.push(["gemini_default_api_key_1", apiKey1]);
    }

    const apiKey2 = (payload?.api_key_2 || "").trim();
    if (apiKey2) {
      updates.push(["gemini_default_api_key_2", apiKey2]);
    }

    const results = await Promise.all(
      updates.map(([key, value]) => callInternalRpc<boolean>("set_global_setting", [key, value])),
    );

    if (results.some((result) => !result)) {
      return NextResponse.json(
        { success: false, error: "Global AI defaultlarni saqlab bo'lmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "AI defaultlar saqlanmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
