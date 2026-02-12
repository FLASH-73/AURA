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
import { ManusWebSocket } from "@/lib/ws";

interface WebSocketContextValue {
  connected: boolean;
  lastMessage: unknown;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const wsRef = useRef<ManusWebSocket | null>(null);

  useEffect(() => {
    const ws = new ManusWebSocket(WS_URL);
    wsRef.current = ws;

    const unsubscribe = ws.onMessage((data) => {
      setLastMessage(data);
      setConnected(ws.connected);
    });

    ws.connect();
    // Poll connection state since mock mode sets it synchronously
    const pollId = setInterval(() => setConnected(ws.connected), 1000);

    return () => {
      unsubscribe();
      clearInterval(pollId);
      ws.disconnect();
    };
  }, []);

  const value = useMemo<WebSocketContextValue>(
    () => ({ connected, lastMessage }),
    [connected, lastMessage],
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
