"use client";

import { Grid, ContactShadows } from "@react-three/drei";

interface GroundPlaneProps {
  groundY?: number;
  cellSize?: number;
  sectionSize?: number;
}

export function GroundPlane({
  groundY = -0.02,
  cellSize = 0.02,
  sectionSize = 0.1,
}: GroundPlaneProps) {
  return (
    <group>
      <Grid
        args={[2, 2]}
        cellSize={cellSize}
        cellColor="#EDECE9"
        sectionSize={sectionSize}
        sectionColor="#DEDDD9"
        fadeDistance={sectionSize * 8}
        fadeStrength={1.2}
        infiniteGrid
        position={[0, groundY, 0]}
      />
      <ContactShadows
        position={[0, groundY + 0.001, 0]}
        opacity={0.35}
        scale={sectionSize * 6}
        blur={2.5}
        far={sectionSize * 2}
      />
    </group>
  );
}
