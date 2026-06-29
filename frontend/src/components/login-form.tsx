"use client";

import { startTransition, useState, type FormEvent } from "react";
import { LockKeyhole, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BaseCard, Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

function ForgotPasswordForm({ onBack }: { onBack: () => void }) {
  const [username, setUsername] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await fetch("/api/auth/request-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim() }),
      });
      setSent(true);
    } catch {
      setError("Xato yuz berdi. Qaytadan urinib ko'ring.");
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <div className="flex flex-col gap-4">
        <Notice tone="success">
          Agar bu username mavjud bo'lsa va emaili bo'lsa, tiklash havolasi yuborildi.
        </Notice>
        <button className="text-sm text-muted-foreground hover:text-foreground" onClick={onBack} type="button">
          ← Loginga qaytish
        </button>
      </div>
    );
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={onSubmit}>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Parolni tiklash</h2>
        <p className="text-sm text-muted-foreground">Username kiriting — emailga havola yuboramiz.</p>
      </div>
      <Field label="Username">
        <Input
          autoComplete="username"
          onChange={(e) => setUsername(e.target.value)}
          placeholder="username@company"
          required
          value={username}
        />
      </Field>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button disabled={submitting} fullWidth type="submit">
        {submitting ? "Yuborilmoqda..." : "Havola yuborish"}
      </Button>
      <button className="text-center text-sm text-muted-foreground hover:text-foreground" onClick={onBack} type="button">
        ← Orqaga
      </button>
    </form>
  );
}

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForgot, setShowForgot] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      const payload = (await response.json().catch(() => null)) as {
        error?: string;
        redirectTo?: string;
        success?: boolean;
      } | null;

      if (!response.ok || !payload?.success) {
        setError(payload?.error || "Login muvaffaqiyatsiz tugadi.");
        return;
      }

      startTransition(() => {
        router.push(payload?.redirectTo || "/dashboard");
        router.refresh();
      });
    } catch (submitError) {
      const message =
        submitError instanceof Error
          ? submitError.message
          : "Backend bilan ulanishda xato yuz berdi.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (showForgot) {
    return (
      <Card
        className="mx-auto flex w-full max-w-[460px] flex-col gap-6 rounded-[28px] px-7 py-7"
        tone="soft"
      >
        <Badge tone="soft">Web Portal</Badge>
        <ForgotPasswordForm onBack={() => setShowForgot(false)} />
      </Card>
    );
  }

  return (
    <Card
      as="form"
      className="mx-auto flex w-full max-w-[460px] flex-col gap-6 rounded-[28px] px-7 py-7"
      onSubmit={onSubmit}
      tone="soft"
    >
      <div className="space-y-4">
        <Badge tone="soft">Web Portal</Badge>
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            QA-Assistant portaliga kiring
          </h1>
          <p className="text-sm leading-6 text-muted-foreground">
            O&apos;z rolingizga mos ish maydoniga kirish uchun login va parolni kiriting.
          </p>
        </div>
      </div>

      <Field label="Login">
        <Input
          autoComplete="username"
          className="qa-login-input"
          name="username"
          onChange={(event) => setUsername(event.target.value)}
          placeholder="admin yoki user@company"
          required
          value={username}
        />
      </Field>

      <Field label="Parol">
        <Input
          autoComplete="current-password"
          className="qa-login-input"
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Parolni kiriting"
          required
          type="password"
          value={password}
        />
      </Field>

      {error ? <Notice tone="error">{error}</Notice> : null}

      <Button disabled={submitting} fullWidth type="submit">
        <LockKeyhole size={16} />
        {submitting ? "Kirilmoqda..." : "Kirish"}
      </Button>

      <button
        className="text-center text-sm text-muted-foreground hover:text-foreground"
        onClick={() => setShowForgot(true)}
        type="button"
      >
        Parolni unutdim?
      </button>

      <div className="grid gap-3 pt-1 sm:grid-cols-2">
        <BaseCard as="div" className="px-4 py-4" padding="none" tone="soft">
          <div className="mb-3 inline-flex rounded-full bg-primary/10 p-2 text-primary">
            <UserRound size={16} />
          </div>
          <div className="text-sm font-medium text-foreground">Access</div>
          <div className="mt-1 text-sm text-muted-foreground">Role-based</div>
        </BaseCard>
        <BaseCard as="div" className="px-4 py-4" padding="none" tone="soft">
          <div className="mb-3 inline-flex rounded-full bg-primary/10 p-2 text-primary">
            <LockKeyhole size={16} />
          </div>
          <div className="text-sm font-medium text-foreground">Session</div>
          <div className="mt-1 text-sm text-muted-foreground">Secure cookie</div>
        </BaseCard>
      </div>
    </Card>
  );
}
