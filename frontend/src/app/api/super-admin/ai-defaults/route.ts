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
      api_key_2_clear?: boolean;
      key_freeze_minutes?: number;
      agent1_primary_model?: string;
      agent1_fallback_model?: string;
      agent2_primary_model?: string;
      agent2_fallback_model?: string;
      agent3_primary_model?: string;
      agent3_fallback_model?: string;
      testcase_agent1_primary_model?: string;
      testcase_agent1_fallback_model?: string;
      testcase_agent2_primary_model?: string;
      testcase_agent2_fallback_model?: string;
      testcase_agent3_primary_model?: string;
      testcase_agent3_fallback_model?: string;
    } | null;

    const freezeMinutesRaw = Number(payload?.key_freeze_minutes ?? 10);
    const freezeMinutes = Number.isFinite(freezeMinutesRaw)
      ? Math.max(0, Math.trunc(freezeMinutesRaw))
      : 10;

    const updates: Array<[string, string]> = [
      ["gemini_key_freeze_minutes", String(freezeMinutes)],
      ["checker_agent1_primary_model", (payload?.agent1_primary_model || "").trim()],
      ["checker_agent1_fallback_model", (payload?.agent1_fallback_model || "").trim()],
      ["checker_agent2_primary_model", (payload?.agent2_primary_model || "").trim()],
      ["checker_agent2_fallback_model", (payload?.agent2_fallback_model || "").trim()],
      ["checker_agent3_primary_model", (payload?.agent3_primary_model || "").trim()],
      ["checker_agent3_fallback_model", (payload?.agent3_fallback_model || "").trim()],
      ["testcase_agent1_primary_model", (payload?.testcase_agent1_primary_model || "").trim()],
      ["testcase_agent1_fallback_model", (payload?.testcase_agent1_fallback_model || "").trim()],
      ["testcase_agent2_primary_model", (payload?.testcase_agent2_primary_model || "").trim()],
      ["testcase_agent2_fallback_model", (payload?.testcase_agent2_fallback_model || "").trim()],
      ["testcase_agent3_primary_model", (payload?.testcase_agent3_primary_model || "").trim()],
      ["testcase_agent3_fallback_model", (payload?.testcase_agent3_fallback_model || "").trim()],
    ];

    // Bo'sh qiymat yuborilsa, saqlangan kalit o'zgarmaydi; backup key faqat clear flag bilan o'chadi.
    const apiKey1 = (payload?.api_key_1 || "").trim();
    if (apiKey1) {
      updates.push(["gemini_default_api_key_1", apiKey1]);
    }

    const apiKey2 = (payload?.api_key_2 || "").trim();
    if (payload?.api_key_2_clear) {
      updates.push(["gemini_default_api_key_2", ""]);
    } else if (apiKey2) {
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
