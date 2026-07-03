"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Notice } from "@/components/ui/notice";
import { SectionHeader } from "@/components/ui/section-header";
import { SettingsBaseCard } from "@/components/settings/base-card-system";

type AdminJob = {
  id: number;
  job_type: string;
  task_key: string;
  company_id: number | null;
  dedupe_key: string;
  status: string;
  attempts: number;
  max_attempts: number;
  worker_name: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  last_error: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type JobsResponse = {
  success: boolean;
  jobs: AdminJob[];
  total: number;
  error?: string;
};

const STATUS_FILTERS = [
  { key: "", label: "Barchasi" },
  { key: "failed", label: "Failed" },
  { key: "queued", label: "Queued" },
  { key: "running", label: "Running" },
  { key: "done", label: "Done" },
];

const PAGE_SIZE = 50;

function statusTone(status: string): "danger" | "warning" | "success" | "default" {
  if (status === "failed") return "danger";
  if (status === "running") return "warning";
  if (status === "done") return "success";
  return "default";
}

function formatTs(value: string | null): string {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 19);
}

export function AdminJobsPanel() {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("failed");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [busyJobId, setBusyJobId] = useState<number | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams();
      if (statusFilter) query.set("status", statusFilter);
      query.set("limit", String(PAGE_SIZE));
      query.set("offset", String(offset));
      const response = await fetch(`/api/super-admin/jobs?${query.toString()}`);
      const payload = (await response.json().catch(() => null)) as JobsResponse | null;
      if (!response.ok || !payload?.success) {
        setError(payload?.error || "Job ro'yxatini o'qib bo'lmadi.");
        return;
      }
      setJobs(payload.jobs || []);
      setTotal(payload.total || 0);
    } catch {
      setError("Job ro'yxatini o'qib bo'lmadi.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, offset]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const changeFilter = (key: string) => {
    setStatusFilter(key);
    setOffset(0);
    setConfirmDeleteId(null);
  };

  const requeueJob = async (jobId: number) => {
    setBusyJobId(jobId);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/super-admin/jobs/${jobId}/requeue`, { method: "POST" });
      const payload = (await response.json().catch(() => null)) as { success?: boolean; error?: string } | null;
      if (!response.ok || !payload?.success) {
        setError(payload?.error || "Job requeue bo'lmadi.");
        return;
      }
      setSuccess(`Job #${jobId} qayta navbatga qo'yildi.`);
      await loadJobs();
    } catch {
      setError("Job requeue bo'lmadi.");
    } finally {
      setBusyJobId(null);
    }
  };

  const deleteJob = async (jobId: number) => {
    if (confirmDeleteId !== jobId) {
      setConfirmDeleteId(jobId);
      return;
    }
    setBusyJobId(jobId);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/super-admin/jobs/${jobId}`, { method: "DELETE" });
      const payload = (await response.json().catch(() => null)) as { success?: boolean; error?: string } | null;
      if (!response.ok || !payload?.success) {
        setError(payload?.error || "Job o'chirilmadi.");
        return;
      }
      setSuccess(`Job #${jobId} o'chirildi.`);
      setConfirmDeleteId(null);
      await loadJobs();
    } catch {
      setError("Job o'chirilmadi.");
    } finally {
      setBusyJobId(null);
    }
  };

  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <SettingsBaseCard
      header={(
        <SectionHeader
          action={(
            <Button disabled={loading} onClick={() => void loadJobs()} type="button" variant="ghost">
              Yangilash
            </Button>
          )}
          eyebrow="Job Queue (DLQ)"
          title="Background joblar konsoli"
        />
      )}
    >
      <div className="mt-4 grid gap-4">
        {error ? <Notice tone="error">{error}</Notice> : null}
        {success ? <Notice tone="success">{success}</Notice> : null}

        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((item) => (
            <Button
              key={item.key || "all"}
              onClick={() => changeFilter(item.key)}
              size="sm"
              type="button"
              variant={statusFilter === item.key ? "primary" : "ghost"}
            >
              {item.label}
            </Button>
          ))}
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Task</th>
                <th>Turi</th>
                <th>Status</th>
                <th>Urinish</th>
                <th>Xato</th>
                <th>Yangilangan</th>
                <th>Amallar</th>
              </tr>
            </thead>
            <tbody>
              {jobs.length ? (
                jobs.map((job) => (
                  <tr key={job.id}>
                    <td>#{job.id}</td>
                    <td>
                      <div className="font-semibold text-foreground">{job.task_key || "-"}</div>
                      <div className="text-xs text-muted-foreground">
                        company {job.company_id ?? "-"}
                      </div>
                    </td>
                    <td>{job.job_type}</td>
                    <td>
                      <Badge tone={statusTone(job.status)}>{job.status}</Badge>
                    </td>
                    <td>
                      {job.attempts}/{job.max_attempts}
                    </td>
                    <td>
                      {job.last_error ? (
                        <span className="text-xs text-muted-foreground" title={job.last_error}>
                          {job.last_error.length > 80 ? `${job.last_error.slice(0, 80)}…` : job.last_error}
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="text-xs">{formatTs(job.updated_at)}</td>
                    <td>
                      <div className="flex gap-2">
                        {job.status === "failed" ? (
                          <Button
                            disabled={busyJobId === job.id}
                            onClick={() => void requeueJob(job.id)}
                            size="sm"
                            type="button"
                          >
                            Requeue
                          </Button>
                        ) : null}
                        {job.status === "failed" || job.status === "done" ? (
                          <Button
                            disabled={busyJobId === job.id}
                            onClick={() => void deleteJob(job.id)}
                            size="sm"
                            type="button"
                            variant={confirmDeleteId === job.id ? "danger" : "ghost"}
                          >
                            {confirmDeleteId === job.id ? "Tasdiqlash" : "O'chirish"}
                          </Button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8}>{loading ? "Yuklanmoqda..." : "Job topilmadi."}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            Jami: {total} ta job · {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} ko'rsatilmoqda
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
