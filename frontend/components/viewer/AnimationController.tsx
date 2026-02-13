"use client";

// Renderless R3F component — lives inside <Canvas>, drives all per-frame
// animation via useFrame. Writes computed per-part render state to a shared
// ref that PartMesh components read from.

import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Part } from "@/lib/types";
import {
  type AnimationPhase,
  type AnimationState,
  type PartRenderState,
  type Vec3,
  tickPhase,
  computeExplodeOffset,
  computeCentroid,
  computeAssemblyRadius,
  computePartAnimation,
  easeInOut,
  stepToScrubber,
  TIMING,
} from "@/lib/animation";

interface AnimationControllerProps {
  parts: Part[];
  stepOrder: string[];
  steps: Record<string, { partIds: string[] }>;
  exploded: boolean;
  animStateRef: React.RefObject<AnimationState>;
  renderStatesRef: React.RefObject<Record<string, PartRenderState>>;
  scrubberProgressRef: React.RefObject<number>;
  onPhaseChange: (phase: AnimationPhase) => void;
}

export function AnimationController({
  parts,
  stepOrder,
  steps,
  exploded,
  animStateRef,
  renderStatesRef,
  scrubberProgressRef,
  onPhaseChange,
}: AnimationControllerProps) {
  const centroidRef = useRef<Vec3>([0, 0, 0]);
  const radiusRef = useRef(0.1);
  const explodeOffsetsRef = useRef<Record<string, Vec3>>({});
  const explodeTRef = useRef(0);

  // Recompute when parts change
  useEffect(() => {
    centroidRef.current = computeCentroid(parts);
    radiusRef.current = computeAssemblyRadius(parts, centroidRef.current);
    const offsets: Record<string, Vec3> = {};
    for (const p of parts) {
      offsets[p.id] = computeExplodeOffset(p, centroidRef.current, radiusRef.current);
    }
    explodeOffsetsRef.current = offsets;
  }, [parts]);

  useFrame((_, delta) => {
    const prev = animStateRef.current;
    if (!prev) return;

    // 1. Tick phase machine forward
    const next = tickPhase(prev, delta, parts.length, stepOrder.length);
    if (next.phase !== prev.phase) {
      onPhaseChange(next.phase);
    }
    // Mutate ref directly — no setState for 60fps perf
    Object.assign(animStateRef.current, next);

    // 2. Compute explode interpolation
    if (next.phase === "demo_explode") {
      explodeTRef.current = easeInOut(next.phaseTime / TIMING.DEMO_EXPLODE);
    } else if (next.phase === "demo_assemble" || next.phase === "playing") {
      // Collapse back when assembling
      explodeTRef.current = Math.max(0, explodeTRef.current - delta * 3);
    } else if (next.phase === "idle" || next.phase === "scrubbing") {
      // Smooth toggle
      const target = exploded ? 1 : 0;
      explodeTRef.current += (target - explodeTRef.current) * Math.min(1, delta * 5);
    } else {
      // fadein / hold — no explode
      explodeTRef.current = Math.max(0, explodeTRef.current - delta * 5);
    }

    // 3. Compute per-part render state
    const eT = explodeTRef.current;
    const result: Record<string, PartRenderState> = {};

    for (const part of parts) {
      const anim = computePartAnimation(part, next, stepOrder, steps, radiusRef.current);
      const explodeOff = explodeOffsetsRef.current[part.id] ?? [0, 0, 0];

      result[part.id] = {
        position: [
          anim.position[0] + explodeOff[0] * eT,
          anim.position[1] + explodeOff[1] * eT,
          anim.position[2] + explodeOff[2] * eT,
        ],
        opacity: anim.opacity,
        visualState: anim.visualState,
      };
    }

    renderStatesRef.current = result;

    // 4. Scrubber progress (for the HTML timeline overlay)
    if (next.phase === "playing" || next.phase === "demo_assemble") {
      scrubberProgressRef.current = stepToScrubber(
        next.stepIndex,
        next.stepProgress,
        stepOrder.length,
      );
    }
  });

  return null;
}
