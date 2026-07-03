import { NextResponse } from "next/server";

import {
  BackendRequestError,
  callInternalRpc,
  generateWebhookSecretWithBackend,
} from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

function absoluteWebhookUrl(rawUrl: string, request: Request): string {
  if (!rawUrl.startsWith("/")) return rawUrl;
  return `${new URL(request.url).origin}${rawUrl}`;
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
      { success: false, error: "Webhook settings faqat company admin uchun." },
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

    const payload = await generateWebhookSecretWithBackend({ company_id: companyId });
    return NextResponse.json({
      success: Boolean(payload?.success),
      generated: Boolean(payload?.generated),
      webhook_url: absoluteWebhookUrl(String(payload?.webhook_url || ""), request),
    });
  } catch (error) {
    if (error instanceof BackendRequestError) {
      return NextResponse.json(
        { success: false, error: error.message },
        { status: error.status },
      );
    }
    const message = error instanceof Error ? error.message : "Webhook parol yaratilmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
