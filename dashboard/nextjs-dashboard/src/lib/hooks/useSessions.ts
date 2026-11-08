"use client";

import { useQuery } from "@tanstack/react-query";
import { getSessions } from "@/lib/api";
import type { SessionFilters } from "@/lib/api";
import { queryKeys } from "@/lib/query";

export function useSessions(filters?: SessionFilters) {
  return useQuery({
    queryKey: queryKeys.sessions.list(filters ? filters as Record<string, unknown> : {}),
    queryFn: () => getSessions(filters),
  });
}

export function useSession(id: string) {
  return useQuery({
    queryKey: queryKeys.sessions.detail(id),
    queryFn: async () => {
      const { getSession } = await import("@/lib/api");
      return getSession(id);
    },
    enabled: !!id,
  });
}
