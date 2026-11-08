// Query keys factory for TanStack Query
export const queryKeys = {
  // Memories
  memories: {
    all: ["memories"] as const,
    lists: () => [...queryKeys.memories.all, "list"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.memories.lists(), filters] as const,
    details: () => [...queryKeys.memories.all, "detail"] as const,
    detail: (id: string) =>
      [...queryKeys.memories.details(), id] as const,
    search: (query: string) =>
      [...queryKeys.memories.all, "search", query] as const,
  },

  // Sessions
  sessions: {
    all: ["sessions"] as const,
    lists: () => [...queryKeys.sessions.all, "list"] as const,
    list: (filters: Record<string, unknown>) =>
      [...queryKeys.sessions.lists(), filters] as const,
    details: () => [...queryKeys.sessions.all, "detail"] as const,
    detail: (id: string) =>
      [...queryKeys.sessions.details(), id] as const,
  },

  // Analytics
  analytics: {
    all: ["analytics"] as const,
    systemStats: () => [...queryKeys.analytics.all, "system"] as const,
    structuredStats: () => [...queryKeys.analytics.all, "structured"] as const,
    health: () => [...queryKeys.analytics.all, "health"] as const,
  },

  // Timeline
  timeline: (memoryId: string) =>
    ["timeline", memoryId] as const,
} as const;
