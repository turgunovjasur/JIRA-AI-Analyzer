import { redirect } from "next/navigation";

import { LandingAd } from "@/components/landing/landing-ad";
import { getDefaultRouteForRole } from "@/lib/app-routes";
import { getOptionalSession } from "@/lib/session";

export default async function HomePage() {
  const session = await getOptionalSession();
  if (session?.auth?.logged_in) {
    redirect(getDefaultRouteForRole(session.auth.role));
  }

  return <LandingAd />;
}
