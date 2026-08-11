export const JIRA_COMMENT_SECTIONS = [
  "statistics",
  "ai_pipeline",
  "summary",
  "completed",
  "failed",
  "skipped",
  "issues",
] as const;

export type JiraCommentSection = (typeof JIRA_COMMENT_SECTIONS)[number];

export const JIRA_COMMENT_SECTION_LABELS: Record<JiraCommentSection, string> = {
  statistics: "Statistika",
  ai_pipeline: "AI pipeline",
  summary: "Xulosa",
  completed: "Bajarilgan",
  failed: "Bajarilmagan",
  skipped: "Skip qilingan",
  issues: "Qo'shimcha tekshiruv",
};

export function normalizeJiraCommentSections(value: unknown): JiraCommentSection[] {
  if (!Array.isArray(value)) return [...JIRA_COMMENT_SECTIONS];
  const selected = new Set(value.filter((item): item is string => typeof item === "string"));
  return JIRA_COMMENT_SECTIONS.filter((key) => selected.has(key));
}

export function toggleJiraCommentSection(
  current: readonly string[],
  section: JiraCommentSection,
  enabled: boolean,
): JiraCommentSection[] {
  const selected = new Set(current);
  if (enabled) selected.add(section);
  else selected.delete(section);
  return JIRA_COMMENT_SECTIONS.filter((key) => selected.has(key));
}
