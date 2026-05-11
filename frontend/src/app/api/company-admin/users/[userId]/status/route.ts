import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import {
  getCompanyUsers,
  isProtectedCompanyAdminUser,
  parseUserId,
  requireCompanyAdminSession,
  userBelongsToCompany,
} from "../../../_helpers";

export async function PATCH(
  request: Request,
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

  const payload = (await request.json().catch(() => null)) as { is_active?: boolean } | null;
  if (typeof payload?.is_active !== "boolean") {
    return NextResponse.json(
      { success: false, error: "is_active boolean bo'lishi kerak." },
      { status: 400 },
    );
  }

  const companyId = session.auth.company_id as number;

  try {
    const users = await getCompanyUsers(companyId);
    if (!userBelongsToCompany(users, userId)) {
      return NextResponse.json({ success: false, error: "User topilmadi." }, { status: 404 });
    }

    if (isProtectedCompanyAdminUser(users, userId)) {
      return NextResponse.json(
        { success: false, error: "Company admin statusi bu route orqali o'zgarmaydi." },
        { status: 400 },
      );
    }

    const success = await callInternalRpc<boolean>("update_user_status_for_company", [
      userId,
      companyId,
      payload.is_active,
    ]);

    if (!success) {
      return NextResponse.json(
        { success: false, error: "User statusini yangilab bo'lmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "User statusida xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
