import { describe, expect, it } from "vitest";

import {
  JIRA_COMMENT_SECTIONS,
  normalizeJiraCommentSections,
  toggleJiraCommentSection,
} from "@/lib/jira-comment-sections";

describe("JIRA comment sections", () => {
  it("keeps the canonical seven-section order", () => {
    expect(JIRA_COMMENT_SECTIONS).toEqual([
      "statistics",
      "ai_pipeline",
      "summary",
      "completed",
      "failed",
      "skipped",
      "issues",
    ]);
  });

  it("enables and disables one section without changing canonical order", () => {
    expect(toggleJiraCommentSection(["summary", "failed"], "statistics", true)).toEqual([
      "statistics",
      "summary",
      "failed",
    ]);
    expect(toggleJiraCommentSection(["statistics", "summary", "failed"], "summary", false)).toEqual([
      "statistics",
      "failed",
    ]);
    expect(toggleJiraCommentSection(["failed"], "failed", false)).toEqual([]);
  });

  it("normalizes missing and unknown API values", () => {
    expect(normalizeJiraCommentSections(undefined)).toEqual(JIRA_COMMENT_SECTIONS);
    expect(normalizeJiraCommentSections(["failed", "unknown", "summary", "failed"])).toEqual([
      "summary",
      "failed",
    ]);
    expect(normalizeJiraCommentSections([])).toEqual([]);
  });
});
