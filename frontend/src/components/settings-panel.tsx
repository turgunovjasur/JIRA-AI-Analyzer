"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Notice } from "@/components/ui/notice";
import { PageIntro } from "@/components/ui/page-intro";
import { SectionHeader } from "@/components/ui/section-header";
import {
  BaseCheckGroup,
  BaseOrderPills,
  BaseInputField,
  BaseSelectField,
  NumberField,
  SettingsBaseCard,
  SettingsCardItem,
  SettingsCardSection,
  SettingsInnerCard,
  ToggleRow,
} from "@/components/settings/base-card-system";
import { SetupWizard } from "@/components/setup-wizard";
import type {
  ModuleSettingsAllowed,
  ModuleSettingsSaveRequest,
  SharedSettingsSaveRequest,
  SharedSettingsView,
  UserRole,
} from "@/lib/types";
import { CHECKER_SECTION_LABELS } from "@/lib/tzpr-sections";

type SettingsPanelProps = {
  companyName: string;
  hasWebhookModule: boolean;
  role: UserRole | null | undefined;
};

type SettingsTab = "integrations" | "webhook" | "modules";

type SettingsFormState = {
  jira_server: string;
  jira_email: string;
  jira_project_keys: string;
  github_org: string;
  figma_token: string;
  gemini_model: string;
  jira_token: string;
  github_token: string;
  gemini_api_key_1: string;
  gemini_api_key_2: string;
};

type WebhookFormState = {
  auto_return_enabled: boolean;
  allowed_issue_types: string;
  checker_delay_seconds: string;
  excluded_assignees: string;
  max_skip_check_comments: string;
  min_tz_description_chars: string;
  return_status: string;
  return_threshold: string;
  tz_pr_footer_text: string;
  recheck_comment_text: string;
  return_notification_text: string;
  read_comments_enabled: boolean;
  max_comments_to_read: string;
  show_contradictory_comments: boolean;
  visible_sections: string[];
  ai_data_section_order: string[];
  skip_code: string;
  skip_comment_text: string;
  trigger_status: string;
  trigger_status_aliases: string;
  trigger_statuses: string[];
  testcase_auto_comment_enabled: boolean;
  testcase_auto_comment_trigger_status: string;
  testcase_auto_comment_trigger_aliases: string;
  testcase_default_include_pr: boolean;
  testcase_default_use_smart_patch: boolean;
  testcase_default_test_types: string[];
  testcase_max_test_cases: string;
  testcase_ai_data_section_order: string[];
  testcase_read_comments_enabled: boolean;
  testcase_max_comments_to_read: string;
  testcase_footer_text: string;
  agent1_primary_model: string;
  agent1_fallback_model: string;
  agent2_batch_size: string;
  agent2_extra_scan_enabled: boolean;
  agent2_primary_model: string;
  agent2_fallback_model: string;
  agent3_primary_model: string;
  agent3_fallback_model: string;
};

type SystemFormState = {
  queue_enabled: boolean;
  task_wait_timeout: string;
  checker_testcase_delay: string;
  blocked_retry_delay: string;
  gemini_min_interval: string;
  blocked_check_interval: string;
};

type ModuleFormState = {
  checker: {
    default_use_smart_patch: boolean;
    visible_sections: string[];
    ai_data_section_order: string[];
    read_comments_enabled: boolean;
    max_comments_to_read: string;
    trusted_scope_comment_authors: string;
    agent2_batch_size: string;
    agent2_extra_scan_enabled: boolean;
    agent1_primary_model: string;
    agent1_fallback_model: string;
    agent2_primary_model: string;
    agent2_fallback_model: string;
    agent3_primary_model: string;
    agent3_fallback_model: string;
  };
  testcase: {
    default_include_pr: boolean;
    default_use_smart_patch: boolean;
    default_test_types: string[];
    max_test_cases: string;
    ai_data_section_order: string[];
    read_comments_enabled: boolean;
    max_comments_to_read: string;
  };
};

const EMPTY_FORM: SettingsFormState = {
  jira_server: "",
  jira_email: "",
  jira_project_keys: "",
  github_org: "",
  figma_token: "",
  gemini_model: "",
  jira_token: "",
  github_token: "",
  gemini_api_key_1: "",
  gemini_api_key_2: "",
};

const EMPTY_WEBHOOK_FORM: WebhookFormState = {
  auto_return_enabled: false,
  allowed_issue_types: "",
  checker_delay_seconds: "15",
  excluded_assignees: "",
  max_skip_check_comments: "5",
  min_tz_description_chars: "50",
  return_status: "NEED CLARIFICATION/RETURN TEST",
  return_threshold: "60",
  tz_pr_footer_text: "🤖 Bu komment AI tomonidan avtomatik yaratilgan. Savollar bo'lsa QA Team ga murojaat qiling.",
  recheck_comment_text: "🔄 Re-check: Task qaytarildigan so'ng qaytadan tekshirilmoqda...",
  return_notification_text: "TZ-PR tekshiruvi past natija ko'rsatdi. Iltimos, TZ talablarini to'liq bajarilganligini tekshiring va qaytadan PR bering.",
  read_comments_enabled: true,
  max_comments_to_read: "0",
  show_contradictory_comments: true,
  visible_sections: ["completed", "partial", "failed", "issues", "figma"],
  ai_data_section_order: ["tz", "comments", "figma", "code"],
  skip_code: "AI_SKIP",
  skip_comment_text: "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi.",
  trigger_status: "READY TO TEST",
  trigger_status_aliases: "",
  trigger_statuses: ["READY TO TEST"],
  testcase_auto_comment_enabled: false,
  testcase_auto_comment_trigger_status: "READY TO TEST",
  testcase_auto_comment_trigger_aliases: "Ready To Test,READY TO TEST",
  testcase_default_include_pr: true,
  testcase_default_use_smart_patch: true,
  testcase_default_test_types: ["positive", "negative"],
  testcase_max_test_cases: "10",
  testcase_ai_data_section_order: ["tz", "comments", "custom_context", "code"],
  testcase_read_comments_enabled: true,
  testcase_max_comments_to_read: "0",
  testcase_footer_text: "🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan. QA Team tomonidan tekshirilishi va to'ldirilishi kerak.",
  agent1_primary_model: "",
  agent1_fallback_model: "",
  agent2_batch_size: "6",
  agent2_extra_scan_enabled: true,
  agent2_primary_model: "",
  agent2_fallback_model: "",
  agent3_primary_model: "",
  agent3_fallback_model: "",
};

const EMPTY_SYSTEM_FORM: SystemFormState = {
  queue_enabled: true,
  task_wait_timeout: "60",
  checker_testcase_delay: "15",
  blocked_retry_delay: "5",
  gemini_min_interval: "6",
  blocked_check_interval: "30",
};

const DEFAULT_MODULE_ALLOWED: ModuleSettingsAllowed = {
  checker_visible_sections: ["completed", "partial", "failed", "issues", "figma"],
  checker_ai_data_order: ["tz", "comments", "figma", "code"],
  testcase_ai_data_order: ["tz", "comments", "custom_context", "code"],
  testcase_types: ["positive", "negative", "boundary", "edge"],
};

const EMPTY_MODULE_FORM: ModuleFormState = {
  checker: {
    default_use_smart_patch: true,
    visible_sections: ["completed", "partial", "failed", "issues", "figma"],
    ai_data_section_order: ["tz", "comments", "figma", "code"],
    read_comments_enabled: true,
    max_comments_to_read: "0",
    trusted_scope_comment_authors: "",
    agent2_batch_size: "6",
    agent2_extra_scan_enabled: true,
    agent1_primary_model: "",
    agent1_fallback_model: "",
    agent2_primary_model: "",
    agent2_fallback_model: "",
    agent3_primary_model: "",
    agent3_fallback_model: "",
  },
  testcase: {
    default_include_pr: true,
    default_use_smart_patch: true,
    default_test_types: ["positive", "negative"],
    max_test_cases: "10",
    ai_data_section_order: ["tz", "comments", "custom_context", "code"],
    read_comments_enabled: true,
    max_comments_to_read: "0",
  },
};

const SETTINGS_INPUT_CLASS = "settings-form-input";

function modelOptions() {
  return ["", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"];
}

export function SettingsPanel({ companyName, hasWebhookModule, role }: SettingsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [savingShared, setSavingShared] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [savingModules, setSavingModules] = useState(false);
  const [savingSystem, setSavingSystem] = useState(false);
  const [webhookLoading, setWebhookLoading] = useState(false);
  const [modulesLoading, setModulesLoading] = useState(false);
  const [systemLoading, setSystemLoading] = useState(false);
  const [checkerDirty, setCheckerDirty] = useState(false);
  const [testcaseDirty, setTestcaseDirty] = useState(false);
  const [whDirty, setWhDirty] = useState(false);
  const [systemDirty, setSystemDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sharedError, setSharedError] = useState<string | null>(null);
  const [webhookSharedError, setWebhookSharedError] = useState<string | null>(null);
  const [webhookService1Error, setWebhookService1Error] = useState<string | null>(null);
  const [webhookService2Error, setWebhookService2Error] = useState<string | null>(null);
  const [systemError, setSystemError] = useState<string | null>(null);
  const [modulesCheckerError, setModulesCheckerError] = useState<string | null>(null);
  const [modulesTestcaseError, setModulesTestcaseError] = useState<string | null>(null);
  const [sharedSuccess, setSharedSuccess] = useState<string | null>(null);
  const [webhookSharedSuccess, setWebhookSharedSuccess] = useState<string | null>(null);
  const [webhookService1Success, setWebhookService1Success] = useState<string | null>(null);
  const [webhookService2Success, setWebhookService2Success] = useState<string | null>(null);
  const [systemSuccess, setSystemSuccess] = useState<string | null>(null);
  const [modulesCheckerSuccess, setModulesCheckerSuccess] = useState<string | null>(null);
  const [modulesTestcaseSuccess, setModulesTestcaseSuccess] = useState<string | null>(null);
  const [view, setView] = useState<SharedSettingsView | null>(null);
  const [tab, setTab] = useState<SettingsTab>("integrations");
  const [form, setForm] = useState<SettingsFormState>(EMPTY_FORM);
  const [webhookForm, setWebhookForm] = useState<WebhookFormState>(EMPTY_WEBHOOK_FORM);
  const [webhookBaseline, setWebhookBaseline] = useState<WebhookFormState>(EMPTY_WEBHOOK_FORM);
  const [systemForm, setSystemForm] = useState<SystemFormState>(EMPTY_SYSTEM_FORM);
  const [moduleForm, setModuleForm] = useState<ModuleFormState>(EMPTY_MODULE_FORM);
  const [moduleAllowed, setModuleAllowed] = useState<ModuleSettingsAllowed>(DEFAULT_MODULE_ALLOWED);
  const [jiraTokenMask, setJiraTokenMask] = useState("");
  const [githubTokenMask, setGithubTokenMask] = useState("");
  const [figmaTokenMask, setFigmaTokenMask] = useState("");
  const [geminiKey1Mask, setGeminiKey1Mask] = useState("");
  const [geminiKey2Mask, setGeminiKey2Mask] = useState("");
  const [jiraTokenDirty, setJiraTokenDirty] = useState(false);
  const [githubTokenDirty, setGithubTokenDirty] = useState(false);
  const [figmaTokenDirty, setFigmaTokenDirty] = useState(false);
  const [geminiKey1Dirty, setGeminiKey1Dirty] = useState(false);
  const [geminiKey2Dirty, setGeminiKey2Dirty] = useState(false);
  const [showFigmaToken, setShowFigmaToken] = useState(false);
  const [showGeminiKey2, setShowGeminiKey2] = useState(false);

  const checkerOrderError = !moduleForm.checker.ai_data_section_order.includes("tz")
    || !moduleForm.checker.ai_data_section_order.includes("code");
  const checkerBatchError = Number(moduleForm.checker.agent2_batch_size || "0") < 1
    || Number(moduleForm.checker.agent2_batch_size || "0") > 20;
  const testcaseOrderError = !moduleForm.testcase.ai_data_section_order.includes("tz");
  const testcaseCountError = Number(moduleForm.testcase.max_test_cases || "0") < 1
    || Number(moduleForm.testcase.max_test_cases || "0") > 50;
  const moduleHasError = checkerOrderError || checkerBatchError || testcaseOrderError || testcaseCountError;
  const whThresholdError = webhookForm.auto_return_enabled
    && (Number(webhookForm.return_threshold || "0") < 0
      || Number(webhookForm.return_threshold || "0") > 100);
  const whCheckerOrderError = !webhookForm.ai_data_section_order.includes("tz")
    || !webhookForm.ai_data_section_order.includes("code");
  const whAgent2BatchError = Number(webhookForm.agent2_batch_size || "0") < 1
    || Number(webhookForm.agent2_batch_size || "0") > 20;
  const whMinTzError = Number(webhookForm.min_tz_description_chars || "0") < 0;
  const whMaxReadCommentsError = webhookForm.read_comments_enabled
    && Number(webhookForm.max_comments_to_read || "0") < 0;
  const whMaxSkipError = Boolean(webhookForm.skip_code.trim()) && Number(webhookForm.max_skip_check_comments || "0") < 1;
  const whTcMaxCasesError = webhookForm.testcase_auto_comment_enabled
    && (Number(webhookForm.testcase_max_test_cases || "0") < 1
      || Number(webhookForm.testcase_max_test_cases || "0") > 50);
  const whTcMaxCommentsError = webhookForm.testcase_auto_comment_enabled
    && webhookForm.testcase_read_comments_enabled
    && Number(webhookForm.testcase_max_comments_to_read || "0") < 0;
  const webhookHasError = whThresholdError
    || whCheckerOrderError
    || whAgent2BatchError
    || whMinTzError
    || whMaxReadCommentsError
    || whMaxSkipError
    || whTcMaxCasesError
    || whTcMaxCommentsError;

  const WEBHOOK_SHARED_KEYS: Array<keyof WebhookFormState> = [
    "allowed_issue_types",
    "excluded_assignees",
    "min_tz_description_chars",
  ];
  const WEBHOOK_SERVICE1_KEYS: Array<keyof WebhookFormState> = [
    "auto_return_enabled",
    "return_status",
    "return_threshold",
    "return_notification_text",
    "read_comments_enabled",
    "max_comments_to_read",
    "show_contradictory_comments",
    "visible_sections",
    "ai_data_section_order",
    "skip_code",
    "skip_comment_text",
    "max_skip_check_comments",
    "trigger_status",
    "trigger_status_aliases",
    "trigger_statuses",
    "tz_pr_footer_text",
    "recheck_comment_text",
    "agent2_batch_size",
    "agent1_primary_model",
    "agent1_fallback_model",
    "agent2_primary_model",
    "agent2_fallback_model",
    "agent3_primary_model",
    "agent3_fallback_model",
  ];
  const WEBHOOK_SERVICE2_KEYS: Array<keyof WebhookFormState> = [
    "testcase_auto_comment_enabled",
    "testcase_auto_comment_trigger_status",
    "testcase_auto_comment_trigger_aliases",
    "testcase_default_include_pr",
    "testcase_default_use_smart_patch",
    "testcase_default_test_types",
    "testcase_max_test_cases",
    "testcase_ai_data_section_order",
    "testcase_read_comments_enabled",
    "testcase_max_comments_to_read",
    "testcase_footer_text",
  ];

  function sameWebhookValue(a: unknown, b: unknown) {
    if (Array.isArray(a) && Array.isArray(b)) {
      if (a.length !== b.length) return false;
      return a.every((item, idx) => item === b[idx]);
    }
    return a === b;
  }

  function isWebhookCardDirty(keys: Array<keyof WebhookFormState>) {
    return keys.some((key) => !sameWebhookValue(webhookForm[key], webhookBaseline[key]));
  }

  const webhookSharedDirty = isWebhookCardDirty(WEBHOOK_SHARED_KEYS);
  const webhookService1Dirty = isWebhookCardDirty(WEBHOOK_SERVICE1_KEYS);
  const webhookService2Dirty = isWebhookCardDirty(WEBHOOK_SERVICE2_KEYS);
  const webhookAnyDirty = webhookSharedDirty || webhookService1Dirty || webhookService2Dirty;

  const sysWaitTimeoutError = Number(systemForm.task_wait_timeout || "0") < 1;
  const sysDelayError = Number(systemForm.checker_testcase_delay || "0") < 1;
  const sysRetryDelayError = Number(systemForm.blocked_retry_delay || "0") < 1;
  const sysGeminiIntervalError = Number(systemForm.gemini_min_interval || "0") < 1;
  const sysBlockedCheckError = Number(systemForm.blocked_check_interval || "0") < 1;
  const systemHasError = (systemForm.queue_enabled && sysWaitTimeoutError)
    || sysDelayError
    || sysRetryDelayError
    || (systemForm.queue_enabled && sysGeminiIntervalError)
    || sysBlockedCheckError;

  const testcaseTypeLabels: Record<string, string> = {
    positive: "Ijobiy — to'g'ri ma'lumotlar bilan muvaffaqiyatli bajarilish",
    negative: "Salbiy — noto'g'ri ma'lumotlar bilan rad etilish",
    boundary: "Chegara — qiymatlarning chegaralari",
    edge: "Ekstremal — nostandart holatlar",
  };

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setWebhookLoading(Boolean(hasWebhookModule));
      setModulesLoading(true);
      setSystemLoading(Boolean(hasWebhookModule));
      setError(null);
      try {
        const sharedResponse = await fetch("/api/settings/shared", { cache: "no-store" });

        const sharedPayload = (await sharedResponse.json().catch(() => null)) as
          | (SharedSettingsView & { error?: string })
          | null;
        if (!sharedResponse.ok || !sharedPayload?.success) {
          throw new Error(sharedPayload?.error || "Settings yuklanmadi.");
        }

        if (cancelled) return;

        setView(sharedPayload);
        const canUseWebhook = sharedPayload.mode === "company" && hasWebhookModule;
        const canUseModules = sharedPayload.mode === "company";
        const canUseSystem = sharedPayload.mode === "company" && hasWebhookModule;
        if (sharedPayload.mode === "company") {
          setTab("integrations");
        }

        setForm({
          jira_server: sharedPayload.fields.jira_server || "",
          jira_email: sharedPayload.fields.jira_email || "",
          jira_project_keys: sharedPayload.fields.jira_project_keys || "",
          github_org: sharedPayload.fields.github_org || "",
          figma_token: sharedPayload.fields.figma_token_mask || "",
          gemini_model: sharedPayload.fields.gemini_model || "",
          jira_token: sharedPayload.fields.jira_token_mask || "",
          github_token: sharedPayload.fields.github_token_mask || "",
          gemini_api_key_1: sharedPayload.fields.gemini_api_key_1_mask || "",
          gemini_api_key_2: sharedPayload.fields.gemini_api_key_2_mask || "",
        });
        setJiraTokenMask(sharedPayload.fields.jira_token_mask || "");
        setGithubTokenMask(sharedPayload.fields.github_token_mask || "");
        setFigmaTokenMask(sharedPayload.fields.figma_token_mask || "");
        setGeminiKey1Mask(sharedPayload.fields.gemini_api_key_1_mask || "");
        setGeminiKey2Mask(sharedPayload.fields.gemini_api_key_2_mask || "");
        setJiraTokenDirty(false);
        setGithubTokenDirty(false);
        setFigmaTokenDirty(false);
        setGeminiKey1Dirty(false);
        setGeminiKey2Dirty(false);
        setShowFigmaToken(Boolean(sharedPayload.fields.figma_token_present));
        setShowGeminiKey2(Boolean(sharedPayload.fields.gemini_api_key_2_present));

        if (canUseWebhook) {
          const webhookResponse = await fetch("/api/settings/webhook", { cache: "no-store" });
          const webhookPayload = (await webhookResponse.json().catch(() => null)) as
            | {
                data?: {
                  auto_return_enabled?: boolean;
                  allowed_issue_types?: string;
                  checker_delay_seconds?: number;
                  excluded_assignees?: string;
                  max_skip_check_comments?: number;
                  min_tz_description_chars?: number;
                  return_status?: string;
                  return_threshold?: number;
                  tz_pr_footer_text?: string;
                  recheck_comment_text?: string;
                  return_notification_text?: string;
                  read_comments_enabled?: boolean;
                  max_comments_to_read?: number;
                  show_contradictory_comments?: boolean;
                  visible_sections?: string[];
                  ai_data_section_order?: string[];
                  skip_code?: string;
                  skip_comment_text?: string;
                  trigger_status?: string;
                  trigger_status_aliases?: string;
                  testcase_auto_comment_enabled?: boolean;
                  testcase_auto_comment_trigger_status?: string;
                  testcase_auto_comment_trigger_aliases?: string;
                  testcase_default_include_pr?: boolean;
                  testcase_default_use_smart_patch?: boolean;
                  testcase_default_test_types?: string[];
                  testcase_max_test_cases?: number;
                  testcase_ai_data_section_order?: string[];
                  testcase_read_comments_enabled?: boolean;
                  testcase_max_comments_to_read?: number;
                  testcase_footer_text?: string;
                  agent1_primary_model?: string;
                  agent1_fallback_model?: string;
                  agent2_batch_size?: number;
                  agent2_extra_scan_enabled?: boolean;
                  agent2_primary_model?: string;
                  agent2_fallback_model?: string;
                  agent3_primary_model?: string;
                  agent3_fallback_model?: string;
                };
                success?: boolean;
              }
            | null;

          if (webhookResponse.ok && webhookPayload?.success) {
            const data = webhookPayload.data || {};
            const current = String(data.trigger_status || "READY TO TEST");
            const showContradictory = Boolean(data.show_contradictory_comments ?? true);
            const rawSections = Array.isArray(data.visible_sections) ? data.visible_sections : EMPTY_WEBHOOK_FORM.visible_sections;
            const normalizedSections = showContradictory
              ? Array.from(new Set([...rawSections, "contradictory_comments"]))
              : rawSections.filter((item) => item !== "contradictory_comments");

            setWebhookForm({
              auto_return_enabled: Boolean(data.auto_return_enabled),
              allowed_issue_types: String(data.allowed_issue_types || ""),
              checker_delay_seconds: String(data.checker_delay_seconds ?? 15),
              excluded_assignees: String(data.excluded_assignees || ""),
              max_skip_check_comments: String(data.max_skip_check_comments ?? 5),
              min_tz_description_chars: String(data.min_tz_description_chars ?? 50),
              return_status: String(data.return_status || "NEED CLARIFICATION/RETURN TEST"),
              return_threshold: String(data.return_threshold ?? 60),
              tz_pr_footer_text: String(data.tz_pr_footer_text || EMPTY_WEBHOOK_FORM.tz_pr_footer_text),
              recheck_comment_text: String(data.recheck_comment_text || EMPTY_WEBHOOK_FORM.recheck_comment_text),
              return_notification_text: String(data.return_notification_text || EMPTY_WEBHOOK_FORM.return_notification_text),
              read_comments_enabled: Boolean(data.read_comments_enabled ?? true),
              max_comments_to_read: String(data.max_comments_to_read ?? 0),
              show_contradictory_comments: showContradictory,
              visible_sections: normalizedSections,
              ai_data_section_order: Array.isArray(data.ai_data_section_order) ? data.ai_data_section_order : EMPTY_WEBHOOK_FORM.ai_data_section_order,
              skip_code: String(data.skip_code || "AI_SKIP"),
              skip_comment_text: String(data.skip_comment_text || "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi."),
              trigger_status: current || "READY TO TEST",
              trigger_status_aliases: String(data.trigger_status_aliases || ""),
              trigger_statuses: [current || "READY TO TEST"],
              testcase_auto_comment_enabled: Boolean(data.testcase_auto_comment_enabled),
              testcase_auto_comment_trigger_status: String(data.testcase_auto_comment_trigger_status || "READY TO TEST"),
              testcase_auto_comment_trigger_aliases: String(data.testcase_auto_comment_trigger_aliases || "Ready To Test,READY TO TEST"),
              testcase_default_include_pr: Boolean(data.testcase_default_include_pr ?? true),
              testcase_default_use_smart_patch: Boolean(data.testcase_default_use_smart_patch ?? true),
              testcase_default_test_types: Array.isArray(data.testcase_default_test_types) ? data.testcase_default_test_types : ["positive", "negative"],
              testcase_max_test_cases: String(data.testcase_max_test_cases ?? 10),
              testcase_ai_data_section_order: Array.isArray(data.testcase_ai_data_section_order) ? data.testcase_ai_data_section_order : ["tz", "comments", "custom_context", "code"],
              testcase_read_comments_enabled: Boolean(data.testcase_read_comments_enabled ?? true),
              testcase_max_comments_to_read: String(data.testcase_max_comments_to_read ?? 0),
              testcase_footer_text: String(data.testcase_footer_text || EMPTY_WEBHOOK_FORM.testcase_footer_text),
              agent1_primary_model: String(data.agent1_primary_model || ""),
              agent1_fallback_model: String(data.agent1_fallback_model || ""),
              agent2_batch_size: String(data.agent2_batch_size ?? 6),
              agent2_extra_scan_enabled: Boolean(data.agent2_extra_scan_enabled ?? true),
              agent2_primary_model: String(data.agent2_primary_model || ""),
              agent2_fallback_model: String(data.agent2_fallback_model || ""),
              agent3_primary_model: String(data.agent3_primary_model || ""),
              agent3_fallback_model: String(data.agent3_fallback_model || ""),
            });
            setWebhookBaseline({
              auto_return_enabled: Boolean(data.auto_return_enabled),
              allowed_issue_types: String(data.allowed_issue_types || ""),
              checker_delay_seconds: String(data.checker_delay_seconds ?? 15),
              excluded_assignees: String(data.excluded_assignees || ""),
              max_skip_check_comments: String(data.max_skip_check_comments ?? 5),
              min_tz_description_chars: String(data.min_tz_description_chars ?? 50),
              return_status: String(data.return_status || "NEED CLARIFICATION/RETURN TEST"),
              return_threshold: String(data.return_threshold ?? 60),
              tz_pr_footer_text: String(data.tz_pr_footer_text || EMPTY_WEBHOOK_FORM.tz_pr_footer_text),
              recheck_comment_text: String(data.recheck_comment_text || EMPTY_WEBHOOK_FORM.recheck_comment_text),
              return_notification_text: String(data.return_notification_text || EMPTY_WEBHOOK_FORM.return_notification_text),
              read_comments_enabled: Boolean(data.read_comments_enabled ?? true),
              max_comments_to_read: String(data.max_comments_to_read ?? 0),
              show_contradictory_comments: showContradictory,
              visible_sections: normalizedSections,
              ai_data_section_order: Array.isArray(data.ai_data_section_order) ? data.ai_data_section_order : EMPTY_WEBHOOK_FORM.ai_data_section_order,
              skip_code: String(data.skip_code || "AI_SKIP"),
              skip_comment_text: String(data.skip_comment_text || "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi."),
              trigger_status: current || "READY TO TEST",
              trigger_status_aliases: String(data.trigger_status_aliases || ""),
              trigger_statuses: [current || "READY TO TEST"],
              testcase_auto_comment_enabled: Boolean(data.testcase_auto_comment_enabled),
              testcase_auto_comment_trigger_status: String(data.testcase_auto_comment_trigger_status || "READY TO TEST"),
              testcase_auto_comment_trigger_aliases: String(data.testcase_auto_comment_trigger_aliases || "Ready To Test,READY TO TEST"),
              testcase_default_include_pr: Boolean(data.testcase_default_include_pr ?? true),
              testcase_default_use_smart_patch: Boolean(data.testcase_default_use_smart_patch ?? true),
              testcase_default_test_types: Array.isArray(data.testcase_default_test_types) ? data.testcase_default_test_types : ["positive", "negative"],
              testcase_max_test_cases: String(data.testcase_max_test_cases ?? 10),
              testcase_ai_data_section_order: Array.isArray(data.testcase_ai_data_section_order) ? data.testcase_ai_data_section_order : ["tz", "comments", "custom_context", "code"],
              testcase_read_comments_enabled: Boolean(data.testcase_read_comments_enabled ?? true),
              testcase_max_comments_to_read: String(data.testcase_max_comments_to_read ?? 0),
              testcase_footer_text: String(data.testcase_footer_text || EMPTY_WEBHOOK_FORM.testcase_footer_text),
              agent1_primary_model: String(data.agent1_primary_model || ""),
              agent1_fallback_model: String(data.agent1_fallback_model || ""),
              agent2_batch_size: String(data.agent2_batch_size ?? 6),
              agent2_extra_scan_enabled: Boolean(data.agent2_extra_scan_enabled ?? true),
              agent2_primary_model: String(data.agent2_primary_model || ""),
              agent2_fallback_model: String(data.agent2_fallback_model || ""),
              agent3_primary_model: String(data.agent3_primary_model || ""),
              agent3_fallback_model: String(data.agent3_fallback_model || ""),
            });
            setWhDirty(false);
          } else {
            setWebhookForm(EMPTY_WEBHOOK_FORM);
            setWebhookBaseline(EMPTY_WEBHOOK_FORM);
            setWhDirty(false);
          }
        } else {
          setWebhookForm(EMPTY_WEBHOOK_FORM);
          setWebhookBaseline(EMPTY_WEBHOOK_FORM);
          setWhDirty(false);
          setWebhookLoading(false);
        }

        if (canUseSystem) {
          const systemResponse = await fetch("/api/settings/system", { cache: "no-store" });
          const systemPayload = (await systemResponse.json().catch(() => null)) as
            | {
                success?: boolean;
                data?: {
                  queue_enabled?: boolean;
                  task_wait_timeout?: number;
                  checker_testcase_delay?: number;
                  blocked_retry_delay?: number;
                  gemini_min_interval?: number;
                  blocked_check_interval?: number;
                };
              }
            | null;

          if (systemResponse.ok && systemPayload?.success && systemPayload.data) {
            const data = systemPayload.data;
            setSystemForm({
              queue_enabled: Boolean(data.queue_enabled ?? true),
              task_wait_timeout: String(data.task_wait_timeout ?? 60),
              checker_testcase_delay: String(data.checker_testcase_delay ?? 15),
              blocked_retry_delay: String(data.blocked_retry_delay ?? 5),
              gemini_min_interval: String(data.gemini_min_interval ?? 6),
              blocked_check_interval: String(data.blocked_check_interval ?? 30),
            });
            setSystemDirty(false);
          } else {
            setSystemForm(EMPTY_SYSTEM_FORM);
            setSystemDirty(false);
          }
        } else {
          setSystemForm(EMPTY_SYSTEM_FORM);
          setSystemDirty(false);
          setSystemLoading(false);
        }

        if (canUseModules) {
          const modulesResponse = await fetch("/api/settings/modules", { cache: "no-store" });
          const modulesPayload = (await modulesResponse.json().catch(() => null)) as
            | {
                success?: boolean;
                data?: {
                  checker?: {
                    default_use_smart_patch?: boolean;
                    visible_sections?: string[];
                    ai_data_section_order?: string[];
                    read_comments_enabled?: boolean;
                    max_comments_to_read?: number;
                    trusted_scope_comment_authors?: string;
                    agent2_batch_size?: number;
                    agent2_extra_scan_enabled?: boolean;
                    agent1_primary_model?: string;
                    agent1_fallback_model?: string;
                    agent2_primary_model?: string;
                    agent2_fallback_model?: string;
                    agent3_primary_model?: string;
                    agent3_fallback_model?: string;
                  };
                  testcase?: {
                    default_include_pr?: boolean;
                    default_use_smart_patch?: boolean;
                    default_test_types?: string[];
                    max_test_cases?: number;
                    ai_data_section_order?: string[];
                    read_comments_enabled?: boolean;
                    max_comments_to_read?: number;
                  };
                  allowed?: ModuleSettingsAllowed;
                };
                error?: string;
              }
            | null;

          if (modulesResponse.ok && modulesPayload?.success && modulesPayload.data) {
            const checker = modulesPayload.data.checker || {};
            const testcase = modulesPayload.data.testcase || {};
            setModuleAllowed(modulesPayload.data.allowed || DEFAULT_MODULE_ALLOWED);
            setModuleForm({
              checker: {
                default_use_smart_patch: checker.default_use_smart_patch ?? true,
                visible_sections: Array.isArray(checker.visible_sections) ? checker.visible_sections : EMPTY_MODULE_FORM.checker.visible_sections,
                ai_data_section_order: Array.isArray(checker.ai_data_section_order) ? checker.ai_data_section_order : EMPTY_MODULE_FORM.checker.ai_data_section_order,
                read_comments_enabled: Boolean(checker.read_comments_enabled),
                max_comments_to_read: String(checker.max_comments_to_read ?? 0),
                trusted_scope_comment_authors: String(checker.trusted_scope_comment_authors || ""),
                agent2_batch_size: String(checker.agent2_batch_size ?? 6),
                agent2_extra_scan_enabled: Boolean(checker.agent2_extra_scan_enabled ?? true),
                agent1_primary_model: String(checker.agent1_primary_model || ""),
                agent1_fallback_model: String(checker.agent1_fallback_model || ""),
                agent2_primary_model: String(checker.agent2_primary_model || ""),
                agent2_fallback_model: String(checker.agent2_fallback_model || ""),
                agent3_primary_model: String(checker.agent3_primary_model || ""),
                agent3_fallback_model: String(checker.agent3_fallback_model || ""),
              },
              testcase: {
                default_include_pr: Boolean(testcase.default_include_pr),
                default_use_smart_patch: Boolean(testcase.default_use_smart_patch),
                default_test_types: Array.isArray(testcase.default_test_types) ? testcase.default_test_types : EMPTY_MODULE_FORM.testcase.default_test_types,
                max_test_cases: String(testcase.max_test_cases ?? 10),
                ai_data_section_order: Array.isArray(testcase.ai_data_section_order) ? testcase.ai_data_section_order : EMPTY_MODULE_FORM.testcase.ai_data_section_order,
                read_comments_enabled: Boolean(testcase.read_comments_enabled),
                max_comments_to_read: String(testcase.max_comments_to_read ?? 0),
              },
            });
            setCheckerDirty(false);
            setTestcaseDirty(false);
          } else {
            setModuleAllowed(DEFAULT_MODULE_ALLOWED);
            setModuleForm(EMPTY_MODULE_FORM);
            setCheckerDirty(false);
            setTestcaseDirty(false);
          }
        } else {
          setModuleAllowed(DEFAULT_MODULE_ALLOWED);
          setModuleForm(EMPTY_MODULE_FORM);
          setCheckerDirty(false);
          setTestcaseDirty(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Settings yuklashda xato.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setWebhookLoading(false);
          setModulesLoading(false);
          setSystemLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [hasWebhookModule]);

  function updateField(field: keyof SettingsFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateWebhookField<K extends keyof WebhookFormState>(field: K, value: WebhookFormState[K]) {
    setWhDirty(true);
    setWebhookForm((current) => ({ ...current, [field]: value }));
  }

  function updateSystemField(field: keyof SystemFormState, value: string | boolean) {
    setSystemDirty(true);
    setSystemForm((current) => ({ ...current, [field]: value }));
  }

  function updateCheckerField<K extends keyof ModuleFormState["checker"]>(
    field: K,
    value: ModuleFormState["checker"][K],
  ) {
    setCheckerDirty(true);
    setModuleForm((current) => ({
      ...current,
      checker: {
        ...current.checker,
        [field]: value,
      },
    }));
  }

  function updateTestcaseField<K extends keyof ModuleFormState["testcase"]>(
    field: K,
    value: ModuleFormState["testcase"][K],
  ) {
    setTestcaseDirty(true);
    setModuleForm((current) => ({
      ...current,
      testcase: {
        ...current.testcase,
        [field]: value,
      },
    }));
  }

  function updateModuleOrderField(
    moduleName: "checker" | "testcase",
    field: "ai_data_section_order",
    value: string[],
  ) {
    if (moduleName === "checker") {
      updateCheckerField(field, value);
      return;
    }
    updateTestcaseField(field, value);
  }

  function maskSecret(value: string) {
    const raw = (value || "").trim();
    if (!raw) return "";
    const tail = raw.slice(-4);
    const stars = "*".repeat(Math.max(4, raw.length - tail.length));
    return `${stars}${tail}`;
  }

  function formatSaveError(
    scopeLabel: string,
    response: Response,
    result: { error?: string; success?: boolean } | null,
  ) {
    const backendMessage = result?.error || "Noma'lum server xatosi";
    return `${scopeLabel} saqlanmadi. DEBUG: status=${response.status}, ok=${response.ok}, message=${backendMessage}`;
  }

  async function saveShared() {
    setSavingShared(true);
    setError(null);
    setSharedError(null);
    setSharedSuccess(null);

    const payload: SharedSettingsSaveRequest = {
      gemini_model: form.gemini_model,
    };
    if (geminiKey1Dirty && form.gemini_api_key_1.trim()) {
      payload.gemini_api_key_1 = form.gemini_api_key_1.trim();
    }
    if (geminiKey2Dirty && form.gemini_api_key_2.trim()) {
      payload.gemini_api_key_2 = form.gemini_api_key_2.trim();
    }

    if (view?.mode === "company") {
      payload.jira_server = form.jira_server;
      payload.jira_email = form.jira_email;
      payload.jira_project_keys = form.jira_project_keys;
      payload.github_org = form.github_org;
      if (figmaTokenDirty && form.figma_token.trim()) {
        payload.figma_token = form.figma_token.trim();
      }
      if (jiraTokenDirty && form.jira_token.trim()) {
        payload.jira_token = form.jira_token.trim();
      }
      if (githubTokenDirty && form.github_token.trim()) {
        payload.github_token = form.github_token.trim();
      }
    }

    try {
      const response = await fetch("/api/settings/shared", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean } | null;
      if (!response.ok || !result?.success) {
        throw new Error(formatSaveError("Settings", response, result));
      }

      setSharedSuccess("✓ Muvaffaqiyatli saqlandi.");
      const nextJiraMask = jiraTokenDirty && form.jira_token.trim()
        ? maskSecret(form.jira_token.trim())
        : jiraTokenMask;
      const nextGithubMask = githubTokenDirty && form.github_token.trim()
        ? maskSecret(form.github_token.trim())
        : githubTokenMask;
      const nextFigmaMask = figmaTokenDirty && form.figma_token.trim()
        ? maskSecret(form.figma_token.trim())
        : figmaTokenMask;
      const nextGemini1Mask = geminiKey1Dirty && form.gemini_api_key_1.trim()
        ? maskSecret(form.gemini_api_key_1.trim())
        : geminiKey1Mask;
      const nextGemini2Mask = geminiKey2Dirty && form.gemini_api_key_2.trim()
        ? maskSecret(form.gemini_api_key_2.trim())
        : geminiKey2Mask;
      setJiraTokenMask(nextJiraMask);
      setGithubTokenMask(nextGithubMask);
      setFigmaTokenMask(nextFigmaMask);
      setGeminiKey1Mask(nextGemini1Mask);
      setGeminiKey2Mask(nextGemini2Mask);
      setJiraTokenDirty(false);
      setGithubTokenDirty(false);
      setFigmaTokenDirty(false);
      setGeminiKey1Dirty(false);
      setGeminiKey2Dirty(false);
      if (nextFigmaMask) setShowFigmaToken(true);
      if (nextGemini2Mask) setShowGeminiKey2(true);
      setForm((current) => ({
        ...current,
        figma_token: nextFigmaMask,
        jira_token: nextJiraMask,
        github_token: nextGithubMask,
        gemini_api_key_1: nextGemini1Mask,
        gemini_api_key_2: nextGemini2Mask,
      }));
    } catch (e) {
      setSharedError(e instanceof Error ? e.message : "Settings save xatosi.");
    } finally {
      setSavingShared(false);
    }
  }

  async function saveWebhook(target: "shared" | "service1" | "service2") {
    if (webhookHasError) return;
    setSavingWebhook(true);
    setError(null);
    setWebhookSharedError(null);
    setWebhookService1Error(null);
    setWebhookService2Error(null);
    setWebhookSharedSuccess(null);
    setWebhookService1Success(null);
    setWebhookService2Success(null);

    try {
      const response = await fetch("/api/settings/webhook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          auto_return_enabled: webhookForm.auto_return_enabled,
          allowed_issue_types: webhookForm.allowed_issue_types,
          excluded_assignees: webhookForm.excluded_assignees,
          max_skip_check_comments: Number(webhookForm.max_skip_check_comments || 5),
          min_tz_description_chars: Number(webhookForm.min_tz_description_chars || 50),
          return_status: webhookForm.return_status,
          return_threshold: Number(webhookForm.return_threshold || 60),
          use_adf_format: true,
          tz_pr_footer_text: webhookForm.tz_pr_footer_text,
          recheck_comment_text: webhookForm.recheck_comment_text,
          return_notification_text: webhookForm.return_notification_text,
          read_comments_enabled: webhookForm.read_comments_enabled,
          max_comments_to_read: Number(webhookForm.max_comments_to_read || 0),
          show_contradictory_comments: webhookForm.show_contradictory_comments,
          visible_sections: webhookForm.visible_sections,
          ai_data_section_order: webhookForm.ai_data_section_order,
          skip_code: webhookForm.skip_code,
          skip_comment_text: webhookForm.skip_comment_text,
          trigger_status: webhookForm.trigger_status,
          trigger_status_aliases: "",
          testcase_auto_comment_enabled: webhookForm.testcase_auto_comment_enabled,
          testcase_auto_comment_trigger_status: webhookForm.testcase_auto_comment_trigger_status,
          testcase_auto_comment_trigger_aliases: webhookForm.testcase_auto_comment_trigger_aliases,
          testcase_default_include_pr: webhookForm.testcase_default_include_pr,
          testcase_default_use_smart_patch: webhookForm.testcase_default_use_smart_patch,
          testcase_default_test_types: webhookForm.testcase_default_test_types,
          testcase_max_test_cases: Number(webhookForm.testcase_max_test_cases || 10),
          testcase_ai_data_section_order: webhookForm.testcase_ai_data_section_order,
          testcase_read_comments_enabled: webhookForm.testcase_read_comments_enabled,
          testcase_max_comments_to_read: Number(webhookForm.testcase_max_comments_to_read || 0),
          testcase_ai_max_output_tokens: 16384,
          testcase_use_adf_format: true,
          testcase_footer_text: webhookForm.testcase_footer_text,
          agent1_primary_model: webhookForm.agent1_primary_model,
          agent1_fallback_model: webhookForm.agent1_fallback_model,
          agent2_batch_size: Number(webhookForm.agent2_batch_size || 6),
          agent2_extra_scan_enabled: webhookForm.agent2_extra_scan_enabled,
          agent2_primary_model: webhookForm.agent2_primary_model,
          agent2_fallback_model: webhookForm.agent2_fallback_model,
          agent3_primary_model: webhookForm.agent3_primary_model,
          agent3_fallback_model: webhookForm.agent3_fallback_model,
        }),
      });

      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean } | null;
      if (!response.ok || !result?.success) {
        throw new Error(formatSaveError("Webhook", response, result));
      }

      if (target === "shared") setWebhookSharedSuccess("✓ Muvaffaqiyatli saqlandi.");
      if (target === "service1") setWebhookService1Success("✓ Muvaffaqiyatli saqlandi.");
      if (target === "service2") setWebhookService2Success("✓ Muvaffaqiyatli saqlandi.");
      setWebhookBaseline(webhookForm);
      setWhDirty(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Webhook sozlamalarini saqlashda xato.";
      if (target === "shared") setWebhookSharedError(msg);
      if (target === "service1") setWebhookService1Error(msg);
      if (target === "service2") setWebhookService2Error(msg);
    } finally {
      setSavingWebhook(false);
    }
  }

  async function saveSystem() {
    if (systemHasError) return;
    setSavingSystem(true);
    setError(null);
    setSystemError(null);
    setSystemSuccess(null);

    try {
      const response = await fetch("/api/settings/system", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          queue_enabled: systemForm.queue_enabled,
          task_wait_timeout: Number(systemForm.task_wait_timeout || 60),
          checker_testcase_delay: Number(systemForm.checker_testcase_delay || 15),
          blocked_retry_delay: Number(systemForm.blocked_retry_delay || 5),
          gemini_min_interval: Number(systemForm.gemini_min_interval || 6),
          blocked_check_interval: Number(systemForm.blocked_check_interval || 30),
        }),
      });

      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean } | null;
      if (!response.ok || !result?.success) {
        throw new Error(formatSaveError("Tizim sozlamalari", response, result));
      }

      setSystemSuccess("✓ Muvaffaqiyatli saqlandi.");
      setSystemDirty(false);
    } catch (e) {
      setSystemError(e instanceof Error ? e.message : "Tizim sozlamalarini saqlashda xato.");
    } finally {
      setSavingSystem(false);
    }
  }

  async function saveModules(target: "checker" | "testcase") {
    if (moduleHasError) return;
    setSavingModules(true);
    setError(null);
    setModulesCheckerError(null);
    setModulesTestcaseError(null);
    setModulesCheckerSuccess(null);
    setModulesTestcaseSuccess(null);

    try {
      const payload: ModuleSettingsSaveRequest = {
        checker: {
          default_use_smart_patch: moduleForm.checker.default_use_smart_patch,
          visible_sections: moduleForm.checker.visible_sections,
          ai_data_section_order: moduleForm.checker.ai_data_section_order,
          read_comments_enabled: moduleForm.checker.read_comments_enabled,
          max_comments_to_read: Number(moduleForm.checker.max_comments_to_read || 0),
          trusted_scope_comment_authors: moduleForm.checker.trusted_scope_comment_authors,
          agent2_batch_size: Number(moduleForm.checker.agent2_batch_size || 6),
          agent2_extra_scan_enabled: moduleForm.checker.agent2_extra_scan_enabled,
          agent1_primary_model: moduleForm.checker.agent1_primary_model,
          agent1_fallback_model: moduleForm.checker.agent1_fallback_model,
          agent2_primary_model: moduleForm.checker.agent2_primary_model,
          agent2_fallback_model: moduleForm.checker.agent2_fallback_model,
          agent3_primary_model: moduleForm.checker.agent3_primary_model,
          agent3_fallback_model: moduleForm.checker.agent3_fallback_model,
        },
        testcase: {
          default_include_pr: moduleForm.testcase.default_include_pr,
          default_use_smart_patch: moduleForm.testcase.default_use_smart_patch,
          default_test_types: moduleForm.testcase.default_test_types,
          max_test_cases: Number(moduleForm.testcase.max_test_cases || 10),
          ai_data_section_order: moduleForm.testcase.ai_data_section_order,
          read_comments_enabled: moduleForm.testcase.read_comments_enabled,
          max_comments_to_read: Number(moduleForm.testcase.max_comments_to_read || 0),
        },
      };

      const response = await fetch("/api/settings/modules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean } | null;
      if (!response.ok || !result?.success) {
        throw new Error(formatSaveError("Module sozlamalari", response, result));
      }

      if (target === "checker") setModulesCheckerSuccess("✓ Muvaffaqiyatli saqlandi.");
      if (target === "testcase") setModulesTestcaseSuccess("✓ Muvaffaqiyatli saqlandi.");
      setCheckerDirty(false);
      setTestcaseDirty(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Module settingsni saqlashda xato.";
      if (target === "checker") setModulesCheckerError(msg);
      if (target === "testcase") setModulesTestcaseError(msg);
    } finally {
      setSavingModules(false);
    }
  }

  return (
    <>
      <PageIntro
        eyebrow="Configuration"
        title="Settings"
        description={`${companyName} uchun webhook, integration va modul sozlamalari.`}
        badge={(
          <div className="flex items-center gap-2">
            <Badge tone="success">● Online</Badge>
            <Badge tone="soft">v2.5</Badge>
          </div>
        )}
      />

      {!loading && view && view.mode === "company" ? (
        <SetupWizard hasWebhookModule={hasWebhookModule} settings={view} />
      ) : null}

      {loading ? <PageIntro eyebrow="Loading" title="Settings yuklanmoqda..." /> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      {!loading && view?.mode === "platform" ? (
        <PageIntro
          eyebrow="Platform Session"
          title="Bu bo'lim customer sozlamalari uchun"
          description="Platform-level boshqaruv uchun Admin bo'limidan foydalaning."
        />
      ) : null}

      {!loading && view && view.mode !== "platform" ? (
        <>
          {view.mode === "company" ? (
            <section className="flex flex-wrap items-center justify-between gap-3">
              <div className="tabs">
                <button
                  className={`tab-btn ${tab === "modules" ? "active" : ""}`}
                  onClick={() => setTab("modules")}
                >
                  📦 Modules
                </button>
                {hasWebhookModule ? (
                  <button className={`tab-btn ${tab === "webhook" ? "active" : ""}`} onClick={() => setTab("webhook")}>
                    🔗 Webhook
                  </button>
                ) : null}
                <button
                  className={`tab-btn ${tab === "integrations" ? "active" : ""}`}
                  onClick={() => setTab("integrations")}
                >
                  🔌 AI & Integrations
                </button>
              </div>
              {tab === "modules" && (checkerDirty || testcaseDirty) ? (
                <Notice tone="warning">Saqlanmagan o'zgarishlar</Notice>
              ) : null}
              {tab === "webhook" && (webhookAnyDirty || systemDirty) ? (
                <Notice tone="warning">Saqlanmagan o'zgarishlar</Notice>
              ) : null}
            </section>
          ) : null}

          {view.mode === "company" && tab === "integrations" ? (
            <SettingsBaseCard
              error={sharedError}
              header={<SectionHeader eyebrow="AI & Integrations" title="JIRA va GitHub sozlamalari" />}
              onSave={saveShared}
              saveDisabled={savingShared}
              saveLabel="Saqlash"
              saving={savingShared}
              success={sharedSuccess}
            >
              <div className="mt-5 grid gap-4">
                <SettingsInnerCard>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">JIRA</p>
                  <div className="mt-3 grid gap-4">
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      label="JIRA Base URL"
                      onChange={(value) => updateField("jira_server", value)}
                      placeholder="https://yourcompany.atlassian.net"
                      value={form.jira_server}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      label="JIRA User Email"
                      onChange={(value) => updateField("jira_email", value)}
                      placeholder="admin@yourcompany.uz"
                      value={form.jira_email}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint={view.fields.jira_token_present ? "Bo'sh qoldirilsa mavjud token saqlanadi" : undefined}
                      label="JIRA Token"
                      onBlur={() => {
                        if (jiraTokenDirty && !form.jira_token.trim() && jiraTokenMask) {
                          setForm((current) => ({ ...current, jira_token: jiraTokenMask }));
                          setJiraTokenDirty(false);
                        }
                      }}
                      onChange={(value) => {
                        setJiraTokenDirty(true);
                        updateField("jira_token", value);
                      }}
                      onFocus={() => {
                        if (!jiraTokenDirty && form.jira_token === jiraTokenMask) {
                          setForm((current) => ({ ...current, jira_token: "" }));
                          setJiraTokenDirty(true);
                        }
                      }}
                      placeholder="ATATT..."
                      type="text"
                      value={form.jira_token}
                    />
                  </div>
                </SettingsInnerCard>

                <SettingsInnerCard>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">GitHub</p>
                  <div className="mt-3 grid gap-4">
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint={view.fields.github_token_present ? "Bo'sh qoldirilsa mavjud token saqlanadi" : undefined}
                      label="GitHub Token"
                      onBlur={() => {
                        if (githubTokenDirty && !form.github_token.trim() && githubTokenMask) {
                          setForm((current) => ({ ...current, github_token: githubTokenMask }));
                          setGithubTokenDirty(false);
                        }
                      }}
                      onChange={(value) => {
                        setGithubTokenDirty(true);
                        updateField("github_token", value);
                      }}
                      onFocus={() => {
                        if (!githubTokenDirty && form.github_token === githubTokenMask) {
                          setForm((current) => ({ ...current, github_token: "" }));
                          setGithubTokenDirty(true);
                        }
                      }}
                      placeholder="ghp_xxx..."
                      type="text"
                      value={form.github_token}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      label="GitHub Organization"
                      onChange={(value) => updateField("github_org", value)}
                      placeholder="your-org-name"
                      value={form.github_org}
                    />
                  </div>
                </SettingsInnerCard>

                <SettingsInnerCard>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Figma</p>
                  <div className="mt-3 grid gap-4">
                    {showFigmaToken ? (
                      <BaseInputField
                        className={SETTINGS_INPUT_CLASS}
                        hint={view.fields.figma_token_present ? "Bo'sh qoldirilsa mavjud token saqlanadi" : undefined}
                        label="Figma Token"
                        onBlur={() => {
                          if (figmaTokenDirty && !form.figma_token.trim() && figmaTokenMask) {
                            setForm((current) => ({ ...current, figma_token: figmaTokenMask }));
                            setFigmaTokenDirty(false);
                          }
                        }}
                        onChange={(value) => {
                          setFigmaTokenDirty(true);
                          updateField("figma_token", value);
                        }}
                        onFocus={() => {
                          if (!figmaTokenDirty && form.figma_token === figmaTokenMask) {
                            setForm((current) => ({ ...current, figma_token: "" }));
                            setFigmaTokenDirty(true);
                          }
                        }}
                        placeholder="figd_..."
                        type="text"
                        value={form.figma_token}
                      />
                    ) : (
                      <button
                        className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                        onClick={() => {
                          setShowFigmaToken(true);
                          setFigmaTokenDirty(true);
                          setForm((current) => ({ ...current, figma_token: "" }));
                        }}
                        type="button"
                      >
                        + Figma token qo&apos;shish
                      </button>
                    )}
                  </div>
                </SettingsInnerCard>

                <SettingsInnerCard>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Gemini</p>
                  <div className="mt-3 grid gap-4">
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      label="Gemini Model"
                      onChange={(value) => updateField("gemini_model", value)}
                      placeholder="gemini-2.5-flash"
                      value={form.gemini_model}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint={view.fields.gemini_api_key_1_present ? "Bo'sh qoldirilsa mavjud kalit saqlanadi" : undefined}
                      label="Gemini API Key 1"
                      onBlur={() => {
                        if (geminiKey1Dirty && !form.gemini_api_key_1.trim() && geminiKey1Mask) {
                          setForm((current) => ({ ...current, gemini_api_key_1: geminiKey1Mask }));
                          setGeminiKey1Dirty(false);
                        }
                      }}
                      onChange={(value) => {
                        setGeminiKey1Dirty(true);
                        updateField("gemini_api_key_1", value);
                      }}
                      onFocus={() => {
                        if (!geminiKey1Dirty && form.gemini_api_key_1 === geminiKey1Mask) {
                          setForm((current) => ({ ...current, gemini_api_key_1: "" }));
                          setGeminiKey1Dirty(true);
                        }
                      }}
                      placeholder="AIza..."
                      type="text"
                      value={form.gemini_api_key_1}
                    />
                    {showGeminiKey2 ? (
                      <BaseInputField
                        className={SETTINGS_INPUT_CLASS}
                        hint={view.fields.gemini_api_key_2_present ? "Bo'sh qoldirilsa mavjud kalit saqlanadi" : undefined}
                        label="Gemini API Key 2 (ixtiyoriy)"
                        onBlur={() => {
                          if (geminiKey2Dirty && !form.gemini_api_key_2.trim() && geminiKey2Mask) {
                            setForm((current) => ({ ...current, gemini_api_key_2: geminiKey2Mask }));
                            setGeminiKey2Dirty(false);
                          }
                        }}
                        onChange={(value) => {
                          setGeminiKey2Dirty(true);
                          updateField("gemini_api_key_2", value);
                        }}
                        onFocus={() => {
                          if (!geminiKey2Dirty && form.gemini_api_key_2 === geminiKey2Mask) {
                            setForm((current) => ({ ...current, gemini_api_key_2: "" }));
                            setGeminiKey2Dirty(true);
                          }
                        }}
                        placeholder="AIza..."
                        type="text"
                        value={form.gemini_api_key_2}
                      />
                    ) : (
                      <button
                        className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                        onClick={() => {
                          setShowGeminiKey2(true);
                          setGeminiKey2Dirty(true);
                          setForm((current) => ({ ...current, gemini_api_key_2: "" }));
                        }}
                        type="button"
                      >
                        + Yana qo&apos;shimcha key kerakmi?
                      </button>
                    )}
                  </div>
                </SettingsInnerCard>
              </div>

              <Notice className="mt-4" tone="info">
                ℹ️ Bu bo'limdagi Gemini key userlar uchun shared default bo'ladi. User o'zinikini kiritsa ustun turadi; hech biri bo'lmasa super admin default ishlatiladi.
              </Notice>
            </SettingsBaseCard>
          ) : null}

          {view.mode === "company" && hasWebhookModule && tab === "webhook" ? (
            <>

              {webhookLoading ? <p className="mt-3 text-sm text-muted-foreground">Webhook sozlamalari yuklanmoqda...</p> : null}
              {webhookHasError ? (
                <Notice className="mt-3" tone="warning">
                  {[whThresholdError ? "Return threshold 0-100 oralig'ida bo'lishi kerak." : null, whCheckerOrderError ? "Checker AI order ichida 'tz' va 'code' bo'lishi shart." : null, whAgent2BatchError ? "Agent2 batch size 1-20 bo'lishi shart." : null, whMinTzError ? "Min TZ belgilari 0 yoki undan katta bo'lishi kerak." : null, whMaxReadCommentsError ? "Max izohlar 0 yoki undan katta bo'lishi kerak." : null, whMaxSkipError ? "Max skip comment soni 1 yoki undan katta bo'lishi kerak." : null]
                    .filter(Boolean)
                    .join(" ")}
                </Notice>
              ) : null}

              <div className="g2 mt-4 items-start webhook-cards-grid">
                <SettingsBaseCard
                  className="webhook-shared-card"
                  customizerId="settings-webhook-shared"
                  description="Checker va Testcase uchun bir xil qo'llanadigan filtr va istisnolar."
                  dirty={webhookSharedDirty}
                  error={webhookSharedError}
                  onSave={() => saveWebhook("shared")}
                  saveDisabled={savingWebhook || webhookHasError}
                  saveLabel="Umumiy bo'limni saqlash"
                  saving={savingWebhook}
                  success={webhookSharedSuccess}
                  title="Servislar uchun umumiy"
                >
                  <SettingsCardSection
                    className="ssec mt-4 border-none pt-0"
                    icon={(
                      <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                      </svg>
                    )}
                    label="Filtrlar va istisnolar"
                  >
                    <div className="grid gap-3">
                      <SettingsCardItem>
                        <BaseInputField
                          className={SETTINGS_INPUT_CLASS}
                          hint="Faqat shu issue type'lar uchun webhook ishlaydi. Ikkala servis ham shu filtrlarga bo'ysunadi."
                          label="Ruxsat etilgan issue type'lar"
                          onChange={(value) => updateWebhookField("allowed_issue_types", value)}
                          placeholder="DEV-BUG,DEV-TECHTASK,DEV-CLIENT TASK"
                          value={webhookForm.allowed_issue_types}
                        />
                      </SettingsCardItem>
                      <SettingsCardItem>
                        <BaseInputField
                          className={SETTINGS_INPUT_CLASS}
                          hint="Vergul bilan ajrating. Bu assigneelardagi tasklarda checker ham testcase ham ishlamaydi."
                          label="Istisno assigneelar"
                          onChange={(value) => updateWebhookField("excluded_assignees", value)}
                          placeholder="bot-user, qa-auto, test-account"
                          value={webhookForm.excluded_assignees}
                        />
                      </SettingsCardItem>
                      <SettingsCardItem>
                        <NumberField
                          hint="TZ maydoni shu belgilardan kam bo'lsa checker ham testcase ham to'xtatiladi."
                          label="Min TZ belgilari"
                          min={0}
                          onChange={(value) => updateWebhookField("min_tz_description_chars", value)}
                          value={webhookForm.min_tz_description_chars}
                        />
                      </SettingsCardItem>
                    </div>
                  </SettingsCardSection>
                </SettingsBaseCard>

                <SettingsBaseCard
                  className="webhook-service-card webhook-service-card--main"
                  customizerId="settings-webhook-service1"
                  description="Trigger, return va checker comment sozlamalari."
                  dirty={webhookService1Dirty}
                  error={webhookService1Error}
                  onSave={() => saveWebhook("service1")}
                  saveDisabled={savingWebhook || webhookHasError}
                  saveLabel="Servis-1 ni saqlash"
                  saving={savingWebhook}
                  success={webhookService1Success}
                  title="Servis-1: Webhook TZ-PR"
                >
                  <div className="webhook-family-stack">
                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                          </svg>
                          Trigger sozlamalari
                        </div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <BaseInputField
                              className={SETTINGS_INPUT_CLASS}
                              hint="Webhook shu statusdagi JIRA tasklar uchun ishga tushadi"
                              label="Asosiy trigger status"
                              onChange={(nextMain) => {
                                setWhDirty(true);
                                setWebhookForm((current) => {
                                  return {
                                    ...current,
                                    trigger_status: nextMain,
                                    trigger_statuses: nextMain ? [nextMain] : [],
                                    trigger_status_aliases: "",
                                  };
                                });
                              }}
                              placeholder="READY TO TEST"
                              value={webhookForm.trigger_status}
                            />
                          </SettingsCardItem>
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Auto-return oilasi</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <ToggleRow
                              desc="Moslik bali threshold dan past bo'lsa JIRA taskni avtomatik qaytaradi."
                              label="Auto-return"
                              onChange={(value) => updateWebhookField("auto_return_enabled", value)}
                              value={webhookForm.auto_return_enabled}
                            />
                          </SettingsCardItem>
                          {webhookForm.auto_return_enabled ? (
                            <>
                              <div className="grid gap-3">
                                <SettingsCardItem>
                                  <BaseInputField
                                    className={SETTINGS_INPUT_CLASS}
                                    hint="Auto-return yoqilganda task qaytariladigan JIRA status nomi."
                                    label="Return status"
                                    onChange={(value) => updateWebhookField("return_status", value)}
                                    placeholder="NEED CLARIFICATION/RETURN TEST"
                                    value={webhookForm.return_status}
                                  />
                                </SettingsCardItem>
                                <SettingsCardItem>
                                  <NumberField
                                    hint="Bu foizdan past moslik — task qaytariladi (0-100)"
                                    label="Return threshold (%)"
                                    max={100}
                                    min={0}
                                    onChange={(value) => updateWebhookField("return_threshold", value)}
                                    value={webhookForm.return_threshold}
                                  />
                                </SettingsCardItem>
                              </div>
                              <SettingsCardItem>
                                <BaseInputField
                                  className={SETTINGS_INPUT_CLASS}
                                  hint="Auto-return holatida JIRA'ga yoziladigan notification matni."
                                  label="Qaytarish Notification Matn"
                                  onChange={(value) => updateWebhookField("return_notification_text", value)}
                                  value={webhookForm.return_notification_text ?? ""}
                                />
                              </SettingsCardItem>
                            </>
                          ) : null}
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Comment o'qish oilasi</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <ToggleRow
                              desc="Checker promptiga JIRA commentlarini qo'shadi."
                              label="Comment o'qish"
                              onChange={(value) => updateWebhookField("read_comments_enabled", value)}
                              value={webhookForm.read_comments_enabled}
                            />
                          </SettingsCardItem>
                          {webhookForm.read_comments_enabled ? (
                            <SettingsCardItem>
                              <NumberField
                                hint="0 = barcha commentlar."
                                label="Max commentlar"
                                min={0}
                                onChange={(value) => updateWebhookField("max_comments_to_read", value)}
                                value={webhookForm.max_comments_to_read}
                              />
                            </SettingsCardItem>
                          ) : null}
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Skip kodi oilasi</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <BaseInputField
                              className={SETTINGS_INPUT_CLASS}
                              hint="Task tavsifida yoki izohda bu kod bo'lsa — checker (Servis-1) skip bo'ladi."
                              label="Skip kodi"
                              onChange={(value) => updateWebhookField("skip_code", value)}
                              placeholder="AI_SKIP"
                              value={webhookForm.skip_code}
                            />
                          </SettingsCardItem>
                          {webhookForm.skip_code.trim() ? (
                            <>
                              <SettingsCardItem>
                                <NumberField
                                  hint="Skip kod qidirilganda oxirgi nechta comment tekshiriladi."
                                  label="Skip tekshirish comment soni"
                                  min={1}
                                  onChange={(value) => updateWebhookField("max_skip_check_comments", value)}
                                  value={webhookForm.max_skip_check_comments}
                                />
                              </SettingsCardItem>
                              <SettingsCardItem>
                                <BaseInputField
                                  className={SETTINGS_INPUT_CLASS}
                                  hint="SKIP topilganda JIRA'ga yoziladigan xabar matni. Bo'sh bo'lsa tizim default matn yozadi."
                                  label="SKIP xabar matni"
                                  onChange={(value) => updateWebhookField("skip_comment_text", value)}
                                  placeholder="Dev tomonidan skip ko'rsatma berilgan..."
                                  value={webhookForm.skip_comment_text ?? ""}
                                />
                              </SettingsCardItem>
                            </>
                          ) : null}
                        </div>
                      </div>
                    </SettingsInnerCard>
                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                          </svg>
                          📝 Comment bo'limlari
                        </div>
                        <BaseCheckGroup
                          onChange={(nextValues) => {
                            const hasContradictory = nextValues.includes("contradictory_comments");
                            setWhDirty(true);
                            setWebhookForm((current) => ({
                              ...current,
                              visible_sections: nextValues,
                              show_contradictory_comments: hasContradictory,
                            }));
                          }}
                          options={[
                            ...moduleAllowed.checker_visible_sections.map((sectionKey) => ({
                              key: sectionKey,
                              label: CHECKER_SECTION_LABELS[sectionKey as keyof typeof CHECKER_SECTION_LABELS] || sectionKey,
                            })),
                            {
                              key: "contradictory_comments",
                              label: CHECKER_SECTION_LABELS.contradictory_comments,
                            },
                          ]}
                          value={webhookForm.visible_sections}
                        />
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                          </svg>
                          📊 AI ga ma'lumotlar darajasi (tartibi)
                        </div>
                        <BaseOrderPills
                          available={["tz", "comments", "figma", "code"]}
                          onChange={(nextValue) => updateWebhookField("ai_data_section_order", nextValue)}
                          required={["tz", "code"]}
                          value={webhookForm.ai_data_section_order}
                        />
                        {!webhookForm.ai_data_section_order.includes("figma") ? (
                          <p className="mt-1 text-xs text-muted-foreground">Figma o'chirilgan: Agent1 Figma signalni requirementga aylantirmaydi.</p>
                        ) : null}
                        {whCheckerOrderError ? <p className="err-text mt-1">tz va code bo'lishi shart</p> : null}
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Agent modellari</div>
                        <div className="grid gap-3 md:grid-cols-2">
                          <NumberField
                            hint="1 = har talab alohida call, 6 = default batch."
                            label="Agent2 batch size"
                            max={20}
                            min={1}
                            onChange={(value) => updateWebhookField("agent2_batch_size", value)}
                            value={webhookForm.agent2_batch_size}
                          />
                          <div className="md:col-span-2">
                            <ToggleRow
                              desc="TZ da yo'q qo'shimcha kod o'zgarishlarni aniqlash."
                              label="Agent2 Extra scan"
                              onChange={(value) => updateWebhookField("agent2_extra_scan_enabled", value)}
                              value={Boolean(webhookForm.agent2_extra_scan_enabled)}
                            />
                          </div>
                          {[
                            ["agent1_primary_model", "Agent1 primary"],
                            ["agent1_fallback_model", "Agent1 fallback"],
                            ["agent2_primary_model", "Agent2 primary"],
                            ["agent2_fallback_model", "Agent2 fallback"],
                            ["agent3_primary_model", "Agent3 primary"],
                            ["agent3_fallback_model", "Agent3 fallback"],
                          ].map(([field, label]) => (
                            <BaseSelectField
                              className="settings-form-select"
                              key={field}
                              label={label}
                              onChange={(value) =>
                                updateWebhookField(field as keyof WebhookFormState, value)
                              }
                              value={String(webhookForm[field as keyof WebhookFormState] || "")}
                            >
                              {modelOptions().map((model) => (
                                <option key={model || "inherit"} value={model}>
                                  {model || "Global default"}
                                </option>
                              ))}
                            </BaseSelectField>
                          ))}
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                            <path d="M8 10h8" />
                            <path d="M8 14h6" />
                          </svg>
                          Mustaqil settinglar
                        </div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <BaseInputField
                              className={SETTINGS_INPUT_CLASS}
                              hint="Task qaytib kelib qayta tekshirilganda yoziladigan xabar."
                              label="Re-check Xabari"
                              onChange={(value) => updateWebhookField("recheck_comment_text", value)}
                              value={webhookForm.recheck_comment_text ?? ""}
                            />
                          </SettingsCardItem>
                          <SettingsCardItem>
                            <BaseInputField
                              className={SETTINGS_INPUT_CLASS}
                              hint="Checker JIRA commentining pastki qismidagi footer matni."
                              label="TZ-PR Comment Footer"
                              onChange={(value) => updateWebhookField("tz_pr_footer_text", value)}
                              value={webhookForm.tz_pr_footer_text ?? ""}
                            />
                          </SettingsCardItem>
                        </div>
                      </div>
                    </SettingsInnerCard>
                  </div>
                </SettingsBaseCard>

                <SettingsBaseCard
                  className="webhook-service-card webhook-service-card--main"
                  customizerId="settings-webhook-service2"
                  description="Auto-comment va testcase generation sozlamalari."
                  dirty={webhookService2Dirty}
                  error={webhookService2Error}
                  onSave={() => saveWebhook("service2")}
                  saveDisabled={savingWebhook || webhookHasError}
                  saveLabel="Servis-2 ni saqlash"
                  saving={savingWebhook}
                  success={webhookService2Success}
                  title="Servis-2: Webhook Testcase"
                >
                  <div className="webhook-family-stack">
                      {webhookForm.testcase_auto_comment_enabled ? (
                        <SettingsInnerCard>
                          <div className="ssec mt-0 border-none pt-0">
                            <div className="ssec-label">Trigger sozlamalari</div>
                            <div className="grid gap-3">
                              <SettingsCardItem>
                                <BaseInputField
                                  className={SETTINGS_INPUT_CLASS}
                                  label="Asosiy trigger status"
                                  onChange={(value) => updateWebhookField("testcase_auto_comment_trigger_status", value)}
                                  placeholder="READY TO TEST"
                                  value={webhookForm.testcase_auto_comment_trigger_status ?? ""}
                                />
                              </SettingsCardItem>
                            </div>
                          </div>
                        </SettingsInnerCard>
                      ) : null}

                      <SettingsInnerCard>
                        <div className="ssec mt-0 border-none pt-0">
                          <div className="ssec-label">Auto-comment oilasi</div>
                          <div className="grid gap-3">
                            <SettingsCardItem>
                              <ToggleRow
                                desc="Webhook trigger bo'lganda testcase'larni avtomatik yaratib JIRA'ga yozadi."
                                label="Auto-comment yoqilgan"
                                onChange={(value) => updateWebhookField("testcase_auto_comment_enabled", value)}
                                value={webhookForm.testcase_auto_comment_enabled}
                              />
                            </SettingsCardItem>

                            {webhookForm.testcase_auto_comment_enabled ? (
                              <>
                                <SettingsCardItem>
                                  <ToggleRow
                                    desc="Default holatda PR ma'lumotlari testcase generatsiyaga qo'shiladi."
                                    label="Default include PR"
                                    onChange={(value) => updateWebhookField("testcase_default_include_pr", value)}
                                    value={webhookForm.testcase_default_include_pr}
                                  />
                                </SettingsCardItem>
                                <SettingsCardItem>
                                  <ToggleRow
                                    desc="Default holatda smart patch ishlatiladi."
                                    label="Default smart patch"
                                    onChange={(value) => updateWebhookField("testcase_default_use_smart_patch", value)}
                                    value={webhookForm.testcase_default_use_smart_patch}
                                  />
                                </SettingsCardItem>
                              </>
                            ) : null}
                          </div>
                        </div>
                      </SettingsInnerCard>

                      {webhookForm.testcase_auto_comment_enabled ? (
                        <>
                          <SettingsInnerCard>
                            <div className="ssec mt-0 border-none pt-0">
                              <div className="ssec-label">Comment o'qish oilasi</div>
                              <div className="grid gap-3">
                                <SettingsCardItem>
                                  <ToggleRow
                                    desc="JIRA commentlar testcase AI contextiga qo'shiladi."
                                    label="Commentlarni o'qish"
                                    onChange={(value) => updateWebhookField("testcase_read_comments_enabled", value)}
                                    value={webhookForm.testcase_read_comments_enabled}
                                  />
                                </SettingsCardItem>
                                {webhookForm.testcase_read_comments_enabled ? (
                                  <SettingsCardItem>
                                    <NumberField
                                      hint="0 = hammasi."
                                      label="Max comments"
                                      min={0}
                                      onChange={(value) => updateWebhookField("testcase_max_comments_to_read", value)}
                                      value={webhookForm.testcase_max_comments_to_read}
                                    />
                                  </SettingsCardItem>
                                ) : null}
                              </div>
                            </div>
                          </SettingsInnerCard>

                          <SettingsInnerCard>
                            <div className="ssec mt-0 border-none pt-0">
                              <div className="ssec-label">📊 AI ga ma'lumotlar darajasi (tartibi)</div>
                              <div className="grid gap-3">
                                <SettingsCardItem>
                                  <BaseOrderPills
                                    available={["tz", "comments", "custom_context", "code"]}
                                    onChange={(nextValue) => updateWebhookField("testcase_ai_data_section_order", nextValue)}
                                    required={["tz"]}
                                    value={webhookForm.testcase_ai_data_section_order}
                                  />
                                </SettingsCardItem>
                              </div>
                            </div>
                          </SettingsInnerCard>

                          <SettingsInnerCard>
                            <div className="ssec mt-0 border-none pt-0">
                              <div className="ssec-label">Mustaqil settinglar</div>
                              <div className="grid gap-3">
                                <SettingsCardItem>
                                  <div className="ssec mt-0 border-none pt-0">
                                    <div className="ssec-label">Default test turlari</div>
                                    <BaseCheckGroup
                                      onChange={(nextValues) => updateWebhookField("testcase_default_test_types", nextValues)}
                                      options={moduleAllowed.testcase_types.map((typeKey) => ({
                                        key: typeKey,
                                        label: testcaseTypeLabels[typeKey] || typeKey,
                                        badge: typeKey,
                                      }))}
                                      value={webhookForm.testcase_default_test_types}
                                    />
                                  </div>
                                </SettingsCardItem>
                                <SettingsCardItem>
                                  <NumberField
                                    hint="1-50 oralig'ida."
                                    label="Max test cases"
                                    max={50}
                                    min={1}
                                    onChange={(value) => updateWebhookField("testcase_max_test_cases", value)}
                                    value={webhookForm.testcase_max_test_cases}
                                  />
                                </SettingsCardItem>
                                <SettingsCardItem>
                                  <BaseInputField
                                    className={SETTINGS_INPUT_CLASS}
                                    label="Testcase footer matni"
                                    onChange={(value) => updateWebhookField("testcase_footer_text", value)}
                                    value={webhookForm.testcase_footer_text ?? ""}
                                  />
                                </SettingsCardItem>
                              </div>
                            </div>
                          </SettingsInnerCard>
                        </>
                      ) : null}
                  </div>
                </SettingsBaseCard>

              </div>
            </>
          ) : null}

          {view.mode === "company" && hasWebhookModule && tab === "webhook" ? (
            <SettingsBaseCard
              customizerId="settings-webhook-system"
              description="Queue va retry policy kabi umumiy ishlash parametrlari."
              dirty={systemDirty}
              error={systemError}
              onSave={saveSystem}
              saveDisabled={savingSystem || systemHasError}
              saveLabel="Saqlash"
              saving={savingSystem}
              success={systemSuccess}
              title="Tizim sozlamalari"
            >
              {systemLoading ? <p className="mt-3 text-sm text-muted-foreground">Tizim sozlamalari yuklanmoqda...</p> : null}
              {systemHasError ? (
                <Notice className="mt-3" tone="warning">
                  Tizim maydonlarida noto'g'ri qiymat bor. Barcha sonli maydonlar 1 yoki undan katta bo'lishi kerak.
                </Notice>
              ) : null}

              <SettingsCardSection className="ssec mt-4 border-none pt-0">
                <ToggleRow
                  desc="Yoqilsa tasklar bittalab ketadi. O'chirilsa ko'p task birdan ketadi va xato ko'payishi mumkin."
                  label="Queue yoqilgan"
                  onChange={(value) => updateSystemField("queue_enabled", value)}
                  value={systemForm.queue_enabled}
                />
              </SettingsCardSection>

              <SettingsCardSection label="Asosiy ishlash">
                <div className="g2">
                  {systemForm.queue_enabled ? (
                    <NumberField
                      hint="Task navbatda qancha kutadi. Shu vaqt ichida navbat kelmasa task vaqtincha to'xtaydi (blocked)."
                      label="Task wait timeout (sec)"
                      min={1}
                      onChange={(value) => updateSystemField("task_wait_timeout", value)}
                      value={systemForm.task_wait_timeout}
                    />
                  ) : null}
                  <NumberField
                    hint="Checker tugagach testcase boshlanishidan oldin qancha kutish. Kichik bo'lsa tezroq, katta bo'lsa barqarorroq."
                    label="Checker->Testcase delay (sec)"
                    min={1}
                    onChange={(value) => updateSystemField("checker_testcase_delay", value)}
                    value={systemForm.checker_testcase_delay}
                  />
                  {systemForm.queue_enabled ? (
                    <NumberField
                      hint="AI chaqiruvlari orasidagi pauza. Juda kichik bo'lsa AI limitga urilishi mumkin."
                      label="Gemini min interval (sec)"
                      min={1}
                      onChange={(value) => updateSystemField("gemini_min_interval", value)}
                      value={systemForm.gemini_min_interval}
                    />
                  ) : null}
                  <NumberField
                    hint="Blocked bo'lgan taskni necha daqiqadan keyin yana urinib ko'rish."
                    label="Blocked retry delay (min)"
                    min={1}
                    onChange={(value) => updateSystemField("blocked_retry_delay", value)}
                    value={systemForm.blocked_retry_delay}
                  />
                </div>
              </SettingsCardSection>

              <SettingsCardSection label="Retry va limitlar">
                <div className="g2">
                  <NumberField
                    hint="Tizim blocked tasklarni har necha sekundda tekshiradi."
                    label="Blocked check interval (sec)"
                    min={1}
                    onChange={(value) => updateSystemField("blocked_check_interval", value)}
                    value={systemForm.blocked_check_interval}
                  />
                </div>
              </SettingsCardSection>
            </SettingsBaseCard>
          ) : null}

          {view.mode === "company" && tab === "modules" ? (
            <>
              {modulesLoading ? <p className="mt-3 text-sm text-muted-foreground">Module sozlamalari yuklanmoqda...</p> : null}
              {moduleHasError ? (
                <Notice className="mt-3" tone="warning">
                  {[testcaseCountError ? "Max test cases 1-50 bo'lishi shart." : null, checkerOrderError ? "Checker order ichida tz va code bo'lishi shart." : null, checkerBatchError ? "Agent2 batch size 1-20 bo'lishi shart." : null, testcaseOrderError ? "Testcase order ichida tz bo'lishi shart." : null]
                    .filter(Boolean)
                    .join(" ")}
                </Notice>
              ) : null}

              <div className="webhook-cards-grid mt-4">
                <SettingsBaseCard
                  className="webhook-service-card webhook-service-card--main"
                  collapsible
                  customizerId="settings-module-checker"
                  description="Spec va pull request mosligini tekshirish sozlamalari."
                  dirty={checkerDirty}
                  error={modulesCheckerError}
                  icon={(
                    <div className="scard-icon scard-icon-tzpr">
                      <svg fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" width="20">
                        <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18" />
                      </svg>
                    </div>
                  )}
                  onSave={() => saveModules("checker")}
                  saveDisabled={savingModules || moduleHasError}
                  saveLabel="Checker ni saqlash"
                  saving={savingModules}
                  success={modulesCheckerSuccess}
                  title="TZ-PR Checker"
                >
                  <div className="webhook-family-stack">
                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Default ishga tushirish</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <ToggleRow
                              desc="AI faqat o'zgargan kod qismlarini tahlil qiladi — tezroq va tejamkor."
                              label="Smart Patch (default)"
                              onChange={(value) => updateCheckerField("default_use_smart_patch", value)}
                              value={Boolean(moduleForm.checker.default_use_smart_patch)}
                            />
                          </SettingsCardItem>
                          <SettingsCardItem>
                            <NumberField
                              hint="1 = har talab alohida call, 6 = default batch."
                              label="Agent2 batch size"
                              max={20}
                              min={1}
                              onChange={(value) => updateCheckerField("agent2_batch_size", value)}
                              value={moduleForm.checker.agent2_batch_size}
                            />
                          </SettingsCardItem>
                          <SettingsCardItem>
                            <ToggleRow
                              desc="TZ da yo'q qo'shimcha kod o'zgarishlarni aniqlash."
                              label="Agent2 Extra scan"
                              onChange={(value) => updateCheckerField("agent2_extra_scan_enabled", value)}
                              value={Boolean(moduleForm.checker.agent2_extra_scan_enabled)}
                            />
                          </SettingsCardItem>
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Comment o'qish oilasi</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <ToggleRow
                              desc="JIRA task izohlarini AI tahlilga qo'shadi."
                              label="Izohlarni o'qish"
                              onChange={(value) => updateCheckerField("read_comments_enabled", value)}
                              value={Boolean(moduleForm.checker.read_comments_enabled)}
                            />
                          </SettingsCardItem>
                          {moduleForm.checker.read_comments_enabled ? (
                            <>
                              <SettingsCardItem>
                                <NumberField
                                  hint="0 = barchasi o'qiladi, boshqa son = shu miqdor bilan cheklanadi."
                                  label="Max izohlar"
                                  min={0}
                                  onChange={(value) => updateCheckerField("max_comments_to_read", value)}
                                  value={moduleForm.checker.max_comments_to_read}
                                />
                              </SettingsCardItem>
                              <SettingsCardItem>
                                <BaseInputField
                                  className={SETTINGS_INPUT_CLASS}
                                  hint="Vergul bilan ajrating. Faqat shu authorlar comment orqali scope o'zgartira oladi."
                                  label="Trusted scope comment authorlar"
                                  onChange={(value) => updateCheckerField("trusted_scope_comment_authors", value)}
                                  placeholder="QA Lead, Product Owner"
                                  value={moduleForm.checker.trusted_scope_comment_authors}
                                />
                              </SettingsCardItem>
                            </>
                          ) : null}
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                          </svg>
                          Comment bo'limlari
                        </div>
                        <BaseCheckGroup
                          onChange={(nextValues) => updateCheckerField("visible_sections", nextValues)}
                          options={moduleAllowed.checker_visible_sections.map((sectionKey) => ({
                            key: sectionKey,
                            label: CHECKER_SECTION_LABELS[sectionKey as keyof typeof CHECKER_SECTION_LABELS] || sectionKey,
                          }))}
                          value={moduleForm.checker.visible_sections}
                        />
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                          </svg>
                          AI ga ma'lumotlar darajasi (tartibi)
                        </div>
                        <BaseOrderPills
                          available={["tz", "comments", "figma", "code"]}
                          onChange={(nextValue) => updateModuleOrderField("checker", "ai_data_section_order", nextValue)}
                          required={["tz", "code"]}
                          value={moduleForm.checker.ai_data_section_order}
                        />
                        {!moduleForm.checker.ai_data_section_order.includes("figma") ? (
                          <p className="mt-1 text-xs text-muted-foreground">Figma o'chirilgan: Agent1 Figma signalni requirementga aylantirmaydi.</p>
                        ) : null}
                        {checkerOrderError ? <p className="err-text mt-1">tz va code bo'lishi shart</p> : null}
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Agent modellari</div>
                        <div className="grid gap-3 md:grid-cols-2">
                          {[
                            ["agent1_primary_model", "Agent1 primary"],
                            ["agent1_fallback_model", "Agent1 fallback"],
                            ["agent2_primary_model", "Agent2 primary"],
                            ["agent2_fallback_model", "Agent2 fallback"],
                            ["agent3_primary_model", "Agent3 primary"],
                            ["agent3_fallback_model", "Agent3 fallback"],
                          ].map(([field, label]) => (
                            <BaseSelectField
                              className="settings-form-select"
                              key={field}
                              label={label}
                              onChange={(value) =>
                                updateCheckerField(field as keyof ModuleFormState["checker"], value)
                              }
                              value={String(moduleForm.checker[field as keyof ModuleFormState["checker"]] || "")}
                            >
                              {modelOptions().map((model) => (
                                <option key={model || "inherit"} value={model}>
                                  {model || "Global default"}
                                </option>
                              ))}
                            </BaseSelectField>
                          ))}
                        </div>
                      </div>
                    </SettingsInnerCard>
                  </div>
                </SettingsBaseCard>

                <SettingsBaseCard
                  className="webhook-service-card webhook-service-card--main"
                  collapsible
                  customizerId="settings-module-testcase"
                  description="AI orqali QA test scenariylarini yaratish sozlamalari."
                  dirty={testcaseDirty}
                  error={modulesTestcaseError}
                  icon={(
                    <div className="scard-icon scard-icon-tc">
                      <svg fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" width="20">
                        <path d="M9 11l3 3L22 4" />
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                      </svg>
                    </div>
                  )}
                  onSave={() => saveModules("testcase")}
                  saveDisabled={savingModules || moduleHasError}
                  saveLabel="Testcase ni saqlash"
                  saving={savingModules}
                  success={modulesTestcaseSuccess}
                  title="Test Case Generator"
                >
                  <div className="webhook-family-stack">
                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Default ishga tushirish</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <ToggleRow
                              desc="Defolt ravishda PR tahlilini test case generatsiyaga qo'shadi."
                              label="PR biriktirish (default)"
                              onChange={(value) => updateTestcaseField("default_include_pr", value)}
                              value={Boolean(moduleForm.testcase.default_include_pr)}
                            />
                          </SettingsCardItem>
                          <SettingsCardItem>
                            <ToggleRow
                              desc="AI faqat o'zgargan kod qismlarini tahlil qiladi."
                              label="Smart Patch (default)"
                              onChange={(value) => updateTestcaseField("default_use_smart_patch", value)}
                              value={Boolean(moduleForm.testcase.default_use_smart_patch)}
                            />
                          </SettingsCardItem>
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Comment o'qish oilasi</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <ToggleRow
                              desc="JIRA task izohlarini generatsiyaga qo'shadi."
                              label="Izohlarni o'qish"
                              onChange={(value) => updateTestcaseField("read_comments_enabled", value)}
                              value={Boolean(moduleForm.testcase.read_comments_enabled)}
                            />
                          </SettingsCardItem>
                          {moduleForm.testcase.read_comments_enabled ? (
                            <SettingsCardItem>
                              <NumberField
                                hint="0 = barchasi."
                                label="Max izohlar"
                                min={0}
                                onChange={(value) => updateTestcaseField("max_comments_to_read", value)}
                                value={moduleForm.testcase.max_comments_to_read}
                              />
                            </SettingsCardItem>
                          ) : null}
                        </div>
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">
                          <svg fill="none" height="13" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" width="13">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                          </svg>
                          AI ga ma'lumotlar darajasi (tartibi)
                        </div>
                        <BaseOrderPills
                          available={["tz", "comments", "custom_context", "code"]}
                          onChange={(nextValue) => updateModuleOrderField("testcase", "ai_data_section_order", nextValue)}
                          required={["tz"]}
                          value={moduleForm.testcase.ai_data_section_order}
                        />
                        {testcaseOrderError ? <p className="err-text mt-1">tz bo'lishi shart</p> : null}
                      </div>
                    </SettingsInnerCard>

                    <SettingsInnerCard>
                      <div className="ssec mt-0 border-none pt-0">
                        <div className="ssec-label">Mustaqil settinglar</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <div className="ssec mt-0 border-none pt-0">
                              <div className="ssec-label">Default test turlari</div>
                              <BaseCheckGroup
                                onChange={(nextValues) => updateTestcaseField("default_test_types", nextValues)}
                                options={moduleAllowed.testcase_types.map((typeKey) => ({
                                  key: typeKey,
                                  label: testcaseTypeLabels[typeKey] || typeKey,
                                  badge: typeKey,
                                }))}
                                value={moduleForm.testcase.default_test_types}
                              />
                            </div>
                          </SettingsCardItem>
                          <SettingsCardItem>
                            <NumberField
                              hint="Har bir generatsiyada maksimum shu qadar test case yaratiladi."
                              label="Max test cases"
                              max={50}
                              min={1}
                              onChange={(value) => updateTestcaseField("max_test_cases", value)}
                              required
                              value={moduleForm.testcase.max_test_cases}
                            />
                          </SettingsCardItem>
                        </div>
                      </div>
                    </SettingsInnerCard>
                  </div>
                </SettingsBaseCard>
              </div>
            </>
          ) : null}

          {view.mode === "user" ? (
            <SettingsBaseCard
              error={sharedError}
              header={(
                <SectionHeader
                  eyebrow="AI & Integrations"
                  title="Shaxsiy Gemini sozlamalari"
                  action={<Badge>{role || "user"}</Badge>}
                />
              )}
              onSave={saveShared}
              saveDisabled={savingShared}
              saveLabel="Saqlash"
              saving={savingShared}
              success={sharedSuccess}
            >
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                JIRA, GitHub va Figma konfiguratsiyasi kompaniya admini tomonidan boshqariladi.
              </p>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <BaseInputField
                  className={SETTINGS_INPUT_CLASS}
                  label="Model"
                  onChange={(value) => updateField("gemini_model", value)}
                  placeholder="gemini-2.5-flash"
                  value={form.gemini_model}
                />
                <div />
                <BaseInputField
                  className={SETTINGS_INPUT_CLASS}
                  hint={view.fields.gemini_api_key_1_present ? "Bo'sh qoldirilsa mavjud kalit saqlanadi" : undefined}
                  label="API Key 1"
                  onChange={(value) => updateField("gemini_api_key_1", value)}
                  placeholder={view.fields.gemini_api_key_1_present ? "••••••••" : "AIza..."}
                  type="password"
                  value={form.gemini_api_key_1}
                />
                <BaseInputField
                  className={SETTINGS_INPUT_CLASS}
                  hint={view.fields.gemini_api_key_2_present ? "Bo'sh qoldirilsa mavjud kalit saqlanadi" : undefined}
                  label="API Key 2 (ixtiyoriy)"
                  onChange={(value) => updateField("gemini_api_key_2", value)}
                  placeholder={view.fields.gemini_api_key_2_present ? "••••••••" : "AIza..."}
                  type="password"
                  value={form.gemini_api_key_2}
                />
              </div>
              <Notice className="mt-4" tone="info">
                ℹ️ Agar API key kiritmasangiz, avval admin sozlagan shared key, bo'lmasa super admin default Gemini key ishlatiladi.
              </Notice>
            </SettingsBaseCard>
          ) : null}
        </>
      ) : null}
    </>
  );
}
