import { NextResponse } from "next/server";

import { BASE_PLAN_MODULE_KEYS, PAID_ADDON_MODULE_KEYS } from "@/lib/product-catalog";
import type { BillingHealth, CompanyModules, CompanySubscription } from "@/lib/types";
import { getOptionalSession } from "@/lib/session";

const BILLABLE_STATUSES = new Set(["trial", "active", "past_due"]);

function parseIsoDate(value: string | null | undefined) {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function dayDiffFromToday(value: string | null | undefined) {
  const date = parseIsoDate(value);
  if (!date) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffMs = date.getTime() - today.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export function buildSubscriptionHealth(subscription: CompanySubscription): BillingHealth {
  const status = (subscription.subscription_status || "active").trim().toLowerCase();
  const endDateRaw = (subscription.billing_end_date || "").trim();

  if (status === "suspended" || status === "cancelled") {
    return {
      severity: "danger",
      message: `Obuna bloklangan holatda: ${status}. Login yopiladi.`,
    };
  }

  if (status === "past_due") {
    return {
      severity: "danger",
      message: endDateRaw
        ? `To'lov muddati o'tgan. Muddat tugashi: ${endDateRaw}.`
        : "To'lov muddati o'tgan. Qo'lda tekshirish kerak.",
    };
  }

  if (!endDateRaw) {
    return {
      severity: "warning",
      message: "Billing tugash sanasi kiritilmagan.",
    };
  }

  const daysLeft = dayDiffFromToday(endDateRaw);
  if (daysLeft === null) {
    return {
      severity: "warning",
      message: `Billing sana noto'g'ri formatda: ${endDateRaw}`,
    };
  }

  if (daysLeft < 0) {
    return {
      severity: "danger",
      message: `Obuna muddati tugagan (${endDateRaw}). Login bloklanadi.`,
    };
  }

  if (daysLeft <= 7) {
    return {
      severity: "warning",
      message: `Obuna tez tugaydi: ${endDateRaw} (${daysLeft} kun qoldi).`,
    };
  }

  return {
    severity: "ok",
    message: `Obuna sog'lom holatda. Tugash sanasi: ${endDateRaw}.`,
  };
}

export function buildModuleSummary(modules: CompanyModules, planName?: string | null) {
  const normalizedPlan = (planName || "base").trim().toLowerCase();
  const includedModules =
    normalizedPlan === "base" ? [...BASE_PLAN_MODULE_KEYS] : [...BASE_PLAN_MODULE_KEYS];
  const addonModules = PAID_ADDON_MODULE_KEYS.filter((moduleKey) => Boolean(modules[moduleKey]));
  const derivedModules = Boolean(modules.webhook) ? ["monitoring"] : [];

  return {
    addon_modules: addonModules,
    derived_modules: derivedModules,
    included_modules: includedModules,
  };
}

export function isBillableSubscription(subscription: CompanySubscription) {
  const status = (subscription.subscription_status || "").trim().toLowerCase();
  return BILLABLE_STATUSES.has(status);
}

export async function requireSuperAdminSession() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return {
      error: NextResponse.json(
        { success: false, error: "Sessiya topilmadi yoki muddati tugagan." },
        { status: 401 },
      ),
      session: null,
    };
  }

  if (session.auth.role !== "super_admin") {
    return {
      error: NextResponse.json(
        { success: false, error: "Bu route faqat super admin uchun." },
        { status: 403 },
      ),
      session: null,
    };
  }

  return { error: null, session };
}

export function parseCompanyId(rawValue: string) {
  const companyId = Number(rawValue);
  if (!Number.isInteger(companyId) || companyId <= 0) {
    return null;
  }
  return companyId;
}
