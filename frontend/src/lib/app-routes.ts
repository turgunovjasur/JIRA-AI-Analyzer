import type { UserRole } from "@/lib/types";

export function getDefaultRouteForRole(role?: UserRole | null) {
  return role === "super_admin" ? "/admin" : "/dashboard";
}
