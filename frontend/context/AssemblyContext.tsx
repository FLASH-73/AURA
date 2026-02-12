"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import useSWR from "swr";
import type { Assembly, AssemblySummary } from "@/lib/types";
import { MOCK_ASSEMBLY, MOCK_SUMMARIES } from "@/lib/mock-data";
import { api } from "@/lib/api";

interface AssemblyContextValue {
  assemblies: AssemblySummary[];
  assembly: Assembly | null;
  isLoading: boolean;
  selectedStepId: string | null;
  selectStep: (stepId: string | null) => void;
  selectAssembly: (assemblyId: string) => void;
  refreshAssemblies: () => void;
}

const AssemblyContext = createContext<AssemblyContextValue | null>(null);

export function AssemblyProvider({ children }: { children: ReactNode }) {
  const [assemblyId, setAssemblyId] = useState<string>(
    MOCK_SUMMARIES[0]?.id ?? "",
  );
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  const { data: assemblies = MOCK_SUMMARIES, mutate: mutateAssemblies } =
    useSWR<AssemblySummary[]>(
      "/assemblies",
      api.fetchAssemblySummaries,
      { fallbackData: MOCK_SUMMARIES },
    );

  const refreshAssemblies = useCallback(() => {
    void mutateAssemblies();
  }, [mutateAssemblies]);

  const { data: assembly = null, isLoading } = useSWR<Assembly>(
    assemblyId ? `/assemblies/${assemblyId}` : null,
    () => api.fetchAssembly(assemblyId),
    { fallbackData: assemblyId === MOCK_ASSEMBLY.id ? MOCK_ASSEMBLY : undefined },
  );

  const selectStep = useCallback((stepId: string | null) => {
    setSelectedStepId(stepId);
  }, []);

  const selectAssembly = useCallback(
    (id: string) => {
      setAssemblyId(id);
      setSelectedStepId(null);
    },
    [],
  );

  const value = useMemo<AssemblyContextValue>(
    () => ({
      assemblies,
      assembly,
      isLoading,
      selectedStepId,
      selectStep,
      selectAssembly,
      refreshAssemblies,
    }),
    [assemblies, assembly, isLoading, selectedStepId, selectStep, selectAssembly, refreshAssemblies],
  );

  return (
    <AssemblyContext.Provider value={value}>{children}</AssemblyContext.Provider>
  );
}

export function useAssembly(): AssemblyContextValue {
  const ctx = useContext(AssemblyContext);
  if (!ctx) throw new Error("useAssembly must be used within AssemblyProvider");
  return ctx;
}
