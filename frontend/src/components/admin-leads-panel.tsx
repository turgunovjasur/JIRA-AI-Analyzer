"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import { SettingsBaseCard } from "@/components/settings/base-card-system";

type Lead = {
  id: number;
  name: string;
  phone: string;
  role: string;
  source: string;
  status: string;
  note: string | null;
  created_at: string | null;
};

type LeadsResponse = {
  success: boolean;
  leads: Lead[];
  total: number;
  error?: string;
};

const PAGE_SIZE = 50;

function formatTs(value: string | null): string {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
}

export function AdminLeadsPanel() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams();
      query.set("limit", String(PAGE_SIZE));
      query.set("offset", String(offset));
      const response = await fetch(`/api/super-admin/leads?${query.toString()}`, { cache: "no-store" });
      const payload = (await response.json().catch(() => null)) as LeadsResponse | null;
      if (!response.ok || !payload?.success) {
        setError(payload?.error || "Lidlarni o'qib bo'lmadi.");
        return;
      }
      setLeads(payload.leads || []);
      setTotal(payload.total || 0);
    } catch {
      setError("Lidlarni o'qib bo'lmadi.");
    } finally {
      setLoading(false);
    }
  }, [offset]);

  useEffect(() => {
    void loadLeads();
  }, [loadLeads]);

  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <SettingsBaseCard
      header={(
        <SectionHeader
          action={(
            <Button disabled={loading} onClick={() => void loadLeads()} type="button" variant="ghost">
              Yangilash
            </Button>
          )}
          eyebrow="Lidlar"
          title="Kelib tushgan so'rovlar"
        />
      )}
    >
      <div className="mt-4 grid gap-4">
        {error ? <Notice tone="error">{error}</Notice> : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Ism familiya</th>
                <th>Telefon</th>
                <th>Kasb</th>
                <th>Manba</th>
                <th>Sana</th>
              </tr>
            </thead>
            <tbody>
              {leads.length ? (
                leads.map((lead) => (
                  <tr key={lead.id}>
                    <td>#{lead.id}</td>
                    <td className="font-semibold text-foreground">{lead.name}</td>
                    <td>
                      <a className="text-primary hover:underline" href={`tel:${lead.phone}`}>
                        {lead.phone}
                      </a>
                    </td>
                    <td>{lead.role}</td>
                    <td>
                      <Badge tone="default">{lead.source}</Badge>
                    </td>
                    <td className="text-xs">{formatTs(lead.created_at)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6}>{loading ? "Yuklanmoqda..." : "Hozircha lid yo'q."}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Jami: {total} ta lid
            {total > 0 ? ` · ${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} ko'rsatilmoqda` : ""}
          </div>
          <div className="flex gap-2">
            <Button
              disabled={!canPrev || loading}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              size="sm"
              type="button"
              variant="ghost"
            >
              ← Oldingi
            </Button>
            <Button
              disabled={!canNext || loading}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              size="sm"
              type="button"
              variant="ghost"
            >
              Keyingi →
            </Button>
          </div>
        </div>
      </div>
    </SettingsBaseCard>
  );
}
