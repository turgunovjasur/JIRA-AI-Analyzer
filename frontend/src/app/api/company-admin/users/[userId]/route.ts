import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import {
  getCompanyUsers,
  isProtectedCompanyAdminUser,
  parseUserId,
  requireCompanyAdminSession,
  userBelongsToCompany,
} from "../../_helpers";

export async function DELETE(
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

    if (isProtectedCompanyAdminUser(users, userId)) {
      return NextResponse.json(
        { success: false, error: "Company admin user o'chirilmaydi." },
        { status: 400 },
      );
    }

    const success = await callInternalRpc<boolean>("delete_user_for_company", [userId, companyId]);
    if (!success) {
      return NextResponse.json(
        { success: false, error: "Userni o'chirishga ruxsat yo'q yoki user topilmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "User o'chirishda xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
