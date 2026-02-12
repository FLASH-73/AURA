"use client";

import type { AssemblyStep, StepRuntimeState } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

interface StepCardProps {
  step: AssemblyStep;
  stepIndex: number;
  runtimeState: StepRuntimeState;
  isSelected: boolean;
  onClick: () => void;
}

function StepCircle({ index, status }: { index: number; status: StepRuntimeState["status"] }) {
  const base = "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold";

  switch (status) {
    case "success":
      return (
        <div className={`${base} bg-status-success text-white`}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3.5 7L6 9.5L10.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      );
    case "running":
      return (
        <div className={`${base} bg-accent text-white animate-pulse-subtle`}>
          {index}
        </div>
      );
    case "failed":
      return (
        <div className={`${base} bg-status-error text-white`}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M4 4L10 10M10 4L4 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      );
    case "human":
      return (
        <div className={`${base} bg-status-human text-white`}>{index}</div>
      );
    case "retrying":
      return (
        <div className={`${base} bg-status-warning text-white`}>{index}</div>
      );
    default:
      return (
        <div className={`${base} border border-bg-tertiary text-text-tertiary`}>
          {index}
        </div>
      );
  }
}

function formatDuration(ms: number): string {
  const seconds = Math.round(ms / 1000);
  return `${(seconds / 60) | 0}:${String(seconds % 60).padStart(2, "0")}`;
}

export function StepCard({ step, stepIndex, runtimeState, isSelected, onClick }: StepCardProps) {
  const handlerLabel = step.handler === "primitive"
    ? `primitive \u00B7 ${step.primitiveType ?? "unknown"}`
    : "policy";

  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
        isSelected ? "border-l-2 border-accent bg-accent-light" : ""
      }`}
    >
      <StepCircle index={stepIndex} status={runtimeState.status} />

      <div className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-[13px] font-medium text-text-primary">
          {step.name}
        </span>
        <span className="text-[12px] text-text-secondary">{handlerLabel}</span>
      </div>

      <div className="flex shrink-0 flex-col items-end gap-1">
        <StatusBadge
          status={runtimeState.status}
          retryInfo={
            runtimeState.status === "retrying"
              ? `${runtimeState.attempt}/${step.maxRetries}`
              : undefined
          }
        />
        {runtimeState.durationMs != null && (
          <span className="font-mono text-[11px] text-text-tertiary">
            {formatDuration(runtimeState.durationMs)}
          </span>
        )}
      </div>
    </button>
  );
}
