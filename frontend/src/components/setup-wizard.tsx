"use client";

import { useState } from "react";
import { CheckCircle, Circle, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";

import type { SharedSettingsView } from "@/lib/types";

type Step = {
  key: string;
  title: string;
  done: boolean;
  description: string;
  hint: string;
};

function buildSteps(settings: SharedSettingsView | null, webhookUrl: string): Step[] {
  const f = settings?.fields;
  return [
    {
      key: "jira",
      title: "JIRA ulanishi",
      done: Boolean(f?.jira_server && f?.jira_token_present),
      description: "JIRA server manzili va API token sozlang.",
      hint: `Settings → JIRA bo'limiga o'ting va "JIRA Server", "JIRA Email", "JIRA API Token" maydonlarini to'ldiring.`,
    },
    {
      key: "gemini",
      title: "Gemini AI kaliti",
      done: Boolean(f?.gemini_api_key_1_present || f?.gemini_api_key_2_present),
      description: "Google Gemini AI API kalitini qo'shing.",
      hint: `Settings → AI bo'limida "Gemini API Key 1" maydonini to'ldiring. Kalit aistudio.google.com dan olinadi.`,
    },
    {
      key: "github",
      title: "GitHub ulanishi",
      done: Boolean(f?.github_token_present),
      description: "GitHub Personal Access Token qo'shing (PR ma'lumotlari uchun).",
      hint: `Settings → GitHub bo'limida "GitHub Token" va "GitHub Org" maydonlarini to'ldiring.`,
    },
    {
      key: "webhook",
      title: "Webhook JIRA ga ulash",
      done: false,
      description: "JIRA webhook URL ni JIRA Admin panelga qo'shing.",
      hint: `JIRA Admin → System → WebHooks → Create a WebHook. URL: ${webhookUrl || "https://sizning-domen.com/webhook/jira"}. Events: Issue Updated (status change).`,
    },
  ];
}

type SetupWizardProps = {
  settings: SharedSettingsView | null;
  webhookUrl?: string;
};

export function SetupWizard({ settings, webhookUrl = "" }: SetupWizardProps) {
  const steps = buildSteps(settings, webhookUrl);
  const completedCount = steps.filter((s) => s.done).length;
  const allDone = completedCount === steps.length;
  const [open, setOpen] = useState(!allDone);
  const [expandedKey, setExpandedKey] = useState<string | null>(
    steps.find((s) => !s.done)?.key ?? null,
  );

  if (allDone) return null;

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 12,
        marginBottom: 24,
        overflow: "hidden",
        background: "var(--card)",
      }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 20px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          gap: 12,
        }}
        type="button"
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--foreground)" }}>
            🚀 Boshlang'ich sozlash
          </span>
          <span
            style={{
              fontSize: 12,
              padding: "2px 8px",
              borderRadius: 20,
              background: completedCount === steps.length ? "#22c55e22" : "#f59e0b22",
              color: completedCount === steps.length ? "#16a34a" : "#b45309",
              fontWeight: 600,
            }}
          >
            {completedCount}/{steps.length} bajarildi
          </span>
        </div>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {open && (
        <div style={{ borderTop: "1px solid var(--border)", padding: "4px 0 8px" }}>
          {steps.map((step, idx) => (
            <div key={step.key} style={{ borderBottom: idx < steps.length - 1 ? "1px solid var(--border)" : "none" }}>
              <button
                onClick={() => setExpandedKey(expandedKey === step.key ? null : step.key)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "12px 20px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  textAlign: "left",
                }}
                type="button"
              >
                {step.done ? (
                  <CheckCircle size={18} style={{ color: "#22c55e", flexShrink: 0 }} />
                ) : (
                  <Circle size={18} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
                )}
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 500,
                      color: step.done ? "var(--muted-foreground)" : "var(--foreground)",
                      textDecoration: step.done ? "line-through" : "none",
                    }}
                  >
                    {step.title}
                  </div>
                  {!step.done && (
                    <div style={{ fontSize: 12, color: "var(--muted-foreground)", marginTop: 2 }}>
                      {step.description}
                    </div>
                  )}
                </div>
                {!step.done && (
                  expandedKey === step.key ? <ChevronUp size={14} /> : <ChevronDown size={14} />
                )}
              </button>

              {!step.done && expandedKey === step.key && (
                <div
                  style={{
                    padding: "0 20px 16px 50px",
                    fontSize: 13,
                    color: "var(--muted-foreground)",
                    lineHeight: 1.6,
                  }}
                >
                  {step.hint}
                  {step.key === "jira" || step.key === "gemini" || step.key === "github" ? (
                    <div style={{ marginTop: 8 }}>
                      <a
                        href="/settings"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          fontSize: 13,
                          color: "var(--primary)",
                          textDecoration: "none",
                        }}
                      >
                        Settings ga o'tish <ExternalLink size={12} />
                      </a>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
