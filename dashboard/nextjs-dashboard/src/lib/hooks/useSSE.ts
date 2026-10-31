"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query/queryKeys";

type ConnectionStatus = "connected" | "connecting" | "disconnected";

interface MemoryAddedEvent {
  memory_id: string;
  content: string;
  memory_type?: string;
  memory_concept?: string;
  created_at: string;
}

interface MemoryUpdatedEvent {
  memory_id: string;
  content?: string;
  memory_type?: string;
  memory_concept?: string;
  updated_at: string;
}

interface MemoryDeletedEvent {
  memory_id: string;
}

interface StatsUpdatedEvent {
  total_memories: number;
  total_sessions: number;
  timestamp: string;
}

export function useSSE() {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const retryCount = useRef(0);
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate backoff delay with max of 30 seconds
  const getBackoffDelay = (attempt: number): number => {
    const delays = [1000, 2000, 4000, 8000, 30000]; // 1s, 2s, 4s, 8s, 30s
    return delays[Math.min(attempt, delays.length - 1)];
  };

  const connect = useCallback(function connectStream() {
    if (eventSourceRef.current?.readyState === EventSource.OPEN) {
      return;
    }

    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setStatus("connecting");

    try {
      const eventSource = new EventSource("http://localhost:8000/api/stream");
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setStatus("connected");
        retryCount.current = 0;
      };

      eventSource.addEventListener("keepalive", () => {
        // Keepalive event to maintain connection
        // No action needed, just confirms connection is alive
      });

      eventSource.addEventListener("memory_added", (e) => {
        try {
          const data = JSON.parse(e.data) as MemoryAddedEvent;

          // Invalidate memories list to trigger refetch
          queryClient.invalidateQueries({
            queryKey: queryKeys.memories.lists(),
          });

          // Optionally set the new memory in cache
          queryClient.setQueryData(
            queryKeys.memories.detail(data.memory_id),
            { ...data, id: data.memory_id }
          );
        } catch (error) {
          console.error("Failed to parse memory_added event:", error);
        }
      });

      eventSource.addEventListener("memory_updated", (e) => {
        try {
          const data = JSON.parse(e.data) as MemoryUpdatedEvent;

          // Update specific memory in cache
          queryClient.setQueryData(
            queryKeys.memories.detail(data.memory_id),
            (oldData: unknown) => {
              if (oldData && typeof oldData === "object" && "id" in oldData) {
                return { ...oldData, ...data };
              }
              return oldData;
            }
          );

          // Invalidate list to reflect changes
          queryClient.invalidateQueries({
            queryKey: queryKeys.memories.lists(),
          });
        } catch (error) {
          console.error("Failed to parse memory_updated event:", error);
        }
      });

      eventSource.addEventListener("memory_deleted", (e) => {
        try {
          const data = JSON.parse(e.data) as MemoryDeletedEvent;

          // Remove from cache
          queryClient.removeQueries({
            queryKey: queryKeys.memories.detail(data.memory_id),
          });

          // Invalidate list
          queryClient.invalidateQueries({
            queryKey: queryKeys.memories.lists(),
          });
        } catch (error) {
          console.error("Failed to parse memory_deleted event:", error);
        }
      });

      eventSource.addEventListener("stats_updated", (e) => {
        try {
          JSON.parse(e.data) as StatsUpdatedEvent;

          // Invalidate stats queries
          queryClient.invalidateQueries({
            queryKey: queryKeys.analytics.systemStats(),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.analytics.structuredStats(),
          });
        } catch (error) {
          console.error("Failed to parse stats_updated event:", error);
        }
      });

      eventSource.onerror = (error) => {
        console.error("SSE connection error:", error);
        setStatus("disconnected");

        // Close the failed connection
        eventSource.close();

        // Reconnect with exponential backoff
        const delay = getBackoffDelay(retryCount.current);
        retryCount.current += 1;

        reconnectTimeoutRef.current = setTimeout(() => {
          connectStream();
        }, delay);
      };
    } catch (error) {
      console.error("Failed to create SSE connection:", error);
      setStatus("disconnected");

      // Retry connection
      const delay = getBackoffDelay(retryCount.current);
      retryCount.current += 1;

      reconnectTimeoutRef.current = setTimeout(() => {
        connectStream();
      }, delay);
    }
  }, [queryClient]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setStatus("disconnected");
    retryCount.current = 0;
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    status,
    isConnected: status === "connected",
    isConnecting: status === "connecting",
    reconnect: connect,
    disconnect,
  };
}
