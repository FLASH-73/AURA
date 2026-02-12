"use client";

import type { StepStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  StepStatus,
  { label: string; bg: string; text: string }
> = {
  pending: { label: "PENDING", bg: "bg-bg-tertiary", text: "text-text-tertiary" },
  running: { label: "RUNNING", bg: "bg-status-running-bg", text: "text-status-running" },
  success: { label: "DONE", bg: "bg-status-success-bg", text: "text-status-success" },
  failed: { label: "FAILED", bg: "bg-status-error-bg", text: "text-status-error" },
  human: { label: "HUMAN", bg: "bg-status-human-bg", text: "text-status-human" },
  retrying: { label: "RETRY", bg: "bg-status-warning-bg", text: "text-status-warning" },
};

interface StatusBadgeProps {
  status: StepStatus;
  retryInfo?: string;
}

export function StatusBadge({ status, retryInfo }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const label = status === "retrying" && retryInfo
    ? `RETRY ${retryInfo}`
    : config.label;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.02em] ${config.bg} ${config.text}`}
    >
      {label}
    </span>
  );
}
