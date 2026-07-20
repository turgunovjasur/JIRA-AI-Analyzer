"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Eye, EyeOff, Plus, X } from "lucide-react";

import { AdminJobsPanel } from "@/components/admin-jobs-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BaseCard } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { MetricCard } from "@/components/ui/metric-card";
import { Notice } from "@/components/ui/notice";
import { PageIntro } from "@/components/ui/page-intro";
import { SectionHeader } from "@/components/ui/section-header";
import {
  BaseCheckGroup,
  type BaseCheckOption,
  BaseInputField,
  BaseInlineActionField,
  BaseSelectField,
  NumberField,
  SettingsBaseCard,
  SettingsInnerCard,
} from "@/components/settings/base-card-system";
import {
  MODULE_CATALOG,
  SUBSCRIPTION_STATUS_LABELS,
  SUPER_ADMIN_MANAGED_MODULE_KEYS,
} from "@/lib/product-catalog";
import type {
  AiUsageCompanyRow,
  AiUsageEventRow,
  AiUsageModuleRow,
  CompanyModules,
  CompanySubscription,
  SuperAdminCompany,
  SuperAdminOverview,
} from "@/lib/types";

type SuperAdminPanelProps = {
  authSource: string | null;
  currentUsername: string;
};

type SuperAdminTab = "companies" | "ai" | "usage" | "jobs" | "system" | "platform";

type CompanyCreateForm = {
  admin_password: string;
  admin_username: string;
  company_code: string;
  company_name: string;
  enabled_modules: CompanyModules;
  seat_limit: number;
};

type AiDefaultsForm = {
  agent1_fallback_model: string;
  agent1_primary_model: string;
  agent2_fallback_model: string;
  agent2_primary_model: string;
  agent3_fallback_model: string;
  agent3_primary_model: string;
  api_key_1: string;
  api_key_2: string;
  key_freeze_minutes: number;
  testcase_free_quota_limit: number;
  testcase_agent1_fallback_model: string;
  testcase_agent1_primary_model: string;
  testcase_agent2_fallback_model: string;
  testcase_agent2_primary_model: string;
  testcase_agent3_fallback_model: string;
  testcase_agent3_primary_model: string;
  tzpr_free_quota_limit: number;
};

type SuperAdminSystemForm = {
  task_wait_timeout: number;
  blocked_retry_delay: number;
  gemini_min_interval: number;
  blocked_check_interval: number;
  gemini_max_retries: number;
  key_freeze_duration: number;
  db_connection_timeout: number;
  http_timeout: number;
  executor_timeout: number;
};

const SETTINGS_INPUT_CLASS = "settings-form-input";
const SETTINGS_SELECT_CLASS = "settings-form-select";
const SECONDS_PER_MINUTE = 60;

type UsageFilters = {
  module: string;
  task: string;
  tenant: string;
};

function buildCreateForm(): CompanyCreateForm {
  // Yangi kompaniya standarti: 2 ta asosiy modul yoqiq, webhook + servislar o'chiq.
  const moduleDefaults: CompanyModules = {
    tz_pr_checker: true,
    testcase_generator: true,
    webhook: false,
    webhook_service1: false,
    webhook_service2: false,
  };
  return {
    admin_password: "",
    admin_username: "",
    company_code: "",
    company_name: "",
    enabled_modules: moduleDefaults,
    seat_limit: 0,
  };
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

function formatDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addMonths(date: Date, months: number) {
  const next = new Date(date);
  const originalDay = next.getDate();
  next.setMonth(next.getMonth() + months);
  if (next.getDate() < originalDay) {
    next.setDate(0);
  }
  return next;
}

function normalizeDateInputValue(value: string | null | undefined) {
  const rawValue = String(value || "").trim();
  if (!rawValue) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(rawValue)) return rawValue;
  const parsed = new Date(rawValue);
  return Number.isNaN(parsed.getTime()) ? "" : formatDateInputValue(parsed);
}

function numberValue(value: number | string | null | undefined) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function secondsToMinutesInput(value: number | string | null | undefined) {
  const minutes = numberValue(value) / SECONDS_PER_MINUTE;
  if (!Number.isFinite(minutes)) return "0";
  return Number.isInteger(minutes) ? String(minutes) : String(Number(minutes.toFixed(2)));
}

function minutesInputToSeconds(value: number | string | null | undefined) {
  return Math.max(0, Math.round(numberValue(value) * SECONDS_PER_MINUTE));
}

function formatCompactNumber(value: number | string | null | undefined) {
  return new Intl.NumberFormat("en-US", {
    compactDisplay: "short",
    maximumFractionDigits: 1,
    notation: "compact",
  }).format(numberValue(value));
}

function formatPlainNumber(value: number | string | null | undefined) {
  return new Intl.NumberFormat("en-US").format(Math.round(numberValue(value)));
}

function formatUsd(value: number | string | null | undefined) {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 4,
    minimumFractionDigits: 2,
    style: "currency",
  }).format(numberValue(value));
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(date);
}

function moduleLabel(value: string | null | undefined) {
  const key = String(value || "").trim();
  const catalog = MODULE_CATALOG as Record<string, { label?: string } | undefined>;
  return catalog[key]?.label || key.replace(/_/g, " ") || "-";
}

function companyLabel(row: AiUsageCompanyRow) {
  return row.company_code || row.company_name || (row.company_id ? `Company #${row.company_id}` : "No company");
}

function usageTenantValue(row: AiUsageEventRow) {
  if (row.company_id !== null && row.company_id !== undefined) return `id:${row.company_id}`;
  const code = String(row.company_code || "").trim();
  return code ? `code:${code}` : "none";
}

function usageTenantLabel(row: AiUsageEventRow) {
  const code = String(row.company_code || "").trim();
  if (code) return code;
  return row.company_id ? `#${row.company_id}` : "No tenant";
}

function usageTone(warnings: number | string | null | undefined): "success" | "warning" {
  return numberValue(warnings) > 0 ? "warning" : "success";
}

function billingTone(company: SuperAdminCompany): "success" | "warning" | "danger" {
  if (company.billing_health.severity === "danger") return "danger";
  if (company.billing_health.severity === "warning") return "warning";
  return "success";
}

function billingPriority(company: SuperAdminCompany) {
  if (company.billing_health.severity === "danger") return 0;
  if (company.billing_health.severity === "warning") return 1;
  return 2;
}

function billingAlertLabel(company: SuperAdminCompany) {
  const status = (company.subscription.subscription_status || "").trim().toLowerCase();
  const message = company.billing_health.message.toLowerCase();
  if (message.includes("obuna muddati tugagan")) return "MUDDATI TUGAGAN";
  if (status === "past_due") return "TO'LOV KECHIKKAN";
  if (status === "suspended" || status === "cancelled") return "BLOKLANGAN";
  if (company.billing_health.severity === "danger") return "LOGIN BLOK";
  if (company.billing_health.severity === "warning") return "TEKSHIRISH KERAK";
  return "SOG'LOM";
}

function modelOptions() {
  return ["", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"];
}

// Super-admin checkbox guruhi uchun variantlar. Webhook servislari faqat
// `webhook` addon tanlangan bo'lsa faollashadi; monitoring derived (read-only).
function moduleOptions(selected: string[]): BaseCheckOption[] {
  const webhookOn = selected.includes("webhook");
  return [
    { badge: "modul", key: "tz_pr_checker", label: MODULE_CATALOG.tz_pr_checker.label },
    { badge: "modul", key: "testcase_generator", label: MODULE_CATALOG.testcase_generator.label },
    { badge: "addon", key: "webhook", label: MODULE_CATALOG.webhook.label },
    { badge: "servis", disabled: !webhookOn, key: "webhook_service1", label: MODULE_CATALOG.webhook_service1.label },
    { badge: "servis", disabled: !webhookOn, key: "webhook_service2", label: MODULE_CATALOG.webhook_service2.label },
    { badge: "auto", disabled: true, key: "monitoring", label: MODULE_CATALOG.monitoring.label },
  ];
}

// Tanlovni amaldagi modul holatiga aylantiradi. Webhook yoqilganda kamida bitta
// servis bo'lishi shart — hech biri tanlanmagan bo'lsa, ikkalasini default yoqamiz.
function buildManagedModuleState(selected: string[]): CompanyModules {
  const sel = new Set(selected);
  const webhookOn = sel.has("webhook");
  let service1 = webhookOn && sel.has("webhook_service1");
  let service2 = webhookOn && sel.has("webhook_service2");
  if (webhookOn && !service1 && !service2) {
    service1 = true;
    service2 = true;
  }
  return {
    tz_pr_checker: sel.has("tz_pr_checker"),
    testcase_generator: sel.has("testcase_generator"),
    webhook: webhookOn,
    webhook_service1: service1,
    webhook_service2: service2,
  } as CompanyModules;
}

// Modul holatidan tanlangan checkbox kalitlarini hosil qiladi (monitoring derived).
function selectedManagedModules(modules: CompanyModules | undefined): string[] {
  const selected: string[] = [];
  for (const moduleKey of SUPER_ADMIN_MANAGED_MODULE_KEYS) {
    if (modules?.[moduleKey]) selected.push(moduleKey);
  }
  if (modules?.webhook || modules?.monitoring) selected.push("monitoring");
  return selected;
}

async function parseJson<T>(response: Response) {
  return (await response.json().catch(() => null)) as T | null;
}

export function SuperAdminPanel({ authSource: _authSource, currentUsername }: SuperAdminPanelProps) {
  const [overview, setOverview] = useState<SuperAdminOverview | null>(null);
  const [tab, setTab] = useState<SuperAdminTab>("companies");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<CompanyCreateForm>(buildCreateForm);
  const [aiForm, setAiForm] = useState<AiDefaultsForm>({
    agent1_fallback_model: "",
    agent1_primary_model: "",
    agent2_fallback_model: "",
    agent2_primary_model: "",
    agent3_fallback_model: "",
    agent3_primary_model: "",
    api_key_1: "",
    api_key_2: "",
    key_freeze_minutes: 10,
    testcase_free_quota_limit: 3,
    testcase_agent1_fallback_model: "",
    testcase_agent1_primary_model: "",
    testcase_agent2_fallback_model: "",
    testcase_agent2_primary_model: "",
    testcase_agent3_fallback_model: "",
    testcase_agent3_primary_model: "",
    tzpr_free_quota_limit: 3,
  });
  const [showApiKey1, setShowApiKey1] = useState(false);
  const [showApiKey2, setShowApiKey2] = useState(false);
  const [showBackupApiKey, setShowBackupApiKey] = useState(false);
  const [apiKey1Mask, setApiKey1Mask] = useState("");
  const [apiKey2Mask, setApiKey2Mask] = useState("");
  const [apiKey1Dirty, setApiKey1Dirty] = useState(false);
  const [apiKey2Dirty, setApiKey2Dirty] = useState(false);
  const [apiKey2Clear, setApiKey2Clear] = useState(false);
  const [platformAdminForm, setPlatformAdminForm] = useState({
    confirm_password: "",
    password: "",
    username: currentUsername,
  });
  const [systemForm, setSystemForm] = useState<SuperAdminSystemForm>({
    task_wait_timeout: 60,
    blocked_retry_delay: 5,
    gemini_min_interval: 6,
    blocked_check_interval: 30,
    gemini_max_retries: 3,
    key_freeze_duration: 600,
    db_connection_timeout: 30,
    http_timeout: 30,
    executor_timeout: 120,
  });
  const [openCompanyId, setOpenCompanyId] = useState<number | null>(null);
  const [seatDrafts, setSeatDrafts] = useState<Record<number, number>>({});
  const [budgetDrafts, setBudgetDrafts] = useState<Record<number, string>>({});
  const [moduleDrafts, setModuleDrafts] = useState<Record<number, CompanyModules>>({});
  const [subscriptionDrafts, setSubscriptionDrafts] = useState<Record<number, CompanySubscription>>({});
  const [deleteDrafts, setDeleteDrafts] = useState<Record<number, string>>({});
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [usageFilters, setUsageFilters] = useState<UsageFilters>({
    module: "",
    task: "",
    tenant: "",
  });

  const companyMetrics = useMemo(() => {
    if (!overview) return { activeRate: 0, totalUsers: 0 };
    const totalUsers = overview.companies.reduce((sum, company) => sum + (company.total_accounts || 0), 0);
    const activeRate = overview.metrics.total
      ? Math.round((overview.metrics.active / overview.metrics.total) * 100)
      : 0;
    return { activeRate, totalUsers };
  }, [overview]);

  const orderedCompanies = useMemo(() => {
    if (!overview) return [];
    return [...overview.companies].sort((left, right) => {
      const priorityDiff = billingPriority(left) - billingPriority(right);
      if (priorityDiff !== 0) return priorityDiff;
      return left.company_code.localeCompare(right.company_code);
    });
  }, [overview]);

  const recentUsageEvents = useMemo(
    () => overview?.ai_usage?.recent_events || [],
    [overview?.ai_usage?.recent_events],
  );

  const usageFilterOptions = useMemo(() => {
    const tenants = new Map<string, string>();
    const modules = new Map<string, string>();
    for (const row of recentUsageEvents) {
      tenants.set(usageTenantValue(row), usageTenantLabel(row));
      const moduleKey = String(row.module_key || "").trim();
      if (moduleKey) modules.set(moduleKey, moduleLabel(moduleKey));
    }
    return {
      modules: Array.from(modules, ([value, label]) => ({ label, value })).sort((left, right) =>
        left.label.localeCompare(right.label),
      ),
      tenants: Array.from(tenants, ([value, label]) => ({ label, value })).sort((left, right) =>
        left.label.localeCompare(right.label),
      ),
    };
  }, [recentUsageEvents]);

  const filteredUsageEvents = useMemo(() => {
    const taskQuery = usageFilters.task.trim().toLowerCase();
    return recentUsageEvents.filter((row) => {
      const matchesTenant = !usageFilters.tenant || usageTenantValue(row) === usageFilters.tenant;
      const matchesModule = !usageFilters.module || String(row.module_key || "") === usageFilters.module;
      const matchesTask = !taskQuery || String(row.task_key || "").toLowerCase().includes(taskQuery);
      return matchesTenant && matchesModule && matchesTask;
    });
  }, [recentUsageEvents, usageFilters]);

  const usageFiltersActive = Boolean(
    usageFilters.tenant || usageFilters.module || usageFilters.task.trim(),
  );

  async function loadOverview() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/super-admin/overview", { cache: "no-store" });
      const payload = await parseJson<SuperAdminOverview & { error?: string }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Super admin ma'lumotlari yuklanmadi.");
      }

      setOverview(payload);
      setSeatDrafts(
        Object.fromEntries(payload.companies.map((company) => [company.id, company.seat_limit])),
      );
      setModuleDrafts(
        Object.fromEntries(
          payload.companies.map((company) => [
            company.id,
            buildManagedModuleState(selectedManagedModules(company.modules)),
          ]),
        ),
      );
      setSubscriptionDrafts(
        Object.fromEntries(
          payload.companies.map((company) => [company.id, { ...(company.subscription || {}) }]),
        ),
      );
      const nextApiKey1Mask = payload.global_ai_defaults.api_key_1_mask || "";
      const nextApiKey2Mask = payload.global_ai_defaults.api_key_2_mask || "";
      setApiKey1Mask(nextApiKey1Mask);
      setApiKey2Mask(nextApiKey2Mask);
      setApiKey1Dirty(false);
      setApiKey2Dirty(false);
      setApiKey2Clear(false);
      setShowBackupApiKey(Boolean(nextApiKey2Mask || payload.global_ai_defaults.api_key_2_present));
      setAiForm({
        agent1_fallback_model: payload.global_ai_defaults.agent1_fallback_model || "",
        agent1_primary_model: payload.global_ai_defaults.agent1_primary_model || "",
        agent2_fallback_model: payload.global_ai_defaults.agent2_fallback_model || "",
        agent2_primary_model: payload.global_ai_defaults.agent2_primary_model || "",
        agent3_fallback_model: payload.global_ai_defaults.agent3_fallback_model || "",
        agent3_primary_model: payload.global_ai_defaults.agent3_primary_model || "",
        api_key_1: nextApiKey1Mask,
        api_key_2: nextApiKey2Mask,
        key_freeze_minutes: payload.global_ai_defaults.key_freeze_minutes ?? 10,
        testcase_free_quota_limit: payload.global_ai_defaults.testcase_free_quota_limit ?? 3,
        testcase_agent1_fallback_model: payload.global_ai_defaults.testcase_agent1_fallback_model || "",
        testcase_agent1_primary_model: payload.global_ai_defaults.testcase_agent1_primary_model || "",
        testcase_agent2_fallback_model: payload.global_ai_defaults.testcase_agent2_fallback_model || "",
        testcase_agent2_primary_model: payload.global_ai_defaults.testcase_agent2_primary_model || "",
        testcase_agent3_fallback_model: payload.global_ai_defaults.testcase_agent3_fallback_model || "",
        testcase_agent3_primary_model: payload.global_ai_defaults.testcase_agent3_primary_model || "",
        tzpr_free_quota_limit: payload.global_ai_defaults.tzpr_free_quota_limit ?? 3,
      });
      setPlatformAdminForm((current) => ({
        ...current,
        username: currentUsername || current.username,
      }));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Yuklashda xato.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOverview();
  }, []);

  useEffect(() => {
    async function loadSystemSettings() {
      try {
        const response = await fetch("/api/super-admin/system", { cache: "no-store" });
        const payload = await parseJson<{ success?: boolean; data?: Partial<SuperAdminSystemForm> }>(response);
        if (!response.ok || !payload?.success || !payload.data) {
          return;
        }
        setSystemForm({
          task_wait_timeout: Number(payload.data.task_wait_timeout ?? 60),
          blocked_retry_delay: Number(payload.data.blocked_retry_delay ?? 5),
          gemini_min_interval: Number(payload.data.gemini_min_interval ?? 6),
          blocked_check_interval: Number(payload.data.blocked_check_interval ?? 30),
          gemini_max_retries: Number(payload.data.gemini_max_retries ?? 3),
          key_freeze_duration: Number(payload.data.key_freeze_duration ?? 600),
          db_connection_timeout: Number(payload.data.db_connection_timeout ?? 30),
          http_timeout: Number(payload.data.http_timeout ?? 30),
          executor_timeout: Number(payload.data.executor_timeout ?? 120),
        });
      } catch {
        // Silent fallback: default qiymatlar bilan qoladi.
      }
    }

    void loadSystemSettings();
  }, []);

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setSuccess(null);

    try {
      await action();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Action bajarilmadi.");
    } finally {
      setBusy(false);
    }
  }

  async function createCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction(async () => {
      const response = await fetch("/api/super-admin/companies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createForm),
      });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Kompaniya yaratilmadi.");
      }

      setCreateForm(buildCreateForm());
      setCreateOpen(false);
      setSuccess("Yangi kompaniya yaratildi.");
      await loadOverview();
    });
  }

  async function updateCompanyAction(
    company: SuperAdminCompany,
    body: Record<string, unknown>,
    successMessage: string,
  ) {
    await runAction(async () => {
      const response = await fetch(`/api/super-admin/companies/${company.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Kompaniya yangilashda xato.");
      }
      setSuccess(successMessage);
      await loadOverview();
    });
  }

  async function toggleCompanyStatus(company: SuperAdminCompany) {
    await updateCompanyAction(
      company,
      { action: "status", is_active: !company.is_active },
      `${company.company_code} statusi yangilandi.`,
    );
  }

  useEffect(() => {
    if (!openCompanyId) return;
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch(`/api/super-admin/companies/${openCompanyId}`);
        const payload = await parseJson<{ ai_monthly_budget_usd?: number | null; success?: boolean }>(response);
        if (!cancelled && response.ok && payload?.success) {
          const value = payload.ai_monthly_budget_usd;
          setBudgetDrafts((current) => ({
            ...current,
            [openCompanyId]: value === null || value === undefined ? "" : String(value),
          }));
        }
      } catch {
        // Budjet o'qilmasa input bo'sh qoladi — saqlashda baribir yangilanadi.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [openCompanyId]);

  async function saveAiBudget(company: SuperAdminCompany) {
    const draft = (budgetDrafts[company.id] ?? "").trim();
    await updateCompanyAction(
      company,
      { action: "ai_budget", ai_monthly_budget_usd: draft === "" ? null : Number(draft) },
      `${company.company_code} oylik AI budjeti saqlandi.`,
    );
  }

  async function saveSeatLimit(company: SuperAdminCompany) {
    await updateCompanyAction(
      company,
      {
        action: "seat_limit",
        seat_limit: Number(seatDrafts[company.id] ?? company.seat_limit),
      },
      `${company.company_code} seat limiti saqlandi.`,
    );
  }

  async function saveModules(company: SuperAdminCompany) {
    await updateCompanyAction(
      company,
      { action: "modules", enabled_modules: moduleDrafts[company.id] || {} },
      `${company.company_code} modullari saqlandi.`,
    );
  }

  function activateSubscriptionDraft(company: SuperAdminCompany, months: number) {
    const today = new Date();
    const billingStartDate = formatDateInputValue(today);
    const billingEndDate = formatDateInputValue(addMonths(today, months));

    setSubscriptionDrafts((current) => {
      const currentDraft = current[company.id] || {};
      return {
        ...current,
        [company.id]: {
          ...(company.subscription || {}),
          ...currentDraft,
          billing_end_date: billingEndDate,
          billing_mode: currentDraft.billing_mode || company.subscription.billing_mode || "manual",
          billing_start_date: billingStartDate,
          last_payment_date: billingStartDate,
          next_payment_date: billingEndDate,
          plan_name: currentDraft.plan_name || company.subscription.plan_name || "base",
          subscription_status: "active",
        },
      };
    });
  }

  function activateTrialDraft(company: SuperAdminCompany, days: number) {
    const today = new Date();
    const trialEnd = new Date(today);
    trialEnd.setDate(trialEnd.getDate() + days);
    const billingStartDate = formatDateInputValue(today);
    const billingEndDate = formatDateInputValue(trialEnd);

    setSubscriptionDrafts((current) => ({
      ...current,
      [company.id]: {
        ...(company.subscription || {}),
        ...(current[company.id] || {}),
        billing_end_date: billingEndDate,
        billing_mode: "manual",
        billing_start_date: billingStartDate,
        last_payment_date: "",
        last_payment_note: `${days} kunlik trial`,
        next_payment_date: billingEndDate,
        plan_name: (current[company.id] || {}).plan_name || company.subscription.plan_name || "base",
        subscription_status: "trial",
      },
    }));
  }

  async function saveSubscription(company: SuperAdminCompany) {
    await updateCompanyAction(
      company,
      { action: "subscription", subscription: subscriptionDrafts[company.id] || {} },
      `${company.company_code} billing holati saqlandi.`,
    );
  }

  async function deleteCompany(company: SuperAdminCompany) {
    await runAction(async () => {
      const response = await fetch(`/api/super-admin/companies/${company.id}`, { method: "DELETE" });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Kompaniya o'chirilmadi.");
      }
      setConfirmDeleteId(null);
      setDeleteDrafts((current) => ({ ...current, [company.id]: "" }));
      setSuccess(`${company.company_code} kompaniyasi o'chirildi.`);
      await loadOverview();
    });
  }

  async function saveAiDefaults(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction(async () => {
      const body: Partial<AiDefaultsForm> & { api_key_2_clear?: boolean } = { ...aiForm };
      if (apiKey1Dirty && aiForm.api_key_1.trim()) {
        body.api_key_1 = aiForm.api_key_1.trim();
      } else {
        delete body.api_key_1;
      }
      if (apiKey2Clear) {
        body.api_key_2_clear = true;
        delete body.api_key_2;
      } else if (apiKey2Dirty && aiForm.api_key_2.trim()) {
        body.api_key_2 = aiForm.api_key_2.trim();
      } else {
        delete body.api_key_2;
      }

      const response = await fetch("/api/super-admin/ai-defaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "AI sozlamalar saqlanmadi.");
      }

      setSuccess("AI sozlamalar saqlandi.");
      await loadOverview();
    });
  }

  function removeBackupApiKey() {
    const hasSavedBackup = Boolean(apiKey2Mask || overview?.global_ai_defaults.api_key_2_present);
    setAiForm((current) => ({ ...current, api_key_2: "" }));
    setApiKey2Mask("");
    setApiKey2Dirty(false);
    setApiKey2Clear(hasSavedBackup);
    setShowApiKey2(false);
    setShowBackupApiKey(false);
  }

  async function savePlatformAdminPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction(async () => {
      const response = await fetch("/api/super-admin/platform-admin/password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(platformAdminForm),
      });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Platform admin paroli saqlanmadi.");
      }

      setPlatformAdminForm((current) => ({
        ...current,
        confirm_password: "",
        password: "",
      }));
      setSuccess("Platform admin paroli yangilandi.");
    });
  }

  async function saveSystemSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction(async () => {
      const response = await fetch("/api/super-admin/system", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(systemForm),
      });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "System sozlamalar saqlanmadi.");
      }
      setSuccess("System sozlamalar saqlandi.");
    });
  }

  return (
    <>
      <PageIntro eyebrow="Platform" title="Super Admin" />

      {loading ? <PageIntro eyebrow="Loading" title="Yuklanmoqda..." /> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      {success ? <Notice tone="success">{success}</Notice> : null}

      {overview ? (
        <>
          <div className="tabs">
            {[
              { key: "companies", label: "🏢 Kompaniyalar" },
              { key: "ai", label: "🤖 AI Sozlamalar" },
              { key: "usage", label: "AI Usage" },
              { key: "jobs", label: "📋 Job Queue" },
              { key: "system", label: "⚙️ System" },
              { key: "platform", label: "🔐 Platform Admin" },
            ].map((item) => (
              <button
                key={item.key}
                className={`tab-btn${tab === item.key ? " active" : ""}`}
                onClick={() => setTab(item.key as SuperAdminTab)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>

          {tab === "companies" ? (
            <>
              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <MetricCard helper="Tenantlar" label="Jami" value={overview.metrics.total} />
                <MetricCard helper="Ishlayotgan" label="Faol" value={overview.metrics.active} />
                <MetricCard helper="Barcha kompaniya" label="Jami users" value={companyMetrics.totalUsers} />
                <MetricCard helper="Login bloklanadigan tenantlar" label="Obuna blok" value={overview.metrics.blocked} />
                <MetricCard helper="Faol tenantlar ulushi" label="Faollik foizi" value={`${companyMetrics.activeRate}%`} />
              </section>

              <SettingsBaseCard
                header={(
                  <SectionHeader
                    action={(
                      <Button onClick={() => setCreateOpen(true)} type="button">
                        + Yangi kompaniya
                      </Button>
                    )}
                    eyebrow="Kompaniyalar"
                    title="Tenant boshqaruvi"
                  />
                )}
              >
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  Obuna muammosi bor kompaniyalar ro'yxat tepasida chiqadi. Qizil kartalar login bloklangan tenantlarni bildiradi.
                </p>
                <div className="mt-4 grid gap-3">
                  {orderedCompanies.length ? (
                    orderedCompanies.map((company) => {
                      const moduleDraft = moduleDrafts[company.id] || company.modules || {};
                      const subscriptionDraft = subscriptionDrafts[company.id] || company.subscription;
                      const billingSeverity = company.billing_health.severity;
                      const deleteMatch =
                        (deleteDrafts[company.id] || "").trim().toLowerCase() ===
                        company.company_code.toLowerCase();

                      return (
                        <BaseCard
                          as="details"
                          key={company.id}
                          className="co-card"
                          open={openCompanyId === company.id}
                          padding="none"
                          style={
                            billingSeverity === "danger"
                              ? {
                                  background: "var(--error-soft)",
                                  borderColor: "var(--error)",
                                  boxShadow: "0 0 0 1px var(--error-border)",
                                }
                              : billingSeverity === "warning"
                                ? {
                                    borderColor: "var(--warning)",
                                    boxShadow: "0 0 0 1px var(--warn-border)",
                                  }
                                : undefined
                          }
                        >
                          <summary
                            className="co-summary"
                            onClick={(event) => {
                              event.preventDefault();
                              setOpenCompanyId((current) => (current === company.id ? null : company.id));
                            }}
                          >
                            <div>
                              <div style={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 8 }}>
                                <span style={{ fontWeight: 700, fontSize: 14.5 }}>
                                  {company.company_code.toUpperCase()} - {company.company_name}
                                </span>
                                {billingSeverity !== "ok" ? (
                                  <Badge tone={billingTone(company)}>
                                    {billingAlertLabel(company)}
                                  </Badge>
                                ) : null}
                              </div>
                              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                                {company.total_accounts}/{company.seat_limit} user · Plan:{" "}
                                {company.subscription.plan_name || "base"} ·{" "}
                                {formatDate(company.subscription.billing_end_date || company.created_at)}
                              </div>
                              <div
                                style={{
                                  color:
                                    billingSeverity === "danger"
                                      ? "var(--error)"
                                      : billingSeverity === "warning"
                                        ? "var(--warning)"
                                        : "var(--muted)",
                                  fontSize: 12,
                                  fontWeight: billingSeverity === "danger" ? 700 : 500,
                                  marginTop: 4,
                                }}
                              >
                                {company.billing_health.message}
                              </div>
                            </div>
                            <div className="flex-c gap-2">
                              <Badge tone={company.is_active ? "success" : "danger"}>
                                {company.is_active ? "● Faol" : "● Nofaol"}
                              </Badge>
                              <Badge tone={billingTone(company)}>
                                {company.subscription.subscription_status || "active"}
                              </Badge>
                            </div>
                          </summary>

                          {openCompanyId === company.id ? (
                            <div className="co-body">
                              <div className="g2">
                                <div className="sbox">
                                  <h4>⚙ Seat Limit va Status</h4>
                                  <BaseInlineActionField
                                    action={(
                                      <Button
                                        className="tenant-action-btn tenant-action-btn--save"
                                        disabled={busy}
                                        onClick={() => void saveSeatLimit(company)}
                                        size="sm"
                                        type="button"
                                        variant="ghost"
                                      >
                                        Saqlash
                                      </Button>
                                    )}
                                    className={SETTINGS_INPUT_CLASS}
                                    label="User limiti"
                                    min={0}
                                    onChange={(value) =>
                                      setSeatDrafts((current) => ({
                                        ...current,
                                        [company.id]: Number(value || 0),
                                      }))
                                    }
                                    type="number"
                                    value={seatDrafts[company.id] ?? company.seat_limit}
                                  />
                                  <BaseInlineActionField
                                    action={(
                                      <Button
                                        className="tenant-action-btn tenant-action-btn--save"
                                        disabled={busy}
                                        onClick={() => void saveAiBudget(company)}
                                        size="sm"
                                        type="button"
                                        variant="ghost"
                                      >
                                        Saqlash
                                      </Button>
                                    )}
                                    className={SETTINGS_INPUT_CLASS}
                                    hint="Bo'sh = cheksiz. Limitga yetganda yangi AI runlar bloklanadi (F2-5)."
                                    label="Oylik AI budjet (USD)"
                                    min={0}
                                    onChange={(value) =>
                                      setBudgetDrafts((current) => ({
                                        ...current,
                                        [company.id]: String(value ?? ""),
                                      }))
                                    }
                                    type="number"
                                    value={budgetDrafts[company.id] ?? ""}
                                  />
                                  <Button
                                    className="mt-3 tenant-action-btn tenant-action-btn--status"
                                    disabled={busy}
                                    onClick={() => void toggleCompanyStatus(company)}
                                    size="sm"
                                    type="button"
                                    variant="ghost"
                                  >
                                    {company.is_active ? "Nofaol qilish" : "Faollashtirish"}
                                  </Button>
                                </div>

                                <div className="sbox">
                                  <h4>📦 Modullar</h4>
                                  <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
                                    Har modulni alohida yoqib-o'chiring. Webhook servislari (Servis-1/Servis-2)
                                    faqat webhook yoqilganda faollashadi; monitoring webhookdan kelib chiqadi.
                                  </p>
                                  <BaseCheckGroup
                                    onChange={(nextValues) =>
                                      setModuleDrafts((current) => ({
                                        ...current,
                                        [company.id]: buildManagedModuleState(nextValues),
                                      }))
                                    }
                                    options={moduleOptions(selectedManagedModules(moduleDraft))}
                                    value={selectedManagedModules(moduleDraft)}
                                  />
                                  <Button
                                    className="mt-3 tenant-action-btn tenant-action-btn--save"
                                    disabled={busy}
                                    onClick={() => void saveModules(company)}
                                    size="sm"
                                    type="button"
                                    variant="ghost"
                                  >
                                    Saqlash
                                  </Button>
                                </div>
                              </div>

                              <div className="sbox">
                                <h4>💳 Billing</h4>
                                <div className="flex flex-wrap gap-2" style={{ marginBottom: 12 }}>
                                  <Button
                                    disabled={busy}
                                    onClick={() => activateTrialDraft(company, 14)}
                                    size="sm"
                                    type="button"
                                    variant="soft"
                                  >
                                    14 kun trial
                                  </Button>
                                  <Button
                                    disabled={busy}
                                    onClick={() => activateSubscriptionDraft(company, 1)}
                                    size="sm"
                                    type="button"
                                    variant="soft"
                                  >
                                    1 oyga aktivlash
                                  </Button>
                                  <Button
                                    disabled={busy}
                                    onClick={() => activateSubscriptionDraft(company, 12)}
                                    size="sm"
                                    type="button"
                                    variant="soft"
                                  >
                                    1 yilga aktivlash
                                  </Button>
                                </div>
                                <div className="g2">
                                  <BaseInputField
                                    className={SETTINGS_INPUT_CLASS}
                                    label="Plan"
                                    onChange={(value) =>
                                      setSubscriptionDrafts((current) => ({
                                        ...current,
                                        [company.id]: {
                                          ...(current[company.id] || {}),
                                          plan_name: value,
                                        },
                                      }))
                                    }
                                    value={subscriptionDraft.plan_name || ""}
                                  />
                                  <BaseSelectField
                                    className={SETTINGS_SELECT_CLASS}
                                    label="Status"
                                    onChange={(value) =>
                                      setSubscriptionDrafts((current) => ({
                                        ...current,
                                        [company.id]: {
                                          ...(current[company.id] || {}),
                                          subscription_status: value,
                                        },
                                      }))
                                    }
                                    value={subscriptionDraft.subscription_status || "active"}
                                  >
                                    {Object.entries(SUBSCRIPTION_STATUS_LABELS).map(([statusKey, label]) => (
                                      <option key={statusKey} value={statusKey}>
                                        {label}
                                      </option>
                                    ))}
                                  </BaseSelectField>
                                  <BaseInputField
                                    className={SETTINGS_INPUT_CLASS}
                                    label="Boshlanish sanasi"
                                    onChange={(value) =>
                                      setSubscriptionDrafts((current) => ({
                                        ...current,
                                        [company.id]: {
                                          ...(current[company.id] || {}),
                                          billing_start_date: value,
                                        },
                                      }))
                                    }
                                    type="date"
                                    value={normalizeDateInputValue(subscriptionDraft.billing_start_date)}
                                  />
	                                  <BaseInputField
	                                    className={SETTINGS_INPUT_CLASS}
	                                    label="Muddat tugashi"
	                                    onChange={(value) =>
	                                      setSubscriptionDrafts((current) => ({
                                        ...current,
                                        [company.id]: {
                                          ...(current[company.id] || {}),
                                          billing_end_date: value,
                                        },
                                      }))
                                    }
	                                    type="date"
	                                    value={normalizeDateInputValue(subscriptionDraft.billing_end_date)}
	                                  />
	                                </div>
                                <div className="mt-2">
                                  <BaseInputField
                                    className={SETTINGS_INPUT_CLASS}
                                    label="To'lov izohi (ichki eslatma)"
                                    onChange={(value) =>
                                      setSubscriptionDrafts((current) => ({
                                        ...current,
                                        [company.id]: {
                                          ...(current[company.id] || {}),
                                          last_payment_note: value,
                                        },
                                      }))
                                    }
                                    value={subscriptionDraft.last_payment_note || ""}
                                  />
                                </div>
                                <Button
                                  className="mt-3 tenant-action-btn tenant-action-btn--save"
                                  disabled={busy}
                                  onClick={() => void saveSubscription(company)}
                                  size="sm"
                                  type="button"
                                  variant="ghost"
                                >
                                  Saqlash
                                </Button>
                              </div>

                                <div className="sbox">
                                  <h4 style={{ color: "var(--error)" }}>🗑 Kompaniyani o'chirish</h4>
                                  <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
                                    Tasdiqlash uchun: <strong>{company.company_code}</strong>
                                  </p>
                                  <BaseInlineActionField
                                    action={(
                                      <Button
                                        className="tenant-action-btn tenant-action-btn--danger"
                                        disabled={busy || !deleteMatch}
                                        onClick={() =>
                                          setConfirmDeleteId((current) =>
                                            current === company.id ? null : company.id,
                                          )
                                        }
                                        size="sm"
                                        type="button"
                                        variant="ghost"
                                      >
                                        O'chirish
                                      </Button>
                                    )}
                                    className={SETTINGS_INPUT_CLASS}
                                    label="Tasdiqlash kodi"
                                    onChange={(value) =>
                                      setDeleteDrafts((current) => ({
                                        ...current,
                                        [company.id]: value,
                                      }))
                                    }
                                    placeholder={company.company_code}
                                    value={deleteDrafts[company.id] || ""}
                                  />
                                {confirmDeleteId === company.id ? (
                                  <Notice className="mt-3" tone="warning">
                                    <p className="font-semibold">{company.company_name} butunlay o'chiriladi.</p>
                                    <div className="mt-3 flex gap-2">
                                      <Button
                                        className="tenant-action-btn tenant-action-btn--danger-solid"
                                        disabled={busy || !deleteMatch}
                                        onClick={() => void deleteCompany(company)}
                                        size="sm"
                                        type="button"
                                      >
                                        Ha, o'chirish
                                      </Button>
                                      <Button
                                        className="tenant-action-btn tenant-action-btn--neutral"
                                        onClick={() => setConfirmDeleteId(null)}
                                        size="sm"
                                        type="button"
                                        variant="ghost"
                                      >
                                        Bekor
                                      </Button>
                                    </div>
                                  </Notice>
                                ) : null}
                              </div>
                            </div>
                          ) : null}
                        </BaseCard>
                      );
                    })
                  ) : (
                    <BaseCard as="p" className="border-dashed px-4 py-6 text-sm text-muted-foreground" padding="none" tone="soft">
                      Hali kompaniyalar yaratilmagan.
                    </BaseCard>
                  )}
                </div>
              </SettingsBaseCard>
            </>
          ) : null}

          {tab === "ai" ? (
            <SettingsBaseCard
              header={(
                <SectionHeader
                  action={<Badge tone="soft">Platform scope</Badge>}
                  eyebrow="AI DEFAULTS"
                  title="Global AI kalitlar va agent defaultlari"
                />
              )}
            >
              <form className="mt-4 grid gap-4" onSubmit={saveAiDefaults}>
                <div className="grid gap-4 md:grid-cols-2">
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    hint={overview.global_ai_defaults.api_key_1_present ? "Bo'sh qoldirilsa mavjud kalit saqlanadi" : undefined}
                    label="API Key 1"
                    onBlur={() => {
                      if (apiKey1Dirty && !aiForm.api_key_1.trim() && apiKey1Mask) {
                        setAiForm((current) => ({ ...current, api_key_1: apiKey1Mask }));
                        setApiKey1Dirty(false);
                      }
                    }}
                    onChange={(value) => {
                      setApiKey1Dirty(true);
                      setAiForm((current) => ({ ...current, api_key_1: value }));
                    }}
                    onFocus={() => {
                      if (!apiKey1Dirty && apiKey1Mask && aiForm.api_key_1 === apiKey1Mask) {
                        setAiForm((current) => ({ ...current, api_key_1: "" }));
                        setApiKey1Dirty(true);
                      }
                    }}
                    placeholder="AIza..."
                    rightSlot={(
                      <button
                        aria-label={showApiKey1 ? "API Key 1 ni yashirish" : "API Key 1 ni ko'rsatish"}
                        className="eye-btn"
                        onClick={() => setShowApiKey1((current) => !current)}
                        type="button"
                      >
                        {showApiKey1 ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    )}
                    type={apiKey1Dirty && !showApiKey1 ? "password" : "text"}
                    value={aiForm.api_key_1}
                  />
                  {showBackupApiKey ? (
                    <Field
                      hint={overview.global_ai_defaults.api_key_2_present ? "Bo'sh qoldirilsa mavjud kalit saqlanadi" : undefined}
                      label="API Key 2 (backup)"
                    >
                      <div className="input-eye">
                        <Input
                          className={`${SETTINGS_INPUT_CLASS} pr-20`}
                          onBlur={() => {
                            if (apiKey2Dirty && !aiForm.api_key_2.trim() && apiKey2Mask) {
                              setAiForm((current) => ({ ...current, api_key_2: apiKey2Mask }));
                              setApiKey2Dirty(false);
                            }
                          }}
                          onChange={(event) => {
                            setApiKey2Clear(false);
                            setApiKey2Dirty(true);
                            setAiForm((current) => ({ ...current, api_key_2: event.target.value }));
                          }}
                          onFocus={() => {
                            if (!apiKey2Dirty && apiKey2Mask && aiForm.api_key_2 === apiKey2Mask) {
                              setAiForm((current) => ({ ...current, api_key_2: "" }));
                              setApiKey2Dirty(true);
                            }
                          }}
                          placeholder="AIza..."
                          type={apiKey2Dirty && !showApiKey2 ? "password" : "text"}
                          value={aiForm.api_key_2}
                        />
                        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
                          <button
                            aria-label="API Key 2 ni o'chirish"
                            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                            onClick={removeBackupApiKey}
                            type="button"
                          >
                            <X size={15} />
                          </button>
                          <button
                            aria-label={showApiKey2 ? "API Key 2 ni yashirish" : "API Key 2 ni ko'rsatish"}
                            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                            onClick={() => setShowApiKey2((current) => !current)}
                            type="button"
                          >
                            {showApiKey2 ? <EyeOff size={16} /> : <Eye size={16} />}
                          </button>
                        </div>
                      </div>
                    </Field>
                  ) : (
                    <div className="grid gap-2">
                      <span className="text-sm font-medium text-foreground">API Key 2 (backup)</span>
                      <Button
                        fullWidth
                        onClick={() => {
                          setApiKey2Clear(false);
                          setShowBackupApiKey(true);
                        }}
                        type="button"
                        variant="soft"
                      >
                        <Plus size={16} />
                        API Key 2 qo'shish
                      </Button>
                      <small className="text-xs leading-5 text-muted-foreground">
                        Ixtiyoriy backup key kerak bo'lsa qo'shing.
                      </small>
                    </div>
                  )}
                </div>

                <SettingsInnerCard>
                  <div className="ssec mt-0 border-none pt-0">
                    <div className="ssec-label">Global kalit uchun bepul kvota</div>
                    <p className="mb-4 text-xs leading-5 text-muted-foreground">
                      Limit har bir kompaniya va har bir modul uchun alohida hisoblanadi. 0 qo&apos;yilsa, shu modul global kalitdan bepul foydalana olmaydi.
                    </p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <NumberField
                        hint="Har bir kompaniyaga TZ-PR Checker uchun beriladigan global Gemini runlari soni."
                        inputClassName={SETTINGS_INPUT_CLASS}
                        label="TZ-PR Checker bepul urinishlari"
                        max={100000}
                        min={0}
                        onChange={(value) =>
                          setAiForm((current) => ({
                            ...current,
                            tzpr_free_quota_limit: Number(value || 0),
                          }))
                        }
                        required
                        value={String(aiForm.tzpr_free_quota_limit)}
                      />
                      <NumberField
                        hint="Har bir kompaniyaga Test Case Generator uchun beriladigan global Gemini runlari soni."
                        inputClassName={SETTINGS_INPUT_CLASS}
                        label="Test Case Generator bepul urinishlari"
                        max={100000}
                        min={0}
                        onChange={(value) =>
                          setAiForm((current) => ({
                            ...current,
                            testcase_free_quota_limit: Number(value || 0),
                          }))
                        }
                        required
                        value={String(aiForm.testcase_free_quota_limit)}
                      />
                    </div>
                  </div>
                </SettingsInnerCard>

                <div className="grid gap-4 lg:grid-cols-2">
                  <SettingsInnerCard>
                    <div className="ssec mt-0 border-none pt-0">
                      <div className="ssec-label">TZ-PR agent modellari</div>
                      <div className="grid gap-4 md:grid-cols-2">
                        {[
                          ["agent1_primary_model", "Agent1 primary"],
                          ["agent1_fallback_model", "Agent1 fallback"],
                          ["agent2_primary_model", "Agent2 primary"],
                          ["agent2_fallback_model", "Agent2 fallback"],
                          ["agent3_primary_model", "Agent3 primary"],
                          ["agent3_fallback_model", "Agent3 fallback"],
                        ].map(([field, label]) => (
                          <BaseSelectField
                            className={SETTINGS_SELECT_CLASS}
                            key={field}
                            label={label}
                            onChange={(value) =>
                              setAiForm((current) => ({ ...current, [field]: value }))
                            }
                            value={String(aiForm[field as keyof AiDefaultsForm] || "")}
                          >
                            {modelOptions().map((model) => (
                              <option key={model || "unset"} value={model}>
                                {model || "Tanlanmagan"}
                              </option>
                            ))}
                          </BaseSelectField>
                        ))}
                      </div>
                    </div>
                  </SettingsInnerCard>

                  <SettingsInnerCard>
                    <div className="ssec mt-0 border-none pt-0">
                      <div className="ssec-label">Testcase agent modellari</div>
                      <div className="grid gap-4 md:grid-cols-2">
                        {[
                          ["testcase_agent1_primary_model", "Agent1 primary"],
                          ["testcase_agent1_fallback_model", "Agent1 fallback"],
                          ["testcase_agent2_primary_model", "Agent2 primary"],
                          ["testcase_agent2_fallback_model", "Agent2 fallback"],
                          ["testcase_agent3_primary_model", "Agent3 primary"],
                          ["testcase_agent3_fallback_model", "Agent3 fallback"],
                        ].map(([field, label]) => (
                          <BaseSelectField
                            className={SETTINGS_SELECT_CLASS}
                            key={field}
                            label={label}
                            onChange={(value) =>
                              setAiForm((current) => ({ ...current, [field]: value }))
                            }
                            value={String(aiForm[field as keyof AiDefaultsForm] || "")}
                          >
                            {modelOptions().map((model) => (
                              <option key={model || "unset"} value={model}>
                                {model || "Tanlanmagan"}
                              </option>
                            ))}
                          </BaseSelectField>
                        ))}
                      </div>
                    </div>
                  </SettingsInnerCard>
                </div>

                <div>
                  <Button disabled={busy} type="submit">
                    {busy ? "Saqlanmoqda..." : "Saqlash"}
                  </Button>
                </div>
              </form>
            </SettingsBaseCard>
          ) : null}

          {tab === "usage" ? (
            <>
              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <MetricCard
                  helper="Yozilgan AI chaqiruvlar"
                  label="Calls"
                  value={formatPlainNumber(overview.ai_usage?.summary.event_count)}
                />
                <MetricCard
                  helper="Prompt tokenlar"
                  label="Input tokens"
                  value={formatCompactNumber(overview.ai_usage?.summary.prompt_token_count)}
                />
                <MetricCard
                  helper="Thinking tokenlar"
                  label="Thinking"
                  value={formatCompactNumber(overview.ai_usage?.summary.thoughts_token_count)}
                />
                <MetricCard
                  helper="Barcha tokenlar"
                  label="Total tokens"
                  value={formatCompactNumber(overview.ai_usage?.summary.total_token_count)}
                />
                <MetricCard
                  helper="Taxminiy Gemini xarajati"
                  label="Est. cost"
                  value={formatUsd(overview.ai_usage?.summary.estimated_total_cost_usd)}
                />
              </section>

              <SettingsBaseCard
                header={(
                  <SectionHeader
                    action={(
                      <Badge tone={usageTone(overview.ai_usage?.summary.cost_warning_count)}>
                        {formatPlainNumber(overview.ai_usage?.summary.cost_warning_count)} expensive calls
                      </Badge>
                    )}
                    eyebrow="AI Usage"
                    title="Tenant va modul bo'yicha xarajat"
                  />
                )}
              >
                <div className="mt-4 grid gap-4">
                  <div>
                    <div className="mb-2 text-sm font-semibold text-foreground">Tenantlar bo'yicha</div>
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Tenant</th>
                            <th>Calls</th>
                            <th>Input</th>
                            <th>Thinking</th>
                            <th>Cost</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(overview.ai_usage?.by_company || []).length ? (
                            (overview.ai_usage?.by_company || []).map((row: AiUsageCompanyRow) => (
                              <tr key={`${row.company_id || "none"}-${row.company_code || ""}`}>
                                <td>
                                  <div className="font-semibold text-foreground">{companyLabel(row)}</div>
                                  <div className="text-xs text-muted-foreground">{row.company_name || "-"}</div>
                                </td>
                                <td>{formatPlainNumber(row.event_count)}</td>
                                <td>{formatCompactNumber(row.prompt_token_count)}</td>
                                <td>{formatCompactNumber(row.thoughts_token_count)}</td>
                                <td>
                                  <div>{formatUsd(row.estimated_total_cost_usd)}</div>
                                  {numberValue(row.cost_warning_count) > 0 ? (
                                    <Badge tone="warning">{formatPlainNumber(row.cost_warning_count)} expensive</Badge>
                                  ) : null}
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={5}>AI usage hali yozilmagan.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div>
                    <div className="mb-2 text-sm font-semibold text-foreground">Modullar bo'yicha</div>
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Module</th>
                            <th>Calls</th>
                            <th>Input</th>
                            <th>Thinking</th>
                            <th>Cost</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(overview.ai_usage?.by_module || []).length ? (
                            (overview.ai_usage?.by_module || []).map((row: AiUsageModuleRow) => (
                              <tr key={row.module_key || "unknown"}>
                                <td className="font-semibold text-foreground">{moduleLabel(row.module_key)}</td>
                                <td>{formatPlainNumber(row.event_count)}</td>
                                <td>{formatCompactNumber(row.prompt_token_count)}</td>
                                <td>{formatCompactNumber(row.thoughts_token_count)}</td>
                                <td>
                                  <div>{formatUsd(row.estimated_total_cost_usd)}</div>
                                  {numberValue(row.cost_warning_count) > 0 ? (
                                    <Badge tone="warning">{formatPlainNumber(row.cost_warning_count)} expensive</Badge>
                                  ) : null}
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={5}>Module bo'yicha usage hali yo'q.</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </SettingsBaseCard>

              <SettingsBaseCard
                header={<SectionHeader eyebrow="Recent Calls" title="Oxirgi AI chaqiruvlar" />}
              >
                <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_140px] lg:items-end">
                  <BaseSelectField
                    className={SETTINGS_SELECT_CLASS}
                    label="Tenant filter"
                    onChange={(value) =>
                      setUsageFilters((current) => ({
                        ...current,
                        tenant: value,
                      }))
                    }
                    value={usageFilters.tenant}
                  >
                    <option value="">Barcha tenantlar</option>
                    {usageFilterOptions.tenants.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </BaseSelectField>
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    label="Task filter"
                    onChange={(value) =>
                      setUsageFilters((current) => ({
                        ...current,
                        task: value,
                      }))
                    }
                    placeholder="DEV-1234"
                    value={usageFilters.task}
                  />
                  <BaseSelectField
                    className={SETTINGS_SELECT_CLASS}
                    label="Module filter"
                    onChange={(value) =>
                      setUsageFilters((current) => ({
                        ...current,
                        module: value,
                      }))
                    }
                    value={usageFilters.module}
                  >
                    <option value="">Barcha modullar</option>
                    {usageFilterOptions.modules.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </BaseSelectField>
                  <Button
                    disabled={!usageFiltersActive}
                    fullWidth
                    onClick={() => setUsageFilters({ module: "", task: "", tenant: "" })}
                    type="button"
                    variant="soft"
                  >
                    Tozalash
                  </Button>
                </div>
                <div className="mt-4 table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Tenant</th>
                        <th>Task</th>
                        <th>Module / Agent</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentUsageEvents.length ? (
                        filteredUsageEvents.length ? (
                          filteredUsageEvents.map((row: AiUsageEventRow) => (
                            <tr key={row.id || `${row.created_at}-${row.task_key}-${row.agent_key}`}>
                              <td>{formatDateTime(row.created_at)}</td>
                              <td>{row.company_code || (row.company_id ? `#${row.company_id}` : "-")}</td>
                              <td>
                                <div className="font-semibold text-foreground">{row.task_key || "-"}</div>
                                <div className="text-xs text-muted-foreground">{row.source || "-"}</div>
                              </td>
                              <td>
                                <div>{moduleLabel(row.module_key)}</div>
                                <div className="text-xs text-muted-foreground">{row.agent_key || "-"}</div>
                              </td>
                              <td>
                                <div>{row.model || "-"}</div>
                                <div className="text-xs text-muted-foreground">{row.pricing_tier || "-"}</div>
                              </td>
                              <td>
                                <div>{formatCompactNumber(row.total_token_count)} total</div>
                                <div className="text-xs text-muted-foreground">
                                  {formatCompactNumber(row.prompt_token_count)} in ·{" "}
                                  {formatCompactNumber(row.thoughts_token_count)} think
                                </div>
                              </td>
                              <td>
                                <div>{formatUsd(row.estimated_total_cost_usd)}</div>
                                {row.cost_warning ? <Badge tone="warning">expensive</Badge> : null}
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={7}>Tanlangan filterlar bo'yicha AI chaqiruv topilmadi.</td>
                          </tr>
                        )
                      ) : (
                        <tr>
                          <td colSpan={7}>Real Gemini chaqiruvi bo'lgandan keyin yozuvlar chiqadi.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </SettingsBaseCard>
            </>
          ) : null}

          {tab === "jobs" ? <AdminJobsPanel /> : null}

          {tab === "platform" ? (
            <SettingsBaseCard header={<SectionHeader eyebrow="PLATFORM ADMIN" title="Super admin parolini yangilash" />}>
              <form className="mt-4 grid gap-4 md:max-w-xl" onSubmit={savePlatformAdminPassword}>
                <BaseInputField
                  className={SETTINGS_INPUT_CLASS}
                  label="Username"
                  onChange={(value) =>
                    setPlatformAdminForm((current) => ({
                      ...current,
                      username: value,
                    }))
                  }
                  value={platformAdminForm.username}
                />
                <BaseInputField
                  className={SETTINGS_INPUT_CLASS}
                  label="Yangi parol"
                  onChange={(value) =>
                    setPlatformAdminForm((current) => ({
                      ...current,
                      password: value,
                    }))
                  }
                  placeholder="Kamida 8 belgi"
                  type="password"
                  value={platformAdminForm.password}
                />
                <BaseInputField
                  className={SETTINGS_INPUT_CLASS}
                  label="Parolni tasdiqlang"
                  onChange={(value) =>
                    setPlatformAdminForm((current) => ({
                      ...current,
                      confirm_password: value,
                    }))
                  }
                  placeholder="Qayta kiriting"
                  type="password"
                  value={platformAdminForm.confirm_password}
                />
                <div>
                  <Button disabled={busy} type="submit">
                    {busy ? "Saqlanmoqda..." : "Parolni o'zgartirish"}
                  </Button>
                </div>
              </form>
            </SettingsBaseCard>
          ) : null}

          {tab === "system" ? (
            <SettingsBaseCard
              header={(
                <SectionHeader
                  action={<Badge tone="soft">Platform scope</Badge>}
                  eyebrow="SYSTEM DEFAULTS"
                  title="Global queue va timeout konfiguratsiya"
                />
              )}
            >
              <form className="mt-4 grid gap-4 md:max-w-3xl" onSubmit={saveSystemSettings}>
                <div className="grid gap-4 md:grid-cols-2">
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Task wait timeout (min)"
                    hint="Navbatda turgan task eng ko'p shuncha daqiqa kutadi; bo'shamasa bloklanib, keyin avtomatik qayta urinadi (yo'qolmaydi)."
                    min={0.1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        task_wait_timeout: minutesInputToSeconds(value),
                      }))
                    }
                    step={0.1}
                    value={secondsToMinutesInput(systemForm.task_wait_timeout)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Gemini min interval (sec)"
                    hint="AI so'rovlar orasidagi eng kam tanaffus. 6 sek = 10 so'rov/daqiqa (Google bepul limiti). '429 limit' ko'p chiqsa oshiring."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        gemini_min_interval: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.gemini_min_interval)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Blocked retry delay (min)"
                    hint="Bu taskning kutish muddati: Gemini timeout/429 sabab blocked bo'lgan task shu daqiqadan oldin retry qilinmaydi."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        blocked_retry_delay: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.blocked_retry_delay)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Blocked check interval (min)"
                    hint="Bu scheduler scan davri: tizim retry vaqti kelgan blocked tasklarni qanchada bir qidiradi. 0.5 = har 30 sekund tekshiradi."
                    min={0.1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        blocked_check_interval: minutesInputToSeconds(value),
                      }))
                    }
                    step={0.1}
                    value={secondsToMinutesInput(systemForm.blocked_check_interval)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Gemini max retries (503/overload)"
                    hint="Bitta Gemini so'rov 503/overload qaytarsa, final xatoga o'tishdan oldin shuncha marta qayta urinadi. Tanaffus: 5s -> 10s -> 20s."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        gemini_max_retries: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.gemini_max_retries)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Key freeze (daqiqa)"
                    hint="Gemini API key 429/quota limit bersa, shu key shuncha daqiqaga muzlatiladi. Shu vaqt ichida boshqa key bo'lsa, tizim o'shanga o'tadi."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        key_freeze_duration: minutesInputToSeconds(value),
                      }))
                    }
                    value={secondsToMinutesInput(systemForm.key_freeze_duration)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="DB connection timeout (sec)"
                    hint="Bazadan bo'sh ulanish (pool'dan) olishda eng ko'p shuncha sekund kutiladi. Odatda 30 yetarli."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        db_connection_timeout: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.db_connection_timeout)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="HTTP timeout (sec)"
                    hint="GitHub, JIRA va Figma so'rovlari uchun timeout. Sekin internet yoki katta repo/fayl bo'lsa oshiring."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        http_timeout: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.http_timeout)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Executor timeout (sec)"
                    hint="Testcase yaratish jarayoni eng ko'p shuncha sekund ishlaydi. Katta task / sekin AI'da oshiring. 120 = 2 daqiqa."
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        executor_timeout: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.executor_timeout)}
                  />
                </div>
                <div>
                  <Button disabled={busy} type="submit">
                    {busy ? "Saqlanmoqda..." : "Saqlash"}
                  </Button>
                </div>
              </form>
            </SettingsBaseCard>
          ) : null}
        </>
      ) : null}

      {createOpen ? (
        <div className="fixed inset-0 z-[1000]">
          <button
            aria-label="Modalni yopish"
            className="absolute inset-0 bg-slate-900/45"
            onClick={() => setCreateOpen(false)}
            type="button"
          />
          <div className="absolute left-1/2 top-1/2 z-[1001] max-h-[calc(100vh-48px)] w-[min(92vw,760px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto">
            <SettingsBaseCard header={<SectionHeader eyebrow="Create Company" title="Yangi kompaniya yaratish" />}>
              <form className="mt-4 grid gap-4" onSubmit={createCompany}>
                <div className="grid gap-4 md:grid-cols-2">
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    label="Kompaniya kodi"
                    onChange={(value) =>
                      setCreateForm((current) => ({
                        ...current,
                        company_code: value,
                      }))
                    }
                    placeholder="smartup"
                    value={createForm.company_code}
                  />
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    label="Kompaniya nomi"
                    onChange={(value) =>
                      setCreateForm((current) => ({
                        ...current,
                        company_name: value,
                      }))
                    }
                    placeholder="Smartup Inc"
                    value={createForm.company_name}
                  />
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    label="Admin username"
                    onChange={(value) =>
                      setCreateForm((current) => ({
                        ...current,
                        admin_username: value,
                      }))
                    }
                    placeholder="admin"
                    value={createForm.admin_username}
                  />
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    label="Admin parol"
                    onChange={(value) =>
                      setCreateForm((current) => ({
                        ...current,
                        admin_password: value,
                      }))
                    }
                    placeholder="Kamida 6 belgi"
                    type="password"
                    value={createForm.admin_password}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="User limiti"
                    min={0}
                    onChange={(value) =>
                      setCreateForm((current) => ({
                        ...current,
                        seat_limit: Number(value || 0),
                      }))
                    }
                    value={String(createForm.seat_limit)}
                  />
                </div>
                <div className="grid gap-2">
                  <p className="text-xs text-muted-foreground">
                    Asosiy modullar (`tz_pr_checker`, `testcase_generator`) default yoqiq.
                    Webhook servislari faqat webhook yoqilganda faollashadi; `monitoring` webhookdan kelib chiqadi.
                  </p>
                  <BaseCheckGroup
                    onChange={(nextValues) =>
                      setCreateForm((current) => ({
                        ...current,
                        enabled_modules: buildManagedModuleState(nextValues),
                      }))
                    }
                    options={moduleOptions(selectedManagedModules(createForm.enabled_modules))}
                    value={selectedManagedModules(createForm.enabled_modules)}
                  />
                </div>
                <div className="flex gap-3">
                  <Button disabled={busy} type="submit">
                    {busy ? "Yaratilmoqda..." : "Yaratish"}
                  </Button>
                  <Button onClick={() => setCreateOpen(false)} type="button" variant="ghost">
                    Bekor qilish
                  </Button>
                </div>
              </form>
            </SettingsBaseCard>
          </div>
        </div>
      ) : null}
    </>
  );
}
