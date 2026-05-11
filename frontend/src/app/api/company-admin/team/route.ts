import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";
import type { CompanyAdminTeamOverview, CompanyAdminUser } from "@/lib/types";

import { requireCompanyAdminSession } from "../_helpers";

export async function GET() {
  const { error, session } = await requireCompanyAdminSession();
  if (error || !session) {
    return error;
  }

  const companyId = session.auth.company_id as number;

  try {
    const [company, users, extraUserCount] = await Promise.all([
      callInternalRpc<Record<string, unknown> | null>("get_company_by_id", [companyId]),
      callInternalRpc<CompanyAdminUser[]>("get_users_by_company", [companyId]),
      callInternalRpc<number>("count_users_in_company", [companyId]),
    ]);

    if (!company) {
      return NextResponse.json(
        { success: false, error: "Kompaniya topilmadi." },
        { status: 404 },
      );
    }

    const seatLimit = Math.max(0, Number(company.seat_limit || 0));
    const payload: CompanyAdminTeamOverview = {
      success: true,
      company: {
        id: Number(company.id || companyId),
        company_code: typeof company.company_code === "string" ? company.company_code : "",
        company_name: typeof company.company_name === "string" ? company.company_name : "",
        seat_limit: seatLimit,
      },
      users: Array.isArray(users) ? users : [],
      total_accounts: Array.isArray(users) ? users.length : 0,
      extra_user_count: Number(extraUserCount || 0),
      available_slots: Math.max(seatLimit - Number(extraUserCount || 0), 0),
    };

    return NextResponse.json(payload);
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Team ma'lumotlarini olishda xato.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
