"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  LayoutDashboard,
  Moon,
  Shield,
  Sun,
  TestTube2,
  Waypoints,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";

type NavItem = {
  href: string;
  icon: ReactNode;
  label: string;
  description: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/demo/dashboard", icon: <LayoutDashboard size={15} />, label: "Dashboard", description: "Loyiha va aloqa" },
  { href: "/demo/tzpr", icon: <Waypoints size={15} />, label: "TZ-PR Checker", description: "Spec va PR moslik tahlili" },
  { href: "/demo/testcase", icon: <TestTube2 size={15} />, label: "Test Case Generator", description: "QA draft yaratish" },
  { href: "/demo/monitoring", icon: <Activity size={15} />, label: "Monitoring", description: "Queue va xizmat holati" },
];

const PAGE_META: Record<string, { kicker: string; title: string }> = {
  "/demo/dashboard": { kicker: "Workspace", title: "Dashboard" },
  "/demo/tzpr": { kicker: "Quality", title: "TZ-PR Checker" },
  "/demo/testcase": { kicker: "Quality", title: "Test Case Generator" },
  "/demo/monitoring": { kicker: "Operations", title: "Monitoring" },
};

const THEME_STORAGE_KEY = "qa_theme_mode";

type ThemeMode = "light" | "dark";

export function DemoShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const pageMeta = PAGE_META[pathname] ?? { kicker: "Demo", title: "QA-Assistant" };
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [themeReady, setThemeReady] = useState(false);

  function applyTheme(mode: ThemeMode) {
    document.documentElement.classList.toggle("dark", mode === "dark");
  }

  useEffect(() => {
    let next: ThemeMode = "light";
    try {
      const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (saved === "light" || saved === "dark") {
        next = saved;
      } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        next = "dark";
      }
    } catch {
      // default tema
    }
    applyTheme(next);
    setTheme(next);
    setThemeReady(true);
  }, []);

  function toggleTheme() {
    const next: ThemeMode = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // localStorage yo'q bo'lsa ham session davomida ishlaydi
    }
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
              <div className="qa-sidebar-title">Demo Workspace</div>
            </div>
          </div>
        </div>

        <nav className="qa-sidebar-nav">
          <div className="qa-nav-section">
            <span className="qa-nav-section-label">Workspace</span>
            <div className="qa-nav-list">
              {NAV_ITEMS.map((item) => {
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
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
            <p className="qa-sidebar-user-name">Demo kompaniya</p>
            <p className="qa-sidebar-user-sub">Mehmon rejimi</p>
            <div className="qa-sidebar-user-badges">
              <Badge tone="warning">DEMO</Badge>
              <Badge tone="soft">namuna</Badge>
            </div>
          </div>
          <Link href="/demo/dashboard#contact" className="qa-demo-cta">
            Bog&apos;lanish
            <ArrowRight size={14} />
          </Link>
          <Link href="/" className="qa-demo-back">
            ← Reklama sahifasi
          </Link>
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
            <Badge tone="warning">Demo · mock ma&apos;lumot</Badge>
          </div>
        </header>

        <div className="qa-demo-banner" role="note">
          <span>
            Bu <strong>demo</strong> — barcha natijalar oldindan tayyorlangan namuna ma&apos;lumot. Real
            tizim aynan shunday ishlaydi.
          </span>
          <Link href="/demo/dashboard#contact" className="qa-demo-banner-link">
            Bog&apos;lanish →
          </Link>
        </div>

        <div className="qa-page-body">{children}</div>
      </main>
    </div>
  );
}
