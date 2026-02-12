"use client";

import type { ReactNode } from "react";
import { WebSocketProvider } from "@/context/WebSocketContext";
import { AssemblyProvider } from "@/context/AssemblyContext";
import { ExecutionProvider } from "@/context/ExecutionContext";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <WebSocketProvider>
      <AssemblyProvider>
        <ExecutionProvider>{children}</ExecutionProvider>
      </AssemblyProvider>
    </WebSocketProvider>
  );
}
