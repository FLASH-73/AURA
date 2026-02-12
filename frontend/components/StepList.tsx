"use client";

import { useEffect, useRef } from "react";
import { useAssembly } from "@/context/AssemblyContext";
import { useExecution } from "@/context/ExecutionContext";
import { StepCard } from "./StepCard";

export function StepList() {
  const { assembly, selectedStepId, selectStep } = useAssembly();
  const { executionState } = useExecution();
  const listRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to active step during execution
  useEffect(() => {
    if (executionState.phase === "running" && activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [executionState.currentStepId, executionState.phase]);

  if (!assembly || assembly.stepOrder.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-[13px] text-text-tertiary">No assembly loaded</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col p-4" ref={listRef}>
      <h2 className="mb-3 text-[14px] font-semibold text-text-primary">
        Assembly Steps
      </h2>
      <div className="flex flex-col gap-1">
        {assembly.stepOrder.map((stepId, index) => {
          const step = assembly.steps[stepId];
          if (!step) return null;
          const runtimeState = executionState.stepStates[stepId];
          if (!runtimeState) return null;
          const isActive = executionState.currentStepId === stepId;

          return (
            <div key={stepId} ref={isActive ? activeRef : undefined}>
              <StepCard
                step={step}
                stepIndex={index + 1}
                runtimeState={runtimeState}
                isSelected={selectedStepId === stepId}
                onClick={() => selectStep(stepId)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
