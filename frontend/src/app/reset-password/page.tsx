"use client";

import { useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LockKeyhole, CheckCircle } from "lucide-react";
import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Notice } from "@/components/ui/notice";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 8) {
      setError("Parol kamida 8 ta belgidan iborat bo'lishi kerak.");
      return;
    }
    if (password !== confirm) {
      setError("Parollar mos kelmadi.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/auth/password-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const payload = (await response.json().catch(() => null)) as { success?: boolean } | null;
      if (!response.ok || !payload?.success) {
        setError("Token yaroqsiz yoki muddati tugagan. Qaytadan so'rov yuboring.");
        return;
      }
      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch {
      setError("Xato yuz berdi. Qaytadan urinib ko'ring.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <Card className="mx-auto flex w-full max-w-[460px] flex-col gap-6 rounded-[28px] px-7 py-7" tone="soft">
        <Notice tone="error">Token topilmadi. Email havolasidan qaytadan kiring.</Notice>
        <Button fullWidth onClick={() => router.push("/login")} variant="ghost">
          Loginga qaytish
        </Button>
      </Card>
    );
  }

  if (success) {
    return (
      <Card className="mx-auto flex w-full max-w-[460px] flex-col gap-6 rounded-[28px] px-7 py-7" tone="soft">
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <CheckCircle className="text-green-500" size={40} />
          <h2 className="text-xl font-semibold">Parol yangilandi!</h2>
          <p className="text-sm text-muted-foreground">3 soniyada login sahifasiga o'tasiz...</p>
        </div>
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
      <div className="space-y-2">
        <Badge tone="soft">Parolni tiklash</Badge>
        <h1 className="text-2xl font-semibold tracking-tight">Yangi parol o'rnating</h1>
        <p className="text-sm text-muted-foreground">Kamida 8 ta belgidan iborat yangi parol kiriting.</p>
      </div>

      <Field label="Yangi parol">
        <Input
          autoComplete="new-password"
          minLength={8}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Yangi parol"
          required
          type="password"
          value={password}
        />
      </Field>

      <Field label="Parolni tasdiqlang">
        <Input
          autoComplete="new-password"
          minLength={8}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="Parolni qayta kiriting"
          required
          type="password"
          value={confirm}
        />
      </Field>

      {error ? <Notice tone="error">{error}</Notice> : null}

      <Button disabled={submitting} fullWidth type="submit">
        <LockKeyhole size={16} />
        {submitting ? "Saqlanmoqda..." : "Parolni saqlash"}
      </Button>

      <button
        className="text-center text-sm text-muted-foreground hover:text-foreground"
        onClick={() => router.push("/login")}
        type="button"
      >
        ← Loginga qaytish
      </button>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="qa-login-layout">
      <div className="qa-login-form-panel" style={{ gridColumn: "1 / -1" }}>
        <Suspense fallback={null}>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </main>
  );
}
