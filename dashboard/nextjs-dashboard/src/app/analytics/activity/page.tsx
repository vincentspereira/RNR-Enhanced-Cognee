"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ActivityHeatmap } from "@/components/organisms/ActivityHeatmap";
import { getMemories } from "@/lib/api/memories";
import { useMemoryFilters } from "@/lib/stores/memoryFilters";
import type { MemoryResponse } from "@/lib/api/types";

export default function ActivityPage() {
  const { filters } = useMemoryFilters();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  // Fetch memories for heatmap
  const { data: memories = [], isLoading, error } = useQuery<MemoryResponse[]>({
    queryKey: ["memories", "activity", filters],
    queryFn: () =>
      getMemories({
        limit: 10000, // Get all memories for the heatmap
        ...filters,
      }),
  });

  const handleDayClick = (date: Date) => {
    setSelectedDate(date);
    // Could filter memories list or show a modal with that day's memories
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
        <div className="text-red-500">Error loading activity: {(error as Error).message}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-100 mb-2">Activity Heatmap</h1>
        <p className="text-slate-400">
          Visualize your memory activity over the last 365 days
        </p>
      </div>

      <ActivityHeatmap
        memories={memories}
        days={365}
        onDayClick={handleDayClick}
      />

      {selectedDate && (
        <div className="mt-6 bg-slate-800 rounded-lg p-4 border border-slate-700">
          <p className="text-slate-300">
            Selected: {selectedDate.toLocaleDateString()}
          </p>
          <p className="text-sm text-slate-400 mt-2">
            Feature coming soon: Show memories from this date
          </p>
        </div>
      )}
    </div>
  );
}
