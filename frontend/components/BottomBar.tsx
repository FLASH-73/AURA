"use client";

import useSWR from "swr";
import { useAssembly } from "@/context/AssemblyContext";
import { useExecution } from "@/context/ExecutionContext";
import type { TeleopState } from "@/lib/types";
import { api } from "@/lib/api";

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function TeleopIndicator() {
  const { data: teleop } = useSWR<TeleopState>(
    "/teleop/state",
    api.getTeleopState,
    { refreshInterval: 3000 },
  );

  if (!teleop?.active) return null;

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-2 animate-pulse-subtle rounded-full bg-status-success" />
      <span className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
        Teleop
      </span>
      <span className="font-mono text-[13px] font-medium tabular-nums text-text-primary">
        {teleop.arms.join(", ")}
      </span>
    </div>
  );
}

export function BottomBar() {
  const { assembly } = useAssembly();
  const { executionState } = useExecution();

  const completedSteps = Object.values(executionState.stepStates).filter(
    (s) => s.status === "success",
  ).length;
  const totalSteps = assembly?.stepOrder.length ?? 0;

  const items = [
    { label: "Cycle", value: formatTime(executionState.elapsedMs) },
    { label: "Success", value: `${Math.round(executionState.overallSuccessRate * 100)}%` },
    { label: "Steps", value: `${completedSteps} / ${totalSteps}` },
    { label: "Run", value: `#${executionState.runNumber}` },
  ];

  return (
    <footer className="flex h-10 shrink-0 items-center justify-center gap-8 border-t border-bg-tertiary px-6">
      <TeleopIndicator />
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
            {item.label}
          </span>
          <span className="font-mono text-[13px] font-medium tabular-nums text-text-primary">
            {item.value}
          </span>
        </div>
      ))}
    </footer>
  );
}
