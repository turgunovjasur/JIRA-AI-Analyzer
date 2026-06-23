export const CHECKER_VISIBLE_SECTION_KEYS = [
  "completed",
  "failed",
  "skipped",
  "issues",
  "figma",
] as const;

export type CheckerVisibleSectionKey = (typeof CHECKER_VISIBLE_SECTION_KEYS)[number];

export const CHECKER_SECTION_LABELS: Record<CheckerVisibleSectionKey | "contradictory_comments", string> = {
  completed: "Bajarilgan talablar",
  failed: "Bajarilmagan talablar",
  skipped: "Skip qilingan talablar",
  issues: "Potensial muammolar",
  figma: "Figma dizayn mosligi",
  contradictory_comments: "Zid commentlar",
};

export const CHECKER_SECTION_PROMPT_TITLES: Record<CheckerVisibleSectionKey | "summary", string> = {
  summary: "🧭 XULOSA",
  completed: "✅ BAJARILGAN TALABLAR",
  failed: "❌ BAJARILMAGAN TALABLAR",
  skipped: "⏭️ SKIP QILINGAN",
  issues: "🐛 POTENSIAL MUAMMOLAR",
  figma: "🎨 FIGMA DIZAYN MOSLIGI",
};
