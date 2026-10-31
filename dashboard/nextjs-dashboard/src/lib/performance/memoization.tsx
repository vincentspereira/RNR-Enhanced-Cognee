/**
 * Performance optimization utilities
 * Includes memoized components and hooks
 */

import { memo, useMemo, type FC } from "react";
import type { Memory } from "@/lib/api/types";

/**
 * Memoized MemoryCard component to prevent unnecessary re-renders
 */
export const MemoizedMemoryCard = memo(function MemoryCard({ memory }: { memory: Memory }) {
  return (
    <div data-testid="memory-card" className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="font-semibold mb-2">{memory.content.substring(0, 100)}...</h3>
      <p className="text-sm text-gray-600">
        {new Date(memory.created_at).toLocaleString()}
      </p>
    </div>
  );
}, (prevProps, nextProps) => {
  // Custom comparison for MemoryCard
  return (
    prevProps.memory.id === nextProps.memory.id &&
    prevProps.memory.updated_at === nextProps.memory.updated_at
  );
});

/**
 * Memoized chart component wrapper
 */
export function withMemo<P extends object>(
  Component: FC<P>,
  displayName?: string
): FC<P> {
  const Memoized = memo(Component, (prevProps, nextProps) => {
    // Deep comparison for complex objects
    return JSON.stringify(prevProps) === JSON.stringify(nextProps);
  });

  Memoized.displayName = displayName || Component.displayName || Component.name || "MemoComponent";

  return Memoized;
}

// Preserve the public helper names using React's native implementations.
export { useMemo as useExpensiveCalculation, useCallback as useEventHandler } from "react";

/**
 * Memoize memory list sorting
 */
export function useSortedMemories(memories: Memory[], sortBy: "date" | "type" | "size"): Memory[] {
  return useMemo(() => {
    const sorted = [...memories];

    switch (sortBy) {
      case "date":
        return sorted.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      case "type":
        return sorted.sort((a, b) =>
          (a.memory_type || "").localeCompare(b.memory_type || "")
        );
      case "size":
        return sorted.sort((a, b) => (b.char_count || 0) - (a.char_count || 0));
      default:
        return sorted;
    }
  }, [memories, sortBy]);
}

/**
 * Memoize memory filtering
 */
export function useFilteredMemories(
  memories: Memory[],
  filters: {
    type?: string;
    concept?: string;
    agentId?: string;
    searchQuery?: string;
  }
): Memory[] {
  return useMemo(() => {
    return memories.filter((memory) => {
      // Type filter
      if (filters.type && memory.memory_type !== filters.type) {
        return false;
      }

      // Concept filter
      if (filters.concept && memory.memory_concept !== filters.concept) {
        return false;
      }

      // Agent filter
      if (filters.agentId && memory.agent_id !== filters.agentId) {
        return false;
      }

      // Search query filter
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const content = memory.content.toLowerCase();
        const summary = (memory.summary || "").toLowerCase();
        if (!content.includes(query) && !summary.includes(query)) {
          return false;
        }
      }

      return true;
    });
  }, [memories, filters.type, filters.concept, filters.agentId, filters.searchQuery]);
}

/**
 * Memoize statistics calculation
 */
export function useMemoryStats(memories: Memory[]) {
  return useMemo(() => {
    const totalMemories = memories.length;
    const totalCharacters = memories.reduce((sum, m) => sum + (m.char_count || 0), 0);
    const totalTokens = memories.reduce((sum, m) => sum + (m.estimated_tokens || 0), 0);

    // Type distribution
    const typeDistribution = memories.reduce((acc, m) => {
      const type = m.memory_type || "unknown";
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Concept distribution
    const conceptDistribution = memories.reduce((acc, m) => {
      const concept = m.memory_concept || "unknown";
      acc[concept] = (acc[concept] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalMemories,
      totalCharacters,
      totalTokens,
      avgTokensPerMemory: totalMemories > 0 ? totalTokens / totalMemories : 0,
      typeDistribution,
      conceptDistribution,
    };
  }, [memories]);
}

/**
 * Debounce hook for search and other expensive operations
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

import { useState, useEffect } from "react";
