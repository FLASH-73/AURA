"use client";

import { useEffect, useRef, useState } from "react";
import { useExecution } from "@/context/ExecutionContext";
import { useAssembly } from "@/context/AssemblyContext";

export function ExecutionProgressHUD() {
  const { executionState } = useExecution();
  const { assembly } = useAssembly();
  const [elapsed, setElapsed] = useState("00:00");
  const startRef = useRef<number | null>(null);

  const stepOrder = assembly?.stepOrder ?? [];
  const totalSteps = stepOrder.length;

  // Count completed steps
  const completedCount = Object.values(executionState.stepStates).filter(
    (s) => s.status === "success",
  ).length;

  // Current step number (1-indexed, clamped — WS state may lag behind assembly)
  const currentStepIdx = executionState.currentStepId
    ? stepOrder.indexOf(executionState.currentStepId)
    : -1;
  const currentStepNum = Math.min(Math.max(1, completedCount + 1, currentStepIdx + 1), totalSteps || 1);

  const progressPercent =
    totalSteps > 0 ? Math.min(100, Math.max(0, Math.round((completedCount / totalSteps) * 100))) : 0;

  // Track start time
  useEffect(() => {
    if (
      (executionState.phase === "running" || executionState.phase === "paused") &&
      !startRef.current
    ) {
      startRef.current = executionState.startTime ?? Date.now();
    }
    if (executionState.phase === "idle" || executionState.phase === "complete") {
      startRef.current = null;
    }
  }, [executionState.phase, executionState.startTime]);

  // Elapsed timer
  useEffect(() => {
    if (executionState.phase !== "running" && executionState.phase !== "paused") return;
    const tick = setInterval(() => {
      const start = startRef.current ?? Date.now();
      const secs = Math.floor((Date.now() - start) / 1000);
      const m = Math.floor(secs / 60)
        .toString()
        .padStart(2, "0");
      const s = (secs % 60).toString().padStart(2, "0");
      setElapsed(`${m}:${s}`);
    }, 1000);
    return () => clearInterval(tick);
  }, [executionState.phase]);

  // Progress bar (12 chars wide, clamped to avoid RangeError)
  const filledBlocks = Math.min(12, Math.max(0, Math.round((progressPercent / 100) * 12)));
  const bar = "\u2588".repeat(filledBlocks) + "\u2591".repeat(12 - filledBlocks);

  return (
    <div
      className="absolute bottom-3 left-3 pointer-events-none select-none"
      style={{
        fontFamily: "var(--font-mono, monospace)",
        fontSize: "10px",
        lineHeight: "15px",
        color: "#52525B",
        background: "rgba(250, 250, 250, 0.75)",
        backdropFilter: "blur(4px)",
        borderRadius: "4px",
        padding: "6px 8px",
      }}
    >
      <div>
        Step {currentStepNum} / {totalSteps}
      </div>
      <div>
        {bar} {progressPercent}%
      </div>
      <div>Elapsed: {elapsed}</div>
    </div>
  );
}
