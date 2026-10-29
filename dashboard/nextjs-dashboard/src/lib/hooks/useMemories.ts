"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMemories, createMemory, searchMemories } from "@/lib/api";
import type { MemoryFilters } from "@/lib/api";
import { queryKeys } from "@/lib/query";

export function useMemories(filters?: MemoryFilters) {
  return useQuery({
    queryKey: queryKeys.memories.list(filters ? filters as Record<string, unknown> : {}),
    queryFn: () => getMemories(filters),
  });
}

export function useMemory(id: string) {
  return useQuery({
    queryKey: queryKeys.memories.detail(id),
    queryFn: async () => {
      const { getMemory: fetchMemory } = await import("@/lib/api");
      return fetchMemory(id);
    },
    enabled: !!id,
  });
}

export function useCreateMemory() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.memories.all });
    },
  });
}

export function useSearchMemories() {
  return useMutation({
    mutationFn: (params: { query: string; agent_id?: string; limit?: number }) =>
      searchMemories(params),
  });
}
