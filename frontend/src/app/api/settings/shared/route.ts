import { NextResponse } from "next/server";

import {
  readSharedSettingsWithBackend,
  saveSharedSettingsWithBackend,
} from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";
import type { SharedSettingsSaveRequest, SharedSettingsView } from "@/lib/types";

function textValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function hasSecret(value: unknown) {
  return typeof value === "string" && value.trim().length > 0;
}

function maskSecret(value: unknown) {
  const raw = textValue(value).trim();
  if (!raw) return "";
  const tail = raw.slice(-4);
  const stars = "*".repeat(Math.max(4, raw.length - tail.length));
  return `${stars}${tail}`;
}

function buildIntegrationStatus(raw: Record<string, unknown>) {
  return {
    jira:
      hasSecret(raw.jira_token) &&
      Boolean(textValue(raw.jira_email)) &&
      Boolean(textValue(raw.jira_project_keys)),
    github: hasSecret(raw.github_token) && Boolean(textValue(raw.github_org)),
    figma:
      hasSecret(raw.figma_token) ||
      Array.isArray(raw.figma_tokens) ||
      Boolean(textValue(raw.figma_tokens)),
    gemini: hasSecret(raw.gemini_api_key_1) || hasSecret(raw.gemini_api_key_2),
  };
}

function buildView(params: {
  editable: boolean;
  mode: SharedSettingsView["mode"];
  role?: SharedSettingsView["role"];
  companyName?: string | null;
  raw: Record<string, unknown>;
  statusSource?: Record<string, unknown>;
}) {
  const source = params.raw || {};
  const statusSource = params.statusSource || source;
  return {
    success: true,
    mode: params.mode,
    editable: params.editable,
    role: params.role || null,
    company_name: params.companyName || null,
    fields: {
      jira_server: textValue(source.jira_server),
      jira_email: textValue(source.jira_email),
      jira_project_keys: textValue(source.jira_project_keys),
      github_org: textValue(source.github_org),
      gemini_model: textValue(source.gemini_model),
      figma_token_mask: maskSecret(source.figma_token),
      jira_token_mask: maskSecret(source.jira_token),
      github_token_mask: maskSecret(source.github_token),
      gemini_api_key_1_mask: maskSecret(source.gemini_api_key_1),
      gemini_api_key_2_mask: maskSecret(source.gemini_api_key_2),
      figma_token_present: hasSecret(source.figma_token),
      jira_token_present: hasSecret(source.jira_token),
      github_token_present: hasSecret(source.github_token),
      gemini_api_key_1_present: hasSecret(source.gemini_api_key_1),
      gemini_api_key_2_present: hasSecret(source.gemini_api_key_2),
    },
    integration_status: buildIntegrationStatus(statusSource),
  } satisfies SharedSettingsView;
}

export async function GET() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json({ success: false, error: "Sessiya topilmadi." }, { status: 401 });
  }

  const role = session.auth.role;
  const companyId = session.auth.company_id || null;
  const userId = session.auth.user_id || null;
  const companyName = session.auth.company_name || "Platform";

  try {
    if (role === "company_admin" && companyId) {
      const companyPayload = await readSharedSettingsWithBackend({
        company_id: companyId,
        is_company_admin: true,
      });
      return NextResponse.json(
        buildView({
          mode: "company",
          editable: true,
          role,
          companyName,
          raw: companyPayload.data || {},
        }),
      );
    }

    if (role === "user" && userId) {
      const [userPayload, companyPayload] = await Promise.all([
        readSharedSettingsWithBackend({
          user_id: userId,
          company_id: companyId,
          is_company_admin: false,
        }),
        companyId
          ? readSharedSettingsWithBackend({
              company_id: companyId,
              is_company_admin: true,
            })
          : Promise.resolve({ data: {} }),
      ]);

      return NextResponse.json(
        buildView({
          mode: "user",
          editable: true,
          role,
          companyName,
          raw: userPayload.data || {},
          statusSource: (companyPayload.data || {}) as Record<string, unknown>,
        }),
      );
    }

    return NextResponse.json(
      buildView({
        mode: "platform",
        editable: false,
        role,
        companyName,
        raw: {},
      }),
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Settings o'qishda xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return NextResponse.json({ success: false, error: "Sessiya topilmadi." }, { status: 401 });
  }

  const role = session.auth.role;
  const companyId = session.auth.company_id || null;
  const userId = session.auth.user_id || null;

  if (role !== "company_admin" && role !== "user") {
    return NextResponse.json(
      { success: false, error: "Bu sessiya settings save uchun mos emas." },
      { status: 403 },
    );
  }

  try {
    const payload = (await request.json()) as SharedSettingsSaveRequest;
    const data: SharedSettingsSaveRequest = {};

    if (role === "company_admin") {
      if (typeof payload.jira_server === "string") data.jira_server = payload.jira_server.trim();
      if (typeof payload.jira_email === "string") data.jira_email = payload.jira_email.trim();
      if (typeof payload.jira_project_keys === "string") data.jira_project_keys = payload.jira_project_keys.trim();
      if (typeof payload.github_org === "string") data.github_org = payload.github_org.trim();
      if (typeof payload.gemini_model === "string") data.gemini_model = payload.gemini_model.trim();
      // Credential maydonlari faqat dirty/cleared bo'lganda yuboriladi.
      // Bo'sh string = aniq o'chirish (clear); shuning uchun trim emas, present tekshiriladi.
      if (typeof payload.figma_token === "string") data.figma_token = payload.figma_token.trim();
      if (typeof payload.jira_token === "string") data.jira_token = payload.jira_token.trim();
      if (typeof payload.github_token === "string") data.github_token = payload.github_token.trim();
    } else {
      if (typeof payload.gemini_model === "string") data.gemini_model = payload.gemini_model.trim();
    }

    if (typeof payload.gemini_api_key_1 === "string") data.gemini_api_key_1 = payload.gemini_api_key_1.trim();
    if (typeof payload.gemini_api_key_2 === "string") data.gemini_api_key_2 = payload.gemini_api_key_2.trim();

    if (role === "company_admin" && !Object.keys(data).length) {
      return NextResponse.json(
        { success: false, error: "Saqlash uchun kamida bitta maydon kiriting." },
        { status: 400 },
      );
    }

    if (role === "user" && !Object.keys(data).length) {
      return NextResponse.json(
        { success: false, error: "Saqlash uchun kamida bitta maydon kiriting." },
        { status: 400 },
      );
    }

    const saveResult = await saveSharedSettingsWithBackend({
      user_id: userId,
      company_id: companyId,
      is_company_admin: role === "company_admin",
      data,
    });

    if (!saveResult.success) {
      return NextResponse.json(
        {
          success: false,
          error: saveResult.reasons?.join(" ") || "Settings saqlanmadi.",
        },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Settings save xatosi yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
