"use client";

import { useCallback, useState } from "react";
import { useExecution } from "@/context/ExecutionContext";
import { ActionButton } from "./ActionButton";
import { EstopBanner } from "./EstopBanner";

export function RunControls() {
  const {
    executionState,
    startExecution,
    pauseExecution,
    resumeExecution,
    stopExecution,
    emergencyStop,
    intervene,
  } = useExecution();

  const { phase } = executionState;
  const isIdle = phase === "idle" || phase === "complete";
  const isRunning = phase === "running";
  const isPaused = phase === "paused";

  const [estopFired, setEstopFired] = useState(false);

  const handleEstop = useCallback(() => {
    emergencyStop();
    setEstopFired(true);
  }, [emergencyStop]);

  return (
    <>
      <div className="flex items-center gap-2">
        {isRunning ? (
          <span className="inline-flex items-center gap-2 rounded-md bg-status-running px-4 py-2 text-[13px] font-semibold text-white">
            <span className="h-[5px] w-[5px] animate-pulse rounded-full bg-white" />
            Running
          </span>
        ) : isPaused ? (
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
          variant="ghost"
          onClick={stopExecution}
          disabled={isIdle}
        >
          Stop
        </ActionButton>

        <div className="ml-2 h-6 w-px bg-bg-tertiary" />

        <ActionButton variant="danger" className="ml-1 font-bold" onClick={handleEstop}>
          E-STOP
        </ActionButton>
      </div>

      <EstopBanner visible={estopFired} onDismiss={() => setEstopFired(false)} />
    </>
  );
}
