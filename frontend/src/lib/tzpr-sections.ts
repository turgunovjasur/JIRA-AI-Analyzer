export const CHECKER_VISIBLE_SECTION_KEYS = [
  "completed",
  "failed",
  "issues",
  "figma",
] as const;

export type CheckerVisibleSectionKey = (typeof CHECKER_VISIBLE_SECTION_KEYS)[number];

export const CHECKER_SECTION_LABELS: Record<CheckerVisibleSectionKey | "contradictory_comments", string> = {
  completed: "Bajarilgan talablar",
  failed: "Bajarilmagan talablar",
  issues: "Potensial muammolar",
  figma: "Figma dizayn mosligi",
  contradictory_comments: "Zid commentlar",
};

export const CHECKER_SECTION_PROMPT_TITLES: Record<CheckerVisibleSectionKey | "summary", string> = {
  summary: "🧭 XULOSA",
  completed: "✅ BAJARILGAN TALABLAR",
  failed: "❌ BAJARILMAGAN TALABLAR",
  issues: "🐛 POTENSIAL MUAMMOLAR",
  figma: "🎨 FIGMA DIZAYN MOSLIGI",
};
