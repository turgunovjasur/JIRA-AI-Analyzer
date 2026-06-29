import { Activity, ShieldCheck, Workflow } from "lucide-react";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/login-form";
import { getDefaultRouteForRole } from "@/lib/app-routes";
import { getOptionalSession } from "@/lib/session";

export default async function LoginPage() {
  const session = await getOptionalSession();
  if (session?.auth?.logged_in) {
    redirect(getDefaultRouteForRole(session.auth.role));
  }

  return (
    <main className="qa-login-layout">
      {/* ── Hero panel ── */}
      <section className="qa-login-hero">
        <div className="qa-login-hero-content">
          <div className="qa-login-hero-badge">
            <ShieldCheck size={11} />
            Production Portal v2.5
          </div>

          <h1 className="qa-login-hero-title">
            QA jamoasi uchun aqlli ish muhiti
          </h1>
          <p className="qa-login-hero-desc">
            JIRA tasklarini AI bilan tahlil qiling, test case&apos;lar yarating
            va PR mosligini tekshiring — barchasi bitta platformada.
          </p>

          <div className="qa-login-features">
            {[
              {
                icon: <Workflow size={16} />,
                title: "TZ-PR Checker",
                desc: "Spetsifikatsiya va pull request mosligini avtomatik tekshirish",
              },
              {
                icon: <ShieldCheck size={16} />,
                title: "Test Case Generator",
                desc: "AI yordamida QA test scenariylarini yaratish",
              },
              {
                icon: <Activity size={16} />,
                title: "Monitoring",
                desc: "Queue holati va xizmat ishlashini real-time kuzatish",
              },
              {
                icon: <Workflow size={16} />,
                title: "Team Management",
                desc: "Jamoa a'zolari va ruxsatlarni boshqarish",
              },
            ].map((f) => (
              <div key={f.title} className="qa-login-feature">
                <div className="qa-login-feature-icon">{f.icon}</div>
                <div>
                  <div className="qa-login-feature-title">{f.title}</div>
                  <div className="qa-login-feature-desc">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="qa-login-hero-footer">© 2026 QA-Assistant Platform</p>
      </section>

      {/* ── Login form panel ── */}
      <div className="qa-login-form-panel">
        <LoginForm />
      </div>
    </main>
  );
}
