"use client";

import { useCallback, useState } from "react";
import type { Assembly } from "@/lib/types";
import { useAssembly } from "@/context/AssemblyContext";
import { useExecution } from "@/context/ExecutionContext";
import { useConnectionStatus } from "@/lib/hooks";
import { RunControls } from "./RunControls";
import { UploadDialog } from "./UploadDialog";

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function ConnectionIndicator() {
  const { isConnected } = useConnectionStatus();
  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`h-2 w-2 rounded-full ${isConnected ? "bg-status-success" : "bg-status-error"}`}
      />
      <span className="text-[11px] text-text-tertiary">
        {isConnected ? "Connected" : "Offline"}
      </span>
    </div>
  );
}

export function TopBar() {
  const { assemblies, assembly, selectAssembly, refreshAssemblies } = useAssembly();
  const { executionState } = useExecution();
  const [uploadOpen, setUploadOpen] = useState(false);

  const showTime = executionState.phase !== "idle";
  const timeDisplay = showTime ? formatTime(executionState.elapsedMs) : "--:--";

  const handleUploadSuccess = useCallback(
    (newAssembly: Assembly) => {
      setUploadOpen(false);
      refreshAssemblies();
      selectAssembly(newAssembly.id);
    },
    [refreshAssemblies, selectAssembly],
  );

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-bg-tertiary px-6">
      {/* Left: wordmark + assembly selector + upload + connection status */}
      <div className="flex items-center gap-4">
        <span className="text-[18px] font-semibold tracking-[0.05em] text-accent">
          AURA
        </span>
        <div className="flex items-center gap-1.5">
          <select
            value={assembly?.id ?? ""}
            onChange={(e) => selectAssembly(e.target.value)}
            className="rounded-md border border-bg-tertiary bg-bg-secondary px-3 py-1.5 text-[13px] text-text-primary outline-none focus:ring-2 focus:ring-accent"
          >
            {assemblies.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setUploadOpen(true)}
            className="rounded-md border border-bg-tertiary bg-bg-secondary px-2 py-1.5 text-[13px] text-text-secondary hover:text-text-primary"
          >
            +
          </button>
        </div>
        <ConnectionIndicator />
      </div>

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={handleUploadSuccess}
      />

      {/* Center: cycle time */}
      <div className="absolute left-1/2 -translate-x-1/2">
        <span className="font-mono text-[28px] font-semibold tabular-nums text-text-primary">
          {timeDisplay}
        </span>
      </div>

      {/* Right: run controls */}
      <RunControls />
    </header>
  );
}
