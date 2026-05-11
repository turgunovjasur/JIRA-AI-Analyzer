import { Notice } from "@/components/ui/notice";
import type { AnalysisStatusBanner } from "@/lib/types";

type AnalysisStatusBannerProps = {
  banner?: AnalysisStatusBanner | null;
};

function toTone(level?: string | null): "error" | "warning" | "info" {
  const normalized = (level || "").toLowerCase();
  if (normalized === "warning") return "warning";
  if (normalized === "info") return "info";
  return "error";
}

function prettyKey(key: string) {
  return key.replace(/_/g, " ");
}

export function AnalysisStatusBannerView({ banner }: AnalysisStatusBannerProps) {
  if (!banner) return null;

  const tone = toTone(banner.level);
  const lines: string[] = [];
  if (banner.title) lines.push(banner.title);
  if (banner.message) lines.push(banner.message);
  if (banner.code) lines.push(`Code: ${banner.code}`);

  const meta = banner.meta || {};
  const metaEntries = Object.entries(meta).filter(([, value]) => value !== null && value !== undefined);
  if (metaEntries.length) {
    lines.push(
      ...metaEntries.map(([key, value]) => `${prettyKey(key)}: ${String(value)}`),
    );
  }

  if (banner.actions?.length) {
    lines.push(`Actions: ${banner.actions.join(" | ")}`);
  }

  return <Notice tone={tone}>{lines.join("\n")}</Notice>;
}
