"use client";

import type { ReactNode } from "react";
import { SWRConfig } from "swr";
import { WebSocketProvider } from "@/context/WebSocketContext";
import { AssemblyProvider } from "@/context/AssemblyContext";
import { ExecutionProvider } from "@/context/ExecutionContext";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SWRConfig value={{ revalidateOnFocus: false, shouldRetryOnError: false }}>
      <WebSocketProvider>
        <AssemblyProvider>
          <ExecutionProvider>{children}</ExecutionProvider>
        </AssemblyProvider>
      </WebSocketProvider>
    </SWRConfig>
  );
}
