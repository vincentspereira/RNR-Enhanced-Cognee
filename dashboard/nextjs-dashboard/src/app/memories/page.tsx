"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Input, Card, CardContent } from "@/components/atoms";
import { MemoryCard } from "@/components/molecules";
import { MemoryListSkeleton, AddMemoryModal } from "@/components/organisms";
import { useFilterStore, useUIStore } from "@/lib/stores";
import type { MemoryFilters } from "@/lib/stores/filterStore";
import { deleteMemory } from "@/lib/api/memories";
import { queryKeys } from "@/lib/query/queryKeys";
import { toast } from "sonner";
import {
  Search,
  RefreshCw,
  Grid3x3,
  List,
  Filter,
  X,
  Download,
  Trash2,
  CheckSquare,
  Square,
  Plus
} from "lucide-react";

export default function MemoriesListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const {
    filters,
    setFilters,
    clearFilters,
    selectedMemories,
    toggleMemorySelection,
    selectAllMemories,
    deselectAllMemories,
    isMemorySelected,
    getSelectedCount,
  } = useFilterStore();
  const {
    memoriesViewMode: viewMode,
    setMemoriesViewMode: setViewMode,
  } = useUIStore();

  const [localSearch, setLocalSearch] = useState(filters.search);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Pre-apply agent_id filter from query param (e.g. when navigating from /agents)
  useEffect(() => {
    const agentId = searchParams.get("agent_id");
    if (agentId) {
      setFilters({ agent_id: [agentId] });
    }
  }, [searchParams, setFilters]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters({ search: localSearch });
    }, 300);
    return () => clearTimeout(timer);
  }, [localSearch, setFilters]);

  // Infinite scroll query
  const {
    data,
    isLoading,
    isError,
    error,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
    refetch,
  } = useInfiniteQuery({
    queryKey: ["memories", filters],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(
        `${apiBase}/api/memories?limit=50&offset=${pageParam}&${buildQueryString(filters)}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch memories");
      }
      const json = await response.json();
      // Normalize memory_id -> id for MemoryCard compatibility
      const rawMemories: Record<string, unknown>[] = json.memories || json || [];
      return {
        ...json,
        memories: rawMemories.map((m) => ({
          ...m,
          id: (m.id as string) || (m.memory_id as string),
        })),
      };
    },
    getNextPageParam: (lastPage, allPages) => {
      const mems = (lastPage as { memories: unknown[] }).memories || [];
      if (mems.length < 50) return undefined;
      return allPages.length * 50;
    },
    initialPageParam: 0,
  });

  // Flatten all pages
  type MemoryItem = {
    id: string;
    content: string;
    summary?: string;
    memory_type?: string;
    memory_concept?: string;
    data_type?: string;
    created_at: string;
    updated_at?: string;
    char_count?: number;
    estimated_tokens?: number;
    metadata?: Record<string, unknown>;
    [key: string]: unknown;
  };
  const memories = (data?.pages.flatMap((page) => (page as { memories: MemoryItem[] }).memories) || []) as MemoryItem[];
  const allMemoryIds = memories.map((m) => m.id);

  // Pull to refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  // Handle view memory
  const handleViewMemory = (id: string) => {
    router.push(`/memories/${id}`);
  };

  // Handle edit memory
  const handleEditMemory = (id: string) => {
    router.push(`/memories/${id}/edit`);
  };

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.memories.all });
      toast.success("Memory deleted");
    },
    onError: (error: Error) => {
      toast.error("Failed to delete memory", { description: error.message });
    },
  });

  // Handle delete memory
  const handleDeleteMemory = (id: string) => {
    if (confirm("Are you sure you want to delete this memory?")) {
      deleteMutation.mutate(id);
    }
  };

  // Handle select all
  const handleSelectAll = () => {
    if (getSelectedCount() === memories.length) {
      deselectAllMemories();
    } else {
      selectAllMemories(allMemoryIds);
    }
  };

  // Handle batch delete
  const handleBatchDelete = async () => {
    const ids = Array.from(selectedMemories);
    const count = ids.length;
    if (confirm(`Are you sure you want to delete ${count} memories?`)) {
      try {
        await Promise.all(ids.map((id) => deleteMemory(id)));
        queryClient.invalidateQueries({ queryKey: queryKeys.memories.all });
        toast.success(`Deleted ${count} memories`);
      } catch (error) {
        toast.error("Some deletions failed", {
          description: error instanceof Error ? error.message : "Unknown error",
        });
      } finally {
        deselectAllMemories();
      }
    }
  };

  // Build query string from filters
  function buildQueryString(filters: MemoryFilters) {
    const params = new URLSearchParams();
    if (filters.search) params.set("search", filters.search);
    if (filters.memory_type.length > 0)
      params.set("memory_type", filters.memory_type.join(","));
    if (filters.memory_concept.length > 0)
      params.set("memory_concept", filters.memory_concept.join(","));
    if (filters.category.length > 0)
      params.set("category", filters.category.join(","));
    if (filters.agent_id.length > 0)
      params.set("agent_id", filters.agent_id.join(","));
    if (filters.date_from) params.set("date_from", filters.date_from);
    if (filters.date_to) params.set("date_to", filters.date_to);
    return params.toString();
  }

  // Infinite scroll handler
  const handleScroll = useCallback(() => {
    const scrollTop = window.scrollY;
    const scrollHeight = document.documentElement.scrollHeight;
    const clientHeight = window.innerHeight;

    if (scrollHeight - scrollTop - clientHeight < 500 && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  useEffect(() => {
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Memories</h1>
          <p className="text-muted-foreground">
            Browse and manage your AI memories ({memories.length} total)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode(viewMode === "list" ? "grid" : "list")}
          >
            {viewMode === "list" ? <Grid3x3 className="h-4 w-4" /> : <List className="h-4 w-4" />}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
            {Object.values(filters).some(
              (v) => Array.isArray(v) ? v.length > 0 : v !== ""
            ) && (
              <span className="ml-2 h-2 w-2 rounded-full bg-primary" />
            )}
          </Button>
          <Button onClick={() => setIsAddModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Memory
          </Button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search memories..."
              className="pl-10"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
            />
            {localSearch && (
              <button
                onClick={() => setLocalSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2"
              >
                <X className="h-4 w-4 text-muted-foreground hover:text-foreground" />
              </button>
            )}
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Expanded Filters */}
        {showFilters && (
          <Card>
            <CardContent className="p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {/* Memory Type */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Memory Type</label>
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={filters.memory_type[0] || ""}
                    onChange={(e) =>
                      setFilters({ memory_type: e.target.value ? [e.target.value] : [] })
                    }
                  >
                    <option value="">All Types</option>
                    <option value="bugfix">Bug Fix</option>
                    <option value="feature">Feature</option>
                    <option value="decision">Decision</option>
                    <option value="refactor">Refactor</option>
                    <option value="discovery">Discovery</option>
                    <option value="general">General</option>
                  </select>
                </div>

                {/* Memory Concept */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Memory Concept</label>
                  <select
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={filters.memory_concept[0] || ""}
                    onChange={(e) =>
                      setFilters({ memory_concept: e.target.value ? [e.target.value] : [] })
                    }
                  >
                    <option value="">All Concepts</option>
                    <option value="how-it-works">How It Works</option>
                    <option value="gotcha">Gotcha</option>
                    <option value="trade-off">Trade Off</option>
                    <option value="pattern">Pattern</option>
                    <option value="general">General</option>
                  </select>
                </div>

                {/* Agent ID */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Agent</label>
                  <Input
                    placeholder="Agent ID"
                    value={filters.agent_id[0] || ""}
                    onChange={(e) =>
                      setFilters({ agent_id: e.target.value ? [e.target.value] : [] })
                    }
                  />
                </div>

                {/* Date Range */}
                <div>
                  <label className="text-sm font-medium mb-2 block">Date Range</label>
                  <Input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) => setFilters({ date_from: e.target.value })}
                  />
                </div>
              </div>

              {/* Clear Filters */}
              <div className="mt-4 flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-muted-foreground"
                >
                  Clear All Filters
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Batch Actions Toolbar */}
      {getSelectedCount() > 0 && (
        <Card className="border-primary">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">
                  {getSelectedCount()} memories selected
                </span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handleSelectAll}>
                    {getSelectedCount() === memories.length ? (
                      <CheckSquare className="h-4 w-4 mr-2" />
                    ) : (
                      <Square className="h-4 w-4 mr-2" />
                    )}
                    {getSelectedCount() === memories.length ? "Deselect All" : "Select All"}
                  </Button>
                  <Button variant="outline" size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                  <Button variant="destructive" size="sm" onClick={handleBatchDelete}>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </Button>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={deselectAllMemories}>
                Clear Selection
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Memories List */}
      {isLoading ? (
        <MemoryListSkeleton count={10} />
      ) : isError ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
          <p className="text-destructive mb-4">Error loading memories: {error.message}</p>
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      ) : memories.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">
            {Object.values(filters).some((v) => (Array.isArray(v) ? v.length > 0 : v !== ""))
              ? "No memories found matching your filters."
              : "No memories found. Start by adding your first memory!"}
          </p>
          {Object.values(filters).some((v) => (Array.isArray(v) ? v.length > 0 : v !== "")) && (
            <Button variant="outline" onClick={clearFilters}>
              Clear Filters
            </Button>
          )}
        </div>
      ) : (
        <div
          className={
            viewMode === "grid"
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              : "space-y-4"
          }
        >
          {memories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              isSelected={isMemorySelected(memory.id)}
              onSelect={toggleMemorySelection}
              onView={handleViewMemory}
              onEdit={handleEditMemory}
              onDelete={handleDeleteMemory}
              variant={viewMode === "grid" ? "compact" : "default"}
            />
          ))}
        </div>
      )}

      {/* Load More Indicator */}
      {isFetchingNextPage && <MemoryListSkeleton count={3} />}

      {/* Results Count */}
      {!isLoading && !isError && memories.length > 0 && (
        <div className="text-sm text-muted-foreground text-center">
          Showing {memories.length} memories
          {hasNextPage && " (scroll to load more)"}
        </div>
      )}

      {/* Add Memory Modal */}
      <AddMemoryModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
      />
    </div>
  );
}
