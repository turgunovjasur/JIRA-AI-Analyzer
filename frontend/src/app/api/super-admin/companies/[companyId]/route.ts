import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";
import { PAID_ADDON_MODULE_KEYS } from "@/lib/product-catalog";
import type { CompanyModules } from "@/lib/types";

import { parseCompanyId, requireSuperAdminSession } from "../../_helpers";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ companyId: string }> },
) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  const { companyId: rawCompanyId } = await context.params;
  const companyId = parseCompanyId(rawCompanyId);
  if (!companyId) {
    return NextResponse.json({ success: false, error: "companyId noto'g'ri." }, { status: 400 });
  }

  try {
    const payload = (await request.json().catch(() => null)) as
      | {
          action?: "modules" | "seat_limit" | "status" | "subscription";
          enabled_modules?: CompanyModules;
          is_active?: boolean;
          seat_limit?: number;
          subscription?: Record<string, string>;
        }
      | null;

    switch (payload?.action) {
      case "status": {
        if (typeof payload.is_active !== "boolean") {
          return NextResponse.json(
            { success: false, error: "is_active boolean bo'lishi kerak." },
            { status: 400 },
          );
        }
        const success = await callInternalRpc<boolean>("update_company_status", [
          companyId,
          payload.is_active,
        ]);
        if (!success) {
          return NextResponse.json(
            { success: false, error: "Kompaniya statusini yangilab bo'lmadi." },
            { status: 400 },
          );
        }
        return NextResponse.json({ success });
      }

      case "seat_limit": {
        const seatLimit = Number(payload.seat_limit);
        if (!Number.isInteger(seatLimit) || seatLimit < 0) {
          return NextResponse.json(
            { success: false, error: "seat_limit 0 yoki undan katta bo'lishi kerak." },
            { status: 400 },
          );
        }
        const success = await callInternalRpc<boolean>("update_company_seat_limit", [
          companyId,
          seatLimit,
        ]);
        if (!success) {
          return NextResponse.json(
            { success: false, error: "Kompaniya seat limitini yangilab bo'lmadi." },
            { status: 400 },
          );
        }
        return NextResponse.json({ success });
      }

      case "modules": {
        const currentModules = await callInternalRpc<CompanyModules>("get_company_modules", [companyId]);
        const nextModules = { ...(currentModules || {}) };
        for (const moduleKey of PAID_ADDON_MODULE_KEYS) {
          if (payload.enabled_modules && moduleKey in payload.enabled_modules) {
            nextModules[moduleKey] = Boolean(payload.enabled_modules[moduleKey]);
          }
        }
        const success = await callInternalRpc<boolean>("save_company_modules", [companyId, nextModules]);
        if (!success) {
          return NextResponse.json(
            { success: false, error: "Kompaniya modullarini saqlab bo'lmadi." },
            { status: 400 },
          );
        }
        return NextResponse.json({ success });
      }

      case "subscription": {
        const subscription = payload.subscription || {};
        const validation = await callInternalRpc<[boolean, string, Record<string, string>]>(
          "validate_company_subscription_data",
          [subscription],
        );
        const isValid = Array.isArray(validation) ? validation[0] : false;
        const validationError = Array.isArray(validation) ? validation[1] : "Subscription noto'g'ri.";
        const normalizedSubscription = Array.isArray(validation) ? validation[2] : {};
        if (!isValid) {
          return NextResponse.json(
            { success: false, error: validationError || "Subscription noto'g'ri." },
            { status: 400 },
          );
        }
        const success = await callInternalRpc<boolean>("save_company_subscription", [
          companyId,
          normalizedSubscription,
        ]);
        if (!success) {
          return NextResponse.json(
            { success: false, error: "Kompaniya billing holatini saqlab bo'lmadi." },
            { status: 400 },
          );
        }
        return NextResponse.json({ success });
      }

      default:
        return NextResponse.json(
          { success: false, error: "Noma'lum action." },
          { status: 400 },
        );
    }
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Company action bajarilmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ companyId: string }> },
) {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  const { companyId: rawCompanyId } = await context.params;
  const companyId = parseCompanyId(rawCompanyId);
  if (!companyId) {
    return NextResponse.json({ success: false, error: "companyId noto'g'ri." }, { status: 400 });
  }

  try {
    const success = await callInternalRpc<boolean>("delete_company", [companyId]);
    if (!success) {
      return NextResponse.json(
        { success: false, error: "Kompaniyani o'chirib bo'lmadi." },
        { status: 400 },
      );
    }
    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Kompaniya o'chirishda xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
