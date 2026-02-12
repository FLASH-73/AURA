"use client";

import { useExecution } from "@/context/ExecutionContext";
import { ActionButton } from "./ActionButton";

export function RunControls() {
  const {
    executionState,
    startExecution,
    pauseExecution,
    resumeExecution,
    stopExecution,
    intervene,
  } = useExecution();

  const { phase } = executionState;
  const isIdle = phase === "idle" || phase === "complete";
  const isRunning = phase === "running";
  const isPaused = phase === "paused";

  return (
    <div className="flex items-center gap-2">
      {isPaused ? (
        <ActionButton variant="primary" onClick={resumeExecution}>
          Resume
        </ActionButton>
      ) : (
        <ActionButton
          variant="primary"
          onClick={startExecution}
          disabled={!isIdle}
        >
          Start
        </ActionButton>
      )}

      <ActionButton
        variant="secondary"
        onClick={pauseExecution}
        disabled={!isRunning}
      >
        Pause
      </ActionButton>

      <ActionButton
        variant="secondary"
        onClick={intervene}
        disabled={!isRunning}
      >
        Intervene
      </ActionButton>

      <ActionButton
        variant="danger"
        onClick={stopExecution}
        disabled={isIdle}
      >
        Stop
      </ActionButton>

      <div className="ml-2 h-6 w-px bg-bg-tertiary" />

      <ActionButton variant="danger" className="ml-1 font-bold">
        E-STOP
      </ActionButton>
    </div>
  );
}
