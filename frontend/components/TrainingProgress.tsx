"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import type { TrainStatus } from "@/lib/types";
import { api } from "@/lib/api";
import { ActionButton } from "./ActionButton";

interface TrainingProgressProps {
  stepId: string;
  handler: string;
  policyId: string | null;
}

export function TrainingProgress({ stepId, handler, policyId }: TrainingProgressProps) {
  const [status, setStatus] = useState<TrainStatus | null>(null);
  const [lossHistory, setLossHistory] = useState<{ step: number; loss: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>(null);

  // Stop polling on unmount or step change
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [stepId]);

  const startPolling = useCallback((jobId: string) => {
    setLossHistory([]);
    let pollCount = 0;

    pollRef.current = setInterval(async () => {
      try {
        const s = await api.getTrainingStatus(jobId);
        setStatus(s);
        pollCount++;
        if (s.loss != null) {
          setLossHistory((prev) => [...prev, { step: pollCount, loss: s.loss! }]);
        }
        if (s.state === "complete" || s.state === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
          if (s.state === "failed") setError("Training failed");
        }
      } catch {
        // Polling error — keep trying
      }
    }, 2000);
  }, []);

  const handleTrain = useCallback(async () => {
    setError(null);
    setStatus(null);
    try {
      const result = await api.trainStep(stepId, { architecture: "act", numSteps: 10_000 });
      setStatus(result);
      startPolling(result.jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start training");
    }
  }, [stepId, startPolling]);

  if (handler !== "policy") return null;

  const isTraining = status?.state === "queued" || status?.state === "training";
  const isComplete = status?.state === "complete";

  return (
    <div className="flex flex-col gap-2">
      {isComplete ? (
        <div className="flex items-center gap-2">
          <div className="h-2.5 w-2.5 rounded-full bg-status-success" />
          <span className="text-[13px] font-medium text-status-success">Policy trained</span>
          {policyId && (
            <span className="font-mono text-[11px] text-text-tertiary">{policyId}</span>
          )}
        </div>
      ) : (
        <ActionButton
          variant="primary"
          disabled={isTraining}
          onClick={() => void handleTrain()}
        >
          {isTraining
            ? `Training... ${Math.round(status?.progress ?? 0)}%`
            : "Train"}
        </ActionButton>
      )}

      {/* Loss sparkline during training */}
      {isTraining && lossHistory.length > 1 && (
        <div className="h-[40px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={lossHistory} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2574D4" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#2574D4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="loss"
                stroke="#2574D4"
                strokeWidth={1.5}
                fill="url(#lossGradient)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2">
          <p className="text-[11px] text-status-error">{error}</p>
          <ActionButton
            variant="secondary"
            className="!px-2 !py-0.5 !text-[11px]"
            onClick={() => void handleTrain()}
          >
            Retry
          </ActionButton>
        </div>
      )}
    </div>
  );
}
