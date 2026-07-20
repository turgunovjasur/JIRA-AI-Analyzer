"use client";

import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  Check,
  ChevronDown,
  ClipboardList,
  Moon,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  Sun,
  Waypoints,
  Webhook,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { ContactSection } from "@/components/contact-section";
import { Badge } from "@/components/ui/badge";
import { BaseCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ComplianceRing } from "@/components/ui/compliance-ring";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusPill } from "@/components/ui/status-pill";
import { cn } from "@/lib/cn";
import {
  DEMO_CHECKER_RESULT,
  DEMO_MONITORING,
  DEMO_TESTCASE_RESULT,
  type DemoRequirementStatus,
} from "@/lib/demo-data";

/* ─────────────── hooks: bir martalik in-view + count-up ─────────────── */

function useInViewOnce(threshold = 0.25) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            setInView(true);
            io.disconnect();
          }
        });
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return [ref, inView] as const;
}

function prefersReduced() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function useCountUp(target: number, active: boolean, ms = 900, decimals = 0) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!active) return;
    if (prefersReduced()) {
      setVal(target);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(Number((target * eased).toFixed(decimals)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, target, ms, decimals]);
  return val;
}

/* ─────────────── reusable wrappers ─────────────── */

function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const [ref, inView] = useInViewOnce();
  return (
    <div ref={ref} className={cn("reveal", inView && "in", className)} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function Page({ id, className, children }: { id?: string; className?: string; children: ReactNode }) {
  return (
    <section id={id} className={cn("flex min-h-[calc(100vh-4rem)] scroll-mt-16 items-center py-20", className)}>
      <div className="mx-auto w-full max-w-6xl px-5">{children}</div>
    </section>
  );
}

/* ─────────────── main ─────────────── */

export function LandingAd() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    let next = false;
    try {
      const saved = window.localStorage.getItem("qa_theme_mode");
      next = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    } catch {
      next = false;
    }
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
  }, []);

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
    try {
      window.localStorage.setItem("qa_theme_mode", next ? "dark" : "light");
    } catch {
      // ignore
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-[9px] bg-primary text-white">
              <ShieldCheck size={16} />
            </span>
            <div className="leading-tight">
              <span className="block text-sm font-bold tracking-tight text-foreground">QA-Assistant</span>
              <span className="block font-mono text-[10px] text-muted-foreground">qa-assistant.uz</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={toggleTheme}
              className="flex h-9 w-9 items-center justify-center rounded-[10px] border border-border text-muted-foreground hover:text-primary"
              aria-label="Tema"
            >
              {dark ? <Moon size={15} /> : <Sun size={15} />}
            </button>
            <Button asChild variant="ghost" size="sm">
              <Link href="#contact">Bog&apos;lanish</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/demo">
                Demo&apos;ni ochish <ArrowRight size={14} />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main>
        {/* ── HERO ── */}
        <Page>
          <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
            <Reveal>
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                <Sparkles size={14} /> AI multi-agent · zamonaviy QA
              </span>
              <h1 className="mt-4 text-4xl font-bold leading-[1.05] tracking-tight text-foreground md:text-5xl">
                <span className="block">QA-Assistant</span>
                <span className="mt-2 block text-primary">sizning zamonaviy AI yordamchi agentingiz</span>
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">
                TZ va PR mosligini AI tekshiradi, test case&apos;larni yozadi va JIRA&apos;da avtonom ishlaydi —
                uchta modul, bitta multi-agent jamoa.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Button asChild size="md">
                  <Link href="/demo">
                    Demo&apos;ni ochish <ArrowRight size={16} />
                  </Link>
                </Button>
              </div>
            </Reveal>

            <Reveal delay={140} className="grid gap-3">
              {[
                { icon: <Waypoints size={16} />, title: "TZ-PR Checker", note: "3 agentli moslik tahlili", href: "#checker" },
                { icon: <ClipboardList size={16} />, title: "Test Case Generator", note: "3 agentli test case", href: "#testcase" },
                { icon: <Activity size={16} />, title: "Monitoring", note: "Real vaqt statistika", href: "#monitoring" },
                { icon: <Webhook size={16} />, title: "JIRA Webhook", note: "Avtonom ishlash + auto-return", href: "#webhook" },
              ].map((x) => (
                <Link
                  key={x.href}
                  href={x.href}
                  className="flex items-center gap-3 rounded-[13px] border border-border bg-card p-4 transition-transform hover:-translate-y-0.5 hover:border-primary/30"
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-[11px] bg-primary/10 text-primary">
                    {x.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold text-foreground">{x.title}</span>
                    <span className="block text-xs text-muted-foreground">{x.note}</span>
                  </span>
                  <ArrowRight size={15} className="text-muted-foreground" />
                </Link>
              ))}
            </Reveal>
          </div>
          <Reveal delay={280} className="mt-14 flex justify-center">
            <span className="flex flex-col items-center gap-1 text-xs text-muted-foreground">
              Pastga suring
              <ChevronDown size={16} className="animate-bounce" />
            </span>
          </Reveal>
        </Page>

        {/* ── CHECKER ── */}
        <ModulePage
          id="checker"
          icon={<Waypoints size={14} />}
          eyebrow="Modul 1 · UI"
          title="TZ-PR Checker"
          agents="scope → verify → arbiter"
          text="TZ talablarini GitHub PR kodi bilan solishtiradi, moslik balini (0–100%) qo'yadi, bajarilgan/bajarilmagan talablarni va potensial muammolarni ko'rsatadi."
          href="/demo/tzpr"
        >
          <CheckerShowcase />
        </ModulePage>

        {/* ── TESTCASE ── */}
        <ModulePage
          id="testcase"
          icon={<ClipboardList size={14} />}
          eyebrow="Modul 2 · UI"
          title="Test Case Generator"
          agents="talablar → yozish → audit"
          text="Talablar asosida positive/negative test case'lar yozadi — qadamlar, kutilgan natija, prioritet va talab qamrovi bilan."
          href="/demo/testcase"
          reverse
        >
          <TestcaseShowcase />
        </ModulePage>

        {/* ── MONITORING ── */}
        <ModulePage
          id="monitoring"
          icon={<Activity size={14} />}
          eyebrow="Modul 3 · UI"
          title="Monitoring"
          agents="real-time"
          text="Barcha tasklar, servis holati, o'rtacha moslik va queue bir joyda. Xatolar va bloklangan navbatni kuzatasiz."
          href="/demo/monitoring"
        >
          <MonitoringShowcase />
        </ModulePage>

        {/* ── WEBHOOK ── */}
        <Page id="webhook" className="py-12">
          <Reveal className="max-w-2xl">
            <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              <Webhook size={14} /> JIRA Webhook — avtonom
            </span>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
              Jirada o&apos;zi ishlaydi — siz hech narsa qilmaysiz
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              <strong className="text-foreground">Webhook</strong> — JIRA&apos;da biror narsa o&apos;zgarganda tizimga
              yuboriladigan avtomatik signal. Task &quot;Testing&quot;ga o&apos;tishi bilan QA-Assistant tahlil qiladi va
              natijani task ostiga izoh qilib yozadi.
            </p>
          </Reveal>
          <WebhookShowcase />
        </Page>

        {/* ── AUTO-RETURN ── */}
        <Page id="autoreturn">
          <AutoReturnCallout />
        </Page>

        {/* ── CONTACT ── */}
        <Page id="contact">
          <Reveal className="max-w-2xl">
            <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              <Send size={14} /> Bog&apos;lanish
            </span>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
              Tizimni bepul sinab ko&apos;rmoqchimisiz?
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Ma&apos;lumotingizni qoldiring — biz sizga alohida kompaniya (akkaunt) ochib beramiz va tizimni o&apos;z
              JIRA&apos;ngizda, real natijalar bilan sinab ko&apos;rasiz. Yoki bevosita Telegram, email, telefon orqali
              yozing.
            </p>
          </Reveal>
          <Reveal delay={120} className="mt-8">
            <ContactSection />
          </Reveal>
        </Page>

        {/* ── CTA ── */}
        <Page className="text-center">
          <Reveal>
            <h2 className="mx-auto max-w-2xl text-3xl font-bold tracking-tight text-foreground md:text-4xl">
              O&apos;z ko&apos;zingiz bilan ko&apos;ring
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-muted-foreground">
              Demo — real tizimning aynan o&apos;zi, namuna ma&apos;lumot bilan. Ro&apos;yxatdan o&apos;tmasdan barcha
              modullarni bosib ko&apos;ring.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button asChild size="md">
                <Link href="/demo">
                  Demo&apos;ni ochish <ArrowRight size={16} />
                </Link>
              </Button>
              <Button asChild variant="ghost" size="md">
                <Link href="#contact">
                  <Send size={15} /> Bog&apos;lanish
                </Link>
              </Button>
            </div>
          </Reveal>
        </Page>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-6 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <ShieldCheck size={15} className="text-primary" /> QA-Assistant
          </span>
          <span className="font-mono text-xs">qa-assistant.uz · JIRA + Gemini AI</span>
        </div>
      </footer>
    </div>
  );
}

/* ─────────────── module page wrapper ─────────────── */

function ModulePage({
  id,
  icon,
  eyebrow,
  title,
  agents,
  text,
  href,
  reverse,
  children,
}: {
  id: string;
  icon: ReactNode;
  eyebrow: string;
  title: string;
  agents: string;
  text: string;
  href: string;
  reverse?: boolean;
  children: ReactNode;
}) {
  return (
    <Page id={id}>
      <div className="grid items-center gap-8 lg:grid-cols-2">
        <Reveal className={cn(reverse && "lg:order-2")}>
          <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            {icon} {eyebrow}
          </span>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-foreground">{title}</h2>
          <p className="mt-1.5 font-mono text-xs text-primary">{agents}</p>
          <p className="mt-4 max-w-lg text-sm leading-7 text-muted-foreground">{text}</p>
          <Button asChild variant="ghost" size="sm" className="mt-6">
            <Link href={href}>
              Demo&apos;da ochish <ArrowRight size={14} />
            </Link>
          </Button>
        </Reveal>
        <div className={cn(reverse && "lg:order-1")}>{children}</div>
      </div>
    </Page>
  );
}

/* ─────────────── showcases (real UI, bir martalik animatsiya) ─────────────── */

const REQ_PILL: Record<DemoRequirementStatus, { tone: "good" | "bad" | "warn"; label: string }> = {
  completed: { tone: "good", label: "Bajarilgan" },
  failed: { tone: "bad", label: "Topilmadi" },
  skipped: { tone: "warn", label: "Skip" },
};

function ShowcaseFrame({
  label,
  frameRef,
  className,
  children,
}: {
  label: string;
  frameRef?: React.Ref<HTMLDivElement>;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      ref={frameRef}
      className={cn(
        "rounded-[16px] border border-border bg-card shadow-[0_16px_38px_rgba(9,20,30,0.08)]",
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <span className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#f0736a]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#e0a63a]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#2ecc9b]" />
        </span>
        <span className="ml-1 font-mono text-[11px] text-muted-foreground">{label}</span>
      </div>
      <div className="p-4 md:p-5">{children}</div>
    </div>
  );
}

function CheckerShowcase() {
  const r = DEMO_CHECKER_RESULT;
  const [ref, inView] = useInViewOnce(0.3);
  const score = useCountUp(r.complianceScore, inView);
  return (
    <ShowcaseFrame frameRef={ref} label="TZ-PR Checker · natija" className={cn("reveal", inView && "in")}>
      <div className="flex flex-col items-center gap-4 sm:flex-row">
        <ComplianceRing score={score} size={92} />
        <div>
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="success">{r.verdict}</Badge>
            <Badge tone="success">{r.completed} bajarildi</Badge>
            <Badge tone="danger">{r.failed} bajarilmadi</Badge>
          </div>
          <p className="mt-2 text-sm font-semibold text-foreground">{r.taskSummary}</p>
          <p className="mt-0.5 font-mono text-xs text-muted-foreground">
            {r.filesChanged} fayl · PR {r.prLabel} · Figma {r.figma ? "bor" : "yo'q"}
          </p>
        </div>
      </div>
      <div className="mt-4 grid gap-2">
        {r.requirements.slice(0, 4).map((req) => {
          const pill = REQ_PILL[req.status];
          const dot =
            req.status === "completed" ? "var(--success)" : req.status === "failed" ? "var(--error)" : "var(--warning)";
          return (
            <div
              key={req.id}
              className="flex items-center gap-2.5 rounded-[10px] border border-border bg-[color:var(--bg-layer)] px-3 py-2"
            >
              <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: dot }} />
              <span className="flex-1 truncate text-xs text-foreground">{req.requirement}</span>
              <StatusPill tone={pill.tone} value={pill.label} />
            </div>
          );
        })}
      </div>
    </ShowcaseFrame>
  );
}

function TestcaseShowcase() {
  const r = DEMO_TESTCASE_RESULT;
  const cards = r.testCases.slice(0, 2);
  const [ref, inView] = useInViewOnce(0.3);
  return (
    <ShowcaseFrame frameRef={ref} label="Test Case Generator · natija" className={cn("reveal", inView && "in")}>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-[7px] bg-[color:var(--bg-layer)] px-2.5 py-1 font-mono text-[11px] text-muted-foreground">
          Jami: <b className="text-foreground">{r.totalTestCases}</b>
        </span>
        <span className="rounded-[7px] bg-[color:var(--bg-layer)] px-2.5 py-1 font-mono text-[11px] text-muted-foreground">
          Qamrov: <b className="text-foreground">{r.covered}/{r.totalRequirements}</b>
        </span>
        <span className="rounded-[7px] bg-[color:var(--bg-layer)] px-2.5 py-1 font-mono text-[11px] text-muted-foreground">
          High: <b className="text-foreground">{r.highPriority}</b>
        </span>
      </div>
      <div className="mt-3 grid gap-2.5">
        {cards.map((tc, i) => {
          const priorityTone = tc.priority === "High" ? "danger" : tc.priority === "Medium" ? "warning" : "soft";
          return (
            <BaseCard as="details" key={tc.id} className="qa-tc-card" padding="none" {...(i === 0 ? { open: true } : {})}>
              <summary>
                <span className="qa-tc-id">{tc.id}</span>
                <span className="flex-1 text-sm font-semibold text-foreground">{tc.title}</span>
                <Badge tone={priorityTone}>{tc.priority}</Badge>
                <Badge tone="soft">{tc.type}</Badge>
              </summary>
              <div className="qa-tc-body">
                <div>
                  <p className="qa-tc-section-label">Qadamlar</p>
                  <ol className="qa-tc-steps">
                    {tc.steps.map((s, k) => (
                      <li key={k}>{s}</li>
                    ))}
                  </ol>
                </div>
                <div>
                  <p className="qa-tc-section-label">Kutilgan natija</p>
                  <div className="qa-tc-expected">{tc.expected}</div>
                </div>
              </div>
            </BaseCard>
          );
        })}
      </div>
    </ShowcaseFrame>
  );
}

const MON_TONE: Record<string, "good" | "bad" | "warn" | "info" | "muted"> = {
  completed: "good",
  done: "good",
  error: "bad",
  returned: "warn",
  blocked: "info",
  progressing: "warn",
  pending: "warn",
};

function MonitoringShowcase() {
  const m = DEMO_MONITORING;
  const rows = m.recentTasks.slice(0, 4);
  const [ref, inView] = useInViewOnce(0.3);
  const total = useCountUp(m.metrics.total, inView);
  const done = useCountUp(m.metrics.completed, inView);
  const avg = useCountUp(m.metrics.avgCompliance, inView, 900, 1);
  return (
    <ShowcaseFrame frameRef={ref} label="Monitoring · real vaqt" className={cn("reveal", inView && "in")}>
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Total" value={total} />
        <MetricCard label="Bajarildi" value={done} />
        <MetricCard label="Avg Moslik" value={`${avg.toFixed(1)}%`} />
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[420px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
              <th className="px-2 py-2 font-semibold">Task</th>
              <th className="px-2 py-2 font-semibold">Status</th>
              <th className="px-2 py-2 font-semibold">Moslik</th>
              <th className="px-2 py-2 font-semibold">Vaqt</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id} className="border-b border-border/60">
                <td className="px-2 py-2 font-mono text-xs text-foreground">{t.id}</td>
                <td className="px-2 py-2">
                  <StatusPill tone={MON_TONE[t.status] ?? "muted"} value={t.status} />
                </td>
                <td className="px-2 py-2">
                  {t.score === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <Badge tone={t.score >= 80 ? "success" : t.score >= 60 ? "warning" : "danger"}>{t.score}%</Badge>
                  )}
                </td>
                <td className="px-2 py-2 text-xs text-muted-foreground">{t.updated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ShowcaseFrame>
  );
}

/* ─────────────── webhook: jira issue view (bir marta ijro) ─────────────── */

const JIRA_STEPS = [
  { label: "Status o'zgardi", desc: "Task \"Testing\"ga o'tdi" },
  { label: "Webhook signal", desc: "Tizimga signal keldi" },
  { label: "AI ishga tushdi", desc: "3 agent tahlil qildi" },
  { label: "Izoh yozildi", desc: "Natija task ostiga yozildi" },
];

function WebhookShowcase() {
  const [ref, inView] = useInViewOnce(0.3);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (prefersReduced()) {
      setStep(4);
      return;
    }
    const timers: number[] = [];
    timers.push(window.setTimeout(() => setStep(1), 500));
    timers.push(window.setTimeout(() => setStep(2), 1700));
    timers.push(window.setTimeout(() => setStep(3), 3100));
    timers.push(window.setTimeout(() => setStep(4), 4300));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [inView]);

  const reached = step === 0 ? 0 : step === 1 ? 2 : step === 2 ? 3 : 4;
  const statusCls = step === 0 ? "lz-prog" : step >= 4 ? "lz-done" : "lz-test";
  const statusText = step === 0 ? "In Progress" : step >= 4 ? "Ready to Test" : "Testing";
  const revealed = (show: boolean) => ({ opacity: show ? 1 : 0, transform: show ? "none" : "translateY(7px)" });

  return (
    <div ref={ref} className={cn("lj-scope reveal mt-6", inView && "in")}>
      {/* qadam strip */}
      <ol className="mb-4 grid gap-3 sm:grid-cols-4">
        {JIRA_STEPS.map((s, idx) => {
          const i = idx + 1;
          const state = i < reached ? "done" : i === reached ? "active" : "pending";
          return (
            <li
              key={s.label}
              className={cn(
                "flex items-center gap-2.5 rounded-[12px] border px-3 py-2.5 transition-colors",
                state === "active" ? "border-primary/40 bg-primary/5" : "border-border bg-card",
                state === "pending" && "opacity-60",
              )}
            >
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold transition-colors",
                  state === "active" && "bg-primary text-white",
                  state === "done" && "bg-[color:var(--success)] text-white",
                  state === "pending" && "bg-[color:var(--bg-strong)] text-muted-foreground",
                )}
              >
                {state === "done" ? <Check size={12} /> : i}
              </span>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-foreground">{s.label}</p>
                <p className="truncate text-[11px] text-muted-foreground">{s.desc}</p>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="lj-win">
        <div className="lj-chrome">
          <span className="lj-dots">
            <i style={{ background: "#ff5f57" }} />
            <i style={{ background: "#febc2e" }} />
            <i style={{ background: "#28c840" }} />
          </span>
          <span className="lj-url">kompaniyangiz.atlassian.net/browse/DEV-1284</span>
        </div>

        <div className="lj-app">
          <div className="lj-main">
            <div className="lj-crumb">Loyihalar / QA / DEV-1284</div>
            <h3 className="lj-summary">Parolni tiklash: SMS orqali kod yuborish</h3>

            <div className="lj-status-row">
              <button type="button" className={cn("lj-status", statusCls)}>
                {statusText}
                <ChevronDown size={12} />
              </button>
              <span className="lj-signal" style={revealed(step === 1 || step === 2)}>
                <Webhook size={11} style={{ color: "var(--lj-blue)" }} /> webhook signal keldi
              </span>
            </div>

            <div className="lj-activity-head">
              <span className="t">Faoliyat</span>
              <span className="lj-tab on">Izohlar</span>
              <span className="lj-tab">Tarix</span>
            </div>

            <div className="lj-feed">
              {step >= 1 ? (
                <div className="lj-sys lj-appear">
                  <span className="lj-av">✦</span>
                  <span>
                    <b>QA-Assistant</b> statusni o&apos;zgartirdi: <span className="from">In Progress</span> →{" "}
                    <span className="to lz-test">Testing</span>
                  </span>
                </div>
              ) : null}

              {step === 2 ? (
                <div className="lj-sys lj-appear">
                  <span className="lj-spin" />
                  <span>AI multi-agent tahlil qilmoqda… (scope → verify → arbiter)</span>
                </div>
              ) : null}

              {step >= 3 ? (
                <div className="lj-cm lj-appear">
                  <span className="lj-av">✦</span>
                  <div className="body">
                    <div className="by">
                      <b>QA-Assistant</b> <span className="time">hozir</span>
                      <span className="lj-marker">[AI_S1]</span>
                    </div>
                    <div className="lj-box">
                      <p className="text-sm font-semibold" style={{ color: "var(--lj-text)" }}>
                        🎯 Moslik bali: <span className="lj-score">88%</span>
                      </p>
                      <div className="mt-1.5 grid gap-1">
                        <span className="lj-req">✅ 7 talab bajarilgan</span>
                        <span className="lj-req">❌ 1 talab bajarilmagan (kichik)</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {step >= 4 ? (
                <div className="lj-sys lj-appear">
                  <span className="lj-av">✦</span>
                  <span>
                    <b>QA-Assistant</b> statusni o&apos;zgartirdi: <span className="from">Testing</span> →{" "}
                    <span className="to lz-done">Ready to Test</span>
                  </span>
                </div>
              ) : null}

              {step >= 4 ? (
                <div className="lj-cm lj-appear">
                  <span className="lj-av">✦</span>
                  <div className="body">
                    <div className="by">
                      <b>QA-Assistant</b> <span className="time">hozir</span>
                      <span className="lj-marker">[AI_S2]</span>
                    </div>
                    <div className="lj-box">
                      <p className="text-sm" style={{ color: "var(--lj-text)" }}>
                        🧪 8 ta test case yozildi
                      </p>
                      <p className="lj-req mt-0.5" style={{ color: "var(--lj-sub)" }}>
                        positive: 5 · negative: 3 · qamrov 8/8
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          <aside className="lj-side">
            <div className="lj-side-row">
              <div className="lj-side-label">Holat</div>
              <div className="lj-side-val">
                <span className={cn("lj-status", statusCls)} style={{ padding: "3px 8px" }}>
                  {statusText}
                </span>
              </div>
            </div>
            <div className="lj-side-row">
              <div className="lj-side-label">Ijrochi</div>
              <div className="lj-side-val">
                <span className="lj-side-av" style={{ background: "#8b6fd6" }}>AR</span> Aziz R.
              </div>
            </div>
            <div className="lj-side-row">
              <div className="lj-side-label">Reporter</div>
              <div className="lj-side-val">
                <span className="lj-side-av" style={{ background: "#d69f6f" }}>MK</span> Malika K.
              </div>
            </div>
            <div className="lj-side-row">
              <div className="lj-side-label">PR</div>
              <div className="lj-side-val" style={{ color: "var(--lj-blue)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                #482 · merged
              </div>
            </div>
            <div className="lj-side-row" style={{ marginBottom: 0 }}>
              <div className="lj-side-label">Labels</div>
              <div className="lj-side-val" style={{ gap: 6, flexWrap: "wrap" }}>
                <span className="rounded-[4px] px-1.5 py-0.5 text-[10px]" style={{ background: "var(--lj-surface2)", color: "var(--lj-sub)" }}>auth</span>
                <span className="rounded-[4px] px-1.5 py-0.5 text-[10px]" style={{ background: "var(--lj-surface2)", color: "var(--lj-sub)" }}>sms</span>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function AutoReturnCallout() {
  const [ref, inView] = useInViewOnce(0.3);
  return (
    <div
      ref={ref}
      className={cn(
        "lj-scope reveal grid items-center gap-7 rounded-[18px] border border-border bg-card p-5 md:p-7 lg:grid-cols-[0.85fr_1.15fr]",
        inView && "in",
      )}
    >
      <div>
        <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
          <RotateCcw size={14} /> Avtomatik qaytarish
        </span>
        <h2 className="mt-3 text-2xl font-bold tracking-tight text-foreground md:text-3xl">
          Ball chegaradan past bo&apos;lsa — task o&apos;zi qaytadi
        </h2>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">
          Arbiter agent moslik balini hisoblaydi. Agar u chegaradan (masalan 80%) past bo&apos;lsa, QA-Assistant
          taskni developerga qaytaradi va sababini yozadi. Keyingi tekshiruvda dev izohlarini ham hisobga oladi.
        </p>
      </div>

      <div className="lj-win">
        <div className="lj-chrome">
          <span className="lj-dots">
            <i style={{ background: "#ff5f57" }} />
            <i style={{ background: "#febc2e" }} />
            <i style={{ background: "#28c840" }} />
          </span>
          <span className="lj-url">kompaniyangiz.atlassian.net/browse/DEV-1291</span>
        </div>
        <div className="lj-main">
          <div className="lj-crumb">Loyihalar / QA / DEV-1291</div>
          <h3 className="lj-summary">To&apos;lov: karta orqali to&apos;lash</h3>
          <div className="lj-status-row">
            <button type="button" className="lj-status lz-ret">
              Qaytarildi
              <ChevronDown size={12} />
            </button>
          </div>

          <div className="lj-feed" style={{ marginTop: 14 }}>
            <div className="lj-sys">
              <span className="lj-av">✦</span>
              <span>
                <b>QA-Assistant</b> statusni o&apos;zgartirdi: <span className="from">Testing</span> →{" "}
                <span className="to lz-ret">Qaytarildi</span>
              </span>
            </div>
            <div className="lj-cm">
              <span className="lj-av">✦</span>
              <div className="body">
                <div className="by">
                  <b>QA-Assistant</b> <span className="time">hozir</span>
                  <span className="lj-marker">[AI_S1]</span>
                </div>
                <div className="lj-box">
                  <p className="text-sm font-semibold" style={{ color: "var(--lj-text)" }}>
                    🎯 Moslik bali: <span className="lj-score" style={{ color: "var(--error)" }}>57%</span>
                  </p>
                  <div className="lj-warn" style={{ marginTop: 8 }}>
                    <span>🔄</span>
                    <span>
                      <b>Task qaytarildi</b> — moslik bali 57% (chegara 80%). 3 ta talab bajarilmagan.{" "}
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>[WARN_LOW_SCORE]</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
