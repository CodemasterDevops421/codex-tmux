import { useEffect, useRef, useState } from "react";
import type { Event } from "./api";

export function useEventStream() {
  const [events, setEvents] = useState<Event[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/events`);
    wsRef.current = ws;
    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as Event;
        setEvents((prev) => [event, ...prev].slice(0, 500));
      } catch {
        return;
      }
    };
    return () => {
      ws.close();
    };
  }, []);

  return { events };
}
