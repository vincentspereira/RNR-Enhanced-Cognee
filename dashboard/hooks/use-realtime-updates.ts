/**
 * React Hook for Real-Time Enhanced Cognee Updates
 * Provides SSE connection and WebSocket functionality
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { useToast } from '@/components/ui/use-toast';

interface RealTimeEvent {
  event_type: string;
  data: any;
  timestamp: string;
  client_id?: string;
}

interface UseRealTimeUpdatesOptions {
  eventType?: string;
  onEvent?: (event: RealTimeEvent) => void;
  onError?: (error: Error) => void;
}

interface UseRealTimeUpdatesReturn {
  isConnected: boolean;
  latestEvent: RealTimeEvent | null;
  eventHistory: RealTimeEvent[];
  sendNotification: (event: string, data: any) => Promise<void>;
  reconnect: () => void;
  disconnect: () => void;
}

export function useRealTimeUpdates(
  options: UseRealTimeUpdatesOptions = {}
): UseRealTimeUpdatesReturn {
  const { eventType = 'all', onEvent, onError } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [latestEvent, setLatestEvent] = useState<RealTimeEvent | null>(null);
  const [eventHistory, setEventHistory] = useState<RealTimeEvent[]>([]);

  const eventSourceRef = useRef<EventSource | null>(null);
  const { toast } = useToast();

  // Connect to SSE endpoint
  const connect = useCallback(() => {
    const url = new URL('/api/realtime/events', window.location.origin);
    if (eventType !== 'all') {
      url.searchParams.set('event', eventType);
    }

    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      console.log('[RealTime] Connected to SSE');
    };

    eventSource.onmessage = (event) => {
      try {
        const data: RealTimeEvent = JSON.parse(event.data);

        // Update state
        setLatestEvent(data);
        setEventHistory((prev) => [...prev.slice(-49), data]); // Keep last 50

        // Call custom handler
        if (onEvent) {
          onEvent(data);
        }

        // Show toast for important events
        if (data.event_type === 'memory_added') {
          toast({
            title: 'New Memory Added',
            description: data.data.content_preview,
            duration: 3000,
          });
        } else if (data.event_type === 'error') {
          toast({
            title: 'Error',
            description: data.data.error,
            variant: 'destructive',
            duration: 5000,
          });
        }
      } catch (error) {
        console.error('[RealTime] Failed to parse event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('[RealTime] SSE error:', error);
      setIsConnected(false);

      if (onError) {
        onError(new Error('SSE connection error'));
      }
    };
  }, [eventType, onEvent, onError, toast]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
      console.log('[RealTime] Disconnected from SSE');
    }
  }, []);

  // Reconnect
  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [connect, disconnect]);

  // Send notification to server
  const sendNotification = useCallback(async (event: string, data: any) => {
    try {
      const response = await fetch('/api/realtime/notify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event, data }),
      });

      if (!response.ok) {
        throw new Error('Failed to send notification');
      }
    } catch (error) {
      console.error('[RealTime] Failed to send notification:', error);
      throw error;
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    latestEvent,
    eventHistory,
    sendNotification,
    reconnect,
    disconnect,
  };
}

/**
 * Hook for memory-specific real-time updates
 */
export function useMemoryRealTimeUpdates() {
  const { toast } = useToast();

  return useRealTimeUpdates({
    eventType: 'all',
    onEvent: (event) => {
      switch (event.event_type) {
        case 'memory_added':
          console.log('[Memory] Added:', event.data.memory_id);
          break;
        case 'memory_updated':
          console.log('[Memory] Updated:', event.data.memory_id);
          break;
        case 'memory_deleted':
          toast({
            title: 'Memory Deleted',
            description: `Memory ${event.data.memory_id} was deleted`,
          });
          break;
        case 'search_result':
          console.log('[Search] Results:', event.data.results_count);
          break;
        case 'summary_generated':
          toast({
            title: 'Summary Generated',
            description: `Compression: ${event.data.compression_ratio.toFixed(2)}x`,
          });
          break;
        case 'memory_clustered':
          console.log('[Cluster] Created:', event.data.cluster_id);
          break;
      }
    },
    onError: (error) => {
      toast({
        title: 'Real-Time Connection Error',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for system status monitoring
 */
export function useSystemStatus() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/realtime/stats');
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Update every 30s

    return () => clearInterval(interval);
  }, []);

  return { stats, loading };
}
