"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AuraWebSocket, type ConnectionState } from "@/lib/ws";

interface WebSocketContextValue {
  connected: boolean;
  connectionState: ConnectionState;
  lastMessage: unknown;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/execution/ws";

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const wsRef = useRef<AuraWebSocket | null>(null);

  useEffect(() => {
    const ws = new AuraWebSocket(WS_URL);
    wsRef.current = ws;

    const unsubscribe = ws.onMessage((data) => {
      // Update connection state only when changed (callback form skips re-render on same value)
      setConnected((prev) => (prev === ws.connected ? prev : ws.connected));
      setConnectionState((prev) => (prev === ws.state ? prev : ws.state));

      // Skip heartbeats — they carry no actionable payload for consumers
      if (
        typeof data === "object" &&
        data !== null &&
        (data as Record<string, unknown>).type === "heartbeat"
      ) {
        return;
      }
      setLastMessage(data);
    });

    ws.connect();
    // Poll connection state for reconnection transitions
    const pollId = setInterval(() => {
      setConnected((prev) => (prev === ws.connected ? prev : ws.connected));
      setConnectionState((prev) => (prev === ws.state ? prev : ws.state));
    }, 1000);

    return () => {
      unsubscribe();
      clearInterval(pollId);
      ws.disconnect();
    };
  }, []);

  const value = useMemo<WebSocketContextValue>(
    () => ({ connected, connectionState, lastMessage }),
    [connected, connectionState, lastMessage],
  );

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket(): WebSocketContextValue {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWebSocket must be used within WebSocketProvider");
  return ctx;
}
