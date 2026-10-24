"use client";

import { useQuery } from "@tanstack/react-query";
import { getSystemStats, getStructuredStats, checkHealth } from "@/lib/api";
import { queryKeys } from "@/lib/query";

export function useSystemStats() {
  return useQuery({
    queryKey: queryKeys.analytics.systemStats(),
    queryFn: getSystemStats,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

export function useStructuredStats() {
  return useQuery({
    queryKey: queryKeys.analytics.structuredStats(),
    queryFn: getStructuredStats,
    refetchInterval: 60000, // Refetch every minute
  });
}

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.analytics.health(),
    queryFn: checkHealth,
    refetchInterval: 15000, // Refetch every 15 seconds
  });
}
