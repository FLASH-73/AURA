"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Assembly } from "@/lib/types";
import { MOCK_ASSEMBLIES } from "@/lib/mock-data";

interface AssemblyContextValue {
  assemblies: Assembly[];
  assembly: Assembly | null;
  selectedStepId: string | null;
  selectStep: (stepId: string | null) => void;
  selectAssembly: (assemblyId: string) => void;
}

const AssemblyContext = createContext<AssemblyContextValue | null>(null);

export function AssemblyProvider({ children }: { children: ReactNode }) {
  const [assemblies] = useState<Assembly[]>(MOCK_ASSEMBLIES);
  const [assemblyId, setAssemblyId] = useState<string>(
    MOCK_ASSEMBLIES[0]?.id ?? "",
  );
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  const assembly = useMemo(
    () => assemblies.find((a) => a.id === assemblyId) ?? null,
    [assemblies, assemblyId],
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
    () => ({ assemblies, assembly, selectedStepId, selectStep, selectAssembly }),
    [assemblies, assembly, selectedStepId, selectStep, selectAssembly],
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
