import { NextResponse } from "next/server";

import {
  readModuleSettingsWithBackend,
  saveModuleSettingsWithBackend,
} from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";
import type { ModuleSettingsSaveRequest } from "@/lib/types";

export async function GET() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json({ success: false, error: "Sessiya topilmadi." }, { status: 401 });
  }

  const role = session.auth.role;
  const companyId = session.auth.company_id || null;
  const userId = session.auth.user_id || null;
  if (role !== "company_admin" || !companyId || !userId) {
    return NextResponse.json(
      { success: false, error: "Module settings faqat company admin uchun." },
      { status: 403 },
    );
  }

  try {
    const payload = await readModuleSettingsWithBackend({
      company_id: companyId,
      user_id: userId,
    });
    if (!payload?.success) {
      return NextResponse.json(
        { success: false, error: "Module settings o'qilmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Module settingsni o'qib bo'lmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json({ success: false, error: "Sessiya topilmadi." }, { status: 401 });
  }

  const role = session.auth.role;
  const companyId = session.auth.company_id || null;
  const userId = session.auth.user_id || null;
  if (role !== "company_admin" || !companyId || !userId) {
    return NextResponse.json(
      { success: false, error: "Module settings faqat company admin uchun." },
      { status: 403 },
    );
  }

  try {
    const body = (await request.json().catch(() => null)) as ModuleSettingsSaveRequest | null;
    if (!body?.checker || !body?.testcase) {
      return NextResponse.json(
        { success: false, error: "Noto'g'ri module settings payload." },
        { status: 400 },
      );
    }

    const result = await saveModuleSettingsWithBackend({
      company_id: companyId,
      user_id: userId,
      data: body,
    });

    if (!result?.success) {
      return NextResponse.json(
        { success: false, error: "Module settings saqlanmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Module settings saqlashda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
