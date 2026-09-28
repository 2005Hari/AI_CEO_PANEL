"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface WebSocketContextType {
  isConnected: boolean;
  latestEvent: any | null;
}

const WebSocketContext = createContext<WebSocketContextType>({
  isConnected: false,
  latestEvent: null,
});

export function useGlobalWebSocket() {
  return useContext(WebSocketContext);
}

interface WebSocketProviderProps {
  projectId: string | undefined;
  children: ReactNode;
}

export function WebSocketProvider({ projectId, children }: WebSocketProviderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [latestEvent, setLatestEvent] = useState<any | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/ws/${projectId}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`Connected to global WS for project ${projectId}`);
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLatestEvent(data);
      } catch (e) {
        console.error("Failed to parse WS message", e);
      }
    };

    ws.onclose = () => {
      console.log(`Disconnected global WS for project ${projectId}`);
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [projectId]);

  return (
    <WebSocketContext.Provider value={{ isConnected, latestEvent }}>
      {children}
    </WebSocketContext.Provider>
  );
}
