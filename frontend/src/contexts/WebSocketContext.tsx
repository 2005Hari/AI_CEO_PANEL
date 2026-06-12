"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

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

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//localhost:8000/api/v1/ws/${projectId}`;

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
