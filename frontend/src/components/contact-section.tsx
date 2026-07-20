"use client";

import { useState } from "react";
import { Mail, Phone, Send } from "lucide-react";

import { BaseCard, Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

export const CONTACT = {
  email: "tjasur224@gmail.com",
  telegram: "JasurTurgunov01",
  phone: "+998936026869",
  phoneDisplay: "+998 93 602 68 69",
};

export function ContactSection({ source = "landing" }: { source?: string }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !phone.trim() || !role.trim()) {
      setError("Ism familiya, telefon raqami va kasbingizni kiriting.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), phone: phone.trim(), role: role.trim(), source }),
      });
      const data = (await response.json().catch(() => null)) as { success?: boolean; error?: string } | null;
      if (!response.ok || !data?.success) {
        setError(data?.error || "Yuborib bo'lmadi. Iltimos, o'ngdagi bevosita aloqa orqali yozing.");
        return;
      }
      setSent(true);
      setName("");
      setPhone("");
      setRole("");
    } catch {
      setError("Tarmoq xatosi. Iltimos, o'ngdagi bevosita aloqa orqali yozing.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* forma */}
      <Card as="form" onSubmit={submit} className="grid content-start gap-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Bepul sinab ko&apos;ring</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Ma&apos;lumotingizni qoldiring — biz sizga alohida kompaniya (akkaunt) ochib beramiz va tizimni o&apos;z
            JIRA&apos;ngizda, real natijalar bilan bepul sinab ko&apos;rasiz.
          </p>
        </div>
        <Field label="Ism familiya">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Aziz Rahimov" autoComplete="name" />
        </Field>
        <Field label="Telefon raqam">
          <Input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+998 90 123 45 67"
            autoComplete="tel"
          />
        </Field>
        <Field label="Kasbingiz">
          <Input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="QA muhandisi, dasturchi, PM..."
            autoComplete="organization-title"
          />
        </Field>
        {error ? <Notice tone="error">{error}</Notice> : null}
        {sent ? (
          <Notice tone="success">
            Rahmat! So&apos;rovingiz qabul qilindi — tez orada siz bilan bog&apos;lanamiz.
          </Notice>
        ) : null}
        <Button type="submit" disabled={loading}>
          <Send size={15} /> {loading ? "Yuborilmoqda..." : "Yuborish"}
        </Button>
      </Card>

      {/* bevosita aloqa */}
      <div className="grid content-start gap-3">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Yoki bevosita bog&apos;laning</h3>
          <p className="mt-1 text-sm text-muted-foreground">Qulay usulni tanlang.</p>
        </div>
        <ContactLink
          href={`https://t.me/${CONTACT.telegram}`}
          external
          icon={<TelegramIcon />}
          label="Telegram"
          value={`@${CONTACT.telegram}`}
        />
        <ContactLink
          href={`mailto:${CONTACT.email}`}
          icon={<Mail size={17} />}
          label="Email"
          value={CONTACT.email}
        />
        <ContactLink
          href={`tel:${CONTACT.phone}`}
          icon={<Phone size={17} />}
          label="Telefon"
          value={CONTACT.phoneDisplay}
        />
      </div>
    </div>
  );
}

function ContactLink({
  href,
  external,
  icon,
  label,
  value,
}: {
  href: string;
  external?: boolean;
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <BaseCard
      as="a"
      href={href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      className="flex items-center gap-3.5 p-4 transition-transform hover:-translate-y-0.5 hover:border-primary/30"
      padding="none"
      interactive
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-primary/10 text-primary">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</span>
        <span className="block truncate text-sm font-semibold text-foreground">{value}</span>
      </span>
    </BaseCard>
  );
}

function TelegramIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M21.94 4.4 18.6 20.1c-.25 1.1-.9 1.37-1.83.86l-5.05-3.72-2.44 2.35c-.27.27-.5.5-1.01.5l.36-5.13 9.34-8.44c.4-.36-.09-.56-.63-.2L5.79 13.2 1.6 11.9c-1.06-.33-1.08-1.06.22-1.57L20.5 3.06c.88-.33 1.65.2 1.44 1.34z" />
    </svg>
  );
}
