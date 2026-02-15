"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { api } from "@/lib/api";
import { ActionButton } from "./ActionButton";

interface RecordingControlsProps {
  stepId: string;
  assemblyId: string;
}

const TELEOP_SWR_KEY = "/teleop/state";

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function RecordingControls({ stepId, assemblyId }: RecordingControlsProps) {
  const [active, setActive] = useState(false);
  const [teleopActive, setTeleopActive] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>(null);
  const { mutate } = useSWRConfig();

  const demosKey = `/recording/demos/${assemblyId}/${stepId}`;
  const { data: demos } = useSWR(demosKey, () => api.getDemos(assemblyId, stepId));
  const demoCount = demos?.length ?? 0;
  const totalDurationMs = demos?.reduce((sum, d) => sum + d.durationMs, 0) ?? 0;

  // Elapsed timer
  useEffect(() => {
    if (active && startTime) {
      timerRef.current = setInterval(() => {
        setElapsed(Date.now() - startTime);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [active, startTime]);

  // Reset when step changes
  useEffect(() => {
    setActive(false);
    setTeleopActive(false);
    setStartTime(null);
    setElapsed(0);
    setError(null);
  }, [stepId]);

  const handleStart = useCallback(async () => {
    setError(null);
    // Start teleop first — if it fails, still try recording (mock mode)
    try {
      await api.startTeleop([]);
      setTeleopActive(true);
      void mutate(TELEOP_SWR_KEY);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Teleop start failed");
    }
    // Start recording regardless of teleop result
    try {
      await api.startRecording(stepId);
      setActive(true);
      setStartTime(Date.now());
      setElapsed(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start recording");
    }
  }, [stepId, mutate]);

  const handleStop = useCallback(async () => {
    try {
      await api.stopRecording();
    } catch {
      // Stop may fail if backend is unavailable
    }
    try {
      await api.stopTeleop();
    } catch {
      // Teleop stop may fail
    }
    setActive(false);
    setTeleopActive(false);
    setStartTime(null);
    void mutate(demosKey);
    void mutate(TELEOP_SWR_KEY);
  }, [demosKey, mutate]);

  const handleDiscard = useCallback(async () => {
    try {
      await api.discardRecording();
    } catch {
      // Discard may fail if backend is unavailable
    }
    try {
      await api.stopTeleop();
    } catch {
      // Teleop stop may fail
    }
    setActive(false);
    setTeleopActive(false);
    setStartTime(null);
    void mutate(demosKey);
    void mutate(TELEOP_SWR_KEY);
  }, [demosKey, mutate]);

  return (
    <div>
      {active ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            {teleopActive && (
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-1.5 animate-pulse-subtle rounded-full bg-status-success" />
                <span className="text-[9px] font-medium uppercase tracking-[0.06em] text-text-tertiary">
                  Teleop
                </span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-status-error" />
              <span className="text-[13px] font-medium text-status-error">Recording...</span>
            </div>
            <span className="font-mono text-[13px] tabular-nums text-text-secondary">
              {formatElapsed(elapsed)}
            </span>
          </div>
          <div className="flex gap-2">
            <ActionButton variant="primary" onClick={() => void handleStop()}>
              Stop Recording
            </ActionButton>
            <ActionButton variant="danger" onClick={() => void handleDiscard()}>
              Discard
            </ActionButton>
          </div>
        </div>
      ) : (
        <ActionButton variant="primary" onClick={() => void handleStart()}>
          Record Demo
        </ActionButton>
      )}

      {error && (
        <p className="mt-1 text-[11px] text-status-error">{error}</p>
      )}

      <p className="mt-1.5 text-[11px] text-text-tertiary">
        {demoCount} demo{demoCount !== 1 ? "s" : ""} recorded
        {demoCount > 0 && ` \u00B7 ${formatElapsed(totalDurationMs)}`}
      </p>
    </div>
  );
}
