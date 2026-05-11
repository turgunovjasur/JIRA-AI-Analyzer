import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";
import { getOptionalSession } from "@/lib/session";
import type { CompanyAdminUser } from "@/lib/types";

export async function requireCompanyAdminSession() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    return {
      error: NextResponse.json(
        { success: false, error: "Sessiya topilmadi yoki muddati tugagan." },
        { status: 401 },
      ),
      session: null,
    };
  }

  if (session.auth.role !== "company_admin" || !session.auth.company_id) {
    return {
      error: NextResponse.json(
        { success: false, error: "Bu route faqat company admin uchun." },
        { status: 403 },
      ),
      session: null,
    };
  }

  return { error: null, session };
}

export function parseUserId(rawValue: string) {
  const userId = Number(rawValue);
  if (!Number.isInteger(userId) || userId <= 0) {
    return null;
  }
  return userId;
}

export async function getCompanyUsers(companyId: number) {
  return callInternalRpc<CompanyAdminUser[]>("get_users_by_company", [companyId]);
}

export function userBelongsToCompany(users: CompanyAdminUser[], userId: number) {
  return users.some((user) => Number(user.id) === userId);
}

export function isProtectedCompanyAdminUser(users: CompanyAdminUser[], userId: number) {
  return users.some(
    (user) => Number(user.id) === userId && (user.role || "user") === "company_admin",
  );
}
