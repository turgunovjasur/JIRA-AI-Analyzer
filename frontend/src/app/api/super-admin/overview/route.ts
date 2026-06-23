import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";
import type {
  AiUsageDashboard,
  CompanyAdminUser,
  CompanyModules,
  CompanySubscription,
  GlobalAiDefaults,
  LoginAuditLog,
  SecurityStatus,
  SuperAdminCompany,
  SuperAdminOverview,
} from "@/lib/types";

import {
  buildModuleSummary,
  buildSubscriptionHealth,
  isBillableSubscription,
  requireSuperAdminSession,
} from "../_helpers";

type RawCompany = {
  company_code?: string | null;
  company_name?: string | null;
  created_at?: string | null;
  id?: number | null;
  is_active?: boolean | number | null;
  seat_limit?: number | null;
};

function maskSecret(value: unknown) {
  const raw = typeof value === "string" ? value.trim() : "";
  if (!raw) return "";
  const tail = raw.slice(-4);
  const stars = "*".repeat(Math.max(4, raw.length - tail.length));
  return `${stars}${tail}`;
}

export async function GET() {
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const [
      companies,
      securityStatus,
      auditLogs,
      globalDefaults,
      keyFreezeMinutes,
      agent1PrimaryModel,
      agent1FallbackModel,
      agent2PrimaryModel,
      agent2FallbackModel,
      agent3PrimaryModel,
      agent3FallbackModel,
      testcaseAgent1PrimaryModel,
      testcaseAgent1FallbackModel,
      testcaseAgent2PrimaryModel,
      testcaseAgent2FallbackModel,
      testcaseAgent3PrimaryModel,
      testcaseAgent3FallbackModel,
      aiUsage,
    ] =
      await Promise.all([
        callInternalRpc<RawCompany[]>("get_all_companies"),
        callInternalRpc<SecurityStatus>("get_credential_security_status"),
        callInternalRpc<LoginAuditLog[]>("get_recent_login_audit_logs", [], { limit: 20 }),
        callInternalRpc<Record<string, string>>("get_global_gemini_defaults"),
        callInternalRpc<string>("get_global_setting", ["gemini_key_freeze_minutes", "10"]),
        callInternalRpc<string>("get_global_setting", ["checker_agent1_primary_model", ""]),
        callInternalRpc<string>("get_global_setting", ["checker_agent1_fallback_model", ""]),
        callInternalRpc<string>("get_global_setting", ["checker_agent2_primary_model", ""]),
        callInternalRpc<string>("get_global_setting", ["checker_agent2_fallback_model", ""]),
        callInternalRpc<string>("get_global_setting", ["checker_agent3_primary_model", ""]),
        callInternalRpc<string>("get_global_setting", ["checker_agent3_fallback_model", ""]),
        callInternalRpc<string>("get_global_setting", ["testcase_agent1_primary_model", ""]),
        callInternalRpc<string>("get_global_setting", ["testcase_agent1_fallback_model", ""]),
        callInternalRpc<string>("get_global_setting", ["testcase_agent2_primary_model", ""]),
        callInternalRpc<string>("get_global_setting", ["testcase_agent2_fallback_model", ""]),
        callInternalRpc<string>("get_global_setting", ["testcase_agent3_primary_model", ""]),
        callInternalRpc<string>("get_global_setting", ["testcase_agent3_fallback_model", ""]),
        callInternalRpc<AiUsageDashboard>("get_ai_usage_dashboard", [], { limit: 20 }),
      ]);

    const companyPayload = await Promise.all(
      (companies || []).map(async (company) => {
        const companyId = Number(company.id || 0);
        const [hasApiKeys, storedModules, effectiveModules, extraUserCount, users, subscription] = await Promise.all([
          callInternalRpc<boolean>("has_api_keys_configured", [companyId]),
          callInternalRpc<CompanyModules>("get_company_modules", [companyId]),
          callInternalRpc<CompanyModules>("get_effective_company_modules", [companyId]),
          callInternalRpc<number>("count_users_in_company", [companyId]),
          callInternalRpc<CompanyAdminUser[]>("get_users_by_company", [companyId]),
          callInternalRpc<CompanySubscription>("get_company_subscription", [companyId]),
        ]);

        const modules = effectiveModules || storedModules || {};
        const moduleSummary = buildModuleSummary(modules, subscription?.plan_name);
        return {
          addon_modules: moduleSummary.addon_modules,
          billing_health: buildSubscriptionHealth(subscription || {}),
          company_code: company.company_code || "",
          company_name: company.company_name || "",
          created_at: company.created_at || null,
          derived_modules: moduleSummary.derived_modules,
          extra_user_count: Number(extraUserCount || 0),
          has_api_keys: Boolean(hasApiKeys),
          id: companyId,
          included_modules: moduleSummary.included_modules,
          is_active: Boolean(company.is_active),
          modules,
          seat_limit: Math.max(0, Number(company.seat_limit || 0)),
          subscription: subscription || {},
          total_accounts: Array.isArray(users) ? users.length : 0,
        } satisfies SuperAdminCompany;
      }),
    );

    const metrics = companyPayload.reduce(
      (summary, company) => {
        summary.total += 1;
        if (company.is_active) summary.active += 1;
        if (isBillableSubscription(company.subscription)) summary.billable += 1;
        if (company.billing_health.severity === "warning") summary.expiring_soon += 1;
        if ((company.subscription.subscription_status || "").trim().toLowerCase() === "past_due") {
          summary.past_due += 1;
        }
        if (company.billing_health.severity === "danger") summary.blocked += 1;
        return summary;
      },
      {
        active: 0,
        billable: 0,
        blocked: 0,
        expiring_soon: 0,
        past_due: 0,
        total: 0,
      },
    );

    const aiDefaults = {
      api_key_1_mask: maskSecret(globalDefaults?.api_key_1),
      api_key_1_present: Boolean(globalDefaults?.api_key_1),
      api_key_2_mask: maskSecret(globalDefaults?.api_key_2),
      api_key_2_present: Boolean(globalDefaults?.api_key_2),
      key_freeze_minutes: Number.parseInt((keyFreezeMinutes || "10").trim(), 10) || 10,
      agent1_primary_model: (agent1PrimaryModel || "").trim(),
      agent1_fallback_model: (agent1FallbackModel || "").trim(),
      agent2_primary_model: (agent2PrimaryModel || "").trim(),
      agent2_fallback_model: (agent2FallbackModel || "").trim(),
      agent3_primary_model: (agent3PrimaryModel || "").trim(),
      agent3_fallback_model: (agent3FallbackModel || "").trim(),
      testcase_agent1_primary_model: (testcaseAgent1PrimaryModel || "").trim(),
      testcase_agent1_fallback_model: (testcaseAgent1FallbackModel || "").trim(),
      testcase_agent2_primary_model: (testcaseAgent2PrimaryModel || "").trim(),
      testcase_agent2_fallback_model: (testcaseAgent2FallbackModel || "").trim(),
      testcase_agent3_primary_model: (testcaseAgent3PrimaryModel || "").trim(),
      testcase_agent3_fallback_model: (testcaseAgent3FallbackModel || "").trim(),
    } satisfies GlobalAiDefaults;

    const payload = {
      auth_source: session.auth.auth_source || null,
      ai_usage: aiUsage || {
        by_company: [],
        by_module: [],
        recent_events: [],
        summary: {},
      },
      companies: companyPayload,
      current_admin: Boolean(session.auth.user_name),
      global_ai_defaults: aiDefaults,
      metrics,
      recent_login_audit_logs: auditLogs || [],
      security_status: securityStatus || {
        message: "Security holati topilmadi.",
        status: "warning",
      },
      success: true,
    } satisfies SuperAdminOverview;

    return NextResponse.json(payload);
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Super admin overview yuklanmadi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
