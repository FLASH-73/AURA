"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import useSWR, { mutate as globalMutate } from "swr";
import type { Assembly, AssemblyStep, AssemblySummary } from "@/lib/types";
import { api } from "@/lib/api";

interface AssemblyContextValue {
  assemblies: AssemblySummary[];
  assembly: Assembly | null;
  isLoading: boolean;
  selectedStepId: string | null;
  selectStep: (stepId: string | null) => void;
  selectAssembly: (assemblyId: string, data?: Assembly) => void;
  refreshAssemblies: () => void;
  deleteAssembly: (id: string) => Promise<void>;
  updateStep: (stepId: string, data: Partial<AssemblyStep>) => Promise<void>;
}

const AssemblyContext = createContext<AssemblyContextValue | null>(null);

export function AssemblyProvider({ children }: { children: ReactNode }) {
  const [assemblyId, setAssemblyId] = useState<string>("");
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  const { data: assemblies = [], mutate: mutateAssemblies } =
    useSWR<AssemblySummary[]>("/assemblies", api.fetchAssemblySummaries);

  const refreshAssemblies = useCallback(() => {
    void mutateAssemblies();
  }, [mutateAssemblies]);

  // Auto-select first assembly from server on initial load
  const autoSelected = useRef(false);
  useEffect(() => {
    const first = assemblies[0];
    if (autoSelected.current || !first) return;
    autoSelected.current = true;
    setAssemblyId(first.id);
  }, [assemblies]);

  const { data: assembly = null, isLoading } = useSWR<Assembly>(
    assemblyId ? `/assemblies/${assemblyId}` : null,
    () => api.fetchAssembly(assemblyId),
  );

  const selectStep = useCallback((stepId: string | null) => {
    setSelectedStepId(stepId);
  }, []);

  const selectAssembly = useCallback(
    (id: string, data?: Assembly) => {
      if (id === assemblyId) return;
      // Best-effort stop any running execution when switching assemblies
      api.stopExecution().catch(() => {});
      if (data) {
        void globalMutate(`/assemblies/${id}`, data, false);
      }
      setAssemblyId(id);
      setSelectedStepId(null);
    },
    [assemblyId],
  );

  const deleteAssembly = useCallback(
    async (id: string) => {
      await api.deleteAssembly(id);
      const updated = await mutateAssemblies();
      if (id === assemblyId) {
        const remaining = updated?.filter((a) => a.id !== id);
        setAssemblyId(remaining?.[0]?.id ?? "");
        setSelectedStepId(null);
      }
    },
    [assemblyId, mutateAssemblies],
  );

  const updateStep = useCallback(
    async (stepId: string, data: Partial<AssemblyStep>) => {
      if (!assembly) return;
      const prev = assembly;
      const swrKey = `/assemblies/${assembly.id}`;

      // Optimistic: merge partial into step (existing step has all required fields)
      const updatedStep: AssemblyStep = { ...assembly.steps[stepId], ...data } as AssemblyStep;
      const optimistic: Assembly = {
        ...assembly,
        steps: { ...assembly.steps, [stepId]: updatedStep },
      };
      void globalMutate(swrKey, optimistic, false);

      try {
        await api.updateStep(assembly.id, stepId, data);
        void globalMutate(swrKey); // revalidate from server
      } catch {
        void globalMutate(swrKey, prev, false); // rollback
        throw new Error("Failed to save");
      }
    },
    [assembly],
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
      deleteAssembly,
      updateStep,
    }),
    [assemblies, assembly, isLoading, selectedStepId, selectStep, selectAssembly, refreshAssemblies, deleteAssembly, updateStep],
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
