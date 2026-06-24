import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { appendFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

import { callInternalRpc } from "@/lib/backend";
import { BASE_PLAN_MODULE_KEYS, SUPER_ADMIN_MANAGED_MODULE_KEYS } from "@/lib/product-catalog";
import type { CompanyModules } from "@/lib/types";

import { requireSuperAdminSession } from "../_helpers";

type CompanyCreateResult = {
  company_code?: string | null;
  company_name?: string | null;
  id?: number | null;
};

type RawCompany = {
  company_code?: string | null;
};

function resolveDebugLogPath() {
  const cwd = process.cwd();
  const candidates = [
    { dir: path.resolve(cwd, "data"), marker: path.resolve(cwd, "data", "webhook.log") },
    { dir: path.resolve(cwd, "..", "data"), marker: path.resolve(cwd, "..", "data", "webhook.log") },
  ];
  const matched = candidates.find((item) => existsSync(item.marker));
  const baseDir = matched?.dir || candidates[0].dir;
  return path.join(baseDir, "company_create_debug.log");
}

async function writeCompanyCreateDebug(line: string) {
  try {
    const filePath = resolveDebugLogPath();
    await mkdir(path.dirname(filePath), { recursive: true });
    await appendFile(filePath, `${line}\n`, "utf8");
  } catch {
    // Debug logging best-effort: request flow break bo'lmasin.
  }
}

export async function POST(request: Request) {
  const debugId = randomUUID().slice(0, 8);
  const { error, session } = await requireSuperAdminSession();
  if (error || !session) {
    return error;
  }

  try {
    const payload = (await request.json().catch(() => null)) as {
      admin_password?: string;
      admin_username?: string;
      company_code?: string;
      company_name?: string;
      enabled_modules?: CompanyModules;
      seat_limit?: number;
    } | null;

    const companyCode = (payload?.company_code || "").trim().toLowerCase();
    const companyName = (payload?.company_name || "").trim();
    const adminUsername = (payload?.admin_username || "").trim().toLowerCase();
    const adminPassword = payload?.admin_password || "";
    const seatLimit = Number(payload?.seat_limit || 0);

    const startedLine =
      `[company-create:${debugId}] start | by=${session.auth.user_name || "super_admin"} | ` +
      `code=${companyCode} | admin=${adminUsername} | seat_limit=${seatLimit}`;
    console.info(startedLine);
    await writeCompanyCreateDebug(startedLine);

    if (!companyCode || !companyName || !adminUsername) {
      return NextResponse.json(
        { success: false, error: "Kompaniya kodi, nomi va admin username majburiy." },
        { status: 400 },
      );
    }

    if (!companyCode.replace(/[-_]/g, "").match(/^[a-z0-9]+$/)) {
      return NextResponse.json(
        { success: false, error: "Kompaniya kodi faqat kichik lotin harf va raqamdan iborat bo'lishi kerak." },
        { status: 400 },
      );
    }

    if (adminPassword.length < 6) {
      return NextResponse.json(
        { success: false, error: "Admin paroli kamida 6 ta belgi bo'lishi kerak." },
        { status: 400 },
      );
    }

    if (!Number.isFinite(seatLimit) || seatLimit < 0) {
      return NextResponse.json(
        { success: false, error: "User limiti 0 yoki undan katta bo'lishi kerak." },
        { status: 400 },
      );
    }

    const baseModuleKeys = BASE_PLAN_MODULE_KEYS as readonly string[];
    const enabledModules: Record<string, boolean> = {};
    for (const moduleKey of SUPER_ADMIN_MANAGED_MODULE_KEYS) {
      const sent = payload?.enabled_modules?.[moduleKey];
      // Asosiy modullar default yoqiq; webhook va servislar default o'chiq.
      enabledModules[moduleKey] = sent === undefined ? baseModuleKeys.includes(moduleKey) : Boolean(sent);
    }
    if (!enabledModules.webhook) {
      enabledModules.webhook_service1 = false;
      enabledModules.webhook_service2 = false;
    }

    const company = await callInternalRpc<CompanyCreateResult | null>("create_company", [
      companyCode,
      companyName,
      Math.max(0, Number.isFinite(seatLimit) ? seatLimit : 0),
      enabledModules,
    ]);

    if (!company?.id) {
      const existingCompanies = await callInternalRpc<RawCompany[]>("get_all_companies");
      const duplicate = (existingCompanies || []).some(
        (item) => (item.company_code || "").trim().toLowerCase() === companyCode,
      );

      const failedCreateLine =
        `[company-create:${debugId}] create_company returned empty | code=${companyCode} | ` +
        `duplicate=${duplicate} | modules=${JSON.stringify(enabledModules)}`;
      console.error(failedCreateLine);
      await writeCompanyCreateDebug(failedCreateLine);

      return NextResponse.json(
        {
          success: false,
          error: duplicate
            ? "Bu kompaniya kodi band. Boshqa kod kiriting."
            : `Kompaniya yaratilmadi. Debug ID: ${debugId}`,
        },
        { status: 400 },
      );
    }

    const createUserResult = await callInternalRpc<[Record<string, unknown> | null, string | null]>(
      "create_user",
      [Number(company.id), adminUsername, adminPassword, "company_admin"],
    );

    const createdAdmin = Array.isArray(createUserResult) ? createUserResult[0] : null;
    const createUserError = Array.isArray(createUserResult)
      ? createUserResult[1]
      : "Company admin yaratilmadi.";

    if (!createdAdmin) {
      const rollbackOk = await callInternalRpc<boolean>("delete_company", [Number(company.id)]).catch(() => false);
      const createUserFailLine =
        `[company-create:${debugId}] create_user failed | company_id=${company.id} | ` +
        `admin=${adminUsername} | err=${createUserError || "unknown"} | rollback=${rollbackOk}`;
      console.error(createUserFailLine);
      await writeCompanyCreateDebug(createUserFailLine);
      return NextResponse.json(
        { success: false, error: `${createUserError || "Company admin yaratilmadi."} (Debug ID: ${debugId})` },
        { status: 400 },
      );
    }

    const successLine =
      `[company-create:${debugId}] success | company_id=${company.id} | code=${companyCode} | admin_id=${(createdAdmin as { id?: number })?.id || "?"}`;
    console.info(successLine);
    await writeCompanyCreateDebug(successLine);

    return NextResponse.json({ success: true, company });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Kompaniya yaratishda xato yuz berdi.";
    const unhandledLine =
      `[company-create:${debugId}] unhandled route error | msg=${message}`;
    console.error(unhandledLine, routeError);
    await writeCompanyCreateDebug(unhandledLine);
    return NextResponse.json(
      { success: false, error: `${message} (Debug ID: ${debugId})` },
      { status: 500 },
    );
  }
}
