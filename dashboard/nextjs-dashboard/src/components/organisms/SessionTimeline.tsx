"use client";

import React from "react";
import { format, parseISO } from "date-fns";
import type { MemoryResponse } from "@/lib/api/types";

export interface SessionTimelineProps {
  memories: MemoryResponse[];
  className?: string;
  onMemoryClick?: (memoryId: string) => void;
}

/**
 * Session Timeline Component
 *
 * Displays a chronological timeline of memories within a session.
 */
export function SessionTimeline({
  memories,
  className = "",
  onMemoryClick,
}: SessionTimelineProps) {
  // Sort memories by created_at
  const sortedMemories = React.useMemo(() => {
    return [...memories].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  }, [memories]);

  // Group by hour
  const groupedMemories = React.useMemo(() => {
    const groups: Record<string, MemoryResponse[]> = {};

    sortedMemories.forEach((memory) => {
      const hour = format(parseISO(memory.created_at), "ha");
      if (!groups[hour]) {
        groups[hour] = [];
      }
      groups[hour].push(memory);
    });

    return Object.entries(groups).sort(([a], [b]) => {
      // Simple string comparison works for "ha" format (e.g., "9AM", "10PM")
      return a.localeCompare(b);
    });
  }, [sortedMemories]);

  return (
    <div className={`bg-slate-900 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-200">Session Timeline</h3>
          <span className="text-sm text-slate-400">({memories.length} memories)</span>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical Line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-700" />

        {/* Memory Groups */}
        <div className="space-y-6">
          {groupedMemories.map(([hour, hourMemories]) => (
            <div key={hour} className="relative pl-12">
              {/* Hour Marker */}
              <div className="absolute left-0 top-0 w-8 h-8 bg-slate-800 border-2 border-slate-600 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
              </div>

              {/* Hour Label */}
              <div className="mb-3">
                <span className="text-sm font-medium text-slate-300">{hour}</span>
              </div>

              {/* Memories in this hour */}
              <div className="space-y-2">
                {hourMemories.map((memory) => (
                  <div
                    key={memory.memory_id}
                    onClick={() => onMemoryClick?.(memory.memory_id)}
                    className="relative p-4 bg-slate-800 rounded-lg border border-slate-700 hover:border-slate-600 cursor-pointer transition-colors"
                  >
                    {/* Timeline Dot */}
                    <div className="absolute left-[-29px] top-4 w-3 h-3 bg-blue-500 rounded-full border-2 border-slate-800" />

                    {/* Memory Type Badge */}
                    {memory.memory_type && (
                      <div className="mb-2">
                        <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-500/20 text-blue-300 capitalize">
                          {memory.memory_type}
                        </span>
                      </div>
                    )}

                    {/* Memory Content */}
                    <p className="text-sm text-slate-300 line-clamp-2 mb-2">
                      {memory.summary || memory.content.slice(0, 200)}
                    </p>

                    {/* Metadata */}
                    <div className="flex items-center gap-4 text-xs text-slate-400">
                      <span>{format(parseISO(memory.created_at), "h:mm a")}</span>
                      {memory.estimated_tokens && (
                        <span>{memory.estimated_tokens} tokens</span>
                      )}
                      {memory.char_count && (
                        <span>{memory.char_count} chars</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {memories.length === 0 && (
        <div className="flex items-center justify-center h-[200px] text-slate-400">
          <p>No memories in this session</p>
        </div>
      )}
    </div>
  );
}
