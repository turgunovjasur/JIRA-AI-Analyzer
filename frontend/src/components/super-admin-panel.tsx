"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/metric-card";
import { Notice } from "@/components/ui/notice";
import { PageIntro } from "@/components/ui/page-intro";
import { SectionHeader } from "@/components/ui/section-header";
import {
  BaseCheckGroup,
  BaseInputField,
  BaseInlineActionField,
  BaseSelectField,
  NumberField,
  SettingsBaseCard,
} from "@/components/settings/base-card-system";
import {
  BASE_PLAN_MODULE_KEYS,
  MODULE_CATALOG,
  PAID_ADDON_MODULE_KEYS,
  SUBSCRIPTION_STATUS_LABELS,
} from "@/lib/product-catalog";
import type {
  CompanyModules,
  CompanySubscription,
  SuperAdminCompany,
  SuperAdminOverview,
} from "@/lib/types";

type SuperAdminPanelProps = {
  authSource: string | null;
  currentUsername: string;
};

type SuperAdminTab = "companies" | "ai" | "system" | "platform";

type CompanyCreateForm = {
  admin_password: string;
  admin_username: string;
  company_code: string;
  company_name: string;
  enabled_modules: CompanyModules;
  seat_limit: number;
};

type AiDefaultsForm = {
  api_key_1: string;
  api_key_2: string;
  fallback_model: string;
  key_freeze_minutes: number;
  model: string;
};

type SuperAdminSystemForm = {
  ai_max_retries: number;
  key_freeze_duration: number;
  db_busy_timeout: number;
  db_connection_timeout: number;
  http_timeout: number;
  executor_timeout: number;
};

const SETTINGS_INPUT_CLASS = "settings-form-input";
const SETTINGS_SELECT_CLASS = "settings-form-select";

function buildCreateForm(): CompanyCreateForm {
  const addonDefaults: CompanyModules = Object.fromEntries(
    PAID_ADDON_MODULE_KEYS.map((moduleKey) => [moduleKey, false]),
  );
  return {
    admin_password: "",
    admin_username: "",
    company_code: "",
    company_name: "",
    enabled_modules: addonDefaults,
    seat_limit: 0,
  };
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

function billingTone(company: SuperAdminCompany): "success" | "warning" | "danger" {
  if (company.billing_health.severity === "danger") return "danger";
  if (company.billing_health.severity === "warning") return "warning";
  return "success";
}

function modelOptions() {
  return ["gemini-2.5-pro", "gemini-2.5-flash"];
}

const ADDON_MODULE_OPTIONS = PAID_ADDON_MODULE_KEYS.map((moduleKey) => ({
  badge: moduleKey,
  key: moduleKey,
  label: MODULE_CATALOG[moduleKey]?.label || moduleKey,
}));

function selectedAddonModules(modules: CompanyModules | undefined): string[] {
  return PAID_ADDON_MODULE_KEYS.filter((moduleKey) => Boolean(modules?.[moduleKey]));
}

function buildAddonModuleState(selected: string[]): CompanyModules {
  return Object.fromEntries(
    PAID_ADDON_MODULE_KEYS.map((moduleKey) => [moduleKey, selected.includes(moduleKey)]),
  ) as CompanyModules;
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
    api_key_1: "",
    api_key_2: "",
    fallback_model: "gemini-2.5-flash",
    key_freeze_minutes: 10,
    model: "gemini-2.5-pro",
  });
  const [showApiKey1, setShowApiKey1] = useState(false);
  const [showApiKey2, setShowApiKey2] = useState(false);
  const [platformAdminForm, setPlatformAdminForm] = useState({
    confirm_password: "",
    password: "",
    username: currentUsername,
  });
  const [systemForm, setSystemForm] = useState<SuperAdminSystemForm>({
    ai_max_retries: 3,
    key_freeze_duration: 600,
    db_busy_timeout: 30000,
    db_connection_timeout: 30,
    http_timeout: 30,
    executor_timeout: 120,
  });
  const [openCompanyId, setOpenCompanyId] = useState<number | null>(null);
  const [seatDrafts, setSeatDrafts] = useState<Record<number, number>>({});
  const [moduleDrafts, setModuleDrafts] = useState<Record<number, CompanyModules>>({});
  const [subscriptionDrafts, setSubscriptionDrafts] = useState<Record<number, CompanySubscription>>({});
  const [deleteDrafts, setDeleteDrafts] = useState<Record<number, string>>({});
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const companyMetrics = useMemo(() => {
    if (!overview) return { activeRate: 0, totalUsers: 0 };
    const totalUsers = overview.companies.reduce((sum, company) => sum + (company.total_accounts || 0), 0);
    const activeRate = overview.metrics.total
      ? Math.round((overview.metrics.active / overview.metrics.total) * 100)
      : 0;
    return { activeRate, totalUsers };
  }, [overview]);

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
            Object.fromEntries(
              PAID_ADDON_MODULE_KEYS.map((moduleKey) => [moduleKey, Boolean(company.modules?.[moduleKey])]),
            ),
          ]),
        ),
      );
      setSubscriptionDrafts(
        Object.fromEntries(
          payload.companies.map((company) => [company.id, { ...(company.subscription || {}) }]),
        ),
      );
      setAiForm((current) => ({
        api_key_1: current.api_key_1,
        api_key_2: current.api_key_2,
        fallback_model: payload.global_ai_defaults.fallback_model || "gemini-2.5-flash",
        key_freeze_minutes: payload.global_ai_defaults.key_freeze_minutes ?? 10,
        model: payload.global_ai_defaults.model || "gemini-2.5-pro",
      }));
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
          ai_max_retries: Number(payload.data.ai_max_retries ?? 3),
          key_freeze_duration: Number(payload.data.key_freeze_duration ?? 600),
          db_busy_timeout: Number(payload.data.db_busy_timeout ?? 30000),
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
      const response = await fetch("/api/super-admin/ai-defaults", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(aiForm),
      });
      const payload = await parseJson<{ error?: string; success?: boolean }>(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "AI sozlamalar saqlanmadi.");
      }

      setSuccess("AI sozlamalar saqlandi.");
      await loadOverview();
    });
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
              <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard helper="Tenantlar" label="Jami" value={overview.metrics.total} />
                <MetricCard helper="Ishlayotgan" label="Faol" value={overview.metrics.active} />
                <MetricCard helper="Barcha kompaniya" label="Jami users" value={companyMetrics.totalUsers} />
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
                <div className="mt-4 grid gap-3">
                  {overview.companies.length ? (
                    overview.companies.map((company) => {
                      const moduleDraft = moduleDrafts[company.id] || company.modules || {};
                      const subscriptionDraft = subscriptionDrafts[company.id] || company.subscription;
                      const deleteMatch =
                        (deleteDrafts[company.id] || "").trim().toLowerCase() ===
                        company.company_code.toLowerCase();

                      return (
                        <details
                          key={company.id}
                          className="co-card"
                          open={openCompanyId === company.id}
                        >
                          <summary
                            className="co-summary"
                            onClick={(event) => {
                              event.preventDefault();
                              setOpenCompanyId((current) => (current === company.id ? null : company.id));
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 700, fontSize: 14.5 }}>
                                {company.company_code.toUpperCase()} - {company.company_name}
                              </div>
                              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                                {company.total_accounts}/{company.seat_limit} user · Plan:{" "}
                                {company.subscription.plan_name || "base"} ·{" "}
                                {formatDate(company.subscription.billing_end_date || company.created_at)}
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
                                    <strong>Base:</strong> {BASE_PLAN_MODULE_KEYS.join(", ")} (doim yoqilgan) ·{" "}
                                    <strong>Derived:</strong> monitoring (webhook yoqilganda avtomatik ochiladi)
                                  </p>
                                  <BaseCheckGroup
                                    onChange={(nextValues) =>
                                      setModuleDrafts((current) => ({
                                        ...current,
                                        [company.id]: buildAddonModuleState(nextValues),
                                      }))
                                    }
                                    options={ADDON_MODULE_OPTIONS}
                                    value={selectedAddonModules(moduleDraft)}
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
                                    value={subscriptionDraft.billing_end_date || ""}
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
                        </details>
                      );
                    })
                  ) : (
                    <p className="rounded-[14px] border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">
                      Hali kompaniyalar yaratilmagan.
                    </p>
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
                  title="Global Gemini konfiguratsiya"
                />
              )}
            >
              <form className="mt-4 grid gap-4" onSubmit={saveAiDefaults}>
                <div className="grid gap-4 md:grid-cols-2">
                  <BaseSelectField
                    className={SETTINGS_SELECT_CLASS}
                    label="Gemini Model"
                    onChange={(value) =>
                      setAiForm((current) => ({ ...current, model: value }))
                    }
                    value={aiForm.model}
                  >
                    {modelOptions().map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </BaseSelectField>
                  <BaseSelectField
                    className={SETTINGS_SELECT_CLASS}
                    label="Fallback Model"
                    onChange={(value) =>
                      setAiForm((current) => ({ ...current, fallback_model: value }))
                    }
                    value={aiForm.fallback_model}
                  >
                    {modelOptions().map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </BaseSelectField>
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    hint={overview.global_ai_defaults.api_key_1_present ? "Saqlangan (yangilash uchun kiriting)" : undefined}
                    label="API Key 1"
                    onChange={(value) =>
                      setAiForm((current) => ({ ...current, api_key_1: value }))
                    }
                    placeholder={
                      overview.global_ai_defaults.api_key_1_present
                        ? "Saqlangan (yangilash uchun yangi key kiriting)"
                        : "AIza..."
                    }
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
                    type={showApiKey1 ? "text" : "password"}
                    value={aiForm.api_key_1}
                  />
                  <BaseInputField
                    className={SETTINGS_INPUT_CLASS}
                    hint={overview.global_ai_defaults.api_key_2_present ? "Saqlangan (yangilash uchun kiriting)" : undefined}
                    label="API Key 2 (backup)"
                    onChange={(value) =>
                      setAiForm((current) => ({ ...current, api_key_2: value }))
                    }
                    placeholder={
                      overview.global_ai_defaults.api_key_2_present
                        ? "Saqlangan (yangilash uchun yangi key kiriting)"
                        : "AIza..."
                    }
                    rightSlot={(
                      <button
                        aria-label={showApiKey2 ? "API Key 2 ni yashirish" : "API Key 2 ni ko'rsatish"}
                        className="eye-btn"
                        onClick={() => setShowApiKey2((current) => !current)}
                        type="button"
                      >
                        {showApiKey2 ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    )}
                    type={showApiKey2 ? "text" : "password"}
                    value={aiForm.api_key_2}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Key freeze (daqiqa)"
                    min={1}
                    onChange={(value) =>
                      setAiForm((current) => ({
                        ...current,
                        key_freeze_minutes: Number(value || 0),
                      }))
                    }
                    value={String(aiForm.key_freeze_minutes)}
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
                    label="AI max retries"
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        ai_max_retries: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.ai_max_retries)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="Key freeze duration (sec)"
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        key_freeze_duration: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.key_freeze_duration)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="DB busy timeout (ms)"
                    min={1}
                    onChange={(value) =>
                      setSystemForm((current) => ({
                        ...current,
                        db_busy_timeout: Number(value || 0),
                      }))
                    }
                    value={String(systemForm.db_busy_timeout)}
                  />
                  <NumberField
                    inputClassName={SETTINGS_INPUT_CLASS}
                    label="DB connection timeout (sec)"
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
        <div className="fixed inset-0 z-40">
          <button
            aria-label="Modalni yopish"
            className="absolute inset-0 bg-slate-900/45"
            onClick={() => setCreateOpen(false)}
            type="button"
          />
          <div className="absolute left-1/2 top-1/2 z-50 w-[min(92vw,760px)] -translate-x-1/2 -translate-y-1/2">
            <SettingsBaseCard className="card p-6" header={<SectionHeader eyebrow="Create Company" title="Yangi kompaniya yaratish" />}>
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
                    Base modullar (`tz_pr_checker`, `testcase_generator`) avtomatik yoqiladi.
                    `monitoring` esa `webhook` addonidan kelib chiqadi.
                  </p>
                  <BaseCheckGroup
                    onChange={(nextValues) =>
                      setCreateForm((current) => ({
                        ...current,
                        enabled_modules: buildAddonModuleState(nextValues),
                      }))
                    }
                    options={ADDON_MODULE_OPTIONS}
                    value={selectedAddonModules(createForm.enabled_modules)}
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
