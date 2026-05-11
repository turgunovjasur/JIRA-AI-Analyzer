import { NextResponse } from "next/server";

import { callInternalRpc } from "@/lib/backend";
import type { CompanyAdminUser } from "@/lib/types";

import { requireCompanyAdminSession } from "../_helpers";

export async function POST(request: Request) {
  const { error, session } = await requireCompanyAdminSession();
  if (error || !session) {
    return error;
  }

  const companyId = session.auth.company_id as number;

  try {
    const payload = (await request.json()) as {
      password?: string;
      username?: string;
    };

    const username = (payload.username || "").trim().toLowerCase();
    const password = payload.password || "";

    if (!username) {
      return NextResponse.json(
        { success: false, error: "Username majburiy." },
        { status: 400 },
      );
    }

    if (password.length < 6) {
      return NextResponse.json(
        { success: false, error: "Parol kamida 6 ta belgi bo'lishi kerak." },
        { status: 400 },
      );
    }

    const result = await callInternalRpc<[CompanyAdminUser | null, string | null]>(
      "create_user",
      [companyId, username, password, "user"],
    );

    const createdUser = Array.isArray(result) ? result[0] : null;
    const createError = Array.isArray(result) ? result[1] : "User yaratilmadi.";

    if (!createdUser) {
      return NextResponse.json(
        { success: false, error: createError || "User yaratilmadi." },
        { status: 400 },
      );
    }

    return NextResponse.json({ success: true, user: createdUser });
  } catch (routeError) {
    const message =
      routeError instanceof Error ? routeError.message : "User yaratishda xato yuz berdi.";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
