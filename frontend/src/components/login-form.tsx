"use client";

import { startTransition, useState, type FormEvent } from "react";
import { LockKeyhole, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
            QA Assistant portaliga kiring
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

      <div className="grid gap-3 pt-1 sm:grid-cols-2">
        <div className="rounded-[18px] border border-border bg-[color:var(--bg-strong)] px-4 py-4">
          <div className="mb-3 inline-flex rounded-full bg-primary/10 p-2 text-primary">
            <UserRound size={16} />
          </div>
          <div className="text-sm font-medium text-foreground">Access</div>
          <div className="mt-1 text-sm text-muted-foreground">Role-based</div>
        </div>
        <div className="rounded-[18px] border border-border bg-[color:var(--bg-strong)] px-4 py-4">
          <div className="mb-3 inline-flex rounded-full bg-primary/10 p-2 text-primary">
            <LockKeyhole size={16} />
          </div>
          <div className="text-sm font-medium text-foreground">Session</div>
          <div className="mt-1 text-sm text-muted-foreground">Secure cookie</div>
        </div>
      </div>
    </Card>
  );
}
