"use client";

// Simple 6-DOF stick-figure robot arm with animated gripper.
// Uses a lightweight "reach toward target" approach — not full IK,
// just enough to look like an arm moving to assembly positions.

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group, Mesh } from "three";
import type { Vec3 } from "@/lib/animation";
import type { ExecutionAnimState } from "@/lib/executionAnimation";

interface RobotArmProps {
  basePosition: Vec3;
  executionAnimRef: React.RefObject<ExecutionAnimState>;
  visible: boolean;
  assemblyRadius: number;
}

const ARM_COLOR = "#C0C0C0";
const JOINT_COLOR = "#A8A8A4";
const GRIPPER_COLOR = "#8C8C88";

// Segment length ratios (fraction of assemblyRadius)
const SEGMENTS = [0.20, 0.18, 0.14, 0.10, 0.08, 0.06];
const JOINT_RADIUS_RATIO = 0.009;
const LINK_RADIUS_RATIO = 0.003;
const BASE_RADIUS_RATIO = 0.025;

// ---------------------------------------------------------------------------
// Animated gripper sub-component (needs its own useFrame for hook rules)
// ---------------------------------------------------------------------------

function GripperEndEffector({
  lr,
  lastLen,
  executionAnimRef,
}: {
  lr: number;
  lastLen: number;
  executionAnimRef: React.RefObject<ExecutionAnimState>;
}) {
  const leftRef = useRef<Mesh>(null);
  const rightRef = useRef<Mesh>(null);
  const gapRef = useRef(1.0);

  const gripperThickness = lr * 1.2;
  const gripperHeight = lastLen * 0.5;
  const gripperDepth = lr * 3;

  useFrame((_, delta) => {
    const phase = executionAnimRef.current?.endEffectorPhase ?? "idle";
    const target = phase === "grasp" ? 0.15 : 1.0;
    gapRef.current += (target - gapRef.current) * Math.min(1, delta * 6);
    const offset = lr * 2 * gapRef.current + lr * 0.5;
    if (leftRef.current) leftRef.current.position.x = offset;
    if (rightRef.current) rightRef.current.position.x = -offset;
  });

  return (
    <group>
      <mesh ref={leftRef} position={[lr * 2.5, 0, 0]}>
        <boxGeometry args={[gripperThickness, gripperHeight, gripperDepth]} />
        <meshStandardMaterial
          color={GRIPPER_COLOR} roughness={0.3} metalness={0.5} transparent opacity={0.6}
        />
      </mesh>
      <mesh ref={rightRef} position={[-lr * 2.5, 0, 0]}>
        <boxGeometry args={[gripperThickness, gripperHeight, gripperDepth]} />
        <meshStandardMaterial
          color={GRIPPER_COLOR} roughness={0.3} metalness={0.5} transparent opacity={0.6}
        />
      </mesh>
      {/* Gripper crossbar */}
      <mesh position={[0, gripperHeight * 0.3, 0]}>
        <boxGeometry args={[lr * 5, lr * 0.8, gripperDepth * 0.8]} />
        <meshStandardMaterial
          color={ARM_COLOR} roughness={0.3} metalness={0.5} transparent opacity={0.6}
        />
      </mesh>
    </group>
  );
}

// ---------------------------------------------------------------------------
// RobotArm
// ---------------------------------------------------------------------------

export function RobotArm({ basePosition, executionAnimRef, visible, assemblyRadius }: RobotArmProps) {
  const groupRef = useRef<Group>(null);
  const jointGroupRefs = useRef<(Group | null)[]>([]);
  const currentEERef = useRef<Vec3>([basePosition[0], basePosition[1] + assemblyRadius, basePosition[2]]);

  // Pre-compute segment lengths from assembly scale
  const segmentLengths = useMemo(
    () => SEGMENTS.map((r) => r * assemblyRadius),
    [assemblyRadius],
  );
  const totalArmLength = useMemo(
    () => segmentLengths.reduce((a, b) => a + b, 0),
    [segmentLengths],
  );
  const jr = JOINT_RADIUS_RATIO * assemblyRadius;
  const lr = LINK_RADIUS_RATIO * assemblyRadius;
  const br = BASE_RADIUS_RATIO * assemblyRadius;

  useFrame((_, delta) => {
    if (!visible || !groupRef.current || !executionAnimRef.current) return;

    const state = executionAnimRef.current;
    const target = state.endEffectorTarget;
    const ee = currentEERef.current;

    // Smooth lerp toward target
    const lerpFactor = Math.min(1, delta * 4);
    ee[0] += (target[0] - ee[0]) * lerpFactor;
    ee[1] += (target[1] - ee[1]) * lerpFactor;
    ee[2] += (target[2] - ee[2]) * lerpFactor;

    // Compute direction from base to end-effector
    const dx = ee[0] - basePosition[0];
    const dy = ee[1] - basePosition[1];
    const dz = ee[2] - basePosition[2];
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

    // Reach ratio (how far the arm extends, 0 = neutral, 1 = fully stretched)
    const reach = Math.min(dist / totalArmLength, 0.95);

    // Distribute the angle chain: base joint points toward target,
    // subsequent joints fold proportionally to (1 - reach)
    const foldAngle = (1 - reach) * Math.PI * 0.4;

    // Yaw: rotate base around Y to point toward target in XZ plane
    const yaw = Math.atan2(dx, dz);

    // Pitch: tilt toward target in the vertical plane
    const horizontalDist = Math.sqrt(dx * dx + dz * dz);
    const pitch = -Math.atan2(dy, horizontalDist);

    // Apply to joint groups
    for (let i = 0; i < SEGMENTS.length; i++) {
      const jg = jointGroupRefs.current[i];
      if (!jg) continue;

      if (i === 0) {
        // Base joint: yaw + main pitch
        jg.rotation.set(pitch + foldAngle * 0.3, yaw, 0);
      } else {
        // Upper joints fold progressively
        const jointFold = foldAngle * (1 - i / SEGMENTS.length) * 0.5;
        jg.rotation.set(jointFold, 0, 0);
      }
    }
  });

  if (!visible) return null;

  // Build a chain of nested groups: each group contains a link + joint sphere,
  // then the next group is positioned at the end of the link.
  function buildChain(depth: number): React.ReactNode {
    if (depth >= SEGMENTS.length) {
      const lastLen = segmentLengths[SEGMENTS.length - 1] ?? lr;
      return (
        <GripperEndEffector
          lr={lr}
          lastLen={lastLen}
          executionAnimRef={executionAnimRef}
        />
      );
    }

    const len = segmentLengths[depth] ?? 0.01;
    // Taper: wider at base (depth 0), narrower toward tip
    const topRadius = lr * Math.max(0.5, 1 - depth * 0.1);
    const bottomRadius = lr * Math.max(0.5, 1 - Math.max(0, depth - 1) * 0.1);

    return (
      <group ref={(el) => { jointGroupRefs.current[depth] = el; }}>
        {/* Joint sphere */}
        <mesh>
          <sphereGeometry args={[jr, 16, 16]} />
          <meshStandardMaterial
            color={JOINT_COLOR} roughness={0.3} metalness={0.5} transparent opacity={0.6}
          />
        </mesh>
        {/* Link cylinder (along local Y axis), tapered */}
        <mesh position={[0, len / 2, 0]}>
          <cylinderGeometry args={[topRadius, bottomRadius, len, 12]} />
          <meshStandardMaterial
            color={ARM_COLOR} roughness={0.3} metalness={0.5} transparent opacity={0.6}
          />
        </mesh>
        {/* Next joint at end of this link */}
        <group position={[0, len, 0]}>
          {buildChain(depth + 1)}
        </group>
      </group>
    );
  }

  return (
    <group ref={groupRef} position={basePosition}>
      {/* Base plate */}
      <mesh>
        <cylinderGeometry args={[br, br * 1.2, br * 0.3, 16]} />
        <meshStandardMaterial
          color={ARM_COLOR} roughness={0.3} metalness={0.5} transparent opacity={0.6}
        />
      </mesh>
      {/* Arm chain starting from base */}
      <group position={[0, br * 0.15, 0]}>
        {buildChain(0)}
      </group>
    </group>
  );
}
