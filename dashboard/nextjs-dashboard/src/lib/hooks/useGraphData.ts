/**
 * useGraphData Hook
 *
 * TanStack Query hook for fetching and caching graph data.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getGraphData,
  getNodeNeighbors,
  searchNodes,
  getNodeDetails,
  getGraphStats,
  type GraphQueryParams,
} from "@/lib/api/neo4j";

/**
 * Hook for fetching graph data
 */
export function useGraphData(params?: GraphQueryParams, enabled: boolean = true) {
  return useQuery({
    queryKey: ["graph", params],
    queryFn: () => getGraphData(params),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook for fetching node neighbors
 */
export function useNodeNeighbors(nodeId: string, depth: number = 1, enabled: boolean = true) {
  return useQuery({
    queryKey: ["graph", "neighbors", nodeId, depth],
    queryFn: () => getNodeNeighbors(nodeId, depth),
    enabled: enabled && !!nodeId,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook for searching nodes
 */
export function useNodeSearch(query: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["graph", "search", query],
    queryFn: () => searchNodes(query),
    enabled: enabled && query.length > 2,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Hook for fetching node details
 */
export function useNodeDetails(nodeId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["graph", "node", nodeId, "details"],
    queryFn: () => getNodeDetails(nodeId),
    enabled: enabled && !!nodeId,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook for fetching graph statistics
 */
export function useGraphStats(enabled: boolean = true) {
  return useQuery({
    queryKey: ["graph", "stats"],
    queryFn: getGraphStats,
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Hook for invalidating graph queries
 */
export function useGraphInvalidate() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () =>
      queryClient.invalidateQueries({
        queryKey: ["graph"],
      }),
    invalidateNode: (nodeId: string) =>
      queryClient.invalidateQueries({
        queryKey: ["graph", "node", nodeId],
      }),
    invalidateStats: () =>
      queryClient.invalidateQueries({
        queryKey: ["graph", "stats"],
      }),
  };
}
