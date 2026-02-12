"use client";

import { AreaChart, Area, ResponsiveContainer } from "recharts";

interface MiniChartProps {
  runs: { success: boolean; durationMs: number; timestamp: number }[];
}

export function MiniChart({ runs }: MiniChartProps) {
  const data = runs.map((r, i) => ({
    index: i,
    value: r.success ? 1 : 0,
    durationMs: r.durationMs,
  }));

  return (
    <div className="h-[60px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E05A1A" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#E05A1A" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke="#E05A1A"
            strokeWidth={1.5}
            fill="url(#chartGradient)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
