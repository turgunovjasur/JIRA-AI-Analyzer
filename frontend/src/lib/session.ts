import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getBackendSession } from "@/lib/backend";
import type { SessionResponse } from "@/lib/types";

const SESSION_COOKIE = "qa_backend_session";

export async function getOptionalSession(): Promise<SessionResponse | null> {
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get(SESSION_COOKIE)?.value;
  if (!sessionToken) {
    return null;
  }
  try {
    return await getBackendSession(sessionToken);
  } catch {
    return null;
  }
}

export async function requireSession() {
  const session = await getOptionalSession();
  if (!session?.success || !session.auth?.logged_in) {
    redirect("/login");
  }
  return session;
}

export async function writeSessionToken(sessionToken: string) {
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE, sessionToken, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
}

export async function readSessionToken() {
  const cookieStore = await cookies();
  return cookieStore.get(SESSION_COOKIE)?.value || null;
}

export async function clearSession() {
  const cookieStore = await cookies();
  cookieStore.delete(SESSION_COOKIE);
}
