import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";

import {
  getCompanyUsers,
  parseUserId,
  requireCompanyAdminSession,
  userBelongsToCompany,
} from "../../../_helpers";

export async function POST(
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

  const payload = (await request.json().catch(() => null)) as { new_password?: string } | null;
  const newPassword = payload?.new_password || "";
  if (newPassword.length < 6) {
    return NextResponse.json(
      { success: false, error: "Parol kamida 6 ta belgi bo'lishi kerak." },
      { status: 400 },
    );
  }

  const companyId = session.auth.company_id as number;

  try {
    const users = await getCompanyUsers(companyId);
    if (!userBelongsToCompany(users, userId)) {
      return NextResponse.json({ success: false, error: "User topilmadi." }, { status: 404 });
    }

    const success = await callInternalRpc<boolean>("update_user_password_for_company", [
      userId,
      companyId,
      newPassword,
    ]);

    if (!success) {
      return NextResponse.json(
        { success: false, error: "Parolni yangilab bo'lmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "Parolni yangilashda xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
