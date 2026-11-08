import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  // Sidebar
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;

  // Theme
  theme: "dark" | "light" | "system";
  setTheme: (theme: "dark" | "light" | "system") => void;

  // Modals
  activeModal: string | null;
  openModal: (modalId: string) => void;
  closeModal: () => void;

  // Selected items
  selectedMemories: string[];
  setSelectedMemories: (ids: string[]) => void;
  toggleMemorySelection: (id: string) => void;
  clearMemorySelection: () => void;

  // View modes
  memoriesViewMode: "list" | "grid";
  setMemoriesViewMode: (mode: "list" | "grid") => void;

  // Filters (persisted)
  filters: {
    category?: string;
    agent_id?: string;
    memory_type?: string;
  };
  setFilters: (filters: Partial<UIState["filters"]>) => void;
  clearFilters: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Sidebar
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      // Theme
      theme: "dark",
      setTheme: (theme) => set({ theme }),

      // Modals
      activeModal: null,
      openModal: (modalId) => set({ activeModal: modalId }),
      closeModal: () => set({ activeModal: null }),

      // Selected items
      selectedMemories: [],
      setSelectedMemories: (ids) => set({ selectedMemories: ids }),
      toggleMemorySelection: (id) =>
        set((state) => ({
          selectedMemories: state.selectedMemories.includes(id)
            ? state.selectedMemories.filter((sid) => sid !== id)
            : [...state.selectedMemories, id],
        })),
      clearMemorySelection: () => set({ selectedMemories: [] }),

      // View modes
      memoriesViewMode: "list",
      setMemoriesViewMode: (mode) => set({ memoriesViewMode: mode }),

      // Filters
      filters: {},
      setFilters: (newFilters) =>
        set((state) => ({ filters: { ...state.filters, ...newFilters } })),
      clearFilters: () => set({ filters: {} }),
    }),
    {
      name: "enhanced-cognee-ui-storage",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        memoriesViewMode: state.memoriesViewMode,
        filters: state.filters,
      }),
    }
  )
);
