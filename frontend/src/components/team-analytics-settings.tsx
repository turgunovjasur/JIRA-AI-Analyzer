"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AnalyticsSettingsValue } from "@/lib/team-analytics-types";

export function TeamAnalyticsSettings({ workingStatus, dailyHours, demo = false, onSaved }: {
  workingStatus: string; dailyHours: number; demo?: boolean;
  onSaved: (settings: AnalyticsSettingsValue) => void;
}) {
  const [status, setStatus] = useState(workingStatus);
  const [hours, setHours] = useState(String(dailyHours));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => { setStatus(workingStatus); setHours(String(dailyHours)); }, [workingStatus, dailyHours]);
  return <Card>
    <h2 className="text-lg font-semibold">Settings</h2>
    <form className="mt-4 flex flex-wrap items-end gap-4" onSubmit={async event => {
      event.preventDefault(); setBusy(true); setMessage("");
      try {
        const values: AnalyticsSettingsValue = { working_status: status.trim(), daily_hours: Number(hours) };
        if (!values.working_status || !Number.isFinite(values.daily_hours) || values.daily_hours <= 0 || values.daily_hours > 24)
          throw new Error("Status va kunlik ish soatini to‘g‘ri kiriting");
        if (demo) { onSaved(values); setMessage("Demo sozlamalari saqlandi."); return; }
        const response = await fetch("/api/team-analytics", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Saqlashda xato");
        onSaved(values); setMessage("Saqlandi.");
      } catch (error) { setMessage(error instanceof Error ? error.message : "Saqlashda xato"); }
      finally { setBusy(false); }
    }}>
      <label className="grid gap-2 text-sm">Vaqt hisoblanadigan Jira statusi
        <input className="rounded-md border bg-background px-3 py-2" required maxLength={128} value={status}
          onChange={event => setStatus(event.target.value)} disabled={busy} placeholder="In Progress" />
      </label>
      <label className="grid gap-2 text-sm">Kunlik ish soati
        <input className="w-36 rounded-md border bg-background px-3 py-2" type="number" required min="0.01" max="24" step="0.01"
          value={hours} onChange={event => setHours(event.target.value)} disabled={busy} placeholder="8" />
      </label>
      <Button type="submit" disabled={busy || !status.trim() || !hours}>{busy ? "Saqlanmoqda…" : "Saqlash"}</Button>
    </form>
    <p className="mt-3 text-sm text-muted-foreground">Vaqt faqat tanlangan statusda yuradi. Boshqa barcha statuslarda to‘xtaydi, qaytganda oldingi vaqtga qo‘shilib davom etadi.</p>
    {message && <p role="status" className="mt-3 text-sm">{message}</p>}
  </Card>;
}
