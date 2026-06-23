import { NextResponse } from "next/server";

import {
  callInternalRpc,
  readSystemConfigWithBackend,
  saveSystemConfigWithBackend,
} from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";
import type { SystemSettingsSaveRequest } from "@/lib/types";

export async function GET() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json({ success: false, error: "Sessiya topilmadi." }, { status: 401 });
  }

  const role = session.auth.role;
  const companyId = session.auth.company_id || null;
  if (role !== "company_admin" || !companyId) {
    return NextResponse.json(
      { success: false, error: "System settings faqat company admin uchun." },
      { status: 403 },
    );
  }

  try {
    const modules = await callInternalRpc<Record<string, boolean>>("get_effective_company_modules", [companyId]);
    if (!modules?.webhook) {
      return NextResponse.json(
        { success: false, error: "Webhook moduli yoqilmagan." },
        { status: 403 },
      );
    }

    const payload = await readSystemConfigWithBackend({ company_id: companyId });
    return NextResponse.json(payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "System settingsni o'qib bo'lmadi.";
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
  if (role !== "company_admin" || !companyId) {
    return NextResponse.json(
      { success: false, error: "System settings faqat company admin uchun." },
      { status: 403 },
    );
  }

  try {
    const modules = await callInternalRpc<Record<string, boolean>>("get_effective_company_modules", [companyId]);
    if (!modules?.webhook) {
      return NextResponse.json(
        { success: false, error: "Webhook moduli yoqilmagan." },
        { status: 403 },
      );
    }

    const body = (await request.json().catch(() => null)) as Partial<SystemSettingsSaveRequest> | null;
    if (!body || typeof body !== "object") {
      return NextResponse.json(
        { success: false, error: "Noto'g'ri system settings payload." },
        { status: 400 },
      );
    }

    const result = await saveSystemConfigWithBackend({
      company_id: companyId,
      data: {
        queue_enabled: true,
      },
    });

    if (!result?.success) {
      return NextResponse.json(
        { success: false, error: "System settings saqlanmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "System settings saqlashda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
