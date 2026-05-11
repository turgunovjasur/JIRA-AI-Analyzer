import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";
import type { CompanyAdminResetTokenPayload } from "@/lib/types";

import {
  getCompanyUsers,
  parseUserId,
  requireCompanyAdminSession,
  userBelongsToCompany,
} from "../../../_helpers";

export async function POST(
  _request: Request,
  context: { params: Promise<{ userId: string }> },
) {
  const { error, session } = await requireCompanyAdminSession();
  if (error || !session) {
    return error;
  }

  const { userId: rawUserId } = await context.params;
  const userId = parseUserId(rawUserId);
  if (!userId) {
    return NextResponse.json({ success: false, error: "userId noto'g'ri." }, { status: 400 });
  }

  const companyId = session.auth.company_id as number;

  try {
    const users = await getCompanyUsers(companyId);
    if (!userBelongsToCompany(users, userId)) {
      return NextResponse.json({ success: false, error: "User topilmadi." }, { status: 404 });
    }

    const payload = await callInternalRpc<CompanyAdminResetTokenPayload | null>(
      "create_password_reset_token",
      [userId],
    );

    if (!payload?.token) {
      return NextResponse.json(
        { success: false, error: "Reset token yaratib bo'lmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true, payload });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Reset token yaratishda xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
