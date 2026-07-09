import { NextResponse } from "next/server";

import {
  BackendRequestError,
  callInternalRpc,
  readWebhookConfigWithBackend,
  saveWebhookConfigWithBackend,
} from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";

type WebhookSavePayload = {
  auto_return_enabled?: boolean;
  allowed_issue_types?: string;
  excluded_assignees?: string;
  max_skip_check_comments?: number;
  min_tz_description_chars?: number;
  return_status?: string;
  return_threshold?: number;
  skip_code?: string;
  skip_comment_text?: string;
  use_adf_format?: boolean;
  tz_pr_footer_text?: string;
  recheck_comment_text?: string;
  return_notification_text?: string;
  read_comments_enabled?: boolean;
  max_comments_to_read?: number;
  dev_comment_source?: string;
  show_contradictory_comments?: boolean;
  visible_sections?: string[];
  ai_data_section_order?: string[];
  trigger_status?: string;
  trigger_status_aliases?: string;
  testcase_auto_comment_enabled?: boolean;
  testcase_auto_comment_trigger_status?: string;
  testcase_auto_comment_trigger_aliases?: string;
  testcase_default_test_types?: string[];
  testcase_testcases_per_requirement?: number;
  testcase_ai_data_section_order?: string[];
  testcase_read_comments_enabled?: boolean;
  testcase_max_comments_to_read?: number;
  testcase_ai_max_output_tokens?: number;
  testcase_use_adf_format?: boolean;
  testcase_footer_text?: string;
};

const CHECKER_COMMENT_SECTIONS = ["completed", "failed", "skipped", "issues", "figma"];

function ensureNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function ensureOptionalBool(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function backendErrorResponse(error: unknown, fallback: string) {
  const message = error instanceof Error ? error.message : fallback;
  if (error instanceof BackendRequestError) {
    const payload =
      typeof error.payload === "object" && error.payload !== null && !Array.isArray(error.payload)
        ? (error.payload as Record<string, unknown>)
        : {};
    return NextResponse.json(
      { success: false, ...payload, error: message },
      { status: error.status },
    );
  }
  return NextResponse.json({ success: false, error: message }, { status: 500 });
}

function absoluteWebhookUrl(rawUrl: string, request: Request): string {
  // APP_BASE_URL backendda sozlanmagan bo'lsa nisbiy path keladi —
  // brauzer kirgan domen (prod'da Caddy domeni) bilan to'ldiramiz.
  if (!rawUrl.startsWith("/")) return rawUrl;
  return `${new URL(request.url).origin}${rawUrl}`;
}

export async function GET(request: Request) {
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

    const webhookPayload = await readWebhookConfigWithBackend({ company_id: companyId });
    const data = webhookPayload?.data || {};
    const trigger = String(data.trigger_status || "");
    const testcaseTrigger = String(data.testcase_auto_comment_trigger_status || "");
    return NextResponse.json({
      success: true,
      data: {
        webhook_url: absoluteWebhookUrl(String(data.webhook_url || ""), request),
        auto_return_enabled: Boolean(data.auto_return_enabled),
        allowed_issue_types: String(data.allowed_issue_types || ""),
        excluded_assignees: String(data.excluded_assignees || ""),
        max_skip_check_comments: ensureNumber(data.max_skip_check_comments, 5),
        min_tz_description_chars: ensureNumber(data.min_tz_description_chars, 50),
        return_status: String(data.return_status || "NEED CLARIFICATION/RETURN TEST"),
        return_threshold: ensureNumber(data.return_threshold, 60),
        use_adf_format: true,
        tz_pr_footer_text: String(data.tz_pr_footer_text || "🤖 Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling."),
        recheck_comment_text: String(data.recheck_comment_text || "🔄 Re-check: Task qaytarildigan so'ng qaytadan tekshirilmoqda..."),
        return_notification_text: String(data.return_notification_text || "TZ-PR tekshiruvi past natija ko'rsatdi. Iltimos, TZ talablarini to'liq bajarilganligini tekshiring va qaytadan PR bering."),
        read_comments_enabled: Boolean(data.read_comments_enabled ?? true),
        max_comments_to_read: ensureNumber(data.max_comments_to_read, 0),
        dev_comment_source: String(data.dev_comment_source || "assignee_reporter"),
        show_contradictory_comments: Boolean(data.show_contradictory_comments ?? true),
        visible_sections: Array.isArray(data.visible_sections) ? data.visible_sections : CHECKER_COMMENT_SECTIONS,
        ai_data_section_order: Array.isArray(data.ai_data_section_order) ? data.ai_data_section_order : ["tz", "comments", "figma", "code"],
        skip_code: String(data.skip_code ?? "AI_SKIP"),
        skip_comment_text: String(data.skip_comment_text || "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi."),
        trigger_configured: Boolean(trigger.trim()),
        trigger_status: trigger || "READY TO TEST",
        trigger_status_aliases: String(data.trigger_status_aliases || ""),
        testcase_auto_comment_enabled: Boolean(data.testcase_auto_comment_enabled),
        testcase_trigger_configured: Boolean(testcaseTrigger.trim()),
        testcase_auto_comment_trigger_status: testcaseTrigger || "READY TO TEST",
        testcase_auto_comment_trigger_aliases: String(data.testcase_auto_comment_trigger_aliases || "Ready To Test,READY TO TEST"),
        testcase_default_test_types: Array.isArray(data.testcase_default_test_types) ? data.testcase_default_test_types : ["positive", "negative"],
        testcase_testcases_per_requirement: ensureNumber(data.testcase_testcases_per_requirement, 3),
        testcase_ai_data_section_order: Array.isArray(data.testcase_ai_data_section_order) ? data.testcase_ai_data_section_order : ["tz", "comments", "custom_context", "code"],
        testcase_read_comments_enabled: Boolean(data.testcase_read_comments_enabled ?? true),
        testcase_max_comments_to_read: ensureNumber(data.testcase_max_comments_to_read, 0),
        testcase_ai_max_output_tokens: 16384,
        testcase_use_adf_format: true,
        testcase_footer_text: String(data.testcase_footer_text || ""),
      },
    });
  } catch (error) {
    return backendErrorResponse(error, "Webhook settingsni o'qib bo'lmadi.");
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

    const payload = (await request.json().catch(() => null)) as WebhookSavePayload | null;
    const current = await readWebhookConfigWithBackend({ company_id: companyId }).catch(() => null);
    const currentTcEnabled = Boolean(current?.data?.testcase_auto_comment_enabled);
    const rawTrigger = String(payload?.trigger_status ?? "");
    const normalizedTrigger = rawTrigger || "READY TO TEST";

    const cleanPayload = {
      trigger_status: normalizedTrigger,
      return_threshold: ensureNumber(payload?.return_threshold, 60),
      return_status: String(payload?.return_status || "NEED CLARIFICATION/RETURN TEST").trim(),
      use_adf_format: true,
      tz_pr_footer_text: String(payload?.tz_pr_footer_text || "🤖 Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling.").trim(),
      recheck_comment_text: String(payload?.recheck_comment_text || "🔄 Re-check: Task qaytarildigan so'ng qaytadan tekshirilmoqda...").trim(),
      return_notification_text: String(payload?.return_notification_text || "TZ-PR tekshiruvi past natija ko'rsatdi. Iltimos, TZ talablarini to'liq bajarilganligini tekshiring va qaytadan PR bering.").trim(),
      read_comments_enabled: Boolean(payload?.read_comments_enabled ?? true),
      max_comments_to_read: ensureNumber(payload?.max_comments_to_read, 0),
      dev_comment_source:
        String(payload?.dev_comment_source || "").trim().toLowerCase() === "all"
          ? "all"
          : "assignee_reporter",
      show_contradictory_comments: Boolean(payload?.show_contradictory_comments ?? true),
      visible_sections: Array.isArray(payload?.visible_sections) ? payload!.visible_sections! : CHECKER_COMMENT_SECTIONS,
      ai_data_section_order: Array.isArray(payload?.ai_data_section_order) ? payload!.ai_data_section_order! : ["tz", "comments", "figma", "code"],
      min_tz_description_chars: ensureNumber(payload?.min_tz_description_chars, 50),
      excluded_assignees: String(payload?.excluded_assignees || "").trim(),
      allowed_issue_types: String(payload?.allowed_issue_types || "").trim(),
      skip_code: Object.prototype.hasOwnProperty.call(payload || {}, "skip_code")
        ? String(payload?.skip_code ?? "").trim()
        : "AI_SKIP",
      skip_comment_text: String(payload?.skip_comment_text || "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi.").trim(),
      max_skip_check_comments: ensureNumber(payload?.max_skip_check_comments, 5),
      auto_return_enabled: Boolean(payload?.auto_return_enabled),
      trigger_status_aliases: String(payload?.trigger_status_aliases || "").trim(),
      testcase_auto_comment_enabled:
        ensureOptionalBool(payload?.testcase_auto_comment_enabled) ?? currentTcEnabled,
      testcase_auto_comment_trigger_status: String(payload?.testcase_auto_comment_trigger_status || "READY TO TEST").trim(),
      testcase_auto_comment_trigger_aliases: String(payload?.testcase_auto_comment_trigger_aliases || "Ready To Test,READY TO TEST").trim(),
      testcase_default_test_types: Array.isArray(payload?.testcase_default_test_types) ? payload!.testcase_default_test_types! : ["positive", "negative"],
      testcase_testcases_per_requirement: ensureNumber(payload?.testcase_testcases_per_requirement, 3),
      testcase_ai_data_section_order: Array.isArray(payload?.testcase_ai_data_section_order) ? payload!.testcase_ai_data_section_order! : ["tz", "comments", "custom_context", "code"],
      testcase_read_comments_enabled: Boolean(payload?.testcase_read_comments_enabled ?? true),
      testcase_max_comments_to_read: ensureNumber(payload?.testcase_max_comments_to_read, 0),
      testcase_ai_max_output_tokens: 16384,
      testcase_use_adf_format: true,
      testcase_footer_text: String(payload?.testcase_footer_text || "").trim(),
    };

    if (
      cleanPayload.skip_code
      && cleanPayload.max_comments_to_read > 0
      && cleanPayload.max_skip_check_comments >= cleanPayload.max_comments_to_read
    ) {
      return NextResponse.json(
        {
          success: false,
          error: "Max commentlar skip tekshirish comment sonidan katta bo'lishi kerak.",
        },
        { status: 400 },
      );
    }

    await saveWebhookConfigWithBackend({
      company_id: companyId,
      data: {
        auto_return_enabled: cleanPayload.auto_return_enabled,
        excluded_assignees: cleanPayload.excluded_assignees,
        allowed_issue_types: cleanPayload.allowed_issue_types,
        max_skip_check_comments: cleanPayload.max_skip_check_comments,
        min_tz_description_chars: cleanPayload.min_tz_description_chars,
        return_status: cleanPayload.return_status,
        return_threshold: cleanPayload.return_threshold,
        use_adf_format: true,
        tz_pr_footer_text: cleanPayload.tz_pr_footer_text,
        recheck_comment_text: cleanPayload.recheck_comment_text,
        return_notification_text: cleanPayload.return_notification_text,
        read_comments_enabled: cleanPayload.read_comments_enabled,
        max_comments_to_read: cleanPayload.max_comments_to_read,
        dev_comment_source: cleanPayload.dev_comment_source,
        show_contradictory_comments: cleanPayload.show_contradictory_comments,
        visible_sections: cleanPayload.visible_sections,
        ai_data_section_order: cleanPayload.ai_data_section_order,
        skip_code: cleanPayload.skip_code,
        skip_comment_text: cleanPayload.skip_comment_text,
        trigger_status: cleanPayload.trigger_status,
        trigger_status_aliases: cleanPayload.trigger_status_aliases,
        testcase_auto_comment_enabled: cleanPayload.testcase_auto_comment_enabled,
        testcase_auto_comment_trigger_status: cleanPayload.testcase_auto_comment_trigger_status,
        testcase_auto_comment_trigger_aliases: cleanPayload.testcase_auto_comment_trigger_aliases,
        testcase_default_test_types: cleanPayload.testcase_default_test_types,
        testcase_testcases_per_requirement: cleanPayload.testcase_testcases_per_requirement,
        testcase_ai_data_section_order: cleanPayload.testcase_ai_data_section_order,
        testcase_read_comments_enabled: cleanPayload.testcase_read_comments_enabled,
        testcase_max_comments_to_read: cleanPayload.testcase_max_comments_to_read,
        testcase_ai_max_output_tokens: 16384,
        testcase_use_adf_format: true,
        testcase_footer_text: cleanPayload.testcase_footer_text,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    return backendErrorResponse(error, "Webhook settings saqlashda xato.");
  }
}
