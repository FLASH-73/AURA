"use client";

import { useMemo } from "react";
import { Grid, ContactShadows, Line } from "@react-three/drei";

interface GroundPlaneProps {
  groundY?: number;
  cellSize?: number;
  sectionSize?: number;
  surfaceWidth?: number;
  surfaceDepth?: number;
  assemblyRadius?: number;
}

/** Generates points for a circle in the XZ plane at the given Y height. */
function circlePoints(
  radius: number,
  y: number,
  segments: number,
): [number, number, number][] {
  const pts: [number, number, number][] = [];
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * Math.PI * 2;
    pts.push([Math.cos(angle) * radius, y, Math.sin(angle) * radius]);
  }
  return pts;
}

export function GroundPlane({
  groundY = -0.02,
  cellSize = 0.02,
  sectionSize = 0.1,
  surfaceWidth = 0.5,
  surfaceDepth = 0.4,
  assemblyRadius,
}: GroundPlaneProps) {
  const surfaceZ = surfaceDepth / 4;

  const { edgePoints, ringPoints } = useMemo(() => {
    const halfW = surfaceWidth / 2;
    const halfD = surfaceDepth / 2;
    const sZ = surfaceDepth / 4;
    const edges: [number, number, number][] = [
      [-halfW, groundY, sZ - halfD],
      [halfW, groundY, sZ - halfD],
      [halfW, groundY, sZ + halfD],
      [-halfW, groundY, sZ + halfD],
      [-halfW, groundY, sZ - halfD],
    ];
    const ring =
      assemblyRadius && assemblyRadius > 0
        ? circlePoints(assemblyRadius * 1.2, groundY + 0.0005, 64)
        : null;
    return { edgePoints: edges, ringPoints: ring };
  }, [surfaceWidth, surfaceDepth, groundY, assemblyRadius]);

  return (
    <group>
      {/* Background grid — softened, infinite for spatial context */}
      <Grid
        args={[2, 2]}
        cellSize={cellSize}
        cellColor="#E8E8E8"
        sectionSize={sectionSize}
        sectionColor="#DCDCE0"
        fadeDistance={sectionSize * 4}
        fadeStrength={2}
        infiniteGrid
        position={[0, groundY, 0]}
      />

      {/* Soft shadow catcher below work surface */}
      <mesh position={[0, groundY - 0.001, surfaceZ]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[surfaceWidth * 1.5, surfaceDepth * 1.5]} />
        <meshStandardMaterial color="#D8D6D1" roughness={0.95} transparent opacity={0.3} />
      </mesh>

      {/* Work surface — bounded table rectangle */}
      <mesh
        position={[0, groundY, surfaceZ]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[surfaceWidth, surfaceDepth]} />
        <meshStandardMaterial color="#E8E6E1" roughness={0.85} metalness={0.05} />
      </mesh>

      {/* Surface edge lines */}
      <Line points={edgePoints} color="#C4C2BD" lineWidth={1} />

      {/* Contact shadows — covers work surface */}
      <ContactShadows
        position={[0, groundY + 0.001, surfaceZ]}
        opacity={0.35}
        scale={Math.max(surfaceWidth, surfaceDepth) * 1.2}
        blur={1.8}
        far={sectionSize * 3}
        resolution={512}
      />

      {/* Center crosshair */}
      <Line
        points={[[-0.012, groundY + 0.001, 0], [0.012, groundY + 0.001, 0]]}
        color="#BEBBB5"
        lineWidth={1}
      />
      <Line
        points={[[0, groundY + 0.001, -0.012], [0, groundY + 0.001, 0.012]]}
        color="#BEBBB5"
        lineWidth={1}
      />

      {/* Optional assembly zone indicator */}
      {ringPoints && (
        <Line
          points={ringPoints}
          color="#C8C5BC"
          lineWidth={1.5}
          dashed
          dashSize={0.008}
          gapSize={0.008}
        />
      )}
    </group>
  );
}
