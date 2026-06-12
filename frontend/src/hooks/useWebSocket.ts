import { useEffect, useRef, useState } from 'react';

export function useWebSocket(projectId: string | undefined, onMessage: (msg: any) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!projectId) return;

    // Use ws:// for local dev, wss:// for production if needed
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//localhost:8000/ws/${projectId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`Connected to WS for project ${projectId}`);
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error("Failed to parse WS message", e);
      }
    };

    ws.onclose = () => {
      console.log(`Disconnected WS for project ${projectId}`);
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [projectId, onMessage]);

  return { isConnected };
}
