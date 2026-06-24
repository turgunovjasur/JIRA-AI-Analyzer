export const MODULE_CATALOG = {
  tz_pr_checker: {
    icon: "🔍",
    label: "TZ-PR Checker",
  },
  testcase_generator: {
    icon: "🧪",
    label: "Test Case Generator",
  },
  monitoring: {
    icon: "📈",
    label: "Monitoring",
  },
  webhook: {
    icon: "🔗",
    label: "JIRA Webhook",
  },
  webhook_service1: {
    icon: "🔍",
    label: "Webhook · Servis-1 (Checker)",
  },
  webhook_service2: {
    icon: "🧪",
    label: "Webhook · Servis-2 (Testcase)",
  },
} as const;

export const BASE_PLAN_MODULE_KEYS = ["tz_pr_checker", "testcase_generator"] as const;
export const PAID_ADDON_MODULE_KEYS = ["webhook"] as const;
// Webhook addon yoqilganda alohida boshqariladigan sub-servislar.
export const WEBHOOK_SERVICE_MODULE_KEYS = ["webhook_service1", "webhook_service2"] as const;
// Super-admin per-company yoqib-o'chira oladigan barcha modul kalitlari
// (monitoring derived bo'lgani uchun bu ro'yxatda yo'q).
export const SUPER_ADMIN_MANAGED_MODULE_KEYS = [
  "tz_pr_checker",
  "testcase_generator",
  "webhook",
  "webhook_service1",
  "webhook_service2",
] as const;

export const SUBSCRIPTION_STATUS_LABELS = {
  active: "Active",
  cancelled: "Cancelled",
  past_due: "Past Due",
  suspended: "Suspended",
  trial: "Trial",
} as const;

export type ModuleCatalogKey = keyof typeof MODULE_CATALOG;

export function getModuleLabel(moduleKey: string) {
  return MODULE_CATALOG[moduleKey as ModuleCatalogKey]?.label || moduleKey;
}

export function getModuleIcon(moduleKey: string) {
  return MODULE_CATALOG[moduleKey as ModuleCatalogKey]?.icon || "•";
}
