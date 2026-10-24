/**
 * Filter store for memory list
 * Persists filters to localStorage and syncs with URL query params
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface MemoryFilters {
  search: string;
  memory_type: string[];
  memory_concept: string[];
  category: string[];
  agent_id: string[];
  date_from: string;
  date_to: string;
  sort_by: "created_at" | "updated_at" | "relevance";
  sort_order: "asc" | "desc";
}

export interface FilterPreset {
  id: string;
  name: string;
  filters: MemoryFilters;
  created_at: string;
}

interface FilterState {
  filters: MemoryFilters;
  selectedMemories: Set<string>;
  presets: FilterPreset[];
  setFilters: (filters: Partial<MemoryFilters>) => void;
  clearFilters: () => void;
  toggleMemorySelection: (id: string) => void;
  selectAllMemories: (ids: string[]) => void;
  deselectAllMemories: () => void;
  isMemorySelected: (id: string) => boolean;
  getSelectedCount: () => number;
  savePreset: (name: string) => void;
  loadPreset: (id: string) => void;
  deletePreset: (id: string) => void;
  syncWithUrl: () => void;
  updateFromUrl: () => void;
}

const DEFAULT_FILTERS: MemoryFilters = {
  search: "",
  memory_type: [],
  memory_concept: [],
  category: [],
  agent_id: [],
  date_from: "",
  date_to: "",
  sort_by: "created_at",
  sort_order: "desc",
};

export const useFilterStore = create<FilterState>()(
  persist(
    (set, get) => ({
      filters: DEFAULT_FILTERS,
      selectedMemories: new Set<string>(),
      presets: [],

      setFilters: (newFilters) => {
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
        }));
        get().syncWithUrl();
      },

      clearFilters: () => {
        set({ filters: DEFAULT_FILTERS });
        get().syncWithUrl();
      },

      toggleMemorySelection: (id) => {
        set((state) => {
          const newSelected = new Set(state.selectedMemories);
          if (newSelected.has(id)) {
            newSelected.delete(id);
          } else {
            newSelected.add(id);
          }
          return { selectedMemories: newSelected };
        });
      },

      selectAllMemories: (ids) => {
        set({ selectedMemories: new Set(ids) });
      },

      deselectAllMemories: () => {
        set({ selectedMemories: new Set() });
      },

      isMemorySelected: (id) => {
        return get().selectedMemories.has(id);
      },

      getSelectedCount: () => {
        return get().selectedMemories.size;
      },

      savePreset: (name) => {
        const preset: FilterPreset = {
          id: `preset-${Date.now()}`,
          name,
          filters: { ...get().filters },
          created_at: new Date().toISOString(),
        };
        set((state) => ({
          presets: [...state.presets, preset],
        }));
      },

      loadPreset: (id) => {
        const preset = get().presets.find((p) => p.id === id);
        if (preset) {
          set({ filters: { ...preset.filters } });
          get().syncWithUrl();
        }
      },

      deletePreset: (id) => {
        set((state) => ({
          presets: state.presets.filter((p) => p.id !== id),
        }));
      },

      syncWithUrl: () => {
        if (typeof window === "undefined") return;

        const filters = get().filters;
        const params = new URLSearchParams();

        if (filters.search) params.set("search", filters.search);
        if (filters.memory_type.length > 0)
          params.set("type", filters.memory_type.join(","));
        if (filters.memory_concept.length > 0)
          params.set("concept", filters.memory_concept.join(","));
        if (filters.category.length > 0)
          params.set("category", filters.category.join(","));
        if (filters.agent_id.length > 0)
          params.set("agent", filters.agent_id.join(","));
        if (filters.date_from) params.set("from", filters.date_from);
        if (filters.date_to) params.set("to", filters.date_to);
        params.set("sort", filters.sort_by);
        params.set("order", filters.sort_order);

        const queryString = params.toString();
        const newUrl = queryString
          ? `${window.location.pathname}?${queryString}`
          : window.location.pathname;

        window.history.replaceState({}, "", newUrl);
      },

      updateFromUrl: () => {
        if (typeof window === "undefined") return;

        const params = new URLSearchParams(window.location.search);
        const newFilters: Partial<MemoryFilters> = {};

        if (params.has("search")) newFilters.search = params.get("search")!;
        if (params.has("type"))
          newFilters.memory_type = params.get("type")!.split(",");
        if (params.has("concept"))
          newFilters.memory_concept = params.get("concept")!.split(",");
        if (params.has("category"))
          newFilters.category = params.get("category")!.split(",");
        if (params.has("agent"))
          newFilters.agent_id = params.get("agent")!.split(",");
        if (params.has("from")) newFilters.date_from = params.get("from")!;
        if (params.has("to")) newFilters.date_to = params.get("to")!;
        if (params.has("sort"))
          newFilters.sort_by = params.get("sort")! as MemoryFilters["sort_by"];
        if (params.has("order"))
          newFilters.sort_order = params.get("order")! as MemoryFilters["sort_order"];

        if (Object.keys(newFilters).length > 0) {
          set((state) => ({
            filters: { ...state.filters, ...newFilters },
          }));
        }
      },
    }),
    {
      name: "memory-filters-storage",
      partialize: (state) => ({
        filters: state.filters,
        presets: state.presets,
        // Don't persist selectedMemories
      }),
    }
  )
);

// Hook to initialize filters from URL on mount
export function useInitializeFiltersFromUrl() {
  const updateFromUrl = useFilterStore((state) => state.updateFromUrl);

  // Only run on client side
  if (typeof window !== "undefined") {
    updateFromUrl();
  }
}
