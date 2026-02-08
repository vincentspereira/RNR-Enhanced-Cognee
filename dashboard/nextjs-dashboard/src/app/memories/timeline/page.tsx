"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TimelineView, TimelineDetail } from "@/components/organisms/TimelineView";
import { getMemories } from "@/lib/api/memories";
import { useMemoryFilters } from "@/lib/stores/memoryFilters";
import type { MemoryResponse } from "@/lib/api/types";

export default function TimelinePage() {
  const { filters } = useMemoryFilters();
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);

  // Fetch memories
  const { data: memories = [], isLoading, error } = useQuery<MemoryResponse[]>({
    queryKey: ["memories", "timeline", filters],
    queryFn: () =>
      getMemories({
        limit: 1000, // Get more memories for timeline
        ...filters,
      }),
  });

  const handleMemoryClick = (memoryId: string) => {
    setSelectedMemoryId(memoryId);
    // Could open a modal or navigate to detail page
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">Error loading timeline: {(error as Error).message}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100 mb-2">Memory Timeline</h1>
        <p className="text-slate-400">
          Visualize your memories chronologically with filtering and export capabilities
        </p>
      </div>

      <div className="space-y-8">
        {/* Timeline Visualization */}
        <TimelineView memories={memories} />

        {/* Timeline Details */}
        <TimelineDetail
          memories={memories}
          onMemoryClick={handleMemoryClick}
        />
      </div>
    </div>
  );
}
