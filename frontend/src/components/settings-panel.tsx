"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { PageIntro } from "@/components/ui/page-intro";
import { SectionHeader } from "@/components/ui/section-header";
import {
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

const CHECKER_COMMENT_SECTIONS = ["completed", "failed", "skipped", "issues", "figma"];

type SettingsPanelProps = {
  companyName: string;
  hasCheckerModule: boolean;
  hasService1: boolean;
  hasService2: boolean;
  hasTestcaseModule: boolean;
  hasWebhookModule: boolean;
  role: UserRole | null | undefined;
};

type SettingsTab = "integrations" | "webhook" | "modules";

type FigmaTokenEntry = {
  name: string;
  token: string; // joriy input qiymati (o'zgarmagan token uchun mask)
  mask: string; // saqlangan mask ("" — yangi token)
  dirty: boolean; // qiymat o'zgartirildi
  isNew: boolean; // shu sessiyada qo'shilgan (mavjud emas)
  origIdx: number | null; // saqlangan figma_tokens dagi indeks (keep uchun)
};

type SettingsFormState = {
  jira_server: string;
  jira_email: string;
  jira_project_keys: string;
  github_org: string;
  figma_token: string;
  jira_token: string;
  github_token: string;
  gemini_api_key_1: string;
  gemini_api_key_2: string;
};

type WebhookFormState = {
  auto_return_enabled: boolean;
  allowed_issue_types: string;
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
  dev_comment_source: string;
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
  testcase_default_test_types: string[];
  testcase_testcases_per_requirement: string;
  testcase_ai_data_section_order: string[];
  testcase_read_comments_enabled: boolean;
  testcase_max_comments_to_read: string;
  testcase_footer_text: string;
  testcase_agent1_primary_model: string;
  testcase_agent1_fallback_model: string;
  testcase_agent2_primary_model: string;
  testcase_agent2_fallback_model: string;
  testcase_agent3_primary_model: string;
  testcase_agent3_fallback_model: string;
  agent1_primary_model: string;
  agent1_fallback_model: string;
  agent2_batch_size: string;
  agent2_extra_scan_enabled: boolean;
  agent2_primary_model: string;
  agent2_fallback_model: string;
  agent3_primary_model: string;
  agent3_fallback_model: string;
};

type WebhookTriggerConfiguredState = {
  service1: boolean;
  service2: boolean;
};

type ModuleFormState = {
  checker: {
    visible_sections: string[];
    ai_data_section_order: string[];
    read_comments_enabled: boolean;
    max_comments_to_read: string;
    trusted_scope_comment_authors: string;
    dev_comment_source: string;
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
    default_test_types: string[];
    testcases_per_requirement: string;
    ai_data_section_order: string[];
    read_comments_enabled: boolean;
    max_comments_to_read: string;
    agent1_primary_model: string;
    agent1_fallback_model: string;
    agent2_primary_model: string;
    agent2_fallback_model: string;
    agent3_primary_model: string;
    agent3_fallback_model: string;
  };
};

const EMPTY_FORM: SettingsFormState = {
  jira_server: "",
  jira_email: "",
  jira_project_keys: "",
  github_org: "",
  figma_token: "",
  jira_token: "",
  github_token: "",
  gemini_api_key_1: "",
  gemini_api_key_2: "",
};

const EMPTY_WEBHOOK_FORM: WebhookFormState = {
  auto_return_enabled: false,
  allowed_issue_types: "",
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
  dev_comment_source: "assignee_reporter",
  show_contradictory_comments: true,
  visible_sections: CHECKER_COMMENT_SECTIONS,
  ai_data_section_order: ["tz", "comments", "figma", "code"],
  skip_code: "AI_SKIP",
  skip_comment_text: "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi.",
  trigger_status: "READY TO TEST",
  trigger_status_aliases: "",
  trigger_statuses: ["READY TO TEST"],
  testcase_auto_comment_enabled: false,
  testcase_auto_comment_trigger_status: "READY TO TEST",
  testcase_auto_comment_trigger_aliases: "Ready To Test,READY TO TEST",
  testcase_default_test_types: ["positive", "negative"],
  testcase_testcases_per_requirement: "3",
  testcase_ai_data_section_order: ["tz", "comments", "custom_context", "code"],
  testcase_read_comments_enabled: true,
  testcase_max_comments_to_read: "0",
  testcase_footer_text: "🤖 Test case'lar AI (Gemini) tomonidan avtomatik yaratilgan. QA Team tomonidan tekshirilishi va to'ldirilishi kerak.",
  testcase_agent1_primary_model: "",
  testcase_agent1_fallback_model: "",
  testcase_agent2_primary_model: "",
  testcase_agent2_fallback_model: "",
  testcase_agent3_primary_model: "",
  testcase_agent3_fallback_model: "",
  agent1_primary_model: "",
  agent1_fallback_model: "",
  agent2_batch_size: "6",
  agent2_extra_scan_enabled: true,
  agent2_primary_model: "",
  agent2_fallback_model: "",
  agent3_primary_model: "",
  agent3_fallback_model: "",
};

const EMPTY_WEBHOOK_TRIGGER_CONFIGURED: WebhookTriggerConfiguredState = {
  service1: false,
  service2: false,
};

const DEFAULT_MODULE_ALLOWED: ModuleSettingsAllowed = {
  checker_visible_sections: CHECKER_COMMENT_SECTIONS,
  checker_ai_data_order: ["tz", "comments", "figma", "code"],
  testcase_ai_data_order: ["tz", "comments", "custom_context", "code"],
  testcase_types: ["positive", "negative", "boundary", "edge"],
};

const EMPTY_MODULE_FORM: ModuleFormState = {
  checker: {
    visible_sections: CHECKER_COMMENT_SECTIONS,
    ai_data_section_order: ["tz", "comments", "figma", "code"],
    read_comments_enabled: true,
    max_comments_to_read: "0",
    trusted_scope_comment_authors: "",
    dev_comment_source: "assignee_reporter",
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
    default_test_types: ["positive", "negative"],
    testcases_per_requirement: "3",
    ai_data_section_order: ["tz", "comments", "custom_context", "code"],
    read_comments_enabled: true,
    max_comments_to_read: "0",
    agent1_primary_model: "",
    agent1_fallback_model: "",
    agent2_primary_model: "",
    agent2_fallback_model: "",
    agent3_primary_model: "",
    agent3_fallback_model: "",
  },
};

const SETTINGS_INPUT_CLASS = "settings-form-input";

function CredHelp({ href }: { href: string }) {
  return (
    <>
      {" · "}
      <a className="text-primary underline whitespace-nowrap" href={href} rel="noopener noreferrer" target="_blank">
        Qayerdan olaman? →
      </a>
    </>
  );
}

function modelOptions() {
  return ["", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"];
}

export function SettingsPanel({
  companyName,
  hasCheckerModule,
  hasService1,
  hasService2,
  hasTestcaseModule,
  hasWebhookModule,
  role,
}: SettingsPanelProps) {
  const [loading, setLoading] = useState(true);
  const [savingShared, setSavingShared] = useState(false);
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [savingModules, setSavingModules] = useState(false);
  const [webhookLoading, setWebhookLoading] = useState(false);
  const [modulesLoading, setModulesLoading] = useState(false);
  const [checkerDirty, setCheckerDirty] = useState(false);
  const [testcaseDirty, setTestcaseDirty] = useState(false);
  const [whDirty, setWhDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sharedError, setSharedError] = useState<string | null>(null);
  const [webhookSharedError, setWebhookSharedError] = useState<string | null>(null);
  const [webhookService1Error, setWebhookService1Error] = useState<string | null>(null);
  const [webhookService2Error, setWebhookService2Error] = useState<string | null>(null);
  const [modulesCheckerError, setModulesCheckerError] = useState<string | null>(null);
  const [modulesTestcaseError, setModulesTestcaseError] = useState<string | null>(null);
  const [sharedSuccess, setSharedSuccess] = useState<string | null>(null);
  const [webhookSharedSuccess, setWebhookSharedSuccess] = useState<string | null>(null);
  const [webhookService1Success, setWebhookService1Success] = useState<string | null>(null);
  const [webhookService2Success, setWebhookService2Success] = useState<string | null>(null);
  const [modulesCheckerSuccess, setModulesCheckerSuccess] = useState<string | null>(null);
  const [modulesTestcaseSuccess, setModulesTestcaseSuccess] = useState<string | null>(null);
  const [view, setView] = useState<SharedSettingsView | null>(null);
  const [tab, setTab] = useState<SettingsTab>("integrations");
  const [form, setForm] = useState<SettingsFormState>(EMPTY_FORM);
  const [webhookForm, setWebhookForm] = useState<WebhookFormState>(EMPTY_WEBHOOK_FORM);
  const [webhookBaseline, setWebhookBaseline] = useState<WebhookFormState>(EMPTY_WEBHOOK_FORM);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookUrlCopied, setWebhookUrlCopied] = useState(false);

  const [webhookSecretGenerating, setWebhookSecretGenerating] = useState(false);
  const [webhookSecretError, setWebhookSecretError] = useState<string | null>(null);

  const webhookSecretMissing = Boolean(webhookUrl) && !webhookUrl.includes("token=");
  const maskedWebhookUrl = webhookUrl.replace(/(token=)[^&]+/, "$1••••••••");
  const copyWebhookUrl = async () => {
    try {
      await navigator.clipboard.writeText(webhookUrl);
      setWebhookUrlCopied(true);
      setTimeout(() => setWebhookUrlCopied(false), 2000);
    } catch {
      // clipboard ruxsati yo'q — foydalanuvchi URL'ni qo'lda belgilab nusxalaydi
    }
  };
  const generateWebhookSecret = async () => {
    setWebhookSecretGenerating(true);
    setWebhookSecretError(null);
    try {
      const response = await fetch("/api/settings/webhook/secret", { method: "POST" });
      const payload = (await response.json().catch(() => null)) as
        | { success?: boolean; webhook_url?: string; error?: string }
        | null;
      if (!response.ok || !payload?.success || !payload.webhook_url) {
        setWebhookSecretError(payload?.error || "Webhook parol yaratilmadi.");
        return;
      }
      setWebhookUrl(String(payload.webhook_url));
    } catch {
      setWebhookSecretError("Webhook parol yaratilmadi.");
    } finally {
      setWebhookSecretGenerating(false);
    }
  };
  const [webhookTriggerConfigured, setWebhookTriggerConfigured] = useState<WebhookTriggerConfiguredState>(
    EMPTY_WEBHOOK_TRIGGER_CONFIGURED,
  );
  const [moduleForm, setModuleForm] = useState<ModuleFormState>(EMPTY_MODULE_FORM);
  const [moduleAllowed, setModuleAllowed] = useState<ModuleSettingsAllowed>(DEFAULT_MODULE_ALLOWED);
  const [jiraTokenMask, setJiraTokenMask] = useState("");
  const [githubTokenMask, setGithubTokenMask] = useState("");
  const [geminiKey1Mask, setGeminiKey1Mask] = useState("");
  const [geminiKey2Mask, setGeminiKey2Mask] = useState("");
  const [jiraTokenDirty, setJiraTokenDirty] = useState(false);
  const [githubTokenDirty, setGithubTokenDirty] = useState(false);
  const [geminiKey1Dirty, setGeminiKey1Dirty] = useState(false);
  const [geminiKey2Dirty, setGeminiKey2Dirty] = useState(false);
  const [showGeminiKey2, setShowGeminiKey2] = useState(false);
  const [clearedCreds, setClearedCreds] = useState<Record<string, boolean>>({});
  const [figmaTokens, setFigmaTokens] = useState<FigmaTokenEntry[]>([]);
  const [figmaListDirty, setFigmaListDirty] = useState(false);

  const checkerOrderError = !moduleForm.checker.ai_data_section_order.includes("tz")
    || !moduleForm.checker.ai_data_section_order.includes("code");
  const checkerBatchError = Number(moduleForm.checker.agent2_batch_size || "0") < 1
    || Number(moduleForm.checker.agent2_batch_size || "0") > 20;
  const testcaseOrderError = !moduleForm.testcase.ai_data_section_order.includes("tz");
  const testcaseCountError = Number(moduleForm.testcase.testcases_per_requirement || "0") < 1
    || Number(moduleForm.testcase.testcases_per_requirement || "0") > 3;
  const moduleHasError = checkerOrderError || checkerBatchError || testcaseOrderError || testcaseCountError;
  const whThresholdError = webhookForm.auto_return_enabled
    && (Number(webhookForm.return_threshold || "0") < 0
      || Number(webhookForm.return_threshold || "0") > 100);
  const whCheckerOrderError = !webhookForm.ai_data_section_order.includes("tz")
    || !webhookForm.ai_data_section_order.includes("code");
  const whAgent2BatchError = Number(webhookForm.agent2_batch_size || "0") < 1
    || Number(webhookForm.agent2_batch_size || "0") > 20;
  const whMinTzError = Number(webhookForm.min_tz_description_chars || "0") < 0;
  const whCommentWindowVisible = webhookForm.read_comments_enabled || Boolean(webhookForm.skip_code.trim());
  const whMaxReadCommentsError = whCommentWindowVisible
    && Number(webhookForm.max_comments_to_read || "0") < 0;
  const whMaxSkipError = Boolean(webhookForm.skip_code.trim()) && Number(webhookForm.max_skip_check_comments || "0") < 1;
  const whSkipWindowError = Boolean(webhookForm.skip_code.trim())
    && Number(webhookForm.max_comments_to_read || "0") > 0
    && Number(webhookForm.max_skip_check_comments || "0") >= Number(webhookForm.max_comments_to_read || "0");
  const whTcMaxCasesError = webhookForm.testcase_auto_comment_enabled
    && (Number(webhookForm.testcase_testcases_per_requirement || "0") < 1
      || Number(webhookForm.testcase_testcases_per_requirement || "0") > 3);
  const whTcMaxCommentsError = webhookForm.testcase_auto_comment_enabled
    && webhookForm.testcase_read_comments_enabled
    && Number(webhookForm.testcase_max_comments_to_read || "0") < 0;
  const webhookHasError = whThresholdError
    || whCheckerOrderError
    || whAgent2BatchError
    || whMinTzError
    || whMaxReadCommentsError
    || whMaxSkipError
    || whSkipWindowError
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
    "dev_comment_source",
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
    "testcase_default_test_types",
    "testcase_testcases_per_requirement",
    "testcase_ai_data_section_order",
    "testcase_read_comments_enabled",
    "testcase_max_comments_to_read",
    "testcase_footer_text",
    "testcase_agent1_primary_model",
    "testcase_agent1_fallback_model",
    "testcase_agent2_primary_model",
    "testcase_agent2_fallback_model",
    "testcase_agent3_primary_model",
    "testcase_agent3_fallback_model",
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
  const webhookWizardTriggerConfigured = Boolean(
    hasWebhookModule
      && (
        (hasService1 && webhookTriggerConfigured.service1)
        || (hasService2 && webhookForm.testcase_auto_comment_enabled && webhookTriggerConfigured.service2)
      ),
  );
  const showGeminiKey1 = Boolean(
    geminiKey1Mask ||
    geminiKey1Dirty ||
    clearedCreds.gemini_api_key_1 ||
    form.gemini_api_key_1.trim(),
  );
  const geminiKey1Configured = Boolean(
    !clearedCreds.gemini_api_key_1
      && (geminiKey1Mask || (geminiKey1Dirty && form.gemini_api_key_1.trim())),
  );
  const geminiKey2Configured = Boolean(
    !clearedCreds.gemini_api_key_2
      && (geminiKey2Mask || (geminiKey2Dirty && form.gemini_api_key_2.trim())),
  );
  const hasConfiguredGeminiKey = geminiKey1Configured || geminiKey2Configured;
  const hasPendingGeminiRemoval = Boolean(
    clearedCreds.gemini_api_key_1 || clearedCreds.gemini_api_key_2,
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setWebhookLoading(Boolean(hasWebhookModule));
      setModulesLoading(true);
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
        if (sharedPayload.mode === "company") {
          setTab("integrations");
        }

        setForm({
          jira_server: sharedPayload.fields.jira_server || "",
          jira_email: sharedPayload.fields.jira_email || "",
          jira_project_keys: sharedPayload.fields.jira_project_keys || "",
          github_org: sharedPayload.fields.github_org || "",
          figma_token: "",
          jira_token: sharedPayload.fields.jira_token_mask || "",
          github_token: sharedPayload.fields.github_token_mask || "",
          gemini_api_key_1: sharedPayload.fields.gemini_api_key_1_mask || "",
          gemini_api_key_2: sharedPayload.fields.gemini_api_key_2_mask || "",
        });
        setJiraTokenMask(sharedPayload.fields.jira_token_mask || "");
        setGithubTokenMask(sharedPayload.fields.github_token_mask || "");
        setGeminiKey1Mask(sharedPayload.fields.gemini_api_key_1_mask || "");
        setGeminiKey2Mask(sharedPayload.fields.gemini_api_key_2_mask || "");
        setJiraTokenDirty(false);
        setGithubTokenDirty(false);
        setGeminiKey1Dirty(false);
        setGeminiKey2Dirty(false);
        setShowGeminiKey2(Boolean(sharedPayload.fields.gemini_api_key_2_present));
        setClearedCreds({});
        setFigmaTokens(
          (sharedPayload.fields.figma_tokens || []).map((entry, index) => ({
            name: entry.name || "",
            token: entry.mask || "",
            mask: entry.mask || "",
            dirty: false,
            isNew: false,
            origIdx: index,
          })),
        );
        setFigmaListDirty(false);

        if (canUseWebhook) {
          const webhookResponse = await fetch("/api/settings/webhook", { cache: "no-store" });
          const webhookPayload = (await webhookResponse.json().catch(() => null)) as
            | {
                data?: {
                  webhook_url?: string;
                  auto_return_enabled?: boolean;
                  allowed_issue_types?: string;
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
                  dev_comment_source?: string;
                  show_contradictory_comments?: boolean;
                  visible_sections?: string[];
                  ai_data_section_order?: string[];
                  skip_code?: string;
                  skip_comment_text?: string;
                  trigger_configured?: boolean;
                  trigger_status?: string;
                  trigger_status_aliases?: string;
                  testcase_auto_comment_enabled?: boolean;
                  testcase_trigger_configured?: boolean;
                  testcase_auto_comment_trigger_status?: string;
                  testcase_auto_comment_trigger_aliases?: string;
                  testcase_default_test_types?: string[];
                  testcase_testcases_per_requirement?: number;
                  testcase_ai_data_section_order?: string[];
                  testcase_read_comments_enabled?: boolean;
                  testcase_max_comments_to_read?: number;
                  testcase_footer_text?: string;
                  testcase_agent1_primary_model?: string;
                  testcase_agent1_fallback_model?: string;
                  testcase_agent2_primary_model?: string;
                  testcase_agent2_fallback_model?: string;
                  testcase_agent3_primary_model?: string;
                  testcase_agent3_fallback_model?: string;
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
            setWebhookUrl(String(data.webhook_url || ""));
            const current = String(data.trigger_status || "READY TO TEST");
            const showContradictory = Boolean(data.show_contradictory_comments ?? true);
            const normalizedSections = CHECKER_COMMENT_SECTIONS;
            setWebhookTriggerConfigured({
              service1: Boolean(data.trigger_configured),
              service2: Boolean(data.testcase_trigger_configured),
            });

            setWebhookForm({
              auto_return_enabled: Boolean(data.auto_return_enabled),
              allowed_issue_types: String(data.allowed_issue_types || ""),
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
              dev_comment_source: String(data.dev_comment_source || "assignee_reporter"),
              show_contradictory_comments: showContradictory,
              visible_sections: normalizedSections,
              ai_data_section_order: Array.isArray(data.ai_data_section_order) ? data.ai_data_section_order : EMPTY_WEBHOOK_FORM.ai_data_section_order,
              skip_code: String(data.skip_code ?? "AI_SKIP"),
              skip_comment_text: String(data.skip_comment_text || "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi."),
              trigger_status: current || "READY TO TEST",
              trigger_status_aliases: String(data.trigger_status_aliases || ""),
              trigger_statuses: [current || "READY TO TEST"],
              testcase_auto_comment_enabled: Boolean(data.testcase_auto_comment_enabled),
              testcase_auto_comment_trigger_status: String(data.testcase_auto_comment_trigger_status || "READY TO TEST"),
              testcase_auto_comment_trigger_aliases: String(data.testcase_auto_comment_trigger_aliases || "Ready To Test,READY TO TEST"),
              testcase_default_test_types: Array.isArray(data.testcase_default_test_types) ? data.testcase_default_test_types : ["positive", "negative"],
              testcase_testcases_per_requirement: String(data.testcase_testcases_per_requirement ?? 3),
              testcase_ai_data_section_order: Array.isArray(data.testcase_ai_data_section_order) ? data.testcase_ai_data_section_order : ["tz", "comments", "custom_context", "code"],
              testcase_read_comments_enabled: Boolean(data.testcase_read_comments_enabled ?? true),
              testcase_max_comments_to_read: String(data.testcase_max_comments_to_read ?? 0),
              testcase_footer_text: String(data.testcase_footer_text || EMPTY_WEBHOOK_FORM.testcase_footer_text),
              testcase_agent1_primary_model: String(data.testcase_agent1_primary_model || ""),
              testcase_agent1_fallback_model: String(data.testcase_agent1_fallback_model || ""),
              testcase_agent2_primary_model: String(data.testcase_agent2_primary_model || ""),
              testcase_agent2_fallback_model: String(data.testcase_agent2_fallback_model || ""),
              testcase_agent3_primary_model: String(data.testcase_agent3_primary_model || ""),
              testcase_agent3_fallback_model: String(data.testcase_agent3_fallback_model || ""),
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
              dev_comment_source: String(data.dev_comment_source || "assignee_reporter"),
              show_contradictory_comments: showContradictory,
              visible_sections: normalizedSections,
              ai_data_section_order: Array.isArray(data.ai_data_section_order) ? data.ai_data_section_order : EMPTY_WEBHOOK_FORM.ai_data_section_order,
              skip_code: String(data.skip_code ?? "AI_SKIP"),
              skip_comment_text: String(data.skip_comment_text || "⏭️ AI tekshirish o'chirilgan. Dev tomanidan skip ko'rsatma berilgan. Manual tekshirish tavsiya etiladi."),
              trigger_status: current || "READY TO TEST",
              trigger_status_aliases: String(data.trigger_status_aliases || ""),
              trigger_statuses: [current || "READY TO TEST"],
              testcase_auto_comment_enabled: Boolean(data.testcase_auto_comment_enabled),
              testcase_auto_comment_trigger_status: String(data.testcase_auto_comment_trigger_status || "READY TO TEST"),
              testcase_auto_comment_trigger_aliases: String(data.testcase_auto_comment_trigger_aliases || "Ready To Test,READY TO TEST"),
              testcase_default_test_types: Array.isArray(data.testcase_default_test_types) ? data.testcase_default_test_types : ["positive", "negative"],
              testcase_testcases_per_requirement: String(data.testcase_testcases_per_requirement ?? 3),
              testcase_ai_data_section_order: Array.isArray(data.testcase_ai_data_section_order) ? data.testcase_ai_data_section_order : ["tz", "comments", "custom_context", "code"],
              testcase_read_comments_enabled: Boolean(data.testcase_read_comments_enabled ?? true),
              testcase_max_comments_to_read: String(data.testcase_max_comments_to_read ?? 0),
              testcase_footer_text: String(data.testcase_footer_text || EMPTY_WEBHOOK_FORM.testcase_footer_text),
              testcase_agent1_primary_model: String(data.testcase_agent1_primary_model || ""),
              testcase_agent1_fallback_model: String(data.testcase_agent1_fallback_model || ""),
              testcase_agent2_primary_model: String(data.testcase_agent2_primary_model || ""),
              testcase_agent2_fallback_model: String(data.testcase_agent2_fallback_model || ""),
              testcase_agent3_primary_model: String(data.testcase_agent3_primary_model || ""),
              testcase_agent3_fallback_model: String(data.testcase_agent3_fallback_model || ""),
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
            setWebhookTriggerConfigured(EMPTY_WEBHOOK_TRIGGER_CONFIGURED);
            setWhDirty(false);
          }
        } else {
          setWebhookForm(EMPTY_WEBHOOK_FORM);
          setWebhookBaseline(EMPTY_WEBHOOK_FORM);
          setWebhookTriggerConfigured(EMPTY_WEBHOOK_TRIGGER_CONFIGURED);
          setWhDirty(false);
          setWebhookLoading(false);
        }

        if (canUseModules) {
          const modulesResponse = await fetch("/api/settings/modules", { cache: "no-store" });
          const modulesPayload = (await modulesResponse.json().catch(() => null)) as
            | {
                success?: boolean;
                data?: {
                  checker?: {
                    visible_sections?: string[];
                    ai_data_section_order?: string[];
                    read_comments_enabled?: boolean;
                    max_comments_to_read?: number;
                    trusted_scope_comment_authors?: string;
                    dev_comment_source?: string;
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
                    default_test_types?: string[];
                    testcases_per_requirement?: number;
                    ai_data_section_order?: string[];
                    read_comments_enabled?: boolean;
                    max_comments_to_read?: number;
                    agent1_primary_model?: string;
                    agent1_fallback_model?: string;
                    agent2_primary_model?: string;
                    agent2_fallback_model?: string;
                    agent3_primary_model?: string;
                    agent3_fallback_model?: string;
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
                visible_sections: Array.isArray(checker.visible_sections) ? checker.visible_sections : EMPTY_MODULE_FORM.checker.visible_sections,
                ai_data_section_order: Array.isArray(checker.ai_data_section_order) ? checker.ai_data_section_order : EMPTY_MODULE_FORM.checker.ai_data_section_order,
                read_comments_enabled: Boolean(checker.read_comments_enabled),
                max_comments_to_read: String(checker.max_comments_to_read ?? 0),
                trusted_scope_comment_authors: String(checker.trusted_scope_comment_authors || ""),
                dev_comment_source: String(checker.dev_comment_source || "assignee_reporter"),
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
                default_test_types: Array.isArray(testcase.default_test_types) ? testcase.default_test_types : EMPTY_MODULE_FORM.testcase.default_test_types,
                testcases_per_requirement: String(testcase.testcases_per_requirement ?? 3),
                ai_data_section_order: Array.isArray(testcase.ai_data_section_order) ? testcase.ai_data_section_order : EMPTY_MODULE_FORM.testcase.ai_data_section_order,
                read_comments_enabled: Boolean(testcase.read_comments_enabled),
                max_comments_to_read: String(testcase.max_comments_to_read ?? 0),
                agent1_primary_model: String(testcase.agent1_primary_model || ""),
                agent1_fallback_model: String(testcase.agent1_fallback_model || ""),
                agent2_primary_model: String(testcase.agent2_primary_model || ""),
                agent2_fallback_model: String(testcase.agent2_fallback_model || ""),
                agent3_primary_model: String(testcase.agent3_primary_model || ""),
                agent3_fallback_model: String(testcase.agent3_fallback_model || ""),
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

  function clearCredential(field: keyof SettingsFormState, setDirty: (next: boolean) => void) {
    setDirty(true);
    setClearedCreds((current) => ({ ...current, [field]: true }));
    setForm((current) => ({ ...current, [field]: "" }));
  }

  function clearCredentialSlot(field: keyof SettingsFormState, setDirty: (next: boolean) => void, present: boolean) {
    if (!present || clearedCreds[field]) return undefined;
    return (
      <button
        className="eye-btn"
        onClick={() => clearCredential(field, setDirty)}
        tabIndex={-1}
        title="Kalitni o'chirish"
        type="button"
      >
        ✕
      </button>
    );
  }

  function updateFigmaTokenEntry(index: number, patch: Partial<FigmaTokenEntry>) {
    setFigmaListDirty(true);
    setFigmaTokens((current) => current.map((entry, i) => (i === index ? { ...entry, ...patch } : entry)));
  }

  function addFigmaTokenEntry() {
    setFigmaListDirty(true);
    setFigmaTokens((current) => [
      ...current,
      { name: "", token: "", mask: "", dirty: true, isNew: true, origIdx: null },
    ]);
  }

  function removeFigmaTokenEntry(index: number) {
    setFigmaListDirty(true);
    setFigmaTokens((current) => current.filter((_, i) => i !== index));
  }

  function updateWebhookField<K extends keyof WebhookFormState>(field: K, value: WebhookFormState[K]) {
    setWhDirty(true);
    setWebhookForm((current) => ({ ...current, [field]: value }));
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
    result: { error?: string; success?: boolean; request_id?: string | null } | null,
  ) {
    const backendMessage = result?.error || "Noma'lum server xatosi";
    const reqId = result?.request_id ? ` (kod: ${result.request_id})` : "";
    return `${scopeLabel} saqlanmadi: ${backendMessage}${reqId}`;
  }

  async function saveShared() {
    setSavingShared(true);
    setError(null);
    setSharedError(null);
    setSharedSuccess(null);

    const payload: SharedSettingsSaveRequest = {};
    if (geminiKey1Dirty && form.gemini_api_key_1.trim()) {
      payload.gemini_api_key_1 = form.gemini_api_key_1.trim();
    } else if (clearedCreds.gemini_api_key_1) {
      payload.gemini_api_key_1 = "";
    }
    if (geminiKey2Dirty && form.gemini_api_key_2.trim()) {
      payload.gemini_api_key_2 = form.gemini_api_key_2.trim();
    } else if (clearedCreds.gemini_api_key_2) {
      payload.gemini_api_key_2 = "";
    }

    if (view?.mode === "company") {
      payload.jira_server = form.jira_server;
      payload.jira_email = form.jira_email;
      payload.jira_project_keys = form.jira_project_keys;
      payload.github_org = form.github_org;
      if (figmaListDirty) {
        payload.figma_tokens = figmaTokens
          .map((entry, i) =>
            entry.isNew || entry.dirty
              ? { name: entry.name.trim(), token: entry.token.trim() }
              : { name: entry.name.trim(), keep: true, idx: entry.origIdx ?? i },
          )
          .filter((entry) => "keep" in entry || Boolean(entry.token));
      }
      if (jiraTokenDirty && form.jira_token.trim()) {
        payload.jira_token = form.jira_token.trim();
      } else if (clearedCreds.jira_token) {
        payload.jira_token = "";
      }
      if (githubTokenDirty && form.github_token.trim()) {
        payload.github_token = form.github_token.trim();
      } else if (clearedCreds.github_token) {
        payload.github_token = "";
      }
    }

    try {
      const response = await fetch("/api/settings/shared", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean; request_id?: string | null } | null;
      if (!response.ok || !result?.success) {
        throw new Error(formatSaveError("Settings", response, result));
      }

      setSharedSuccess("✓ Muvaffaqiyatli saqlandi.");
      const maskAfterSave = (
        field: keyof SettingsFormState,
        dirty: boolean,
        currentMask: string,
      ) => {
        if (clearedCreds[field]) return "";
        return dirty && form[field].trim() ? maskSecret(form[field].trim()) : currentMask;
      };
      const nextJiraMask = maskAfterSave("jira_token", jiraTokenDirty, jiraTokenMask);
      const nextGithubMask = maskAfterSave("github_token", githubTokenDirty, githubTokenMask);
      const nextGemini1Mask = maskAfterSave("gemini_api_key_1", geminiKey1Dirty, geminiKey1Mask);
      const nextGemini2Mask = maskAfterSave("gemini_api_key_2", geminiKey2Dirty, geminiKey2Mask);
      setJiraTokenMask(nextJiraMask);
      setGithubTokenMask(nextGithubMask);
      setGeminiKey1Mask(nextGemini1Mask);
      setGeminiKey2Mask(nextGemini2Mask);
      setJiraTokenDirty(false);
      setGithubTokenDirty(false);
      setGeminiKey1Dirty(false);
      setGeminiKey2Dirty(false);
      setClearedCreds({});
      setShowGeminiKey2(Boolean(nextGemini2Mask));
      // Figma ko'p token: yangi/o'zgargan tokenlarni mask'ga aylantirib, qayta indekslaymiz
      if (figmaListDirty) {
        const savedFigma = figmaTokens
          .filter((entry) => (!entry.isNew && !entry.dirty) || entry.token.trim())
          .map((entry, i) => {
            const nextMask = entry.isNew || entry.dirty ? maskSecret(entry.token.trim()) : entry.mask;
            return {
              name: entry.name.trim(),
              token: nextMask,
              mask: nextMask,
              dirty: false,
              isNew: false,
              origIdx: i,
            };
          });
        setFigmaTokens(savedFigma);
        setFigmaListDirty(false);
      }
      setForm((current) => ({
        ...current,
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
          dev_comment_source: webhookForm.dev_comment_source,
          show_contradictory_comments: webhookForm.show_contradictory_comments,
          visible_sections: CHECKER_COMMENT_SECTIONS,
          ai_data_section_order: webhookForm.ai_data_section_order,
          skip_code: webhookForm.skip_code,
          skip_comment_text: webhookForm.skip_comment_text,
          trigger_status: webhookForm.trigger_status,
          trigger_status_aliases: "",
          testcase_auto_comment_enabled: webhookForm.testcase_auto_comment_enabled,
          testcase_auto_comment_trigger_status: webhookForm.testcase_auto_comment_trigger_status,
          testcase_auto_comment_trigger_aliases: webhookForm.testcase_auto_comment_trigger_aliases,
          testcase_default_test_types: webhookForm.testcase_default_test_types,
          testcase_testcases_per_requirement: Number(webhookForm.testcase_testcases_per_requirement || 3),
          testcase_ai_data_section_order: webhookForm.testcase_ai_data_section_order,
          testcase_read_comments_enabled: webhookForm.testcase_read_comments_enabled,
          testcase_max_comments_to_read: Number(webhookForm.testcase_max_comments_to_read || 0),
          testcase_ai_max_output_tokens: 16384,
          testcase_use_adf_format: true,
          testcase_footer_text: webhookForm.testcase_footer_text,
          testcase_agent1_primary_model: webhookForm.testcase_agent1_primary_model,
          testcase_agent1_fallback_model: webhookForm.testcase_agent1_fallback_model,
          testcase_agent2_primary_model: webhookForm.testcase_agent2_primary_model,
          testcase_agent2_fallback_model: webhookForm.testcase_agent2_fallback_model,
          testcase_agent3_primary_model: webhookForm.testcase_agent3_primary_model,
          testcase_agent3_fallback_model: webhookForm.testcase_agent3_fallback_model,
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

      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean; request_id?: string | null } | null;
      if (!response.ok || !result?.success) {
        throw new Error(formatSaveError("Webhook", response, result));
      }

      if (target === "shared") setWebhookSharedSuccess("✓ Muvaffaqiyatli saqlandi.");
      if (target === "service1") setWebhookService1Success("✓ Muvaffaqiyatli saqlandi.");
      if (target === "service2") setWebhookService2Success("✓ Muvaffaqiyatli saqlandi.");
      setWebhookBaseline(webhookForm);
      setWebhookTriggerConfigured((current) => ({
        service1: target === "service1" ? Boolean(webhookForm.trigger_status.trim()) : current.service1,
        service2:
          target === "service2"
            ? Boolean(webhookForm.testcase_auto_comment_enabled && webhookForm.testcase_auto_comment_trigger_status.trim())
            : current.service2,
      }));
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
          visible_sections: moduleForm.checker.visible_sections,
          ai_data_section_order: moduleForm.checker.ai_data_section_order,
          read_comments_enabled: moduleForm.checker.read_comments_enabled,
          max_comments_to_read: Number(moduleForm.checker.max_comments_to_read || 0),
          trusted_scope_comment_authors: moduleForm.checker.trusted_scope_comment_authors,
          dev_comment_source: moduleForm.checker.dev_comment_source,
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
          default_test_types: moduleForm.testcase.default_test_types,
          testcases_per_requirement: Number(moduleForm.testcase.testcases_per_requirement || 3),
          ai_data_section_order: moduleForm.testcase.ai_data_section_order,
          read_comments_enabled: moduleForm.testcase.read_comments_enabled,
          max_comments_to_read: Number(moduleForm.testcase.max_comments_to_read || 0),
          agent1_primary_model: moduleForm.testcase.agent1_primary_model,
          agent1_fallback_model: moduleForm.testcase.agent1_fallback_model,
          agent2_primary_model: moduleForm.testcase.agent2_primary_model,
          agent2_fallback_model: moduleForm.testcase.agent2_fallback_model,
          agent3_primary_model: moduleForm.testcase.agent3_primary_model,
          agent3_fallback_model: moduleForm.testcase.agent3_fallback_model,
        },
      };

      const response = await fetch("/api/settings/modules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as { error?: string; success?: boolean; request_id?: string | null } | null;
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
        description={`${companyName} uchun ${hasWebhookModule ? "webhook, " : ""}integration va modul sozlamalari.`}
        badge={(
          <div className="flex items-center gap-2">
            <Badge tone="success">● Online</Badge>
            <Badge tone="soft">v2.5</Badge>
          </div>
        )}
      />

      {!loading && view && view.mode === "company" ? (
        <SetupWizard
          hasWebhookModule={hasWebhookModule}
          settings={view}
          webhookTriggerConfigured={webhookWizardTriggerConfigured}
        />
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
              {tab === "webhook" && webhookAnyDirty ? (
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
                      hint="JIRA saytingiz manzili (https://kompaniya.atlassian.net)"
                      label="JIRA Base URL"
                      onChange={(value) => updateField("jira_server", value)}
                      placeholder="https://yourcompany.atlassian.net"
                      value={form.jira_server}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint="JIRA'ga kiradigan email"
                      label="JIRA User Email"
                      onChange={(value) => updateField("jira_email", value)}
                      placeholder="admin@yourcompany.uz"
                      value={form.jira_email}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint="Task havolasidan: .../browse/DEV-123 → DEV"
                      label="JIRA Project Key(lar)"
                      onChange={(value) => updateField("jira_project_keys", value.toUpperCase())}
                      placeholder="DEV, QA"
                      value={form.jira_project_keys}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint={<>{clearedCreds.jira_token ? "Saqlansa token o'chiriladi" : view.fields.jira_token_present ? "Bo'sh qoldirilsa mavjud token saqlanadi" : "Atlassian → Security → API tokens"}<CredHelp href="https://id.atlassian.com/manage-profile/security/api-tokens" /></>}
                      label="JIRA Token"
                      onBlur={() => {
                        if (jiraTokenDirty && !clearedCreds.jira_token && !form.jira_token.trim() && jiraTokenMask) {
                          setForm((current) => ({ ...current, jira_token: jiraTokenMask }));
                          setJiraTokenDirty(false);
                        }
                      }}
                      onChange={(value) => {
                        setJiraTokenDirty(true);
                        setClearedCreds((current) => ({ ...current, jira_token: false }));
                        updateField("jira_token", value);
                      }}
                      onFocus={() => {
                        if (!jiraTokenDirty && form.jira_token === jiraTokenMask) {
                          setForm((current) => ({ ...current, jira_token: "" }));
                          setJiraTokenDirty(true);
                        }
                      }}
                      placeholder="ATATT..."
                      rightSlot={clearCredentialSlot("jira_token", setJiraTokenDirty, view.fields.jira_token_present)}
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
                      hint={<>{clearedCreds.github_token ? "Saqlansa token o'chiriladi" : view.fields.github_token_present ? "Bo'sh qoldirilsa mavjud token saqlanadi" : "GitHub → Settings → Developer → Tokens"}<CredHelp href="https://github.com/settings/tokens" /></>}
                      label="GitHub Token"
                      onBlur={() => {
                        if (githubTokenDirty && !clearedCreds.github_token && !form.github_token.trim() && githubTokenMask) {
                          setForm((current) => ({ ...current, github_token: githubTokenMask }));
                          setGithubTokenDirty(false);
                        }
                      }}
                      onChange={(value) => {
                        setGithubTokenDirty(true);
                        setClearedCreds((current) => ({ ...current, github_token: false }));
                        updateField("github_token", value);
                      }}
                      onFocus={() => {
                        if (!githubTokenDirty && form.github_token === githubTokenMask) {
                          setForm((current) => ({ ...current, github_token: "" }));
                          setGithubTokenDirty(true);
                        }
                      }}
                      placeholder="ghp_xxx..."
                      rightSlot={clearCredentialSlot("github_token", setGithubTokenDirty, view.fields.github_token_present)}
                      type="text"
                      value={form.github_token}
                    />
                    <BaseInputField
                      className={SETTINGS_INPUT_CLASS}
                      hint="Repo manzilidagi tashkilot nomi (github.com/ORG/repo)"
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
                    {figmaTokens.map((entry, index) => (
                      <div className="grid gap-3 rounded-lg border border-border p-3" key={`figma-token-${index}`}>
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-muted-foreground">Figma token #{index + 1}</span>
                          <button
                            className="text-xs font-medium text-muted-foreground transition-colors hover:text-red-500"
                            onClick={() => removeFigmaTokenEntry(index)}
                            type="button"
                          >
                            ✕ O&apos;chirish
                          </button>
                        </div>
                        <BaseInputField
                          className={SETTINGS_INPUT_CLASS}
                          label="Nom (ixtiyoriy)"
                          onChange={(value) => updateFigmaTokenEntry(index, { name: value })}
                          placeholder="Masalan: Asosiy loyiha"
                          value={entry.name}
                        />
                        <BaseInputField
                          className={SETTINGS_INPUT_CLASS}
                          hint={<>{!entry.isNew ? "Bo'sh qoldirilsa mavjud token saqlanadi" : "Figma → Settings → Personal tokens"}<CredHelp href="https://www.figma.com/settings" /></>}
                          label="Token"
                          onBlur={() => {
                            if (entry.dirty && !entry.isNew && !entry.token.trim() && entry.mask) {
                              updateFigmaTokenEntry(index, { token: entry.mask, dirty: false });
                            }
                          }}
                          onChange={(value) => updateFigmaTokenEntry(index, { token: value, dirty: true })}
                          onFocus={() => {
                            if (!entry.dirty && entry.mask && entry.token === entry.mask) {
                              updateFigmaTokenEntry(index, { token: "", dirty: true });
                            }
                          }}
                          placeholder="figd_..."
                          type="text"
                          value={entry.token}
                        />
                      </div>
                    ))}
                    <button
                      className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                      onClick={addFigmaTokenEntry}
                      type="button"
                    >
                      + Figma token qo&apos;shish
                    </button>
                  </div>
                </SettingsInnerCard>

                <SettingsInnerCard>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Gemini</p>
                  <div className="mt-3 grid gap-4">
                    {showGeminiKey1 ? (
                      <div className="grid gap-3 rounded-lg border border-border p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-muted-foreground">Gemini key #1</span>
                          <button
                            className="text-xs font-medium text-muted-foreground transition-colors hover:text-red-500"
                            onClick={() => {
                              if (view.fields.gemini_api_key_1_present) {
                                clearCredential("gemini_api_key_1", setGeminiKey1Dirty);
                                return;
                              }
                              setGeminiKey1Dirty(false);
                              setClearedCreds((current) => ({ ...current, gemini_api_key_1: false }));
                              setForm((current) => ({ ...current, gemini_api_key_1: "" }));
                            }}
                            type="button"
                          >
                            Company kalitini olib tashlash
                          </button>
                        </div>
                        <BaseInputField
                          className={SETTINGS_INPUT_CLASS}
                          hint={<>{clearedCreds.gemini_api_key_1 ? "Saqlash bosilgach bu kalit o'chiriladi" : geminiKey1Mask ? "Kalit saqlangan. Almashtirish uchun yangi kalit kiriting" : "Google AI Studio → Get API key"}<CredHelp href="https://aistudio.google.com/app/apikey" /></>}
                          label="Token"
                          onBlur={() => {
                            if (geminiKey1Dirty && !clearedCreds.gemini_api_key_1 && !form.gemini_api_key_1.trim() && geminiKey1Mask) {
                              setForm((current) => ({ ...current, gemini_api_key_1: geminiKey1Mask }));
                              setGeminiKey1Dirty(false);
                            }
                          }}
                          onChange={(value) => {
                            setGeminiKey1Dirty(true);
                            setClearedCreds((current) => ({ ...current, gemini_api_key_1: false }));
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
                      </div>
                    ) : (
                      <button
                        className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                        onClick={() => {
                          setGeminiKey1Dirty(true);
                          setClearedCreds((current) => ({ ...current, gemini_api_key_1: false }));
                          setForm((current) => ({ ...current, gemini_api_key_1: "" }));
                        }}
                        type="button"
                      >
                        + Gemini key qo&apos;shish
                      </button>
                    )}
                    {showGeminiKey1 || showGeminiKey2 ? (
                      showGeminiKey2 ? (
                        <div className="grid gap-3 rounded-lg border border-border p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-semibold text-muted-foreground">Gemini key #2</span>
                            <button
                              className="text-xs font-medium text-muted-foreground transition-colors hover:text-red-500"
                              onClick={() => {
                                if (view.fields.gemini_api_key_2_present) {
                                  clearCredential("gemini_api_key_2", setGeminiKey2Dirty);
                                  return;
                                }
                                setShowGeminiKey2(false);
                                setGeminiKey2Dirty(false);
                                setClearedCreds((current) => ({ ...current, gemini_api_key_2: false }));
                                setForm((current) => ({ ...current, gemini_api_key_2: "" }));
                              }}
                              type="button"
                            >
                              Company kalitini olib tashlash
                            </button>
                          </div>
                          <BaseInputField
                            className={SETTINGS_INPUT_CLASS}
                            hint={clearedCreds.gemini_api_key_2 ? "Saqlash bosilgach bu kalit o'chiriladi" : geminiKey2Mask ? "Kalit saqlangan. Almashtirish uchun yangi kalit kiriting" : undefined}
                            label="Token"
                            onBlur={() => {
                              if (geminiKey2Dirty && !clearedCreds.gemini_api_key_2 && !form.gemini_api_key_2.trim() && geminiKey2Mask) {
                                setForm((current) => ({ ...current, gemini_api_key_2: geminiKey2Mask }));
                                setGeminiKey2Dirty(false);
                              }
                            }}
                            onChange={(value) => {
                              setGeminiKey2Dirty(true);
                              setClearedCreds((current) => ({ ...current, gemini_api_key_2: false }));
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
                        </div>
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
                          + Gemini key qo&apos;shish
                        </button>
                      )
                    ) : null}
                    {hasPendingGeminiRemoval && !hasConfiguredGeminiKey ? (
                      <Notice tone="warning">
                        Saqlash bosilgach barcha company Gemini kalitlari o&apos;chiriladi va super admin global kaliti mavjud bo&apos;lsa, tizim unga o&apos;tadi.
                      </Notice>
                    ) : hasConfiguredGeminiKey ? (
                      <Notice tone="info">
                        Hozir company Gemini kaliti ustuvor. Global kalitga o&apos;tish uchun barcha company Gemini kalitlarini olib tashlab, Saqlashni bosing.
                      </Notice>
                    ) : (
                      <Notice tone="info">
                        Company Gemini kaliti yo&apos;q. Super admin global kaliti mavjud bo&apos;lsa tizim undan foydalanadi; aks holda AI ishga tushmaydi.
                      </Notice>
                    )}
                  </div>
                </SettingsInnerCard>
              </div>
            </SettingsBaseCard>
          ) : null}

          {view.mode === "company" && hasWebhookModule && tab === "webhook" ? (
            <>

              {webhookLoading ? <p className="mt-3 text-sm text-muted-foreground">Webhook sozlamalari yuklanmoqda...</p> : null}
              {webhookHasError ? (
                <Notice className="mt-3" tone="warning">
                  {[whThresholdError ? "Return threshold 0-100 oralig'ida bo'lishi kerak." : null, whCheckerOrderError ? "Checker AI order ichida 'tz' va 'code' bo'lishi shart." : null, whAgent2BatchError ? "Agent2 batch size 1-20 bo'lishi shart." : null, whMinTzError ? "Min TZ belgilari 0 yoki undan katta bo'lishi kerak." : null, whMaxReadCommentsError ? "Max izohlar 0 yoki undan katta bo'lishi kerak." : null, whMaxSkipError ? "Max skip comment soni 1 yoki undan katta bo'lishi kerak." : null, whSkipWindowError ? "Max commentlar skip tekshirish comment sonidan katta bo'lishi kerak." : null, whTcMaxCasesError ? "Testcase soni 1-3 oralig'ida bo'lishi kerak." : null, whTcMaxCommentsError ? "Testcase izohlari 0 yoki undan katta bo'lishi kerak." : null]
                    .filter(Boolean)
                    .join(" ")}
                </Notice>
              ) : null}

              {webhookUrl ? (
                <div className="mt-4">
                  <SettingsInnerCard>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-foreground">📡 JIRA Webhook URL</div>
                        <div className="mt-1 text-xs text-muted-foreground">
                          {webhookSecretMissing
                            ? "Bu kompaniya uchun webhook parol hali yaratilmagan. Avval parol yarating — token URL tarkibiga qo'shiladi."
                            : "JIRA'da ⚙️ → System → Webhooks bo'limiga aynan shu URL'ni qo'ying. Token — kompaniyangizning webhook paroli (nusxalashda to'liq olinadi)."}
                        </div>
                        <code className="mt-2 block truncate text-xs" title={maskedWebhookUrl}>
                          {maskedWebhookUrl}
                        </code>
                        {webhookSecretError ? (
                          <div className="mt-1 text-xs text-destructive">{webhookSecretError}</div>
                        ) : null}
                      </div>
                      {webhookSecretMissing ? (
                        <Button
                          disabled={webhookSecretGenerating}
                          onClick={() => void generateWebhookSecret()}
                          size="sm"
                          type="button"
                          variant="primary"
                        >
                          {webhookSecretGenerating ? "Yaratilmoqda..." : "Parol yaratish"}
                        </Button>
                      ) : (
                        <Button onClick={() => void copyWebhookUrl()} size="sm" type="button" variant="primary">
                          {webhookUrlCopied ? "Nusxalandi ✓" : "URL'ni nusxalash"}
                        </Button>
                      )}
                    </div>
                  </SettingsInnerCard>
                </div>
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
                          hint="JIRA description shu belgilardan kam bo'lsa checker ham testcase ham to'xtatiladi."
                          label="Min TZ belgilari"
                          min={0}
                          onChange={(value) => updateWebhookField("min_tz_description_chars", value)}
                          value={webhookForm.min_tz_description_chars}
                        />
                      </SettingsCardItem>
                    </div>
                  </SettingsCardSection>

                </SettingsBaseCard>

                {hasService1 ? (
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
                          {whCommentWindowVisible ? (
                            <SettingsCardItem>
                              <NumberField
                                hint="0 = barcha commentlar. Skip kodi yoqilganida bu qiymat skip oynasidan katta bo'lishi kerak."
                                label="Max commentlar"
                                min={0}
                                onChange={(value) => updateWebhookField("max_comments_to_read", value)}
                                value={webhookForm.max_comments_to_read}
                              />
                            </SettingsCardItem>
                          ) : null}
                          {webhookForm.read_comments_enabled ? (
                            <SettingsCardItem>
                              <BaseSelectField
                                className="settings-form-select"
                                hint="Dev izohlar Agent3 (arbiter) ga beriladi: u bajarilmagan talablarni dev tushuntirgan bo'lsa skip qiladi (manual tekshiruvga). Faqat ishonchli manba tanlang."
                                label="Dev comment manbai (Agent3 uchun)"
                                onChange={(value) => updateWebhookField("dev_comment_source", value)}
                                value={webhookForm.dev_comment_source}
                              >
                                <option value="assignee_reporter">Faqat assignee + reporter izohlari</option>
                                <option value="all">Barcha dev izohlari</option>
                              </BaseSelectField>
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
                              hint="JIRA commentda bu kod bo'lsa — checker (Servis-1) skip bo'ladi."
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
                                {whSkipWindowError ? (
                                  <span className="err-text">
                                    Max commentlar 0 yoki bu qiymatdan katta bo'lishi kerak.
                                  </span>
                                ) : null}
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
                ) : null}

                {hasService2 ? (
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
                              <div className="ssec-label">Agent modellari</div>
                              <div className="grid gap-3 md:grid-cols-2">
                                {[
                                  ["testcase_agent1_primary_model", "Agent1 primary"],
                                  ["testcase_agent1_fallback_model", "Agent1 fallback"],
                                  ["testcase_agent2_primary_model", "Agent2 primary"],
                                  ["testcase_agent2_fallback_model", "Agent2 fallback"],
                                  ["testcase_agent3_primary_model", "Agent3 primary"],
                                  ["testcase_agent3_fallback_model", "Agent3 fallback"],
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
                              <div className="ssec-label">Mustaqil settinglar</div>
                              <div className="grid gap-3">
                                <SettingsCardItem>
                                  <NumberField
                                    hint="Har bir requirement uchun target testcase soni. Default: 3."
                                    label="Har requirement uchun testcase soni"
                                    max={3}
                                    min={1}
                                    onChange={(value) => updateWebhookField("testcase_testcases_per_requirement", value)}
                                    value={webhookForm.testcase_testcases_per_requirement}
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
                ) : null}

              </div>
            </>
          ) : null}

          {view.mode === "company" && tab === "modules" ? (
            <>
              {modulesLoading ? <p className="mt-3 text-sm text-muted-foreground">Module sozlamalari yuklanmoqda...</p> : null}
              {moduleHasError ? (
                <Notice className="mt-3" tone="warning">
                  {[testcaseCountError ? "Har requirement uchun testcase soni 1-3 bo'lishi shart." : null, checkerOrderError ? "Checker order ichida tz va code bo'lishi shart." : null, checkerBatchError ? "Agent2 batch size 1-20 bo'lishi shart." : null, testcaseOrderError ? "Testcase order ichida tz bo'lishi shart." : null]
                    .filter(Boolean)
                    .join(" ")}
                </Notice>
              ) : null}

              <div className="webhook-cards-grid mt-4">
                {hasCheckerModule ? (
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
                                <BaseSelectField
                                  className="settings-form-select"
                                  hint="Dev izohlar Agent3 (arbiter) ga beriladi: u bajarilmagan talablarni dev tushuntirgan bo'lsa skip qiladi (manual tekshiruvga). Faqat ishonchli manba tanlang."
                                  label="Dev comment manbai (Agent3 uchun)"
                                  onChange={(value) => updateCheckerField("dev_comment_source", value)}
                                  value={moduleForm.checker.dev_comment_source}
                                >
                                  <option value="assignee_reporter">Faqat assignee + reporter izohlari</option>
                                  <option value="all">Barcha dev izohlari</option>
                                </BaseSelectField>
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
                ) : null}

                {hasTestcaseModule ? (
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
                                updateTestcaseField(field as keyof ModuleFormState["testcase"], value)
                              }
                              value={String(moduleForm.testcase[field as keyof ModuleFormState["testcase"]] || "")}
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
                        <div className="ssec-label">Mustaqil settinglar</div>
                        <div className="grid gap-3">
                          <SettingsCardItem>
                            <NumberField
                              hint="Har bir requirement uchun target testcase soni. Default: 3."
                              label="Har requirement uchun testcase soni"
                              max={3}
                              min={1}
                              onChange={(value) => updateTestcaseField("testcases_per_requirement", value)}
                              required
                              value={moduleForm.testcase.testcases_per_requirement}
                            />
                          </SettingsCardItem>
                        </div>
                      </div>
                    </SettingsInnerCard>
                  </div>
                </SettingsBaseCard>
                ) : null}
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
                <div className="grid gap-2">
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    hint={clearedCreds.gemini_api_key_1 ? "Saqlash bosilgach bu kalit o'chiriladi" : geminiKey1Mask ? "Kalit saqlangan. Almashtirish uchun yangi kalit kiriting" : undefined}
                    label="API Key 1"
                    onBlur={() => {
                      if (geminiKey1Dirty && !clearedCreds.gemini_api_key_1 && !form.gemini_api_key_1.trim() && geminiKey1Mask) {
                        setForm((current) => ({ ...current, gemini_api_key_1: geminiKey1Mask }));
                        setGeminiKey1Dirty(false);
                      }
                    }}
                    onChange={(value) => {
                      setGeminiKey1Dirty(true);
                      setClearedCreds((current) => ({ ...current, gemini_api_key_1: false }));
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
                  {geminiKey1Mask && !clearedCreds.gemini_api_key_1 ? (
                    <button
                      className="w-fit text-xs font-medium text-red-500 transition-colors hover:text-red-600"
                      onClick={() => clearCredential("gemini_api_key_1", setGeminiKey1Dirty)}
                      type="button"
                    >
                      Shaxsiy kalitni olib tashlash
                    </button>
                  ) : null}
                </div>
                <div className="grid gap-2">
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    hint={clearedCreds.gemini_api_key_2 ? "Saqlash bosilgach bu kalit o'chiriladi" : geminiKey2Mask ? "Kalit saqlangan. Almashtirish uchun yangi kalit kiriting" : undefined}
                    label="API Key 2 (ixtiyoriy)"
                    onBlur={() => {
                      if (geminiKey2Dirty && !clearedCreds.gemini_api_key_2 && !form.gemini_api_key_2.trim() && geminiKey2Mask) {
                        setForm((current) => ({ ...current, gemini_api_key_2: geminiKey2Mask }));
                        setGeminiKey2Dirty(false);
                      }
                    }}
                    onChange={(value) => {
                      setGeminiKey2Dirty(true);
                      setClearedCreds((current) => ({ ...current, gemini_api_key_2: false }));
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
                  {geminiKey2Mask && !clearedCreds.gemini_api_key_2 ? (
                    <button
                      className="w-fit text-xs font-medium text-red-500 transition-colors hover:text-red-600"
                      onClick={() => clearCredential("gemini_api_key_2", setGeminiKey2Dirty)}
                      type="button"
                    >
                      Shaxsiy kalitni olib tashlash
                    </button>
                  ) : null}
                </div>
              </div>
              {hasPendingGeminiRemoval && !hasConfiguredGeminiKey ? (
                <Notice className="mt-4" tone="warning">
                  Saqlash bosilgach shaxsiy kalitlaringiz o&apos;chiriladi. Keyin company admin sozlagan shared kalit, u bo&apos;lmasa super admin global Gemini kaliti ishlatiladi.
                </Notice>
              ) : hasConfiguredGeminiKey ? (
                <Notice className="mt-4" tone="info">
                  Hozir shaxsiy Gemini kalitingiz ustuvor. Umumiy kalitga o&apos;tish uchun barcha shaxsiy Gemini kalitlarini olib tashlab, Saqlashni bosing.
                </Notice>
              ) : (
                <Notice className="mt-4" tone="info">
                  Shaxsiy Gemini kaliti yo&apos;q. Company admin sozlagan shared kalit, u bo&apos;lmasa super admin global Gemini kaliti ishlatiladi. Ikkalasi ham bo&apos;lmasa AI ishga tushmaydi.
                </Notice>
              )}
            </SettingsBaseCard>
          ) : null}
        </>
      ) : null}
    </>
  );
}
