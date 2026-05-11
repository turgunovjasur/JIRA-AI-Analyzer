"use client";

import { useEffect, useState, type FormEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/metric-card";
import { Notice } from "@/components/ui/notice";
import { PageIntro } from "@/components/ui/page-intro";
import { SectionHeader } from "@/components/ui/section-header";
import { BaseInputField, SettingsBaseCard } from "@/components/settings/base-card-system";
import { StatusPill } from "@/components/ui/status-pill";
import type {
  CompanyAdminResetTokenPayload,
  CompanyAdminTeamOverview,
  CompanyAdminUser,
} from "@/lib/types";

type CompanyAdminPanelProps = {
  companyName: string;
};

const SETTINGS_INPUT_CLASS = "settings-form-input";

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

function roleLabel(user: CompanyAdminUser) {
  return user.role === "company_admin" ? "Company admin" : "User";
}

export function CompanyAdminPanel({ companyName }: CompanyAdminPanelProps) {
  const [team, setTeam] = useState<CompanyAdminTeamOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordDrafts, setPasswordDrafts] = useState<Record<number, string>>({});
  const [resetTokens, setResetTokens] = useState<Record<number, CompanyAdminResetTokenPayload | null>>({});
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [openUserId, setOpenUserId] = useState<number | null>(null);

  async function loadTeam() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/company-admin/team", { cache: "no-store" });
      const payload = (await response.json().catch(() => null)) as
        | (CompanyAdminTeamOverview & { error?: string; success?: boolean })
        | null;

      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Team ma'lumotlari yuklanmadi.");
      }

      setTeam(payload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Team yuklashda xato.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTeam();
  }, []);

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      await action();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Action xatosi.");
    } finally {
      setBusy(false);
    }
  }

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newUsername.trim()) {
      setError("Username kiriting.");
      return;
    }
    if (newPassword.length < 6) {
      setError("Parol kamida 6 ta belgi bo'lishi kerak.");
      return;
    }

    await runAction(async () => {
      const response = await fetch("/api/company-admin/users", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: newUsername.trim().toLowerCase(),
          password: newPassword,
        }),
      });

      const payload = (await response.json().catch(() => null)) as
        | { error?: string; success?: boolean; user?: CompanyAdminUser }
        | null;

      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "User yaratilmadi.");
      }

      setNewUsername("");
      setNewPassword("");
      setSuccess(`User yaratildi: ${payload.user?.username || newUsername}`);
      await loadTeam();
    });
  }

  async function toggleUserStatus(user: CompanyAdminUser) {
    await runAction(async () => {
      const response = await fetch(`/api/company-admin/users/${user.id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          is_active: !Boolean(user.is_active),
        }),
      });

      const payload = (await response.json().catch(() => null)) as
        | { error?: string; success?: boolean }
        | null;

      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Status yangilanmadi.");
      }

      setSuccess(`${user.username} statusi yangilandi.`);
      await loadTeam();
    });
  }

  async function savePassword(user: CompanyAdminUser) {
    const newPasswordValue = passwordDrafts[user.id] || "";
    if (newPasswordValue.length < 6) {
      setError("Parol kamida 6 ta belgi bo'lishi kerak.");
      return;
    }

    await runAction(async () => {
      const response = await fetch(`/api/company-admin/users/${user.id}/password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          new_password: newPasswordValue,
        }),
      });

      const payload = (await response.json().catch(() => null)) as
        | { error?: string; success?: boolean }
        | null;

      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "Parol yangilanmadi.");
      }

      setPasswordDrafts((current) => ({ ...current, [user.id]: "" }));
      setSuccess(`${user.username} paroli yangilandi.`);
    });
  }

  async function createResetToken(user: CompanyAdminUser) {
    await runAction(async () => {
      const response = await fetch(`/api/company-admin/users/${user.id}/reset-token`, {
        method: "POST",
      });

      const payload = (await response.json().catch(() => null)) as
        | { error?: string; payload?: CompanyAdminResetTokenPayload; success?: boolean }
        | null;

      if (!response.ok || !payload?.success || !payload.payload) {
        throw new Error(payload?.error || "Reset token yaratilmadi.");
      }

      setResetTokens((current) => ({ ...current, [user.id]: payload.payload || null }));
      setSuccess(`${user.username} uchun reset token yaratildi.`);
    });
  }

  async function deleteUser(user: CompanyAdminUser) {
    await runAction(async () => {
      const response = await fetch(`/api/company-admin/users/${user.id}`, {
        method: "DELETE",
      });

      const payload = (await response.json().catch(() => null)) as
        | { error?: string; success?: boolean }
        | null;

      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || "User o'chirilmadi.");
      }

      setConfirmDeleteId(null);
      setOpenUserId((current) => (current === user.id ? null : current));
      setSuccess(`${user.username} o'chirildi.`);
      await loadTeam();
    });
  }

  return (
    <>
      <PageIntro
        eyebrow="Team Management"
        title={`${companyName} jamoasi va kirish huquqlarini boshqaring`}
        description="Yangi a'zo qo'shish, status o'zgartirish, parol yangilash va reset token yaratish kabi kundalik boshqaruv vazifalari shu yerda jamlangan."
      />

      {loading ? (
        <PageIntro eyebrow="Loading" title="Jamoa ma'lumotlari yuklanmoqda..." />
      ) : null}

      {error ? <Notice tone="error">{error}</Notice> : null}
      {success ? <Notice tone="success">{success}</Notice> : null}

      {team ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <MetricCard helper="Company admin va barcha userlar" label="Jami Akkaunt" value={team.total_accounts} />
            <MetricCard
              helper="Seat limitga kiradigan oddiy userlar"
              label="Qo'shimcha Userlar"
              value={`${team.extra_user_count}/${team.company.seat_limit || 0}`}
            />
            <MetricCard helper="Yangi user qo'shish uchun qolgan joy" label="Bo'sh Joy" value={team.available_slots} />
          </section>

          <SettingsBaseCard
            header={(
              <SectionHeader
                action={<Badge>Login: `username@{(team.company.company_code || "").toLowerCase()}`</Badge>}
                eyebrow="Add User"
                title="Yangi a'zo qo'shish"
              />
            )}
          >

            {team.available_slots <= 0 ? (
              <Notice className="mt-4" tone="warning">
                Qo'shimcha user limiti to'lgan. Yangi a'zo qo'shish uchun bo'sh joy kerak.
              </Notice>
            ) : null}

            <form className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_180px] lg:items-end" onSubmit={createUser}>
              <BaseInputField
                className={SETTINGS_INPUT_CLASS}
                label="Username"
                onChange={setNewUsername}
                placeholder="olim"
                value={newUsername}
              />
              <BaseInputField
                className={SETTINGS_INPUT_CLASS}
                label="Parol"
                onChange={setNewPassword}
                placeholder="Kamida 6 ta belgi"
                type="password"
                value={newPassword}
              />
              <Button
                disabled={busy || team.available_slots <= 0}
                type="submit"
              >
                {busy ? "Qo'shilmoqda..." : "Qo'shish"}
              </Button>
            </form>
          </SettingsBaseCard>

          <SettingsBaseCard header={<SectionHeader eyebrow="Team Members" title="Jamoa a'zolari" />}>
            {team.users.length ? (
              <div className="mt-5 grid gap-3">
                {team.users.map((user) => {
                  const isCompanyAdmin = user.role === "company_admin";
                  const resetToken = resetTokens[user.id];
                  const isOpen = openUserId === user.id;
                  return (
                    <article className="rounded-[16px] border border-border bg-layer" key={user.id}>
                      <button
                        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                        onClick={() => setOpenUserId((current) => (current === user.id ? null : user.id))}
                        type="button"
                      >
                        <div className="min-w-0">
                          <p className="truncate text-base font-semibold text-foreground">{user.username}</p>
                          <p className="mt-1 truncate text-sm text-muted-foreground">
                            {roleLabel(user)} | yaratilgan: {formatDate(user.created_at)}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusPill
                            tone={Boolean(user.is_active) ? "good" : "bad"}
                            value={Boolean(user.is_active) ? "Active" : "Inactive"}
                          />
                          <span className="text-xs text-muted-foreground">{isOpen ? "Yopish" : "Ochish"}</span>
                        </div>
                      </button>

                      {isOpen ? (
                        <div className="border-t border-border px-4 pb-4 pt-3">
                          <div className="flex flex-wrap gap-2">
                            {!isCompanyAdmin ? (
                              <Button
                                disabled={busy}
                                onClick={() => void toggleUserStatus(user)}
                                type="button"
                                variant="ghost"
                              >
                                {Boolean(user.is_active) ? "Nofaol qilish" : "Faollashtirish"}
                              </Button>
                            ) : (
                              <Badge tone="soft">Protected admin</Badge>
                            )}

                            {!isCompanyAdmin ? (
                              <Button
                                className="user-actions__button"
                                disabled={busy}
                                onClick={() => setConfirmDeleteId(confirmDeleteId === user.id ? null : user.id)}
                                type="button"
                                variant="ghost"
                              >
                                O'chirish
                              </Button>
                            ) : null}
                          </div>

                          {confirmDeleteId === user.id ? (
                            <Notice className="mt-4" tone="warning">
                              <p>{user.username} ni o'chirasizmi?</p>
                              <div className="mt-3 flex flex-wrap gap-2">
                                <Button
                                  disabled={busy}
                                  onClick={() => void deleteUser(user)}
                                  type="button"
                                >
                                  Ha, o'chirish
                                </Button>
                                <Button
                                  className="user-actions__button"
                                  onClick={() => setConfirmDeleteId(null)}
                                  type="button"
                                  variant="ghost"
                                >
                                  Bekor qilish
                                </Button>
                              </div>
                            </Notice>
                          ) : null}

                          <div className="mt-4 grid gap-4 lg:grid-cols-2">
                            <div className="space-y-4 rounded-[18px] border border-border bg-card p-4">
                              <h4 className="text-lg font-semibold text-foreground">Parolni yangilash</h4>
                              <BaseInputField
                                className={SETTINGS_INPUT_CLASS}
                                label="Yangi parol"
                                onChange={(value) =>
                                  setPasswordDrafts((current) => ({
                                    ...current,
                                    [user.id]: value,
                                  }))
                                }
                                placeholder="Kamida 6 ta belgi"
                                type="password"
                                value={passwordDrafts[user.id] || ""}
                              />
                              <Button
                                disabled={busy}
                                onClick={() => void savePassword(user)}
                                type="button"
                                variant="ghost"
                              >
                                Saqlash
                              </Button>
                            </div>

                            <div className="space-y-4 rounded-[18px] border border-border bg-card p-4">
                              <h4 className="text-lg font-semibold text-foreground">Reset Token</h4>
                              <p className="text-sm leading-6 text-muted-foreground">
                                Token bir martalik bo'ladi va userga xavfsiz kanal orqali yuboriladi.
                              </p>
                              <Button
                                disabled={busy}
                                onClick={() => void createResetToken(user)}
                                type="button"
                                variant="ghost"
                              >
                                Reset Token yaratish
                              </Button>
                              {resetToken ? (
                                <div className="rounded-[16px] border border-border bg-layer p-4">
                                  <code className="break-all text-foreground">{resetToken.token}</code>
                                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                                    Amal qilish muddati: {resetToken.expires_at}
                                  </p>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            ) : (
              <p className="mt-5 text-sm leading-6 text-muted-foreground">Hali jamoa a'zosi yo'q.</p>
            )}
          </SettingsBaseCard>
        </>
      ) : null}
    </>
  );
}
