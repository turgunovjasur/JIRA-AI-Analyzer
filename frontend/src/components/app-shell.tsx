"use client";

import { startTransition, useEffect, useState } from "react";
import {
  Activity,
  LayoutDashboard,
  LogOut,
  Moon,
  Settings,
  Shield,
  Sun,
  TestTube2,
  Users,
  Waypoints,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { SessionResponse } from "@/lib/types";

type NavSection = "Workspace" | "Administration";

type NavItem = {
  href: string;
  icon: ReactNode;
  label: string;
  description: string;
  section: NavSection;
};

function getNavItems(session: SessionResponse) {
  const role = session.auth.role;
  const items: NavItem[] = [];

  if (role !== "super_admin") {
    items.push({
      href: "/dashboard",
      icon: <LayoutDashboard size={15} />,
      label: "Dashboard",
      description: "Asosiy ish maydoni",
      section: "Workspace",
    });
  }

  if (role !== "super_admin") {
    items.push({
      href: "/settings",
      icon: <Settings size={15} />,
      label: "Settings",
      description: "Integrations va AI",
      section: "Workspace",
    });
  }

  if (role === "super_admin") {
    items.splice(1, 0, {
      href: "/admin",
      icon: <Shield size={15} />,
      label: "Admin",
      description: "Tenantlar va platform",
      section: "Administration",
    });
  }

  if (role !== "super_admin" && session.companyModules?.tz_pr_checker) {
    items.push({
      href: "/tzpr",
      icon: <Waypoints size={15} />,
      label: "TZ-PR Checker",
      description: "Spec va PR moslik tahlili",
      section: "Workspace",
    });
  }

  if (role !== "super_admin" && session.companyModules?.testcase_generator) {
    items.push({
      href: "/testcase",
      icon: <TestTube2 size={15} />,
      label: "Test Case Generator",
      description: "QA draft yaratish",
      section: "Workspace",
    });
  }

  if (role === "company_admin" && session.companyModules?.monitoring) {
    items.push({
      href: "/monitoring",
      icon: <Activity size={15} />,
      label: "Monitoring",
      description: "Queue va xizmat holati",
      section: "Administration",
    });
  }

  if (role === "company_admin") {
    items.push({
      href: "/team",
      icon: <Users size={15} />,
      label: "Team",
      description: "Foydalanuvchilar",
      section: "Administration",
    });
  }

  return items;
}

function getPageMeta(pathname: string) {
  const map: Record<string, { kicker: string; title: string }> = {
    "/admin": { kicker: "Platform", title: "Admin" },
    "/dashboard": { kicker: "Workspace", title: "Dashboard" },
    "/settings": { kicker: "Configuration", title: "Settings" },
    "/monitoring": { kicker: "Operations", title: "Monitoring" },
    "/tzpr": { kicker: "Quality", title: "TZ-PR Checker" },
    "/testcase": { kicker: "Quality", title: "Test Case Generator" },
    "/team": { kicker: "Administration", title: "Team" },
  };
  return map[pathname] ?? { kicker: "Workspace", title: pathname.slice(1) || "Dashboard" };
}

type AppShellProps = {
  children: ReactNode;
  session: SessionResponse;
};

const THEME_STORAGE_KEY = "qa_theme_mode";

type ThemeMode = "light" | "dark";

export function AppShell({ children, session }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const navItems = getNavItems(session);
  const pageMeta = getPageMeta(pathname);
  const sessionCode = session.auth.company_code || "global";
  const navSections: NavSection[] = ["Workspace", "Administration"];
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [themeReady, setThemeReady] = useState(false);

  function applyTheme(mode: ThemeMode) {
    document.documentElement.classList.toggle("dark", mode === "dark");
  }

  useEffect(() => {
    let nextTheme: ThemeMode = "light";
    try {
      const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "light" || saved === "dark") {
        nextTheme = saved;
      } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        nextTheme = "dark";
      }
    } catch {
      // localStorage cheklangan brauzer rejimlarida default tema ishlatiladi.
    }
    applyTheme(nextTheme);
    setTheme(nextTheme);
    setThemeReady(true);
  }, []);

  function toggleTheme() {
    const nextTheme: ThemeMode = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    applyTheme(nextTheme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch {
      // localStorage yozib bo'lmasa ham tema session davomida ishlaydi.
    }
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  return (
    <div className="qa-shell">
      <aside className="qa-sidebar">
        <div className="qa-sidebar-brand">
          <div className="qa-sidebar-logo">
            <div className="qa-sidebar-logo-icon">
              <Shield size={16} color="white" />
            </div>
            <div>
              <span className="qa-sidebar-eyebrow">QA ASSISTANT</span>
              <div className="qa-sidebar-title">Workspace Portal</div>
            </div>
          </div>
        </div>

        <nav className="qa-sidebar-nav">
          {navSections.map((section) => {
            const items = navItems.filter((item) => item.section === section);
            if (!items.length) return null;
            return (
              <div key={section} className="qa-nav-section">
                <span className="qa-nav-section-label">{section}</span>
                <div className="qa-nav-list">
                  {items.map((item) => {
                    const active = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn("qa-nav-item", active && "qa-nav-item--active")}
                      >
                        <span className={cn("qa-nav-item-icon", active && "qa-nav-item-icon--active")}>
                          {item.icon}
                        </span>
                        <span className="qa-nav-item-text">
                          <span className="qa-nav-item-label">{item.label}</span>
                          <span className="qa-nav-item-desc">{item.description}</span>
                        </span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        <div className="qa-sidebar-footer">
          <div className="sb-theme-row">
            <span className="sb-theme-label">Tema</span>
            <button className="theme-toggle" onClick={toggleTheme} type="button">
              {theme === "dark" ? <Moon size={14} /> : <Sun size={14} />}
              {themeReady ? (theme === "dark" ? "Dark" : "Light") : "Light"}
            </button>
          </div>
          <div className="qa-sidebar-user">
            <p className="qa-sidebar-user-name">
              {session.auth.company_name || "Platform"}
            </p>
            <p className="qa-sidebar-user-sub">{session.auth.user_name || "User"}</p>
            <div className="qa-sidebar-user-badges">
              <Badge>{session.auth.role || "role"}</Badge>
              <Badge tone="soft">{sessionCode}</Badge>
            </div>
          </div>
          <Button className="w-full" onClick={logout} variant="ghost">
            <LogOut size={14} />
            Chiqish
          </Button>
        </div>
      </aside>

      <main className="qa-main">
        <header className="qa-topbar">
          <div className="qa-topbar-left">
            <span className="qa-topbar-kicker">{pageMeta.kicker}</span>
            <span className="qa-topbar-sep">/</span>
            <h1 className="qa-topbar-title">{pageMeta.title}</h1>
          </div>
          <div className="qa-topbar-right">
            <Badge tone="soft">v2.5</Badge>
          </div>
        </header>

        <div className="qa-page-body">{children}</div>
      </main>
    </div>
  );
}
