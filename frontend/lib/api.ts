import type {
  Assembly,
  ExecutionState,
  StepMetrics,
  TrainConfig,
  TrainStatus,
  AssemblyStep,
} from "./types";
import {
  MOCK_ASSEMBLIES,
  MOCK_ASSEMBLY,
  MOCK_EXECUTION_STATE,
  MOCK_STEP_METRICS,
} from "./mock-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T = void>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<T>;
}

async function patch<T = void>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<T>;
}

// Fetcher with mock fallback — used by SWR
async function withMockFallback<T>(fetcher: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fetcher();
  } catch {
    return fallback;
  }
}

export const api = {
  // Assembly
  getAssemblies: () =>
    withMockFallback(() => get<Assembly[]>("/assemblies"), MOCK_ASSEMBLIES),
  getAssembly: (id: string) =>
    withMockFallback(() => get<Assembly>(`/assemblies/${id}`), MOCK_ASSEMBLY),

  // Execution
  startAssembly: (id: string) => post("/execution/start", { assembly_id: id }),
  pauseExecution: () => post("/execution/pause"),
  stopExecution: () => post("/execution/stop"),
  intervene: () => post("/execution/intervene"),
  getExecutionState: () =>
    withMockFallback(
      () => get<ExecutionState>("/execution/state"),
      MOCK_EXECUTION_STATE,
    ),

  // Step updates
  updateStep: (assemblyId: string, stepId: string, data: Partial<AssemblyStep>) =>
    patch(`/assemblies/${assemblyId}/steps/${stepId}`, data),

  // Teleop
  startTeleop: (arms: string[]) => post("/teleop/start", { arms }),
  stopTeleop: () => post("/teleop/stop"),

  // Recording
  startRecording: (stepId: string) => post(`/recording/step/${stepId}/start`),
  stopRecording: () => post("/recording/stop"),

  // Training
  trainStep: (stepId: string, config: TrainConfig) =>
    post<TrainStatus>(`/training/step/${stepId}/train`, config),
  getTrainingStatus: (jobId: string) =>
    get<TrainStatus>(`/training/jobs/${jobId}`),

  // Analytics
  getStepMetrics: (assemblyId: string) =>
    withMockFallback(
      () => get<StepMetrics[]>(`/analytics/${assemblyId}/steps`),
      Object.values(MOCK_STEP_METRICS),
    ),
};
