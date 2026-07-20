import Link from "next/link";
import { Activity, ArrowRight, Bot, ShieldCheck, Sparkles, TestTube2, Waypoints } from "lucide-react";

import { ContactSection } from "@/components/contact-section";
import { Badge } from "@/components/ui/badge";
import { BaseCard, Card } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { SectionHeader } from "@/components/ui/section-header";
import { DEMO_ABOUT } from "@/lib/demo-data";

const HIGHLIGHT_ICONS = [Bot, Waypoints, ShieldCheck];

const MODULES = [
  {
    href: "/demo/tzpr",
    icon: <Waypoints size={18} />,
    title: "TZ-PR Checker",
    note: "Spec va PR mosligini 3 agent bilan tekshirish",
  },
  {
    href: "/demo/testcase",
    icon: <TestTube2 size={18} />,
    title: "Test Case Generator",
    note: "Talablar asosida test case yozish",
  },
  {
    href: "/demo/monitoring",
    icon: <Activity size={18} />,
    title: "Monitoring",
    note: "Queue, servis holati va statistika",
  },
];

export default function DemoDashboardPage() {
  const { productName, tagline, intro, highlights } = DEMO_ABOUT;

  return (
    <div className="grid gap-5">
      <div className="qa-page-intro">
        <span className="qa-eyebrow">Biz haqimizda</span>
        <h2 className="qa-page-heading">{productName} — {tagline}</h2>
        <p className="qa-page-desc">{intro}</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Modullar" value="2 + 1" helper="Checker, Testcase + Monitoring" />
        <MetricCard label="Har modul" value="3 agent" helper="scope → verify → arbiter" />
        <MetricCard label="Integratsiya" value="JIRA" helper="GitHub PR + Figma" />
        <MetricCard label="Rejim" value="Multi-tenant" helper="Har kompaniya alohida" />
      </section>

      <Card>
        <SectionHeader
          eyebrow="Nima uchun QA-Assistant"
          title="Bir emas — bir nechta agent tekshiradi"
          action={<Badge tone="soft"><Sparkles size={13} className="mr-1" /> AI multi-agent</Badge>}
        />
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {highlights.map((h, i) => {
            const Icon = HIGHLIGHT_ICONS[i] ?? Bot;
            return (
              <BaseCard as="div" key={h.title} className="p-5" padding="none" tone="soft">
                <div className="mb-3 inline-flex rounded-full bg-primary/10 p-2 text-primary">
                  <Icon size={18} />
                </div>
                <strong className="block text-base font-semibold text-foreground">{h.title}</strong>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{h.text}</p>
              </BaseCard>
            );
          })}
        </div>
      </Card>

      <Card>
        <SectionHeader
          eyebrow="Sinab ko'ring"
          title="Modullar"
          action={<Badge>{MODULES.length} ta</Badge>}
        />
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MODULES.map((m) => (
            <BaseCard
              as={Link}
              href={m.href}
              key={m.href}
              className="qa-module-card group"
              interactive
              padding="none"
            >
              <span className="qa-module-card-icon">{m.icon}</span>
              <strong className="block text-base font-semibold text-foreground">{m.title}</strong>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{m.note}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary">
                Ochish <ArrowRight size={14} />
              </span>
            </BaseCard>
          ))}
        </div>
      </Card>

      <div id="contact" className="scroll-mt-24">
        <SectionHeader eyebrow="Aloqa" title="Qiziqdingizmi? Bog'laning" />
        <p className="mt-3 mb-5 max-w-2xl text-sm leading-6 text-muted-foreground">
          Tizimni o&apos;z jamoangizda sinab ko&apos;rmoqchi bo&apos;lsangiz yoki savollaringiz bo&apos;lsa —
          ma&apos;lumotingizni qoldiring yoki bevosita yozing.
        </p>
        <ContactSection source="demo" />
      </div>
    </div>
  );
}
